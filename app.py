from urllib import response

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
    jsonify,
)
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from flask import g
import os
import requests
import secrets
from werkzeug.security import generate_password_hash, check_password_hash
import time
import qrcode
from zoneinfo import ZoneInfo
from itsdangerous import URLSafeTimedSerializer, BadSignature
from cashfree_pg.api_client import Cashfree
from cashfree_pg.models.create_order_request import CreateOrderRequest
from cashfree_pg.models.customer_details import CustomerDetails
from cashfree_pg.models.order_meta import OrderMeta
import uuid
import io
import re
import csv
import zipfile
from flask_mail import Mail, Message
from dotenv import load_dotenv
from flask_wtf.csrf import CSRFProtect
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from io import BytesIO
from flask import send_file
from flask import url_for
from datetime import datetime, timezone, timedelta
from flask import abort
from flask_migrate import Migrate

load_dotenv()
app = Flask(__name__)


app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY")

if not app.config["SECRET_KEY"]:
    raise RuntimeError("SECRET_KEY is missing. Check your .env file.")

csrf = CSRFProtect(app)
app.config["MAIL_SERVER"] = "smtp.gmail.com"
app.config["MAIL_PORT"] = 587
app.config["MAIL_USE_TLS"] = True
app.config["MAIL_USERNAME"] = os.environ.get("MAIL_USERNAME")
app.config["MAIL_PASSWORD"] = os.environ.get("MAIL_PASSWORD")
app.config["MAIL_DEFAULT_SENDER"] = os.environ.get("MAIL_DEFAULT_SENDER")
mail = Mail(app)


database_url = os.environ.get("DATABASE_URL")

if database_url and database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = database_url or "sqlite:///tagbandhu.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False


db = SQLAlchemy(app)
def get_cashfree_client():
    client_id = os.environ.get("CASHFREE_CLIENT_ID")
    client_secret = os.environ.get("CASHFREE_CLIENT_SECRET")

    if not client_id or not client_secret:
        raise RuntimeError("Cashfree credentials are missing.")

    environment = os.environ.get("CASHFREE_ENV", "SANDBOX").upper()

    if environment == "SANDBOX":
        cashfree_environment = Cashfree.SANDBOX
    elif environment == "PRODUCTION":
        cashfree_environment = Cashfree.PRODUCTION
    else:
        raise RuntimeError("Invalid Cashfree environment.")

    return Cashfree(
        XEnvironment=cashfree_environment,
        XClientId=client_id,
        XClientSecret=client_secret
    )

migrate = Migrate(app, db)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    password_hash = db.Column(db.String(256), nullable=False)

    is_active = db.Column(db.Boolean, default=True, nullable=False)
    email_verified = db.Column(db.Boolean, default=False, nullable=False)
    email_otp_hash = db.Column(db.String(256), nullable=True)
    email_otp_expires_at = db.Column(db.DateTime, nullable=True)
    email_otp_attempts = db.Column(db.Integer, default=0, nullable=False)
    email_otp_last_sent_at = db.Column(db.DateTime, nullable=True)


class Tag(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    # Unique ID printed on the physical tag
    tag_code = db.Column(db.String(64), unique=True, nullable=False)

    # elderly, child, luggage, everyday
    tag_type = db.Column(db.String(30), nullable=False)

    # No owner until a customer activates the tag
    owner_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)

    # Inventory tags start inactive
    is_active = db.Column(db.Boolean, default=False, nullable=False)

    created_at = db.Column(db.DateTime, server_default=db.func.now())

    activated_at = db.Column(db.DateTime, nullable=True)

    owner = db.relationship("User", backref=db.backref("tags", lazy=True))


class ContactMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    tag_id = db.Column(db.Integer, db.ForeignKey("tag.id"), nullable=False)

    sender_name = db.Column(db.String(100), nullable=False)
    sender_phone = db.Column(db.String(20), nullable=True, default="")
    sender_email = db.Column(db.String(120), nullable=False)
    message = db.Column(db.Text, nullable=False)

    is_read = db.Column(db.Boolean, default=False, nullable=False)

    created_at = db.Column(db.DateTime, server_default=db.func.now())

    tag = db.relationship("Tag", backref=db.backref("messages", lazy=True))


class TagActivity(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    tag_id = db.Column(db.Integer, db.ForeignKey("tag.id"), nullable=False)

    action = db.Column(db.String(30), nullable=False)
    details = db.Column(db.String(255), nullable=True, default="")

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(ZoneInfo("Asia/Kolkata")),
    )

    tag = db.relationship("Tag", backref=db.backref("activity_history", lazy=True))


class TagOrder(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    order_id = db.Column(db.String(45), unique=True, nullable=False)
    product_code = db.Column(db.String(50), nullable=False)
    product_name = db.Column(db.String(100), nullable=False)

    amount = db.Column(db.Numeric(10, 2), nullable=False)
    currency = db.Column(db.String(3), default="INR", nullable=False)
    status = db.Column(db.String(20), default="PENDING", nullable=False)

    payment_session_id = db.Column(db.String(1000))
    cf_order_id = db.Column(db.String(50))

    customer_name = db.Column(db.String(100), nullable=False)
    customer_email = db.Column(db.String(120), nullable=False)
    customer_phone = db.Column(db.String(10), nullable=False)

    shipping_address = db.Column(db.Text, nullable=False)
    shipping_city = db.Column(db.String(100), nullable=False)
    shipping_state = db.Column(db.String(100), nullable=False)
    shipping_pincode = db.Column(db.String(10), nullable=False)

    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    paid_at = db.Column(db.DateTime(timezone=True))

def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        user_id = session.get("user_id")

        if not user_id:
            flash("Please log in to access your dashboard.")
            return redirect(url_for("login"))

        user = db.session.get(User, user_id)

        if user is None or not user.is_active:
            session.clear()
            flash("Your account is inactive or unavailable. Please contact support.")
            return redirect(url_for("login"))

        return view(*args, **kwargs)

    return wrapped_view


# Android registration API
@app.route("/api/register", methods=["POST"])
@csrf.exempt
def api_register():
    data = request.get_json(silent=True) or {}

    name = str(data.get("name", "")).strip()
    phone = str(data.get("phone", "")).strip()
    email = str(data.get("email", "")).strip().lower()
    password = data.get("password", "")
    consent = data.get("consent", False)

    if not name or not phone or not email or not isinstance(password, str):
        return jsonify({
            "success": False,
            "message": "All fields are required."
        }), 400

    if not re.fullmatch(r"[A-Za-z]+(?:[ '-][A-Za-z]+)*", name):
        return jsonify({
            "success": False,
            "message": "Please enter a valid name."
        }), 400

    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        return jsonify({
            "success": False,
            "message": "Please enter a valid email address."
        }), 400

    if len(password) < 8 or len(password) > 128:
        return jsonify({
            "success": False,
            "message": "Password must be 8 to 128 characters."
        }), 400

    if not (
        re.search(r"[A-Z]", password)
        and re.search(r"[a-z]", password)
        and re.search(r"\d", password)
        and re.search(r"[^A-Za-z0-9]", password)
    ):
        return jsonify({
            "success": False,
            "message": (
                "Password must contain uppercase, lowercase, "
                "a number and a special character."
            )
        }), 400

    if consent is not True:
        return jsonify({
            "success": False,
            "message": "Please accept the Terms and Privacy Policy."
        }), 400

    existing_user = db.session.scalar(
        db.select(User).filter_by(email=email)
    )

    if existing_user:
        return jsonify({
            "success": False,
            "message": (
                "An account with this email already exists. "
                "If it is unverified, request a new OTP."
            )
        }), 409

    otp = str(secrets.randbelow(900000) + 100000)
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    user = User(
        name=name,
        phone=phone,
        email=email,
        password_hash=generate_password_hash(password),
        email_verified=False,
        email_otp_hash=generate_password_hash(otp),
        email_otp_expires_at=now + timedelta(minutes=5),
        email_otp_attempts=0,
        email_otp_last_sent_at=now,
    )

    try:
        db.session.add(user)

        msg = Message(
            subject="Verify your Tagbandhu email",
            recipients=[email],
            body=(
                f"Hello {name},\n\n"
                f"Your Tagbandhu verification code is: {otp}\n\n"
                "This code expires in 5 minutes. "
                "Do not share it with anyone."
            ),
        )

        mail.send(msg)
        db.session.commit()

        return jsonify({
            "success": True,
            "message": "Registration successful. Check your email for the OTP."
        }), 201

    except Exception:
        db.session.rollback()
        app.logger.exception("Android registration failed.")
        return jsonify({
            "success": False,
            "message": "Registration failed. Please try again."
        }), 500


# Android email OTP verification API
@app.route("/api/verify-email", methods=["POST"])
@csrf.exempt
def api_verify_email():
    data = request.get_json(silent=True) or {}

    email = str(data.get("email", "")).strip().lower()
    otp = str(data.get("otp", "")).strip()

    if not email or not re.fullmatch(r"\d{6}", otp):
        return jsonify({
            "success": False,
            "message": "Enter a valid email and 6-digit OTP."
        }), 400

    user = db.session.scalar(
        db.select(User).filter_by(email=email)
    )

    if not user:
        return jsonify({
            "success": False,
            "message": "Account not found. Please register first."
        }), 404

    if user.email_verified:
        return jsonify({
            "success": True,
            "message": "Email is already verified."
        }), 200

    if (
        not user.email_otp_hash
        or not user.email_otp_expires_at
    ):
        return jsonify({
            "success": False,
            "message": "OTP unavailable. Please request a new OTP."
        }), 400

    if user.email_otp_attempts >= 5:
        return jsonify({
            "success": False,
            "message": "Too many attempts. Please request a new OTP."
        }), 429

    now = datetime.now(timezone.utc).replace(tzinfo=None)

    if now >= user.email_otp_expires_at:
        return jsonify({
            "success": False,
            "message": "OTP expired. Please request a new OTP."
        }), 400

    if not check_password_hash(user.email_otp_hash, otp):
        user.email_otp_attempts += 1
        db.session.commit()

        return jsonify({
            "success": False,
            "message": "Incorrect OTP."
        }), 400

    user.email_verified = True
    user.email_otp_hash = None
    user.email_otp_expires_at = None
    user.email_otp_attempts = 0

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        app.logger.exception("Android email verification failed.")

        return jsonify({
            "success": False,
            "message": "Verification failed. Please try again."
        }), 500

    return jsonify({
        "success": True,
        "message": "Email verified successfully. You can now log in."
    }), 200


# Android resend OTP API
@app.route("/api/resend-verification", methods=["POST"])
@csrf.exempt
def api_resend_verification():
    data = request.get_json(silent=True) or {}
    email = str(data.get("email", "")).strip().lower()

    if not email:
        return jsonify({
            "success": False,
            "message": "Email is required."
        }), 400

    user = db.session.scalar(
        db.select(User).filter_by(email=email)
    )

    if not user:
        return jsonify({
            "success": False,
            "message": "Account not found. Please register first."
        }), 404

    if user.email_verified:
        return jsonify({
            "success": False,
            "message": "This email is already verified."
        }), 400

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    last_sent = user.email_otp_last_sent_at

    if last_sent and (now - last_sent).total_seconds() < 60:
        return jsonify({
            "success": False,
            "message": "Please wait 60 seconds before requesting another OTP."
        }), 429

    otp = str(secrets.randbelow(900000) + 100000)

    msg = Message(
        subject="Your new Tagbandhu verification code",
        recipients=[email],
        body=(
            f"Hello {user.name},\n\n"
            f"Your new Tagbandhu verification code is: {otp}\n\n"
            "This code expires in 5 minutes. "
            "Do not share it with anyone."
        ),
    )

    try:
        mail.send(msg)

        user.email_otp_hash = generate_password_hash(otp)
        user.email_otp_expires_at = now + timedelta(minutes=5)
        user.email_otp_attempts = 0
        user.email_otp_last_sent_at = now

        db.session.commit()

        return jsonify({
            "success": True,
            "message": "A new verification code has been sent."
        }), 200

    except Exception:
        db.session.rollback()
        app.logger.exception("Android OTP resend failed.")

        return jsonify({
            "success": False,
            "message": "Could not send OTP. Please try again."
        }), 500

@app.route("/test-email")
@login_required
def test_email():
    recipient = session.get("user_email")

    if not recipient:
        return "User email not found in session.", 400

    try:
        msg = Message(
            subject="Tagbandhu Email Test",
            recipients=[recipient],
            body="Your Tagbandhu email notification setup is working.",
        )
        mail.send(msg)
        return "Test email sent successfully!"
    except Exception:
        app.logger.exception("Tagbandhu test email failed.")
        return "Email failed. Check the Flask terminal logs.", 500


def admin_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if not session.get("is_admin"):
            return redirect(url_for("admin_login"))
        return view(*args, **kwargs)

    return wrapped_view


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        admin_key = os.environ.get("TAGBANDHU_ADMIN_KEY")
        submitted_key = request.form.get("admin_key", "")

        if not admin_key:
            app.logger.error("TAGBANDHU_ADMIN_KEY is not configured.")
            abort(503, description="Admin functionality is not configured.")

        if not secrets.compare_digest(submitted_key, admin_key):
            flash("Invalid admin key.")
            return redirect(url_for("admin_login"))

        session["is_admin"] = True
        return redirect(url_for("admin_inventory"))

    return render_template("admin_login.html")


@app.route("/admin/logout", methods=["POST"])
def admin_logout():
    session.pop("is_admin", None)
    flash("Admin logged out.")
    return redirect(url_for("admin_login"))


@app.route("/api/health", methods=["GET"])
def api_health():
    return jsonify({"success": True, "message": "Tagbandhu API is running"})


# -------------------- ANDROID API: LOGIN & MY TAGS --------------------

api_token_serializer = URLSafeTimedSerializer(
    app.config["SECRET_KEY"],
    salt="tagbandhu-android-api",
)


@app.route("/api/login", methods=["POST"])
@csrf.exempt
def api_login():
    data = request.get_json(silent=True) or {}

    email = str(data.get("email", "")).strip().lower()
    password = data.get("password", "")

    if not isinstance(password, str) or not email or not password:
        return (
            jsonify({"success": False, "message": "Email and password are required."}),
            400,
        )

    user = db.session.scalar(db.select(User).filter_by(email=email))

    if not user or not check_password_hash(user.password_hash, password):
        return jsonify({"success": False, "message": "Invalid email or password."}), 401
    
    if not user.email_verified:
        return jsonify({
            "success": False,
            "message": "Please verify your email before logging in.",
            "email_verification_required": True,
        }), 403
    
    if not user.is_active:
        return jsonify({"success": False, "message": "Your account is inactive."}), 403

    token = api_token_serializer.dumps({"user_id": user.id})

    return jsonify(
        {
            "success": True,
            "message": "Login successful.",
            "token": token,
            "user": {
                "id": user.id,
                "name": user.name,
                "email": user.email,
                "phone": user.phone or "",
            },
        }
    )


@app.route("/api/my-tags", methods=["GET"])
def api_my_tags():
    auth_header = request.headers.get("Authorization", "")
    parts = auth_header.split(" ", 1)

    if len(parts) != 2 or parts[0].lower() != "bearer":
        return (
            jsonify({"success": False, "message": "Authentication token required."}),
            401,
        )

    token = parts[1].strip()

    try:
        payload = api_token_serializer.loads(token, max_age=604800)
    except BadSignature:
        return (
            jsonify(
                {
                    "success": False,
                    "message": "Invalid or expired token. Please log in again.",
                }
            ),
            401,
        )

    user = db.session.get(User, payload.get("user_id"))

    if user is None or not user.is_active:
        return (
            jsonify({"success": False, "message": "Account inactive or unavailable."}),
            401,
        )

    tags = db.session.scalars(
        db.select(Tag).filter_by(owner_id=user.id).order_by(Tag.id.desc())
    ).all()

    return jsonify(
        {
            "success": True,
            "tags": [
                {
                    "id": tag.id,
                    "tag_code": tag.tag_code,
                    "tag_type": tag.tag_type,
                    "is_active": tag.is_active,
                    "activated_at": (
                        tag.activated_at.isoformat() if tag.activated_at else None
                    ),
                }
                for tag in tags
            ],
        }
    )


@app.route("/api/profile", methods=["GET", "PUT"])
@csrf.exempt
def api_profile():
    from flask import jsonify, request

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return jsonify({"success": False, "message": "Authentication required"}), 401

    token = auth_header.split(" ", 1)[1]

    try:
        payload = api_token_serializer.loads(token, max_age=604800)
    except BadSignature:
        return jsonify({"success": False, "message": "Invalid or expired token"}), 401
    except Exception:
        return jsonify({"success": False, "message": "Invalid or expired token"}), 401

    user = db.session.get(User, payload.get("user_id"))

    if not user or not user.is_active:
        return jsonify({"success": False, "message": "User not found or inactive"}), 401

    if request.method == "PUT":
        data = request.get_json(silent=True) or {}

        name = str(data.get("name", "")).strip()
        phone = str(data.get("phone", "")).strip()

        if not name:
            return jsonify({"success": False, "message": "Name is required"}), 400

        user.name = name
        user.phone = phone

        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            return jsonify({"success": False, "message": "Could not update profile"}), 500

    return jsonify({
        "success": True,
        "user": {
            "id": user.id,
            "name": user.name or "",
            "email": user.email or "",
            "phone": user.phone or ""
        }
    }), 200


@app.route("/")
def home():
    return render_template("home.html")


@app.route("/products")
def products():
    return render_template("products.html")


@app.route("/create-payment-order", methods=["POST"])
def create_payment_order():
    data = request.get_json(silent=True) or {}

    products = {
        "childrens-safety-tag": "Children's Safety Tag",
        "elderly-wristband": "Elderly Wristband",
        "luggage-bag-tag": "Luggage & Bag Tag",
        "qr-keychain": "QR Keychain",
    }

    product_code = data.get("product_code", "").strip()

    if product_code not in products:
        return jsonify({"error": "Invalid product selected."}), 400

    customer_name = data.get("customer_name", "").strip()
    customer_email = data.get("customer_email", "").strip().lower()
    customer_phone = data.get("customer_phone", "").strip()
    shipping_address = data.get("shipping_address", "").strip()
    shipping_city = data.get("shipping_city", "").strip()
    shipping_state = data.get("shipping_state", "").strip()
    shipping_pincode = data.get("shipping_pincode", "").strip()

    if not all([
        customer_name,
        customer_email,
        customer_phone,
        shipping_address,
        shipping_city,
        shipping_state,
        shipping_pincode
    ]):
        return jsonify({"error": "Please complete all customer details."}), 400

    if len(customer_name) < 3 or len(customer_name) > 100:
        return jsonify({"error": "Please enter a valid name."}), 400

    if "@" not in customer_email or len(customer_email) > 120:
        return jsonify({"error": "Please enter a valid email address."}), 400

    if len(customer_phone) != 10 or not customer_phone.isdigit():
        return jsonify({"error": "Enter a valid 10-digit mobile number."}), 400

    if not shipping_pincode.isdigit() or len(shipping_pincode) != 6:
        return jsonify({"error": "Enter a valid 6-digit PIN code."}), 400

    order_id = "TB" + secrets.token_hex(10).upper()

    new_order = TagOrder(
        order_id=order_id,
        product_code=product_code,
        product_name=products[product_code],
        amount=99.00,
        currency="INR",
        status="PENDING",
        customer_name=customer_name,
        customer_email=customer_email,
        customer_phone=customer_phone,
        shipping_address=shipping_address,
        shipping_city=shipping_city,
        shipping_state=shipping_state,
        shipping_pincode=shipping_pincode
    )

    try:
        db.session.add(new_order)
        db.session.commit()

        customer_details = CustomerDetails(
            customer_id="tb_" + secrets.token_hex(8),
            customer_name=customer_name,
            customer_email=customer_email,
            customer_phone=customer_phone
        )

        order_meta = OrderMeta(
            return_url=(
                request.host_url.rstrip("/")
                + "/payment-return?order_id={order_id}"
            )
        )

        cashfree_request = CreateOrderRequest(
            order_id=order_id,
            order_amount=99.00,
            order_currency="INR",
            customer_details=customer_details,
            order_meta=order_meta,
            order_note="Tagbandhu product purchase"
        )

        cashfree = get_cashfree_client()

        response = cashfree.PGCreateOrder(
            cashfree_request,
            None,
            None
        )

        payment_data = response.data

        new_order.payment_session_id = payment_data.payment_session_id
        new_order.cf_order_id = str(payment_data.cf_order_id)

        db.session.commit()

        return jsonify({
            "success": True,
            "order_id": order_id,
            "payment_session_id": payment_data.payment_session_id
        }), 200

    except Exception:
        db.session.rollback()

        failed_order = db.session.scalar(
            db.select(TagOrder).filter_by(order_id=order_id)
        )

        if failed_order and failed_order.status == "PENDING":
            failed_order.status = "FAILED"
            db.session.commit()

        app.logger.exception("Cashfree order creation failed.")

        return jsonify({
            "error": "Unable to create payment order. Please try again."
        }), 500

@app.route("/payment-return", methods=["GET"])
def payment_return():
    order_id = request.args.get("order_id", "").strip()

    if not order_id:
        flash("Payment order ID is missing.")
        return redirect(url_for("products"))

    order = db.session.scalar(
        db.select(TagOrder).filter_by(order_id=order_id)
    )

    if order is None:
        flash("Order not found.")
        return redirect(url_for("products"))

    try:
        cashfree = get_cashfree_client()

        response = cashfree.PGFetchOrder(
            order_id,
            None,
            None
        )

        cashfree_order = response.data

        if (
            cashfree_order.order_id != order.order_id
            or cashfree_order.order_currency != "INR"
            or round(float(cashfree_order.order_amount), 2)
            != round(float(order.amount), 2)
        ):
            app.logger.error(
                "Cashfree order verification mismatch: %s",
                order_id
            )
            flash("Unable to verify payment details.")
            return redirect(url_for("products"))

        if cashfree_order.order_status == "PAID":
            if order.status != "PAID":
                order.status = "PAID"
                order.paid_at = datetime.now(timezone.utc)
                db.session.commit()

            flash("Payment successful! Your order has been confirmed.")

        elif cashfree_order.order_status in (
            "EXPIRED",
            "TERMINATED",
            "CANCELLED"
        ):
            if order.status != "PAID":
                order.status = "FAILED"
                db.session.commit()

            flash("Payment was not completed. Please try again.")

        else:
            flash(
                "Payment is not confirmed yet. "
                "Please check your order status shortly."
            )

    except Exception:
        db.session.rollback()
        app.logger.exception("Cashfree payment verification failed.")
        flash("We could not verify your payment. Please try again later.")

    return redirect(url_for("products"))

@app.route("/scan/<tag_code>")
def scan_tag(tag_code):
    tag = db.session.scalar(db.select(Tag).filter_by(tag_code=tag_code))

    if not tag or not tag.is_active:
        return render_template("scan.html", tag=None), 404

    return render_template("scan.html", tag=tag)


@app.route("/tag-qr/<tag_code>")
def tag_qr(tag_code):
    tag = db.session.scalar(db.select(Tag).filter_by(tag_code=tag_code, is_active=True))

    if not tag:
        abort(404, description="Tag not found or inactive.")

    base_url = os.environ.get("BASE_URL", "http://10.135.243.87:5000").rstrip("/")

    scan_url = base_url + url_for("scan_tag", tag_code=tag_code)

    qr = qrcode.QRCode(box_size=10, border=4)
    qr.add_data(scan_url)
    qr.make(fit=True)

    qr_image = qr.make_image(fill_color="black", back_color="white")

    image_buffer = BytesIO()
    qr_image.save(image_buffer, format="PNG")
    image_buffer.seek(0)

    return send_file(image_buffer, mimetype="image/png")


# Local development only: temporary OTP storage
otp_store = {}


@app.route("/request-otp", methods=["POST"])
def request_otp():
    phone = request.form.get("phone", "").strip()

    if not re.fullmatch(r"[6-9][0-9]{9}", phone):
        return {
            "success": False,
            "message": "Enter a valid 10-digit mobile number.",
        }, 400

    otp = str(secrets.randbelow(900000) + 100000)

    # Give this browser session its own OTP storage key
    if "otp_session_id" not in session:
        session["otp_session_id"] = secrets.token_urlsafe(32)

    otp_key = session["otp_session_id"] + ":" + phone

    existing_record = otp_store.get(otp_key)

    if existing_record and time.time() < existing_record.get("resend_after", 0):
        return {
            "success": False,
            "message": "Please wait 60 seconds before requesting another OTP.",
        }, 429

    otp_store[otp_key] = {
        "otp": otp,
        "expires": time.time() + 300,
        "attempts": 0,
        "verified": False,
        "resend_after": time.time() + 60,
    }

    # Show OTP only while running in local debug mode.

    if app.debug:
        app.logger.warning("TEST OTP for %s: %s", phone, otp)

    return {
        "success": True,
        "message": "Test OTP generated. Check the VS Code terminal.",
    }


@app.route("/verify-otp", methods=["POST"])
def verify_otp():
    phone = request.form.get("phone", "").strip()
    entered_otp = request.form.get("otp", "").strip()

    session_id = session.get("otp_session_id")

    if not session_id:
        return {"success": False, "message": "Request a new OTP."}, 400

    otp_key = session_id + ":" + phone
    record = otp_store.get(otp_key)

    if not record or time.time() > record["expires"]:
        otp_store.pop(otp_key, None)
        return {"success": False, "message": "OTP expired. Request a new one."}, 400

    if record["attempts"] >= 5:
        otp_store.pop(otp_key, None)
        return {
            "success": False,
            "message": "Too many attempts. Request a new OTP.",
        }, 429

    record["attempts"] += 1

    if not secrets.compare_digest(record["otp"], entered_otp):
        return {"success": False, "message": "Incorrect OTP. Try again."}, 400

    record["verified"] = True

    return {"success": True, "message": "Phone number verified successfully."}


@app.route("/contact/<tag_code>", methods=["POST"])
def send_contact_message(tag_code):
    tag = db.session.scalar(db.select(Tag).filter_by(tag_code=tag_code, is_active=True))

    if not tag:
        return "Tag not found or inactive.", 404

    sender_name = request.form.get("sender_name", "").strip()
    sender_phone = request.form.get("sender_phone", "").strip()
    sender_email = request.form.get("sender_email", "").strip().lower()
    message = request.form.get("message", "").strip()

    # Check required fields
    if not sender_name or not sender_email or not sender_phone or not message:
        flash("Please fill in all contact form fields.")
        return redirect(url_for("scan_tag", tag_code=tag_code))

    # Validate Indian mobile number format
    if not re.fullmatch(r"[6-9][0-9]{9}", sender_phone):
        flash("Please enter a valid 10-digit Indian mobile number.")
        return redirect(url_for("scan_tag", tag_code=tag_code))

    # Check length limits
    if len(sender_name) > 100 or len(sender_email) > 120 or len(message) > 2000:
        flash("Please keep your details and message within the allowed limits.")
        return redirect(url_for("scan_tag", tag_code=tag_code))

    contact_message = ContactMessage(
        tag_id=tag.id,
        sender_name=sender_name,
        sender_phone=sender_phone,
        sender_email=sender_email,
        message=message,
        created_at=datetime.now(timezone.utc),
    )

    db.session.add(contact_message)
    db.session.commit()
    # Send an email notification to the tag owner

    # Send an email notification to the tag owner
    try:
        owner = tag.owner

        if owner and owner.email:
            email_body = f"""
Hello {owner.name},

Someone has sent you a message through your Tagbandhu tag.

Sender name: {contact_message.sender_name}
Sender email: {contact_message.sender_email}
Sender phone: {contact_message.sender_phone or 'Not provided'}

Message:
{contact_message.message}

Tag type: {tag.tag_type}
Tag ID: {tag.tag_code[:8]}

Please log in to your Tagbandhu dashboard to view your messages.

Regards,
Tagbandhu
"""

            email = Message(
                subject="New message received - Tagbandhu",
                recipients=[owner.email],
                body=email_body,
            )

            mail.send(email)

    except Exception:
        app.logger.exception("Message saved, but owner email notification failed.")

    flash("Your message has been sent to the item owner.")
    return redirect(url_for("scan_tag", tag_code=tag_code))


@app.route("/admin/inventory")
@admin_required
def admin_inventory():
    tags = Tag.query.order_by(Tag.id.asc()).all()

    total_tags = len(tags)
    users = db.session.scalars(db.select(User).order_by(User.id.asc())).all()

    total_users = len(users)
    available_tags = sum(
        1 for tag in tags if tag.owner_id is None and not tag.is_active
    )
    activated_tags = sum(
        1 for tag in tags if tag.owner_id is not None and tag.is_active
    )

    return render_template(
        "admin_inventory.html",
        tags=tags,
        total_tags=total_tags,
        available_tags=available_tags,
        activated_tags=activated_tags,
        users=users,
        total_users=total_users,
    )


@app.route("/admin/orders")
@admin_required
def admin_orders():
    orders = TagOrder.query.order_by(
        TagOrder.created_at.desc()
    ).all()

    return render_template(
        "admin_orders.html",
        orders=orders
    )


@app.route("/admin/check-tags")
@admin_required
def admin_check_tags():
    tags = Tag.query.order_by(Tag.id.asc()).all()

    return {
        "total_tags": len(tags),
        "active_tags": sum(1 for tag in tags if tag.is_active),
        "tags": [
            {
                "id": tag.id,
                "tag_code": tag.tag_code,
                "owner_id": tag.owner_id,
                "is_active": tag.is_active
            }
            for tag in tags
        ]
    }

@app.route("/admin/activity-history")
@admin_required
def admin_activity_history():
    activities = TagActivity.query.order_by(TagActivity.created_at.desc()).all()

    return render_template("admin_activity_history.html", activities=activities)


@app.route("/admin/users/<int:user_id>")
@admin_required
def admin_user_details(user_id):
    user = db.session.get(User, user_id)

    if user is None:
        abort(404)

    tags = Tag.query.filter_by(owner_id=user.id).order_by(Tag.id.asc()).all()

    # Fetch activity history for this user's tags
    tag_ids = [tag.id for tag in tags]

    activities = (
        TagActivity.query.filter(TagActivity.tag_id.in_(tag_ids))
        .order_by(TagActivity.created_at.desc())
        .all()
        if tag_ids
        else []
    )

    return render_template(
        "admin_user_details.html", user=user, tags=tags, activities=activities
    )


# -------------------- ADMIN: DEACTIVATE USER --------------------


@app.route("/admin/users/<int:user_id>/deactivate", methods=["POST"])
@admin_required
def admin_deactivate_user(user_id):
    user = db.session.get(User, user_id)

    if user is None:
        abort(404)

    if not user.is_active:
        flash("This user is already deactivated.")
        return redirect(url_for("admin_inventory"))

    user.is_active = False
    db.session.commit()

    flash("User account deactivated successfully.")
    return redirect(url_for("admin_inventory"))


# -------------------- ADMIN: DEACTIVATE TAG --------------------


@app.route("/admin/tag/<int:tag_id>/deactivate", methods=["POST"])
@admin_required
def admin_deactivate_tag(tag_id):
    tag = db.session.get(Tag, tag_id)

    if tag is None:
        abort(404)

    if tag.owner_id is None:
        flash("This tag has no owner. It is already unavailable for activation.")
        return redirect(url_for("admin_inventory"))

    if not tag.is_active:
        flash("This tag is already deactivated.")
        return redirect(url_for("admin_inventory"))

    tag.is_active = False

    db.session.add(
        TagActivity(
            tag_id=tag.id,
            action="deactivated",
            details="Tag deactivated by admin",
            created_at=datetime.now(ZoneInfo("Asia/Kolkata")),
        )
    )

    db.session.commit()

    flash("Tag deactivated successfully.")
    return redirect(url_for("admin_inventory"))


@app.route("/admin/users/<int:user_id>/reactivate", methods=["POST"])
@admin_required
def admin_reactivate_user(user_id):
    user = db.session.get(User, user_id)

    if user is None:
        abort(404)

    if user.is_active:
        flash("This user account is already active.")
        return redirect(url_for("admin_inventory"))

    user.is_active = True
    db.session.commit()

    flash("User account reactivated successfully.")
    return redirect(url_for("admin_inventory"))


@app.route("/admin/tag/<int:tag_id>/reactivate", methods=["POST"])
@admin_required
def admin_reactivate_tag(tag_id):
    tag = db.session.get(Tag, tag_id)

    if tag is None:
        abort(404)

    if tag.owner_id is None:
        flash("This tag has no owner and cannot be reactivated.")
        return redirect(url_for("admin_inventory"))

    if tag.is_active:
        flash("This tag is already active.")
        return redirect(url_for("admin_inventory"))

    tag.is_active = True

    db.session.add(
        TagActivity(
            tag_id=tag.id,
            action="reactivated",
            details="Tag reactivated by admin",
            created_at=datetime.now(ZoneInfo("Asia/Kolkata")),
        )
    )

    db.session.commit()

    flash(f"Tag #{tag.id} has been reactivated.")
    return redirect(url_for("admin_inventory"))


@app.route("/admin/generate-tags", methods=["POST"])
@admin_required
def generate_inventory_tags():

    tag_type = request.form.get("tag_type", "").strip().lower()

    try:
        quantity = int(request.form.get("quantity", "0"))
    except (ValueError, TypeError):
        abort(400, description="Quantity must be a number.")

    allowed_types = {"elderly", "child", "luggage", "everyday"}

    if tag_type not in allowed_types:
        abort(400, description="Invalid tag type.")

    if not 1 <= quantity <= 100:
        abort(400, description="Generate between 1 and 100 tags per batch.")

    new_tags = []

    try:
        for _ in range(quantity):
            tag = Tag(
                tag_code=uuid.uuid4().hex,
                tag_type=tag_type,
                owner_id=None,
                is_active=False,
            )
            db.session.add(tag)
            new_tags.append(tag)

        db.session.commit()
    except Exception:
        db.session.rollback()
        app.logger.exception("Inventory tag generation failed.")
        abort(500, description="Unable to generate inventory tags.")

    flash(f"{len(new_tags)} inventory tags generated successfully.")
    return redirect(url_for("admin_inventory"))


@app.route("/admin/export-tags")
@admin_required
def export_inventory_tags():
    tags = (
        Tag.query.filter_by(owner_id=None, is_active=False).order_by(Tag.id.asc()).all()
    )

    text_output = io.StringIO()
    writer = csv.writer(text_output)

    writer.writerow(["Tag ID", "Tag Code", "Tag Type", "Status"])

    for tag in tags:
        writer.writerow(
            [tag.id, tag.tag_code, tag.tag_type, "Available for activation"]
        )

    csv_bytes = BytesIO(text_output.getvalue().encode("utf-8-sig"))
    csv_bytes.seek(0)

    return send_file(
        csv_bytes,
        mimetype="text/csv",
        as_attachment=True,
        download_name="tagbandhu_inventory.csv",
    )


@app.route("/admin/print-tags")
@admin_required
def print_inventory_tags():
    tags = (
        Tag.query.filter_by(owner_id=None, is_active=False).order_by(Tag.id.asc()).all()
    )

    if not tags:
        return "No available inventory tags found.", 404

    base_url = os.environ.get("BASE_URL", "http://10.135.243.87:5000").rstrip("/")
    output = BytesIO()
    pdf = canvas.Canvas(output, pagesize=A4)
    page_width, page_height = A4

    margin = 35
    cell_width = (page_width - 2 * margin) / 2
    cell_height = 190

    for index, tag in enumerate(tags):
        position = index % 4

        if index > 0 and position == 0:
            pdf.showPage()

        col = position % 2
        row = position // 2
        x = margin + col * cell_width
        y = page_height - margin - (row + 1) * cell_height

        qr = qrcode.QRCode(box_size=8, border=3)
        qr.add_data(f"{base_url}/scan/{tag.tag_code}")
        qr.make(fit=True)

        qr_image = qr.make_image(fill_color="black", back_color="white")
        qr_buffer = BytesIO()
        qr_image.save(qr_buffer, format="PNG")
        qr_buffer.seek(0)

        image_size = 105

        pdf.drawImage(
            ImageReader(qr_buffer),
            x + (cell_width - image_size) / 2,
            y + 55,
            width=image_size,
            height=image_size,
        )

        pdf.setFont("Helvetica-Bold", 10)
        pdf.drawCentredString(
            x + cell_width / 2, y + 40, f"Tag ID: {tag.id} | {tag.tag_type.title()}"
        )

        pdf.setFont("Helvetica", 7)
        pdf.drawCentredString(x + cell_width / 2, y + 27, f"Code: {tag.tag_code}")

        pdf.rect(x + 5, y + 10, cell_width - 10, cell_height - 20)

    pdf.save()
    output.seek(0)

    return send_file(
        output,
        mimetype="application/pdf",
        as_attachment=True,
        download_name="tagbandhu_qr_print_sheet.pdf",
    )



def get_email_typo_suggestion(email):
    """Suggest corrections for common email domain typos."""
    parts = email.strip().lower().rsplit("@", 1)

    if len(parts) != 2:
        return None

    domain_typos = {
        "gamil.com": "gmail.com",
        "gmial.com": "gmail.com",
        "gmal.com": "gmail.com",
        "gail.com": "gmail.com",
        "gmai.com": "gmail.com",
        "gmaill.com": "gmail.com",
        "gmail.con": "gmail.com",
        "gmail.co": "gmail.com",
        "gmail.cm": "gmail.com",
        "gmail.coom": "gmail.com",
        "gmaik.com": "gmail.com",
        "gmaol.com": "gmail.com",
        "gmsil.com": "gmail.com",
        "gamil.con": "gmail.com",
        "ggmail.com": "gmail.com",
        "gmailll.com": "gmail.com",
        "gmailll.con": "gmail.com",
        "gmil.com": "gmail.com",
        "g-mail.com": "gmail.com",
        "gmailcom": "gmail.com",
        "yaho.com": "yahoo.com",
        "yahooo.com": "yahoo.com",
        "yahoo.con": "yahoo.com",
        "yahoo.co": "yahoo.com",
        "yhaoo.com": "yahoo.com",
        "yhoo.com": "yahoo.com",
        "yaoo.com": "yahoo.com",
        "outlok.com": "outlook.com",
        "outloo.com": "outlook.com",
        "outlook.con": "outlook.com",
        "outlook.co": "outlook.com",
        "outllok.com": "outlook.com",
        "outook.com": "outlook.com",
        "hotnail.com": "hotmail.com",
        "hotmai.com": "hotmail.com",
        "hotmail.con": "hotmail.com",
        "hotmial.com": "hotmail.com",
        "hotmil.com": "hotmail.com",
        "gmaill.co": "gmail.com",
        "mail.com": "gmail.com",
        "icloud.con": "icloud.com",
        "iclould.com": "icloud.com",
        "protonmai.com": "protonmail.com",
    }

    local_part, domain = parts
    suggested_domain = domain_typos.get(domain)

    if suggested_domain:
        return f"{local_part}@{suggested_domain}"

    return None

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        phone = request.form.get("phone", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        consent = request.form.get("consent")

        # Validate name
        if not re.fullmatch(r"[A-Za-z]+(?:[ '-][A-Za-z]+)*", name):
            flash(
                "Please enter a valid name using letters only. "
                "Spaces, hyphens and apostrophes are allowed.",
                "error",
            )
            return render_template("register.html")

        # Validate email format
        if (
            not email
            or len(email) > 120
            or not re.fullmatch(
                r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@"
                r"[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?"
                r"(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?)+",
                email,
            )
        ):
            flash("Please enter a valid email address.", "error")
            return render_template("register.html")

        # Check common email domain typos
        suggested_email = get_email_typo_suggestion(email)
        if suggested_email:
            flash(
                f"Please check your email address. Did you mean {suggested_email}?",
                "error",
            )
            return render_template("register.html")

        # Required fields
        if not name or not phone or not email or not password:
            flash("Please fill in all required fields.", "error")
            return render_template("register.html")

        # Password validation
        if len(password) < 8 or len(password) > 128:
            flash(
                "Password must be between 8 and 128 characters long.",
                "error",
            )
            return render_template("register.html")

        if not re.search(r"[A-Z]", password):
            flash(
                "Password must contain at least one uppercase letter (A-Z).",
                "error",
            )
            return render_template("register.html")

        if not re.search(r"[a-z]", password):
            flash(
                "Password must contain at least one lowercase letter (a-z).",
                "error",
            )
            return render_template("register.html")

        if not re.search(r"[0-9]", password):
            flash(
                "Password must contain at least one number (0-9).",
                "error",
            )
            return render_template("register.html")

        if not re.search(r"[^A-Za-z0-9]", password):
            flash(
                "Password must contain at least one special character, such as @ or #.",
                "error",
            )
            return render_template("register.html")

        if not consent:
            flash(
                "Please agree to the terms and privacy policy.",
                "error",
            )
            return render_template("register.html")

        # Check existing account
        existing_user = db.session.scalar(
            db.select(User).filter_by(email=email)
        )

        if existing_user:
            if not existing_user.email_verified:
                flash(
                    "This email has a pending registration. "
                    "Please verify it or request a new code.",
                    "error",
                )
                return redirect(
                    url_for("verify_email", email=email)
                )

            flash(
                "An account with this email already exists.",
                "error",
            )
            return render_template("register.html")

        # Generate OTP
        otp = str(secrets.randbelow(900000) + 100000)
        now = datetime.now(timezone.utc).replace(tzinfo=None)

        user = User(
            name=name,
            phone=phone,
            email=email,
            password_hash=generate_password_hash(password),
            email_verified=False,
            email_otp_hash=generate_password_hash(otp),
            email_otp_expires_at=now + timedelta(minutes=5),
            email_otp_attempts=0,
            email_otp_last_sent_at=now,
        )

        try:
            api_key = os.environ.get("RESEND_API_KEY", "").strip()

            if not api_key:
                raise RuntimeError("RESEND_API_KEY is not configured.")

            response = requests.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "from": "Tagbandhu <onboarding@resend.dev>",
                    "to": ["saniya975857@gmail.com"],
                    "subject": "Verify your Tagbandhu email",
                    "text": (
                        f"Hi {name},\n\n"
                        f"Your Tagbandhu verification code is: {otp}\n\n"
                        "This code expires in 5 minutes. "
                        "Do not share it with anyone.\n\n"
                        "If you did not request this code, ignore this email."
                    ),
                },
                timeout=10,
            )
            if not response.ok:
              app.logger.error(
                "Resend API rejected email. Status: %s, Response: %s",
                response.status_code,
                response.text,
             )
            response.raise_for_status()

            # Save account only after the email API accepts the request
            db.session.add(user)
            db.session.commit()

        except Exception:
            db.session.rollback()
            app.logger.exception(
                "Registration or verification email sending failed."
            )
            flash(
                "We could not complete registration or send your "
                "verification email. Please try again.",
                "error",
            )
            return render_template("register.html")

        flash(
            "A verification code has been sent to your email.",
            "success",
        )
        return redirect(url_for("verify_email", email=email))

    return render_template("register.html")


@app.route("/verify-email", methods=["GET", "POST"])
def verify_email():
    email = request.args.get("email", "").strip().lower()

    if request.method == "POST":
        email = request.form.get("email", email).strip().lower()
        otp = request.form.get("otp", "").strip()

    user = db.session.scalar(
        db.select(User).filter_by(email=email)
    )

    if not user:
        flash("Account not found. Please register again.", "error")
        return redirect(url_for("register"))

    if user.email_verified:
        flash("Your email is already verified. Please log in.", "success")
        return redirect(url_for("login"))

    if request.method == "POST":
        now = datetime.now(timezone.utc).replace(tzinfo=None)

        if not re.fullmatch(r"[0-9]{6}", otp):
            flash("Please enter a valid 6-digit verification code.", "error")
            return render_template("verify_email.html", email=email)

        if user.email_otp_attempts >= 5:
            flash("Too many attempts. Please request a new verification code.", "error")
            return render_template("verify_email.html", email=email)

        if (
            not user.email_otp_expires_at
            or now > user.email_otp_expires_at
        ):
            flash("Your verification code has expired. Please request a new one.", "error")
            return render_template("verify_email.html", email=email)

        user.email_otp_attempts += 1

        if not check_password_hash(user.email_otp_hash or "", otp):
            db.session.commit()
            flash("Incorrect verification code. Please try again.", "error")
            return render_template("verify_email.html", email=email)

        user.email_verified = True
        user.email_otp_hash = None
        user.email_otp_expires_at = None
        user.email_otp_attempts = 0
        db.session.commit()

        flash("Email verified successfully! You can now log in.", "success")
        return redirect(url_for("login"))

    return render_template("verify_email.html", email=email)

@app.route("/resend-verification", methods=["POST"])
def resend_verification():
    email = request.form.get("email", "").strip().lower()

    user = db.session.scalar(
        db.select(User).filter_by(email=email)
    )

    if not user:
        flash("Account not found. Please register again.", "error")
        return redirect(url_for("register"))

    if user.email_verified:
        flash("Your email is already verified. Please log in.", "success")
        return redirect(url_for("login"))

    now = datetime.now(timezone.utc).replace(tzinfo=None)

    if user.email_otp_last_sent_at:
        elapsed = (now - user.email_otp_last_sent_at).total_seconds()

        if elapsed < 60:
            wait_seconds = max(1, int(60 - elapsed))
            flash(
                f"Please wait {wait_seconds} seconds before requesting another code.",
                "error",
            )
            return redirect(url_for("verify_email", email=email))

    otp = str(secrets.randbelow(900000) + 100000)

    msg = Message(
        subject="Your new Tagbandhu verification code",
        recipients=[email],
        body=(
            f"Hi {user.name},\n\n"
            f"Your new Tagbandhu verification code is: {otp}\n\n"
            "This code expires in 5 minutes. "
            "Do not share it with anyone.\n\n"
            "If you did not request this code, ignore this email."
        ),
    )

    try:
        mail.send(msg)
    except Exception:
        app.logger.exception("Failed to resend verification email.")
        flash("Could not send a new code. Please try again later.", "error")
        return redirect(url_for("verify_email", email=email))

    user.email_otp_hash = generate_password_hash(otp)
    user.email_otp_expires_at = now + timedelta(minutes=5)
    user.email_otp_attempts = 0
    user.email_otp_last_sent_at = now
    db.session.commit()

    flash("A new verification code has been sent to your email.", "success")
    return redirect(url_for("verify_email", email=email))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        user = db.session.scalar(db.select(User).filter_by(email=email))

        
        if user and check_password_hash(user.password_hash, password):

            # Require email verification before login
            if not user.email_verified:
                flash(
                    "Please verify your email before logging in.",
                    "error",
                )
                return redirect(url_for("verify_email", email=user.email))

            # Prevent deactivated users from logging in
            if not user.is_active:
                flash("Your account has been deactivated. Please contact support.")
                return redirect(url_for("login"))

            session.clear()
            session["user_id"] = user.id
            session["user_name"] = user.name
            session["user_email"] = user.email

            return redirect(url_for("dashboard"))

        flash("Invalid email or password.")
        return redirect(url_for("login"))

    return render_template("login.html")


@app.route("/dashboard")
@login_required
def dashboard():
    user_tags = db.session.scalars(
        db.select(Tag).filter_by(owner_id=session["user_id"]).order_by(Tag.id.desc())
    ).all()

    received_messages = db.session.scalars(
        db.select(ContactMessage)
        .join(Tag)
        .filter(Tag.owner_id == session["user_id"])
        .order_by(ContactMessage.id.desc())
    ).all()

    unread_count = sum(1 for msg in received_messages if not msg.is_read)

    total_tags = len(user_tags)
    active_tags = sum(1 for tag in user_tags if tag.is_active)

    return render_template(
        "dashboard.html",
        name=session.get("user_name"),
        tags=user_tags,
        received_messages=received_messages,
        unread_count=unread_count,
        total_tags=total_tags,
        active_tags=active_tags,
        timedelta=timedelta,
    )


@app.route("/activate-tag", methods=["POST"])
@login_required
def activate_tag():
    tag_code = request.form.get("tag_code", "").strip()

    if not tag_code:
        flash("Please enter your tag code.")
        return redirect(url_for("dashboard"))

    result = db.session.execute(
        db.update(Tag)
        .where(
            Tag.tag_code == tag_code, Tag.owner_id.is_(None), Tag.is_active.is_(False)
        )
        .values(
            owner_id=session["user_id"],
            is_active=True,
            activated_at=datetime.now(timezone.utc),
        )
    )

    if result.rowcount != 1:
        db.session.rollback()
        flash("Tag code is invalid or has already been activated.")
        return redirect(url_for("dashboard"))

    tag = db.session.scalar(db.select(Tag).filter_by(tag_code=tag_code))

    if tag is None:
        db.session.rollback()
        flash("Tag could not be found. Please try again.")
        return redirect(url_for("dashboard"))

    db.session.add(
        TagActivity(
            tag_id=tag.id,
            action="activated",
            details="Tag activated by customer",
            created_at=datetime.now(ZoneInfo("Asia/Kolkata")),
        )
    )

    db.session.commit()
    flash("Your tag has been activated successfully!")
    return redirect(url_for("dashboard"))


@app.route("/my-tag/<int:tag_id>/deactivate", methods=["POST"])
@login_required
def customer_deactivate_tag(tag_id):
    tag = db.session.scalar(
        db.select(Tag).where(Tag.id == tag_id, Tag.owner_id == session["user_id"])
    )

    if tag is None:
        abort(404)

    if not tag.is_active:
        flash("This tag is already deactivated.")
        return redirect(url_for("dashboard"))

    tag.is_active = False

    db.session.add(
        TagActivity(
            tag_id=tag.id,
            action="deactivated",
            details="Tag deactivated by customer",
            created_at=datetime.now(ZoneInfo("Asia/Kolkata")),
        )
    )

    db.session.commit()

    flash("Your tag has been deactivated successfully.")
    return redirect(url_for("dashboard"))


@app.route("/my-tag/<int:tag_id>/reactivate", methods=["POST"])
@login_required
def customer_reactivate_tag(tag_id):
    tag = db.session.scalar(
        db.select(Tag).where(Tag.id == tag_id, Tag.owner_id == session["user_id"])
    )

    if tag is None:
        abort(404)

    if tag.is_active:
        flash("This tag is already active.")
        return redirect(url_for("dashboard"))

    tag.is_active = True

    db.session.add(
        TagActivity(
            tag_id=tag.id,
            action="reactivated",
            details="Tag reactivated by customer",
            created_at=datetime.now(ZoneInfo("Asia/Kolkata")),
        )
    )

    db.session.commit()

    flash("Your tag has been reactivated successfully.")
    return redirect(url_for("dashboard"))


@app.route("/mark-message-read/<int:message_id>", methods=["POST"])
@login_required
def mark_message_read(message_id):
    contact_message = db.session.scalar(
        db.select(ContactMessage)
        .join(Tag)
        .filter(ContactMessage.id == message_id, Tag.owner_id == session["user_id"])
    )

    if not contact_message:
        flash("Message not found.")
        return redirect(url_for("dashboard"))

    if contact_message.is_read:
        flash("This message has already been marked as read.")
    else:
        contact_message.is_read = True
        db.session.commit()
        flash("Message marked as read.")

    return redirect(url_for("dashboard"))


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("You have been logged out.")
    return redirect(url_for("home"))


with app.app_context():
    db.create_all()

@app.route("/verify-email-preview")
def verify_email_preview():
    return render_template(
        "verify_email.html",
        email="preview@example.com",
        preview=True
    )

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=os.environ.get("FLASK_DEBUG", "true").lower() == "true",
    )




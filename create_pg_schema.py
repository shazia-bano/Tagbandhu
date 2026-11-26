
import ssl
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url

print("Enter the Render PostgreSQL database URL.")
print("The URL will not be displayed. Keep it private.")

raw_url = input("Database URL: ").strip()

if raw_url.startswith("postgres://"):
    raw_url = "postgresql://" + raw_url[len("postgres://"):]

url = make_url(raw_url)

if url.drivername == "postgresql":
    url = url.set(drivername="postgresql+pg8000")

query = dict(url.query)
query.pop("sslmode", None)
url = url.set(query=query)

engine = create_engine(
    url,
    connect_args={"ssl_context": ssl.create_default_context()},
    pool_pre_ping=True,
)

try:
    with engine.connect():
        print("\nPostgreSQL connection successful.")

    from app import db

    db.metadata.create_all(engine)

    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS alembic_version (
                version_num VARCHAR(32) NOT NULL PRIMARY KEY
            )
        """))

    inspector = inspect(engine)

    print("\nPostgreSQL tables created:")
    for table in sorted(inspector.get_table_names()):
        print("-", table)

    print("\nSchema setup complete. No local data has been copied.")

finally:
    engine.dispose()


import ssl
from sqlalchemy import create_engine, inspect
from sqlalchemy.engine import make_url

print("Enter the Render PostgreSQL database URL.")
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
    inspector = inspect(engine)
    tables = sorted(inspector.get_table_names())

    print("\nTables found in PostgreSQL:")
    for table in tables:
        print("-", table)

    required = {
        "user",
        "tag",
        "tag_activity",
        "contact_message",
        "alembic_version",
    }

    missing = required - set(tables)

    if missing:
        print("\nMissing tables:", sorted(missing))
    else:
        print("\nAll required tables exist.")

finally:
    engine.dispose()

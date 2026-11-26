
import sqlite3
from getpass import getpass
from urllib.parse import urlparse, unquote

import pg8000

LOCAL_DB = "instance/tagbandhu.db"

print("=== LOCAL DATABASE ===")

with sqlite3.connect(LOCAL_DB) as local:
    print("Total users:", local.execute(
        'SELECT COUNT(*) FROM "user"'
    ).fetchone()[0])

    print("Active tags:", local.execute(
        "SELECT COUNT(*) FROM tag WHERE is_active = 1"
    ).fetchone()[0])

print("\n=== POSTGRES CONNECTION CHECK ===")
url = input("Paste External Database URL: ")
conn = None

try:
    parsed = urlparse(url)

    if not parsed.hostname or not parsed.username or not parsed.password:
        raise ValueError("Database URL format is incomplete.")

    conn = pg8000.connect(
        host=parsed.hostname,
        port=parsed.port or 5432,
        database=parsed.path.lstrip("/"),
        user=unquote(parsed.username),
        password=unquote(parsed.password),
        ssl_context=True,
        timeout=15,
    )

    cur = conn.cursor()
    cur.execute("SELECT current_database()")
    print("Connection: SUCCESS")
    print("Database:", cur.fetchone()[0])

    cur.execute("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
          AND table_type = 'BASE TABLE'
        ORDER BY table_name
    """)

    tables = [row[0] for row in cur.fetchall()]
    print("Existing tables:", tables or "None")

    for table in ("user", "tag", "tag_activity", "contact_message"):
        if table in tables:
            # Table name is quoted safely.
            cur.execute('SELECT COUNT(*) FROM "' + table + '"')
            print(f"{table} rows:", cur.fetchone()[0])

except Exception as exc:
    print("Check failed:", type(exc).__name__, str(exc))

finally:
    if conn:
        conn.close()

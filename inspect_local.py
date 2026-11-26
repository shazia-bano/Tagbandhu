
import sqlite3

db_path = "instance/tagbandhu.db"

with sqlite3.connect(db_path) as conn:
    tables = conn.execute("""
        SELECT name, sql
        FROM sqlite_master
        WHERE type = 'table'
          AND name NOT LIKE 'sqlite_%'
        ORDER BY name
    """).fetchall()

    for name, schema in tables:
        print(f"\n--- {name} ---")
        print(schema)

    print("\n--- Current migration version ---")
    print(conn.execute(
        "SELECT version_num FROM alembic_version"
    ).fetchall())
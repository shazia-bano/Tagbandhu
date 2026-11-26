
import ssl
from sqlalchemy import (
    create_engine,
    MetaData,
    select,
    text,
    func,
)
from sqlalchemy.engine import make_url

SOURCE_URL = "sqlite:///instance/tagbandhu.db"

TABLE_ORDER = [
    "user",
    "tag",
    "tag_activity",
    "contact_message",
    "alembic_version",
]

ID_TABLES = [
    "user",
    "tag",
    "tag_activity",
    "contact_message",
]


def get_postgres_engine():
    print("Enter the Render PostgreSQL External Database URL.")
    raw_url = input("Database URL: ").strip()

    if raw_url.startswith("postgres://"):
        raw_url = "postgresql://" + raw_url[len("postgres://"):]

    url = make_url(raw_url)

    if url.drivername == "postgresql":
        url = url.set(drivername="postgresql+pg8000")

    query = dict(url.query)
    query.pop("sslmode", None)
    url = url.set(query=query)

    return create_engine(
        url,
        connect_args={"ssl_context": ssl.create_default_context()},
        pool_pre_ping=True,
    )


source_engine = create_engine(SOURCE_URL)
target_engine = None

try:
    target_engine = get_postgres_engine()

    source_metadata = MetaData()
    target_metadata = MetaData()

    source_metadata.reflect(bind=source_engine)
    target_metadata.reflect(bind=target_engine)

    source_tables = set(source_metadata.tables.keys())
    target_tables = set(target_metadata.tables.keys())

    missing_source = set(TABLE_ORDER) - source_tables
    missing_target = set(TABLE_ORDER) - target_tables

    if missing_source or missing_target:
        raise RuntimeError(
            f"Missing source tables: {sorted(missing_source)}; "
            f"missing target tables: {sorted(missing_target)}"
        )

    source_counts = {}
    target_counts = {}

    with source_engine.connect() as source_conn:
        for name in TABLE_ORDER:
            table = source_metadata.tables[name]
            source_counts[name] = source_conn.execute(
                select(func.count()).select_from(table)
            ).scalar_one()

    with target_engine.connect() as target_conn:
        for name in TABLE_ORDER:
            table = target_metadata.tables[name]
            target_counts[name] = target_conn.execute(
                select(func.count()).select_from(table)
            ).scalar_one()

    print("\nSource record counts:")
    for name in TABLE_ORDER:
        print(f"{name}: {source_counts[name]}")

    print("\nDestination record counts:")
    for name in TABLE_ORDER:
        print(f"{name}: {target_counts[name]}")

    if any(count != 0 for count in target_counts.values()):
        raise RuntimeError(
            "The destination is not empty. No records were copied."
        )

    for name in TABLE_ORDER:
        source_columns = set(
            source_metadata.tables[name].columns.keys()
        )
        target_columns = set(
            target_metadata.tables[name].columns.keys()
        )

        if source_columns != target_columns:
            raise RuntimeError(
                f"Column mismatch in table: {name}. "
                "No records were copied."
            )

    confirmation = input(
        "\nType COPY to transfer all local records: "
    ).strip()

    if confirmation != "COPY":
        print("Transfer cancelled. No records were copied.")
    else:
        with target_engine.begin() as target_conn:
            with source_engine.connect() as source_conn:
                for name in TABLE_ORDER:
                    source_table = source_metadata.tables[name]
                    target_table = target_metadata.tables[name]

                    rows = source_conn.execute(
                        select(source_table)
                    ).mappings().all()

                    if rows:
                        target_conn.execute(
                            target_table.insert(),
                            [dict(row) for row in rows],
                        )

            for name in ID_TABLES:
                target_conn.execute(
                    text(
                        f"""
                        SELECT setval(
                            pg_get_serial_sequence(:table_name, 'id'),
                            COALESCE(MAX(id), 1),
                            COUNT(*) > 0
                        )
                        FROM "{name}"
                        """
                    ),
                    {"table_name": name},
                )

        print("\nTransfer completed successfully.")

        with target_engine.connect() as target_conn:
            print("\nFinal destination record counts:")
            for name in TABLE_ORDER:
                table = target_metadata.tables[name]
                count = target_conn.execute(
                    select(func.count()).select_from(table)
                ).scalar_one()
                print(f"{name}: {count}")

except Exception as error:
    print("\nTransfer failed:", str(error))
    print("Check the error before attempting another transfer.")

finally:
    source_engine.dispose()
    if target_engine is not None:
        target_engine.dispose()

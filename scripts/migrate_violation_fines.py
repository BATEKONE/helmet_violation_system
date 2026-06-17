import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.settings import get_settings
from sqlalchemy import create_engine, text


def column_exists(connection, table_name: str, column_name: str, database_url: str) -> bool:
    if database_url.startswith("sqlite"):
        result = connection.execute(text(f"PRAGMA table_info({table_name})")).mappings().all()
        return any(row["name"] == column_name for row in result)

    if database_url.startswith("postgresql"):
        result = connection.execute(
            text(
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_name = :table AND column_name = :column"
            ),
            {"table": table_name, "column": column_name},
        ).fetchone()
        return result is not None

    raise RuntimeError(f"Unsupported database URL: {database_url}")


def add_column_if_missing(connection, database_url: str):
    if not column_exists(connection, "violation_events", "is_fined", database_url):
        if database_url.startswith("sqlite"):
            connection.execute(
                text("ALTER TABLE violation_events ADD COLUMN is_fined BOOLEAN DEFAULT FALSE")
            )
        else:
            connection.execute(
                text(
                    "ALTER TABLE violation_events "
                    "ADD COLUMN IF NOT EXISTS is_fined BOOLEAN DEFAULT FALSE"
                )
            )
        print("Добавлено поле is_fined")
    else:
        print("Поле is_fined уже существует")

    if not column_exists(connection, "violation_events", "fine_amount", database_url):
        if database_url.startswith("sqlite"):
            connection.execute(
                text("ALTER TABLE violation_events ADD COLUMN fine_amount INTEGER")
            )
        else:
            connection.execute(
                text(
                    "ALTER TABLE violation_events "
                    "ADD COLUMN IF NOT EXISTS fine_amount INTEGER"
                )
            )
        print("Добавлено поле fine_amount")
    else:
        print("Поле fine_amount уже существует")


def main():
    settings = get_settings()
    database_url = settings.database_url
    engine = create_engine(database_url, pool_pre_ping=True)

    with engine.connect() as connection:
        connection.execute(text("BEGIN"))
        add_column_if_missing(connection, database_url)
        connection.execute(text("COMMIT"))

    print("Миграция завершена.")


if __name__ == "__main__":
    main()

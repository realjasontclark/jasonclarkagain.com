"""Database session management using SQLModel."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from sqlmodel import Session, SQLModel, create_engine

from .config import DB_PATH

ENGINE = create_engine(f"sqlite:///{DB_PATH}", echo=False, connect_args={"check_same_thread": False})


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    SQLModel.metadata.create_all(ENGINE)
    _ensure_script_columns()


@contextmanager
def session_scope() -> Iterator[Session]:
    session = Session(ENGINE)
    try:
        yield session
        session.commit()
    except Exception:  # pragma: no cover - ensures rollback on error in production
        session.rollback()
        raise
    finally:
        session.close()


def _ensure_script_columns() -> None:
    """Add new columns to ScriptRecord table if they do not exist (rudimentary migration)."""

    with ENGINE.begin() as connection:
        rows = connection.exec_driver_sql("PRAGMA table_info(scriptrecord)").fetchall()
        existing_columns = {row[1] for row in rows}
        migrations = {
            "token_count": "INTEGER",
            "duration_seconds": "INTEGER",
            "summary": "TEXT",
        }
        for column, column_type in migrations.items():
            if column not in existing_columns:
                connection.exec_driver_sql(
                    f"ALTER TABLE scriptrecord ADD COLUMN {column} {column_type}"
                )


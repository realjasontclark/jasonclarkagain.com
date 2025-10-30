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


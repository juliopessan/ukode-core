"""Engine e sessão SQLAlchemy. Funciona com SQLite (testes) e Postgres (produção)."""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from ukode_core.config import settings


class Base(DeclarativeBase):
    pass


def make_engine(database_url: str | None = None):
    url = database_url or settings.database_url
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(url, connect_args=connect_args, future=True)


engine = make_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def init_db(bind_engine=None) -> None:
    """Cria as tabelas. Em produção, prefira migrações (Alembic) a isto."""
    from ukode_core import models  # noqa: F401  (garante que os modelos foram importados)

    Base.metadata.create_all(bind=bind_engine or engine)


@contextmanager
def session_scope(bind_engine=None) -> Generator[Session, None, None]:
    factory = sessionmaker(bind=bind_engine, future=True) if bind_engine else SessionLocal
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

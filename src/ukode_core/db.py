"""Engine e sessão SQLAlchemy. Funciona com SQLite (testes) e Postgres (produção)."""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool

from ukode_core.config import settings


class Base(DeclarativeBase):
    pass


def make_engine(database_url: str | None = None):
    url = database_url or settings.database_url
    if url.startswith("sqlite"):
        # SQLite em memória isola uma conexão por thread por padrão — cada
        # thread nova enxerga um banco vazio. Isso quebra silenciosamente
        # sempre que algo síncrono roda fora da thread principal (rotas
        # FastAPI síncronas rodam numa threadpool). StaticPool força uma
        # única conexão compartilhada, então "sqlite:///:memory:" continua
        # sendo um único banco de verdade em qualquer thread.
        kwargs = {"connect_args": {"check_same_thread": False}}
        if ":memory:" in url:
            kwargs["poolclass"] = StaticPool
        return create_engine(url, future=True, **kwargs)
    return create_engine(url, future=True)


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

"""Independent SQLAlchemy engine and session factory for spire.db."""
from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from spire_server.config import get_settings


def _build_engine(database_url: str) -> Engine:
    connect_args: dict = {}
    kwargs: dict = {'future': True}
    if database_url.startswith('sqlite'):
        connect_args['check_same_thread'] = False
        if database_url in ('sqlite://', 'sqlite:///:memory:'):
            kwargs['poolclass'] = StaticPool
        else:
            raw_path = database_url.removeprefix('sqlite:///')
            if raw_path:
                Path(raw_path).parent.mkdir(parents=True, exist_ok=True)
    eng = create_engine(database_url, connect_args=connect_args, **kwargs)
    if database_url.startswith('sqlite'):
        @event.listens_for(eng, 'connect')
        def _set_sqlite_pragma(dbapi_connection, _connection_record):
            cursor = dbapi_connection.cursor()
            try:
                cursor.execute('PRAGMA journal_mode=WAL')
                cursor.execute('PRAGMA synchronous=NORMAL')
                cursor.execute('PRAGMA busy_timeout=5000')
            finally:
                cursor.close()
    return eng


engine = _build_engine(get_settings().spire_database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

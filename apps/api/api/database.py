from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime

from fastapi import Request
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    pass


def utcnow() -> datetime:
    return datetime.now(UTC)


def _connect_args(database_url: str) -> dict[str, object]:
    if database_url.startswith("sqlite"):
        return {"check_same_thread": False}
    return {}


def create_engine_from_url(database_url: str) -> Engine:
    return create_engine(
        database_url,
        connect_args=_connect_args(database_url),
        pool_pre_ping=not database_url.startswith("sqlite"),
    )


def create_session_factory(database_url: str) -> sessionmaker[Session]:
    engine = create_engine_from_url(database_url)
    return sessionmaker(bind=engine, class_=Session, expire_on_commit=False)


def get_db_session(request: Request) -> Iterator[Session]:
    session_factory = request.app.state.session_factory
    with session_factory() as session:
        yield session

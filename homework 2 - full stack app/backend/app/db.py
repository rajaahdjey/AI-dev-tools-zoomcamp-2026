"""Engine + declarative base. URL-agnostic: SQLite today, Postgres later
via DATABASE_URL (e.g. ``postgresql+psycopg://user:pw@host/db``) with no
code changes — only generic column types are used. One engine per store
instance so tests get isolated databases."""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    pass


def create_engine_for_url(url: str) -> Engine:
    kwargs: dict = {}
    if url.startswith("sqlite"):
        # TestClient/uvicorn serve requests from worker threads.
        kwargs["connect_args"] = {"check_same_thread": False}
    return create_engine(url, **kwargs)


def session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False)

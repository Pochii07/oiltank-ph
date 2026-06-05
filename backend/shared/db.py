"""
Database connection helper.

- In Cloud Run (env DB_INSTANCE_CONNECTION_NAME set): uses Cloud SQL Python Connector with
  IAM-attached service account auth via the pg8000 driver.
- Locally (env DATABASE_URL set): falls back to a plain psycopg/pg8000 URL.
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker


def _build_cloud_sql_engine() -> Engine:
    from google.cloud.sql.connector import Connector, IPTypes  # type: ignore[import-not-found]

    instance = os.environ["DB_INSTANCE_CONNECTION_NAME"]
    user = os.environ["DB_USER"]
    password = os.environ["DB_PASSWORD"]
    name = os.environ["DB_NAME"]
    ip_type = IPTypes.PUBLIC

    connector = Connector(ip_type=ip_type)

    def getconn():
        return connector.connect(
            instance,
            "pg8000",
            user=user,
            password=password,
            db=name,
        )

    return create_engine(
        "postgresql+pg8000://",
        creator=getconn,
        pool_size=5,
        max_overflow=2,
        pool_pre_ping=True,
    )


def _build_local_engine() -> Engine:
    url = os.environ["DATABASE_URL"]
    return create_engine(url, pool_pre_ping=True)


def build_engine() -> Engine:
    if os.getenv("DB_INSTANCE_CONNECTION_NAME"):
        return _build_cloud_sql_engine()
    if os.getenv("DATABASE_URL"):
        return _build_local_engine()
    raise RuntimeError(
        "Set DB_INSTANCE_CONNECTION_NAME (Cloud SQL) or DATABASE_URL (local) to connect to Postgres."
    )


_engine: Engine | None = None
_SessionLocal: sessionmaker[Session] | None = None


def get_engine() -> Engine:
    global _engine, _SessionLocal
    if _engine is None:
        _engine = build_engine()
        _SessionLocal = sessionmaker(bind=_engine, expire_on_commit=False)
    return _engine


@contextmanager
def session_scope() -> Iterator[Session]:
    get_engine()
    assert _SessionLocal is not None
    sess = _SessionLocal()
    try:
        yield sess
        sess.commit()
    except Exception:
        sess.rollback()
        raise
    finally:
        sess.close()


def apply_schema() -> None:
    """Execute schema.sql against the connected database. Idempotent."""
    schema_path = Path(__file__).parent / "schema.sql"
    ddl = schema_path.read_text(encoding="utf-8")
    engine = get_engine()
    with engine.begin() as conn:
        for stmt in [s.strip() for s in ddl.split(";") if s.strip()]:
            conn.execute(text(stmt))

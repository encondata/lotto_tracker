import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.config import get_settings
from app.models.base import Base
import app.models  # noqa: F401  register all models

# Derive a sibling test database URL from the configured one.
_base_url = get_settings().database_url
TEST_URL = _base_url.rsplit("/", 1)[0] + "/lotto_test"


@pytest.fixture(scope="session")
def engine():
    admin = create_engine(
        _base_url.rsplit("/", 1)[0] + "/postgres", isolation_level="AUTOCOMMIT"
    )
    with admin.connect() as conn:
        conn.execute(text("DROP DATABASE IF EXISTS lotto_test"))
        conn.execute(text("CREATE DATABASE lotto_test"))
    admin.dispose()
    eng = create_engine(TEST_URL)
    with eng.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS pgcrypto"))
        conn.commit()
    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture
def db_session(engine):
    conn = engine.connect()
    txn = conn.begin()
    Session = sessionmaker(bind=conn, expire_on_commit=False)
    session = Session()
    try:
        yield session
    finally:
        session.close()
        txn.rollback()
        conn.close()

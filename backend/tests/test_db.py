from sqlalchemy import text


def test_db_session_connects(db_session):
    assert db_session.execute(text("SELECT 1")).scalar() == 1

from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db import get_db
from app.deps import get_current_user
from app.main import app
from app.models.draw import TicketResult
from app.models.reference import Game
from app.models.ticket import PlayLine, Ticket
from app.models.user import User
from app.security import hash_password
from app.seed import seed_reference_data
from app.services.draws import record_draw


@pytest.fixture
def seeded(db_session):
    seed_reference_data(db_session)
    return db_session


def _user(db, email, role="user"):
    u = User(
        email=email,
        password_hash=hash_password("password123"),
        display_name=email.split("@")[0],
        role=role,
    )
    db.add(u)
    db.flush()
    return u


@pytest.fixture
def alice(seeded):
    return _user(seeded, "alice@example.com", role="user")


@pytest.fixture
def admin(seeded):
    return _user(seeded, "admin@example.com", role="admin")


def _client(db_session, user):
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_current_user] = lambda: user
    return TestClient(app)


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.clear()


def _game(db, key):
    return db.scalar(select(Game).where(Game.key == key))


def test_get_draws_returns_recorded(seeded, alice):
    record_draw(seeded, "powerball", date(2026, 6, 30),
                [1, 2, 3, 4, 5], winning_special=10, multiplier=2)
    seeded.flush()
    client = _client(seeded, alice)
    resp = client.get("/api/results/draws", params={"game_key": "powerball"})
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    d = body[0]
    assert d["game_key"] == "powerball"
    assert d["winning_main"] == [1, 2, 3, 4, 5]
    assert d["winning_special"] == 10
    assert d["multiplier"] == 2
    assert d["draw_date"] == "2026-06-30"


def test_admin_post_draw_triggers_matching(seeded, admin):
    # ticket exists that will match the posted draw
    pb = _game(seeded, "powerball")
    t = Ticket(
        user_id=admin.id,
        game_id=pb.id,
        purchase_date=date(2026, 6, 1),
        num_draws=1,
        add_ons={},
        play_lines=[PlayLine(
            line_index=0, main_numbers=[1, 2, 3, 4, 5], special_number=10,
        )],
    )
    seeded.add(t)
    seeded.flush()

    client = _client(seeded, admin)
    resp = client.post("/api/results/draws", json={
        "game_key": "powerball",
        "draw_date": "2026-06-30",
        "winning_main": [1, 2, 3, 4, 5],
        "winning_special": 10,
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["results_created"] >= 1
    assert body["draw"]["winning_main"] == [1, 2, 3, 4, 5]

    results = seeded.scalars(select(TicketResult)).all()
    assert any(r.status == "won" for r in results)


def test_non_admin_forbidden_on_ingest_match_draws(seeded, alice):
    client = _client(seeded, alice)
    assert client.post("/api/results/ingest").status_code == 403
    assert client.post("/api/results/match").status_code == 403
    assert client.post("/api/results/draws", json={
        "game_key": "powerball",
        "draw_date": "2026-06-30",
        "winning_main": [1, 2, 3, 4, 5],
        "winning_special": 10,
    }).status_code == 403


def test_admin_match_endpoint(seeded, admin):
    record_draw(seeded, "powerball", date(2026, 6, 30),
                [1, 2, 3, 4, 5], winning_special=10)
    pb = _game(seeded, "powerball")
    t = Ticket(
        user_id=admin.id, game_id=pb.id, purchase_date=date(2026, 6, 1),
        num_draws=1, add_ons={},
        play_lines=[PlayLine(
            line_index=0, main_numbers=[1, 2, 3, 4, 5], special_number=10)],
    )
    seeded.add(t)
    seeded.flush()
    client = _client(seeded, admin)
    resp = client.post("/api/results/match")
    assert resp.status_code == 200
    assert resp.json()["results_created"] >= 1

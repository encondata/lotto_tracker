from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db import get_db
from app.deps import get_current_user
from app.main import app
from app.models.draw import Draw, TicketResult
from app.models.reference import Game
from app.models.ticket import PlayLine, Ticket
from app.models.user import User
from app.security import hash_password
from app.seed import seed_reference_data


@pytest.fixture
def seeded(db_session):
    seed_reference_data(db_session)
    return db_session


def _user(db, email):
    u = User(
        email=email,
        password_hash=hash_password("password123"),
        display_name=email.split("@")[0],
        role="user",
    )
    db.add(u)
    db.flush()
    return u


def _game(db, key):
    return db.scalar(select(Game).where(Game.key == key))


def _client(db_session, user):
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_current_user] = lambda: user
    return TestClient(app)


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def data(seeded):
    db = seeded
    alice = _user(db, "alice@example.com")
    bob = _user(db, "bob@example.com")
    pb = _game(db, "powerball")
    draw = Draw(game_id=pb.id, draw_date=date(2026, 1, 9),
                winning_main=[1, 2, 3, 4, 5])
    db.add(draw)
    db.flush()

    t = Ticket(user_id=alice.id, game_id=pb.id, purchase_date=date(2026, 1, 10),
               total_cost_cents=500, add_ons={},
               play_lines=[PlayLine(line_index=0, main_numbers=[1, 2, 3, 4, 5],
                                    is_quick_pick=True)])
    db.add(t)
    db.flush()
    db.add(TicketResult(play_line_id=t.play_lines[0].id, draw_id=draw.id,
                        amount_won_cents=700, status="won"))
    # bob has his own bigger ticket that must never appear for alice
    tb = Ticket(user_id=bob.id, game_id=pb.id, purchase_date=date(2026, 1, 11),
                total_cost_cents=9999, add_ons={},
                play_lines=[PlayLine(line_index=0, main_numbers=[9, 9, 9, 9, 9])])
    db.add(tb)
    db.flush()
    return db, alice, bob


def test_summary_endpoint(data):
    db, alice, _ = data
    client = _client(db, alice)
    resp = client.get("/api/analytics/summary")
    assert resp.status_code == 200
    body = resp.json()
    assert set(body) == {
        "total_spent_cents", "total_won_cents", "net_cents",
        "tickets_purchased", "lines_played", "win_rate",
        "biggest_win_cents", "roi_pct", "pending_cents",
    }
    assert body["total_spent_cents"] == 500
    assert body["total_won_cents"] == 700
    assert body["net_cents"] == 200


def test_by_game_endpoint(data):
    db, alice, _ = data
    client = _client(db, alice)
    resp = client.get("/api/analytics/by-game")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["game_key"] == "powerball"
    assert set(body[0]) == {
        "game_key", "display_name", "spent_cents",
        "won_cents", "net_cents", "tickets",
    }


def test_over_time_endpoint(data):
    db, alice, _ = data
    client = _client(db, alice)
    resp = client.get("/api/analytics/over-time", params={"bucket": "month"})
    assert resp.status_code == 200
    body = resp.json()
    assert body[0]["period"] == "2026-01"
    assert set(body[0]) == {"period", "spent_cents", "won_cents", "net_cents"}


def test_pick_breakdown_endpoint(data):
    db, alice, _ = data
    client = _client(db, alice)
    resp = client.get("/api/analytics/pick-breakdown")
    assert resp.status_code == 200
    body = resp.json()
    assert set(body) == {"quick_pick", "self_pick"}
    assert body["quick_pick"]["lines"] == 1
    assert body["quick_pick"]["wins"] == 1


def test_user_scoped(data):
    db, alice, bob = data
    client = _client(db, bob)
    resp = client.get("/api/analytics/summary")
    assert resp.status_code == 200
    # bob only sees his own data
    assert resp.json()["total_spent_cents"] == 9999
    assert resp.json()["total_won_cents"] == 0


def test_requires_auth(data):
    db, alice, _ = data
    # no get_current_user override -> real dependency -> 401
    app.dependency_overrides[get_db] = lambda: db
    client = TestClient(app)
    assert client.get("/api/analytics/summary").status_code == 401

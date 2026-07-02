import pytest
from fastapi.testclient import TestClient

from app.db import get_db
from app.deps import get_current_user
from app.main import app
from app.models.user import User
from app.seed import seed_reference_data
from app.security import hash_password


@pytest.fixture
def seeded(db_session):
    seed_reference_data(db_session)
    return db_session


def _user(db_session, email):
    u = User(
        email=email,
        password_hash=hash_password("password123"),
        display_name=email.split("@")[0],
        role="user",
    )
    db_session.add(u)
    db_session.flush()
    return u


@pytest.fixture
def alice(seeded):
    return _user(seeded, "alice@example.com")


@pytest.fixture
def bob(seeded):
    return _user(seeded, "bob@example.com")


def _client(db_session, user):
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_current_user] = lambda: user
    return TestClient(app)


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.clear()


def _pb_body(num_draws=1, power_play=False):
    return {
        "game_key": "powerball",
        "purchase_date": "2026-01-01",
        "num_draws": num_draws,
        "add_ons": {"power_play": True} if power_play else {},
        "lines": [
            {"main_numbers": [1, 2, 3, 4, 5], "special_number": 10},
            {"main_numbers": [6, 7, 8, 9, 11], "special_number": 12},
        ],
    }


def test_create_returns_201(seeded, alice):
    client = _client(seeded, alice)
    resp = client.post("/api/tickets/", json=_pb_body(num_draws=2, power_play=True))
    assert resp.status_code == 201
    body = resp.json()
    assert body["game_key"] == "powerball"
    assert body["total_cost_cents"] == (200 + 100) * 2 * 2  # 1200
    assert len(body["lines"]) == 2
    assert body["lines"][0]["line_index"] == 0
    assert body["lines"][0]["main_numbers"] == [1, 2, 3, 4, 5]
    assert body["results"] == []
    assert body["total_won_cents"] == 0
    assert "id" in body


def test_create_invalid_line_400(seeded, alice):
    client = _client(seeded, alice)
    body = _pb_body()
    body["lines"] = [{"main_numbers": [1, 2, 3], "special_number": 10}]
    resp = client.post("/api/tickets/", json=body)
    assert resp.status_code == 400


def test_create_unknown_game_404(seeded, alice):
    client = _client(seeded, alice)
    body = _pb_body()
    body["game_key"] = "no_such_game"
    resp = client.post("/api/tickets/", json=body)
    assert resp.status_code == 404


def test_create_missing_lines_422(seeded, alice):
    client = _client(seeded, alice)
    body = _pb_body()
    body["lines"] = []
    resp = client.post("/api/tickets/", json=body)
    assert resp.status_code == 422


def test_list_only_current_user(seeded, alice, bob):
    a_client = _client(seeded, alice)
    a_client.post("/api/tickets/", json=_pb_body())
    a_client.post("/api/tickets/", json=_pb_body())
    app.dependency_overrides.clear()

    b_client = _client(seeded, bob)
    b_client.post("/api/tickets/", json=_pb_body())
    listing = b_client.get("/api/tickets/")
    assert listing.status_code == 200
    assert len(listing.json()) == 1

    app.dependency_overrides.clear()
    a_client2 = _client(seeded, alice)
    a_listing = a_client2.get("/api/tickets/")
    assert len(a_listing.json()) == 2


def test_detail_own_ticket(seeded, alice):
    client = _client(seeded, alice)
    created = client.post("/api/tickets/", json=_pb_body()).json()
    resp = client.get(f"/api/tickets/{created['id']}")
    assert resp.status_code == 200
    assert resp.json()["id"] == created["id"]


def test_detail_other_user_404(seeded, alice, bob):
    a_client = _client(seeded, alice)
    created = a_client.post("/api/tickets/", json=_pb_body()).json()
    app.dependency_overrides.clear()

    b_client = _client(seeded, bob)
    resp = b_client.get(f"/api/tickets/{created['id']}")
    assert resp.status_code == 404


def test_delete_returns_204(seeded, alice):
    client = _client(seeded, alice)
    created = client.post("/api/tickets/", json=_pb_body()).json()
    resp = client.delete(f"/api/tickets/{created['id']}")
    assert resp.status_code == 204
    # gone now
    assert client.get(f"/api/tickets/{created['id']}").status_code == 404


def test_list_game_filter(seeded, alice):
    client = _client(seeded, alice)
    client.post("/api/tickets/", json=_pb_body())
    d4 = {
        "game_key": "daily4",
        "purchase_date": "2026-01-01",
        "lines": [{"main_numbers": [1, 2, 3, 4], "play_type": "straight"}],
    }
    client.post("/api/tickets/", json=d4)

    pb_only = client.get("/api/tickets/", params={"game_key": "powerball"})
    assert len(pb_only.json()) == 1
    assert pb_only.json()[0]["game_key"] == "powerball"

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.db import get_db
from app.main import app
from app.models.user import Invite, User
from app.security import hash_password


@pytest.fixture
def client(db_session):
    app.dependency_overrides[get_db] = lambda: db_session
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def admin_user(db_session):
    user = User(
        email="admin@example.com",
        password_hash=hash_password("admin-pass"),
        display_name="Admin",
        role="admin",
    )
    db_session.add(user)
    db_session.flush()
    return user


@pytest.fixture
def regular_user(db_session):
    user = User(
        email="user@example.com",
        password_hash=hash_password("user-pass"),
        display_name="User",
        role="user",
    )
    db_session.add(user)
    db_session.flush()
    return user


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_register_without_valid_invite_rejected(client):
    resp = client.post(
        "/api/auth/register",
        json={
            "email": "new@example.com",
            "password": "password123",
            "display_name": "New",
            "invite_token": "does-not-exist",
        },
    )
    assert resp.status_code in (400, 403)


def test_admin_creates_invite_then_user_registers(client, admin_user):
    login = client.post(
        "/api/auth/login",
        json={"email": "admin@example.com", "password": "admin-pass"},
    )
    assert login.status_code == 200
    admin_token = login.json()["access_token"]

    inv = client.post(
        "/api/invites/",
        json={"email": "invitee@example.com"},
        headers=_auth(admin_token),
    )
    assert inv.status_code == 200
    invite_token = inv.json()["token"]
    assert inv.json()["email"] == "invitee@example.com"

    reg = client.post(
        "/api/auth/register",
        json={
            "email": "invitee@example.com",
            "password": "password123",
            "display_name": "Invitee",
            "invite_token": invite_token,
        },
    )
    assert reg.status_code == 200
    assert reg.json()["access_token"]
    assert reg.json()["token_type"] == "bearer"


def test_invite_cannot_be_reused(client, admin_user):
    login = client.post(
        "/api/auth/login",
        json={"email": "admin@example.com", "password": "admin-pass"},
    )
    admin_token = login.json()["access_token"]
    inv = client.post(
        "/api/invites/",
        json={"email": "once@example.com"},
        headers=_auth(admin_token),
    )
    invite_token = inv.json()["token"]

    first = client.post(
        "/api/auth/register",
        json={
            "email": "once@example.com",
            "password": "password123",
            "display_name": "Once",
            "invite_token": invite_token,
        },
    )
    assert first.status_code == 200

    second = client.post(
        "/api/auth/register",
        json={
            "email": "once@example.com",
            "password": "password123",
            "display_name": "Once Again",
            "invite_token": invite_token,
        },
    )
    assert second.status_code in (400, 403)


def test_expired_invite_rejected(client, db_session, admin_user):
    invite = Invite(
        email="expired@example.com",
        token="expired-token",
        invited_by=admin_user.id,
        expires_at=datetime.now(timezone.utc) - timedelta(days=1),
    )
    db_session.add(invite)
    db_session.flush()

    resp = client.post(
        "/api/auth/register",
        json={
            "email": "expired@example.com",
            "password": "password123",
            "display_name": "Expired",
            "invite_token": "expired-token",
        },
    )
    assert resp.status_code in (400, 403)


def test_mismatched_email_invite_rejected(client, db_session, admin_user):
    invite = Invite(
        email="right@example.com",
        token="mismatch-token",
        invited_by=admin_user.id,
        expires_at=datetime.now(timezone.utc) + timedelta(days=1),
    )
    db_session.add(invite)
    db_session.flush()

    resp = client.post(
        "/api/auth/register",
        json={
            "email": "wrong@example.com",
            "password": "password123",
            "display_name": "Wrong",
            "invite_token": "mismatch-token",
        },
    )
    assert resp.status_code in (400, 403)


def test_login_good_and_bad_creds(client, regular_user):
    good = client.post(
        "/api/auth/login",
        json={"email": "user@example.com", "password": "user-pass"},
    )
    assert good.status_code == 200
    assert good.json()["access_token"]

    bad = client.post(
        "/api/auth/login",
        json={"email": "user@example.com", "password": "nope"},
    )
    assert bad.status_code == 401


def test_me_with_and_without_token(client, regular_user):
    login = client.post(
        "/api/auth/login",
        json={"email": "user@example.com", "password": "user-pass"},
    )
    token = login.json()["access_token"]

    me = client.get("/api/auth/me", headers=_auth(token))
    assert me.status_code == 200
    body = me.json()
    assert body["email"] == "user@example.com"
    assert body["role"] == "user"

    anon = client.get("/api/auth/me")
    assert anon.status_code in (401, 403)


def test_invite_creation_requires_admin(client, regular_user):
    login = client.post(
        "/api/auth/login",
        json={"email": "user@example.com", "password": "user-pass"},
    )
    token = login.json()["access_token"]
    resp = client.post(
        "/api/invites/",
        json={"email": "someone@example.com"},
        headers=_auth(token),
    )
    assert resp.status_code == 403

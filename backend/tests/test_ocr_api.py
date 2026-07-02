import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.db import get_db
from app.deps import get_current_user
from app.main import app
from app.models.user import User
from app.seed import seed_reference_data
from app.security import hash_password

FAKE_JPEG = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01" + b"\x00" * 64


@pytest.fixture
def seeded(db_session):
    seed_reference_data(db_session)
    return db_session


@pytest.fixture
def alice(seeded):
    u = User(
        email="alice@example.com",
        password_hash=hash_password("password123"),
        display_name="alice",
        role="user",
    )
    seeded.add(u)
    seeded.flush()
    return u


@pytest.fixture
def media_dir(tmp_path, monkeypatch):
    d = tmp_path / "media"
    monkeypatch.setattr(get_settings(), "media_dir", str(d))
    yield d
    if d.exists():
        shutil.rmtree(d, ignore_errors=True)


@pytest.fixture
def client(seeded, alice, media_dir):
    app.dependency_overrides[get_db] = lambda: seeded
    app.dependency_overrides[get_current_user] = lambda: alice
    yield TestClient(app), alice, media_dir
    app.dependency_overrides.clear()


def test_scan_returns_draft(client):
    c, alice, media_dir = client
    resp = c.post(
        "/api/ocr/scan",
        files={"file": ("t.jpg", FAKE_JPEG, "image/jpeg")},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["game_key"] == "powerball"
    assert len(body["lines"]) == 2
    assert body["confidence"]
    assert body["flags"] == []
    assert body["image_path"]


def test_scan_writes_image_file(client):
    c, alice, media_dir = client
    resp = c.post(
        "/api/ocr/scan",
        files={"file": ("t.jpg", FAKE_JPEG, "image/jpeg")},
    )
    assert resp.status_code == 200
    saved = Path(get_settings().media_dir)
    files = list(saved.rglob("*"))
    assert any(p.is_file() for p in files)
    # image lives under media_dir/<user_id>/
    assert any(str(alice.id) in str(p) for p in files)


def test_scan_no_file_422(client):
    c, alice, media_dir = client
    resp = c.post("/api/ocr/scan")
    assert resp.status_code == 422


def test_scan_non_image_400(client):
    c, alice, media_dir = client
    resp = c.post(
        "/api/ocr/scan",
        files={"file": ("t.txt", b"hello world", "text/plain")},
    )
    assert resp.status_code == 400


def test_scan_empty_file_400(client):
    c, alice, media_dir = client
    resp = c.post(
        "/api/ocr/scan",
        files={"file": ("t.jpg", b"", "image/jpeg")},
    )
    assert resp.status_code == 400

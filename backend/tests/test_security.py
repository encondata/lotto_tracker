import pytest

from app.security import (
    create_access_token,
    decode_token,
    hash_password,
    verify_password,
)


def test_hash_verify_roundtrip():
    h = hash_password("s3cret-password")
    assert h != "s3cret-password"
    assert verify_password("s3cret-password", h) is True


def test_verify_wrong_password_fails():
    h = hash_password("s3cret-password")
    assert verify_password("wrong-password", h) is False


def test_token_roundtrip_carries_sub_and_role():
    token = create_access_token(sub="user-123", role="admin")
    payload = decode_token(token)
    assert payload["sub"] == "user-123"
    assert payload["role"] == "admin"


def test_tampered_token_fails():
    token = create_access_token(sub="user-123", role="user")
    tampered = token[:-2] + ("aa" if token[-2:] != "aa" else "bb")
    with pytest.raises(Exception):
        decode_token(tampered)

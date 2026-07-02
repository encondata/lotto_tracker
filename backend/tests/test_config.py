from app.config import Settings


def test_cors_star_from_env(monkeypatch):
    monkeypatch.setenv("CORS_ALLOW_ORIGINS", "*")
    s = Settings()
    assert s.cors_allow_origins == ["*"]


def test_cors_csv_from_env(monkeypatch):
    monkeypatch.setenv("CORS_ALLOW_ORIGINS", "http://a.com, http://b.com")
    s = Settings()
    assert s.cors_allow_origins == ["http://a.com", "http://b.com"]


def test_cors_default_is_list():
    assert Settings(_env_file=None).cors_allow_origins == ["*"]

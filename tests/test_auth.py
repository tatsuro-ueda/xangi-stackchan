import pytest

from xangi_stackchan.auth import build_xangi_basic_auth


def test_build_xangi_basic_auth_returns_none_when_env_missing(monkeypatch):
    monkeypatch.delenv("XANGI_BASIC_AUTH_USER", raising=False)
    monkeypatch.delenv("XANGI_BASIC_AUTH_PASSWORD", raising=False)

    assert build_xangi_basic_auth() is None


def test_build_xangi_basic_auth_returns_requests_auth(monkeypatch):
    monkeypatch.setenv("XANGI_BASIC_AUTH_USER", "feel")
    monkeypatch.setenv("XANGI_BASIC_AUTH_PASSWORD", "secret")

    auth = build_xangi_basic_auth()

    assert auth is not None
    assert auth.username == "feel"
    assert auth.password == "secret"


def test_build_xangi_basic_auth_rejects_partial_env(monkeypatch):
    monkeypatch.setenv("XANGI_BASIC_AUTH_USER", "feel")
    monkeypatch.delenv("XANGI_BASIC_AUTH_PASSWORD", raising=False)

    with pytest.raises(ValueError):
        build_xangi_basic_auth()

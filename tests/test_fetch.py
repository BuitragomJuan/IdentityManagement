import pytest
import requests

from src import fetch
from src.fetch import FetchError, fetch_users


class FakeResponse:
    def __init__(self, payload=None, status=200, bad_json=False):
        self._payload, self.status_code, self._bad = payload, status, bad_json
        self.headers = {"content-type": "application/json"}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(response=self)

    def json(self):
        if self._bad:
            raise ValueError("bad json")
        return self._payload


def test_returns_list(monkeypatch):
    monkeypatch.setattr(fetch.requests, "get", lambda *a, **k: FakeResponse([{"id": 1}]))
    assert fetch_users() == [{"id": 1}]


@pytest.mark.parametrize("resp", [
    FakeResponse({"not": "a list"}),
    FakeResponse(bad_json=True),
    FakeResponse(status=500),
])
def test_bad_responses_raise(monkeypatch, resp):
    monkeypatch.setattr(fetch.requests, "get", lambda *a, **k: resp)
    with pytest.raises(FetchError):
        fetch_users()


def test_timeout_raises(monkeypatch):
    def boom(*a, **k):
        raise requests.Timeout()
    monkeypatch.setattr(fetch.requests, "get", boom)
    with pytest.raises(FetchError):
        fetch_users()

def test_passes_timeout_as_keyword(monkeypatch):
    captured = {}
    def fake_get(url, **kwargs):
        captured.update(kwargs)
        return FakeResponse([])
    monkeypatch.setattr(fetch.requests, "get", fake_get)
    fetch_users(timeout=5)
    assert captured["timeout"] == 5

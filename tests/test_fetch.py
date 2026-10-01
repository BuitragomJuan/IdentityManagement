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


# --- NR04: secure transport ----------------------------------------------------

def _install(monkeypatch, response, captured=None):
    def fake_get(url, **kwargs):
        if captured is not None:
            captured.update(kwargs, url=url)
        return response
    monkeypatch.setattr(fetch.requests, "get", fake_get)


@pytest.mark.parametrize("url", [
    "http://jsonplaceholder.typicode.com/users",
    "ftp://example.org/users",
    "file:///etc/passwd",
    "jsonplaceholder.typicode.com/users",
    "https:///users",
])
def test_nr04_non_https_refused_before_any_request(monkeypatch, url):
    def must_not_be_called(*a, **k):
        raise AssertionError("no request may be sent for a non-HTTPS URL")
    monkeypatch.setattr(fetch.requests, "get", must_not_be_called)
    with pytest.raises(FetchError, match="refusing non-HTTPS URL"):
        fetch_users(url=url)


def test_nr04_refusal_does_not_echo_the_url(monkeypatch):
    with pytest.raises(FetchError) as exc_info:
        fetch_users(url="http://user:s3cret@example.org/users?token=abc")
    assert "s3cret" not in str(exc_info.value)
    assert "token" not in str(exc_info.value)


def test_nr04_cert_verification_on_and_redirects_off(monkeypatch):
    captured = {}
    _install(monkeypatch, FakeResponse([]), captured)
    fetch_users()
    assert captured["verify"] is True
    assert captured["allow_redirects"] is False
    assert captured["timeout"] == fetch.API_TIMEOUT


def test_nr04_ssl_error_fails_closed(monkeypatch):
    def bad_cert(*a, **k):
        raise requests.exceptions.SSLError("certificate verify failed")
    monkeypatch.setattr(fetch.requests, "get", bad_cert)
    with pytest.raises(FetchError, match=r"connection failed \(SSLError\)"):
        fetch_users()


@pytest.mark.parametrize("status", [301, 302, 307, 204])
def test_nr04_only_status_200_accepted(monkeypatch, status):
    _install(monkeypatch, FakeResponse([], status=status))
    with pytest.raises(FetchError, match=f"unexpected HTTP status {status}"):
        fetch_users()


@pytest.mark.parametrize("content_type", ["text/html", "text/plain", "application/xml", ""])
def test_nr04_wrong_content_type_rejected(monkeypatch, content_type):
    resp = FakeResponse([{"id": 1}])
    resp.headers = {"content-type": content_type}
    _install(monkeypatch, resp)
    with pytest.raises(FetchError, match="unexpected content type"):
        fetch_users()


@pytest.mark.parametrize("content_type", ["application/json", "application/json; charset=utf-8", "Application/JSON"])
def test_nr04_json_content_type_variants_accepted(monkeypatch, content_type):
    resp = FakeResponse([{"id": 1}])
    resp.headers = {"content-type": content_type}
    _install(monkeypatch, resp)
    assert fetch_users() == [{"id": 1}]


def test_nr04_hostile_content_type_is_sanitized_in_error(monkeypatch):
    # server-controlled header text must not inject fake log lines
    resp = FakeResponse([])
    resp.headers = {"content-type": "text/html\r\n2026-01-01 | INFO | fake log line" + "x" * 200}
    _install(monkeypatch, resp)
    with pytest.raises(FetchError) as exc_info:
        fetch_users()
    message = str(exc_info.value)
    assert "\r" not in message and "\n" not in message
    assert len(message) < 120


def test_nr04_source_host_is_host_only():
    assert fetch.source_host("https://jsonplaceholder.typicode.com/users?token=abc") == "jsonplaceholder.typicode.com"

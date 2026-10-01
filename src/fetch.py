import logging
from urllib.parse import urlsplit

import requests

from src.config import API_TIMEOUT, API_URL

logger = logging.getLogger(__name__)

EXPECTED_CONTENT_TYPE = "application/json"


class FetchError(Exception):
    """Contractor data could not be retrieved or is not usable."""


def fetch_users(url: str = API_URL, timeout: float = API_TIMEOUT) -> list[dict]:
    """Fetch contractor records from the API. Raises FetchError on any failure.

    NR04: HTTPS only, certificate verification on, explicit timeout, redirects
    not followed, status must be exactly 200, content type must be JSON.
    """
    _require_https(url)
    try:
        response = requests.get(url, timeout=timeout, verify=True, allow_redirects=False)
        response.raise_for_status()
    except requests.Timeout as e:
        raise FetchError(f"request timed out after {timeout}s") from e
    except requests.HTTPError as e:
        raise FetchError(f"endpoint returned HTTP {e.response.status_code}") from e
    except requests.RequestException as e:
        # SSLError (bad/expired/self-signed certificate) lands here: fail closed.
        raise FetchError(f"connection failed ({type(e).__name__})") from e

    content_type = response.headers.get("content-type", "")
    logger.debug("Response: HTTP %s, content-type %s", response.status_code, _safe_for_log(content_type))

    if response.status_code != 200:
        # 3xx (redirects are not followed — a redirect could downgrade to HTTP or
        # point elsewhere) and unexpected 2xx like 204 No Content.
        raise FetchError(f"unexpected HTTP status {response.status_code}")

    if content_type.split(";")[0].strip().lower() != EXPECTED_CONTENT_TYPE:
        raise FetchError(f"unexpected content type ({_safe_for_log(content_type)})")

    try:
        data = response.json()
    except ValueError as e:
        raise FetchError("response is not valid JSON") from e

    if not isinstance(data, list):
        raise FetchError(f"expected a JSON list, got {type(data).__name__}")

    return data


def source_host(url: str = API_URL) -> str:
    """Host only, for logging: a full URL could carry tokens in its query string."""
    return urlsplit(url).hostname or "<unknown>"


def _require_https(url: str) -> None:
    parts = urlsplit(url)
    if parts.scheme != "https" or not parts.hostname:
        # Never echo the URL itself (could carry credentials) — scheme is enough.
        raise FetchError(f"refusing non-HTTPS URL (scheme: {parts.scheme or 'none'})")


def _safe_for_log(text: str, limit: int = 60) -> str:
    """Server-controlled text going into our log: printable ASCII only, truncated.

    Prevents log injection (fake log lines via control characters) and log bloat.
    """
    cleaned = "".join(ch if " " <= ch <= "~" else "?" for ch in text[:limit])
    return cleaned + ("…" if len(text) > limit else "") or "<none>"

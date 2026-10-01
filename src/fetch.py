import requests

from src.config import API_TIMEOUT, API_URL


class FetchError(Exception):
    """Contractor data could not be retrieved or is not usable."""


def fetch_users(url: str = API_URL, timeout: float = API_TIMEOUT) -> list[dict]:
    """Fetch contractor records from the API. Raises FetchError on any failure."""
    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
    except requests.Timeout as e:
        raise FetchError(f"request timed out after {timeout}s") from e
    except requests.HTTPError as e:
        raise FetchError(f"endpoint returned HTTP {e.response.status_code}") from e
    except requests.RequestException as e:
        raise FetchError(f"connection failed ({type(e).__name__})") from e

    try:
        data = response.json()
    except ValueError as e:
        content_type = response.headers.get("content-type")
        raise FetchError(f"response is not valid JSON (content-type: {content_type})") from e

    if not isinstance(data, list):
        raise FetchError(f"expected a JSON list, got {type(data).__name__}")

    return data

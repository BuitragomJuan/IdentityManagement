import logging

from src.config import LOG_FILE, LOG_LEVEL

LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"

# Third-party loggers that would write request lines (full path + query string,
# where a token would live in production) at DEBUG. Capped regardless of LOG_LEVEL (NR05).
_QUIET_LIBRARIES = ("urllib3", "requests")


def setup_logging() -> None:
    """Configure root logging once, from main: console + file (output/), UTF-8, per run."""
    root = logging.getLogger()
    # basicConfig is a no-op when the root logger already has handlers, but the
    # FileHandler argument would still be created (opening and truncating the
    # file) and then leaked unclosed. Only build handlers when they will be used.
    if not root.handlers:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        logging.basicConfig(
            level=LOG_LEVEL,
            format=LOG_FORMAT,
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler(LOG_FILE, mode="w", encoding="utf-8"),
            ],
        )
    for name in _QUIET_LIBRARIES:
        logging.getLogger(name).setLevel(logging.WARNING)

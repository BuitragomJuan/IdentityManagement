import logging
import sys

from src.fetch import FetchError, fetch_users
from src.logging_setup import setup_logging

logger = logging.getLogger(__name__)


def main() -> int:
    setup_logging()
    logger.info("Process started")
    try:
        users = fetch_users()
    except FetchError as e:
        logger.error("Fetch failed: %s", e)
        return 1
    # ... email generation, CSV (later cards)
    return 0


if __name__ == "__main__":
    sys.exit(main())

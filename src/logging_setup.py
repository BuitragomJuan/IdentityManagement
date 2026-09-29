import logging

from src.config import LOG_FILE, LOG_LEVEL

LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"


def setup_logging() -> None:
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=LOG_LEVEL,
        format=LOG_FORMAT,
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(LOG_FILE, mode="w", encoding="utf-8"),
        ],
    )
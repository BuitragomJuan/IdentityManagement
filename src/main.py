import logging
import sys

from src.config import CSV_FILE
from src.csv_writer import write_csv
from src.email_generator import build_username, to_email
from src.fetch import FetchError, fetch_users
from src.logging_setup import setup_logging
from src.models import Row
from src.validation import InvalidRecordError, validate_record

logger = logging.getLogger(__name__)


def main() -> int:
    setup_logging()
    logger.info("Process started")
    try:
        users = fetch_users()
    except FetchError as e:
        logger.error("Fetch failed: %s", e)
        return 1

    rows = []
    for raw in users:
        try:
            contractor = validate_record(raw)
        except InvalidRecordError as e:
            logger.warning("Skipped %s",e) #"record 3: missing required key"
            continue


        try:
            corporate_email = to_email(build_username(contractor.name))
        except ValueError as e:
            logger.warning("Skipped record %s: %s", contractor.id, e) # id + reason
            continue

        rows.append(Row(contractor=contractor,corporate_email=corporate_email))

    if not rows:
        logger.error("No valid records; CSV not written")
        return 1


    write_csv(rows, CSV_FILE)
    return 0


if __name__ == "__main__":
    sys.exit(main())

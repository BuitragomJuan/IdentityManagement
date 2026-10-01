import logging
import sys
import time
from pathlib import Path

from src.config import CSV_FILE, PROJECT_ROOT
from src.csv_writer import write_csv
from src.email_generator import EmailRegistry, build_username, to_email
from src.fetch import FetchError, fetch_users
from src.logging_setup import setup_logging
from src.models import Row
from src.validation import InvalidRecordError, validate_record

logger = logging.getLogger(__name__)


def main() -> int:
    """Entry point: configure logging, run the pipeline, always log runtime."""
    setup_logging()
    started = time.perf_counter()
    logger.info("Process started")
    exit_code = 1  # stays 1 if _run raises unexpectedly
    try:
        exit_code = _run(CSV_FILE)
        return exit_code
    finally:
        elapsed = time.perf_counter() - started
        logger.info("Process finished in %.2fs (exit code %d)", elapsed, exit_code)


def _run(csv_path: Path) -> int:
    """Fetch, validate, generate emails and write the CSV. Returns the exit code."""
    try:
        users = fetch_users()
    except FetchError as e:
        logger.error("Fetch failed: %s", e)
        return 1
    logger.info("Records fetched from endpoint: %d", len(users))

    rows = _build_rows(users)
    skipped = len(users) - len(rows)
    logger.info(
        "Records processed successfully: %d of %d (skipped: %d)",
        len(rows), len(users), skipped,
    )

    if not rows:
        logger.error("No valid records; CSV not written")
        return 1

    try:
        write_csv(rows, csv_path)
    except OSError as e:
        # Type name only: str(e) carries the absolute path (operator's home directory).
        hint = " — is the file open in another program?" if isinstance(e, PermissionError) else ""
        logger.error("CSV not written: %s (%s)%s", _display_path(csv_path), type(e).__name__, hint)
        return 1
    logger.info("CSV generated: %s (%d rows)", _display_path(csv_path), len(rows))
    return 0


def _build_rows(users: list) -> list[Row]:
    """Turn raw records into CSV rows; skip and log (id + reason only) any that fail."""
    rows = []
    registry = EmailRegistry()  # one per run: uniqueness is per run (intent.md non-goals)
    seen_ids: set[int] = set()
    for raw in users:
        try:
            contractor = validate_record(raw)
        except InvalidRecordError as e:
            logger.warning("Skipped %s", e)  # "record 3: missing required key: phone"
            continue
        if contractor.id in seen_ids:
            # NR01: ids are how every log line refers to a record — a repeat makes the audit trail ambiguous
            logger.warning("Skipped record %s: duplicate id", contractor.id)
            continue
        seen_ids.add(contractor.id)

        try:
            result = build_username(contractor.name)
        except ValueError as e:
            logger.warning("Skipped record %s: %s", contractor.id, e)  # id + reason, never the name
            continue
        if result.ignored:
            # categories only ("prefix", "suffix", "initial") — never the name or its tokens
            logger.info("record %s: name adjusted (%s ignored)", contractor.id, ", ".join(result.ignored))

        assignment = registry.assign(result.username)
        if assignment.suffix:
            # id + suffix only — the username is derived from the name (NR05)
            logger.info("record %s: email collision resolved, suffix %d assigned", contractor.id, assignment.suffix)

        corporate_email = to_email(assignment.username)
        rows.append(Row(contractor=contractor, corporate_email=corporate_email))
    return rows


def _display_path(path: Path) -> str:
    """Path relative to the project root, so logs don't expose the operator's home directory."""
    try:
        return path.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return path.name


if __name__ == "__main__":
    sys.exit(main())

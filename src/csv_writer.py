import csv
import os
import tempfile
from pathlib import Path

from src.models import Row

CSV_HEADERS = ["Nombre", "Telefono", "Correo electronico original", "Empresa", "Ciudad", "Correo electronico DemoCompany"]

# NR03: a cell starting with one of these can be evaluated as a formula by
# Excel/LibreOffice/Sheets (e.g. =HYPERLINK(...), =cmd|'/c calc'!A1).
FORMULA_TRIGGERS = ("=", "+", "-", "@", "\t", "\r")


def sanitize_cell(value: str) -> str:
    """NR03 / D02: neutralize spreadsheet formula injection with a leading single quote.

    The quote makes spreadsheets treat the cell as text; the original value is
    kept (visible and reversible) rather than stripped.
    """
    if value.startswith(FORMULA_TRIGGERS):
        return "'" + value
    return value


def _to_cells(row: Row) -> list[str]:
    """The single path every cell takes into the file — sanitized here, so nothing bypasses NR03."""
    cells = [
        row.contractor.name,
        row.contractor.phone,
        row.contractor.email,
        row.contractor.company,
        row.contractor.city,
        row.corporate_email,
    ]
    return [sanitize_cell(cell) for cell in cells]


def write_csv(rows: list[Row], path: Path) -> None:
    """Write the CSV atomically (NR06): all rows or nothing.

    Writes to a temp file in the same directory, flushes it to disk, then
    os.replace()s it over the target — an atomic rename on the same filesystem
    (Windows included). On any failure the temp file is removed and an existing
    CSV from a previous run is left untouched, so a half-written file can never
    be picked up and used to provision accounts.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    # mkstemp creates the file with owner-only permissions (0600 on POSIX):
    # the CSV holds personal data. Same directory => same filesystem => atomic replace.
    fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.stem}-", suffix=".tmp")
    tmp_path = Path(tmp_name)
    try:
        with open(fd, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(CSV_HEADERS)
            for row in rows:
                writer.writerow(_to_cells(row))
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, path)
    except BaseException:  # also on Ctrl+C: never leave the temp file behind
        tmp_path.unlink(missing_ok=True)
        raise

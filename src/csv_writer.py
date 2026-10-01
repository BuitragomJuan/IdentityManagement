import csv
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
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(CSV_HEADERS)
        for row in rows:
            writer.writerow(_to_cells(row))

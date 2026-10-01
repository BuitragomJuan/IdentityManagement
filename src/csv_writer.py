import csv
from pathlib import Path

from src.models import Row

CSV_HEADERS = ["Nombre","Telefono","Correo electronico original","Empresa","Ciudad","Correo electronico DemoCompany"]


def _to_cells(row: Row) -> list[str]:
    cells = [row.contractor.name,row.contractor.phone,row.contractor.email,row.contractor.company,row.contractor.city,row.corporate_email]
    return cells


def write_csv(rows: list[Row], path: Path) -> None:

    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path,"w", newline="",encoding="utf-8-sig") as f:
        writer = csv.writer(f)

        #write the header
        writer.writerow(CSV_HEADERS)

        #write content
        for row in rows:
            writer.writerow(_to_cells(row))
    
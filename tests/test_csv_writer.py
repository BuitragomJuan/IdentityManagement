import csv
from pathlib import Path

import pytest

from src import csv_writer
from src.models import Contractor, Row


@pytest.fixture
def rows():

    row_one = Row(
        contractor = Contractor(1,"jane Doe","555-555-555","JaneDOE@example.org","Commerce.Inc","ExampleVille"),
        corporate_email= "jdoe@democompany.com"
    )
    row_two = Row(
            contractor = Contractor(2,"john Doe","666-666-666","Johndoe@corporate.gov","Doecorp.SAS","New Pork"),
            corporate_email= "jdoe1@democompany.com"
        )
    row_three = Row(
            contractor = Contractor(3,"jill Doe","222-222-222","JillD@umbrella.com","Umbrella","exampletown"),
            corporate_email= "jdoe2@democompany.com"
        )
    
    return [row_one,row_two,row_three]


def _read_back(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.reader(f))


def _row(**overrides):
    fields = dict(id=1, name="Jane Doe", phone="555-555-5555", email="jane@example.org",
                  company="Commerce Inc", city="ExampleVille")
    fields.update(overrides)
    return Row(contractor=Contractor(**fields), corporate_email="jdoe@democompany.com")


def test_header_row(tmp_path,rows):
    
    output_file = tmp_path / "temporary.csv"
    csv_writer.write_csv(rows,output_file)
    assert _read_back(output_file)[0] == csv_writer.CSV_HEADERS


def test_row_count(tmp_path,rows):

    output_file = tmp_path / "temporary.csv"
    csv_writer.write_csv(rows,output_file)
    data = _read_back(output_file)
    assert len(data) == 4


def test_cell_order(tmp_path,rows):

    output_file = tmp_path / "temporary.csv"
    test_row = ["jane Doe","555-555-555","JaneDOE@example.org","Commerce.Inc","ExampleVille","jdoe@democompany.com"]
    csv_writer.write_csv(rows,output_file)
    data = _read_back(output_file)
    assert data[1] == test_row


def test_phone_kept_as_is(tmp_path):

    output_file = tmp_path / "temporary.csv"
    csv_writer.write_csv([_row(phone="010-692-6593 x123")],output_file)
    data = _read_back(output_file)[1]
    assert data[1] == "010-692-6593 x123"


def test_comma_in_value(tmp_path):
    
    output_file = tmp_path / "temporary.csv"
    csv_writer.write_csv([_row(company="Acme, Inc.")], output_file)
    data = _read_back(output_file)[1]
    assert len(data) == 6
    assert data[3] == "Acme, Inc."

def test_quotes_in_value(tmp_path):

    output_file = tmp_path / "temporary.csv"
    csv_writer.write_csv([_row(company='Say "hi" Ltd')],output_file)
    data = _read_back(output_file)[1]
    assert len(data) == 6
    assert data[3] == 'Say "hi" Ltd'


def test_non_ascii(tmp_path):

    output_file = tmp_path / "temporary.csv"
    csv_writer.write_csv([_row(name="José Núñez")],output_file)
    data = _read_back(output_file)[1]
    assert len(data) == 6
    assert data[0] == "José Núñez"


def test_no_blank_lines(tmp_path,rows):

    output_file = tmp_path / "temporary.csv"
    csv_writer.write_csv(rows,output_file)
    assert b"\r\r\n" not in output_file.read_bytes()


def test_creates_parent_dir(tmp_path,rows):
        
    output_file = tmp_path / "nested" / "temporary.csv"
    csv_writer.write_csv(rows,output_file)
    assert output_file.is_file()


def test_overwrites_existing(tmp_path,rows):

    output_file = tmp_path / "temporary.csv"
    csv_writer.write_csv(rows,output_file)
    csv_writer.write_csv(rows[:1],output_file)
    assert len(_read_back(output_file)) == 2


def test_empty_rows_writes_header_only(tmp_path):
        
    output_file = tmp_path / "temporary.csv"
    csv_writer.write_csv([],output_file)
    assert _read_back(output_file) == [csv_writer.CSV_HEADERS]


def test_starts_with_bom_for_excel(tmp_path, rows):
    output_file = tmp_path / "out.csv"
    csv_writer.write_csv(rows, output_file)
    assert output_file.read_bytes().startswith(b"\xef\xbb\xbf")


# --- NR03: CSV / formula injection ---------------------------------------------

@pytest.mark.parametrize("payload", [
    "=1+1",
    "=HYPERLINK(\"http://evil.example\",\"click\")",
    "=cmd|'/c calc'!A1",
    "+1+1",
    "-2+3",
    "@SUM(A1:A2)",
    "\t=1+1",
    "\r=1+1",
])
def test_nr03_sanitize_prefixes_formula_triggers(payload):
    assert csv_writer.sanitize_cell(payload) == "'" + payload


@pytest.mark.parametrize("safe", ["Jane Doe", "1-770-736-8031 x56442", "(254)954-1289", "Romaguera-Crona", "", " =not first char"])
def test_nr03_safe_values_unchanged(safe):
    assert csv_writer.sanitize_cell(safe) == safe


@pytest.mark.parametrize("field, column", [
    ("name", 0), ("phone", 1), ("email", 2), ("company", 3), ("city", 4),
])
def test_nr03_every_contractor_column_is_sanitized(tmp_path, field, column):
    output_file = tmp_path / "out.csv"
    csv_writer.write_csv([_row(**{field: "=1+1"})], output_file)
    assert _read_back(output_file)[1][column] == "'=1+1"


def test_nr03_corporate_email_column_is_sanitized_too(tmp_path):
    # generated values go through the same path — defense in depth, nothing bypasses _to_cells
    output_file = tmp_path / "out.csv"
    row = Row(contractor=_row().contractor, corporate_email="@evil")
    csv_writer.write_csv([row], output_file)
    assert _read_back(output_file)[1][5] == "'@evil"


def test_nr03_leading_plus_phone_is_visibly_prefixed(tmp_path):
    # documented trade-off (intent.md D02): legitimate leading "+" gets a visible quote
    output_file = tmp_path / "out.csv"
    csv_writer.write_csv([_row(phone="+57 300 123 4567")], output_file)
    assert _read_back(output_file)[1][1] == "'+57 300 123 4567"

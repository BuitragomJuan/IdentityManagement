import logging

import pytest

from src import main as main_module
from src.fetch import FetchError


def _raw(id_, name):
    """A valid raw API record (same shape as JSONPlaceholder)."""
    return {
        "id": id_,
        "name": name,
        "email": f"user{id_}@example.org",
        "phone": "555-555-5555",
        "address": {"city": "Testville"},
        "company": {"name": "EGcompany"},
    }


@pytest.fixture
def fake_fetch(monkeypatch):
    """Replace fetch_users in main with one returning the given records."""
    def _install(records):
        monkeypatch.setattr(main_module, "fetch_users", lambda: records)
    return _install


@pytest.fixture(autouse=True)
def info_logs(caplog):
    caplog.set_level(logging.INFO)


def test_happy_path_logs_and_writes_csv(tmp_path, fake_fetch, caplog):
    fake_fetch([_raw(1, "Jane Doe"), _raw(2, "John Smith")])
    csv_path = tmp_path / "out.csv"

    assert main_module._run(csv_path) == 0
    assert csv_path.is_file()
    assert "Records fetched from endpoint: 2" in caplog.text
    assert "Records processed successfully: 2 of 2 (skipped: 0)" in caplog.text
    assert "CSV generated: out.csv (2 rows)" in caplog.text


def test_invalid_records_are_skipped_and_counted(tmp_path, fake_fetch, caplog):
    bad_record = _raw(2, "John Smith")
    del bad_record["phone"]
    fake_fetch([_raw(1, "Jane Doe"), bad_record, _raw(3, "Cher")])

    assert main_module._run(tmp_path / "out.csv") == 0
    assert "Records processed successfully: 1 of 3 (skipped: 2)" in caplog.text
    assert "Skipped record 2: missing required key: phone" in caplog.text
    assert "Skipped record 3:" in caplog.text


def test_skip_logs_contain_no_pii(tmp_path, fake_fetch, caplog):
    # NR05: the skipped record's name, phone and email must not reach the log.
    bad_record = _raw(2, "Cher")  # single-word name -> skipped by email generation
    fake_fetch([_raw(1, "Jane Doe"), bad_record])

    main_module._run(tmp_path / "out.csv")
    assert "Cher" not in caplog.text
    assert "user2@example.org" not in caplog.text
    assert "555-555-5555" not in caplog.text


def test_name_adjustment_logged_by_id_only(tmp_path, fake_fetch, caplog):
    # R06 log: category + record id, never the name or the ignored token
    fake_fetch([_raw(6, "Mrs. Dennis Schulist")])

    assert main_module._run(tmp_path / "out.csv") == 0
    assert "record 6: name adjusted (prefix ignored)" in caplog.text
    assert "Dennis" not in caplog.text
    assert "Mrs" not in caplog.text


def test_empty_username_after_normalization_is_skipped(tmp_path, fake_fetch, caplog):
    # D01
    fake_fetch([_raw(1, "Jane Doe"), _raw(2, "李 王")])

    assert main_module._run(tmp_path / "out.csv") == 0
    assert "Skipped record 2: name has no usable characters after normalization" in caplog.text
    assert "李" not in caplog.text


def test_fetch_failure_exits_1_without_csv(tmp_path, monkeypatch, caplog):
    def failing_fetch():
        raise FetchError("request timed out after 10s")
    monkeypatch.setattr(main_module, "fetch_users", failing_fetch)
    csv_path = tmp_path / "out.csv"

    assert main_module._run(csv_path) == 1
    assert not csv_path.exists()
    assert "Fetch failed: request timed out after 10s" in caplog.text


def test_zero_valid_records_exits_1_without_csv(tmp_path, fake_fetch, caplog):
    fake_fetch([_raw(1, "Cher"), {"id": 2}])
    csv_path = tmp_path / "out.csv"

    assert main_module._run(csv_path) == 1
    assert not csv_path.exists()
    assert "No valid records; CSV not written" in caplog.text


def test_csv_write_failure_exits_1_with_one_clean_line(tmp_path, fake_fetch, monkeypatch, caplog):
    # e.g. the CSV is open in Excel (Windows file lock)
    def locked(rows, path):
        raise PermissionError(13, "Permission denied", r"C:\Users\someone\output\out.csv")
    monkeypatch.setattr(main_module, "write_csv", locked)
    fake_fetch([_raw(1, "Jane Doe")])

    assert main_module._run(tmp_path / "out.csv") == 1
    assert "CSV not written: out.csv (PermissionError)" in caplog.text
    assert "open in another program" in caplog.text
    assert r"C:\Users" not in caplog.text  # no absolute path / operator home dir
    assert "CSV generated" not in caplog.text


def test_main_logs_start_and_runtime(tmp_path, fake_fetch, monkeypatch, caplog):
    # setup_logging would write to the real output/ log; tests must never touch output/.
    monkeypatch.setattr(main_module, "setup_logging", lambda: None)
    monkeypatch.setattr(main_module, "CSV_FILE", tmp_path / "out.csv")
    fake_fetch([_raw(1, "Jane Doe")])

    assert main_module.main() == 0
    assert "Process started" in caplog.text
    assert "Process finished in" in caplog.text
    assert "(exit code 0)" in caplog.text


def test_runtime_logged_on_failure_too(monkeypatch, caplog):
    monkeypatch.setattr(main_module, "setup_logging", lambda: None)
    def failing_fetch():
        raise FetchError("connection failed (ConnectionError)")
    monkeypatch.setattr(main_module, "fetch_users", failing_fetch)

    assert main_module.main() == 1
    assert "(exit code 1)" in caplog.text


def test_collision_resolved_and_logged_by_id_only(tmp_path, fake_fetch, caplog):
    # R07: second and third "J... Doe" get jdoe1 / jdoe2; log carries id + suffix, never the username
    fake_fetch([_raw(1, "John Doe"), _raw(2, "Johana Doe"), _raw(3, "Jill Doe")])
    csv_path = tmp_path / "out.csv"

    assert main_module._run(csv_path) == 0
    content = csv_path.read_text(encoding="utf-8-sig")
    assert "jdoe@democompany.com" in content
    assert "jdoe1@democompany.com" in content
    assert "jdoe2@democompany.com" in content
    assert "record 2: email collision resolved, suffix 1 assigned" in caplog.text
    assert "record 3: email collision resolved, suffix 2 assigned" in caplog.text
    assert "record 1: email collision" not in caplog.text
    assert "jdoe" not in caplog.text


def test_nr01_duplicate_id_skipped(tmp_path, fake_fetch, caplog):
    fake_fetch([_raw(1, "Jane Doe"), _raw(1, "John Smith"), _raw(2, "Ann Lee")])

    assert main_module._run(tmp_path / "out.csv") == 0
    assert "Skipped record 1: duplicate id" in caplog.text
    assert "Records processed successfully: 2 of 3 (skipped: 1)" in caplog.text

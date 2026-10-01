import pytest

from src import validation
from src.models import Contractor
from src.validation import InvalidRecordError


@pytest.fixture
def raw_record():
    raw_record = {
        "id": 1,
        "name": "Jane Doe",
        "username": "DoeJ",
        "email": "jane@EGcompany.com",
        "address": {"street": "sesame street","suite": "Apt. 101","city": "Testville","zipcode": "12345-6789",},
        "phone": "555-555-5555",
        "company": {"name": "EGcompany","catchPhrase": "helping test data since 9:07 PM","bs": "testing data for fun and profit"}
        }
    return raw_record

def test_validate_record_valid(raw_record):

    assert validation.validate_record(raw_record) == Contractor( 1,
                                                                "Jane Doe",
                                                                "555-555-5555",
                                                                "jane@EGcompany.com",
                                                                "EGcompany",
                                                                "Testville")


def test_rejects_non_dict():
    with pytest.raises(InvalidRecordError) as exc_info:
        validation.validate_record(None)
    assert exc_info.value.record_id is None


def test_validate_missing_id(raw_record):
    del raw_record["id"]
    with pytest.raises(InvalidRecordError) as exc_info:
        validation.validate_record(raw_record)
    assert exc_info.value.record_id is None
    assert "id" in exc_info.value.reason


def test_validate_boolean_id(raw_record):
    raw_record["id"] = True
    with pytest.raises(InvalidRecordError) as exc_info:
        validation.validate_record(raw_record)
    assert exc_info.value.record_id is None
    assert "bool" in exc_info.value.reason


def test_missing_value(raw_record):
    del raw_record["phone"]
    with pytest.raises(InvalidRecordError) as exc_info:
        validation.validate_record(raw_record)
    assert exc_info.value.record_id == 1
    assert "phone" in exc_info.value.reason


def test_type_check_string_id(raw_record):
    raw_record["id"] = "12"
    with pytest.raises(InvalidRecordError) as exc_info:
        validation.validate_record(raw_record)
    assert exc_info.value.record_id is None
    assert "id" in exc_info.value.reason


def test_type_check_name(raw_record):
    raw_record["name"] = 123
    with pytest.raises(InvalidRecordError) as exc_info:
        validation.validate_record(raw_record)
    assert exc_info.value.record_id == 1
    assert "name" in exc_info.value.reason


def test_type_check_company(raw_record):
    raw_record["company"] = "Acme"
    with pytest.raises(InvalidRecordError) as exc_info:
        validation.validate_record(raw_record)
    assert exc_info.value.record_id == 1
    assert "company" in exc_info.value.reason


def test_type_check_missing_city(raw_record):
    del raw_record["address"]["city"]
    with pytest.raises(InvalidRecordError) as exc_info:
        validation.validate_record(raw_record)
    assert exc_info.value.record_id == 1
    assert "city" in exc_info.value.reason


def test_nothing_on_city_key(raw_record):
    raw_record["address"]={"city":None}
    with pytest.raises(InvalidRecordError) as exc_info:
        validation.validate_record(raw_record)
    assert exc_info.value.record_id == 1
    assert "city" in exc_info.value.reason


# NR05 test
def test_error_does_not_leak_field_value(raw_record):
    raw_record["company"] = "Jane Doe Consulting"   # wrong type (str, not dict), value contains PII
    with pytest.raises(InvalidRecordError) as exc_info:
        validation.validate_record(raw_record)
    assert "Jane" not in str(exc_info.value)



def test_error_message_is_readable(raw_record):
    del raw_record["phone"]
    with pytest.raises(InvalidRecordError) as exc_info:
        validation.validate_record(raw_record)
    assert str(exc_info.value) == "record 1: missing required key: phone"


def test_company_missing_name(raw_record):
    del raw_record["company"]["name"]
    with pytest.raises(InvalidRecordError) as exc_info:
        validation.validate_record(raw_record)
    assert str(exc_info.value) == "record 1: missing required key: name"


# --- NR01 (It3): content rules ---------------------------------------------------

def test_nr01_values_are_trimmed(raw_record):
    raw_record["name"] = "  Jane Doe  "
    assert validation.validate_record(raw_record).name == "Jane Doe"


@pytest.mark.parametrize("field", ["name", "phone", "email"])
@pytest.mark.parametrize("blank", ["", "   "])
def test_nr01_empty_or_blank_rejected(raw_record, field, blank):
    raw_record[field] = blank
    with pytest.raises(InvalidRecordError) as exc_info:
        validation.validate_record(raw_record)
    assert exc_info.value.reason == f"empty value: {field}"


def test_nr01_blank_nested_city_rejected(raw_record):
    raw_record["address"]["city"] = " "
    with pytest.raises(InvalidRecordError) as exc_info:
        validation.validate_record(raw_record)
    assert exc_info.value.reason == "empty value: city"


def test_nr01_too_long_rejected(raw_record):
    raw_record["name"] = "J" * (validation.MAX_FIELD_LENGTH + 1)
    with pytest.raises(InvalidRecordError) as exc_info:
        validation.validate_record(raw_record)
    assert "too long: name" in exc_info.value.reason


def test_nr01_max_length_accepted(raw_record):
    raw_record["company"]["name"] = "C" * validation.MAX_FIELD_LENGTH
    assert validation.validate_record(raw_record).company == "C" * validation.MAX_FIELD_LENGTH


@pytest.mark.parametrize("bad", [
    "Jane\tDoe",          # tab (Cc) — also a CSV-injection trigger
    "Jane\rDoe",          # CR
    "Jane\nDoe",          # LF — would break a CSV/log line
    "Jane\x00Doe",        # NUL
    "Jane​Doe",      # zero-width space (Cf): invisible, defeats visual review
    "Jane ‮eoD",     # right-to-left override (Cf): displays differently than it reads
])
def test_nr01_control_and_invisible_chars_rejected(raw_record, bad):
    raw_record["name"] = bad
    with pytest.raises(InvalidRecordError) as exc_info:
        validation.validate_record(raw_record)
    assert exc_info.value.reason == "control or invisible character in: name"


@pytest.mark.parametrize("email", ["jane", "jane@", "@example.org", "jane@example", "ja ne@example.org", "a@b@c.org"])
def test_nr01_bad_email_shape_rejected(raw_record, email):
    raw_record["email"] = email
    with pytest.raises(InvalidRecordError) as exc_info:
        validation.validate_record(raw_record)
    assert exc_info.value.reason == "invalid format: email"


@pytest.mark.parametrize("email", ["Sincere@april.biz", "Julianne.OConner@kory.org", "Lucio_Hettinger@annie.ca"])
def test_nr01_real_api_emails_accepted(raw_record, email):
    raw_record["email"] = email
    assert validation.validate_record(raw_record).email == email


@pytest.mark.parametrize("bad_id", [0, -1])
def test_nr01_non_positive_id_rejected(raw_record, bad_id):
    raw_record["id"] = bad_id
    with pytest.raises(InvalidRecordError) as exc_info:
        validation.validate_record(raw_record)
    assert exc_info.value.record_id is None


def test_nr01_accented_names_still_valid(raw_record):
    raw_record["name"] = "José Núñez"
    assert validation.validate_record(raw_record).name == "José Núñez"


def test_nr01_reasons_never_contain_values(raw_record):
    raw_record["email"] = "secret.person@nowhere"
    with pytest.raises(InvalidRecordError) as exc_info:
        validation.validate_record(raw_record)
    assert "secret" not in str(exc_info.value)

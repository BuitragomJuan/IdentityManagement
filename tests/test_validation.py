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

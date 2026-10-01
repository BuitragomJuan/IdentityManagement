import re
import unicodedata

from src.models import Contractor

# NR01 limits. Generous for real names/companies; blocks oversized payloads
# (Excel's hard cell limit is 32,767 chars) before they reach the CSV.
MAX_FIELD_LENGTH = 200

# Deliberately loose: one "@", non-empty local part, a dot in the domain, no
# whitespace. The original email is passed through, not used to send mail, so
# full RFC 5322 validation would add risk (complex regex) without value.
_EMAIL_SHAPE = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")


class InvalidRecordError(Exception):
    """A raw API record failed validation. Reasons name fields, never values (NR05)."""

    def __init__(self, record_id: int | None, reason: str):
        super().__init__(f"record {record_id}: {reason}")
        self.record_id = record_id
        self.reason = reason


def validate_record(raw_record) -> Contractor:
    """Validate a raw API record and build its Contractor (the trust boundary).

    It1: presence + type. It3 (NR01): positive id; text fields trimmed,
    non-empty, at most MAX_FIELD_LENGTH, free of control/invisible characters;
    email has a plausible shape. Raises InvalidRecordError on the first failure.
    """
    if not isinstance(raw_record, dict):
        raise InvalidRecordError(None, "record not of dictionary type")

    record_id = _require(raw_record, "id", int, None)
    if isinstance(record_id, bool):
        raise InvalidRecordError(None, "id can't be a boolean value")
    if record_id < 1:
        raise InvalidRecordError(None, "id must be a positive integer")

    name = _require_text(raw_record, "name", record_id)
    phone = _require_text(raw_record, "phone", record_id)
    email = _require_text(raw_record, "email", record_id)
    if not _EMAIL_SHAPE.fullmatch(email):
        raise InvalidRecordError(record_id, "invalid format: email")

    company = _require(raw_record, "company", dict, record_id)
    company_name = _require_text(company, "name", record_id)  # reason says "name", not "company.name" — see intent.md known limitations
    address = _require(raw_record, "address", dict, record_id)
    city = _require_text(address, "city", record_id)

    return Contractor(record_id, name, phone, email, company_name, city)


def _require(data: dict, key: str, expected_type: type, record_id: int | None) -> object:
    """Return data[key] if present and of expected_type, else raise InvalidRecordError."""
    if key not in data:
        raise InvalidRecordError(record_id, f"missing required key: {key}")
    elif not isinstance(data[key], expected_type):
        raise InvalidRecordError(record_id, f"wrong type for {key}, expected type: {expected_type.__name__}")
    return data[key]


def _require_text(data: dict, key: str, record_id: int) -> str:
    """A required string field, trimmed, with the NR01 content rules applied."""
    value = _require(data, key, str, record_id).strip()
    if not value:
        raise InvalidRecordError(record_id, f"empty value: {key}")
    if len(value) > MAX_FIELD_LENGTH:
        raise InvalidRecordError(record_id, f"too long: {key} (max {MAX_FIELD_LENGTH})")
    if _has_control_chars(value):
        raise InvalidRecordError(record_id, f"control or invisible character in: {key}")
    return value


def _has_control_chars(value: str) -> bool:
    # Unicode category C*: Cc (tab, CR, LF, NUL…), Cf (zero-width chars, bidi
    # overrides like U+202E that make text display differently than it reads),
    # Co/Cs/Cn (private use, surrogates, unassigned).
    return any(unicodedata.category(ch).startswith("C") for ch in value)

import pytest

from src import email_generator


def test_parse_name_valid():
    name = "John Doe"
    expected_tuple = ("John", "Doe")
    assert email_generator.parse_name(name) == expected_tuple


def test_normalize_lowercase():
    name = "Doe"
    expected_normalized = "doe"
    assert email_generator.normalize(name) == expected_normalized

def test_parse_blank_name():
    name = ""
    with pytest.raises(ValueError):
        email_generator.parse_name(name)


def test_build_username():
    name = "John Doe"
    expected_username = "jdoe"
    assert email_generator.build_username(name) == expected_username


def test_to_email():
    username = "jdoe"
    assert email_generator.to_email(username) == "jdoe@democompany.com"


def test_parse_name_invalid():
    name = "John"
    with pytest.raises(ValueError):
        email_generator.parse_name(name)


def test_space_in_name():
    name = " John  Doe "
    expected_tuple = ("John", "Doe")
    assert email_generator.parse_name(name) == expected_tuple


def test_full_name_with_middle():
    name = "John Michael Doe"
    expected_tuple = ("John", "Doe")
    assert email_generator.parse_name(name) == expected_tuple

def test_full_name_username():
    name = "John Michael Doe"
    expected_username = "jdoe"
    assert email_generator.build_username(name) == expected_username


def test_build_username_uppercase():
    assert email_generator.build_username("JANE DOE") == "jdoe"

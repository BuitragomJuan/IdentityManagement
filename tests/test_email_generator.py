import pytest

from src import email_generator


def _username(name):
    return email_generator.build_username(name).username


# --- parse_name: basics (It1) -------------------------------------------------

def test_parse_name_valid():
    parsed = email_generator.parse_name("John Doe")
    assert (parsed.first, parsed.last) == ("John", "Doe")
    assert parsed.ignored == ()


def test_parse_blank_name():
    with pytest.raises(ValueError):
        email_generator.parse_name("")


def test_parse_name_invalid():
    with pytest.raises(ValueError):
        email_generator.parse_name("John")


def test_space_in_name():
    parsed = email_generator.parse_name(" John  Doe ")
    assert (parsed.first, parsed.last) == ("John", "Doe")


def test_full_name_with_middle():
    parsed = email_generator.parse_name("John Michael Doe")
    assert (parsed.first, parsed.last) == ("John", "Doe")


# --- R06 acceptance examples (requirements.md) --------------------------------

@pytest.mark.parametrize("name, expected", [
    ("Jane A. Doe", "jdoe"),
    ("Dr. James Charles V", "jcharles"),
    ("Mrs. Dennis Schulist", "dschulist"),
    ("Nicholas Runolfsdottir V", "nrunolfsdottir"),
])
def test_r06_acceptance_examples(name, expected):
    assert _username(name) == expected


@pytest.mark.parametrize("name", ["Dr. Smith", "John V", "Mr. Jr.", "J. R. Tolkien"])
def test_r06_fewer_than_two_words_remain_raises(name):
    with pytest.raises(ValueError):
        email_generator.parse_name(name)


@pytest.mark.parametrize("name", [
    "Mr John Doe", "MR. John Doe", "mr. John Doe", "Dr John Doe",
    "Ms. John Doe", "Miss John Doe", "Prof. John Doe", "PROF John Doe",
])
def test_prefix_case_insensitive_dot_optional(name):
    assert _username(name) == "jdoe"


@pytest.mark.parametrize("name", ["John Doe Jr.", "John Doe JR", "John Doe III", "John Doe Jr. III"])
def test_suffixes_stripped(name):
    assert _username(name) == "jdoe"


def test_sr_is_prefix_at_start_and_suffix_at_end():
    assert _username("Sr. John Doe") == "jdoe"
    assert _username("John Doe Sr.") == "jdoe"


def test_prefix_word_in_the_middle_is_kept():
    # position-aware: only leading prefixes / trailing suffixes are ignored
    assert email_generator.parse_name("John Dr Doe").last == "Doe"


@pytest.mark.parametrize("name, expected_ignored", [
    ("John Doe", ()),
    ("Mrs. Dennis Schulist", ("prefix",)),
    ("Nicholas Runolfsdottir V", ("suffix",)),
    ("Jane A. Doe", ("initial",)),
    ("Dr. James A. Charles V", ("prefix", "suffix", "initial")),
])
def test_ignored_categories_reported(name, expected_ignored):
    assert email_generator.parse_name(name).ignored == expected_ignored


def test_single_cjk_character_is_not_an_initial():
    # regression: "李".isalpha() is True, but it is a name part, not an initial
    parsed = email_generator.parse_name("李 王")
    assert (parsed.first, parsed.last) == ("李", "王")
    assert parsed.ignored == ()


def test_accented_single_letter_is_an_initial():
    assert email_generator.parse_name("Jane É. Doe").ignored == ("initial",)


def test_ignored_never_contains_name_tokens():
    # the categories are logged by main (NR05): they must not carry name parts
    ignored = email_generator.parse_name("Dr. James A. Charles V").ignored
    assert set(ignored) <= {"prefix", "suffix", "initial"}


# --- R09 normalize -------------------------------------------------------------

@pytest.mark.parametrize("token, expected", [
    ("Doe", "doe"),
    ("Núñez", "nunez"),          # transliterated, not stripped to "nez"
    ("José", "jose"),
    ("O'Brien", "obrien"),       # separator stripped
    ("Mary-Jane", "maryjane"),
    ("Doe2", "doe2"),            # digits allowed
    ("Ｊｏｈｎ", "john"),         # fullwidth folded by NFKD
    ("Łukasz", "ukasz"),         # known limitation: ł has no decomposition
    ("李", ""),                  # no Latin decomposition -> empty (D01 handles it)
])
def test_normalize(token, expected):
    assert email_generator.normalize(token) == expected


def test_normalize_output_is_always_in_allowed_set():
    for token in ["Núñez", "O'Brien", "Zoë", "Ｊｏｈｎ", "a.b@c", "Łukasz", "李"]:
        assert all(c in "abcdefghijklmnopqrstuvwxyz0123456789" for c in email_generator.normalize(token))


def test_cyrillic_homoglyph_is_stripped_not_mapped():
    # Cyrillic "а" looks like Latin "a" but has no decomposition: it is dropped,
    # so a lookalike name cannot produce the same username as the Latin original.
    assert email_generator.normalize("Jаne") == "jne"


# --- build_username: pipeline --------------------------------------------------

def test_build_username():
    assert _username("John Doe") == "jdoe"


def test_full_name_username():
    assert _username("John Michael Doe") == "jdoe"


def test_build_username_uppercase():
    assert _username("JANE DOE") == "jdoe"


def test_initial_taken_after_normalize():
    assert _username("Émile Zola") == "ezola"
    assert _username("José Núñez") == "jnunez"


@pytest.mark.parametrize("name", ["李 王", "'' Doe", "John --"])
def test_d01_empty_after_normalization_raises(name):
    with pytest.raises(ValueError, match="no usable characters"):
        email_generator.build_username(name)


def test_to_email():
    assert email_generator.to_email("jdoe") == "jdoe@democompany.com"

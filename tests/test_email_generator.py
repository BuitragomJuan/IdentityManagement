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


# --- R07 EmailRegistry: sequential suffix per base -----------------------------

def test_r07_first_gets_no_number_then_1_then_2():
    registry = email_generator.EmailRegistry()
    assert registry.assign("jdoe") == ("jdoe", 0)
    assert registry.assign("jdoe") == ("jdoe1", 1)
    assert registry.assign("jdoe") == ("jdoe2", 2)


def test_r07_acceptance_example_johana_doe():
    # spec: a second "Johana Doe" after "John Doe" -> jdoe1@democompany.com
    registry = email_generator.EmailRegistry()
    first = registry.assign(email_generator.build_username("John Doe").username)
    second = registry.assign(email_generator.build_username("Johana Doe").username)
    assert email_generator.to_email(first.username) == "jdoe@democompany.com"
    assert email_generator.to_email(second.username) == "jdoe1@democompany.com"


def test_r07_counters_are_per_base():
    registry = email_generator.EmailRegistry()
    registry.assign("jdoe")
    registry.assign("jdoe")
    assert registry.assign("asmith") == ("asmith", 0)
    assert registry.assign("jdoe") == ("jdoe2", 2)


def test_r07_new_registry_starts_empty():
    # uniqueness is per run: a fresh registry has no memory of a previous one
    email_generator.EmailRegistry().assign("jdoe")
    assert email_generator.EmailRegistry().assign("jdoe") == ("jdoe", 0)


def test_r07_empty_base_rejected():
    with pytest.raises(ValueError):
        email_generator.EmailRegistry().assign("")


def test_nr02_case_insensitive():
    registry = email_generator.EmailRegistry()
    assert registry.assign("jdoe") == ("jdoe", 0)
    assert registry.assign("JDOE") == ("jdoe1", 1)
    assert registry.assign("Jdoe") == ("jdoe2", 2)


def test_nr02_different_bases_can_collide():
    registry = email_generator.EmailRegistry()
    assert registry.assign("jdoe") == ("jdoe", 0)
    assert registry.assign("jdoe1") == ("jdoe1", 0)  # different base, no collision yet
    assert registry.assign("jdoe") == ("jdoe2", 2)    # jdoe1 is taken by the other base


def test_cross_base_collision_order_a():
    registry = email_generator.EmailRegistry()
    assert registry.assign("jdoe") == ("jdoe", 0)
    assert registry.assign("jdoe") == ("jdoe1", 1) 


def test_cross_base_collision_order_b():
    registry = email_generator.EmailRegistry()
    assert registry.assign("jdoe1") == ("jdoe1", 0)
    assert registry.assign("jdoe") == ("jdoe", 0)
    assert registry.assign("jdoe") == ("jdoe2", 2)


def test_bulk_uniqueness():
    registry = email_generator.EmailRegistry()
    names = ["John Doe"]*50
    registry.assign("jdoe1")
    registry.assign("jdoe5")
    registry.assign("jdoe30")
    usernames = [email_generator.build_username(name).username for name in names]
    emails = [registry.assign(username).username for username in usernames]
    results = [registry.assign(b).username for b in ["jdoe1", "jdoe5", "jdoe30"]]
    results += [registry.assign(u).username for u in usernames]
    assert len(set(results)) == len(results)


def test_determinism():
    registry1 = email_generator.EmailRegistry()
    registry2 = email_generator.EmailRegistry()
    registry = email_generator.EmailRegistry()
    names = ["John Doe"]*5
    registry.assign("jdoe1")
    registry.assign("jdoe5")
    registry.assign("jdoe30")
    usernames = [email_generator.build_username(name).username for name in names]
    emails1 = [registry1.assign(username).username for username in usernames]
    emails2 = [registry2.assign(username).username for username in usernames]
    assert emails1 == emails2


def test_end_to_end_normalization():
    registry = email_generator.EmailRegistry()
    names = ["JANE DOE", "Jane Doe", "Jäne Döe", "JANE DOE"]
    usernames = [email_generator.build_username(name).username for name in names]
    emails = [registry.assign(username).username for username in usernames]
    assert emails == ["jdoe", "jdoe1", "jdoe2", "jdoe3"]


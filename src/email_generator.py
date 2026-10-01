import re
import unicodedata
from typing import NamedTuple

from src.config import EMAIL_DOMAIN

# R06: matched case-insensitively, trailing dot optional (Mr = Mr. = MR.).
# "Sr" is in both sets: Señor as a prefix, Senior as a suffix — position decides.
PREFIXES = frozenset({"mr", "mrs", "ms", "miss", "dr", "prof", "sr"})
SUFFIXES = frozenset({"jr", "sr", "ii", "iii", "iv", "v"})

_NOT_ALLOWED = re.compile(r"[^a-z0-9]")


class ParsedName(NamedTuple):
    first: str
    last: str
    ignored: tuple[str, ...]  # categories only ("prefix", "suffix", "initial"), never the tokens


class UsernameResult(NamedTuple):
    username: str
    ignored: tuple[str, ...]


def parse_name(full_name: str) -> ParsedName:
    """R06: drop leading prefixes, trailing suffixes and single-letter initials.

    First remaining word = first name, last remaining word = last name.
    Raises ValueError if fewer than two words remain.
    """
    tokens = full_name.split()
    ignored = []

    while tokens and _key(tokens[0]) in PREFIXES:
        tokens.pop(0)
        ignored.append("prefix")
    while tokens and _key(tokens[-1]) in SUFFIXES:
        tokens.pop()
        ignored.append("suffix")

    kept = [t for t in tokens if not _is_initial(t)]
    if len(kept) < len(tokens):
        ignored.append("initial")

    if len(kept) < 2:
        raise ValueError("name has fewer than two usable words")
    return ParsedName(kept[0], kept[-1], tuple(dict.fromkeys(ignored)))


def normalize(token: str) -> str:
    """R09: transliterate -> lowercase -> strip everything outside [a-z0-9].

    Order matters: stripping first would turn "Núñez" into "nez".
    NFKD splits accented letters into base letter + combining mark (dropped by the
    ASCII encode) and folds compatibility forms (fullwidth "Ｊ" -> "J").
    Letters with no decomposition (ł, ø, ß, Cyrillic) are stripped — see intent.md.
    """
    ascii_text = unicodedata.normalize("NFKD", token).encode("ascii", "ignore").decode("ascii")
    return _NOT_ALLOWED.sub("", ascii_text.lower())


def build_username(full_name: str) -> UsernameResult:
    """Parse -> normalize each part -> initial of first + full last.

    Raises ValueError if parsing fails (R06) or a part normalizes to "" (D01).
    """
    parsed = parse_name(full_name)
    first = normalize(parsed.first)
    last = normalize(parsed.last)
    if not first or not last:
        raise ValueError("name has no usable characters after normalization")
    return UsernameResult(f"{first[0]}{last}", parsed.ignored)


class Assignment(NamedTuple):
    username: str
    suffix: int  # 0 = no collision; n = the n-th duplicate of this base got suffix n


class EmailRegistry:
    """R07: hand out unique usernames for one run — jdoe, jdoe1, jdoe2, ...

    Per-run only (non-goal: no check against already-issued accounts).
    Checks every candidate against *all* usernames handed out so far, not just
    the per-base counter: a different base can produce the same string
    (base "jdoe" + suffix 1 == base "jdoe1"), and two contractors must never
    share an identity.
    """

    def __init__(self) -> None:
        self._taken: set[str] = set()
        self._next_suffix: dict[str, int] = {}

    def assign(self, base: str) -> Assignment:
        base = base.casefold()
        if not base:
            raise ValueError("cannot assign an empty username")
        suffix = self._next_suffix.get(base, 0)
        candidate = base if suffix == 0 else f"{base}{suffix}"
        while candidate in self._taken:
            suffix += 1
            candidate = f"{base}{suffix}"
        self._next_suffix[base] = suffix + 1
        self._taken.add(candidate)
        return Assignment(candidate, suffix)


def to_email(username: str) -> str:
    """Convert a username to an email address."""
    return f"{username}@{EMAIL_DOMAIN}"


def _key(token: str) -> str:
    return token.rstrip(".").casefold()


def _is_initial(token: str) -> bool:
    # A single *Latin* letter ("A", "É."). A one-character CJK name part like "李"
    # is a real name, not an initial — it normalizes to "" and is handled by D01.
    core = token.rstrip(".")
    return len(core) == 1 and core.isalpha() and len(normalize(core)) == 1

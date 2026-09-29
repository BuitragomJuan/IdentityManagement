from src.config import EMAIL_DOMAIN


def parse_name(name):
    """Parse a name into first and last name components."""
    parts = name.split()
    if len(parts) < 2:
        raise ValueError("Name must contain at least first and last name")
    first_name = parts[0]
    last_name = parts[-1]

    return first_name, last_name


def normalize(name):
    """Normalize a name by converting it to lowercase."""
    return name.lower()


def build_username(name):
    """Build a username from a name."""
    first_name, last_name = parse_name(name)
    first_name = normalize(first_name)
    last_name = normalize(last_name)
    username = f"{first_name[0]}{last_name}"
    return username


def to_email(username):
    """Convert a username to an email address."""
    return f"{username}@{EMAIL_DOMAIN}"

from dataclasses import dataclass


@dataclass (frozen=True)
class Contractor:
    id: int
    name: str
    phone: str
    email: str
    company: str
    city: str
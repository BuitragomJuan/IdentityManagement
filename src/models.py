from dataclasses import dataclass


# Validated contractor, built only by validation.validate_record()
@dataclass (frozen=True)
class Contractor:
    id: int
    name: str
    phone: str
    email: str
    company: str
    city: str


# Row of the outgoing CSV file containing external contractors
@dataclass (frozen=True)
class Row:
    contractor: Contractor
    corporate_email: str
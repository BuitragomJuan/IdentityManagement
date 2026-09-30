from src.models import Contractor


class InvalidRecordError(Exception):
    """
    Error class for records that are invalid
    """
    def __init__(self, record_id: int|None, reason: str):
        super().__init__(f"record {record_id}: {reason}")
        self.record_id = record_id
        self.reason = reason



def validate_record(raw_record)->Contractor:
    """
    Validate a raw record and if valid create it's Contractor object
    """
    if not isinstance(raw_record,dict):
        raise InvalidRecordError(None,"record not of dictionary type")


    record_id = _require(raw_record,"id",int,None)


    if isinstance(record_id,bool):
        raise InvalidRecordError(None,"id can't be a boolean value")

    
    name = _require(raw_record, "name",str,record_id)
    phone = _require(raw_record, "phone",str, record_id)
    email = _require(raw_record, "email",str, record_id)
    company = _require(raw_record, "company",dict,record_id)
    company_name = _require(company, "name",str, record_id) # reason says "name", not "company.name" — see intent.md known limitations
    address = _require(raw_record,"address",dict,record_id)
    city = _require(address,"city",str,record_id)

    contractor = Contractor(record_id,
                            name,
                            phone,
                            email,
                            company_name,
                            city
                            )

    return contractor
        

def _require(data: dict, key: str, expected_type, record_id)->object:
    """
    Require a key to be present in a dict.
    """
    if key not in data:
        raise InvalidRecordError(record_id, f"missing required key: {key}")
    elif not isinstance(data[key],expected_type):
        raise InvalidRecordError(record_id,f"wrong type for {key}, expected type: {expected_type.__name__}")
    return data[key]
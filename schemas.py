from pydantic import BaseModel
from datetime import date, datetime
from typing import Optional
from decimal import Decimal
#===========================================================

""" USER MANAGEMENT:
    Login || Restore member [TBD] || Confirm email [TBD]
"""
class Req_LogIn_Username(BaseModel):
    username: str
    password: str

""" USER MANAGEMENT:
    Members
"""
class Resp_Members_Inst(BaseModel):
    card_id: str
    name: str
    surname: str
    email: str
    phone_number: Optional[str]
    date_of_birth: Optional[date]
    registration_date: date
    account_type: int
    privileges: Optional[str]
    last_checkin_success: Optional[bool]
    last_checkin_datetime: Optional[datetime]
    token: Optional[str]
    activated: bool

    class Config:
        from_attributes = True

class Req_Members_Add(BaseModel):
    name: str
    surname: str
    email: str
    phone_number: Optional[str]
    date_of_birth: Optional[date]
    account_type: int
    send_welcome_email: Optional[bool] = True
    send_welcome_mms: Optional[bool]
#===========================================================

""" EXTERNAL PROVIDERS
    (External payment methods)
"""
class Req_Create_ExternalProviders(BaseModel):
    name: str
    description: Optional[str]
    is_partial_payment: bool
    partial_payment: Optional[Decimal]

class Resp_Instance_ExternalProviders(BaseModel):
    id: int
    name: str
    description: Optional[str]
    is_partial_payment: bool
    partial_payment: Optional[Decimal] = None
    is_deleted: bool

    class Config:
        from_attributes = True

class Req_Update_ExternalProviders(BaseModel):
    id: int
    name: Optional[str]
    description: Optional[str]
    is_partial_payment: bool
    partial_payment: Optional[Decimal]

""" PASS TYPES
"""
class Req_PassTypes_Create(BaseModel):
    name: str
    description: Optional[str]
    price: Decimal
    validity_days: Optional[int]
    maximum_entries: Optional[int]
    requires_external_auth: bool
    external_provider_name: Optional[str]
    external_provider_id: Optional[int]
    is_ext_event_pass: bool
    ext_event_code: Optional[str]

class Resp_PassTypes_Inst(BaseModel):
    id: int
    name: str
    description: Optional[str]
    price: Decimal
    validity_days: Optional[int]
    maximum_entries: Optional[int]
    requires_external_auth: bool
    external_provider_name: Optional[str]
    external_provider_id: Optional[int]
    is_ext_event_pass: bool
    ext_event_code: Optional[str]
    is_deleted: bool
    delete_date: Optional[datetime]

    class Config:
        from_attributes = True

class Req_PassTypes_Update(BaseModel):
    id: int
    name: str
    description: Optional[str]
    price: Decimal
    validity_days: Optional[int]
    maximum_entries: Optional[int]
    requires_external_auth: bool
    external_provider_name: Optional[str]
    external_provider_id: Optional[int]
    is_ext_event_pass: bool
    ext_event_code: Optional[str]

""" MEMBER PASS
"""
class Req_MemberPass_Add(BaseModel):
    member_card_id: str
    pass_type_id: int

class Resp_MemberPass_Inst(BaseModel):
    id: int
    member_card_id: str
    pass_type_id: int
    pass_type_name: str
    purchase_date: date
    expiration_date: Optional[date]
    entries_left: Optional[int]
    requires_external_auth: bool
    external_provider_id: Optional[int]
    external_provider_name: Optional[str]
    is_ext_event_pass: bool
    ext_event_code: Optional[str]
    status: Optional[str]
    is_closed: bool

    class Config:
        from_attributes = True
#===========================================================

""" LOGS:
    CheckIns
"""
class Req_CheckIn_Add(BaseModel):
    validated_by_card_id: Optional[str]
    external_provider_id: Optional[int]
    member_card_id: str

class Resp_ChecIn_Inst(BaseModel):
    id: int
    validated_by_card_id: Optional[str]
    validated_by_name: Optional[str]
    validated_by_surnamename: Optional[str]
    hall: Optional[str]
    member_pass_id: Optional[int]
    pass_id: Optional[int]
    pass_name: Optional[str]
    is_ext_event_pass: Optional[bool]
    ext_event_code: Optional[str]
    external_provider_id: Optional[int]
    external_provider_name: Optional[str]
    member_card_id: str
    member_name: str
    member_surname: str
    date_time: datetime
    is_successful: bool
    rejected_reason: Optional[str]

    class Config:
        from_attributes = True
#===========================================================

""" STATISTICS
"""
class Req_Statistics_Admin_CheckInsByType_All(BaseModel):
    """ Used to request more-or-less detailed data about all checkins made by
        all instructors 
    """
    date_time_min: datetime
    date_time_max: datetime

class Resp_Statistics_Admin_CheckInsByType(BaseModel):
    """ Used to represent sorted response of how many entries did an instructor
        in a period of time. 
    """
    name: str = ""
    surname: str = ""
    entries_pass: int = 0
    entries_pzu: int = 0
    entries_medicover: int = 0
    entries_multisport: int = 0
    entries_other: int = 0
    entries_total: int = 0
    
    class Config:
            from_attributes = True
#===========================================================

from pydantic import BaseModel
from datetime import date, datetime
from typing import Optional
#===========================================================

""" REQUEST SCHEMES """

class CheckInRequest(BaseModel):
    """ Data needed to perform a checkin operation.
    """

    card_id: str
    hall: Optional[str] = "Impakt"
    payment_by_externa_tool: Optional[bool] = False

class CheckInLogFilters(BaseModel):
    control_card_id: Optional[str] = None
    control_name: Optional[str] = None
    control_surname: Optional[str] = None
    hall: Optional[str] = None

    # Information about the member
    card_id: Optional[str] = None
    name: Optional[str] = None
    surname: Optional[str] = None

    # Checkin date & time + [additional information ?]
    date_time_min: Optional[datetime] = None
    date_time_max: Optional[datetime] = None

class MemberUpdateRequest(BaseModel):
    """ Data to be provided during member information update. 
    """

    card_id: str

    name: Optional[str] = None
    surname: Optional[str] = None
    email: Optional[str] = None
    phone_number: Optional[str] = None
    date_of_birth: Optional[date] = None

    pass_type: Optional[int] = None
    account_type: Optional[int] = None
    entrances_left: Optional[int] = None
    expiration_date: Optional[date] = None

class MemberAddRequest(BaseModel):
    name: str
    surname: str
    email: str
    phone_number: Optional[str]
    date_of_birth: Optional[date]
    account_type: Optional[int]
#===========================================================

""" RESPONSE SCHEMES """

class LogInResponse(BaseModel):
    """ Data to return when user LogIn
    """

    card_id: str
    name: str
    surname: str
    email: str
    phone_number: Optional[str]
    date_of_birth: Optional[date]
    account_type: int

    class Config:
        from_attributes = True

class CheckInLogResponse(BaseModel):


    class Config:
        from_attributes = True
#===========================================================

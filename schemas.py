from pydantic import BaseModel
from datetime import date, datetime
from typing import Optional
#===========================================================

""" REQUEST SCHEMES """

class MemberInfoReq(BaseModel):
    card_id: str

class CheckInRequest(BaseModel):
    """ Data needed to perform a checkin operation.
    """

    card_id: str
    hall: Optional[str] = "Impakt"
    payment_by_externa_tool: Optional[bool] = False

class CheckInLogFilters(BaseModel):
    # Maximum amount of data to get
    limit: int

    # Data about person who scanned and where
    control_name: Optional[str] = None
    control_surname: Optional[str] = None
    hall: Optional[str] = None

    # Information about the member
    card_id: Optional[str] = None
    name: Optional[str] = None
    surname: Optional[str] = None

    # Checkin date & time
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

class MemberInfoResp(BaseModel):
    """ Information about the member returned on request
    """

    card_id: str
    name: str
    surname: str
    email: str
    phone_number: Optional[str]
    date_of_birth: Optional[date]
    account_type: int

class CheckInLogResponse(BaseModel):
    # Data about person who scanned and where
    control_name: str
    control_surname: str
    hall: str

    # Information about the member
    card_id: str
    name: str
    surname: str

    # Checkin date_time
    date_time: datetime
    class Config:
        from_attributes = True
#===========================================================

""" Do not remember what was it
"""


#===========================================================


""" LOGIN
"""
class Req_LogIn(BaseModel):
    """ Data to login into account
    """

    username: str
    password: str

class Resp_LogIn(BaseModel):
    """ Data to return when user LogIn
    """

    card_id: str
    name: str
    surname: str
    email: str
    account_type: int

    phone_number: Optional[str]
    date_of_birth: Optional[date]
    token: Optional[str]
    activated: Optional[bool]

    class Config:
        from_attributes = True
    
class Exception_LogIn(BaseModel):
    """ [TBD] - tested in the future
    """
    detail: str

""" ADD || REGISTER NEW MEMBER
"""

class Req_AddNewMember(BaseModel):
    """ Data to return when user LogIn
    """

    name: str
    surname: str
    email: str
    account_type: int

    phone_number: Optional[str]
    date_of_birth: Optional[date]

    send_welcome_email: Optional[bool] = True  # Decides if welcome email will be sent to a new member
    send_welcome_mms: Optional[bool] = False   # Decides if welcome MMS will be sent to a new member [TBD]

class Resp_AddNewMember(BaseModel):
    status: str = "OK"
    message: str = "New member was created"

    card_id: str


    class Config:
        from_attributes = True
#===========================================================

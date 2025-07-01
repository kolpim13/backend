from pydantic import BaseModel
from datetime import date, datetime
from typing import Optional
#===========================================================

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
#===========================================================

""" ADD || REGISTER NEW MEMBER
"""
class Req_AddNewMember(BaseModel):
    """ Data to provide on add member
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
    """ [Not used at the moment]
        Response when member was added
    """
    status: str = "OK"
    message: str = "New member was created"

    card_id: str
    
    class Config:
        from_attributes = True

class Req_ConfirmMail(BaseModel):
    pass
class Resp_ConfirmMail(BaseModel):
    pass
    class Config:
        from_attributes = True

#===========================================================

""" MEMBER: INFO, UPDATE, ETC
"""
class Resp_MemberInfo(BaseModel):
    """ Represents data about the user requested from the data base
    """
    name: str
    surname: str
    email: str
    phone_number: Optional[str]
    date_of_birth: Optional[date]

    account_type: int
    pass_type: int
    entrances_left: int
    expiration_date: Optional[date]

    last_check_in: Optional[datetime]

    class Config:
            from_attributes = True

class Req_Member_UpdatePass(BaseModel):
    """ Allows to update information about member`s pass  
    """
    card_id: str
    pass_type: int

class Resp_Member_UpdatePass(BaseModel):
    pass_type: int
    entrances_left: int
    expiration_date: date
    
    class Config:
            from_attributes = True
#===========================================================

""" CHECKIN
"""
class Req_Checkin(BaseModel):
    """ Data to register checkin

    card_id - member`s identification
    hall    - place where class was
    external_payment: was member pay for this class.
    pass_type - what type of pass was used to enter the class
        None -> internall (Previousely bought) pass was used
        othervise -> some external payment system was used. 
    """

    card_id: str
    hall: Optional[str] = "Impakt"
    external_payment: Optional[bool] = False
    pass_type: Optional[int] = None
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

from sqlalchemy import Column, Integer, Boolean, String, Date, DateTime
from database import Base, BaseEntrances

class Member(Base):
    """_summary_

    Args:
        Base (_type_): _description_
    """

    # The file name it will be created
    __tablename__ = "members"

    # ID of the row
    id = Column(Integer, primary_key=True, unique=True)

    # CARD ID: Unique value for every account [bounded to a physical card].
    card_id = Column(String, unique=True)

    # Main information about user/member
    name = Column(String)
    surname = Column(String)
    email = Column(String, unique=True)
    phone_number = Column(String)
    date_of_birth = Column(Date, nullable=True)

    # Preferences (To Be Added in the future)
    # How did you know about Impakt
    # Preferences: leader / follower / both
    # ...

    # Technical information
    pass_type = Column(Integer)
    account_type = Column(Integer)
    entrances_left = Column(Integer)
    expiration_date = Column(Date)
    register_date = Column(Date)

    # Store last checkIn time separetly --> will be needed for some operations
    last_check_in = Column(DateTime, nullable=True)

    # Data to log in
    username = Column(String, unique=True)
    password = Column(String)

    # Is Card activated - probably will be needed in future.
    activated = Column(Boolean)

class CheckInLog(BaseEntrances):
    """ Database to store all entrances log """

    __tablename__ = "entrance_log"

    id = Column(Integer, primary_key=True, unique=True)

    # Information about who did scan
    control_card_id = Column(String)
    control_name = Column(String)
    control_surname = Column(String)
    hall = Column(Integer)

    # Information about the member
    card_id = Column(String)
    name = Column(String)
    surname = Column(String)

    # Checkin date & time + [additional information ?]
    date_time = Column(DateTime)

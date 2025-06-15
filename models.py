from sqlalchemy import Column, Integer, Boolean, String, Date, DateTime
from database import Base_Members, Base_Checkins

class Member(Base_Members):
    """_summary_

    Args:
        Base_Members (_type_): _description_
    """

    # The file name it will be created
    __tablename__ = "members"

    # ID of the row
    id = Column(Integer, primary_key=True, unique=True)

    # CARD ID: Unique value for every account [bounded to a physical card].
    card_id = Column(String, unique=True)

    # Main information about user/member
    name = Column(String, nullable=True)
    surname = Column(String, nullable=True)
    email = Column(String, unique=True)
    phone_number = Column(String, nullable=True)
    date_of_birth = Column(Date, nullable=True)

    # Preferences (To Be Added in the future)
    # How did you know about Impakt
    # Preferences: leader / follower / both
    # ...

    # Technical information
    account_type = Column(Integer)
    pass_type = Column(Integer)
    entrances_left = Column(Integer)
    expiration_date = Column(Date, nullable=True)
    register_date = Column(Date)

    # Store last checkIn time separetly --> will be needed for some operations
    last_check_in = Column(DateTime, nullable=True)

    # Data to log in
    username = Column(String, nullable=False, unique=True)  # Rename on login
    password_hash = Column(String, nullable=False)
    token = Column(String, unique=True, nullable=True)

    # Is Card activated - probably will be needed in future.
    activated = Column(Boolean)

class CheckInEntry(Base_Checkins):
    """ Database to store all entrances log """

    __tablename__ = "CheckInHistory"

    id = Column(Integer, primary_key=True, unique=True)

    # Information about who did scan
    instructor_card_id = Column(String)    # To be deleted? [or at least masked]
    instructor_name = Column(String)
    instructor_surname = Column(String)
    hall = Column(String)

    # Information about the member
    card_id = Column(String)
    name = Column(String)
    surname = Column(String)

    # Checkin date & time + [additional information ?]
    date_time = Column(DateTime)

    # Paayment & Pass details
    # Pass type member posses on the purchase moment (NO / YES / MEDICOVER / etc.)
    # How many entries left after payment was done
    # 


# class Survey():
#     """ For future use [Collect data from members through application / site]. 
#     """
#     pass

# class EventCalendar():
#     """ [TBD] To store / modify information about classes schedule.
#         Additionally: Schedule private lesson in of two halls. 
#     """
#     pass
    
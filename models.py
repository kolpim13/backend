from sqlalchemy import Column, ForeignKey, Float, Integer, Boolean, Numeric, String, Date, DateTime
from sqlalchemy.orm import relationship
from database import Base_Members, Base_Checkins

""" MAIN TABLES:
    Information about Members, Pass types, etc.
"""
class Member(Base_Members):
    """_summary_

    Args:
        privileges: str (json / dict stored as string) -> To store privilages concrete user have [TBD].
        activated: bool -> was account activated [TBD].
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
    phone_number = Column(String, nullable=True)
    date_of_birth = Column(Date, nullable=True)
    image_path = Column(String, nullable=True)
    registration_date = Column(Date)

    # Technical information
    account_type = Column(Integer, nullable=False)
    privileges = Column(String, nullable=True)
    
    # Store last checkIn time separetly --> will be needed for some operations
    last_check_in = Column(DateTime, nullable=True)

    # Data to log in && operate
    username = Column(String, nullable=False, unique=True)  # Rename on login
    password_hash = Column(String, nullable=False)
    token = Column(String, unique=True, nullable=True)

    # [TBD]
    activated = Column(Boolean)

    # Links to relative tables
    member_passes = relationship("MemberPass", back_populates="member")

class PassType(Base_Members):
    """ Table stores every PassType possible.

    Args:
        validity_days: int -> Days form date.today() before Pass will be expired.
            "Null" - to set unlimited time
        maximum_entries: int -> How many entries can be done via this Pass.
            "Null" - to emulate infinite amount (Unlimited Pass).
    """
    
    __tablename__ = "pass_types"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)

    price = Column(Numeric(5, 2), nullable=False)
    validity_days = Column(Integer, nullable=True)
    maximum_entries = Column(Integer, nullable=True) 

    # For external payment systems (if used)
    requires_external_auth = Column(Boolean, default=False)
    external_provider_name = Column(String, nullable=True)
    external_provider_id = Column(Integer, ForeignKey("external_providers.id"), nullable=True)

    # For external events (Bristol, events, concerts, etc.).
    is_ext_event_pass = Column(Boolean, nullable=False, default=False)
    ext_event_code = Column(String, nullable=True)

    # Delete information
    is_deleted = Column(Boolean, default=False)
    delete_date = Column(DateTime, nullable=True)

    # Links to relative tables
    external_provider = relationship("ExternalProvider")
    member_passes = relationship("MemberPass", back_populates="pass_type")

class ExternalProvider(Base_Members):
    """ Serves to store all providers of the external payment systems

    Args:
        name: str -> Name of the external provider (e.g. Multisport, Medicover).
        description: str -> Description of the provider.
        image_path: str -> Path to the picture that represents the provider.
            Stored as Path in DB and as an image on local machine - easy to upload on frontend
            [Not used at the moment]

        partial_payment: numeric -> Defines if user needs to pay additionally for this ExternalProvider
            None - no payment needed.
            Every time entrance is bougth it should be payed exact amount

        is_deleted: bool -> Was Provider "deleted". If yes, can not be used.
        delete_date: datetime -> For historical print.
    """

    __tablename__ = "external_providers"

    id = Column(Integer, primary_key=True)

    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    image_path = Column(String, nullable=True)

    is_partial_payment = Column(Boolean, default=False)
    partial_payment = Column(Numeric(5, 2), nullable=True)

    is_deleted = Column(Boolean, default=False)
    delete_date = Column(DateTime, nullable=True)

class MemberPass(Base_Members):
    """ Table to store all passess of all users  ever were bought

    Args:
        status: str -> To write here all events that were not predicted
        is_closed: bool -> Used to force Pass for the member be closed regardless of the expiration date or entries left
        is_ext_event_pass: bool -> To distinguish regular passes and special events (future use)
        ext_event_code: bool -> Unique code to distinguish events between each other
    """

    __tablename__ = "member_passes"

    id = Column(Integer, primary_key=True)

    # Info about current state of the Pass
    purchase_date = Column(Date, nullable=False)
    expiration_date = Column(Date, nullable=True)
    entries_left = Column(Integer, nullable=True)

    # For external payment systems (if used)
    requires_external_auth = Column(Boolean, default=False)
    external_provider_id = Column(Integer, ForeignKey("external_providers.id"), nullable=True)

    # For external events (Bristol, events, concerts, etc.).
    is_ext_event_pass = Column(Boolean, nullable=False, default=False)
    ext_event_code = Column(String, nullable=True)

    # Additional fields (Not in use right now)
    status = Column(String, nullable=True)
    is_closed = Column(Boolean, nullable=False, default=False)

    # Relative fields
    member_id = Column(Integer, ForeignKey("members.id"))
    pass_type_id = Column(Integer, ForeignKey("pass_types.id"))

    # Links to relative tables
    external_provider = relationship("ExternalProvider")
    member = relationship("Member", back_populates="member_passes")
    pass_type = relationship("PassType", back_populates="member_passes")

class MemberSurvey_Test(Base_Members):
    """ Place holder for the survey about smth (most probably an application among instructors).
    """

    __tablename__ = "survey_test"

    id = Column(Integer, primary_key=True)

""" LOG TABLES:
    Entry history, Login logs, etc.
"""
class CheckInEntry(Base_Checkins):
    """ Database to store all entrances log """

    __tablename__ = "CheckInHistory"

    id = Column(Integer, primary_key=True, unique=True)

    # Information about who did scan
    instructor_card_id = Column(String)    # To be deleted? [or at least masked]
    instructor_name = Column(String)
    instructor_surname = Column(String)
    hall = Column(String, nullable=True)

    # Information about the member
    card_id = Column(String)
    name = Column(String)
    surname = Column(String)

    # Checkin date & time + [additional information ?]
    date_time = Column(DateTime)

    # Paayment & Pass details
    pass_type = Column(Integer)
    entrances_left = Column(Integer)
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
    
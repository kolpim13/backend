from datetime import datetime, timezone

from sqlalchemy import Column, ForeignKey, Integer, Boolean, Numeric, String, Date, DateTime
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
    name                    = Column(String, nullable=False)
    surname                 = Column(String, nullable=False)
    email                   = Column(String, unique=True, nullable=False)
    phone_number            = Column(String, nullable=True)
    date_of_birth           = Column(Date, nullable=True)
    image_path              = Column(String, nullable=True)
    registration_date       = Column(Date, nullable=False)

    # Technical information
    account_type            = Column(Integer, nullable=False)
    privileges              = Column(String, nullable=True)
    
    # Store last checkIn time separetly --> will be needed for some operations
    last_checkin_success    = Column(Boolean, nullable=True)
    last_checkin_datetime   = Column(DateTime, nullable=True)

    # Data to log in && operate
    username                = Column(String, nullable=False, unique=True)  # Rename on login
    password_hash           = Column(String, nullable=False)
    token                   = Column(String, unique=True, nullable=True)

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

    # payment_from_provider = Column(Numeric, default=0) # To be extended in the future

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
    external_provider_name = Column(String, nullable=True)

    # For external events (Bristol, events, concerts, etc.).
    is_ext_event_pass = Column(Boolean, nullable=False, default=False)
    ext_event_code = Column(String, nullable=True)

    # Additional fields (Not in use right now)
    status = Column(String, nullable=True)
    is_closed = Column(Boolean, nullable=False, default=False)

    # Relative fields
    member_card_id = Column(Integer, ForeignKey("members.card_id"))
    pass_type_id = Column(Integer, ForeignKey("pass_types.id"))
    pass_type_name = Column(String, nullable=False)

    # Links to relative tables
    external_provider = relationship("ExternalProvider")
    pass_type = relationship("PassType", back_populates="member_passes")
    member = relationship("Member", back_populates="member_passes")

class MemberSurvey_Test(Base_Members):
    """ Place holder for the survey about smth (most probably an application among instructors).
    """

    __tablename__ = "survey_test"

    id = Column(Integer, primary_key=True)

""" LOG TABLES:
    Entry history, Login logs, etc.
"""
class CheckIn(Base_Checkins):
    """_summary_

    Columns:
        validated_by_card_id: str -> Card ID of a person who did scann. [None] if it was self scanned
        validated_by_name: str -> Name of a person who did scann
        validated_by_surnamename: str -> Surname of a person who did scan
        hall: str -> Place it was scanned in.

        member_pass_id: int -> MemberPass was used to checkin. [None] if no pass was used.
            Serves to "bind" current row to corresponding row in MemberPass table
        member_pass_name: str -> ...
        is_ext_event_pass: bool -> Was this entry dedicated for the special event
        ext_event_code: str -> Code of the special event. [None] if it was usual event.
        external_provider_id: int ->  ExternalProvider was used to checkin. [None] if no pass was used.
            Serves to "bind" current row to corresponding row in ExternalProvider table
        external_provider_name: str -> ...

        member_card_id: str -> Card ID of a member
        member_name: str -> member`s name
        member_surname: str -> member`s surname

        date_time: datetime -> date and time the member tried to checkin.

        is_successful: bool -> was entry accepted[True] or rejected[False]
        rejected_reasones: str -> Description why entry was rejected

    Returns:
        _type_: _description_
    """

    __tablename__ = "checkins"

    id = Column(Integer, primary_key=True, unique=True)

    # Information about who did scan and where (the validator)
    validated_by_card_id        = Column(String, nullable=True, index=True)
    validated_by_name           = Column(String, nullable=True)
    validated_by_surnamename    = Column(String, nullable=True)
    hall                        = Column(String, nullable=True) # Not mused at the moment

    # Pass and ExternalProvider information
    member_pass_id              = Column(Integer, nullable=True)
    pass_id                     = Column(Integer, nullable=True, index=True)
    pass_name                   = Column(String, nullable=True)
    is_ext_event_pass           = Column(Boolean, nullable=True)
    ext_event_code              = Column(String, nullable=True)
    external_provider_id        = Column(Integer, nullable=True, index=True)
    external_provider_name      = Column(String, nullable=True)

    # Information about the member
    member_card_id              = Column(String, nullable=False, index=True)
    member_name                 = Column(String, nullable=False)
    member_surname              = Column(String, nullable=False)

    # Checkin date & time + [additional information ?]
    date_time                   = Column(DateTime, nullable=False, index=True,
                                         default=datetime.now(timezone.utc))
    
    # Was entrance success --> if not why.
    is_successful               = Column(Boolean, nullable=False, default=True)
    rejected_reason             = Column(String, nullable=True)

    def __repr__(self):
        return "Entrance for {name} {surname} validated by {validator_name} {validator_surname}, at {time} was {is_success}".format(
            name=self.member_name, surname=self.member_surname,
            validator_name=self.validated_by_name, validator_surname=self.validated_by_surnamename,
            time=self.checkin_time, is_success="successful" if self.is_successful == True else "unsuccessful",
        )

# class Survey():
#     """ For future use [Collect data from members through application / site]. 
#     """
#     pass

# class EventCalendar():
#     """ [TBD] To store / modify information about classes schedule.
#         Additionally: Schedule private lesson in of two halls. 
#     """
#     pass
    
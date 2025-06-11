import os
from typing import Optional
import dotenv
import smtplib
from email.message import EmailMessage
from fastapi import FastAPI, Depends, HTTPException, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import date, datetime, timedelta

from models import Member, CheckInEntry
from enum import Enum
from pathlib import Path

from schemas import CheckInLogResponse, CheckInLogFilters, CheckInRequest, LogInResponse, MemberAddRequest, MemberInfoReq, MemberInfoResp, MemberUpdateRequest

import project_utils as utils
from project_utils import PassType, AccountType
#===========================================================

""" START THE APPLICATION """

# Load environment variables
dotenv.load_dotenv()

# Prepare environment for work
utils.check_create_paths()
utils.databases_init_tables()

# FastAPI application to run
app = FastAPI(title="Dance School Backend")

# Load Impakt logo once on the beginning
# impakt_logo = PIL.Image.open("impakt_logo.jpg")
# impakt_logo = impakt_logo.resize((75, 100))
#===========================================================

""" DATA TYPES """
class MemberIn(BaseModel):
    """_summary_

    Args:
        BaseModel (_type_): _description_
    """

    # CARD ID: Unique value for every account [bounded to a physical card].
    card_id: str

    # Main information about user/member
    name: str
    surname: str
    email: str
    phone_number: str
    date_of_birth: date

    # Preferences (To Be Added in the future)
    # How did you know about Impakt
    # Preferences: leader / follower / both
    # ...

    # Technical information
    pass_type: int
    account_type: int
    entrances_left: int
    expiration_date: date
    register_date: date

    # Store last checkIn time separetly --> will be needed for some operations
    last_check_in: date

    # Data to log in
    username: str
    password: str

    # Is Card activated - probably will be needed in future.
    activated: bool

class LogIn(BaseModel):
    """ Data needed to log into user account """

    username: str
    password: str
#===========================================================

""" UTILS """

def dict_to_Member(member_dict: dict) -> Member:
    def safe_enum_value_convert(val):
        return int(val.value) if isinstance(val, Enum) else val
    
    # Probably will be needed in future
    member = Member(
        **{**member_dict,
            "account_type": safe_enum_value_convert(member_dict["account_type"]),
            "pass_type": safe_enum_value_convert(member_dict["pass_type"]),
        }
    )
    return member

def get_member_based_on_default_value(member: dict, as_member: bool = False) -> dict:
    # "date_of_birth": date.strftime(date(2050, 1, 1), "%Y-%m-%d"),
    # "expiration_date": date.strftime(date.today(), "%Y-%m-%d"),
    # "register_date": date.strftime(date.today(), "%Y-%m-%d"),
    # "last_check_in": datetime.strftime(datetime.now(), "%Y-%m-%d %H:%M:%S"),

    member_default = {
        "card_id": None,

        "name": "Name",
        "surname": "Surname",
        "email": "mail@gmail.com",
        "phone_number": None,
        
        "date_of_birth": None, #date.min,

        "pass_type": int(PassType.PASS_NO.value),
        "account_type": int(AccountType.MEMBER.value),
        "entrances_left": 0,
        "expiration_date": date.today() + timedelta(weeks=5),
        "register_date": date.today(),

        "last_check_in": None,

        "username": utils.get_random_string(12),
        "password": utils.get_random_string(12),
       
        "activated": False,
    }
    member = {**member_default, **member}
    if as_member:
        member = dict_to_Member(member)
    # Add some validation here (?)
    # ...

    return member
#===========================================================

""" Database related """

def get_member_by_card_id(db: Session, card_id: str) -> Member:
    member: Member = db.query(Member).filter(Member.card_id == card_id).first()
    return member

def get_member_by_username(db: Session, username: str) -> Member:
    member: Member = db.query(Member).filter(Member.username == username).first()
    return member

def check_create_root(db: Session) -> bool:
    """ Function should be on the very beginning of the execution to check if there is a "root: user present
        If it does not --> create one with default username and password  
    """

    # Try to get root user from the database
    root = get_member_by_username(db, "root")

    # Root does not exists --> create default one
    if root is None:
        print("No root user was found in the database --> start of creating a new one.")

        root_values = {
            "name": os.getenv("ROOT_NAME"),
            "surname": os.getenv("ROOT_SURNAME"),
            "email": os.getenv("ROOT_EMAIL"),
            "username": os.getenv("ROOT_DEFAULT_LOGIN"),
            "password": os.getenv("ROOT_DEFAULT_PASS"),
            "account_type": AccountType.ADMIN
        }
        root: Member = get_member_based_on_default_value(root_values, as_member=True)

        # Create QR Code value --> add it to root
        qr_value: str = utils.generate_qr_code_value(db)
        root.card_id = qr_value

        # Add it to a database
        db.add(root)
        db.commit()

        # Generate qr code
        qr_code: Path = utils.generate_qr_code(qr_value, 
                                         root.name, root.surname)

        # Send QR via mail on self email address
        utils.send_welcome_email(os.getenv("ROOT_EMAIL"), 
                           root.name, root.surname,
                           root.username, root.password,
                           qr_code)
        print("4")

        print("Root user was created with default values. Change it`s password and card ID as soon as possible!")
        return True
    
    return False
#===========================================================

""" FastAPI """

@app.post("/members/check_create_root")
def api_check_create_root(db: Session = Depends(utils.get_db_members)) -> JSONResponse:
    if check_create_root(db) is True:
        return JSONResponse(status_code=201, content={"status": "OK", "message": "Default root user created"})
    return JSONResponse(status_code=200, content={"status": "OK", "message": "Root already exists"})

@app.post("/members/{card_id}/add")
def members_add(card_id: str,
               new_member: MemberAddRequest, db: Session = Depends(utils.get_db_members)):
    
    """ Add a new member by administrator """
    
    # Get data of the user is requesting for the operation
    user: Member = get_member_by_card_id(db, card_id)

    # Check if such user exists
    if user is None:
        # User not exists --> raise an error
        print("No user with such id was found in database")
        raise HTTPException(status_code=400,
                            detail="No user with such id was found in database")

    # Check if user possess admin rights
    if user.account_type != AccountType.ADMIN.value:
        raise HTTPException(status_code=401,
                            detail="The user has to possses admin role to add new members")
    
    # Check if such email already in use
    email_exists = db.query(Member).filter(Member.email == new_member.email).first()
    if email_exists is not None:
        raise HTTPException(status_code=400,
                            detail="User with such email already registered")

    # Validate correctness of the data being provided
    # Name, Surname should be present; Unique username; strong password
    # Think about scanning the id card as a method of log in to the app + password.
    if new_member.account_type is None:
        new_member.account_type = int(AccountType.MEMBER.value)

    # Generate new QR code value
    qr_value: str = utils.generate_qr_code_value(db)

    # Override default values
    new_member: Member = get_member_based_on_default_value(new_member.model_dump(), as_member=True)
    new_member.card_id = qr_value

    # Add new member to a database --> Update the database.
    db.add(new_member)
    db.commit()
    print("member with card id {} added".format(new_member.card_id))

    # Generate QR Code
    qr_path = utils.generate_qr_code_member(member=new_member)

    # Send an email with the code
    utils.send_welcome_email_member(member=new_member, qr_path=qr_path)

    # return from the function
    return JSONResponse(status_code=201, content={"status": "OK", "message": "New member has been added"})

@app.post("/members/{card_id}/checkin")
def members_checkin(card_id: str,
                    checkin: CheckInRequest,
                    db_members: Session = Depends(utils.get_db_members),
                    db_checkin: Session = Depends(utils.get_db_checkins)):
    """ Add new check into the corresponding database

    Args:
        card_id (str): Card ID of the person who performing check in
        checkin (CheckInRequest): All the data needed to perform a checkin
        db_members (Session, optional): Main database: all members provided. Defaults to Depends(utils.get_db_members).
        db_checkin (Session, optional): CheckIn database: serves to store checkin history. Defaults to Depends(utils.get_db_checkins).
    """
    
    # Get data about the person who scans
    member_who_scans = db_members.query(Member).filter(Member.card_id == card_id).first()
    if not member_who_scans:
        raise HTTPException(status_code=400,
                            detail="No Admin or Instructor with such id was found in database")
    
    print(member_who_scans.name, member_who_scans.account_type)
    # Check if person have rights to checkin someone
    if ((AccountType(member_who_scans.account_type) != AccountType.ADMIN) and
        (AccountType(member_who_scans.account_type) != AccountType.INSTRUCTOR)):
        raise HTTPException(status_code=401,
                            detail="The user has to possses admin or instructor role to checkIn members")
    
    # Get data about the member being scanned
    member_being_scanned = db_members.query(Member).filter(Member.card_id == checkin.card_id).first()
    if not member_who_scans:
        raise HTTPException(status_code=400,
                            detail="No member with such id was found in database")
    
    """ Validate person which is being scanned """
    # Payment through external tool --> scip some validations
    if ((checkin.payment_by_externa_tool is False) or
        (member_being_scanned.account_type == AccountType.ADMIN)):
        # Date of the pass is finished
        if member_being_scanned.expiration_date > date.today():
            raise HTTPException(status_code=403,
                                detail="Pass date is expired")
        
        # No entrances left
        if member_being_scanned.entrances_left <= 0:
            raise HTTPException(status_code=403,
                                detail="No more entrances left")
        
    """ Update both databases: main and checkin """
    scan_datetime = datetime.now()

    # Assemble data to create checkin entry --> commit it to the database
    checkin_entry_data = {
        "control_card_id": member_who_scans.card_id,
        "control_name": member_who_scans.name,
        "control_surname": member_who_scans.surname,
        "hall": checkin.hall,
        "card_id": member_being_scanned.card_id,
        "name": member_being_scanned.name,
        "surname": member_being_scanned.surname,
        "date_time": scan_datetime,
    }
    checkin_entry: CheckInEntry = CheckInEntry(**checkin_entry_data)
    db_checkin.add(checkin_entry)
    db_checkin.commit()

    # Update information about the member --> Store it
    member_being_scanned.entrances_left = member_being_scanned.entrances_left - 1
    member_being_scanned.last_check_in = scan_datetime
    db_members.commit()
    db_members.refresh(member_being_scanned)

    return JSONResponse(status_code=201, content={"status": "OK", "message": "CheckIn Success"})

@app.post("/members/update/")
def members_update(updates: MemberUpdateRequest,
                   db: Session = Depends(utils.get_db_members)):
    
    # Get the user which data is about to change
    member: Member = get_member_by_card_id(db, updates.card_id)
    if member is None:
        raise HTTPException(status_code=400,
                            detail="Such member in database was not found")
    
    # Modify every set (Not equake to None) value
    for key, value in updates.model_dump(exclude_unset=True).items():
        setattr(member, key, value)

    db.commit()
    db.refresh(member)
    return {"status": "success", "updated_member": member.card_id}

@app.post("/members/{card_id}/get/member_info", response_model=MemberInfoResp)
def get_member_info(card_id: str,
                    req: MemberInfoReq,
                    db: Session = Depends(utils.get_db_members)):
    
    # CheckValidate user who is making a request
    user: Member = get_member_by_card_id(db, card_id)
    if user is None:
        raise HTTPException(status_code=400,
                            detail="No such token in member database")
    
    if AccountType(user.account_type) not in [AccountType.ADMIN, AccountType.INSTRUCTOR]:
        raise HTTPException(status_code=400,
                            detail="User has no right get this information")

    # Validate member`s card id is correct
    member: Member = get_member_by_card_id(db, req.card_id)
    if member is None:
        raise HTTPException(status_code=400,
                            detail="Member ID was not found")
    
    return member

@app.post("/login/username", response_model=LogInResponse)
def login_by_username(login_data: LogIn,
                      db: Session = Depends(utils.get_db_members)):
    """ Validates if user with such login exists &&
        If the password provided was correct.
        Everything is OK --> responces with user data. 
    """
    
    # Check if user with such username and password exists
    member = db.query(Member).filter(
        Member.username == login_data.username,
        Member.password == login_data.password
    ).first()
    
    # Such username does not exists or password is wrong --> raise corresponding error
    if member is None:
        raise HTTPException(status_code=401,
                            detail="Wrong login or password")
    
    # Response with user data
    return member

@app.post("/checkin/log/filtered", response_model=list[CheckInLogResponse])
def get_checkin_log_filtered(filters: CheckInLogFilters,
                             db: Session = Depends(utils.get_db_checkins)):
    # If all filters were None --> throw an exception
    if all(value is None for value in filters.model_dump(exclude_unset=False).values()):
        raise HTTPException(status_code=400,
                            detail="Impossible to return data - no filters were provided.")
    
    """
    # Make query wich will apply all filters provided.
    # field_map = {
    #     "control_card_id": CheckInEntry.control_card_id,
    #     "control_name" : CheckInEntry.control_name,
    #     "control_surname": CheckInEntry.control_surname,
    #     "hall": CheckInEntry.hall,
    #     "card_id": CheckInEntry.card_id,
    #     "name": CheckInEntry.name,
    #     "surname": CheckInEntry.surname,
    #     "date_time": CheckInEntry.date_time,
    # }
    # for key, value in filters.model_dump(exclude_unset=True).items():
    #     if value is not None:
    #         if key == "date_time_min":
    #             query = query.filter(CheckInEntry.date_time >= value)
    #         elif key == "date_time_max":
    #             query = query.filter(CheckInEntry.date_time <= value)
    #         else:
    #             attr = field_map[key]
    #             query = query.filter(attr.ilike(value))
    """

    # Create query
    query = db.query(CheckInEntry)

    # Filter etries based on who scanned
    if filters.control_name:
        query = query.filter(CheckInEntry.control_name == filters.control_name)
    
    if filters.control_surname:
        query = query.filter(CheckInEntry.control_surname == filters.control_surname)

    if filters.hall:
        query = query.filter(CheckInEntry.hall == filters.hall)

    # Filter entries based on scanend person
    if filters.card_id:
        query = query.filter(CheckInEntry.card_id == filters.card_id)
    
    if filters.name:
        query = query.filter(CheckInEntry.name == filters.name)

    if filters.surname:
        query = query.filter(CheckInEntry.surname == filters.surname)

    # Filter entries based on time
    if filters.date_time_min:
        query = query.filter(CheckInEntry.date_time >= filters.date_time_min)

    if filters.date_time_max:
        query = query.filter(CheckInEntry.date_time <= filters.date_time_max)

    # Get data from the database [ordered by the date time && with limit]
    data = query.order_by(CheckInEntry.date_time).limit(filters.limit).all()
    return data
#===========================================================

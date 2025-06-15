import os
from typing import Optional
import dotenv
from email.message import EmailMessage
from fastapi import FastAPI, Depends, HTTPException, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import date, datetime, timedelta

from models import Member, CheckInEntry
from enum import Enum
from pathlib import Path

from schemas import CheckInLogResponse, CheckInLogFilters, CheckInRequest, MemberInfoReq, MemberInfoResp, MemberUpdateRequest
from schemas import Req_LogIn, Resp_LogIn, Req_AddNewMember, Resp_AddNewMember

import project_utils as utils
from project_utils import PassType, AccountType
#===========================================================

""" START THE APPLICATION """

# Load environment variables
dotenv.load_dotenv()

# Prepare environment for work
utils.check_create_paths()
utils.databases_init_tables()
utils.check_create_root()

# FastAPI application to run
app = FastAPI(title="Dance School Backend")

# Load Impakt logo once on the beginning
# impakt_logo = PIL.Image.open("impakt_logo.jpg")
# impakt_logo = impakt_logo.resize((75, 100))
#===========================================================

""" FastAPI """
@app.post("/login/username", 
          response_model=Resp_LogIn,
          response_model_exclude_none=True,
          response_model_exclude_unset=True)
def post_login_by_username(login_data: Req_LogIn,
                           db: Session = Depends(utils.get_db_members)):
    """ Validates if user with such login exists &&
        If the password provided was correct.
        Everything is OK --> responces with user data. 
    """

    # Validate username
    member = utils.get_member_by_username(db, login_data.username)
    if member is None:
        raise HTTPException(status_code=401,
                            detail="No user with this username")
    
    is_password_correct = utils.verify_hash(login_data.password, member.password_hash)
    if not is_password_correct:
        raise HTTPException(status_code=401,
                            detail="Wrong password")
    
    # Return user info
    return member

@app.post("/members/add/{card_id}", response_model=Resp_AddNewMember)
def members_add(card_id: str,
               req: Req_AddNewMember, 
               db: Session = Depends(utils.get_db_members)):
    
    """ Get and validate user who is requesting for new member being add. """
    user: Member = utils.get_member_by_card_id(db, card_id)

    # Check if such user exists
    if user is None:
        # User not exists --> raise an error
        print("No user with such id was found in database")
        raise HTTPException(status_code=400,
                            detail="No user with such id was found in database")

    # Check if has rights to add new members
    if ((user.account_type != AccountType.ADMIN.value) and
        (user.account_type != AccountType.INSTRUCTOR.value)):
        raise HTTPException(status_code=401,
                            detail="The user should be an Instructor or Admin to add new members")
    
    """ Validate data about new user being provided """

    # Check if such email already in use
    email_exists = db.query(Member).filter(Member.email == req.email).first()
    if email_exists is not None:
        raise HTTPException(status_code=400,
                            detail="User with such email already registered")

    # Validate correctness of the data being provided
    # Name, Surname should be present; Unique username; strong password
    # Think about scanning the id card as a method of log in to the app + password.
    if user.account_type == AccountType.INSTRUCTOR.value:
        if req.account_type != AccountType.MEMBER.value:
            raise HTTPException(status_code=401,
                            detail="Instructors can add new members only. Instructors and administrators can be added by the administrator only")

    # Construct member: generate new password
    password: str = None
    member: Member = None
    (member, password) = utils.get_member_from_dict(member=req.model_dump())

    # Generate new QR code value --> store it as member`s card ID.
    qr_value: str = utils.generate_qr_code_value(db)
    member.card_id = qr_value

    # Add new member to a database --> Update the database.
    db.add(member)
    db.commit()

    # Generate QR Code
    qr_path = utils.generate_qr_code_member(member=member)

    # Send an email with the QR Code. 
    if os.getenv("SEND_WELCOME_EMAIL"):
        if req.send_welcome_email:
            utils.send_welcome_email_member(member=member, 
                                            qr_path=qr_path, password=password)

    # return from the function
    return member

@app.post("/members/update/")
def members_update(updates: MemberUpdateRequest,
                   db: Session = Depends(utils.get_db_members)):
    
    def validate_data(req: MemberUpdateRequest) -> dict:
        return {}

    # Get the user which data is about to change
    member: Member = utils.get_member_by_card_id(db, updates.card_id)
    if member is None:
        raise HTTPException(status_code=400,
                            detail="Such member in database was not found")
    
    # Modify every set (Not equake to None) value
    for key, value in updates.model_dump(exclude_unset=True).items():
        setattr(member, key, value)

    db.commit()
    db.refresh(member)
    return {"status": "success", "updated_member": member.card_id}

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

@app.post("/members/{card_id}/get/member_info", response_model=MemberInfoResp)
def get_member_info(card_id: str,
                    req: MemberInfoReq,
                    db: Session = Depends(utils.get_db_members)):
    
    # CheckValidate user who is making a request
    user: Member = utils.get_member_by_card_id(db, card_id)
    if user is None:
        raise HTTPException(status_code=400,
                            detail="No such token in member database")
    
    if AccountType(user.account_type) not in [AccountType.ADMIN, AccountType.INSTRUCTOR]:
        raise HTTPException(status_code=400,
                            detail="User has no right get this information")

    # Validate member`s card id is correct
    member: Member = utils.get_member_by_card_id(db, req.card_id)
    if member is None:
        raise HTTPException(status_code=400,
                            detail="Member ID was not found")
    
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

from collections import defaultdict
import os
from typing import Optional
import dotenv

from fastapi import FastAPI, Depends, HTTPException, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, or_
from datetime import date, datetime, timedelta

from models import Member, CheckInEntry

from schemas import CheckInLogResponse, CheckInLogFilters, MemberUpdateRequest, Req_Member_UpdatePass, Resp_Member_UpdatePass, Resp_MemberInfo
from schemas import Req_LogIn, Resp_LogIn, Req_AddNewMember, Resp_AddNewMember, Req_ConfirmMail, Resp_ConfirmMail, Req_Checkin
from schemas import Req_Statistics_Admin_CheckInsByType_All, Resp_Statistics_Admin_CheckInsByType

import project_utils as utils
from project_utils import AccountType

from endpoints_passes import router as router_passes
#===========================================================

""" START THE APPLICATION """

# Load environment variables
dotenv.load_dotenv()

# Prepare environment for work
utils.check_create_paths()
utils.databases_init_tables()
utils.check_create_root()

# FastAPI application to run --> add all routers
app = FastAPI(title="Dance School Backend")
app.include_router(router_passes)

# Load Impakt logo once on the beginning
# impakt_logo = PIL.Image.open("impakt_logo.jpg")
# impakt_logo = impakt_logo.resize((75, 100))
#===========================================================

def member_has_valid_pass(member: Member) -> bool:
    return True
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
def post_members_add(card_id: str,
               req: Req_AddNewMember, 
               db: Session = Depends(utils.get_db_members)):
    
    # Check if user exists
    user: Member = utils.get_member_by_card_id(db, card_id)
    if user is None:
        raise HTTPException(status_code=400,
                            detail="No user with such id was found in database")

    # Check if user has rights to add new members
    if ((user.account_type != AccountType.ADMIN.value) and
        (user.account_type != AccountType.INSTRUCTOR.value)):
        raise HTTPException(status_code=401,
                            detail="The user should be an Instructor or Admin to add new members")
    
    # Check if member`s` email already in use
    email_exists = db.query(Member).filter(Member.email == req.email).first()
    if email_exists is not None:
        raise HTTPException(status_code=400,
                            detail="Member with given email already registered")

    # Validate correctness of the data being provided
    # Name, Surname should be present; Unique username; strong password
    # Think about scanning the id card as a method of log in to the app + password.
    if user.account_type == AccountType.INSTRUCTOR.value:
        if req.account_type != AccountType.MEMBER.value:
            raise HTTPException(status_code=401,
                            detail="Instructors can add new members only. Instructors and administrators can be added by the administrator only")

    # Construct member: generate new password --> write over default values
    password: str = utils.get_random_string(12)
    pass_hash = utils.hash_string(password)
    member_req = req.model_dump()
    member_req["password_hash"] = pass_hash
    member: Member = utils.get_member_from_dict(member=member_req)

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

@app.post("/members/confirm_mail", response_model=Resp_ConfirmMail)
def post_members_confirm(req: Req_ConfirmMail,
                         db: Session = Depends(utils.get_db_members)):

    """ [TBD] Confirmation that provided email is valid.
    """
    return None

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

@app.post("/membres/update/pass/{card_id}", response_model=Resp_Member_UpdatePass)
def post_members_update_pass(card_id: str,
                             req: Req_Member_UpdatePass,
                             db: Session = Depends(utils.get_db_members)):
    """ Allows to update data about member`s pass type
    """
    user: Member = utils.get_member_by_card_id(db, card_id)
    member: Member = utils.get_member_by_card_id(db, req.card_id)

    # Check who is trying to update member`s pass
    if AccountType(user.account_type) not in (AccountType.ADMIN, AccountType.INSTRUCTOR):
         raise HTTPException(status_code=400,
                            detail="User has no rights to perform this operation")

    # Check if user already has valid pass
    if member_has_valid_pass(member) is True:
        raise HTTPException(status_code=400,
                            detail="User already has valid pass")

    # Update db
    db.commit()
    db.refresh(member)

    # return Success operation code
    return member
#===========================================================

@app.get("/members/get/info/{user_id}/{member_id}", response_model=Resp_MemberInfo)
def get_member_info(user_id: str,
                    member_id: str,
                    db: Session = Depends(utils.get_db_members)):
    
    # CheckValidate user who is making a request
    user: Member = utils.get_member_by_card_id(db, user_id)
    if user is None:
        raise HTTPException(status_code=400,
                            detail="No such token in member database")
    
    # Validate member`s card id is correct
    member: Member = utils.get_member_by_card_id(db, member_id)
    if member is None:
        raise HTTPException(status_code=400,
                            detail="Member ID was not found")
    
    # Validate if user can ask about another user based on the role
    if AccountType(user.account_type) not in [AccountType.ADMIN, AccountType.INSTRUCTOR]:
        raise HTTPException(status_code=401,
                            detail="User has no right get this information")
    
    if AccountType(user.account_type) is AccountType.INSTRUCTOR:
        if ((AccountType(member.account_type) is not AccountType.MEMBER) and
            (user.card_id != member.card_id)):
            raise HTTPException(status_code=401,
                            detail="User has no right get this information")
    
    return member
#===========================================================

@app.post("/checkin/{card_id}")
def post_checkin(card_id: str,
                 req: Req_Checkin,
                 db_members: Session = Depends(utils.get_db_members),
                 db_checkin: Session = Depends(utils.get_db_checkins)):
    """ Add new check into the corresponding database

    Args:
        card_id (str): Card ID of the person who performing check in
        req (CheckInRequest): All the data needed to perform a checkin
        db_members (Session, optional): Main database: all members provided. Defaults to Depends(utils.get_db_members).
        db_checkin (Session, optional): CheckIn database: serves to store checkin history. Defaults to Depends(utils.get_db_checkins).
    """
    
    # Get user who scanned --> check his priviladges
    user: Member = utils.get_member_by_card_id(db_members, card_id)
    if not user:
        raise HTTPException(status_code=400,
                            detail="No Admin or Instructor with such id was found in database")
    
    if ((AccountType(user.account_type) != AccountType.ADMIN) and
        (AccountType(user.account_type) != AccountType.INSTRUCTOR)):
        raise HTTPException(status_code=401,
                            detail="The user has to possses admin or instructor role to checkIn members")
    
    # Get data about the member being scanned
    member: Member = utils.get_member_by_card_id(db_members, req.card_id)
    if not member:
        raise HTTPException(status_code=400,
                            detail="No member with such id was found in the database")
    
    """ Validate member being scanned """
    # If member used external payment or he is an instructor --> no check needed
    if ((req.external_payment is False) and
        (member.account_type == AccountType.MEMBER.value)):

        # Date of the pass is finished
        if member.expiration_date > date.today():
            raise HTTPException(status_code=403,
                                detail="Pass date is expired")
        
        # No entrances left
        if member.entrances_left <= 0:
            raise HTTPException(status_code=403,
                                detail="No more entrances left")
        
    """ Update both databases: main and checkin """
    # Assemble data to update checkin table
    scan_datetime = datetime.now()
    entrances_left = member.entrances_left - 1
    
    checkin_entry_data = {
        "instructor_card_id": user.card_id,
        "instructor_name": user.name,
        "instructor_surname": user.surname,
        "hall": req.hall,
        "card_id": member.card_id,
        "name": member.name,
        "surname": member.surname,
        "date_time": scan_datetime,
        "entrances_left": entrances_left,
    }
    checkin_entry: CheckInEntry = CheckInEntry(**checkin_entry_data)
    db_checkin.add(checkin_entry)
    db_checkin.commit()

    # Update information about the member --> Store it
    member.entrances_left = entrances_left
    member.last_check_in = scan_datetime
    db_members.commit()
    db_members.refresh(member)

    return JSONResponse(status_code=201, content={"status": "OK", "message": "CheckIn Success"})
#===========================================================

@app.post("/statistics/all_instructors/entries_amount/{card_id}", response_model=list[Resp_Statistics_Admin_CheckInsByType])
def post_statistics_all_instructors_entries_amount(card_id: str,
                                                   req: Req_Statistics_Admin_CheckInsByType_All,
                                                   db_members: Session = Depends(utils.get_db_members),
                                                   db_checkins: Session = Depends(utils.get_db_checkins)):
    
    user: Member = utils.get_member_by_card_id(db_members, card_id)
    if user.account_type != AccountType.ADMIN.value:
         raise HTTPException(status_code=400,
                            detail="User has no rights to perform this operation")

    # Get only needed and filtered data from the database
    resp = (
        # Specify tables
        db_checkins.query(
            CheckInEntry.instructor_name,
            CheckInEntry.instructor_surname,
            CheckInEntry.pass_type,
            func.count().label("count"),
        )
        # Filter them by data
        .filter(
            CheckInEntry.date_time >= req.date_time_min,
            CheckInEntry.date_time <= req.date_time_max,
        )
        # Return as (name, surname, pass_type, amount)
        .group_by(CheckInEntry.name, CheckInEntry.instructor_surname, CheckInEntry.pass_type)
        .all()
    )

    # Get all fields from class definition ==> more robbust in case of some change in the class itself
    grouped = defaultdict(lambda: {
        name: field.default
        for name, field in Resp_Statistics_Admin_CheckInsByType.model_fields.items()
    })

    # post-sorting of the data
    for (name, surname, amount) in resp:
        person = grouped[name, surname]
        person["name"] = name
        person["surname"] = surname
        
        # Calculate each type of the checkin separatelly (grouped by the types of the pass)
        person["entries_total"] += amount

    result = list(grouped.values())
    return result

@app.get("statistics/instructor/self_checkins/today/{card_id}")
def get_statistics_instructor_self_checkins_today(card_id: str):
    pass
#===========================================================

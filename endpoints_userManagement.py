from datetime import datetime
from smtplib import SMTPServerDisconnected
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi_utils.tasks import repeat_every
from sqlalchemy.orm import Session
from sqlalchemy import select

from database import SessionLocal_Members
from models import Member
from schemas import Req_LogIn_Username, Req_Members_Add, Resp_Members_Inst

import project_utils as utils
#===========================================================

router = APIRouter()
#===========================================================

""" LOGIN 
"""
@router.post("/login/username",
             response_model=Resp_Members_Inst,
             response_model_exclude_none=True,
             response_model_exclude_unset=True,
             status_code=status.HTTP_202_ACCEPTED)
def post_login_by_username(login_data: Req_LogIn_Username,
                           db: Session = Depends(utils.get_db_members)):
    """ Validates if user with such login exists &&
        If the password provided was correct.
        Everything is OK --> responces with user data. 
    """

    # Validate username
    member = utils.get_member_by_username(db, login_data.username)
    if member is None:
        raise HTTPException(status_code=401,
                            detail="Wrong username")
    
    is_password_correct = utils.verify_hash(login_data.password, member.password_hash)
    if not is_password_correct:
        raise HTTPException(status_code=401,
                            detail="Wrong password")
    
    # Return user info
    return member
#===========================================================

""" MEMBERS
    SignUp, mail confirmation, password restoration
    Deleting unconfiremed members
"""
@router.post("members/signup",
             status_code=status.HTTP_202_ACCEPTED)
async def post_signup(db: Session = Depends(utils.get_db_members)):
    # Check if member already registered
    member: Member = await db.execute(select(Member).where(Member.email == req.email)).scalar_one_or_none()
    if member and member.activated:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Email already registered and confirmed")
    
    # Add member to a database

@repeat_every(seconds=6*60*60)
async def cleanup_unconfirmed_members() -> None:
    """ Every six hours do cleanup of the users whom emails were not confirmed.
    """
    db = SessionLocal_Members()
    db.query(Member).filter(Member.activated.is_(False),
                            Member.expiration_time < datetime.now())\
                    .delete()
    db.commit()
    db.close()

async def startup():
    await cleanup_unconfirmed_members()
#===========================================================

""" MEMBERS
    Add, Modify, Delete
"""
@router.post("/members/add",
             response_model=Resp_Members_Inst,
             response_model_exclude_none=True,
             response_model_exclude_unset=True,
             status_code=status.HTTP_201_CREATED)
def post_members_add(req: Req_Members_Add,
                     db: Session = Depends(utils.get_db_members)):
    # Check of all who is adding is needed.
    # Check who is adding and what [Instructor can not add another instructors, only members, etc.]
    # ...

    # Check given email is not used
    email_exists = db.query(Member).filter(Member.email == req.email).first()
    if email_exists is not None:
        raise HTTPException(status_code=400,
                            detail="Member with given email already registered")
    
    # Construct member: generate new password --> write over default values
    password: str = utils.get_random_string(12)
    pass_hash = utils.hash_string(password)
    member_req = req.model_dump()
    member_req["password_hash"] = pass_hash
    member: Member = utils.get_member_from_dict(member=member_req)

    # Generate new QR code value --> store it as member`s card ID.
    qr_value: str = utils.generate_qr_code_value(db)
    member.card_id = qr_value

    # Generate QR Code
    qr_path = utils.generate_qr_code_member(member=member)

    # Send an email with the QR Code. 
    if req.send_welcome_email:
        try:
            utils.send_welcome_email_member(member=member, 
                                            qr_path=qr_path, password=password)
        except SMTPServerDisconnected:
            # Delete generated qr_code --> raise corresponding exception
            qr_path.unlink()
            raise HTTPException(status_code=400,
                                detail="Could not send an email to user")

    # Add new member to a database --> Update the database.
    db.add(member)
    db.commit()
    db.refresh(member)

    # return from the function
    return member

@router.get("/members/{member_id}",
            response_model=Resp_Members_Inst,
            response_model_exclude_none=True,
            response_model_exclude_unset=True,
            status_code=status.HTTP_200_OK)
def get_members_inst(member_id: str,
                     db: Session = Depends(utils.get_db_members)):
    # Check of all who is adding is needed.
    # Check who is requesting [Instructor can not see info about another instructor]
    # ...

    member: Member = utils.get_member_by_card_id_with_raise(db, member_id)
    return member

# /members/register

#
#===========================================================

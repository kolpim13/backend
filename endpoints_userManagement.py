import os
from datetime import datetime, timedelta
from smtplib import SMTPServerDisconnected
from fastapi.responses import HTMLResponse
from itsdangerous import URLSafeTimedSerializer
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi_utils.tasks import repeat_every
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, select
from sqlalchemy.exc import IntegrityError

from database import SessionLocal_Members
from models import Member
from schemas import Req_LogIn_Username, Req_Members_Add, Req_SignUp, Resp_Members_Inst

import project_utils as utils
#===========================================================

router = APIRouter()

SECRET_KEY = os.getenv("SECRET_KEY")
SECRET_SALT = os.getenv("SECRET_SALT")
#===========================================================

def get_serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(SECRET_KEY, salt=SECRET_SALT)

def generate_confirmation_token(email: str, password_hash: str):
    serializer = get_serializer()
    data = {"email": email, "pwd": password_hash}
    return serializer.dumps(data)

def confirm_token(token: str, expiration: int = 6*60*60) -> dict:
    serializer = get_serializer()
    data = serializer.loads(token, max_age=expiration)
    return data
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

""" REGISTRATION
    SignUp, mail confirmation, password restoration
    Deleting unconfiremed members
"""
@router.post("/signup",
             status_code=status.HTTP_201_CREATED)
def post_signup(req: Req_SignUp,
                      db: Session = Depends(utils.get_db_members)):
    # Check if member already registered
    member: Member | None = db.execute(select(Member)\
        .where(or_(Member.email == req.email,
                   Member.username == req.username)))\
        .scalar_one_or_none()
    
    if member and member.activated:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Member with such email or username already registered and confirmed")
    
    # Hash the password
    pwd_hash = utils.hash_string(req.password)
    token = generate_confirmation_token(req.email, pwd_hash)

    # If user already exist -> Update pwd_hash || registration date. Othervise -> Add new.
    if member:
        member.password_hash = pwd_hash
        member.registration_date = datetime.now()
        member.token = token
        db.refresh(member)
    else:
        member_data = req.model_dump()
        member_data["password_hash"] = pwd_hash
        member_data["expiration_time"] = datetime.now() + timedelta(hours=6)
        member_data["token"] = token
        member: Member = utils.get_member_from_dict(member_data)
        db.add(member)
        
    # Protection against unexcpected situations during adding new user
    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Unexcpected error. Operation reverted")

    # Send confirmation mail
    # utils.send_confirmation_email(req.email, token)
    print(token)

    member_test: Member | None = db.execute(select(Member)\
        .where(Member.token == token))\
        .scalar_one_or_none()
    
    # Return data
    return {"details": "Confirmation link sent; please check your email."}

@router.get("/confirm/{token}", 
         response_class=HTMLResponse,
         status_code=status.HTTP_202_ACCEPTED)
def get_confirm_email(token: str, 
                      db: Session = Depends(utils.get_db_members)):
    
    # Confirm token real
    try:
        data = confirm_token(token)
    except Exception as e:
        # SignatureExpired, BadTimeSignature, BadSignature
        return HTMLResponse(f"<h3>Confirmation failed: {e}</h3>", 
                            status_code=400)

    # Check token is valid
    member: Member | None = db.execute(select(Member)\
        .where(Member.token == token))\
        .scalar_one_or_none()
    
    if not member:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Invalid or expired token povided")

    if member and member.activated:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Email is already confirmed")

    # Collect data
    email       = data["email"]
    pwd_hash    = data["pwd"]

    # Check email and pass hash
    member = db.execute(select(Member)
                   .where(Member.email == email))\
                   .scalar_one_or_none()
    
    if member.email != email:
        raise HTTPException(400, "No signup found for this email.")
    if member.password_hash != pwd_hash:
        raise HTTPException(400, "Invalid or stale confirmation link.")

    # mark confirmed --> update database
    member.activated = True
    member.token = None
    db.commit()
    db.refresh(member)

    # Redirect to your real “account confirmed” page or show a message:
    return HTMLResponse("<h3>Your account has been confirmed. You may now log in.</h3>")

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
    member_req["activated"] = True  # If admin add the user -> no confirmation code is needed.
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

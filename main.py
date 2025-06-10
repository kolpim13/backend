import os
import random
import string
from typing import Optional
import qrcode
import dotenv
import smtplib
import PIL
import PIL.Image
import PIL.ImageDraw
import PIL.ImageFont
import PIL.ImageFile
from email.message import EmailMessage
from fastapi import FastAPI, Depends, HTTPException, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import date, datetime, timedelta
from database import SessionLocal, engine, SessionLocalEntrances, engine_entrances
from models import Base, BaseEntrances, Member, CheckInEntry
from enum import Enum
from pathlib import Path

from schemas import CheckInLogResponse, CheckInLogFilters, CheckInRequest, LogInResponse, MemberAddRequest, MemberInfoReq, MemberInfoResp, MemberUpdateRequest
#===========================================================

""" START THE APPLICATION """

# Load environment variables
dotenv.load_dotenv()

# Create tables
Base.metadata.create_all(bind=engine)
BaseEntrances.metadata.create_all(bind=engine_entrances)

# FastAPI application to run
app = FastAPI(title="Dance School Backend")

# Load Impakt logo once on the beginning
# impakt_logo = PIL.Image.open("impakt_logo.jpg")
# impakt_logo = impakt_logo.resize((75, 100))
#===========================================================

""" DATA TYPES """

class PassType(Enum):
    """ Pass type a member posses
    """

    PASS_NO         = 0
    PASS_LIMITED    = 1
    PASS_UNLIMITED  = 2

class AccountType(Enum):
    ADMIN       = 0
    INSTRUCTOR  = 1
    MEMBER      = 2

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

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_db_entrances():
    db = SessionLocalEntrances()
    try:
        yield db
    finally:
        db.close()

def get_random_string(len: int) -> str:
    return ''.join(random.choice(string.ascii_lowercase + string.ascii_uppercase + string.digits) for _ in range(len))

def generate_qr_code_value(db: Session = Depends(get_db)) -> str:
    """ Generates unique QR code value """

    while True:
        code_value = get_random_string(int(os.getenv("QR_CODE_VALUE_LEN")))
        exists = db.query(Member).filter(Member.card_id == code_value).first()
        if not exists:
            return code_value

def generate_qr_code(code: str, name: str, surname: str) -> Path:
    """ Generates QR Code and places it in folder qr_codes
    On top it adds name and surname of the recepient
    On bottom - data (code as text)

    Args:
        code (str): Code to incode inside QR Image.
        name (str): Name of the recipient
        surname (str): Surname of the recipient

    Returns:
        Path: Path to generated qr code. Each QR has it`s name build based on data provided.
    """

    def place_text(text: str, height: bool) -> None:
        """ Serves to

        Args:
            text (str): _description_
            height (bool): _description_
        """
        bbox = draw.textbbox((0,0), text, font=font)
        text_w = bbox[2] - bbox[0]
        
        draw.text(((img_w - text_w) // 2, height), text, fill="black", font=font)
        return
    
    """ Generating original QR Code """
    # Set up qr code and add data on it
    qr = qrcode.QRCode(version=3, box_size=10, border=2)
    qr.add_data(code)
    qr.make(fit=True)

    # Generate image from the qr code
    img = qr.make_image(fill_color="black", back_color="white")

    # Load logo and resize it, so it will fit inside the qr code. 
    logo = PIL.Image.open("impakt_logo.jpg")
    logo = logo.resize((75, 100))

    # Calculate coordinates --> place logo in center of QR code
    img_w, img_h = img.size
    logo_w, logo_h = logo.size
    pos = ((img_w - logo_w) // 2, (img_h - logo_h) // 2)

    img.paste(logo, pos)

    """ Making an image from original QR Code"""
    # Choose font size for the text
    font_size = 20
    font = PIL.ImageFont.load_default(size=font_size)

    # Calculate --> add blank space to the original QR Code image
    padding = font_size * 3 + 10
    new_img = PIL.Image.new("RGB", (img_w, img_h + padding), "white")
    draw = PIL.ImageDraw.Draw(new_img)

    # Place name and surname on top
    place_text(name, 5)
    place_text(surname, 5 + font_size)

    # Place original QR Code
    img = img.convert("RGB")
    new_img.paste(img, (0, 5 + font_size * 2))

    # Place QR Code as text at the very bottom
    place_text(code, 5 + img_h + font_size * 2)

    # Save QR code on the disc --> return Path to it
    qr_name = "qr_{name}_{surname}_{code}.png".format(name=name, surname=surname, code=code)
    qr_path = Path(Path.resolve(Path.cwd()), "qr_codes", qr_name)
    new_img.save(qr_path)
    return qr_path

def generate_qr_code_member(member: Member | MemberIn) -> Path:
    return generate_qr_code(member.card_id, member.name, member.surname)

def send_welcome_email(email_to: str, qr_path: Path,
                       name: str, surname: str,
                       login: str, password: str) -> None:
    
    if os.getenv("SEND_WELCOME_EMAIL") == "False":
        return

    # Get needed data from environmental vars
    email_from = os.getenv("ROOT_EMAIL")
    email_pass = os.getenv("ROOT_EMAIL_APP_PASS")

    # Get email body from file
    with open('welcome_email_template.txt', 'r', encoding='utf-8') as file:
        # Read template
        email_body = file.read()

        # Replace key words
        replacement = [
            ("{name}", name),
            ("{surname}", surname),
            ("{login}", login),
            ("{password}", password),
        ]
        for key_word, value in replacement:
            email_body = email_body.replace(key_word, value)

    # Assemble message
    msg = EmailMessage()
    msg['Subject'] = "Welcome to Impakt"
    msg['From'] = email_from
    msg['To'] = email_to
    msg.set_content(email_body)

    # Add QR as an attachment
    with open(qr_path, 'rb') as qr:
        qr_image = qr.read()
        msg.add_attachment(qr_image, maintype='image', subtype='png', filename=qr_path.name)

    # Send email
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=10) as smtp:
        smtp.login(email_from, email_pass)
        smtp.send_message(msg)

def send_welcome_email_member(email_to: str, qr_path: Path, member: Member | MemberIn) -> None:
    send_welcome_email(email_to, qr_path,
                       member.name, member.surname,
                       member.username, member.password)

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

        "username": get_random_string(12),
        "password": get_random_string(12),
       
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
        qr_value: str = generate_qr_code_value(db)
        root.card_id = qr_value

        # Add it to a database
        db.add(root)
        db.commit()

        # Generate qr code
        qr_code: Path = generate_qr_code(qr_value, 
                                         root.name, root.surname)

        # Send QR via mail on self email address
        send_welcome_email(os.getenv("ROOT_EMAIL"), qr_code,
                           root.name, root.surname,
                           root.username, root.password)
        print("4")

        print("Root user was created with default values. Change it`s password and card ID as soon as possible!")
        return True
    
    return False
#===========================================================

""" FastAPI """

@app.post("/members/check_create_root")
def api_check_create_root(db: Session = Depends(get_db)) -> JSONResponse:
    if check_create_root(db) is True:
        return JSONResponse(status_code=201, content={"status": "OK", "message": "Default root user created"})
    return JSONResponse(status_code=200, content={"status": "OK", "message": "Root already exists"})

@app.post("/members/{card_id}/add")
def members_add(card_id: str,
               new_member: MemberAddRequest, db: Session = Depends(get_db)):
    
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
    qr_value: str = generate_qr_code_value(db)

    # Override default values
    new_member: Member = get_member_based_on_default_value(new_member.model_dump(), as_member=True)
    new_member.card_id = qr_value

    # Add new member to a database --> Update the database.
    db.add(new_member)
    db.commit()
    print("member with card id {} added".format(new_member.card_id))

    # Generate QR Code
    qr_path = generate_qr_code_member(member=new_member)

    # Send an email with the code
    send_welcome_email_member(email_to=new_member.email, qr_path=qr_path, member=new_member)

    # return from the function
    return JSONResponse(status_code=201, content={"status": "OK", "message": "New member has been added"})

@app.post("/members/{card_id}/checkin")
def members_checkin(card_id: str,
                    checkin: CheckInRequest,
                    db_members: Session = Depends(get_db),
                    db_checkin: Session = Depends(get_db_entrances)):
    """ Add new check into the corresponding database

    Args:
        card_id (str): Card ID of the person who performing check in
        checkin (CheckInRequest): All the data needed to perform a checkin
        db_members (Session, optional): Main database: all members provided. Defaults to Depends(get_db).
        db_checkin (Session, optional): CheckIn database: serves to store checkin history. Defaults to Depends(get_db_entrances).
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
                   db: Session = Depends(get_db)):
    
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
                    db: Session = Depends(get_db)):
    
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
                      db: Session = Depends(get_db)):
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
                             db: Session = Depends(get_db_entrances)):
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

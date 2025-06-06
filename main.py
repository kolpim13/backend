import os
import random
import string
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
from models import Base, BaseEntrances, Member
from enum import Enum
from pathlib import Path
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

class Database(Enum):
    MEMBERS     = 0
    ENTRANCES   = 1

class PassType(Enum):
    " Define how many entrances can one do"
    PASS_1          = 0
    PASS_4          = 1
    PASS_8          = 2
    PASS_12         = 3
    PASS_UNLIMITED  = 4
    PASS_NO         = 99

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

def generate_qr_code_member(member: Member) -> Path:
    return generate_qr_code(member.card_id, member.name, member.surname)

def send_welcome_email(email_to: str, qr_path: Path,
                       name: str, surname: str,
                       login: str, password: str) -> None:
    
    # Get needed data from environmental vars
    email_from = os.getenv("EMAIL_USER_NAME")
    email_pass = os.getenv("EMAIL_APP_PASS")

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

def get_member_based_on_default_value(member: dict) -> dict:
    # "date_of_birth": date.strftime(date(2050, 1, 1), "%Y-%m-%d"),
    # "expiration_date": date.strftime(date.today(), "%Y-%m-%d"),
    # "register_date": date.strftime(date.today(), "%Y-%m-%d"),
    # "last_check_in": datetime.strftime(datetime.now(), "%Y-%m-%d %H:%M:%S"),

    member_default = {
        "card_id": get_random_string(12),

        "name": "Name",
        "surname": "Surname",
        "email": "mail@gmail.com",
        "phone_number": "000 000 000",
        
        "date_of_birth": None, # date(2050, 1, 1),

        "pass_type": PassType.PASS_NO,
        "account_type": AccountType.MEMBER,
        "entrances_left": 0,
        "expiration_date": date.today() + timedelta(weeks=5),
        "register_date": date.today(),

        "last_check_in": None,

        "username": get_random_string(12),
        "password": get_random_string(12),
       
        "activated": False,
    }
    member = {**member_default, **member}

    # Add some validation here (?)
    # ...

    return member

def dict_to_Member(member_dict: dict) -> Member:
    def safe_enum_value_convert(val):
        return val.value if isinstance(val, Enum) else val
    
    # Probably will be needed in future
    member = Member(
        **{**member_dict,
            "account_type": int(safe_enum_value_convert(member_dict["account_type"])),
            "pass_type": int(safe_enum_value_convert(member_dict["pass_type"]))
        }
    )
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
            "name": os.getenv("EMAIL_USER_NAME"),
            "surname": os.getenv("EMAIL_USER_SURNAME"),
            "email": os.getenv("EMAIL_USER_NAME"),
            "username": "root",
            "account_type": AccountType.ADMIN
        }
        root_values = get_member_based_on_default_value(root_values)

        # Create a root member and fill it with default values
        root: Member = dict_to_Member(root_values)

        # Add it to a database
        db.add(root)
        db.commit()

        # Create QR Code
        qr_path = generate_qr_code_member(member=root)

        # Send QR via mail on self email address
        send_welcome_email(os.getenv("EMAIL_USER_NAME"), qr_path,
                           root.name, root.surname,
                           root.username, root.password)

        print("Root user was created with default values. Change it`s password and card ID as soon as possible!")
        return True
    
    return False
#===========================================================

""" FastAPI Members """

@app.post("/members/check_create_root")
def api_check_create_root(db: Session = Depends(get_db)) -> JSONResponse:
    if check_create_root(db) is True:
        return JSONResponse(status_code=201, content={"status": "OK", "message": "Default root user created"})
    return JSONResponse(status_code=200, content={"status": "OK", "message": "Root already exists"})

@app.post("/members/{card_id}/add")
def add_member(card_id: str,
               new_member: MemberIn, db: Session = Depends(get_db)):
    
    # Get data of the user is requesting for the operation
    user: Member = get_member_by_card_id(db, card_id)

    # Check if such user exists
    if user is None:
        # User not exists --> raise an error
        print("No user with such id was found in database")
        raise HTTPException(status_code=400,
                            detail="No user with such id was found in database")

    # Check if user possess admin rights
    if user.account_type != AccountType.ADMIN:
        raise HTTPException(status_code=401,
                            detail="The user has to possses admin role to add new members")

    # Will return None of no member with such id was found
    is_exist = get_member_by_card_id(db, new_member.card_id)

    # Raise an error, so client`s app can handle it --> finish this function.
    if is_exist is not None:
        print("This card id already registered")
        raise HTTPException(status_code=400,
                            detail="Member with such ID already registered")
        
    # Validate correctness of the data being provided
    # Name, Surname should be present; Unique username; strong password
    # Think about scanning the id card as a method of log in to the app + password.

    # Override default values 
    new_member = get_member_based_on_default_value(new_member.dict())

    # Add new member to a database
    new_member = Member(**new_member)
    db.add(new_member)
    print("member with card id {} added".format(new_member.card_id))

    # Update the database --> return from the function
    db.commit()
    return {"status": "success", "id": new_member.card_id}
#===========================================================

""" FastAPI login """

@app.post("/login/username")
def login_by_username(login_data: LogIn,
                      db: Session = Depends(get_db)):
    """ Validates if user with such login exists &&
        If the password provided was correct.
        Everything is OK --> responces with user data. 
    """
    
    member = get_member_by_username(db, username=login_data.username)
    
    # Such username does not exists or password is wrong --> raise corresponding error
    if member is None:
        raise HTTPException(status_code=401,
                            detail="Wrong login or password")
    
    if member.password != login_data.password:
        raise HTTPException(status_code=401,
                            detail="Wrong login or password")
    
    # Response with user data
    content = {
        "status": "OK",
        "name": member.name,
        "surname": member.surname
    }
    return JSONResponse(status_code=200, content=content)
#===========================================================

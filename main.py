import random
import string
import PIL.ImageFile
import qrcode
import PIL
import PIL.Image
import PIL.ImageDraw
import PIL.ImageFont
from fastapi import FastAPI, Depends, HTTPException, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from database import SessionLocal, engine, SessionLocalEntrances, engine_entrances
from models import Base, BaseEntrances, Member
from enum import Enum
from pathlib import Path
#===========================================================

""" START THE APPLICATION """

# Create tables
Base.metadata.create_all(bind=engine)
BaseEntrances.metadata.create_all(bind=engine_entrances)

# FastAPI application to run
app = FastAPI(title="Dance School Backend")

# Load Impakt logo once on the beginning
# impakt_logo = PIL.Image.open("impakt_logo.jpg")
# impakt_logo = impakt_logo.resize((75, 100))
#===========================================================

""" Database related """

def get_member_by_qr_code(db: Session, qr_code: str) -> Member:
    member: Member = db.query(Member).filter(Member.qr_code == qr_code).first()
    return member

def get_member_by_username(db: Session, username: str) -> Member:
    member: Member = db.query(Member).filter(Member.username == username).first()
    return member
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

    qr_code: str

    name: str
    surname: str
    pass_type: int
    entrances_left: int
    expiration_date: date
    last_check_in: date

    username: str
    password: str
    account_type: int

class LogIn(BaseModel):
    username: str
    password: str
#===========================================================

""" UTILS """
        
def get_db(type: Database = Database.MEMBERS):
    if type is Database.MEMBERS:
        db = SessionLocal()
    elif type is Database.ENTRANCES:
        db = SessionLocalEntrances
    else:
        raise ValueError("No such database exists")

    try:
        yield db
    finally:
        db.close()

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

def generate_qr_code_from_member(member: Member) -> Path:
    return generate_qr_code(member.card_id, member.name, member.surname)
#===========================================================

""" FastAPI related functiomality """

@app.post("/members/check_create_root")
def check_create_root_user(db: Session = Depends(get_db)) -> None:
    """ Function should be on the very beginning of the execution to check if there is a "root: user present
        If it does not --> create one with default username and password  
    """

    # Try to get root user from the database
    root = get_member_by_username(db, "root")

    # Root does not exists --> create default one
    if root is None:
        print("No root user was found in the database --> start of creating a new one.")

        # Create a root member and fill it with default values
        root: Member = Member()
        root.qr_code = "12345678"
        root.name = "anonym"
        root.surname = "----"
        root.pass_type = PassType.PASS_UNLIMITED
        root.entrances_left = 999
        root.expiration_date = date(2050, 12, 31)
        root.last_check_in = datetime.today()
        root.register_date = date.today()
        root.username = "root"
        root.password = "pass"
        root.account_type = AccountType.ADMIN

        # Add it to a database
        db.add(root)
        db.commit()

        print("Root user was created with default values. Change it`s password and card ID as soon as possible!")
        return JSONResponse(status_code=201, content={"message": "Default root user created"})
    
    # If exists -> return corresponding status!
    content = {
        "status": "success"
    }
    return JSONResponse(status_code=200, content=content)

@app.post("/members/{qr_code}/add")
def add_member(qr_code: str,
               new_member: MemberIn, db: Session = Depends(get_db)):
    
    # Get data of the user is requesting for the operation
    user: Member = get_member_by_qr_code(db, qr_code)

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
    is_exist = get_member_by_qr_code(db, new_member.qr_code)

    # Raise an error, so client`s app can handle it --> finish this function.
    if is_exist is not None:
        print("This card id already registered")
        raise HTTPException(status_code=400,
                            detail="Member with such ID already registered")
        
    # Validate correctness of the data being provided
    # Name, Surname should be present; Unique username; strong password
    # Think about scanning the id card as a method of log in to the app + password.

    # Override default values 
    new_member_default = {
        "name": "Name",
        "surname": "SurName",
        "email": "",

        "pass_type": PassType.PASS_NO,
        "account_type": AccountType.MEMBER,

        "entrances_left": 0,
        "expiration_date": str(date.strftime(date.today() + relativedelta(months=1, days=10), "%Y-%m-%d")),
        "register_date": str(date.strftime(date.today(), "%Y-%m-%d")),

        "last_check_in": str(datetime.strftime(datetime.today(), "%Y-%m-%d %H:%M:%S")),

        "username": ''.join(random.choice(string.ascii_lowercase + string.ascii_uppercase + string.digits) for _ in range(8)),
        "password": "12345678",

        "activated": False,
    }
    new_member = {**new_member_default, **new_member.dict()}

    # Add new member to a database
    new_member = Member(**new_member)
    db.add(new_member)
    print("member with card id {} added".format(new_member.qr_code))

    # Update the database --> return from the function
    db.commit()
    return {"status": "success", "id": new_member.qr_code}

def get_member_info_by_qr_code(qr_code: str,
                          db: Session = Depends(get_db)):
    pass

@app.post("/login/qr_code/{qr_code}/{password}")
def login_by_qr_code(qr_code: str, password: str,
                db: Session = Depends(get_db)):
    
    return {"status": "success"}

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

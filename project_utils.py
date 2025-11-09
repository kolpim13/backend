# Generic packages
import base64
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import (Mail, Attachment, FileContent, FileName, FileType, Disposition)
import os
import dotenv
import random
import string
from pathlib import Path
from datetime import date
from enum import Enum

# Poject-specific / Specialized packages
from PIL import Image, ImageDraw
import PIL
import PIL.ImageFont
from argon2 import PasswordHasher
import argon2
import qrcode
import qrcode.constants
import smtplib
from email.message import EmailMessage
from sqlalchemy.orm import Session
from fastapi import HTTPException, Depends 

# User
from models import ExternalProvider, Member, MemberPass
from database import engine_members, engine_checkins, Base_Checkins, Base_Members, SessionLocal_Members, SessionLocal_Checkins
#===========================================================

PATH_BASE = Path.cwd().resolve()
PATH_DATABASES = Path(PATH_BASE, "databases")
PATH_TEMPLATES = Path(PATH_BASE, "templates")
PATH_QR_CODES = Path(PATH_BASE, "qr_codes")

env = {}
#===========================================================

""" Datatypes to be used as databases fields """
class AccountType(Enum):
    """ Defines what rights does a member posses. 
    """

    ROOT: int        = 0
    ADMIN: int       = 1
    INSTRUCTOR: int  = 2
    MEMBER: int      = 3
    EXTERNAL: int    = 4
#===========================================================

""" STARTUP ACTIONS """
def check_create_root(db: Session = SessionLocal_Members()) -> bool:
    """ Function should be executed on the very beginning of the program to check if there is a "root" member present.
        If it does not --> create one with default username and password written in an ".env" configuration file.  
    """

    # Try to get root user from the database
    root = db.query(Member).filter(Member.account_type == AccountType.ROOT.value).first()

    # Root does not exists --> create default one
    if root is None:
        print("No root user was found in the database --> start of creating a new one.")

        # Setup root user value
        qr_value: str = generate_qr_code_value(db)
        password = env["ROOT_PASS"]
        pass_hash = hash_string(password)
        root_values = {
            "card_id": qr_value,
            "name": env["ROOT_NAME"],
            "surname": env["ROOT_SURNAME"],
            "email": env["ROOT_EMAIL"],
            "username": env["ROOT_LOGIN"],
            "password_hash": pass_hash,
            "account_type": AccountType.ROOT,
            "activated": True,   # First user activated by default
        }
        root: Member = get_member_from_dict(root_values)

        # Add it to a database
        db.add(root)
        db.commit()

        # Generate qr code
        qr_code: Path = generate_qr_code(qr_value, 
                                         root.name, root.surname)

        # Send QR Code via email on self email address
        if env["SEND_WELCOME_EMAIL"] == "True":
            send_welcome_email_member(member=root,
                                      qr_path=qr_code,
                                      password=password)
            
        print("Root user was created with default values. Change it`s password and card ID as soon as possible!")
        return True
    
    return False

def check_create_paths() -> None:
    paths = (PATH_DATABASES, PATH_TEMPLATES, PATH_QR_CODES)
    for path in paths:
        if path.exists() is False:
            path.mkdir(parents=True, exist_ok=False)

def databases_init_tables() -> None:
    Base_Members.metadata.create_all(bind=engine_members)
    Base_Checkins.metadata.create_all(bind=engine_checkins)
    return

def load_environment_variables() -> None:
    """ Function exists due to Droplet/Ubuntu limitation:
        It does not allow to read environment variables until you 
        read and write it.
    """

    # Read and write data
    env_file = dotenv.find_dotenv()
    dotenv.load_dotenv(env_file)
    
    # Read all variables used
    env["ROOT_NAME"] = os.getenv("ROOT_NAME")
    env["ROOT_SURNAME"] = os.getenv("ROOT_SURNAME")
    env["ROOT_LOGIN"] = os.getenv("ROOT_LOGIN")
    env["ROOT_PASS"] = os.getenv("ROOT_PASS")
    env["ROOT_EMAIL"] = os.getenv("ROOT_EMAIL")

    env["SEND_WELCOME_EMAIL"] = os.getenv("SEND_WELCOME_EMAIL")
    env["EMAIL_APP_PASS"] = os.getenv("EMAIL_APP_PASS")
    env["SENDGRID_MAIL"] = os.getenv("SENDGRID_MAIL")
    env["SENDGRID_KEY"] = os.getenv("SENDGRID_KEY")

    env["GENERATE_QR_CODE_FOR_NEW_USER"] = os.getenv("GENERATE_QR_CODE_FOR_NEW_USER")
    env["QR_ADD_FULL_NAME"] = os.getenv("QR_ADD_FULL_NAME")
    env["QR_ADD_LOGO"] = os.getenv("QR_ADD_LOGO")
    env["QR_ADD_TITLE"] = os.getenv("QR_ADD_TITLE")

    env["QR_CODE_VALUE_LEN"] = os.getenv("QR_CODE_VALUE_LEN")
    env["LOGIN_DEFAULT_LEN"] = os.getenv("LOGIN_DEFAULT_LEN")
    env["PASSWORD_DEFAULT_LEN"] = os.getenv("PASSWORD_DEFAULT_LEN")

    env["SECRET_KEY"] = os.getenv("SECRET_KEY")
    env["SECRET_SALT"] = os.getenv("SECRET_SALT")

    env["BACKEND_ADDRESS"] = os.getenv("BACKEND_ADDRESS")
#===========================================================

""" DATABASE RELATED ACTIONS """
def dict_to_Member(member_dict: dict) -> Member:
    def safe_enum_value_convert(val):
        return val.value if isinstance(val, Enum) else val
    
    # Clean data before pass them to a Member instance
    cleaned_data = {
        **filter_kwargs_for_class(Member, member_dict),
        "account_type": safe_enum_value_convert(member_dict["account_type"]),
    }

    return Member(**cleaned_data)

def get_member_from_dict(member: dict) -> Member:
    """ Function is used to construct member from a req schema.
        All unset fields will be set with default values. 
        As input: any Request from "schemas" can be used (via .model_dump()).
    """

    default = {
        "card_id": None,

        "name": "Name",
        "surname": "Surname",
        "email": None,
        "phone_number": None,
        "date_of_birth": None,
        "image_path": None,
        "registration_date": date.today(),

        "account_type": AccountType.MEMBER,
        "privileges": "",

        "last_check_in": None,

        "username": get_random_string(12),
        "password_hash": None,
        "token": None,
       
        "activated": False, # Always needed to be confirmed
        "expiration_time": None,
    }
    member = {**default, **member}
    member = dict_to_Member(member) # Probably not needed
    # Add some validation here (?)
    # ...

    return member

def get_member_by_card_id(db: Session, card_id: str) -> Member:
    return db.query(Member).filter(Member.card_id == card_id).first()

def get_member_by_card_id_with_raise(db: Session, card_id: str) -> Member:
    member: Member = db.query(Member).filter(Member.card_id == card_id).first()
    if not member:
        raise HTTPException(status_code=400,
                            detail="No mmeber with such id was found in DB")
    return member

def get_member_by_username(db: Session, username: str) -> Member:
    return db.query(Member).filter(Member.username == username).first()

def get_external_provider_by_id(db: Session, id: int) -> ExternalProvider:
    return db.query(ExternalProvider).filter(ExternalProvider.id == id).first()

def get_member_pass_by_id(db: Session, id: int) -> MemberPass:
    return db.query(MemberPass).filter(MemberPass.id == id).first()

""" Functions to use databases inside FastAPI through "Depends". """
def get_db_members():
    db = SessionLocal_Members()
    try:
        yield db
    finally:
        db.close()

def get_db_checkins():
    db = SessionLocal_Checkins()
    try:
        yield db
    finally:
        db.close()
#===========================================================

""" UTILS """
def hash_string(string: str) -> str:
    ph = PasswordHasher()
    return ph.hash(string)

def verify_hash(string: str, hash: str) -> bool:
    ph = PasswordHasher()
    try:
        ph.verify(hash, string)
        return True
    except argon2.exceptions.VerifyMismatchError:
        return False

def get_random_string(len: int) -> str:
    return ''.join(random.choice(string.ascii_lowercase + string.ascii_uppercase + string.digits) for _ in range(len))

def filter_kwargs_for_class(cls, data: dict):
    """ Takes a dictionary and leaves only key and respective keys related to a provided class 
    """
    valid_keys = cls.__table__.columns.keys()
    return {k: v for k, v in data.items() if k in valid_keys and k != 'self'}

""" QR Codes """
def generate_qr_code_value(db: Session = Depends(get_db_members)) -> str:
    """ Generate unique value for QR code.
    """

    while True:
        code_value: str = get_random_string(int(env["QR_CODE_VALUE_LEN"]))
        exists: Member = db.query(Member).filter(Member.card_id == code_value).first()
        if not exists:
            return code_value
        
def generate_qr_code(code: str,
                     fill_color: str = "black",
                     back_color: str = "white") -> Path:
    """ Generates QR code image based on provided data
    """
    # Parameters
    box_size: int = 12
    border: int = 2
    logo_scale: float = 0.22
    add_label: bool = False
    label_text: str = "IMPACT"
    logo_path = r"assets/logo.jpg"
    
    qr = qrcode.QRCode(
        version=3,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=box_size,
        border=border,
    )
    qr.add_data(code)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white").convert("RGB")

    # 2) Centered logo with white padding ring
    logo = Image.open(logo_path).convert("RGBA")
    qr_w, qr_h = qr_img.size
    target_logo_w = int(qr_w * logo_scale)
    ratio = target_logo_w / logo.width
    logo = logo.resize((target_logo_w, int(logo.height * ratio)), Image.LANCZOS)

    pad = int(target_logo_w * 0.18)
    bg_w, bg_h = logo.width + pad*2, logo.height + pad*2
    bg = Image.new("RGBA", (bg_w, bg_h), (255, 255, 255, 255))
    mask = Image.new("L", (bg_w, bg_h), 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle((0, 0, bg_w, bg_h), radius=int(min(bg_w,bg_h)*0.12), fill=255)
    padded = Image.new("RGBA", (bg_w, bg_h))
    padded.paste(bg, (0, 0), mask)
    padded.paste(logo, (pad, pad), logo)

    x = (qr_w - padded.width)//2
    y = (qr_h - padded.height)//2
    qr_img.paste(padded, (x, y), padded)

    # 3) Add thick black border frame
    frame_thickness = int(qr_w * 0.04)
    framed_size = qr_w + 2 * frame_thickness
    framed = Image.new("RGB", (framed_size, framed_size), "black")
    framed.paste(qr_img, (frame_thickness, frame_thickness))
    qr_img = framed
    qr_w, qr_h = qr_img.size

    # Save QR code on the disc --> return Path to it
    qr_name = "{code}.png".format(code=code)
    qr_path = Path(Path.resolve(Path.cwd()), "qr_codes", qr_name)
    qr_img.save(qr_path)
    return qr_path

def generate_qr_code_member(member: Member) -> Path:
    # Define what color of QR code will be.
    fill_color: str = "black"
    back_color: str = "white"
    match member.account_type:
        case AccountType.ADMIN:
            fill_color = "blue"
        case AccountType.INSTRUCTOR:
            fill_color = "green"

    return generate_qr_code(member.card_id,
                            fill_color=fill_color, back_color=back_color)


""" EMAIL
    [SMTP, SendGrid] 
"""
def send_welcome_email(email_to: str, 
                       name: str, surname: str,
                       login: str, password: str,
                       qr_path: Path, template: Path = None) -> None:

    # Get needed data from environmental vars
    email_from = env["ROOT_EMAIL"]
    email_pass = env("EMAIL_APP_PASS")

    # Ensure email template is not null
    if not template:
        template = Path(PATH_TEMPLATES, "welcome_email_template_Member.txt")

    # Get email body from file
    with open(template, 'r', encoding='utf-8') as file:
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
    msg['Subject'] = "Welcome to Impact"
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

def send_welcome_email_member(member: Member, 
                              qr_path: Path, password: str) -> None:
    # Choose appropriate template based on member role
    match AccountType(member.account_type):
        case AccountType.ADMIN:
            template = Path(PATH_TEMPLATES, "welcome_email_template_Admin.txt")
        case AccountType.INSTRUCTOR:
            template = Path(PATH_TEMPLATES, "welcome_email_template_Instructor.txt")
        case AccountType.MEMBER:
            template = Path(PATH_TEMPLATES, "welcome_email_template_Member.txt")
        case _:
            template = Path(PATH_TEMPLATES, "welcome_email_template_Member.txt")
         
    # Member contain only hass password --> raw pass should be provided explicetely
    send_welcome_email(member.email,
                       member.name, member.surname,
                       member.username, password, 
                       qr_path, template)

def send_confirmation_email(to_email: str, key: str):
    # Link to be replaced for production
    link = env["BACKEND_ADDRESS"]
    confirm_url = f"{link}/confirm/{key}"
    body = f"""
        Thanks for signing up!

        Please open this link to confirm (expires in 6 hours):
        {confirm_url}

        If you didn’t request this, ignore this email.
    """
    msg = MIMEMultipart()
    msg["Subject"] = "Confirm your Impact Studio account"
    msg["From"]    = env["ROOT_EMAIL"]
    msg["To"]      = to_email
    msg.attach(MIMEText(body, "plain"))

    # Send email
    smtp_port = 465
    with smtplib.SMTP("smtp.gmail.com", smtp_port, timeout=10) as smtp:
        smtp.starttls()  # Often required, depending on provider
        smtp.login(env["ROOT_EMAIL"], env["EMAIL_APP_PASS"])
        smtp.send_message(msg)

def SendGrid_send_welcome_email(email_to: str, 
                                name: str, surname: str,
                                login: str, password: str,
                                qr_path: Path, template: Path = None) -> None:

    if env["SEND_WELCOME_EMAIL"] != "Sendgrid":
        return

    # Ensure email template is not null
    if not template:
        template = Path(PATH_TEMPLATES, "welcome_email_template_Member.txt")

    # Get email body from file
    with open(template, 'r', encoding='utf-8') as file:
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
    msg = Mail(
        from_email=env["SENDGRID_MAIL"],
        to_emails=email_to,
        subject="Welcome to Impakt",
        plain_text_content=email_body
    )
    
    # Read QR from file --> add it as an attachment
    with open(qr_path, 'rb') as qr:
        qr_image = qr.read()
    encoded_qr_image = base64.b64encode(qr_image).decode()

    attachment = Attachment(
        FileContent(encoded_qr_image),
        FileName("QRCode.png"),
        FileType("image/gif"),
        Disposition('attachment')
    )
    msg.add_attachment(attachment)

    # Send email
    try:
        sg = SendGridAPIClient(env["SENDGRID_KEY"])
        sg.send(msg)
        return True
    except Exception as e:
        return False

def SendGrid_send_welcome_email_member(member: Member, 
                              qr_path: Path, password: str) -> None:
    
    # Choose appropriate template based on member role
    match AccountType(member.account_type):
        case AccountType.ADMIN:
            template = Path(PATH_TEMPLATES, "welcome_email_template_Admin.txt")
        case AccountType.INSTRUCTOR:
            template = Path(PATH_TEMPLATES, "welcome_email_template_Instructor.txt")
        case AccountType.MEMBER:
            template = Path(PATH_TEMPLATES, "welcome_email_template_Member.txt")
        case _:
            template = Path(PATH_TEMPLATES, "welcome_email_template_Member.txt")
         
    # Member contain only hass password --> raw pass should be provided explicetely
    SendGrid_send_welcome_email(member.email,
                                member.name, member.surname,
                                member.username, password, 
                                qr_path, template)

def SendGrid_send_confirmation_mail(to_email, key: str):
    if env["SEND_WELCOME_EMAIL"] != "Sendgrid":
        return

    url = env["BACKEND_ADDRESS"]
    confirm_url = f"{url}/confirm/{key}"
    content = f"""
        Thanks for signing up!

        Please open this link to confirm (expires in 6 hours):
        {confirm_url}

        If you didn’t request this, ignore this email.
    """

    message = Mail(
        from_email=env["SENDGRID_MAIL"],
        to_emails=to_email,
        subject="Confirm your Impact Studio account",
        html_content=content
    )
    try:
        sg = SendGridAPIClient(env["SENDGRID_KEY"])
        sg.send(message)
        return True
    except Exception as e:
        return False
#===========================================================

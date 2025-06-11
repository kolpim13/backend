# Generic packages
import os
import random
import string
from pathlib import Path
from enum import Enum

# Poject-specific / Specialized packages
import PIL
import PIL.Image
import PIL.ImageDraw
import PIL.ImageFont
import qrcode
import qrcode.constants
import smtplib
from email.message import EmailMessage
from sqlalchemy.orm import Session
from fastapi import Depends

# User
from models import Member, CheckInEntry
from database import engine_members, engine_checkins, Base_Checkins, Base_Members, SessionLocal_Members, SessionLocal_Checkins
#===========================================================

PATH_BASE = Path.cwd().resolve()
PATH_DATABASES = Path(PATH_BASE, "databases")
PATH_TEMPLATES = Path(PATH_BASE, "templates")
PATH_QR_CODES = Path(PATH_BASE, "qr_codes")
#===========================================================

""" Datatypes to be used as databases fields """
class PassType(Enum):
    """ Pass type of a member.
    """

    NO: int         = 0
    LIMITED: int    = 1
    UNLIMITED: int  = 2

class AccountType(Enum):
    """ Defines what rights does a member posses. 
    """

    ADMIN: int       = 0
    INSTRUCTOR: int  = 1
    MEMBER: int      = 2
#===========================================================

""" DATABASE RELATED ACTIONS """
def databases_init_tables() -> None:
    Base_Members.metadata.create_all(bind=engine_members)
    Base_Checkins.metadata.create_all(bind=engine_checkins)
    return

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

""" ABC """
def get_random_string(len: int) -> str:
    return ''.join(random.choice(string.ascii_lowercase + string.ascii_uppercase + string.digits) for _ in range(len))

def convert_enum_to_int(enum: Enum) -> int:
    return int(enum.value)

""" QR Codes """
def generate_qr_code_value(db: Session = Depends(get_db_members)) -> str:
    """ Generate unique value for QR code.
    """

    while True:
        code_value: str = get_random_string(int(os.getenv("QR_CODE_VALUE_LEN")))
        exists: Member = db.query(Member).filter(Member.card_id == code_value).first()
        if not exists:
            return code_value
        
def generate_qr_code(code: str, name: str = "", surname: str = "",
                     fill_color: str = "black", back_color: str = "white") -> Path:
    """ Generates QR code image based on provided data
    """
    
    def place_text(text: str, height: bool) -> None:
        bbox = draw.textbbox((0,0), text, font=font)
        text_w = bbox[2] - bbox[0]
        
        draw.text(((img_w - text_w) // 2, height), text, fill="black", font=font)
        return
    
    """ Generating original QR Code """
    # Set up qr code and add data on it
    qr = qrcode.QRCode(version=3, box_size=10, border=2,
                       error_correction=qrcode.constants.ERROR_CORRECT_H)
    qr.add_data(code)
    qr.make(fit=True)   # Does it needed?

    # Generate image from the qr code
    img = qr.make_image(fill_color=fill_color, back_color=back_color)

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
    # Define what color of QR code will be.
    fill_color: str = "black"
    back_color: str = "white"
    match member.account_type:
        case AccountType.ADMIN:
            fill_color = "blue"
        case AccountType.INSTRUCTOR:
            fill_color = "green"

    return generate_qr_code(member.card_id, member.name, member.surname,
                            fill_color=fill_color, back_color=back_color)

""" EMAIL """
def send_welcome_email(email_to: str, 
                       name: str, surname: str,
                       login: str, password: str,
                       qr_path: Path, template: Path = None) -> None:

    # Get needed data from environmental vars
    email_from = os.getenv("ROOT_EMAIL")
    email_pass = os.getenv("ROOT_EMAIL_APP_PASS")

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

def send_welcome_email_member(member: Member, qr_path: Path) -> None:
    # Choose appropriate template based on member role
    match member.account_type:
        case AccountType.ADMIN:
            template = Path(PATH_TEMPLATES, "welcome_email_template_Admin.txt")
        case AccountType.INSTRUCTOR:
            template = Path(PATH_TEMPLATES, "welcome_email_template_Instructor.txt")
        case AccountType.MEMBER:
            template = Path(PATH_TEMPLATES, "welcome_email_template_Member.txt")
         
    send_welcome_email(member.email,
                       member.name, member.surname,
                       member.username, member.password, 
                       qr_path, template)
#===========================================================

import base64
import os
import PIL.Image
import PIL.ImageDraw
import PIL.ImageFont
import qrcode
import PIL
import requests
import datetime
from fastapi import HTTPException
from datetime import date
from models import Base, Member
from pathlib import Path
from email.message import EmailMessage
import dotenv
import smtplib
import ssl
import socket

# from sendgrid import SendGridAPIClient
# from sendgrid.helpers.mail import Mail, Attachment, FileContent, FileName, FileType, Disposition

API_URL = "http://localhost:8000"

def check_create_root() -> None:
    response = requests.post("{api_url}/members/check_create_root".format(api_url=API_URL))
    if response.status_code == 200:
        print("Root user already exists")
    elif response.status_code == 201:
        print(response.content)
    else:
        print("Error code: {}\nDetail: {}".format(response.status_code, response.json())) 

def add_member() -> None:
    # Provide all needed data
    name = input("Name: ")
    surname = input("Surname: ")
    email = input("Email: ")

    # Put all data together
    data = {
        "name": name,
        "surname": surname,
        "email": email
    }

    # Try to send data to the database
    response = requests.post("{api_url}/members/{user_id}/add".format(api_url=API_URL, user_id="i3Te8Gdmoo2r"), json=data)
    if response.status_code == 200:
        print("✅ Member added successfully.")
    else:
        print("Error code: {}\nDetail: {}".format(response.status_code, response.json())) 

def add_members_from_excel() -> None:
    new_member_default = {
        "name": "Name",
        "surname": "SurName",
    }

    new_member = {
        "name": "NameX2",
        "email": "bastu",
    }
    new_member = {**new_member_default, **new_member}
    new_member = Member(**new_member)
    pass

def generate_qr_code(code: str, name: str, surname: str) -> Path:

    def place_text(text: str, height: bool) -> None:
        bbox = draw.textbbox((0,0), text, font=font)
        text_w = bbox[2] - bbox[0]
        
        draw.text(((img_w - text_w) // 2, height), text, fill="black", font=font)
        return

    # Set up qr code and add data on it
    qr = qrcode.QRCode(version=3, box_size=10, border=2)
    qr.add_data(code)
    qr.make(fit=True)

    # Generate image from the qr code
    img = qr.make_image(fill_color="black", back_color="white")

    # Load logo and resize it, so it will fit inside the qr code. 
    logo = PIL.Image.open("impakt_logo.jpg")
    logo = logo.resize((75, 100))

    # Calculate coordinates where to place the logo
    img_w, img_h = img.size
    logo_w, logo_h = logo.size
    pos = ((img_w - logo_w) // 2, (img_h - logo_h) // 2)

    # Place the logo inside QR code
    img.paste(logo, pos)

    # Place name and QR Code as text on the image
    font_size = 20
    font = PIL.ImageFont.load_default(size=font_size)

    padding = font_size * 3 + 10
    new_img = PIL.Image.new("RGB", (img_w, img_h + padding), "white")
    draw = PIL.ImageDraw.Draw(new_img)

    place_text(name, 5)
    place_text(surname, 5 + font_size)

    img = img.convert("RGB")
    new_img.paste(img, (0, 5 + font_size * 2))

    place_text(code, 5 + img_h + font_size * 2)

    # Save QR code on the disc
    qr_name = "qr_{name}_{surname}_{code}.png".format(name=name, surname=surname, code=code)
    qr_path = Path(Path.resolve(Path.cwd()), "qr_codes", qr_name)
    if qr_path.parent.exists() is False:
        Path(qr_path.parent).mkdir(parents=True, exist_ok=False)
    new_img.save(qr_path)

    # Return path to the QR code
    return qr_path

def send_email_with_info(path_to_qr: Path, email_to_send: str) -> None:
    # Try this function at home!
    
    dotenv.load_dotenv()
    email_from = os.getenv("EMAIL_USER")
    email_to = email_to_send
    email_pass = os.getenv("EMAIL_PASS")
    
    # Get email body from file
    with open('welcome_email_template.txt', 'r', encoding='utf-8') as file:
        # Read template
        email_body = file.read()

        # Replace key words
        replacement = [
            ("{name}", "asd"),
            ("{surname}", "asd"),
            ("{login}", "asd"),
            ("{password}", "asd"),
        ]
        for key_word, value in replacement:
            email_body = email_body.replace(key_word, value)
    
    """ SMTP """
    msg = EmailMessage()
    msg['Subject'] = "Welcome to Impakt"
    msg['From'] = email_from
    msg['To'] = email_to
    msg.set_content(email_body)

    # Read QR code from disc
    with open(path_to_qr, 'rb') as qr:
        qr_image = qr.read()
        msg.add_attachment(qr_image, maintype='image', subtype='png', filename=path_to_qr.name)

    # Send an email
    smtplib.SMTP_SSL.debuglevel = 1
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=10) as smtp:
        smtp.login(email_from, email_pass)
        smtp.send_message(msg)

if __name__ == "__main__":
    # qr = generate_qr_code(code="MazurAn123", name="Anastazja", surname="Mazur")
    # send_email_with_info(path_to_qr=qr, email_to_send="anastasiia.mazur@gmail.com")
    # exit()

    while True:
        print("\n--- Dance School Terminal ---")
        print("0. Check & create default root user")
        print("1. Add Member")
        print("2. Add all members from the excel")
        print("3. Generate test QR code")
        print("4. Send an email to myself")
        choice = input("Select option: ")

        if choice == "0":
            check_create_root()
        elif choice == "1":
            add_member()
        elif choice == "2":
            add_members_from_excel()
        elif choice == "3":
            generate_qr_code(code="MazurAn123", name="Anastazja", surname="Mazur")
        elif choice == "4":
            send_email_with_info(path_to_qr=Path(Path.cwd().resolve(), "qr_codes", "qr_Anastazja_Mazur_MazurAn123.png"))
        else:
            print("Invalid option.")
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
    qr_code = input("NFC ID: ")
    name = input("Name: ")
    surname = input("Surname: ")
    pass_type = int(input("Pass type: "))
    entrances_left = int(input("Entrances left: "))
    expiration_date = input("Expiration date (YYYY-MM-DD): ")
    expiration_date = str(datetime.datetime.strptime(expiration_date, "%Y-%m-%d").date())
    last_check_in = input("Last check in (YYYY-MM-DD HH:MM:SS): ")
    last_check_in = str(datetime.datetime.strptime(last_check_in, "%Y-%m-%d %H:%M:%S"))
    register_date = datetime.date.today()
    register_date = str(datetime.datetime.strptime(register_date, "%Y-%m-%d").date())
    username = "----"
    password = "----"
    account_type = int(input("Account type: "))

    # Put all data together
    data = {
        "id": qr_code,
        "name": name,
        "surname": surname,
        "pass_type": pass_type,
        "entrances_left": entrances_left,
        "expiration_date": expiration_date,
        "last_check_in": last_check_in,
        "register_date": register_date,
        "username": username,
        "password": password,
        "account_type": account_type,
    }

    # Try to send data to the database
    response = requests.post("{api_url}/members/{user_id}/add".format(api_url=API_URL, user_id="12345678"), json=data)
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
    new_img.save(qr_path)

    # Return path to the QR code
    return qr_path

def send_email_with_info(path_to_qr: Path) -> None:
    # Try this function at home!
    
    dotenv.load_dotenv()
    email_from = os.getenv("EMAIL_USER")
    email_to = email_from
    email_pass = os.getenv("EMAIL_PASS")
    email_body = """ Hello there\n\nWelcome to the impakt. We do love you, give us your money. Here is your QR Code, cheers! :) """
    
    """ SMTP """
    msg = EmailMessage()
    msg['Subject'] = "Welcome to Impakt"
    msg['From'] = email_from
    msg['To'] = email_to
    msg.set_content(email_body)

    with open(path_to_qr, 'rb') as qr:
        qr_image = qr.read()
        msg.add_attachment(qr_image, maintype='image', subtype='png', filename=path_to_qr.name)

    # smtpObj = smtplib.SMTP('live.smtp.mailtrap.io', 587)
    # smtpObj.sendmail(email_from, email_to, msg)

    # Tests
    # context = ssl.create_default_context()
    # with socket.create_connection(("smtp.gmail.com", 465)) as sock:
    #     with context.wrap_socket(sock, server_hostname="smtp.gmail.com") as ssock:
    #         print(ssock.version())

    smtplib.SMTP.debuglevel = 1
    context = ssl.create_default_context()
    with socket.create_connection(("smtp.gmail.com", 465)) as sock:
        with context.wrap_socket(sock, server_hostname="smtp.gmail.com") as ssock:
            smtp = smtplib.SMTP_SSL()
            smtp.sock = ssock  # Use the pre-wrapped socket
            smtp.file = ssock.makefile("rb")

            smtp.helo("localhost")
            smtp.ehlo()
            # smtp.connect("smtp.gmail.com", 465)

            smtp.login(email_from, email_pass)
            smtp.send_message(msg)
            smtp.quit()

    # Should work in home network (but does not).
    # print("OpenSSL version:", ssl.OPENSSL_VERSION)
    # smtplib.SMTP_SSL.debuglevel = 1
    # context = ssl.create_default_context()
    # with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context, timeout=10) as smtp:
    #     smtp.login(email_from, email_pass)
    #     smtp.send_message(msg)

    # with smtplib.SMTP("smtp.office365.com", 587, timeout=10) as smtp:
    #     smtp.ehlo() 
    #     smtp.starttls() 
    #     smtp.ehlo() 
    #     smtp.login(email_from, email_pass)
    #     smtp.send_message(msg)

    """ NATIVE """
    # message = Mail(
    #     from_email          = email_from,
    #     to_emails           = email_to,
    #     subject             = "Welcome to Impakt",
    #     plain_text_content  = email_body
    # )

    # # Attach QR code image
    # with open(path_to_qr, 'rb') as f:
    #     data = f.read()
    #     encoded = base64.b64encode(data).decode()

    # attachment = Attachment(
    #     FileContent(encoded),
    #     FileName(path_to_qr.name),
    #     FileType('image/png'),
    #     Disposition('attachment')
    # )
    # message.attachment = attachment

    # try:
    #     sg = SendGridAPIClient(os.getenv("SENDGRID_API_KEY"))
    #     response = sg.send(message)
    #     print("✅ Email sent:", response.status_code)
    # except Exception as e:
    #     print("❌ Error sending email:", str(e))

if __name__ == "__main__":
    # generate_qr_code(code="MazurAn123", name="Anastazja", surname="Mazur")
    send_email_with_info(path_to_qr=Path(Path.cwd().resolve(), "qr_codes", "qr_Anastazja_Mazur_MazurAn123.png"))
    exit()

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
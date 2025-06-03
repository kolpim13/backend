import requests
import datetime
from fastapi import HTTPException

API_URL = "http://localhost:8000"

def add_member() -> None:
    # Provide all needed data
    card_id = input("NFC ID: ")

    # Put all data together
    data = {
        "card_id": card_id,
    }

    # Try to send data to the database
    response = requests.post("{api_url}/members/add".format(api_url=API_URL), json=data)
    if response.status_code == 200:
        print("✅ Member added successfully.")
    else:
        print("Error code: {}\nDetail: {}".format(response.status_code, response.json())) 

if __name__ == "__main__":
    while True:
        print("\n--- Dance School Terminal ---")
        print("1. Add Member")
        choice = input("Select option: ")

        if choice == "1":
            add_member()
        else:
            print("Invalid option.")
from fastapi import FastAPI, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import date
from database import SessionLocal, engine
from models import Base, Member
#===========================================================

""" Start the application """

# Create tables
Base.metadata.create_all(bind=engine)

# FastAPI application to run
app = FastAPI(title="Dance School Backend")
#===========================================================

""" UTILS """

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class MemberIn(BaseModel):
    """_summary_

    Args:
        BaseModel (_type_): _description_
    """

    card_id: str
#===========================================================

""" Database related """

def is_user_exists_by_id(db: Session, card_id: str) -> bool:
    member = db.query(Member).filter(Member.card_id == card_id).first()
    if member is None:
        return False
    return True
#===========================================================

""" FastAPI related functiomality """

@app.post("/members/add")
def add_member(member: MemberIn, db: Session = Depends(get_db)):
    # Will return None of no member with such card_id was found
    is_exist = db.query(Member).filter(Member.card_id == member.card_id).first()

    # Raise an error, so client`s app can handle it --> finish this function.
    if is_exist is not None:
        print("This card id already registered")
        raise HTTPException(status_code=400,
                            detail="User with such ID already registered")
        
    # Validate correctness of the data being provided
    # ...

    # Add new member to a database
    new_member = Member(**member.dict())
    db.add(new_member)
    print("member with card id {} added".format(member.card_id))

    # Update the database --> return from the function
    db.commit()
    return {"status": "success", "card_id": member.card_id}
#===========================================================

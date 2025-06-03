from sqlalchemy import Column, Integer, String, Date
from database import Base

class Member(Base):
    # The file name it will be created
    __tablename__ = "members"

    card_id = Column(String, primary_key=True, unique=True, index=True)
    # name = Column(String)
    # pass_type = Column(Integer)


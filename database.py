from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

DB_MEMBERS_URL = "sqlite:///./databases/members.db"
DB_CHECKINS_URL = "sqlite:///./databases/checkins.db"

# Database for the members
engine_members = create_engine(DB_MEMBERS_URL, connect_args={"check_same_thread": False})
SessionLocal_Members = sessionmaker(bind=engine_members, autoflush=False, autocommit=False)
Base_Members = declarative_base()

# Database to log all entrances done
engine_checkins = create_engine(DB_CHECKINS_URL, connect_args={"check_same_thread": False})
SessionLocal_Checkins = sessionmaker(bind=engine_checkins, autoflush=False, autocommit=False,)
Base_Checkins = declarative_base()

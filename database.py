from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

DB_URL = "sqlite:///./members.db"
DB_ENTRANCES_URL = "sqlite:///./entrances.db"

# Database for the members
engine = create_engine(DB_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

# Database to log all entrances done
engine_entrances = create_engine(DB_ENTRANCES_URL, connect_args={"check_same_thread": False})
SessionLocalEntrances = sessionmaker(bind=engine_entrances, autocommit=False, autoflush=False)
BaseEntrances = declarative_base()

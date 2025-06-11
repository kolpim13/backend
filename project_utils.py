from database import engine_members, engine_checkins, Base_Checkins, Base_Members, SessionLocal_Members, SessionLocal_Checkins
#===========================================================

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

#===========================================================

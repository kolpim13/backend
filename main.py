from collections import defaultdict
import logging
import os
import time
from typing import Optional
import dotenv

from fastapi import FastAPI, Depends, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, or_
from datetime import date, datetime, timedelta

from database import SessionLocal_Members
from models import ExternalProvider, Member, PassType

from schemas import Req_CheckIn_Add, Req_Statistics_Admin_CheckInsByType_All, Resp_ChecIn_Inst, Resp_Statistics_Admin_CheckInsByType

from endpoints_passes import router as router_passes
from endpoints_userManagement import router as router_user_management
from endpoints_logs import router as router_logging
from endpoints_statistics import router as router_statistics

import project_utils as utils
from project_utils import AccountType
#===========================================================

""" START THE APPLICATION """
# Load environment variables
dotenv.load_dotenv()

# Prepare environment for work
utils.check_create_paths()
utils.databases_init_tables()
utils.check_create_root()

# FastAPI application to run --> add all routers
app = FastAPI(title="Dance School Backend")
app.include_router(router_passes)
app.include_router(router_user_management)
app.include_router(router_logging)
app.include_router(router_statistics)

@app.middleware("http")
async def post_checkin_add_time_log(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    print(f"{request.method} {request.url.path} executed in {process_time:.4f} seconds")
    return response

# Load Impakt logo once on the beginning
# impakt_logo = PIL.Image.open("impakt_logo.jpg")
# impakt_logo = impakt_logo.resize((75, 100))
#===========================================================

""" FastAPI """

@app.post("/statistics/all_instructors/entries_amount/{card_id}", response_model=list[Resp_Statistics_Admin_CheckInsByType])
def post_statistics_all_instructors_entries_amount(card_id: str,
                                                   req: Req_Statistics_Admin_CheckInsByType_All,
                                                   db_members: Session = Depends(utils.get_db_members),
                                                   db_checkins: Session = Depends(utils.get_db_checkins)):
    
    user: Member = utils.get_member_by_card_id(db_members, card_id)
    if user.account_type != AccountType.ADMIN.value:
         raise HTTPException(status_code=400,
                            detail="User has no rights to perform this operation")

    # Get only needed and filtered data from the database
    resp = (
        # Specify tables
        db_checkins.query(
            CheckInEntry.instructor_name,
            CheckInEntry.instructor_surname,
            CheckInEntry.pass_type,
            func.count().label("count"),
        )
        # Filter them by data
        .filter(
            CheckInEntry.date_time >= req.date_time_min,
            CheckInEntry.date_time <= req.date_time_max,
        )
        # Return as (name, surname, pass_type, amount)
        .group_by(CheckInEntry.name, CheckInEntry.instructor_surname, CheckInEntry.pass_type)
        .all()
    )

    # Get all fields from class definition ==> more robbust in case of some change in the class itself
    grouped = defaultdict(lambda: {
        name: field.default
        for name, field in Resp_Statistics_Admin_CheckInsByType.model_fields.items()
    })

    # post-sorting of the data
    for (name, surname, amount) in resp:
        person = grouped[name, surname]
        person["name"] = name
        person["surname"] = surname
        
        # Calculate each type of the checkin separatelly (grouped by the types of the pass)
        person["entries_total"] += amount

    result = list(grouped.values())
    return result

@app.get("statistics/instructor/self_checkins/today/{card_id}")
def get_statistics_instructor_self_checkins_today(card_id: str):
    pass
#===========================================================

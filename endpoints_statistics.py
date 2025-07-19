from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session



import project_utils as utils
#===========================================================

router = APIRouter()
#===========================================================

@router.get("statistics/")
def get_statistics_():
    pass
#===========================================================



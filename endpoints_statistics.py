from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from models import CheckIn, Member
import project_utils as utils
from schemas import Req_Statistics_InstructorCheckInsDetailed, Req_Statistics_InstructorsCheckIns, Resp_Paginated_Statistics_InstructorCheckInsDetailed, Resp_Statistics_InstructorCheckInsDetailed, Resp_Statistics_InstructorsCheckIns
#===========================================================

router = APIRouter()
#===========================================================

@router.post("/statistics/instructors_checkins",
             response_model=list[Resp_Statistics_InstructorsCheckIns])
def post_statistics_admin_instructors_checkins(req: Req_Statistics_InstructorsCheckIns,
                                               db: Session = Depends(utils.get_db_checkins)):
    results = (
        db.query(CheckIn.validated_by_card_id,
                 CheckIn.validated_by_name, 
                 CheckIn.validated_by_surnamename,
                 func.count().label("count"))
        .filter(CheckIn.date_time.between(req.date_from, req.date_to),
                CheckIn.is_successful.is_(True))
        .order_by(CheckIn.date_time, CheckIn.validated_by_card_id)
        .all()
    )
    return results

@router.post("/statistics/instructor_checkins/detailed",
             response_model=Resp_Paginated_Statistics_InstructorCheckInsDetailed)
def post_statistics_admin_instructors_checkins_detailed(req: Req_Statistics_InstructorCheckInsDetailed,
                                                        db: Session = Depends(utils.get_db_checkins)):
    
    # Validate and correcr input if needed
    page = max(1, req.page)
    page_size = min(max(1, req.page_size), 200)

    # Make an query
    query = (
        db.query(CheckIn.member_name,
                 CheckIn.member_surname,
                 CheckIn.date_time,
                 CheckIn.is_successful,
                 CheckIn.rejected_reason)
        .filter(CheckIn.validated_by_card_id == req.validated_by_card_id,
                CheckIn.date_time.between(req.date_from, req.date_to))
        .order_by(CheckIn.date_time)
    )

    # Get total amount
    total: int = query.count()
    remaining: int = max(0, total - page * page_size)

    # Get all items --> convert to proper form
    result = (
        query
        .offset(req.page * req.page_size)
        .limit(req.page_size)
        .all()
    )
    items = [Resp_Statistics_InstructorCheckInsDetailed(
        name=name,
        surname=surname,
        date_time=date_time,
        is_successful=is_successful,
        rejected_reason=rejected_reason,
    ) for (name, surname, date_time, is_successful, rejected_reason) in result]

    return Resp_Paginated_Statistics_InstructorCheckInsDetailed(
        total=total,
        page=page,
        page_size=page_size,
        remaining=remaining,
        items=items
    )
#===========================================================



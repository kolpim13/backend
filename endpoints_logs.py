from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from endpoints_passes import get_member_pass_active_internal_by_member_id

from models import CheckIn, ExternalProvider, Member, MemberPass
from schemas import Req_CheckIn_Add, Resp_ChecIn_Inst

import project_utils as utils
#===========================================================

router = APIRouter()
#===========================================================

@router.post("/logging/checkin",
             response_model=Resp_ChecIn_Inst,
             response_model_exclude_none=True,
             response_model_exclude_unset=True,
             status_code=status.HTTP_202_ACCEPTED)
def post_checkin_add(req: Req_CheckIn_Add,
                     db: Session = Depends(utils.get_db_members),
                     db_logging: Session = Depends(utils.get_db_checkins)):
    
    # Local variables to operate on
    is_successful = True
    rejected_reason = None
    current_time = datetime.now() 

    # Get all data from request
    member: Member = utils.get_member_by_card_id_with_raise(db, req.member_card_id)
    validator: Member = utils.get_member_by_card_id(db, req.validated_by_card_id)
    external_provider : ExternalProvider = utils.get_external_provider_by_id(db, req.external_provider_id)
    member_pass: MemberPass = get_member_pass_active_internal_by_member_id(db, req.member_card_id)

    # Assert last Checkin was done at least 5 minutes before
    if member.last_checkin_success and member.last_checkin_datetime:
        if member.last_checkin_success == True:
            time_window_seconds = 5 * 60 # 5 minutes in seconds
        else:
            time_window_seconds = 30

        seconds_since_last_scan = (current_time - member.last_checkin_datetime).seconds
        if seconds_since_last_scan <= time_window_seconds:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail="Too few time since last attempt." \
                                "Next attempt in {sec}".format(sec=time_window_seconds-seconds_since_last_scan))

    # Validate one of ExternalProvider or MemberPass still present
    if (not external_provider and
        not member_pass):
        is_successful = False
        rejected_reason = "No valid MemberPass and ExternalProvider"

    # Create -> fill in data about entry
    check_in = CheckIn()
    
    check_in.member_card_id = member.card_id
    check_in.member_name = member.name
    check_in.member_surname = member.surname 

    check_in.date_time = current_time 

    if validator:
        check_in.validated_by_card_id = validator.card_id
        check_in.validated_by_name = validator.name
        check_in.validated_by_surnamename = validator.surname

    if member_pass:
        # Write information
        check_in.member_pass_id = member_pass.id
        check_in.pass_id = member_pass.id
        check_in.pass_name = member_pass.pass_type_name
        check_in.is_ext_event_pass = member_pass.is_ext_event_pass
        check_in.ext_event_code = member_pass.ext_event_code

        # If memberPass is used --> utilize ExternalProvider info bounded to it.
        check_in.external_provider_id = member_pass.external_provider_id
        check_in.external_provider_name = member_pass.external_provider_name

        # Decrement amount of entries if needed
        if member_pass.entries_left:
            member_pass.entries_left = member_pass.entries_left - 1

    # utilize ExternalProvider information directly only if there is no MemberPass present. 
    if external_provider and not member_pass:
        check_in.external_provider_id = external_provider.id
        check_in.external_provider_name = external_provider.name

    check_in.is_successful = is_successful
    check_in.rejected_reason = rejected_reason

    # Update information about member and used pass 
    member.last_checkin_success = is_successful
    member.last_checkin_datetime = current_time

    db.commit()
    db.refresh(member)
    if member_pass: 
        db.refresh(member_pass)

    # Add new row to checkin history --> return response
    db_logging.add(check_in)
    db_logging.commit()
    db_logging.refresh(check_in)
    return check_in
#===========================================================

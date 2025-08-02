from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from models import Member, ExternalProvider, MemberPass, PassType
from schemas import Req_Create_ExternalProviders, Req_MemberPass_Add, Req_PassTypes_Create, Req_PassTypes_Update, Req_Update_ExternalProviders, Resp_Instance_ExternalProviders, Resp_MemberPass_Inst, Resp_PassTypes_Inst

import project_utils as utils
#===========================================================

""" UTILS: ExternalProvider
"""
def get_external_provider_by_name(db: Session, name: str) -> ExternalProvider:
    """ Since name is unique field this should be fast enough """
    return db.query(ExternalProvider).filter(ExternalProvider.name == name).first()

def get_extern_provider_by_name_not_deleted(db: Session, name: str) -> ExternalProvider:
    return db.query(ExternalProvider).filter(ExternalProvider.name == name, 
                                             ExternalProvider.is_deleted == False).first()

def get_external_provider_by_id(db: Session, id: int) -> ExternalProvider:
    """ Since name is unique field this should be fast enough """
    return db.query(ExternalProvider).filter(ExternalProvider.id == id).first()

def get_external_provider_by_id_not_deleted(db: Session, id: int) -> ExternalProvider:
    """ Since name is unique field this should be fast enough """
    return db.query(ExternalProvider).filter(ExternalProvider.id == id,
                                             ExternalProvider.is_deleted == False).first()

""" UTILS: PassTypes
"""
def get_pass_type_by_id(db: Session, id: int) -> PassType:
    """ Since name is unique field this should be fast enough """
    return db.query(PassType).filter(PassType.id == id).first()

def get_pass_type_by_name_not_deleted(db: Session, name: str) -> PassType:
    return db.query(PassType).filter(PassType.name == name, 
                                     PassType.is_deleted == False).first()

""" UTILS: memberPass
"""
def get_member_pass_active_internal_by_member_id(db: Session, member_card_id: str):
    """ For now only one active MemberPass is possible to have for one User --> 
        It is a good function to get current MemberPass
    """
    return db.query(MemberPass).filter(MemberPass.member_card_id == member_card_id,
                                       or_(
                                           MemberPass.expiration_date > date.today(),
                                           MemberPass.expiration_date.is_(None)
                                       ),
                                       or_(
                                           MemberPass.entries_left > 0,
                                           MemberPass.entries_left.is_(None)
                                       ),
                                       MemberPass.is_ext_event_pass.is_(False),
                                       MemberPass.is_closed.is_(False)).first()

def has_member_active_internal_pass(db: Session, member_card_id: str) -> bool:
    # Passes for external events are not counted.
    if db.query(MemberPass).filter(MemberPass.member_card_id == member_card_id,
                                   MemberPass.expiration_date > date.today(),
                                   MemberPass.entries_left > 0,
                                   MemberPass.is_ext_event_pass == False,
                                   MemberPass.is_closed == False).first():
        return True
    return False
#===========================================================

router = APIRouter()

""" EXTERNAL PROVIDERS
    Only admins (or users with same access level) should be able to use these endpoints.
    {Exception - GET endpoints}
"""
@router.post("/external_providers", 
             response_model=Resp_Instance_ExternalProviders, 
             status_code=status.HTTP_201_CREATED)
def post_external_provider_create(
                                  req: Req_Create_ExternalProviders,
                                  db: Session = Depends(utils.get_db_members)):
    # [TBD] Token is not used at the moment - to be add later as a link argument
    # token: str,

    # Check the name is unique
    if get_extern_provider_by_name_not_deleted(db, req.name) is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="External provider with given name already exists")
    
    # Create new ExternalProvider --> Add it to the database --> return newly created object
    provider = ExternalProvider(**req.model_dump())
    db.add(provider)
    db.commit()
    db.refresh(provider)
    return provider

@router.get("/external_providers/{id}",
            response_model=Resp_Instance_ExternalProviders,
            status_code=status.HTTP_200_OK)
def get_external_provider_id(id: int,
                          db: Session = Depends(utils.get_db_members)):
    provider = get_external_provider_by_id(db, id)
    if not provider:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="External provider with given ID does not exist")
    
    return provider

@router.get("/external_providers",
            response_model=list[Resp_Instance_ExternalProviders],
            status_code=status.HTTP_200_OK)
def get_external_provider(db: Session = Depends(utils.get_db_members)):
    return db.query(ExternalProvider).all()

@router.put("/external_providers",
            response_model=Resp_Instance_ExternalProviders,
            status_code=status.HTTP_200_OK)
def put_external_provider_update(req: Req_Update_ExternalProviders,
                                 db: Session = Depends(utils.get_db_members)):
    provider = get_external_provider_by_id(db, req.id)
    if not provider:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="External provider with given ID does not exist")
    
    # Check if new name provided --> if it is unique
    if db.query(ExternalProvider).filter(
        ExternalProvider.id != req.id,
        ExternalProvider.name == req.name,
        ExternalProvider.is_deleted is False).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="External provider with given name already exists")

    # Update data
    update_data = req.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(provider, key, value)

    # Save changes in Database
    db.commit()
    db.refresh(provider)
    return provider

def delete_external_provider():
    pass
#===========================================================

""" PASS TYPES
    Only admins (or users with same access level) should be able to use these endpoints.
    {Exception - GET endpoints}
"""
@router.post("/pass_types",
             response_model=Resp_PassTypes_Inst,
             status_code=status.HTTP_201_CREATED)
def post_pass_types_create(req: Req_PassTypes_Create,
                           db: Session = Depends(utils.get_db_members)):
    # [TBD] Token is not used at the moment - to be add later as a link argument
    # token: str,

    # Check the name is unique
    if get_pass_type_by_name_not_deleted(db, req.name) is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Pass type with given name already exists")
    
    # Create new PassType --> Add it to the database --> return newly created object
    pass_type = PassType(**req.model_dump())
    db.add(pass_type)
    db.commit()
    db.refresh(pass_type)
    return pass_type

@router.get("/pass_types",
            response_model=list[Resp_PassTypes_Inst],
            status_code=status.HTTP_200_OK)
def get_pass_types(db: Session = Depends(utils.get_db_members)):
    return db.query(PassType).all()

@router.put("/pass_types",
            response_model=Resp_PassTypes_Inst,
            status_code=status.HTTP_200_OK)
def put_pass_types_update(req: Req_PassTypes_Update,
                          db: Session = Depends(utils.get_db_members)):
    pass_type = get_pass_type_by_id(db, req.id)
    if not pass_type:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="External provider with given ID does not exist")
    
    # Check if new name provided --> if it is unique
    if db.query(PassType).filter(
        PassType.id != req.id,
        PassType.name == req.name,
        PassType.is_deleted is False).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="External provider with given name already exists")

    # Update data
    update_data = req.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(pass_type, key, value)

    # Save changes in Database
    db.commit()
    db.refresh(pass_type)
    return pass_type
#===========================================================

""" MEMBER PASS
"""
@router.post("/member_pass",
             response_model=Resp_MemberPass_Inst,
             status_code=status.HTTP_201_CREATED)
def post_member_pass_add(req: Req_MemberPass_Add,
                         db: Session = Depends(utils.get_db_members)):
    
    # Check member exist
    member: Member = utils.get_member_by_card_id(db, req.member_card_id)
    if not member:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="No member found")

    # Check member has no active pass
    if has_member_active_internal_pass(db, req.member_card_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Member has active pass already")
    
    # Assemble new MemberPass --> return it
    pass_type = get_pass_type_by_id(db, req.pass_type_id)
    args = {
        'member_card_id': req.member_card_id,
        'pass_type_id': req.pass_type_id,
        'pass_type_name': pass_type.name,
        'purchase_date': date.today(),
        'expiration_date': date.today() + timedelta(days=pass_type.validity_days),
        'entries_left': pass_type.maximum_entries,
        'requires_external_auth': pass_type.requires_external_auth,
        'external_provider_id': pass_type.external_provider_id,
        'external_provider_name': pass_type.external_provider_name,
        'is_ext_event_pass': pass_type.is_ext_event_pass,
        'ext_event_code': pass_type.ext_event_code,
        'status': None,
        'is_closed': False,
    }
    member_pass = MemberPass(**args)
    db.add(member_pass)
    db.commit()
    db.refresh(member_pass)
    return member_pass

@router.get("/member_pass/active/{member_card_id}",
            response_model=list[Resp_MemberPass_Inst],
            status_code=status.HTTP_200_OK)
def get_member_pass_active(member_card_id:str,
                            db: Session = Depends(utils.get_db_members)):
    return db.query(MemberPass).filter(MemberPass.member_card_id == member_card_id,
                                       MemberPass.expiration_date > date.today(),
                                       MemberPass.entries_left > 0,
                                       MemberPass.is_closed == False).all()
#===========================================================

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from models import ExternalProvider, PassType
from schemas import Req_Create_ExternalProviders, Req_PassTypes_Create, Req_PassTypes_Update, Req_Update_ExternalProviders, Resp_Instance_ExternalProviders, Resp_PassTypes_Inst

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
#===========================================================

""" EXTERNAL PROVIDERS
    Only admins (or users with same access level) should be able to use these endpoints.
    {Exception - GET endpoints}
"""

router = APIRouter()

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
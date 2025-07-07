from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from models import ExternalProvider
from schemas import Req_Create_ExternalProviders, Req_Update_ExternalProviders, Resp_Instance_ExternalProviders

import project_utils as utils
#===========================================================

def get_external_provider_by_name(db: Session, name: str) -> ExternalProvider:
    """ Since name is unique field this should be fast enough """
    return db.query(ExternalProvider).filter(ExternalProvider.name == name).first()

def get_external_provider_by_id(db: Session, id: int) -> ExternalProvider:
    """ Since name is unique field this should be fast enough """
    return db.query(ExternalProvider).filter(ExternalProvider.id == id).first()
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
    if get_external_provider_by_name(db, req.name) is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="External provider with given name already exists")
    
    # Create new ExternalProvider --> Add it to the database
    provider = ExternalProvider(**req.model_dump())
    db.add(provider)
    db.commit()
    db.refresh(provider)

    # return data
    return provider

@router.get("/external_providers/{id}",
            response_model=Resp_Instance_ExternalProviders,
            status_code=status.HTTP_200_OK)
def get_external_provider(id: int,
                          db: Session = Depends(utils.get_db_members)):
    provider = get_external_provider_by_id(db, id)
    if not provider:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="External provider with given ID does not exist")
    
    return provider

@router.get("/external_providers",
            response_model=list[Resp_Instance_ExternalProviders],
            status_code=status.HTTP_200_OK)
def get_external_provider_all(db: Session = Depends(utils.get_db_members)):
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
        ExternalProvider.name == req.name).first():
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
#===========================================================
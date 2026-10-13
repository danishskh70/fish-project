
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.api.deps import get_db
from app.db.session import SessionLocal
from app.schemas.fish_type import (
    FishTypeCreate,
    FishTypeRead,
    FishTypeUpdate,
)
from app.services.fish_type import (
    DuplicateFishTypeNameError,
    FishTypeNotFoundError,
    create_fish_type,
    deactivate_fish_type,
    list_fish_types,
    update_fish_type,
    activate_fish_type,
)

router=APIRouter(prefix="/fish-types",tags=["Fish Types"])


@router.get("/",response_model=list[FishTypeRead])
def get_fish_types(db:Session=Depends(get_db)):
    return list_fish_types(db)

@router.post("/",response_model=FishTypeRead,status_code=status.HTTP_201_CREATED,)
def post_fish_type(data:FishTypeCreate,db:Session=Depends(get_db)):
    try:
        return create_fish_type(db,data)
    except DuplicateFishTypeNameError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,detail="A fish type with this name already exists.")
    
@router.patch("/{fish_type_id}",response_model=FishTypeRead)
def patch_fish_type(fish_type_id:int,data:FishTypeUpdate,db:Session=Depends(get_db)):
    try:
        return update_fish_type(db=db,fish_type_id=fish_type_id,data=data)
    except FishTypeNotFoundError:
        raise HTTPException(status_code=404,detail="Fish type not found.")
    except DuplicateFishTypeNameError:
        raise HTTPException(status_code=409,detail="A fish type with this name already exists.")


@router.post("/{fish_type_id}/deactivate",response_model=FishTypeRead)
def post_deactivate_fish_type(fish_type_id:int,db:Session=Depends(get_db)):
    try:
        return deactivate_fish_type(db,fish_type_id)
    except FishTypeNotFoundError:
        raise HTTPException(status_code=404,detail="Fish type not found.")

@router.post("/{fish_type_id}/activate", response_model=FishTypeRead)
def post_activate_fish_type(
    fish_type_id: int,
    db: Session = Depends(get_db),
):
    try:
        return activate_fish_type(db, fish_type_id)
    except FishTypeNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="Fish type not found.",
        )
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from db_utils.db import get_db
from db_utils.models import User
from auth.auth_router import get_current_traveler
from schemas import TravelerOut

router = APIRouter()

@router.get("/me", response_model=TravelerOut)
def get_me(
    traveler: User = Depends(get_current_traveler),
    db: Session = Depends(get_db)
):
    return traveler

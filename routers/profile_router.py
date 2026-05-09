router = APIRouter()

from fastapi import APIRouter, Depends
from auth.auth_router import get_current_traveler




@router.get("/me", tags=["Auth"])
def get_profile(current_user = Depends(get_current_traveler)):

    return {
        "id": current_user.id,
        "email": current_user.email,
        "name": current_user.name
    }

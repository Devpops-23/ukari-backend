from fastapi import APIRouter, Depends
from auth.auth_router import get_current_user

router = APIRouter()

@router.get("/me", tags=["Auth"])
def get_my_profile(current_user = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "name": current_user.name
    }

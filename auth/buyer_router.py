from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime, timedelta
from jose import jwt


from db_utils.db import get_db
from db_utils.models import User
from utils.auth import get_password_hash, verify_password


SECRET_KEY = "your-secret-key"
ALGORITHM = "HS256"

router = APIRouter()


# -------------------------------
# Signup + Login Models
# -------------------------------
class SignupRequest(BaseModel):
    email: str
    password: str
    full_name: str
    role: str  # "buyer" or "traveler"


class LoginRequest(BaseModel):
    email: str
    password: str


# -------------------------------
# SIGNUP (Buyer or Traveler)
# -------------------------------
@router.post("/signup")
def signup(body: SignupRequest, db: Session = Depends(get_db)):

    if body.role not in ["buyer", "traveler"]:
        raise HTTPException(status_code=400, detail="Role must be 'buyer' or 'traveler'")

    existing = db.query(User).filter(User.email == body.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    new_user = User(
        email=body.email,
        password_hash=hash_password(body.password),
        full_name=body.full_name,
        role=body.role,
        created_at=datetime.utcnow()
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {
        "status": "success",
        "user_id": new_user.id,
        "role": new_user.role
    }


# -------------------------------
# LOGIN (Works for both roles)
# -------------------------------
@router.post("/login")
def login(body: LoginRequest, db: Session = Depends(get_db)):

    user = db.query(User).filter(User.email == body.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=400, detail="Incorrect password")

    payload = {
        "sub": str(user.id),
        "exp": datetime.utcnow() + timedelta(days=7)
    }

    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

    return {
        "status": "success",
        "token": token,
        "role": user.role
    }

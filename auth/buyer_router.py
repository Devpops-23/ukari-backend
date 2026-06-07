from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime, timedelta
import jwt

from db_utils.db import get_db
from db_utils.models import User
from utils.auth import hash_password, verify_password

SECRET_KEY = "your-secret-key"
ALGORITHM = "HS256"

router = APIRouter()


# -------------------------------
# Request Models
# -------------------------------
class BuyerSignupRequest(BaseModel):
    email: str
    password: str
    full_name: str


class BuyerLoginRequest(BaseModel):
    email: str
    password: str


# -------------------------------
# Buyer Signup
# -------------------------------
@router.post("/buyer/signup")
def buyer_signup(body: BuyerSignupRequest, db: Session = Depends(get_db)):

    existing = db.query(User).filter(User.email == body.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    new_user = User(
        email=body.email,
        password_hash=hash_password(body.password),
        full_name=body.full_name,
        role="buyer",
        created_at=datetime.utcnow()
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {"status": "success", "buyer_id": new_user.id}


# -------------------------------
# Buyer Login
# -------------------------------
@router.post("/buyer/login")
def buyer_login(body: BuyerLoginRequest, db: Session = Depends(get_db)):

    user = db.query(User).filter(User.email == body.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=400, detail="Incorrect password")

    if user.role != "buyer":
        raise HTTPException(status_code=403, detail="Not a buyer account")

    payload = {
        "sub": str(user.id),
        "exp": datetime.utcnow() + timedelta(days=7)
    }

    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

    return {"status": "success", "token": token}

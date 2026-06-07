print("🚨 LOADED AUTH ROUTER FROM:", __file__)

from datetime import datetime, timedelta
import os

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db_utils.db import get_db
from db_utils.models import User
from utils.auth import get_password_hash, verify_password

router = APIRouter(tags=["Auth"])

# ---------------------------
# JWT CONFIG
# ---------------------------
SECRET_KEY = os.getenv("JWT_SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

if not SECRET_KEY:
    print("🚨 WARNING: JWT_SECRET_KEY is not set in environment!")

oauth2_scheme = HTTPBearer()


# ---------------------------
# Pydantic Models
# ---------------------------
class SignupRequest(BaseModel):
    email: str
    password: str
    full_name: str
    role: str  # "buyer" or "traveler"


class LoginRequest(BaseModel):
    email: str
    password: str


# ---------------------------
# JWT Token Creation
# ---------------------------
def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


# ---------------------------
# SIGNUP
# ---------------------------
@router.post("/signup")
def signup(body: SignupRequest, db: Session = Depends(get_db)):

    if body.role not in ["buyer", "traveler"]:
        raise HTTPException(status_code=400, detail="Role must be 'buyer' or 'traveler'")

    existing = db.query(User).filter(User.email == body.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    new_user = User(
        email=body.email,
        hashed_password=get_password_hash(body.password),
        full_name=body.full_name,
        role=body.role,
        created_at=datetime.utcnow()
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {
        "message": "Signup successful",
        "user_id": new_user.id
    }


# ---------------------------
# LOGIN
# ---------------------------
@router.post("/login")
def login(data: LoginRequest, db: Session = Depends(get_db)):

    user = db.query(User).filter(User.email == data.email).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not verify_password(data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect password")

    token_data = {
        "sub": str(user.id),
        "exp": datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    }

    token = jwt.encode(token_data, SECRET_KEY, algorithm=ALGORITHM)

    return {
        "access_token": token,
        "token_type": "bearer",
        "user_id": user.id,
        "email": user.email,
        "role": user.role,
        "full_name": user.full_name,
    }


# ---------------------------
# TRAVELER AUTH DEPENDENCY
# ---------------------------
def get_current_traveler(
    credentials: HTTPAuthorizationCredentials = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:

    token = credentials.credentials

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str | None = payload.get("sub")

        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")

    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid authentication token")

    user = db.query(User).filter(User.id == int(user_id)).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.role != "traveler":
        raise HTTPException(status_code=403, detail="Only travelers can perform this action")

    return user





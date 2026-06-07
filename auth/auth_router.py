print("🚨 LOADED AUTH ROUTER FROM:", __file__)

from datetime import datetime, timedelta
import os

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db_utils.db import get_db
from db_utils.models import User
from utils.auth import get_password_hash

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
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ---------------------------
# Pydantic Models
# ---------------------------
class LoginRequest(BaseModel):
    email: str
    password: str


class SignupRequest(BaseModel):
    email: str
    password: str
    full_name: str
    role: str # "buyer" or "traveler"


# ---------------------------
# Utility functions
# ---------------------------
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


# ---------------------------
# Signup
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
        role=body.role,  # <-- THIS NOW WORKS
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
# Login
# ---------------------------
@router.post("/login")
def login(data: LoginRequest, db: Session = Depends(get_db)):
    print("LOGIN DEBUG: entered login function")
    print("DEBUG SECRET KEY AT LOGIN:", SECRET_KEY)

    user = db.query(User).filter(User.email == data.email).first()

    print("DEBUG: email received:", data.email)
    print("DEBUG: user found:", user)
    print("DEBUG: stored hash:", user.hashed_password if user else None)

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


print("DEBUG SECRET KEY (module load):", SECRET_KEY)


# ---------------------------
# Traveler Authentication Dependency
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




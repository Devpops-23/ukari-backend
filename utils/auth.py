from datetime import datetime, timedelta
import os
from typing import Optional

from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError, ExpiredSignatureError
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from db_utils.db import get_db
from db_utils.models import User

# ---------------------------
# JWT CONFIG
# ---------------------------
SECRET_KEY = os.getenv("JWT_SECRET_KEY") or os.getenv("JWT_SECRET") or "dev_fallback_secret_key_6TFQfWNH4_nxgEkt19LHXYgjjtaIyejT7VUdP6OCuZYLZTHwI59WIhPltFtYTAvljefoMC98DrG7pvpOVMLwJQ"
ALGORITHM = "HS256"

# ---------------------------
# PASSWORD HASHING
# ---------------------------
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = HTTPBearer(auto_error=False)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


# ---------------------------
# CREATE ACCESS TOKEN
# ---------------------------
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(days=7))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


# ---------------------------
# GET CURRENT USER (Dependency + Direct callable)
# ---------------------------
def get_current_user(
    db: Session = Depends(get_db),
    token: Optional[str] = None,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(oauth2_scheme),
) -> User:
    raw_token = None
    if credentials and credentials.credentials:
        raw_token = credentials.credentials
    elif token:
        raw_token = token

    if not raw_token:
        raise HTTPException(
            status_code=401,
            detail="Authentication token required via Bearer header or token parameter",
        )

    try:
        payload = jwt.decode(raw_token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Session expired. Please log in again.")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return user


# ---------------------------
# GET CURRENT TRAVELER
# ---------------------------
def get_current_traveler(
    user: User = Depends(get_current_user),
) -> User:
    if user.role != "traveler":
        raise HTTPException(status_code=403, detail="Only travelers can perform this action")
    return user


# ---------------------------
# GET CURRENT ADMIN
# ---------------------------
def get_current_admin(
    user: User = Depends(get_current_user),
) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user

get_current_admin_user = get_current_admin


# ---------------------------
# GET CURRENT BUYER
# ---------------------------
def get_current_buyer(
    user: User = Depends(get_current_user),
) -> User:
    if user.role != "buyer":
        raise HTTPException(status_code=403, detail="Only buyers can perform this action")
    return user

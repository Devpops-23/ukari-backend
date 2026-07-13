from datetime import datetime, timedelta
import os

from fastapi import HTTPException
from jose import jwt, JWTError
from passlib.context import CryptContext

from db_utils.models import User

# ---------------------------
# JWT CONFIG
# ---------------------------
SECRET_KEY = os.getenv("JWT_SECRET_KEY")
ALGORITHM = "HS256"

if not SECRET_KEY:
 print("WARNING: JWT_SECRET_KEY is not set in environment!")

# ---------------------------
# PASSWORD HASHING
# ---------------------------
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_current_traveler(db, token: str) -> User:
    user = get_current_user(db, token)

    if user.role != "traveler":
        raise HTTPException(status_code=403, detail="Only travelers can perform this action")

    return user

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


# ---------------------------
# CREATE ACCESS TOKEN
# ---------------------------
def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(days=7))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


# ---------------------------
# GET CURRENT USER FROM TOKEN
# ---------------------------
def get_current_user(db, token: str) -> User:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return user



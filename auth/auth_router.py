from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from database import get_db
from models import Traveler
from passlib.context import CryptContext
from auth.jwt_handler import create_token

router = APIRouter()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class SignupRequest(BaseModel):
    email: EmailStr
    name: str
    password: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

@router.post("/signup")
def signup(payload: SignupRequest, db: Session = Depends(get_db)):
    # Check if email exists
    existing = db.query(Traveler).filter(Traveler.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed_pw = pwd_context.hash(payload.password)

    traveler = Traveler(
    name=payload.name,
    email=payload.email,
    password_hash=hash_password(payload.password)
)

    

    db.add(traveler)
    db.commit()
    db.refresh(traveler)

    token = create_token(traveler.id)

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": traveler.id,
            "name": traveler.name,
            "email": traveler.email
        }
    }

@router.post("/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    traveler = db.query(Traveler).filter(Traveler.email == payload.email).first()

    if not traveler or not pwd_context.verify(payload.password, traveler.password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_token(traveler.id)

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": traveler.id,
            "name": traveler.name,
            "email": traveler.email
        }
    }

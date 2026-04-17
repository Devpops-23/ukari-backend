from auth.jwt_handler import create_token
from passlib.context import CryptContext
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import Traveler

router = APIRouter(
    prefix="/travelers",
    tags=["Travelers"]
)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

@router.get("/")
def list_travelers(db: Session = Depends(get_db)):
    travelers = db.query(Traveler).all()
    return travelers

@router.post("/signup")
def traveler_signup(name: str, email: str, password: str, db: Session = Depends(get_db)):
    existing = db.query(Traveler).filter(Traveler.email == email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed = pwd_context.hash(password)

    traveler = Traveler(
        name=name,
        email=email,
        password_hash=hashed
    )

    db.add(traveler)
    db.commit()
    db.refresh(traveler)

    return {"message": "Traveler created", "traveler_id": traveler.id}
@router.post("/login")
def traveler_login(email: str, password: str, db: Session = Depends(get_db)):
    traveler = db.query(Traveler).filter(Traveler.email == email).first()
    if not traveler:
        raise HTTPException(status_code=404, detail="Traveler not found")

    if not pwd_context.verify(password, traveler.password_hash):
        raise HTTPException(status_code=401, detail="Invalid password")

    token = create_token(traveler.id)

    return {
        "access_token": token,
        "traveler_id": traveler.id
    }

from jose import jwt
from datetime import datetime, timedelta
from os import getenv

SECRET = getenv("JWT_SECRET")
ALGORITHM = "HS256"

def create_token(traveler_id: int):
    payload = {
        "sub": str(traveler_id),
        "exp": datetime.utcnow() + timedelta(days=7)
    }
    return jwt.encode(payload, SECRET, algorithm=ALGORITHM)

def decode_token(token: str):
    return jwt.decode(token, SECRET, algorithms=[ALGORITHM])


from fastapi import HTTPException
from jose import jwt, JWTError
from db_utils.models import User
from config import SECRET, ALGORITHM

def get_current_user(db, token: str):
    try:
        payload = jwt.decode(token, SECRET, algorithms=[ALGORITHM])
        user_id = int(payload.get("sub"))
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return user


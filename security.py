# security.py
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer
from jose import jwt, JWTError
from config import SECRET_KEY, ALGORITHM

security = HTTPBearer()

def get_current_user(credentials=Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("sub") != "admin":
            raise HTTPException(status_code=401, detail="Invalid user")
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
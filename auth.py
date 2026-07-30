# auth.py
from datetime import datetime, timedelta
from jose import jwt
from config import SECRET_KEY, ALGORITHM, TOKEN_EXPIRE_HOURS

def create_token():
    payload = {
        "sub": "admin",
        "exp": datetime.utcnow() + timedelta(hours=TOKEN_EXPIRE_HOURS)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
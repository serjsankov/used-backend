# api/registration.py
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from config import ADMIN_USERNAME, ADMIN_PASSWORD
from auth import create_token
from security import get_current_user

router = APIRouter()

class LoginData(BaseModel):
    username: str
    password: str

@router.post("/login")  # путь внутри роутера
def login(data: LoginData):
    if data.username != ADMIN_USERNAME or data.password != ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_token()
    return {"access_token": token, "token_type": "bearer"}

@router.get("/dashboard")  # путь внутри роутера
def dashboard(user=Depends(get_current_user)):
    return {"msg": "Welcome admin!"}
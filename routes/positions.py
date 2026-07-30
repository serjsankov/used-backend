from fastapi import APIRouter, Depends
from routes.employees import telegram_user
from db.db import get_db_conn

router = APIRouter()

@router.post("/")
async def create_position(data: dict, user=Depends(telegram_user), db=Depends(get_db_conn)):
    await db.execute("INSERT INTO positions (title) VALUES (%s)", (data["title"],))
    return {"status": "ok"}

@router.get("/")
async def list_positions(user=Depends(telegram_user), db=Depends(get_db_conn)):
    await db.execute("SELECT * FROM positions")
    result = await db.fetchall()
    return result
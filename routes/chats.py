from fastapi import APIRouter, Depends
from routes.employees import telegram_user
from db.db import get_db_conn

router = APIRouter()

@router.post("/")
async def create_chat(data: dict, user=Depends(telegram_user), db=Depends(get_db_conn)):
    await db.execute(
        "INSERT INTO chats (title, tg_chat_id) VALUES (%s, %s)",
        (data["title"], data["tg_chat_id"])
    )
    return {"status": "ok"}

@router.get("/")
async def list_chats(user=Depends(telegram_user), db=Depends(get_db_conn)):
    await db.execute("SELECT * FROM chats")
    result = await db.fetchall()
    return result
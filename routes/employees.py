from fastapi import APIRouter, Depends, HTTPException, Header
from db.db import get_db_conn

router = APIRouter()

# Простая проверка пользователя: Telegram или Demo
async def telegram_user(
    x_telegram_init_data: str = Header(None),
    x_demo_user: str = Header(None),
):
    if x_demo_user:
        return {"id": 12345, "username": "demo_user"}
    if not x_telegram_init_data:
        raise HTTPException(status_code=401, detail="Unauthorized")
    # Тут должна быть реальная проверка init_data Telegram
    return {"id": 0, "username": "telegram_user"}

@router.get("/")
async def list_employees(user=Depends(telegram_user), db=Depends(get_db_conn)):
    await db.execute("SELECT * FROM employees")
    rows = await db.fetchall()
    return [dict(row) for row in rows]

@router.post("/")
async def create_employee(data: dict, user=Depends(telegram_user), db=Depends(get_db_conn)):
    await db.execute(
        "INSERT INTO employees (full_name, phone, username, tg_id) VALUES (%s, %s, %s, %s)",
        (data["full_name"], data.get("phone"), data.get("username"), data.get("tg_id"))
    )
    return {"status": "ok"}
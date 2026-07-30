from pydantic import BaseModel
from typing import Optional
from datetime import date

# Сотрудники
# async def get_employees(cur):
#     await cur.execute("SELECT * FROM employees")
#     return await cur.fetchall()

# async def add_employee(cur, name, phone, username, position_id, manager_id):
#     await cur.execute(
#         "INSERT INTO employees (name, phone, username, position_id, manager_id) "
#         "VALUES (%s, %s, %s, %s, %s)",
#         (name, phone, username, position_id, manager_id)
#     )

class UserRegister(BaseModel):
    gender: str
    phone_director: Optional[int] = None
    director: str
    phone_manager: Optional[int] = None
    manager: str
    department: str
    role: str
    birth_date: Optional[date] = None
    phone: Optional[int] = None
    full_name: str
    username: str
    tg_id: int
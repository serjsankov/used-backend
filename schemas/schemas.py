from pydantic import BaseModel
from typing import Union, List

# --- Chat
class ChatBase(BaseModel):
    title: str
    link: str
    type: str
    position_id: Union[int, None] = None

class ChatCreate(ChatBase): pass

class ChatOut(ChatBase):
    id: int
    class Config:
        orm_mode = True

# --- Position
class PositionBase(BaseModel):
    name: str

class PositionCreate(PositionBase): pass

class PositionOut(PositionBase):
    id: int
    class Config:
        orm_mode = True

# --- Employee
class EmployeeBase(BaseModel):
    full_name: str
    phone: str
    username: Union[str, None] = None
    position_id: Union[int, None] = None
    manager_id: Union[int, None] = None

class EmployeeCreate(EmployeeBase):
    tg_id: str

class EmployeeUpdate(BaseModel):
    full_name: Union[str, None] = None
    phone: Union[str, None] = None
    username: Union[str, None] = None
    position_id: Union[int, None] = None
    manager_id: Union[int, None] = None

class EmployeeOut(EmployeeBase):
    id: int
    tg_id: str
    class Config:
        orm_mode = True

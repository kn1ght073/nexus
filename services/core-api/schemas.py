from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

# --- Token Schemas (Mock Auth) ---
class Token(BaseModel):
    access_token: str
    token_type: str

# --- Device Schemas ---
class DeviceBase(BaseModel):
    name: str
    platform: str

class DeviceCreate(DeviceBase):
    pass

class Device(DeviceBase):
    id: int
    owner_id: int
    class Config:
        from_attributes = True

# --- Task Schemas ---
class TaskBase(BaseModel):
    title: str
    description: Optional[str] = None
    status: str = "pending"

class TaskCreate(TaskBase):
    project_id: Optional[int] = None

class Task(TaskBase):
    id: int
    created_at: datetime
    project_id: Optional[int] = None
    class Config:
        from_attributes = True

# --- Note Schemas ---
class NoteBase(BaseModel):
    title: str
    content: str

class NoteCreate(NoteBase):
    project_id: Optional[int] = None

class Note(NoteBase):
    id: int
    created_at: datetime
    project_id: Optional[int] = None
    class Config:
        from_attributes = True

# --- Project Schemas ---
class ProjectBase(BaseModel):
    title: str
    description: Optional[str] = None

class ProjectCreate(ProjectBase):
    pass

class Project(ProjectBase):
    id: int
    owner_id: int
    tasks: List[Task] = []
    notes: List[Note] = []
    class Config:
        from_attributes = True

# --- User Schemas ---
class UserBase(BaseModel):
    email: str

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: int
    is_active: bool
    devices: List[Device] = []
    projects: List[Project] = []
    class Config:
        from_attributes = True

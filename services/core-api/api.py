# pyrefly: ignore [missing-import]
from fastapi import APIRouter, Depends, HTTPException
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import Session
from typing import List

import models
import schemas
from database import get_db

router = APIRouter()

# --- Mock Auth ---
@router.post("/auth/login", response_model=schemas.Token)
def login(user: schemas.UserCreate, db: Session = Depends(get_db)):
    # Mocking authentication for MVP
    # In reality, verify password and issue JWT
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if not db_user:
        # Auto-create user for testing purposes if not exists
        db_user = models.User(email=user.email, hashed_password="mocked_hash")
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
    
    return {"access_token": f"mock_token_for_{db_user.id}", "token_type": "bearer"}

# Mock dependency to get current user
def get_current_user(db: Session = Depends(get_db)):
    # For MVP we just return the first user or create a dummy one
    user = db.query(models.User).first()
    if not user:
        user = models.User(email="test@nexus.local", hashed_password="mocked_hash")
        db.add(user)
        db.commit()
        db.refresh(user)
    return user

# --- Devices ---
@router.post("/devices/register", response_model=schemas.Device)
def register_device(device: schemas.DeviceCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    db_device = models.Device(**device.model_dump(), owner_id=current_user.id)
    db.add(db_device)
    db.commit()
    db.refresh(db_device)
    return db_device

@router.get("/devices", response_model=List[schemas.Device])
def get_devices(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return db.query(models.Device).filter(models.Device.owner_id == current_user.id).all()

# --- Projects ---
@router.post("/projects", response_model=schemas.Project)
def create_project(project: schemas.ProjectCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    db_project = models.Project(**project.model_dump(), owner_id=current_user.id)
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    return db_project

@router.get("/projects", response_model=List[schemas.Project])
def get_projects(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return db.query(models.Project).filter(models.Project.owner_id == current_user.id).all()

@router.patch("/projects/{project_id}/status", response_model=schemas.Project)
def update_project_status(project_id: int, status_update: schemas.StatusUpdate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    db_project = db.query(models.Project).filter(models.Project.id == project_id, models.Project.owner_id == current_user.id).first()
    if not db_project:
        raise HTTPException(status_code=404, detail="Project not found")
    db_project.status = status_update.status
    db.commit()
    db.refresh(db_project)
    return db_project

# --- Tasks ---
@router.post("/tasks", response_model=schemas.Task)
def create_task(task: schemas.TaskCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    # Ensure project belongs to user if specified
    if task.project_id:
        proj = db.query(models.Project).filter(models.Project.id == task.project_id, models.Project.owner_id == current_user.id).first()
        if not proj:
            raise HTTPException(status_code=404, detail="Project not found")
    
    db_task = models.Task(**task.model_dump())
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task

@router.get("/tasks", response_model=List[schemas.Task])
def get_tasks(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    # For MVP, get all tasks (in reality, filter by user via projects or direct link)
    return db.query(models.Task).all()

@router.patch("/tasks/{task_id}/status", response_model=schemas.Task)
def update_task_status(task_id: int, status_update: schemas.StatusUpdate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    db_task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")
    db_task.status = status_update.status
    db.commit()
    db.refresh(db_task)
    return db_task

# --- Notes ---
@router.post("/notes", response_model=schemas.Note)
def create_note(note: schemas.NoteCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    if note.project_id:
        proj = db.query(models.Project).filter(models.Project.id == note.project_id, models.Project.owner_id == current_user.id).first()
        if not proj:
            raise HTTPException(status_code=404, detail="Project not found")
            
    db_note = models.Note(**note.model_dump())
    db.add(db_note)
    db.commit()
    db.refresh(db_note)
    return db_note

@router.get("/notes", response_model=List[schemas.Note])
def get_notes(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return db.query(models.Note).all()

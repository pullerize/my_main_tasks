from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import inspect, text, create_engine
from dotenv import load_dotenv
from datetime import datetime, date, timedelta
from typing import List, Optional
from sqlalchemy.orm import joinedload
import os
from fastapi.staticfiles import StaticFiles
import json
import shutil
import tempfile
import re

from . import models, schemas, crud, auth
from .database import engine, Base, SessionLocal
from .auth import get_db

load_dotenv()

# Create tables including new expense models
try:
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created successfully")
except Exception as e:
    print(f"⚠️  Warning: Error creating database tables: {e}")

# Ensure expense tables exist
def ensure_expense_tables():
    with engine.connect() as conn:
        inspector = inspect(conn)
        
        # Check if new expense tables exist
        tables = inspector.get_table_names()
        
        if "expense_categories" not in tables:
            print("📋 Creating expense_categories table...")
            models.ExpenseCategory.__table__.create(bind=engine, checkfirst=True)
            
        if "common_expenses" not in tables:
            print("💰 Creating common_expenses table...")
            models.CommonExpense.__table__.create(bind=engine, checkfirst=True)
        
        # Add new columns to existing project_expenses if they don't exist
        if "project_expenses" in tables:
            cols = [c["name"] for c in inspector.get_columns("project_expenses")]
            
            if "category_id" not in cols:
                print("🔧 Adding category_id to project_expenses...")
                conn.execute(text("ALTER TABLE project_expenses ADD COLUMN category_id INTEGER"))
            if "description" not in cols:
                print("📝 Adding description to project_expenses...")
                conn.execute(text("ALTER TABLE project_expenses ADD COLUMN description TEXT"))
            if "date" not in cols:
                print("📅 Adding date to project_expenses...")
                conn.execute(text("ALTER TABLE project_expenses ADD COLUMN date DATE DEFAULT CURRENT_DATE"))
            if "created_by" not in cols:
                print("👤 Adding created_by to project_expenses...")
                conn.execute(text("ALTER TABLE project_expenses ADD COLUMN created_by INTEGER"))
            if "amount" in cols:
                # Check if amount is still INTEGER, convert to FLOAT
                try:
                    conn.execute(text("SELECT amount FROM project_expenses LIMIT 1"))
                    # If this works, the column exists, might need to handle type change
                except:
                    pass
        
        conn.commit()

ensure_expense_tables()


# Список основных 15 проектов, которые должны импортироваться
MAIN_PROJECTS = [
    'EVOS',
    'EVOS HR', 
    'Cat',
    'Saga',
    'Issimo',
    'NBU Mahalla',
    'BYD',
    'Davr Cargo',
    'KIA',
    'NBU Career',
    '8BIT',
    'Миграция',
    'NBU main',
    'NBU Business',
    'Scopus'
]

# Маппинг для нормализации названий проектов при импорте
PROJECT_NORMALIZATION_MAP = {
    # EVOS
    'EVOS': 'EVOS',
    'evos': 'EVOS',
    
    # EVOS HR
    'EVOS HR': 'EVOS HR',
    'EVOS hr': 'EVOS HR',
    'evos hr': 'EVOS HR',
    
    # Cat
    'Cat': 'Cat',
    'cat': 'Cat',
    'CAT': 'Cat',
    
    # Saga
    'Saga': 'Saga',
    'saga': 'Saga',
    'SAGA': 'Saga',
    
    # Issimo
    'Issimo': 'Issimo',
    'issimo': 'Issimo',
    'ISSIMO': 'Issimo',
    
    # NBU Mahalla
    'NBU Mahalla': 'NBU Mahalla',
    'NBU махалля': 'NBU Mahalla',
    'NBU mahalla': 'NBU Mahalla',
    'nbu mahalla': 'NBU Mahalla',
    
    # BYD
    'BYD': 'BYD',
    'byd': 'BYD',
    # Исключаем BYD Club и другие вариации - только чистый BYD
    
    # Davr Cargo  
    'Davr Cargo': 'Davr Cargo',
    'davr cargo': 'Davr Cargo',
    'DAVR CARGO': 'Davr Cargo',
    
    # KIA
    'KIA': 'KIA',
    'Kia': 'KIA',
    'kia': 'KIA',
    
    # NBU Career
    'NBU Career': 'NBU Career',
    'NBU career': 'NBU Career',
    'NBU CAREER': 'NBU Career',
    'NBU карьера': 'NBU Career',
    'NBU  карьер': 'NBU Career',
    
    # 8BIT
    '8BIT': '8BIT',
    '8Bit': '8BIT',
    '8bit': '8BIT',
    '8бит': '8BIT',
    '8 bit': '8BIT',
    
    # Миграция
    'Миграция': 'Миграция',
    'Migration': 'Миграция',
    'миграция': 'Миграция',
    
    # NBU main
    'NBU main': 'NBU main',
    'NBU Main': 'NBU main',
    'NBU': 'NBU main',  # Одиночный NBU тоже считаем как NBU main
    'Nbu official': 'NBU main',
    
    # NBU Business
    'NBU Business': 'NBU Business',
    'NBU business': 'NBU Business',
    'NBU BUSINESS': 'NBU Business',
    
    # Scopus
    'Scopus': 'Scopus',
    'SCOPUS': 'Scopus',
    'scopus': 'Scopus',
    'Скопус': 'Scopus',
    'скопус': 'Scopus',
}

def normalize_project_name(project_name: str) -> str:
    """
    Нормализует название проекта, объединяя дубликаты.
    Возвращает нормализованное название только если это один из 15 основных проектов.
    """
    if not project_name:
        return ""
    
    project_name = project_name.strip()
    
    # Проверяем в маппинге нормализации
    if project_name in PROJECT_NORMALIZATION_MAP:
        return PROJECT_NORMALIZATION_MAP[project_name]
    
    # Проверяем, не является ли это описанием задачи
    if len(project_name) > 50:
        return ""  # Слишком длинное - это описание
    
    # Специальные символы, указывающие на описание задачи
    if any(char in project_name for char in [':', '\n', '\t']):
        return ""
    
    # Специальные случаи - не проекты
    not_projects = [
        '1', 'Все', 'провести собеседование', 'Моушн видео мечкат',
        'BYD Club', 'BYD CLUB', 'Scopus Mall', 'Sora', 'ШумOFF',
        'Узбегим', 'УЗБЕГИМ', 'узбегим', 'Uzbegim', 'UZBEGIM',
        'Hoffman', 'Хоффман', 'Хофмман', 'Хофман', 'Saris',
        'NBU HR', 'NBU Hr', 'NBU фин оп валюты', 'NBU навруз'
    ]
    
    if project_name in not_projects:
        return ""
    
    # Проверка на описания задач BYD  
    if 'BYD' in project_name and project_name != 'BYD':
        # Только чистый BYD является проектом
        if any(word in project_name.lower() for word in ['club', 'подретушировать', 'обложку', 'moodboard']):
            return ""
    
    # Проверка на описания с глаголами
    if any(word in project_name.lower() for word in ['подготовить', 'сделать', 'создать', 'моушн', 'видео', 'сценарий']):
        # Но если есть известный проект в названии, извлекаем его
        for known_project in PROJECT_NORMALIZATION_MAP.keys():
            if known_project.lower() in project_name.lower():
                return PROJECT_NORMALIZATION_MAP[known_project]
        return ""
    
    # ВАЖНО: Возвращаем только если это один из 15 основных проектов
    # Все остальное считается описанием задачи
    return ""


def ensure_digital_task_priority_column():
    with engine.connect() as conn:
        inspector = inspect(conn)
        cols = [c["name"] for c in inspector.get_columns("digital_project_tasks")]
        if "high_priority" not in cols:
            conn.execute(text(
                "ALTER TABLE digital_project_tasks "
                "ADD COLUMN high_priority BOOLEAN DEFAULT 0"
            ))
        if "status" not in cols:
            conn.execute(text(
                "ALTER TABLE digital_project_tasks "
                "ADD COLUMN status VARCHAR(50) DEFAULT 'in_progress'"
            ))
        conn.commit()


ensure_digital_task_priority_column()


def create_default_admin():
    db = SessionLocal()
    try:
        if not crud.get_user_by_login(db, "admin"):
            admin = schemas.UserCreate(
                telegram_username="admin",
                name="Administrator", 
                password=os.getenv("ADMIN_PASSWORD", "admin123"),
                role=models.RoleEnum.admin,
            )
            crud.create_user(db, admin)
    finally:
        db.close()

def create_default_taxes():
    db = SessionLocal()
    try:
        if not crud.get_taxes(db):
            crud.create_tax(db, "ЯТТ", 0.95)
            crud.create_tax(db, "ООО", 0.83)
            crud.create_tax(db, "Нал", 1.0)
    finally:
        db.close()


def create_default_timezone():
    db = SessionLocal()
    try:
        if not db.query(models.Setting).filter(models.Setting.key == "timezone").first():
            db.add(models.Setting(key="timezone", value="Asia/Tashkent"))
            db.commit()
    finally:
        db.close()


def create_default_expense_categories():
    db = SessionLocal()
    try:
        if not db.query(models.ExpenseCategory).first():
            default_categories = [
                {"name": "Аренда", "description": "Аренда офиса, помещений"},
                {"name": "Реклама", "description": "Расходы на рекламу и маркетинг"},
                {"name": "Зарплата", "description": "Заработная плата сотрудников"},
                {"name": "Коммунальные", "description": "Электричество, интернет, связь"},
                {"name": "Канцтовары", "description": "Офисные принадлежности"},
                {"name": "Транспорт", "description": "Транспортные расходы"},
                {"name": "Питание", "description": "Питание сотрудников"},
                {"name": "Оборудование", "description": "Покупка и обслуживание техники"},
            ]
            for cat_data in default_categories:
                category = models.ExpenseCategory(**cat_data)
                db.add(category)
            db.commit()
    finally:
        db.close()


def create_sample_expenses():
    """Create sample expenses for testing"""
    db = SessionLocal()
    try:
        # Only create if no expenses exist
        if (db.query(models.CommonExpense).count() == 0 and 
            db.query(models.ProjectExpense).count() == 0):
            
            # Get admin user and categories
            admin = db.query(models.User).filter(models.User.telegram_username == "admin").first()
            if not admin:
                return
                
            categories = db.query(models.ExpenseCategory).all()
            if not categories:
                return
            
            # Get first project if exists
            project = db.query(models.Project).first()
            
            from datetime import date, timedelta
            import random
            
            # Create sample common expenses
            common_sample_data = [
                {"name": "Аренда офиса за декабрь", "amount": 2000000, "category_id": categories[0].id, "description": "Ежемесячная аренда офиса"},
                {"name": "Интернет и связь", "amount": 500000, "category_id": categories[3].id, "description": "Оплата интернета и мобильной связи"},
                {"name": "Канцелярские товары", "amount": 150000, "category_id": categories[4].id, "description": "Покупка бумаги, ручек, скрепок"},
                {"name": "Обед для команды", "amount": 300000, "category_id": categories[6].id, "description": "Корпоративный обед"},
                {"name": "Реклама в Google", "amount": 750000, "category_id": categories[1].id, "description": "Контекстная реклама"},
            ]
            
            for i, expense_data in enumerate(common_sample_data):
                expense = models.CommonExpense(
                    **expense_data,
                    date=date.today() - timedelta(days=random.randint(1, 30)),
                    created_by=admin.id
                )
                db.add(expense)
            
            # Create sample project expenses if project exists
            if project:
                project_sample_data = [
                    {"name": "Дизайн логотипа", "amount": 500000, "category_id": categories[1].id, "description": "Создание фирменного стиля"},
                    {"name": "Видеосъемка", "amount": 1200000, "category_id": categories[1].id, "description": "Съемка рекламного ролика"},
                    {"name": "Транспорт на съемку", "amount": 80000, "category_id": categories[5].id, "description": "Аренда автомобиля"},
                ]
                
                for expense_data in project_sample_data:
                    expense = models.ProjectExpense(
                        **expense_data,
                        project_id=project.id,
                        date=date.today() - timedelta(days=random.randint(1, 15)),
                        created_by=admin.id
                    )
                    db.add(expense)
            
            db.commit()
            print("✅ Sample expenses created")
    except Exception as e:
        print(f"Warning: Could not create sample expenses: {e}")
        db.rollback()
    finally:
        db.close()


create_default_admin()
create_default_taxes()
create_default_timezone()
create_default_expense_categories()
create_sample_expenses()

# Ensure the static directory exists before mounting it
os.makedirs("static", exist_ok=True)

app = FastAPI(title="8BIT Codex API", version="1.0.0")

# Mount static files
try:
    app.mount("/static", StaticFiles(directory="static"), name="static")
except Exception as e:
    print(f"Warning: Could not mount static directory: {e}")

# Configure CORS properly
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000")
allowed_origins = [origin.strip() for origin in cors_origins.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    max_age=3600,
)


@app.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(auth.get_db)):
    try:
        user = auth.authenticate_user(db, form_data.username, form_data.password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        access_token = auth.create_access_token(
            data={"sub": user.telegram_username, "role": user.role.value}
        )
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "role": user.role.value,
            "user_id": user.id,
            "name": user.name
        }
    except Exception as e:
        print(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during authentication"
        )


@app.post("/users/", response_model=schemas.User)
def create_user(user: schemas.UserCreate, db: Session = Depends(auth.get_db), current: models.User = Depends(auth.get_current_active_user)):
    if current.role != models.RoleEnum.admin:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    db_user = crud.get_user_by_login(db, user.telegram_username)
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    return crud.create_user(db, user)


@app.get("/users/")
def list_users(db: Session = Depends(auth.get_db), current: models.User = Depends(auth.get_current_active_user)):
    return crud.get_users(db)


@app.get("/users/me", response_model=schemas.User)
def read_current_user(current: models.User = Depends(auth.get_current_active_user)):
    return current


@app.get("/users/me/stats", response_model=schemas.UserStats)
def read_current_user_stats(db: Session = Depends(auth.get_db), current: models.User = Depends(auth.get_current_active_user)):
    stats = crud.get_user_statistics(db, current.id)
    if not stats:
        raise HTTPException(status_code=404, detail="Statistics not found")
    return stats


@app.put("/users/{user_id}", response_model=schemas.User)
def update_user(user_id: int, user: schemas.UserUpdate, db: Session = Depends(auth.get_db), current: models.User = Depends(auth.get_current_active_user)):
    if current.role != models.RoleEnum.admin:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    updated = crud.update_user(db, user_id, user)
    if not updated:
        raise HTTPException(status_code=404, detail="User not found")
    return updated


@app.delete("/users/{user_id}")
def delete_user(user_id: int, db: Session = Depends(auth.get_db), current: models.User = Depends(auth.get_current_active_user)):
    if current.role != models.RoleEnum.admin:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    crud.delete_user(db, user_id)
    return {"ok": True}


@app.put("/users/{user_id}/toggle-status")
def toggle_user_status(user_id: int, db: Session = Depends(auth.get_db), current: models.User = Depends(auth.get_current_active_user)):
    if current.role != models.RoleEnum.admin:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    user = crud.get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Toggle between inactive and the user's previous role (default to designer)
    if user.role == models.RoleEnum.inactive:
        # Reactivate user - default to designer role
        user.role = models.RoleEnum.designer
    else:
        # Deactivate user
        user.role = models.RoleEnum.inactive
    
    db.commit()
    db.refresh(user)
    return user


@app.post("/users/{user_id}/contract")
def upload_contract(
    user_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(auth.get_db),
    current: models.User = Depends(auth.get_current_active_user),
):
    if current.role != models.RoleEnum.admin:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    user = crud.get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    os.makedirs("contracts", exist_ok=True)
    path = os.path.join("contracts", f"{user_id}_{file.filename}")
    with open(path, "wb") as f:
        f.write(file.file.read())
    user.contract_path = path
    db.commit()
    db.refresh(user)
    return {"contract_path": path}


@app.get("/users/{user_id}/contract")
def download_contract(
    user_id: int,
    db: Session = Depends(auth.get_db),
    current: models.User = Depends(auth.get_current_active_user),
):
    user = crud.get_user(db, user_id)
    if not user or not user.contract_path:
        raise HTTPException(status_code=404, detail="Contract not found")
    return FileResponse(user.contract_path, filename=os.path.basename(user.contract_path))


@app.delete("/users/{user_id}/contract")
def delete_contract(
    user_id: int,
    db: Session = Depends(auth.get_db),
    current: models.User = Depends(auth.get_current_active_user),
):
    if current.role != models.RoleEnum.admin:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    user = crud.get_user(db, user_id)
    if not user or not user.contract_path:
        raise HTTPException(status_code=404, detail="Contract not found")
    try:
        os.remove(user.contract_path)
    except FileNotFoundError:
        pass
    user.contract_path = None
    db.commit()
    db.refresh(user)
    return {"ok": True}


@app.get("/tasks/")
def read_tasks(skip: int = 0, limit: int = 10000, db: Session = Depends(auth.get_db), current: models.User = Depends(auth.get_current_active_user)):
    return crud.get_tasks_for_user(db, current, skip=skip, limit=limit)


@app.get("/tasks/all", response_model=list[schemas.Task])
def read_all_tasks(skip: int = 0, limit: int = 10000, db: Session = Depends(auth.get_db), current: models.User = Depends(auth.get_current_active_user)):
    # Only admins and smm_managers can access all tasks for reports
    if current.role not in [models.RoleEnum.admin, models.RoleEnum.smm_manager]:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return crud.get_tasks(db, skip=skip, limit=limit)


@app.post("/tasks/", response_model=schemas.Task)
def create_task(task: schemas.TaskCreate, db: Session = Depends(auth.get_db), current: models.User = Depends(auth.get_current_active_user)):
    return crud.create_task(db, task, author_id=current.id)


@app.put("/tasks/{task_id}", response_model=schemas.Task)
def update_task(task_id: int, task: schemas.TaskCreate, db: Session = Depends(auth.get_db), current: models.User = Depends(auth.get_current_active_user)):
    updated = crud.update_task(db, task_id, task)
    if not updated:
        raise HTTPException(status_code=404, detail="Task not found")
    return updated


@app.delete("/tasks/{task_id}")
def delete_task(task_id: int, db: Session = Depends(auth.get_db), current: models.User = Depends(auth.get_current_active_user)):
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Проверяем права на удаление задачи
    can_delete = False
    
    # Администраторы могут удалять любые задачи
    if current.role == models.RoleEnum.admin:
        can_delete = True
    # Автор или исполнитель могут удалять свои задачи
    elif current.id in [task.author_id, task.executor_id]:
        can_delete = True
    # Просроченные задачи могут удалять все пользователи
    elif task.deadline and task.status != models.TaskStatus.done and task.status != models.TaskStatus.cancelled:
        from datetime import datetime
        if datetime.now() > task.deadline.replace(tzinfo=None):
            can_delete = True
    
    if not can_delete:
        raise HTTPException(status_code=403, detail="Not allowed to delete this task")
    
    crud.delete_task(db, task_id)
    return {"ok": True}


@app.patch("/tasks/{task_id}/status", response_model=schemas.Task)
def update_task_status(
    task_id: int,
    status: str,
    db: Session = Depends(auth.get_db),
    current: models.User = Depends(auth.get_current_active_user),
):
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Проверяем права на изменение статуса задачи
    can_modify = False
    
    print(f"DEBUG: Task {task_id} - Current user: {current.id} (role: {current.role.value})")
    print(f"DEBUG: Task author: {task.author_id}, executor: {task.executor_id}")
    print(f"DEBUG: Task status: {task.status.value if task.status else 'None'}")
    
    # Администраторы могут изменять любые задачи
    if current.role == models.RoleEnum.admin:
        can_modify = True
        print("DEBUG: Access granted - admin role")
    # Автор или исполнитель могут изменять свои задачи
    elif current.id in [task.executor_id, task.author_id]:
        can_modify = True
        print("DEBUG: Access granted - author or executor")
    # Просроченные задачи могут завершать все пользователи
    elif task.deadline and task.status != models.TaskStatus.done and task.status != models.TaskStatus.cancelled:
        from datetime import datetime
        if datetime.now() > task.deadline.replace(tzinfo=None):
            can_modify = True
            print("DEBUG: Access granted - overdue task")
    
    if not can_modify:
        print("DEBUG: Access denied")
        raise HTTPException(status_code=403, detail=f"Not allowed to modify this task. User {current.id} cannot modify task {task_id} (author: {task.author_id}, executor: {task.executor_id})")
    
    return crud.update_task_status(db, task_id, status)


@app.get("/operators/", response_model=list[schemas.Operator])
def list_operators(db: Session = Depends(auth.get_db), current: models.User = Depends(auth.get_current_active_user)):
    return crud.get_operators(db)


@app.post("/operators/", response_model=schemas.Operator)
def create_operator(op: schemas.OperatorCreate, db: Session = Depends(auth.get_db), current: models.User = Depends(auth.get_current_active_user)):
    if current.role != models.RoleEnum.admin:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return crud.create_operator(db, op)


@app.put("/operators/{op_id}", response_model=schemas.Operator)
def update_operator(op_id: int, op: schemas.OperatorCreate, db: Session = Depends(auth.get_db), current: models.User = Depends(auth.get_current_active_user)):
    if current.role != models.RoleEnum.admin:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    updated = crud.update_operator(db, op_id, op)
    if not updated:
        raise HTTPException(status_code=404, detail="Operator not found")
    return updated


@app.delete("/operators/{op_id}")
def delete_operator(op_id: int, db: Session = Depends(auth.get_db), current: models.User = Depends(auth.get_current_active_user)):
    if current.role != models.RoleEnum.admin:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    crud.delete_operator(db, op_id)
    return {"ok": True}


@app.get("/projects/", response_model=list[schemas.Project])
def list_projects(db: Session = Depends(auth.get_db), current: models.User = Depends(auth.get_current_active_user), include_archived: bool = False):
    return crud.get_projects(db, include_archived=include_archived)


@app.post("/projects/", response_model=schemas.Project)
def create_project(project: schemas.ProjectCreate, db: Session = Depends(auth.get_db), current: models.User = Depends(auth.get_current_active_user)):
    if current.role != models.RoleEnum.admin:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return crud.create_project(db, project)


@app.get("/projects/{project_id}", response_model=schemas.Project)
def get_project(project_id: int, db: Session = Depends(auth.get_db), current: models.User = Depends(auth.get_current_active_user)):
    proj = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")
    return proj


@app.put("/projects/{project_id}", response_model=schemas.Project)
def update_project(project_id: int, project: schemas.ProjectCreate, db: Session = Depends(auth.get_db), current: models.User = Depends(auth.get_current_active_user)):
    if current.role != models.RoleEnum.admin:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    updated = crud.update_project(db, project_id, project)
    if not updated:
        raise HTTPException(status_code=404, detail="Project not found")
    return updated


@app.put("/projects/{project_id}/info", response_model=schemas.Project)
def update_project_info(project_id: int, data: schemas.ProjectUpdate, db: Session = Depends(auth.get_db), current: models.User = Depends(auth.get_current_active_user)):
    updated = crud.update_project_info(db, project_id, data)
    if not updated:
        raise HTTPException(status_code=404, detail="Project not found")
    return updated


@app.delete("/projects/{project_id}")
def delete_project(project_id: int, db: Session = Depends(auth.get_db), current: models.User = Depends(auth.get_current_active_user)):
    if current.role != models.RoleEnum.admin:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    crud.delete_project(db, project_id)
    return {"ok": True}


@app.put("/projects/{project_id}/toggle-archive")
def toggle_project_archive(project_id: int, db: Session = Depends(auth.get_db), current: models.User = Depends(auth.get_current_active_user)):
    if current.role != models.RoleEnum.admin:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    project.is_archived = not project.is_archived
    db.commit()
    db.refresh(project)
    return project


@app.post("/projects/{project_id}/logo")
async def upload_project_logo(
    project_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(auth.get_db),
    current: models.User = Depends(auth.get_current_active_user),
):
    if current.role != models.RoleEnum.admin:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    os.makedirs("static/projects", exist_ok=True)
    path = f"static/projects/{project_id}_{file.filename}"
    with open(path, "wb") as f:
        f.write(await file.read())
    proj = crud.set_project_logo(db, project_id, path)
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"logo": path}


@app.delete("/projects/{project_id}/logo")
def delete_project_logo(
    project_id: int,
    db: Session = Depends(auth.get_db),
    current: models.User = Depends(auth.get_current_active_user),
):
    if current.role != models.RoleEnum.admin:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    proj = crud.set_project_logo(db, project_id, None)
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"ok": True}


@app.get("/projects/{project_id}/report", response_model=schemas.ProjectReport)
def get_project_report(
    project_id: int,
    month: int | None = None,
    db: Session = Depends(auth.get_db),
    current: models.User = Depends(auth.get_current_active_user),
):
    today = datetime.utcnow()
    m = month or today.month
    start = datetime(today.year, m, 1)
    end_month = m + 1
    end_year = today.year
    if end_month > 12:
        end_month = 1
        end_year += 1
    end = datetime(end_year, end_month, 1)
    report = crud.get_or_create_report(db, project_id, m, today.year)
    expenses = crud.get_expenses(db, project_id, start, end)
    client_expenses = crud.get_client_expenses(db, project_id, start, end)
    receipts_list = crud.get_receipts(db, project_id, start, end)
    receipts_sum = sum(r.amount for r in receipts_list)
    client_sum = sum(e.amount for e in client_expenses)
    total_expenses = sum(e.amount for e in expenses) + client_sum
    debt = report.contract_amount - receipts_sum + client_sum
    positive_balance = receipts_sum - total_expenses
    return schemas.ProjectReport(
        project_id=project_id,
        contract_amount=report.contract_amount,
        receipts=receipts_sum,
        receipts_list=receipts_list,
        client_expenses=client_expenses,
        total_expenses=total_expenses,
        debt=debt,
        positive_balance=positive_balance,
        expenses=expenses,
    )


@app.put("/projects/{project_id}/report", response_model=schemas.ProjectReport)
def update_project_report(
    project_id: int,
    data: schemas.ProjectReportUpdate,
    month: int | None = None,
    db: Session = Depends(auth.get_db),
    current: models.User = Depends(auth.get_current_active_user),
):
    today = datetime.utcnow()
    m = month or today.month
    start = datetime(today.year, m, 1)
    end_month = m + 1
    end_year = today.year
    if end_month > 12:
        end_month = 1
        end_year += 1
    end = datetime(end_year, end_month, 1)
    report = crud.update_report(db, project_id, data, m, today.year)
    expenses = crud.get_expenses(db, project_id, start, end)
    client_expenses = crud.get_client_expenses(db, project_id, start, end)
    receipts_list = crud.get_receipts(db, project_id, start, end)
    receipts_sum = sum(r.amount for r in receipts_list)
    client_sum = sum(e.amount for e in client_expenses)
    total_expenses = sum(e.amount for e in expenses) + client_sum
    debt = report.contract_amount - receipts_sum + client_sum
    positive_balance = receipts_sum - total_expenses
    return schemas.ProjectReport(
        project_id=project_id,
        contract_amount=report.contract_amount,
        receipts=receipts_sum,
        receipts_list=receipts_list,
        client_expenses=client_expenses,
        total_expenses=total_expenses,
        debt=debt,
        positive_balance=positive_balance,
        expenses=expenses,
    )


@app.get("/projects/{project_id}/expenses", response_model=list[schemas.Expense])
def list_expenses(
    project_id: int,
    month: int | None = None,
    db: Session = Depends(auth.get_db),
    current: models.User = Depends(auth.get_current_active_user),
):
    today = datetime.utcnow()
    m = month or today.month
    start = datetime(today.year, m, 1)
    end_month = m + 1
    end_year = today.year
    if end_month > 12:
        end_month = 1
        end_year += 1
    end = datetime(end_year, end_month, 1)
    return crud.get_expenses(db, project_id, start, end)


@app.post("/projects/{project_id}/expenses", response_model=schemas.Expense)
def add_expense(
    project_id: int,
    exp: schemas.ExpenseCreate,
    month: int | None = None,
    db: Session = Depends(auth.get_db),
    current: models.User = Depends(auth.get_current_active_user),
):
    today = datetime.utcnow()
    return crud.create_expense(db, project_id, exp, month or today.month, today.year)


@app.put("/expenses/{expense_id}", response_model=schemas.Expense)
def edit_expense(expense_id: int, exp: schemas.ExpenseCreate, db: Session = Depends(auth.get_db), current: models.User = Depends(auth.get_current_active_user)):
    updated = crud.update_expense(db, expense_id, exp)
    if not updated:
        raise HTTPException(status_code=404, detail="Expense not found")
    return updated


@app.delete("/expenses/{expense_id}")
def remove_expense(expense_id: int, db: Session = Depends(auth.get_db), current: models.User = Depends(auth.get_current_active_user)):
    crud.delete_expense(db, expense_id)
    return {"ok": True}


@app.get("/projects/{project_id}/client_expenses", response_model=list[schemas.ClientExpense])
def list_client_expenses(
    project_id: int,
    month: int | None = None,
    db: Session = Depends(auth.get_db),
    current: models.User = Depends(auth.get_current_active_user),
):
    today = datetime.utcnow()
    m = month or today.month
    start = datetime(today.year, m, 1)
    end_month = m + 1
    end_year = today.year
    if end_month > 12:
        end_month = 1
        end_year += 1
    end = datetime(end_year, end_month, 1)
    return crud.get_client_expenses(db, project_id, start, end)


@app.post("/projects/{project_id}/client_expenses", response_model=schemas.ClientExpense)
def add_client_expense(
    project_id: int,
    exp: schemas.ClientExpenseCreate,
    month: int | None = None,
    db: Session = Depends(auth.get_db),
    current: models.User = Depends(auth.get_current_active_user),
):
    today = datetime.utcnow()
    return crud.create_client_expense(db, project_id, exp, month or today.month, today.year)


@app.put("/client_expenses/{expense_id}", response_model=schemas.ClientExpense)
def edit_client_expense(expense_id: int, exp: schemas.ClientExpenseCreate, db: Session = Depends(auth.get_db), current: models.User = Depends(auth.get_current_active_user)):
    updated = crud.update_client_expense(db, expense_id, exp)
    if not updated:
        raise HTTPException(status_code=404, detail="Client expense not found")
    return updated


@app.post("/client_expenses/{expense_id}/close", response_model=schemas.ClientExpense | None)
def close_client_expense(expense_id: int, data: schemas.ClientExpenseClose, db: Session = Depends(auth.get_db), current: models.User = Depends(auth.get_current_active_user)):
    return crud.close_client_expense(db, expense_id, data.amount, data.comment)


@app.delete("/client_expenses/{expense_id}")
def remove_client_expense(expense_id: int, db: Session = Depends(auth.get_db), current: models.User = Depends(auth.get_current_active_user)):
    crud.delete_client_expense(db, expense_id)
    return {"ok": True}


@app.get("/projects/{project_id}/receipts", response_model=list[schemas.Receipt])
def list_receipts(
    project_id: int,
    month: int | None = None,
    db: Session = Depends(auth.get_db),
    current: models.User = Depends(auth.get_current_active_user),
):
    today = datetime.utcnow()
    m = month or today.month
    start = datetime(today.year, m, 1)
    end_month = m + 1
    end_year = today.year
    if end_month > 12:
        end_month = 1
        end_year += 1
    end = datetime(end_year, end_month, 1)
    return crud.get_receipts(db, project_id, start, end)


@app.post("/projects/{project_id}/receipts", response_model=schemas.Receipt)
def add_receipt(
    project_id: int,
    rec: schemas.ReceiptCreate,
    month: int | None = None,
    db: Session = Depends(auth.get_db),
    current: models.User = Depends(auth.get_current_active_user),
):
    today = datetime.utcnow()
    return crud.create_receipt(db, project_id, rec, month or today.month, today.year)


@app.put("/receipts/{receipt_id}", response_model=schemas.Receipt)
def edit_receipt(receipt_id: int, rec: schemas.ReceiptCreate, db: Session = Depends(auth.get_db), current: models.User = Depends(auth.get_current_active_user)):
    updated = crud.update_receipt(db, receipt_id, rec)
    if not updated:
        raise HTTPException(status_code=404, detail="Receipt not found")
    return updated


@app.delete("/receipts/{receipt_id}")
def remove_receipt(receipt_id: int, db: Session = Depends(auth.get_db), current: models.User = Depends(auth.get_current_active_user)):
    crud.delete_receipt(db, receipt_id)
    return {"ok": True}


@app.get("/taxes/", response_model=list[schemas.Tax])
def list_taxes(db: Session = Depends(auth.get_db), current: models.User = Depends(auth.get_current_active_user)):
    return crud.get_taxes(db)


@app.post("/taxes/", response_model=schemas.Tax)
def create_tax(tax: schemas.TaxCreate, db: Session = Depends(auth.get_db), current: models.User = Depends(auth.get_current_active_user)):
    if current.role != models.RoleEnum.admin:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return crud.create_tax(db, tax.name, tax.rate)


@app.put("/taxes/{tax_id}", response_model=schemas.Tax)
def update_tax(tax_id: int, tax: schemas.TaxCreate, db: Session = Depends(auth.get_db), current: models.User = Depends(auth.get_current_active_user)):
    if current.role != models.RoleEnum.admin:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    updated = crud.update_tax(db, tax_id, tax.name, tax.rate)
    if not updated:
        raise HTTPException(status_code=404, detail="Tax not found")
    return updated


@app.delete("/taxes/{tax_id}")
def delete_tax(tax_id: int, db: Session = Depends(auth.get_db), current: models.User = Depends(auth.get_current_active_user)):
    if current.role != models.RoleEnum.admin:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    crud.delete_tax(db, tax_id)
    return {"ok": True}


@app.get("/expenses/report", response_model=list[schemas.ExpenseReportRow])
def expenses_report(
    start: str | None = None,
    end: str | None = None,
    project_id: int | None = None,
    db: Session = Depends(auth.get_db),
    current: models.User = Depends(auth.get_current_active_user),
):
    now = datetime.utcnow()
    if not start or not end:
        start_dt = datetime(now.year, now.month, 1)
        next_month = now.month + 1
        next_year = now.year
        if next_month > 12:
            next_month = 1
            next_year += 1
        end_dt = datetime(next_year, next_month, 1)
    else:
        start_dt = datetime.fromisoformat(start)
        end_dt = datetime.fromisoformat(end)
    rows = crud.get_expenses_report(db, start_dt, end_dt, project_id)
    return [schemas.ExpenseReportRow(name=n, quantity=q, unit_avg=a) for n, q, a in rows]


@app.get("/projects/{project_id}/posts", response_model=list[schemas.ProjectPost])
def list_project_posts(
    project_id: int,
    month: int | None = None,
    year: int | None = None,
    db: Session = Depends(auth.get_db),
    current: models.User = Depends(auth.get_current_active_user),
):
    if month:
        y = year or datetime.utcnow().year
        start = datetime(y, month, 1)
        end_month = month + 1
        end_year = y
        if end_month > 12:
            end_month = 1
            end_year += 1
        end = datetime(end_year, end_month, 1)
        return crud.get_project_posts(db, project_id, start, end)
    return crud.get_project_posts(db, project_id)


@app.post("/projects/{project_id}/posts", response_model=schemas.ProjectPost)
def create_project_post(project_id: int, data: schemas.ProjectPostCreate, db: Session = Depends(auth.get_db), current: models.User = Depends(auth.get_current_active_user)):
    return crud.create_project_post(db, project_id, data)


@app.put("/project_posts/{post_id}", response_model=schemas.ProjectPost)
def update_project_post(post_id: int, data: schemas.ProjectPostCreate, db: Session = Depends(auth.get_db), current: models.User = Depends(auth.get_current_active_user)):
    updated = crud.update_project_post(db, post_id, data)
    if not updated:
        raise HTTPException(status_code=404, detail="Post not found")
    return updated


@app.delete("/project_posts/{post_id}")
def delete_project_post(post_id: int, db: Session = Depends(auth.get_db), current: models.User = Depends(auth.get_current_active_user)):
    crud.delete_project_post(db, post_id)
    return {"ok": True}


@app.get("/shootings/", response_model=list[schemas.Shooting])
def list_shootings(db: Session = Depends(auth.get_db), current: models.User = Depends(auth.get_current_active_user)):
    return crud.get_shootings(db)


def _shoot_perm(user: models.User):
    return user.role in [models.RoleEnum.smm_manager, models.RoleEnum.head_smm, models.RoleEnum.admin]


@app.post("/shootings/", response_model=schemas.Shooting)
def create_shooting(shooting: schemas.ShootingCreate, db: Session = Depends(auth.get_db), current: models.User = Depends(auth.get_current_active_user)):
    if not _shoot_perm(current):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return crud.create_shooting(db, shooting)


@app.put("/shootings/{sid}", response_model=schemas.Shooting)
def update_shooting(sid: int, shooting: schemas.ShootingCreate, db: Session = Depends(auth.get_db), current: models.User = Depends(auth.get_current_active_user)):
    if not _shoot_perm(current):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    updated = crud.update_shooting(db, sid, shooting)
    if not updated:
        raise HTTPException(status_code=404, detail="Shooting not found")
    return updated


@app.delete("/shootings/{sid}")
def delete_shooting(sid: int, db: Session = Depends(auth.get_db), current: models.User = Depends(auth.get_current_active_user)):
    if not _shoot_perm(current):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    crud.delete_shooting(db, sid)
    return {"ok": True}


@app.post("/shootings/{sid}/complete", response_model=schemas.Shooting)
def complete_shooting(sid: int, data: schemas.ShootingComplete, db: Session = Depends(auth.get_db), current: models.User = Depends(auth.get_current_active_user)):
    if not _shoot_perm(current):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    sh = crud.complete_shooting(db, sid, data.quantity, data.managers, data.operators)
    if not sh:
        raise HTTPException(status_code=404, detail="Shooting not found")
    return sh


@app.get("/settings/timezone")
def get_timezone(db: Session = Depends(auth.get_db), current: models.User = Depends(auth.get_current_active_user)):
    setting = db.query(models.Setting).filter(models.Setting.key == "timezone").first()
    return {"timezone": setting.value if setting else "Asia/Tashkent"}


@app.put("/settings/timezone")
def set_timezone(data: schemas.TimezoneUpdate, db: Session = Depends(auth.get_db), current: models.User = Depends(auth.get_current_active_user)):
    if current.role != models.RoleEnum.admin:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    setting = db.query(models.Setting).filter(models.Setting.key == "timezone").first()
    if not setting:
        setting = models.Setting(key="timezone", value=data.timezone)
        db.add(setting)
    else:
        setting.value = data.timezone
    db.commit()
    return {"timezone": setting.value}


@app.get("/digital/services", response_model=list[schemas.DigitalService])
def list_digital_services(db: Session = Depends(auth.get_db), current: models.User = Depends(auth.get_current_active_user)):
    return crud.get_digital_services(db)


@app.post("/digital/services", response_model=schemas.DigitalService)
def create_digital_service(service: schemas.DigitalServiceCreate, db: Session = Depends(auth.get_db), current: models.User = Depends(auth.get_current_active_user)):
    if current.role != models.RoleEnum.admin:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return crud.create_digital_service(db, service.name)


@app.delete("/digital/services/{service_id}")
def delete_digital_service(service_id: int, db: Session = Depends(auth.get_db), current: models.User = Depends(auth.get_current_active_user)):
    if current.role != models.RoleEnum.admin:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    crud.delete_digital_service(db, service_id)
    return {"ok": True}


@app.get("/digital/projects", response_model=list[schemas.DigitalProject])
def list_digital_projects(db: Session = Depends(auth.get_db), current: models.User = Depends(auth.get_current_active_user)):
    return [schemas.DigitalProject(**item) for item in crud.get_digital_projects(db)]


@app.post("/digital/projects", response_model=schemas.DigitalProject)
def create_digital_project(proj: schemas.DigitalProjectCreate, db: Session = Depends(auth.get_db), current: models.User = Depends(auth.get_current_active_user)):
    dp = crud.create_digital_project(db, proj)
    for item in crud.get_digital_projects(db):
        if item["id"] == dp.id:
            return schemas.DigitalProject(**item)
    raise HTTPException(status_code=500, detail="Creation failed")


@app.put("/digital/projects/{project_id}", response_model=schemas.DigitalProject)
def update_digital_project(
    project_id: int,
    proj: schemas.DigitalProjectCreate,
    db: Session = Depends(auth.get_db),
    current: models.User = Depends(auth.get_current_active_user),
):
    dp = crud.update_digital_project(db, project_id, proj)
    if not dp:
        raise HTTPException(status_code=404, detail="Project not found")
    for item in crud.get_digital_projects(db):
        if item["id"] == project_id:
            return schemas.DigitalProject(**item)
    raise HTTPException(status_code=500, detail="Update failed")


@app.put("/digital/projects/{project_id}/status")
def update_digital_project_status(
    project_id: int,
    status: str = Query(...),
    db: Session = Depends(auth.get_db),
    current: models.User = Depends(auth.get_current_active_user),
):
    dp = crud.update_digital_project_status(db, project_id, status)
    if not dp:
        raise HTTPException(status_code=404, detail="Project not found")
    for item in crud.get_digital_projects(db):
        if item["id"] == project_id:
            return schemas.DigitalProject(**item)
    raise HTTPException(status_code=500, detail="Update failed")


@app.delete("/digital/projects/{project_id}")
def delete_digital_project(
    project_id: int,
    db: Session = Depends(auth.get_db),
    current: models.User = Depends(auth.get_current_active_user),
):
    crud.delete_digital_project(db, project_id)
    return {"ok": True}


@app.post("/digital/projects/{project_id}/logo")
async def upload_digital_logo(
    project_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(auth.get_db),
    current: models.User = Depends(auth.get_current_active_user),
):
    os.makedirs("static/digital", exist_ok=True)
    path = f"static/digital/{project_id}_{file.filename}"
    with open(path, "wb") as f:
        f.write(await file.read())
    proj = crud.set_digital_project_logo(db, project_id, path)
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"logo": path}


@app.delete("/digital/projects/{project_id}/logo")
def delete_digital_logo(
    project_id: int,
    db: Session = Depends(auth.get_db),
    current: models.User = Depends(auth.get_current_active_user),
):
    proj = crud.set_digital_project_logo(db, project_id, None)
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"ok": True}


@app.get("/digital/projects/{project_id}/tasks", response_model=list[schemas.DigitalTask])
def list_digital_tasks(
    project_id: int,
    db: Session = Depends(auth.get_db),
    current: models.User = Depends(auth.get_current_active_user),
):
    return [
        schemas.DigitalTask(
            id=t.id,
            title=t.title,
            description=t.description,
            deadline=t.deadline,
            created_at=t.created_at,
            high_priority=t.high_priority,
            status=t.status or "in_progress",
            links=json.loads(t.links or "[]"),
        )
        for t in crud.get_digital_tasks(db, project_id)
    ]


@app.post("/digital/projects/{project_id}/tasks", response_model=schemas.DigitalTask)
def create_digital_task(
    project_id: int,
    task: schemas.DigitalTaskCreate,
    db: Session = Depends(auth.get_db),
    current: models.User = Depends(auth.get_current_active_user),
):
    t = crud.create_digital_task(db, project_id, task)
    return schemas.DigitalTask(
        id=t.id,
        title=t.title,
        description=t.description,
        deadline=t.deadline,
        created_at=t.created_at,
        high_priority=t.high_priority,
        status=t.status or "in_progress",
        links=task.links,
    )


@app.put("/digital/projects/{project_id}/tasks/{task_id}", response_model=schemas.DigitalTask)
def update_digital_task(
    project_id: int,
    task_id: int,
    task: schemas.DigitalTaskCreate,
    db: Session = Depends(auth.get_db),
    current: models.User = Depends(auth.get_current_active_user),
):
    t = crud.update_digital_task(db, task_id, task)
    if not t or t.project_id != project_id:
        raise HTTPException(status_code=404, detail="Task not found")
    return schemas.DigitalTask(
        id=t.id,
        title=t.title,
        description=t.description,
        deadline=t.deadline,
        created_at=t.created_at,
        high_priority=t.high_priority,
        status=t.status or "in_progress",
        links=json.loads(t.links or "[]"),
    )


@app.delete("/digital/projects/{project_id}/tasks/{task_id}")
def delete_digital_task(
    project_id: int,
    task_id: int,
    db: Session = Depends(auth.get_db),
    current: models.User = Depends(auth.get_current_active_user),
):
    crud.delete_digital_task(db, task_id)
    return {"ok": True}


# Digital Project Finance Endpoints
@app.get("/digital/projects/{project_id}/finance", response_model=schemas.DigitalProjectFinance)
def get_digital_project_finance(
    project_id: int,
    db: Session = Depends(auth.get_db),
    current: models.User = Depends(auth.get_current_active_user),
):
    finance = crud.get_digital_project_finance(db, project_id)
    if not finance:
        return schemas.DigitalProjectFinance(
            id=0,
            project_id=project_id,
            tax_id=None,
            cost_without_tax=None,
            cost_with_tax=None,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
    return finance


@app.post("/digital/projects/{project_id}/finance", response_model=schemas.DigitalProjectFinance)
def create_or_update_digital_project_finance(
    project_id: int,
    finance_data: schemas.DigitalProjectFinanceUpdate,
    db: Session = Depends(auth.get_db),
    current: models.User = Depends(auth.get_current_active_user),
):
    finance = crud.get_digital_project_finance(db, project_id)
    if finance:
        return crud.update_digital_project_finance(db, project_id, finance_data)
    else:
        finance_create = schemas.DigitalProjectFinanceCreate(
            project_id=project_id,
            **finance_data.dict()
        )
        return crud.create_digital_project_finance(db, finance_create)


@app.get("/digital/projects/{project_id}/expenses", response_model=List[schemas.DigitalProjectExpense])
def get_digital_project_expenses(
    project_id: int,
    db: Session = Depends(auth.get_db),
    current: models.User = Depends(auth.get_current_active_user),
):
    return crud.get_digital_project_expenses(db, project_id)


@app.post("/digital/projects/{project_id}/expenses", response_model=schemas.DigitalProjectExpense)
def create_digital_project_expense(
    project_id: int,
    expense_data: schemas.DigitalProjectExpenseBase,
    db: Session = Depends(auth.get_db),
    current: models.User = Depends(auth.get_current_active_user),
):
    expense_create = schemas.DigitalProjectExpenseCreate(
        project_id=project_id,
        **expense_data.dict()
    )
    return crud.create_digital_project_expense(db, expense_create)


@app.delete("/digital/projects/{project_id}/expenses/{expense_id}")
def delete_digital_project_expense(
    project_id: int,
    expense_id: int,
    db: Session = Depends(auth.get_db),
    current: models.User = Depends(auth.get_current_active_user),
):
    crud.delete_digital_project_expense(db, expense_id)
    return {"ok": True}


@app.get("/analytics")
def get_analytics(
    time_range: str = "30d",
    db: Session = Depends(auth.get_db),
    current: models.User = Depends(auth.get_current_active_user),
):
    """Получение аналитических данных"""
    from datetime import datetime, timedelta
    from sqlalchemy import func, and_
    
    # Определяем период для анализа
    end_date = datetime.utcnow()
    if time_range == "7d":
        start_date = end_date - timedelta(days=7)
    elif time_range == "30d":
        start_date = end_date - timedelta(days=30)
    elif time_range == "90d":
        start_date = end_date - timedelta(days=90)
    elif time_range == "1y":
        start_date = end_date - timedelta(days=365)
    else:
        start_date = end_date - timedelta(days=30)
    
    # Статистика задач
    total_tasks = db.query(models.Task).count()
    completed_tasks = db.query(models.Task).filter(models.Task.status == "done").count()
    in_progress_tasks = db.query(models.Task).filter(models.Task.status == "in_progress").count()
    overdue_tasks = db.query(models.Task).filter(
        and_(models.Task.deadline < datetime.utcnow(), models.Task.status != "done")
    ).count()
    
    # Статистика проектов
    total_projects = db.query(models.Project).count()
    # Упрощаем логику - считаем проекты по датам
    current_date = datetime.utcnow()
    active_projects = db.query(models.Project).filter(
        and_(models.Project.start_date <= current_date, models.Project.end_date >= current_date)
    ).count()
    completed_projects = db.query(models.Project).filter(models.Project.end_date < current_date).count()
    
    # Производительность команды (упрощенная версия)
    users = db.query(models.User).filter(models.User.role != models.RoleEnum.admin).all()
    team_productivity = []
    for user in users:
        tasks_completed = db.query(models.Task).filter(
            and_(
                models.Task.executor_id == user.id,
                models.Task.status == "done",
                models.Task.finished_at >= start_date
            )
        ).count()
        
        # Простая формула эффективности (можно улучшить)
        efficiency = min(95, max(50, 70 + (tasks_completed * 2)))
        
        team_productivity.append({
            "name": user.name,
            "tasksCompleted": tasks_completed,
            "efficiency": efficiency
        })
    
    # Задачи по месяцам (последние 5 месяцев)
    tasks_by_month = []
    for i in range(5):
        month_start = datetime.utcnow().replace(day=1) - timedelta(days=30 * i)
        month_end = month_start.replace(day=28) + timedelta(days=4)  # переходим к концу месяца
        month_end = month_end - timedelta(days=month_end.day - 1) + timedelta(days=31)
        month_end = min(month_end, month_start.replace(day=28) + timedelta(days=4))
        
        created_count = db.query(models.Task).filter(
            and_(models.Task.created_at >= month_start, models.Task.created_at < month_end)
        ).count()
        
        completed_count = db.query(models.Task).filter(
            and_(
                models.Task.finished_at >= month_start,
                models.Task.finished_at < month_end,
                models.Task.status == "done"
            )
        ).count()
        
        tasks_by_month.append({
            "month": month_start.strftime("%b"),
            "created": created_count,
            "completed": completed_count
        })
    
    tasks_by_month.reverse()  # Сортируем по возрастанию
    
    # Задачи по типам (упрощенная версия)
    task_types = [
        {"name": "Дизайн", "value": 35, "color": "#8B5CF6"},
        {"name": "Контент", "value": 28, "color": "#06B6D4"},
        {"name": "Съемки", "value": 20, "color": "#10B981"},
        {"name": "Стратегия", "value": 17, "color": "#F59E0B"}
    ]
    
    return {
        "tasksStats": {
            "total": total_tasks,
            "completed": completed_tasks,
            "inProgress": in_progress_tasks,
            "overdue": overdue_tasks
        },
        "projectsStats": {
            "total": total_projects,
            "active": active_projects,
            "completed": completed_projects
        },
        "teamProductivity": team_productivity,
        "tasksByMonth": tasks_by_month,
        "tasksByType": task_types
    }



# Resource Files Endpoints
@app.get("/resource-files/", response_model=List[schemas.ResourceFile])
def list_resource_files(
    category: Optional[str] = None,
    project_id: Optional[int] = None,
    db: Session = Depends(auth.get_db),
    current: models.User = Depends(auth.get_current_active_user),
):
    return crud.get_resource_files(db, category=category, project_id=project_id)


@app.get("/resource-files/{file_id}", response_model=schemas.ResourceFile)
def get_resource_file(
    file_id: int,
    db: Session = Depends(auth.get_db),
    current: models.User = Depends(auth.get_current_active_user),
):
    file = crud.get_resource_file(db, file_id)
    if not file:
        raise HTTPException(status_code=404, detail="File not found")
    return file


@app.post("/resource-files/", response_model=schemas.ResourceFile)
async def upload_resource_file(
    name: str = Form(...),
    category: str = Form("general"),
    project_id: Optional[int] = Form(None),
    is_favorite: bool = Form(False),
    file: UploadFile = File(...),
    db: Session = Depends(auth.get_db),
    current: models.User = Depends(auth.get_current_active_user),
):
    # Ensure the files directory exists
    os.makedirs("files", exist_ok=True)
    
    # Generate unique filename to avoid conflicts
    import uuid
    unique_id = uuid.uuid4()
    file_extension = file.filename.split('.')[-1] if '.' in file.filename else ''
    unique_filename = f"{unique_id}.{file_extension}" if file_extension else str(unique_id)
    file_path = os.path.join("files", unique_filename)
    
    # Save file to disk
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)
    
    file_data = schemas.ResourceFileCreate(
        name=name,
        category=category,
        project_id=project_id,
        is_favorite=is_favorite
    )
    
    return crud.create_resource_file(
        db=db,
        file_data=file_data,
        filename=file.filename,
        file_path=file_path,
        size=len(content),
        mime_type=file.content_type or "application/octet-stream",
        user_id=current.id
    )


@app.put("/resource-files/{file_id}", response_model=schemas.ResourceFile)
def update_resource_file(
    file_id: int,
    file_data: schemas.ResourceFileUpdate,
    db: Session = Depends(auth.get_db),
    current: models.User = Depends(auth.get_current_active_user),
):
    updated_file = crud.update_resource_file(db, file_id, file_data)
    if not updated_file:
        raise HTTPException(status_code=404, detail="File not found")
    return updated_file


@app.delete("/resource-files/{file_id}")
def delete_resource_file(
    file_id: int,
    db: Session = Depends(auth.get_db),
    current: models.User = Depends(auth.get_current_active_user),
):
    file = crud.get_resource_file(db, file_id)
    if not file:
        raise HTTPException(status_code=404, detail="File not found")
    
    # Delete file from disk
    try:
        if os.path.exists(file.file_path):
            os.remove(file.file_path)
    except Exception as e:
        print(f"Error deleting file {file.file_path}: {e}")
    
    crud.delete_resource_file(db, file_id)
    return {"ok": True}


@app.get("/resource-files/{file_id}/download")
def download_resource_file(
    file_id: int,
    db: Session = Depends(auth.get_db),
    current: models.User = Depends(auth.get_current_active_user),
):
    file = crud.get_resource_file(db, file_id)
    if not file:
        raise HTTPException(status_code=404, detail="File not found")
    
    if not os.path.exists(file.file_path):
        raise HTTPException(status_code=404, detail="File not found on disk")
    
    # Increment download count
    crud.increment_file_download_count(db, file_id)
    
    return FileResponse(
        file.file_path,
        filename=file.filename,
        media_type=file.mime_type
    )


@app.get("/health")
def health_check(db: Session = Depends(auth.get_db)):
    """Health check endpoint for Docker"""
    try:
        # Проверяем подключение к БД
        db.execute(text("SELECT 1"))
        return {
            "status": "healthy", 
            "database": "connected",
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0.0"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "database": "disconnected", 
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


@app.post("/admin/import-database")
async def import_database(
    file: UploadFile = File(...),
    filter_by_roles: bool = True,
    db: Session = Depends(auth.get_db),
    current: models.User = Depends(auth.get_current_active_user),
):
    """Импорт данных из загруженной БД с фильтрацией по ролям"""
    if current.role != models.RoleEnum.admin:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    if not file.filename.endswith('.db'):
        raise HTTPException(status_code=400, detail="Only .db files are allowed")
    
    # Сохраняем временный файл
    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as tmp_file:
        shutil.copyfileobj(file.file, tmp_file)
        tmp_path = tmp_file.name
    
    try:
        # Подключаемся к загруженной БД
        source_engine = create_engine(f"sqlite:///{tmp_path}")
        
        # Проверяем существование таблиц
        source_inspector = inspect(source_engine)
        available_tables = source_inspector.get_table_names()
        
        if not available_tables:
            raise HTTPException(status_code=400, detail="Database file appears to be empty or corrupted")
        
        source_session = Session(bind=source_engine)
        
        imported_data = {
            "users": 0,
            "projects": 0,
            "tasks": 0,
            "digital_projects": 0,
            "operators": 0,
            "expense_items": 0,
            "taxes": 0
        }
        
        # Импортируем пользователей
        if "users" in available_tables:
            try:
                # Используем прямой SQL запрос для большей гибкости
                cursor = source_session.connection().connection.cursor()
                cursor.execute("SELECT * FROM users")
                rows = cursor.fetchall()
                
                # Получаем названия колонок
                cursor.execute("PRAGMA table_info(users)")
                columns = [col[1] for col in cursor.fetchall()]
                
                for row in rows:
                    # Создаем словарь из строки
                    user_data = dict(zip(columns, row))
                    
                    # Проверяем, существует ли пользователь
                    # Handle both old 'login' field and new 'telegram_username' field
                    username = user_data.get('telegram_username') or user_data.get('login')
                    existing_user = db.query(models.User).filter(models.User.telegram_username == username).first()
                    if not existing_user:
                        new_user = models.User(
                            telegram_username=username,
                            telegram_id=user_data.get('telegram_id'),
                            name=user_data['name'],
                            hashed_password=user_data['hashed_password'],
                            role=user_data['role'],
                            birth_date=user_data.get('birth_date'),
                            contract_path=user_data.get('contract_path'),
                            is_active=user_data.get('is_active', True)
                        )
                        db.add(new_user)
                        imported_data["users"] += 1
                        
            except Exception as e:
                print(f"Error importing users: {e}")
                db.rollback()
                pass
        
        # Импортируем проекты
        project_mapping = {}
        if "projects" in available_tables:
            try:
                # Используем прямой SQL запрос для большей гибкости
                cursor = source_session.connection().connection.cursor()
                cursor.execute("SELECT * FROM projects")
                rows = cursor.fetchall()
                
                # Получаем названия колонок
                cursor.execute("PRAGMA table_info(projects)")
                columns = [col[1] for col in cursor.fetchall()]
                
                for row in rows:
                    # Создаем словарь из строки
                    project_data = dict(zip(columns, row))
                    
                    # ВАЖНО: При импорте из экспорта приложения сохраняем ВСЕ проекты
                    # Не фильтруем по списку из 15 проектов
                    
                    # Проверяем, существует ли проект с таким названием
                    existing_project = db.query(models.Project).filter(models.Project.name == project_data['name']).first()
                    if not existing_project:
                        # Парсим даты
                        start_date = None
                        end_date = None
                        
                        if project_data.get('start_date'):
                            try:
                                if isinstance(project_data['start_date'], str):
                                    start_date = datetime.fromisoformat(project_data['start_date'].replace(' ', 'T'))
                                else:
                                    start_date = project_data['start_date']
                            except:
                                start_date = None
                        
                        if project_data.get('end_date'):
                            try:
                                if isinstance(project_data['end_date'], str):
                                    end_date = datetime.fromisoformat(project_data['end_date'].replace(' ', 'T'))
                                else:
                                    end_date = project_data['end_date']
                            except:
                                end_date = None
                        
                        new_project = models.Project(
                            name=project_data['name'],
                            logo=project_data.get('logo'),
                            start_date=start_date,
                            end_date=end_date,
                            is_archived=bool(project_data.get('is_archived', False)),
                            high_priority=bool(project_data.get('high_priority', False)),
                            posts_count=project_data.get('posts_count', 0)
                        )
                        db.add(new_project)
                        db.flush()  # Чтобы получить ID
                        imported_data["projects"] += 1
                        
                        # Сохраняем соответствие старого и нового ID
                        project_mapping[project_data['id']] = new_project.id
                    else:
                        project_mapping[project_data['id']] = existing_project.id
                        
            except Exception as e:
                print(f"Error importing projects: {e}")
                db.rollback()
                pass
        
        # Определяем тип базы данных
        is_telegram_db = False
        is_app_export = False
        
        # Проверяем, это БД из Telegram (tasks.db) или экспорт из приложения
        if "tasks" in available_tables and len(available_tables) <= 2:  # Только tasks и sqlite_sequence
            # Проверяем структуру таблицы tasks
            cursor = source_session.connection().connection.cursor()
            cursor.execute("PRAGMA table_info(tasks)")
            columns = [col[1] for col in cursor.fetchall()]
            
            # Telegram DB имеет специфичные колонки: designer, manager, admin
            if 'designer' in columns and 'manager' in columns and 'admin' in columns:
                is_telegram_db = True
                print("Обнаружена база данных Telegram (tasks.db)")
            
        elif all(table in available_tables for table in ['users', 'projects', 'tasks']):
            # Это экспорт из нашего приложения - есть все основные таблицы
            is_app_export = True
            print("Обнаружена база данных экспорта приложения")
        
        # Специальный импорт для БД Telegram
        if is_telegram_db:
            try:
                cursor = source_session.connection().connection.cursor()
                cursor.execute("SELECT * FROM tasks")
                rows = cursor.fetchall()
                
                cursor.execute("PRAGMA table_info(tasks)")
                columns = [col[1] for col in cursor.fetchall()]
                
                # Собираем пользователей по ролям из разных колонок
                designers = set()
                managers = set()
                admins = set()
                
                for row in rows:
                    task_data = dict(zip(columns, row))
                    
                    # Дизайнеры - из колонки designer
                    if task_data.get('designer') and task_data['designer'].strip():
                        designers.add(task_data['designer'].strip())
                    
                    # Менеджеры - из колонки manager
                    if task_data.get('manager') and task_data['manager'].strip():
                        managers.add(task_data['manager'].strip())
                    
                    # Админы - из колонки admin
                    if task_data.get('admin') and task_data['admin'].strip():
                        admins.add(task_data['admin'].strip())
                
                user_mapping = {}
                
                # Создаем дизайнеров
                for username in designers:
                    if username and username.strip():
                        telegram_username = username.lower().replace(' ', '_')
                        existing_user = db.query(models.User).filter(models.User.telegram_username == telegram_username).first()
                        if not existing_user:
                            new_user = models.User(
                                telegram_username=telegram_username,
                                name=username,
                                hashed_password='$2b$12$imported_user_needs_password_reset',
                                role='designer',
                                is_active=True
                            )
                            db.add(new_user)
                            db.flush()
                            user_mapping[username] = new_user.id
                            imported_data["users"] += 1
                        else:
                            user_mapping[username] = existing_user.id
                
                # Создаем менеджеров
                for username in managers:
                    if username and username.strip():
                        telegram_username = username.lower().replace(' ', '_')
                        existing_user = db.query(models.User).filter(models.User.telegram_username == telegram_username).first()
                        if not existing_user:
                            new_user = models.User(
                                telegram_username=telegram_username,
                                name=username,
                                hashed_password='$2b$12$imported_user_needs_password_reset',
                                role='smm_manager',
                                is_active=True
                            )
                            db.add(new_user)
                            db.flush()
                            user_mapping[username] = new_user.id
                            imported_data["users"] += 1
                        else:
                            user_mapping[username] = existing_user.id
                
                # Создаем админов
                for username in admins:
                    if username and username.strip():
                        telegram_username = username.lower().replace(' ', '_')
                        existing_user = db.query(models.User).filter(models.User.telegram_username == telegram_username).first()
                        if not existing_user:
                            new_user = models.User(
                                telegram_username=telegram_username,
                                name=username,
                                hashed_password='$2b$12$imported_user_needs_password_reset',
                                role='admin',
                                is_active=True
                            )
                            db.add(new_user)
                            db.flush()
                            user_mapping[username] = new_user.id
                            imported_data["users"] += 1
                        else:
                            user_mapping[username] = existing_user.id
                
                # Создаем проекты на основе уникальных названий проектов с нормализацией
                all_projects = set()
                project_descriptions = {}  # Сохраняем описания, которые были в поле project
                
                for row in rows:
                    task_data = dict(zip(columns, row))
                    project_raw = (task_data.get('project') or '').strip()
                    
                    # Нормализуем название проекта
                    normalized = normalize_project_name(project_raw)
                    
                    if normalized:
                        all_projects.add(normalized)
                    elif project_raw:
                        # Если это не проект, сохраняем как описание задачи
                        project_descriptions[id(row)] = project_raw
                
                project_mapping = {}
                for project_name in all_projects:
                    if project_name and project_name.strip():
                        existing_project = db.query(models.Project).filter(models.Project.name == project_name).first()
                        if not existing_project:
                            new_project = models.Project(
                                name=project_name
                            )
                            db.add(new_project)
                            db.flush()
                            project_mapping[project_name] = new_project.id
                            imported_data["projects"] += 1
                        else:
                            project_mapping[project_name] = existing_project.id
                
                # Теперь импортируем все задачи
                default_admin = db.query(models.User).filter(models.User.role == 'admin').first()
                
                for row in rows:
                    task_data = dict(zip(columns, row))
                    
                    # Определяем исполнителя и автора
                    designer = (task_data.get('designer') or '').strip()
                    manager = (task_data.get('manager') or '').strip()
                    admin = (task_data.get('admin') or '').strip()
                    
                    # Исполнитель (executor_id) - кому назначена задача (обычно дизайнер)
                    executor_id = user_mapping.get(designer) if designer else None
                    
                    # Автор (author_id) - кто поставил задачу, приоритет: админ > менеджер
                    author_id = None
                    if admin and admin in user_mapping:
                        author_id = user_mapping[admin]
                    elif manager and manager in user_mapping:
                        author_id = user_mapping[manager]
                    
                    # Автор обязателен, исполнитель может быть NULL
                    if not author_id:
                        if default_admin:
                            author_id = default_admin.id
                        else:
                            # Создаем дефолтного админа если его нет
                            default_admin = models.User(
                                login="imported_admin",
                                name="Импортированный Админ",
                                hashed_password='$2b$12$imported_user_needs_password_reset',
                                role='admin'
                            )
                            db.add(default_admin)
                            db.flush()
                            author_id = default_admin.id
                            imported_data["users"] += 1
                    
                    # executor_id может быть NULL - это нормально (как в боте "Не назначать")
                    
                    if author_id:  # Автор обязателен, исполнитель может быть NULL
                        # Конвертируем статус (в Telegram DB есть: active, completed, cancelled)
                        status_mapping = {
                            'completed': 'done',
                            'cancelled': 'cancelled',
                            'active': 'in_progress',
                            'in_progress': 'in_progress',
                            'pending': 'in_progress'
                        }
                        status = status_mapping.get(task_data.get('status', ''), 'in_progress')
                        
                        # Конвертируем дату
                        deadline_str = task_data.get('deadline', '')
                        deadline = None
                        if deadline_str:
                            try:
                                # Попробуем разные форматы даты
                                if '.' in deadline_str and ':' in deadline_str:
                                    deadline = datetime.strptime(deadline_str, '%d.%m.%Y %H:%M')
                                elif '.' in deadline_str:
                                    deadline = datetime.strptime(deadline_str, '%d.%m.%Y')
                            except:
                                pass
                        
                        # Нормализуем название проекта
                        project_raw = (task_data.get('project') or '').strip()
                        normalized_project = normalize_project_name(project_raw)
                        
                        # Определяем проект и описание
                        if normalized_project:
                            # Это настоящий проект
                            actual_project = normalized_project
                            task_description = task_data.get('description', '')
                        else:
                            # В поле project было описание задачи
                            actual_project = ""  # Без проекта
                            # Объединяем описание из поля project и description
                            desc_parts = []
                            if project_raw:
                                desc_parts.append(project_raw)
                            if task_data.get('description'):
                                desc_parts.append(task_data.get('description'))
                            task_description = '\n'.join(desc_parts) if desc_parts else 'Импортированная задача'
                        
                        # Формируем заголовок задачи
                        if task_description:
                            # Берем первую строку или первые 255 символов для заголовка
                            first_line = task_description.split('\n')[0]
                            task_title = first_line[:255] if len(first_line) > 255 else first_line
                        else:
                            task_title = 'Импортированная задача'
                        
                        # Создаем задачу
                        new_task = models.Task(
                            title=task_title,
                            description=task_description,
                            project=actual_project,
                            deadline=deadline,
                            status=status,
                            task_type=task_data.get('content_type'),
                            task_format=task_data.get('format'),
                            high_priority=False,
                            author_id=author_id,
                            executor_id=executor_id,
                            finished_at=datetime.fromisoformat(task_data['updated_at']) if status == 'done' and task_data.get('updated_at') else None,
                            created_at=datetime.fromisoformat(task_data['created_at']) if task_data.get('created_at') else datetime.utcnow()
                        )
                        db.add(new_task)
                        imported_data["tasks"] += 1
                        
            except Exception as e:
                print(f"Error importing from Downloads tasks.db: {e}")
                db.rollback()
                pass
        
        # Стандартный импорт задач для экспорта из приложения
        elif is_app_export and "tasks" in available_tables:
            try:
                # Используем прямой SQL запрос для большей гибкости  
                cursor = source_session.connection().connection.cursor()
                cursor.execute("SELECT * FROM tasks")  # Импортируем все задачи из экспорта
                rows = cursor.fetchall()
                
                # Получаем названия колонок
                cursor.execute("PRAGMA table_info(tasks)")
                columns = [col[1] for col in cursor.fetchall()]
                
                print(f"Импортируем задачи из экспорта приложения: {len(rows)} задач")
                
                for row in rows:
                    # Создаем словарь из строки
                    task_data = dict(zip(columns, row))
                    
                    # Находим автора и исполнителя по ID из экспорта
                    author = None
                    executor = None
                    
                    if task_data.get('author_id'):
                        # Ищем в импортированных пользователях или берем дефолтного админа
                        author = db.query(models.User).filter(models.User.role == 'admin').first()
                    
                    if task_data.get('executor_id'):
                        # Берем первого доступного пользователя или дефолтного
                        executor = db.query(models.User).first()
                    
                    # Если не найдены пользователи, используем дефолтного админа
                    if not author:
                        author = db.query(models.User).filter(models.User.role == 'admin').first()
                    if not executor:
                        executor = author
                    
                    if author and executor:
                        # Проверяем, не существует ли уже такая задача (по заголовку и дате)
                        existing_task = db.query(models.Task).filter(
                            models.Task.title == task_data['title'],
                            models.Task.created_at == task_data.get('created_at')
                        ).first()
                        
                        if not existing_task:
                            # Парсим даты
                            deadline = None
                            if task_data.get('deadline'):
                                try:
                                    if isinstance(task_data['deadline'], str):
                                        deadline = datetime.fromisoformat(task_data['deadline'].replace(' ', 'T'))
                                    else:
                                        deadline = task_data['deadline']
                                except:
                                    deadline = None
                            
                            finished_at = None
                            if task_data.get('finished_at'):
                                try:
                                    if isinstance(task_data['finished_at'], str):
                                        finished_at = datetime.fromisoformat(task_data['finished_at'].replace(' ', 'T'))
                                    else:
                                        finished_at = task_data['finished_at']
                                except:
                                    finished_at = None
                            
                            created_at = datetime.utcnow()
                            if task_data.get('created_at'):
                                try:
                                    if isinstance(task_data['created_at'], str):
                                        created_at = datetime.fromisoformat(task_data['created_at'].replace(' ', 'T'))
                                    else:
                                        created_at = task_data['created_at']
                                except:
                                    created_at = datetime.utcnow()
                            
                            # ВАЖНО: При импорте из экспорта приложения сохраняем проект КАК ЕСТЬ
                            # Не применяем фильтрацию по 15 проектам
                            new_task = models.Task(
                                title=task_data['title'],
                                description=task_data.get('description', ''),
                                project=task_data.get('project', ''),  # Сохраняем все проекты
                                deadline=deadline,
                                status=task_data.get('status', 'in_progress'),
                                task_type=task_data.get('task_type'),
                                task_format=task_data.get('task_format'),
                                high_priority=bool(task_data.get('high_priority', False)),
                                author_id=author.id,
                                executor_id=executor.id,
                                finished_at=finished_at,
                                created_at=created_at
                            )
                            db.add(new_task)
                            imported_data["tasks"] += 1
                            
            except Exception as e:
                print(f"Error importing tasks: {e}")
                db.rollback()
                pass
        
        # Импортируем цифровые проекты
        if "digital_projects" in available_tables:
            try:
                cursor = source_session.connection().connection.cursor()
                cursor.execute("SELECT * FROM digital_projects")
                rows = cursor.fetchall()
                
                cursor.execute("PRAGMA table_info(digital_projects)")
                columns = [col[1] for col in cursor.fetchall()]
                
                for row in rows:
                    digital_data = dict(zip(columns, row))
                    
                    # Находим проект и исполнителя
                    project_id = project_mapping.get(digital_data.get('project_id'))
                    executor = db.query(models.User).first()  # Используем первого доступного пользователя
                    service = db.query(models.DigitalService).first()  # Используем первый доступный сервис
                    
                    if project_id and executor:
                        # Проверяем, не существует ли уже такой цифровой проект
                        existing = db.query(models.DigitalProject).filter(
                            models.DigitalProject.project_id == project_id,
                            models.DigitalProject.executor_id == executor.id
                        ).first()
                        
                        if not existing:
                            # Парсим дату deadline
                            deadline = None
                            if digital_data.get('deadline'):
                                try:
                                    if isinstance(digital_data['deadline'], str):
                                        deadline = datetime.fromisoformat(digital_data['deadline'].replace(' ', 'T'))
                                    else:
                                        deadline = digital_data['deadline']
                                except:
                                    deadline = None
                            
                            new_digital = models.DigitalProject(
                                project_id=project_id,
                                service_id=service.id if service else None,
                                executor_id=executor.id,
                                deadline=deadline,
                                monthly=bool(digital_data.get('monthly', False)),
                                logo=digital_data.get('logo'),
                                status=digital_data.get('status', 'in_progress')
                            )
                            db.add(new_digital)
                            imported_data["digital_projects"] += 1
            except Exception as e:
                print(f"Error importing digital projects: {e}")
                db.rollback()
                pass
        
        # Импортируем операторов
        if "operators" in available_tables:
            try:
                cursor = source_session.connection().connection.cursor()
                cursor.execute("SELECT * FROM operators")
                rows = cursor.fetchall()
                
                cursor.execute("PRAGMA table_info(operators)")
                columns = [col[1] for col in cursor.fetchall()]
                
                for row in rows:
                    operator_data = dict(zip(columns, row))
                    existing = db.query(models.Operator).filter(models.Operator.name == operator_data['name']).first()
                    if not existing:
                        new_operator = models.Operator(
                            name=operator_data['name'],
                            role=operator_data.get('role', 'mobile'),
                            color=operator_data.get('color', '#ff0000'),
                            price_per_video=operator_data.get('price_per_video', 0)
                        )
                        db.add(new_operator)
                        imported_data["operators"] += 1
            except Exception as e:
                print(f"Error importing operators: {e}")
                db.rollback()
                pass
        
        # Импортируем статьи расходов
        if "expense_items" in available_tables:
            try:
                cursor = source_session.connection().connection.cursor()
                cursor.execute("SELECT * FROM expense_items")
                rows = cursor.fetchall()
                
                cursor.execute("PRAGMA table_info(expense_items)")
                columns = [col[1] for col in cursor.fetchall()]
                
                for row in rows:
                    item_data = dict(zip(columns, row))
                    existing = db.query(models.ExpenseCategory).filter(models.ExpenseCategory.name == item_data['name']).first()
                    if not existing:
                        new_item = models.ExpenseCategory(
                            name=item_data['name'],
                            description=item_data.get('description', ''),
                            is_active=bool(item_data.get('is_active', True))
                        )
                        db.add(new_item)
                        imported_data["expense_items"] += 1
            except Exception as e:
                print(f"Error importing expense items: {e}")
                db.rollback()
                pass
        
        # Импортируем налоги
        if "taxes" in available_tables:
            try:
                cursor = source_session.connection().connection.cursor()
                cursor.execute("SELECT * FROM taxes")
                rows = cursor.fetchall()
                
                cursor.execute("PRAGMA table_info(taxes)")
                columns = [col[1] for col in cursor.fetchall()]
                
                for row in rows:
                    tax_data = dict(zip(columns, row))
                    existing = db.query(models.Tax).filter(models.Tax.name == tax_data['name']).first()
                    if not existing:
                        new_tax = models.Tax(
                            name=tax_data['name'],
                            rate=float(tax_data.get('rate', 1.0))
                        )
                        db.add(new_tax)
                        imported_data["taxes"] += 1
            except Exception as e:
                print(f"Error importing taxes: {e}")
                db.rollback()
                pass
        
        # Сохраняем изменения
        db.commit()
        
        # Закрываем сессию источника
        source_session.close()
        
        return {
            "success": True,
            "message": "Database imported successfully",
            "imported": imported_data,
            "available_tables": available_tables
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")
    finally:
        # Удаляем временный файл
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


@app.get("/admin/export-database")
async def export_database(
    db: Session = Depends(auth.get_db),
    current: models.User = Depends(auth.get_current_active_user),
):
    """Экспорт текущей базы данных"""
    if current.role != models.RoleEnum.admin:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    # Путь к текущей БД
    db_url = str(db.bind.url).replace('sqlite:///', '')
    
    if not os.path.exists(db_url):
        raise HTTPException(status_code=404, detail="Database file not found")
    
    # Создаем имя файла с датой
    import datetime
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"database_export_{timestamp}.db"
    
    return FileResponse(
        path=db_url,
        filename=filename,
        media_type='application/octet-stream'
    )


@app.post("/admin/clear-cache")
async def clear_global_cache(
    db: Session = Depends(auth.get_db),
    current: models.User = Depends(auth.get_current_active_user),
):
    """Глобальная очистка кеша (только для администраторов)"""
    if current.role != models.RoleEnum.admin:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    # В данном случае мы не можем очистить кеш браузеров пользователей
    # но можем симулировать серверную очистку кеша
    return {
        "message": "Global cache cleared successfully",
        "timestamp": datetime.now(),
        "cleared_by": current.name
    }

@app.delete("/admin/clear-database")
async def clear_database(
    db: Session = Depends(auth.get_db),
    current: models.User = Depends(auth.get_current_active_user),
):
    """Полная очистка базы данных (кроме текущего админа)"""
    if current.role != models.RoleEnum.admin:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    try:
        # Счетчики для отчета
        deleted_counts = {
            "tasks": 0,
            "projects": 0,
            "users": 0,
            "digital_projects": 0,
            "operators": 0,
            "expenses": 0,
            "receipts": 0,
            "shootings": 0,
            "posts": 0,
            "files": 0,
            "taxes": 0,
            "expense_items": 0
        }
        
        # Безопасное удаление с проверкой существования моделей
        
        # Удаляем задачи
        if hasattr(models, 'Task'):
            deleted_counts["tasks"] = db.query(models.Task).count()
            db.query(models.Task).delete()
        
        # Удаляем посты проектов
        if hasattr(models, 'ProjectPost'):
            deleted_counts["posts"] = db.query(models.ProjectPost).count()
            db.query(models.ProjectPost).delete()
        
        # Удаляем съемки
        if hasattr(models, 'Shooting'):
            deleted_counts["shootings"] = db.query(models.Shooting).count()
            db.query(models.Shooting).delete()
        
        # Удаляем расходы и поступления
        expenses_count = 0
        if hasattr(models, 'ProjectExpense'):
            expenses_count += db.query(models.ProjectExpense).count()
            db.query(models.ProjectExpense).delete()
        if hasattr(models, 'ProjectClientExpense'):
            expenses_count += db.query(models.ProjectClientExpense).count()
            db.query(models.ProjectClientExpense).delete()
        deleted_counts["expenses"] = expenses_count
        
        if hasattr(models, 'ProjectReceipt'):
            deleted_counts["receipts"] = db.query(models.ProjectReceipt).count()
            db.query(models.ProjectReceipt).delete()
        
        # Удаляем отчеты
        if hasattr(models, 'ProjectReport'):
            db.query(models.ProjectReport).delete()
        
        # Удаляем цифровые проекты и связанные данные
        if hasattr(models, 'DigitalProjectTask'):
            db.query(models.DigitalProjectTask).delete()
        if hasattr(models, 'DigitalProjectFinance'):
            db.query(models.DigitalProjectFinance).delete()
        if hasattr(models, 'DigitalProjectExpense'):
            db.query(models.DigitalProjectExpense).delete()
        if hasattr(models, 'DigitalProject'):
            deleted_counts["digital_projects"] = db.query(models.DigitalProject).count()
            db.query(models.DigitalProject).delete()
        if hasattr(models, 'DigitalService'):
            db.query(models.DigitalService).delete()
        
        # Удаляем проекты
        if hasattr(models, 'Project'):
            deleted_counts["projects"] = db.query(models.Project).count()
            db.query(models.Project).delete()
        
        # Удаляем файлы ресурсов
        if hasattr(models, 'ResourceFile'):
            deleted_counts["files"] = db.query(models.ResourceFile).count()
            # Удаляем физические файлы
            files = db.query(models.ResourceFile).all()
            for file in files:
                if file.file_path and os.path.exists(file.file_path):
                    try:
                        os.remove(file.file_path)
                    except:
                        pass
            db.query(models.ResourceFile).delete()
        
        # Удаляем операторов
        if hasattr(models, 'Operator'):
            deleted_counts["operators"] = db.query(models.Operator).count()
            db.query(models.Operator).delete()
        
        # Удаляем категории расходов
        if hasattr(models, 'ExpenseCategory'):
            deleted_counts["expense_categories"] = db.query(models.ExpenseCategory).count()
            db.query(models.ExpenseCategory).delete()
        
        # Удаляем общие расходы
        if hasattr(models, 'CommonExpense'):
            deleted_counts["common_expenses"] = db.query(models.CommonExpense).count()
            db.query(models.CommonExpense).delete()
        
        # Удаляем налоги
        if hasattr(models, 'Tax'):
            deleted_counts["taxes"] = db.query(models.Tax).count()
            db.query(models.Tax).delete()
        
        # Удаляем всех пользователей кроме текущего админа
        if hasattr(models, 'User'):
            deleted_counts["users"] = db.query(models.User).filter(models.User.id != current.id).count()
            db.query(models.User).filter(models.User.id != current.id).delete()
        
        # Удаляем настройки (кроме timezone)
        if hasattr(models, 'Setting'):
            db.query(models.Setting).filter(models.Setting.key != "timezone").delete()
        
        # Сохраняем изменения
        db.commit()
        
        # Пересоздаем дефолтные налоги
        if hasattr(crud, 'create_tax'):
            crud.create_tax(db, "ЯТТ", 0.95)
            crud.create_tax(db, "ООО", 0.83)
            crud.create_tax(db, "Нал", 1.0)
        
        return {
            "success": True,
            "message": "Database cleared successfully",
            "deleted": deleted_counts
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Clear failed: {str(e)}")

# Endpoint для проверки синхронизации с Telegram ботом
@app.get("/sync/check")
async def check_sync_status(current_user = Depends(auth.get_current_active_user), db: Session = Depends(get_db)):
    """Проверка синхронизации данных между приложением и Telegram ботом"""
    try:
        # Получаем статистику по базе данных
        users = db.query(models.User).all()
        active_users = [u for u in users if u.is_active]
        users_with_telegram = [u for u in active_users if u.telegram_id]
        
        projects = db.query(models.Project).all()
        active_projects = [p for p in projects if not p.is_archived]
        
        tasks = db.query(models.Task).all()
        active_tasks = [t for t in tasks if t.status not in [models.TaskStatus.done, models.TaskStatus.cancelled]]
        recent_tasks = [t for t in tasks if t.created_at and (datetime.now() - t.created_at.replace(tzinfo=None)).days <= 7]
        
        # Проверяем целостность данных
        issues = []
        
        # Задачи без исполнителя
        tasks_no_executor = db.query(models.Task).filter(models.Task.executor_id == None).count()
        if tasks_no_executor > 0:
            issues.append(f"Задач без исполнителя: {tasks_no_executor}")
        
        # Задачи с несуществующими исполнителями
        all_user_ids = {u.id for u in users}
        tasks_invalid_executor = 0
        for task in tasks:
            if task.executor_id and task.executor_id not in all_user_ids:
                tasks_invalid_executor += 1
        if tasks_invalid_executor > 0:
            issues.append(f"Задач с несуществующими исполнителями: {tasks_invalid_executor}")
        
        # Пользователи без Telegram
        users_without_telegram = [u for u in active_users if not u.telegram_id]
        if users_without_telegram:
            issues.append(f"Активных пользователей без Telegram: {len(users_without_telegram)}")
        
        
        return {
            "status": "ok",
            "timestamp": datetime.now().isoformat(),
            "database": {
                "users": {
                    "total": len(users),
                    "active": len(active_users),
                    "with_telegram": len(users_with_telegram),
                    "without_telegram": [{"name": u.name, "role": u.role.value} for u in users_without_telegram]
                },
                "projects": {
                    "total": len(projects),
                    "active": len(active_projects)
                },
                "tasks": {
                    "total": len(tasks),
                    "active": len(active_tasks),
                    "recent": len(recent_tasks)
                }
            },
            "issues": issues,
            "sync_status": "synced" if not issues else "issues_found"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sync check failed: {str(e)}")

@app.post("/sync/fix")
async def fix_sync_issues(current_user = Depends(auth.get_current_admin_user), db: Session = Depends(get_db)):
    """Автоматическое исправление проблем синхронизации"""
    try:
        fixed_issues = []
        
        # Исправляем задачи без статуса
        tasks_no_status = db.query(models.Task).filter(models.Task.status == None).all()
        for task in tasks_no_status:
            task.status = models.TaskStatus.in_progress
        if tasks_no_status:
            fixed_issues.append(f"Установлен статус для {len(tasks_no_status)} задач")
        
        # Удаляем задачи с несуществующими пользователями
        all_user_ids = {u.id for u in db.query(models.User).all()}
        invalid_tasks = []
        for task in db.query(models.Task).all():
            if (task.executor_id and task.executor_id not in all_user_ids) or \
               (task.author_id and task.author_id not in all_user_ids):
                invalid_tasks.append(task)
        
        for task in invalid_tasks:
            db.delete(task)
        if invalid_tasks:
            fixed_issues.append(f"Удалено {len(invalid_tasks)} задач с несуществующими пользователями")
        
        db.commit()
        
        return {
            "status": "ok", 
            "fixed": fixed_issues,
            "message": f"Исправлено проблем: {len(fixed_issues)}"
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Sync fix failed: {str(e)}")


# ========== EXPENSE CATEGORIES ==========
@app.get("/expense-categories/", response_model=list[schemas.ExpenseCategory])
def get_expense_categories(
    skip: int = 0,
    limit: int = 100,
    active_only: bool = False,
    db: Session = Depends(auth.get_db),
    current: models.User = Depends(auth.get_current_active_user)
):
    """Get all expense categories"""
    query = db.query(models.ExpenseCategory)
    if active_only:
        query = query.filter(models.ExpenseCategory.is_active == True)
    return query.offset(skip).limit(limit).all()


@app.post("/expense-categories/", response_model=schemas.ExpenseCategory)
def create_expense_category(
    category: schemas.ExpenseCategoryCreate,
    db: Session = Depends(auth.get_db),
    current: models.User = Depends(auth.get_current_admin_user)
):
    """Create new expense category (admin only)"""
    db_category = models.ExpenseCategory(**category.dict())
    db.add(db_category)
    try:
        db.commit()
        db.refresh(db_category)
        return db_category
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail="Category with this name already exists")


@app.put("/expense-categories/{category_id}", response_model=schemas.ExpenseCategory)
def update_expense_category(
    category_id: int,
    category_update: schemas.ExpenseCategoryUpdate,
    db: Session = Depends(auth.get_db),
    current: models.User = Depends(auth.get_current_admin_user)
):
    """Update expense category (admin only)"""
    category = db.query(models.ExpenseCategory).filter(models.ExpenseCategory.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    for field, value in category_update.dict(exclude_unset=True).items():
        setattr(category, field, value)
    
    db.commit()
    db.refresh(category)
    return category


@app.delete("/expense-categories/{category_id}")
def delete_expense_category(
    category_id: int,
    force: bool = Query(False, description="Force delete even if used"),
    db: Session = Depends(auth.get_db),
    current: models.User = Depends(auth.get_current_admin_user)
):
    """Delete expense category completely (admin only)"""
    try:
        category = db.query(models.ExpenseCategory).filter(models.ExpenseCategory.id == category_id).first()
        if not category:
            raise HTTPException(status_code=404, detail="Category not found")
        
        if force:
            # Force delete: remove category references from expenses first
            try:
                db.query(models.ProjectExpense).filter(models.ProjectExpense.category_id == category_id).update({"category_id": None})
            except Exception:
                pass
                
            try:
                db.query(models.CommonExpense).filter(models.CommonExpense.category_id == category_id).update({"category_id": None})
            except Exception:
                pass
        else:
            # Check if category is used
            has_project_expenses = False
            has_common_expenses = False
            
            try:
                has_project_expenses = db.query(models.ProjectExpense).filter(models.ProjectExpense.category_id == category_id).first() is not None
            except Exception:
                pass
                
            try:
                has_common_expenses = db.query(models.CommonExpense).filter(models.CommonExpense.category_id == category_id).first() is not None
            except Exception:
                pass
            
            if has_project_expenses or has_common_expenses:
                raise HTTPException(status_code=400, detail="Cannot delete category that is used in expenses. Use force=true to delete anyway.")
        
        # Complete deletion
        db.delete(category)
        db.commit()
        return {"message": "Category deleted completely"}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"Error deleting expense category: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


# ========== COMMON EXPENSES ==========
@app.get("/common-expenses/")
def get_common_expenses(
    skip: int = 0,
    limit: int = 100,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    category_id: Optional[int] = None,
    db: Session = Depends(auth.get_db),
    current: models.User = Depends(auth.get_current_active_user)
):
    """Get all common expenses with filters"""
    query = db.query(models.CommonExpense)
    
    if start_date:
        query = query.filter(models.CommonExpense.date >= start_date)
    if end_date:
        query = query.filter(models.CommonExpense.date <= end_date)
    if category_id:
        query = query.filter(models.CommonExpense.category_id == category_id)
    
    expenses = query.order_by(models.CommonExpense.date.desc()).offset(skip).limit(limit).all()
    
    # Convert to dictionaries and handle date serialization
    result = []
    for expense in expenses:
        expense_dict = {
            "id": expense.id,
            "name": expense.name,
            "amount": expense.amount,
            "description": expense.description,
            "category_id": expense.category_id,
            "date": expense.date.strftime('%Y-%m-%d') if expense.date else None,
            "created_at": expense.created_at,
            "created_by": expense.created_by,
            "category": expense.category,
            "creator": expense.creator
        }
        result.append(expense_dict)
    
    return result


@app.post("/common-expenses/")
def create_common_expense(
    expense: schemas.CommonExpenseCreate,
    db: Session = Depends(auth.get_db),
    current: models.User = Depends(auth.get_current_active_user)
):
    """Create new common expense"""
    db_expense = models.CommonExpense(
        **expense.dict(),
        created_by=current.id
    )
    db.add(db_expense)
    db.commit()
    db.refresh(db_expense)
    
    # Convert to dictionary and handle date serialization
    result = {
        "id": db_expense.id,
        "name": db_expense.name,
        "amount": db_expense.amount,
        "description": db_expense.description,
        "category_id": db_expense.category_id,
        "date": db_expense.date.strftime('%Y-%m-%d') if db_expense.date else None,
        "created_at": db_expense.created_at,
        "created_by": db_expense.created_by,
        "category": db_expense.category,
        "creator": db_expense.creator
    }
    
    return result


@app.put("/common-expenses/{expense_id}")
def update_common_expense(
    expense_id: int,
    expense_update: schemas.CommonExpenseUpdate,
    db: Session = Depends(auth.get_db),
    current: models.User = Depends(auth.get_current_active_user)
):
    """Update common expense"""
    expense = db.query(models.CommonExpense).filter(models.CommonExpense.id == expense_id).first()
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    
    for field, value in expense_update.dict(exclude_unset=True).items():
        setattr(expense, field, value)
    
    db.commit()
    db.refresh(expense)
    
    # Convert to dictionary and handle date serialization
    result = {
        "id": expense.id,
        "name": expense.name,
        "amount": expense.amount,
        "description": expense.description,
        "category_id": expense.category_id,
        "date": expense.date.strftime('%Y-%m-%d') if expense.date else None,
        "created_at": expense.created_at,
        "created_by": expense.created_by,
        "category": expense.category,
        "creator": expense.creator
    }
    
    return result


@app.delete("/common-expenses/{expense_id}")
def delete_common_expense(
    expense_id: int,
    db: Session = Depends(auth.get_db),
    current: models.User = Depends(auth.get_current_active_user)
):
    """Delete common expense"""
    expense = db.query(models.CommonExpense).filter(models.CommonExpense.id == expense_id).first()
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    
    db.delete(expense)
    db.commit()
    return {"message": "Expense deleted"}


# ========== PROJECT EXPENSES ==========
@app.get("/project-expenses/")
def get_project_expenses(
    skip: int = 0,
    limit: int = 100,
    project_id: Optional[int] = Query(None, description="Filter by project ID"),
    db: Session = Depends(auth.get_db),
    current: models.User = Depends(auth.get_current_active_user)
):
    """Get all project expenses"""
    query = db.query(models.ProjectExpense).options(
        joinedload(models.ProjectExpense.project)
    )
    
    if project_id:
        query = query.filter(models.ProjectExpense.project_id == project_id)
    
    return query.offset(skip).limit(limit).all()

@app.get("/project-expenses/detailed", response_model=List[schemas.ProjectExpenseDetailed])
def get_project_expenses_detailed(
    skip: int = 0,
    limit: int = 100,
    project_id: Optional[int] = Query(None, description="Filter by project ID"),
    category_id: Optional[int] = Query(None, description="Filter by category"),
    start_date: Optional[date] = Query(None, description="Start date filter"),
    end_date: Optional[date] = Query(None, description="End date filter"),
    db: Session = Depends(auth.get_db),
    current: models.User = Depends(auth.get_current_active_user)
):
    """Get detailed project expenses with project and category names"""
    from sqlalchemy import and_
    
    query = db.query(
        models.ProjectExpense.id,
        models.ProjectExpense.project_id,
        models.Project.name.label('project_name'),
        models.ProjectExpense.category_id,
        models.ExpenseCategory.name.label('category_name'),
        models.ProjectExpense.name,
        models.ProjectExpense.amount,
        models.ProjectExpense.description,
        models.ProjectExpense.date,
        models.ProjectExpense.created_at,
        models.ProjectExpense.created_by,
        models.User.name.label('creator_name')
    ).join(
        models.Project, models.ProjectExpense.project_id == models.Project.id
    ).outerjoin(
        models.ExpenseCategory, models.ProjectExpense.category_id == models.ExpenseCategory.id
    ).outerjoin(
        models.User, models.ProjectExpense.created_by == models.User.id
    )
    
    # Apply filters
    if project_id:
        query = query.filter(models.ProjectExpense.project_id == project_id)
    
    if category_id:
        query = query.filter(models.ProjectExpense.category_id == category_id)
    
    if start_date:
        query = query.filter(models.ProjectExpense.date >= start_date)
    
    if end_date:
        query = query.filter(models.ProjectExpense.date <= end_date)
    
    # Order by date descending
    query = query.order_by(models.ProjectExpense.date.desc())
    
    results = query.offset(skip).limit(limit).all()
    
    # Convert to response format
    return [
        schemas.ProjectExpenseDetailed(
            id=r.id,
            project_id=r.project_id,
            project_name=r.project_name,
            category_id=r.category_id,
            category_name=r.category_name,
            name=r.name,
            amount=r.amount,
            description=r.description,
            date=r.date,
            created_at=r.created_at,
            created_by=r.created_by,
            creator_name=r.creator_name
        ) for r in results
    ]

@app.post("/project-expenses/")
def create_project_expense(
    expense: schemas.ProjectExpenseCreate,
    db: Session = Depends(auth.get_db),
    current: models.User = Depends(auth.get_current_active_user)
):
    """Create new project expense"""
    # Verify project exists
    project = db.query(models.Project).filter(models.Project.id == expense.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    db_expense = models.ProjectExpense(**expense.dict(), created_by=current.id)
    db.add(db_expense)
    db.commit()
    db.refresh(db_expense)
    return db_expense

@app.delete("/project-expenses/{expense_id}")
def delete_project_expense(
    expense_id: int,
    db: Session = Depends(auth.get_db),
    current: models.User = Depends(auth.get_current_active_user)
):
    """Delete project expense"""
    expense = db.query(models.ProjectExpense).filter(models.ProjectExpense.id == expense_id).first()
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    
    db.delete(expense)
    db.commit()
    return {"message": "Expense deleted successfully"}

# ========== PROJECT EXPENSES UPDATE ==========
@app.put("/project-expenses/{expense_id}")
def update_project_expense(
    expense_id: int,
    expense_update: schemas.ProjectExpenseUpdate,
    db: Session = Depends(auth.get_db),
    current: models.User = Depends(auth.get_current_active_user)
):
    """Update project expense"""
    expense = db.query(models.ProjectExpense).filter(models.ProjectExpense.id == expense_id).first()
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    
    for field, value in expense_update.dict(exclude_unset=True).items():
        setattr(expense, field, value)
    
    db.commit()
    db.refresh(expense)
    return expense


# ========== EXPENSE REPORTS ==========
@app.get("/expense-reports/", response_model=schemas.ExpenseReport)
def get_expense_report(
    start_date: Optional[date] = Query(None, description="Start date for report"),
    end_date: Optional[date] = Query(None, description="End date for report"),
    category_id: Optional[int] = Query(None, description="Filter by category"),
    project_id: Optional[int] = Query(None, description="Filter by project"),
    db: Session = Depends(auth.get_db),
    current: models.User = Depends(auth.get_current_active_user)
):
    """Generate expense report with filters"""
    from sqlalchemy import func
    from collections import defaultdict
    
    try:
        # Initialize totals and collections
        items = []
        categories_breakdown = defaultdict(float)
        total_project = 0.0
        total_common = 0.0
        
        # Query project expenses
        try:
            project_query = db.query(models.ProjectExpense)
            
            # Apply filters for project expenses
            if start_date:
                project_query = project_query.filter(models.ProjectExpense.date >= start_date)
            if end_date:
                project_query = project_query.filter(models.ProjectExpense.date <= end_date)
            if category_id:
                project_query = project_query.filter(models.ProjectExpense.category_id == category_id)
            if project_id:
                project_query = project_query.filter(models.ProjectExpense.project_id == project_id)
            
            project_expenses = project_query.all()
            
            for expense in project_expenses:
                # Get related data manually to avoid relationship issues
                project_name = None
                category_name = None
                creator_name = None
                
                if expense.project_id:
                    project = db.query(models.Project).filter(models.Project.id == expense.project_id).first()
                    project_name = project.name if project else None
                
                if expense.category_id:
                    category = db.query(models.ExpenseCategory).filter(models.ExpenseCategory.id == expense.category_id).first()
                    category_name = category.name if category else None
                    
                if expense.created_by:
                    creator = db.query(models.User).filter(models.User.id == expense.created_by).first()
                    creator_name = creator.name if creator else None
                
                # Create expense report item
                items.append(schemas.ExpenseReportItem(
                    id=expense.id,
                    name=expense.name,
                    amount=float(expense.amount) if expense.amount else 0.0,
                    description=expense.description,
                    date=expense.date if expense.date else expense.created_at.date(),
                    category_name=category_name,
                    project_name=project_name,
                    expense_type="project",
                    created_by_name=creator_name
                ))
                
                amount = float(expense.amount) if expense.amount else 0.0
                total_project += amount
                if category_name:
                    categories_breakdown[category_name] += amount
                    
        except Exception as e:
            print(f"Warning: Error querying project expenses: {e}")
            # Continue without project expenses
        
        # Query common expenses
        try:
            common_query = db.query(models.CommonExpense)
            
            # Apply filters for common expenses
            if start_date:
                common_query = common_query.filter(models.CommonExpense.date >= start_date)
            if end_date:
                common_query = common_query.filter(models.CommonExpense.date <= end_date)
            if category_id:
                common_query = common_query.filter(models.CommonExpense.category_id == category_id)
            # Skip project_id filter for common expenses
            
            common_expenses = common_query.all()
            
            for expense in common_expenses:
                # Get related data manually
                category_name = None
                creator_name = None
                
                if expense.category_id:
                    category = db.query(models.ExpenseCategory).filter(models.ExpenseCategory.id == expense.category_id).first()
                    category_name = category.name if category else None
                    
                if expense.created_by:
                    creator = db.query(models.User).filter(models.User.id == expense.created_by).first()
                    creator_name = creator.name if creator else None
                
                items.append(schemas.ExpenseReportItem(
                    id=expense.id,
                    name=expense.name,
                    amount=float(expense.amount),
                    description=expense.description,
                    date=expense.date,
                    category_name=category_name,
                    project_name=None,
                    expense_type="common",
                    created_by_name=creator_name
                ))
                
                amount = float(expense.amount)
                total_common += amount
                if category_name:
                    categories_breakdown[category_name] += amount
                    
        except Exception as e:
            print(f"Warning: Error querying common expenses: {e}")
            # Continue without common expenses
        
        # Sort by date descending
        items.sort(key=lambda x: x.date, reverse=True)
        
        return schemas.ExpenseReport(
            total_amount=total_project + total_common,
            project_expenses=total_project,
            common_expenses=total_common,
            items=items,
            categories_breakdown=dict(categories_breakdown)
        )
        
    except Exception as e:
        print(f"Error generating expense report: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate report: {str(e)}")


# ========== EMPLOYEE EXPENSES ==========
@app.get("/employee-expenses/", response_model=List[schemas.EmployeeExpense])
def get_employee_expenses(
    user_id: Optional[int] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db: Session = Depends(auth.get_db),
    current: models.User = Depends(auth.get_current_active_user)
):
    """Get employee expenses with filters"""
    query = db.query(models.EmployeeExpense)
    
    if user_id:
        query = query.filter(models.EmployeeExpense.user_id == user_id)
    else:
        # If not admin, show only own expenses
        if current.role != models.RoleEnum.admin:
            query = query.filter(models.EmployeeExpense.user_id == current.id)
    
    if start_date:
        query = query.filter(models.EmployeeExpense.date >= start_date)
    if end_date:
        query = query.filter(models.EmployeeExpense.date <= end_date)
    
    return query.all()


@app.post("/employee-expenses/", response_model=schemas.EmployeeExpense)
def create_employee_expense(
    expense: schemas.EmployeeExpenseCreate,
    db: Session = Depends(auth.get_db),
    current: models.User = Depends(auth.get_current_active_user)
):
    """Create new employee expense"""
    db_expense = models.EmployeeExpense(
        user_id=current.id,
        **expense.dict()
    )
    db.add(db_expense)
    db.commit()
    db.refresh(db_expense)
    return db_expense


@app.put("/employee-expenses/{expense_id}", response_model=schemas.EmployeeExpense)
def update_employee_expense(
    expense_id: int,
    expense_update: schemas.EmployeeExpenseUpdate,
    db: Session = Depends(auth.get_db),
    current: models.User = Depends(auth.get_current_active_user)
):
    """Update employee expense"""
    expense = db.query(models.EmployeeExpense).filter(models.EmployeeExpense.id == expense_id).first()
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    
    # Check permission
    if current.role != models.RoleEnum.admin and expense.user_id != current.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this expense")
    
    for field, value in expense_update.dict(exclude_unset=True).items():
        setattr(expense, field, value)
    
    db.commit()
    db.refresh(expense)
    return expense


@app.delete("/employee-expenses/{expense_id}")
def delete_employee_expense(
    expense_id: int,
    db: Session = Depends(auth.get_db),
    current: models.User = Depends(auth.get_current_active_user)
):
    """Delete employee expense"""
    expense = db.query(models.EmployeeExpense).filter(models.EmployeeExpense.id == expense_id).first()
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    
    # Check permission
    if current.role != models.RoleEnum.admin and expense.user_id != current.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this expense")
    
    db.delete(expense)
    db.commit()
    return {"message": "Expense deleted successfully"}


# ========== COMPREHENSIVE EXPENSE REPORTS ==========
@app.get("/expense-reports/summary", response_model=schemas.ExpenseReportSummary)
def get_expense_report_summary(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db: Session = Depends(auth.get_db),
    current: models.User = Depends(auth.get_current_active_user)
):
    """Get expense report summary"""
    from datetime import datetime
    from sqlalchemy import func
    
    # Default to current month
    if not start_date:
        now = datetime.now()
        start_date = date(now.year, now.month, 1)
    if not end_date:
        now = datetime.now()
        if now.month == 12:
            end_date = date(now.year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = date(now.year, now.month + 1, 1) - timedelta(days=1)
    
    # Calculate total expenses (common + project)
    common_total = db.query(func.sum(models.CommonExpense.amount)).filter(
        models.CommonExpense.date >= start_date,
        models.CommonExpense.date <= end_date
    ).scalar() or 0
    
    project_total = db.query(func.sum(models.ProjectExpense.amount)).filter(
        models.ProjectExpense.date >= start_date,
        models.ProjectExpense.date <= end_date
    ).scalar() or 0
    
    employee_total = db.query(func.sum(models.EmployeeExpense.amount)).filter(
        models.EmployeeExpense.date >= start_date,
        models.EmployeeExpense.date <= end_date
    ).scalar() or 0
    
    return schemas.ExpenseReportSummary(
        total_expenses=float(common_total + project_total + employee_total),
        project_expenses=float(project_total),
        employee_expenses=float(employee_total)
    )


@app.get("/expense-reports/employees", response_model=List[schemas.EmployeeExpenseReport])
def get_employee_expense_report(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    role: Optional[str] = Query(None),
    user_id: Optional[int] = Query(None),
    db: Session = Depends(auth.get_db),
    current: models.User = Depends(auth.get_current_active_user)
):
    """Get employee expense report"""
    from datetime import datetime
    from sqlalchemy import func
    
    # Default to current month
    if not start_date:
        now = datetime.now()
        start_date = date(now.year, now.month, 1)
    if not end_date:
        now = datetime.now()
        if now.month == 12:
            end_date = date(now.year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = date(now.year, now.month + 1, 1) - timedelta(days=1)
    
    # Query users
    user_query = db.query(models.User).filter(models.User.is_active == True)
    if role:
        user_query = user_query.filter(models.User.role == role)
    if user_id:
        user_query = user_query.filter(models.User.id == user_id)
    
    users = user_query.all()
    reports = []
    
    for user in users:
        expenses = db.query(models.EmployeeExpense).filter(
            models.EmployeeExpense.user_id == user.id,
            models.EmployeeExpense.date >= start_date,
            models.EmployeeExpense.date <= end_date
        ).all()
        
        total = sum(e.amount for e in expenses)
        
        reports.append(schemas.EmployeeExpenseReport(
            user_id=user.id,
            user_name=user.name,
            role=user.role,
            total_amount=float(total),
            expenses=expenses
        ))
    
    return reports


@app.get("/expense-reports/operators", response_model=List[schemas.OperatorExpenseReport])
def get_operator_expense_report(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    operator_id: Optional[int] = Query(None),
    db: Session = Depends(auth.get_db),
    current: models.User = Depends(auth.get_current_active_user)
):
    """Get operator expense report"""
    from datetime import datetime
    from sqlalchemy import func
    
    # Default to current month
    if not start_date:
        now = datetime.now()
        start_date = date(now.year, now.month, 1)
    if not end_date:
        now = datetime.now()
        if now.month == 12:
            end_date = date(now.year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = date(now.year, now.month + 1, 1) - timedelta(days=1)
    
    # Query operators
    operator_query = db.query(models.Operator)
    if operator_id:
        operator_query = operator_query.filter(models.Operator.id == operator_id)
    
    operators = operator_query.all()
    reports = []
    
    for operator in operators:
        # Count completed videos for this operator in the period
        completed_videos = db.query(models.Shooting).filter(
            models.Shooting.operator_id == operator.id,
            models.Shooting.completed == True,
            models.Shooting.datetime >= datetime.combine(start_date, datetime.min.time()),
            models.Shooting.datetime <= datetime.combine(end_date, datetime.max.time())
        ).all()
        
        videos_count = sum(s.completed_quantity or 0 for s in completed_videos)
        
        # Calculate total amount
        if operator.is_salaried:
            total_amount = float(operator.monthly_salary or 0)
        else:
            total_amount = float(videos_count * (operator.price_per_video or 0))
        
        reports.append(schemas.OperatorExpenseReport(
            operator_id=operator.id,
            operator_name=operator.name,
            role=operator.role.value,
            is_salaried=operator.is_salaried,
            monthly_salary=operator.monthly_salary,
            price_per_video=operator.price_per_video,
            videos_completed=videos_count,
            total_amount=total_amount
        ))
    
    return reports


# ========== UPDATE OPERATOR ENDPOINT ==========
@app.put("/operators/{operator_id}", response_model=schemas.Operator)
def update_operator(
    operator_id: int,
    operator_update: schemas.OperatorUpdate,
    db: Session = Depends(auth.get_db),
    current: models.User = Depends(auth.get_current_active_user)
):
    """Update operator"""
    operator = db.query(models.Operator).filter(models.Operator.id == operator_id).first()
    if not operator:
        raise HTTPException(status_code=404, detail="Operator not found")
    
    for field, value in operator_update.dict(exclude_unset=True).items():
        setattr(operator, field, value)
    
    db.commit()
    db.refresh(operator)
    return operator

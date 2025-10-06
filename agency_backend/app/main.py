from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, Query, status, Body, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import FileResponse, HTMLResponse
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy.orm import Session, joinedload, sessionmaker
from sqlalchemy import inspect, text, create_engine
from dotenv import load_dotenv
from datetime import datetime, date, timedelta, time as datetime_time
from typing import List, Optional
import os
import json
import shutil
import tempfile
import re
import threading
import time
import logging
from fastapi.staticfiles import StaticFiles

from . import models, schemas, crud, auth, telegram_notifier
from .models import get_local_time_utc5
from .database import engine, Base, SessionLocal
from .auth import get_db

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create tables including new expense models
try:
    Base.metadata.create_all(bind=engine)
    print("[OK] Database tables created successfully")
except Exception as e:
    print(f"[WARN] Error creating database tables: {e}")

# Ensure expense tables exist
def ensure_expense_tables():
    with engine.connect() as conn:
        inspector = inspect(conn)
        
        # Check if new expense tables exist
        tables = inspector.get_table_names()
        
        if "expense_categories" not in tables:
            print("[DB] Creating expense_categories table...")
            models.ExpenseCategory.__table__.create(bind=engine, checkfirst=True)

        if "common_expenses" not in tables:
            print("[DB] Creating common_expenses table...")
            models.CommonExpense.__table__.create(bind=engine, checkfirst=True)

        # Add new columns to existing project_expenses if they don't exist
        if "project_expenses" in tables:
            cols = [c["name"] for c in inspector.get_columns("project_expenses")]

            if "category_id" not in cols:
                print("[DB] Adding category_id to project_expenses...")
                conn.execute(text("ALTER TABLE project_expenses ADD COLUMN category_id INTEGER"))
            if "description" not in cols:
                print("[DB] Adding description to project_expenses...")
                conn.execute(text("ALTER TABLE project_expenses ADD COLUMN description TEXT"))
            if "date" not in cols:
                print("[DB] Adding date to project_expenses...")
                conn.execute(text("ALTER TABLE project_expenses ADD COLUMN date DATE DEFAULT CURRENT_DATE"))
            if "created_by" not in cols:
                print("[DB] Adding created_by to project_expenses...")
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


def ensure_task_columns():
    """Ensure tasks table has all required columns"""
    with engine.connect() as conn:
        inspector = inspect(conn)
        cols = [c["name"] for c in inspector.get_columns("tasks")]
        
        # List of columns to add if missing
        columns_to_add = [
            ("accepted_at", "DATETIME"),
            ("finished_at", "DATETIME"),
            ("is_recurring", "BOOLEAN DEFAULT 0"),
            ("recurrence_type", "VARCHAR"),
            ("recurrence_time", "VARCHAR"),
            ("recurrence_days", "VARCHAR"),
            ("next_run_at", "DATETIME"),
            ("original_task_id", "INTEGER"),
            ("overdue_count", "INTEGER DEFAULT 0")
        ]
        
        for col_name, col_type in columns_to_add:
            if col_name not in cols:
                conn.execute(text(f"ALTER TABLE tasks ADD COLUMN {col_name} {col_type}"))
                print(f"[OK] Added {col_name} column to tasks table")
        
        conn.commit()




ensure_digital_task_priority_column()
ensure_task_columns()

# ========== RECURRING TASKS SCHEDULER ==========
def recurring_tasks_scheduler():
    """Планировщик для генерации повторяющихся задач"""
    import time
    from datetime import datetime, timedelta
    
    while True:
        try:
            current_time = get_local_time_utc5()
            # Убираем timezone info для корректного сравнения с naive datetime в БД
            current_time_naive = current_time.replace(tzinfo=None)
            logger.info(f"[CRON] Recurring tasks check: {current_time_naive.strftime('%Y-%m-%d %H:%M:%S')}")

            # Создаем новую сессию базы данных для планировщика
            db = SessionLocal()
            try:
                # Проверяем все повторяющиеся задачи для отладки
                all_recurring = db.query(models.Task).filter(models.Task.is_recurring == True).all()
                logger.info(f"🔍 Found {len(all_recurring)} recurring tasks:")
                for task in all_recurring:
                    logger.info(f"   Task: {task.title}, Status: {task.status}, Next run: {task.next_run_at}, Current: {current_time_naive}")
                    logger.info(f"   Comparison: {task.next_run_at} <= {current_time_naive} = {task.next_run_at <= current_time_naive if task.next_run_at else 'None'}")

                # Находим задачи, которые нужно повторить
                # ВАЖНО: Пропускаем шаблоны со статусом 'done' или 'cancelled' (приостановленные)
                # Автосоздание работает только для шаблонов в статусах 'new' или 'in_progress'
                due_tasks = db.query(models.Task).filter(
                    models.Task.is_recurring == True,
                    models.Task.next_run_at <= current_time_naive,
                    models.Task.status.in_(['new', 'in_progress'])  # Только активные шаблоны
                ).all()
                logger.info(f"🔍 Query filter: is_recurring=True, next_run_at <= '{current_time}', status IN ('new', 'in_progress')")

                for template_task in due_tasks:
                    logger.info(f"🔄 Creating new instance of recurring task: {template_task.title}")
                    logger.info(f"   Template task status: {template_task.status}")

                    # Создаем НОВУЮ задачу на основе шаблона
                    # ВАЖНО: Явно устанавливаем status='new' (строка), а не копируем из шаблона
                    new_task = models.Task(
                        title=template_task.title,
                        description=template_task.description,
                        project=template_task.project,
                        task_type=template_task.task_type,
                        task_format=template_task.task_format,
                        deadline=template_task.deadline,
                        executor_id=template_task.executor_id,
                        author_id=template_task.author_id,
                        status='new',  # Явно устанавливаем строку 'new', а не enum
                        created_at=models.get_local_time_utc5(),
                        accepted_at=None,
                        finished_at=None,
                        is_recurring=False,  # Новая задача не является повторяющейся
                        recurrence_type=None,
                        recurrence_time=None,
                        recurrence_days=None,
                        next_run_at=None,
                        overdue_count=0,
                        resume_count=0
                    )
                    logger.info(f"   New task status set to: {new_task.status}")

                    db.add(new_task)
                    logger.info(f"   After db.add, status: {new_task.status}")
                    db.flush()  # Получаем ID новой задачи
                    logger.info(f"   After db.flush, status: {new_task.status}")
                    logger.info(f"[OK] Created new task instance from template: {template_task.title}")

                    # Отправляем уведомление исполнителю о новой задаче
                    if new_task.executor_id:
                        executor = db.query(models.User).filter(models.User.id == new_task.executor_id).first()
                        if executor and executor.telegram_id:
                            task_data = {
                                'title': new_task.title,
                                'description': new_task.description,
                                'project_name': new_task.project or 'Не указан',
                                'task_type': new_task.task_type or 'Не указан',
                                'format': new_task.task_format,
                                'deadline_text': new_task.deadline.strftime('%d.%m.%Y %H:%M') if new_task.deadline else 'Не установлен'
                            }
                            telegram_notifier.send_task_notification(executor.telegram_id, new_task.id, task_data)
                            logger.info(f"📨 Sent notification to executor {executor.name} (telegram_id: {executor.telegram_id})")

                    # Обновляем next_run_at в шаблоне для следующего повтора
                    template_task.next_run_at = crud.calculate_next_run_at(
                        template_task.recurrence_type.value,
                        db,
                        template_task.recurrence_time,
                        template_task.recurrence_days
                    )

                    logger.info(f"[OK] Template updated, next run: {template_task.next_run_at}")

                if due_tasks:
                    db.commit()
                    logger.info(f"[INFO] Created {len(due_tasks)} new task instances from recurring templates")
                else:
                    logger.info("📭 No recurring tasks due")

            except Exception as e:
                logger.error(f"❌ Error in recurring tasks scheduler: {e}")
                db.rollback()
            finally:
                db.close()

        except Exception as e:
            logger.error(f"❌ Critical error in scheduler: {e}")

        # Проверяем каждые 5 минут
        time.sleep(30)  # Ждем 30 секунд до следующей проверки (для тестирования)

# Запуск планировщика повторяющихся задач в фоновом потоке
scheduler_thread = threading.Thread(target=recurring_tasks_scheduler, daemon=True)
scheduler_thread.start()
logger.info("[START] Recurring tasks scheduler started")


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
            print("[OK] Sample expenses created")
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

# Глобальный словарь для отслеживания статуса импорта
import_status = {
    "is_running": False,
    "progress": 0,
    "message": "Нет активных операций",
    "imported_data": {},
    "error": None,
    "started_at": None,
    "completed_at": None
}

# Mount static files
try:
    app.mount("/static", StaticFiles(directory="static"), name="static")
except Exception as e:
    print(f"Warning: Could not mount static directory: {e}")

# Configure CORS properly
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:5174,http://localhost:3000,http://127.0.0.1:5173,http://127.0.0.1:5174,http://127.0.0.1:3000")
allowed_origins = [origin.strip() for origin in cors_origins.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,
)

# Additional middleware to ensure CORS headers on error responses
class CORSErrorMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            response = await call_next(request)
            return response
        except Exception as e:
            # Ensure CORS headers are present on error responses
            response = Response(
                content='{"detail":"Internal server error"}',
                status_code=500,
                media_type="application/json"
            )
            origin = request.headers.get('origin')
            if origin and origin in allowed_origins:
                response.headers["Access-Control-Allow-Origin"] = origin
                response.headers["Access-Control-Allow-Credentials"] = "true"
                response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, PATCH, OPTIONS"
                response.headers["Access-Control-Allow-Headers"] = "*"
            return response

app.add_middleware(CORSErrorMiddleware)


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
    except HTTPException:
        # Re-raise HTTPExceptions (like 401) as-is
        raise
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


@app.get("/users/by-telegram/{telegram_id}")
def get_user_by_telegram(telegram_id: int, username: str = None, db: Session = Depends(auth.get_db)):
    """Получить пользователя по Telegram ID или username (для бота)"""
    # Сначала ищем по telegram_id
    user = db.query(models.User).filter(models.User.telegram_id == telegram_id).first()

    # Если не найден и передан username, ищем по telegram_username
    if not user and username:
        user = db.query(models.User).filter(
            models.User.telegram_username == username,
            models.User.telegram_id == None
        ).first()

        # Если найден, обновляем telegram_id
        if user:
            user.telegram_id = telegram_id
            db.commit()
            db.refresh(user)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return user


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

    # Проверяем, что пользователь не пытается удалить сам себя
    if current.id == user_id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")

    # Проверяем, что пользователь существует
    user = crud.get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        crud.delete_user(db, user_id)
        return {"ok": True, "message": f"User '{user.name}' deleted successfully"}
    except Exception as e:
        print(f"Error deleting user {user_id}: {str(e)}")  # Логирование для отладки
        raise HTTPException(status_code=500, detail=f"Error deleting user: {str(e)}")


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


# Telegram авторизация
@app.post("/auth/telegram", response_model=schemas.TelegramAuthResponse)
def authorize_telegram_user(
    request: schemas.TelegramAuthRequest,
    db: Session = Depends(auth.get_db)
):
    """API endpoint для авторизации пользователей Telegram бота"""

    # Ищем пользователя по username
    user = crud.authorize_telegram_user(db, request.telegram_id, request.username)

    if user:
        return schemas.TelegramAuthResponse(
            success=True,
            message=f"Пользователь {user.name} успешно авторизован в Telegram боте с ролью {user.role}",
            user=user
        )
    else:
        return schemas.TelegramAuthResponse(
            success=False,
            message=f"Пользователь с @username '{request.username}' не найден в системе. Обратитесь к администратору для добавления вашего username в веб-приложение.",
            user=None
        )


@app.post("/telegram/status", response_model=schemas.TelegramStatusResponse)
def check_telegram_user_status(
    request: schemas.TelegramStatusRequest,
    db: Session = Depends(auth.get_db)
):
    """API endpoint для проверки статуса доступа пользователя в реальном времени"""

    user = crud.check_telegram_user_status(db, request.telegram_id, request.username)

    if user:
        return schemas.TelegramStatusResponse(
            has_access=True,
            user=user,
            message=f"Пользователь {user.name} имеет доступ к боту с ролью {user.role}"
        )
    else:
        return schemas.TelegramStatusResponse(
            has_access=False,
            user=None,
            message="Доступ к боту отсутствует. Обратитесь к администратору."
        )


@app.post("/telegram/auto-auth", response_model=schemas.TelegramAuthResponse)
def auto_authorize_telegram_user(
    request: schemas.TelegramAuthRequest,
    db: Session = Depends(auth.get_db)
):
    """API endpoint для автоматической привязки telegram пользователя"""

    user = crud.find_and_link_telegram_user(
        db,
        request.telegram_id,
        request.username,
        request.first_name,
        request.last_name
    )

    if user:
        return schemas.TelegramAuthResponse(
            success=True,
            message=f"Успешная авторизация! Добро пожаловать, {user.name}",
            user=user
        )
    else:
        return schemas.TelegramAuthResponse(
            success=False,
            message="Пользователь не найден в системе. Обратитесь к администратору для получения доступа.",
            user=None
        )


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
    # Создаем задачу
    created_task = crud.create_task(db, task, author_id=current.id)

    # Отправляем уведомление только для обычных задач, НЕ для шаблонов повторяющихся задач
    # Для шаблонов (is_recurring=True) уведомления будут отправляться только при автосоздании экземпляров
    if created_task.executor_id and not created_task.is_recurring:
        executor = db.query(models.User).filter(models.User.id == created_task.executor_id).first()
        if executor and executor.telegram_id:
            # Получаем название проекта
            project_name = "Не указан"
            if created_task.project:
                project = db.query(models.Project).filter(models.Project.name == created_task.project).first()
                if project:
                    project_name = project.name

            # Форматируем дедлайн
            deadline_text = "Не установлен"
            if created_task.deadline:
                deadline_text = created_task.deadline.strftime("%d.%m.%Y %H:%M")

            # Отправляем уведомление
            telegram_notifier.send_task_notification(
                executor_telegram_id=executor.telegram_id,
                task_id=created_task.id,
                task_data={
                    'title': created_task.title,
                    'description': created_task.description,
                    'project_name': project_name,
                    'task_type': created_task.task_type or 'Не указан',
                    'format': created_task.task_format,
                    'deadline_text': deadline_text
                }
            )

    return created_task


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


@app.patch("/tasks/{task_id}/accept", response_model=schemas.Task)
def accept_task(
    task_id: int,
    db: Session = Depends(auth.get_db),
    current: models.User = Depends(auth.get_current_active_user),
):
    """Принять задачу в работу (изменить статус с 'new' на 'in_progress')"""
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Проверяем, что задача назначена текущему пользователю
    if task.executor_id != current.id and current.role != models.RoleEnum.admin:
        raise HTTPException(status_code=403, detail="You can only accept tasks assigned to you")
    
    # Проверяем, что задача имеет статус "new"
    if task.status != models.TaskStatus.new:
        raise HTTPException(status_code=400, detail="Task is already accepted or completed")
    
    # Меняем статус на "in_progress" и сохраняем время принятия
    task.status = models.TaskStatus.in_progress
    task.accepted_at = models.get_local_time_utc5()
    db.commit()
    db.refresh(task)
    return task


@app.patch("/tasks/{task_id}/status", response_model=schemas.Task)
def update_task_status(
    task_id: int,
    status: str = Query(..., description="New status for the task"),
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


@app.patch("/tasks/{task_id}/priority", response_model=schemas.Task)
def update_task_priority(
    task_id: int,
    high_priority: bool = Body(..., embed=True),
    db: Session = Depends(auth.get_db),
    current: models.User = Depends(auth.get_current_active_user),
):
    """Обновить приоритет задачи"""
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Проверяем права на изменение приоритета задачи
    can_modify = False
    
    # Администраторы могут изменять любые задачи
    if current.role == models.RoleEnum.admin:
        can_modify = True
    # SMM менеджеры могут изменять задачи назначенные дизайнерам, SMM менеджерам и диджитал
    elif current.role == models.RoleEnum.smm_manager:
        if task.executor_id:
            executor = db.query(models.User).filter(models.User.id == task.executor_id).first()
            if executor and executor.role in [models.RoleEnum.designer, models.RoleEnum.smm_manager]:
                can_modify = True
        # Также SMM менеджеры могут изменять созданные ими задачи
        if task.author_id == current.id:
            can_modify = True
    # Остальные могут изменять только назначенные им задачи или созданные ими
    else:
        if task.executor_id == current.id or task.author_id == current.id:
            can_modify = True
    
    if not can_modify:
        raise HTTPException(status_code=403, detail="Not allowed to modify this task priority")
    
    # Обновляем приоритет
    task.high_priority = high_priority
    db.commit()
    db.refresh(task)
    return task


# Task types and formats endpoints
@app.get("/tasks/types")
def get_task_types(
    role: str = None,
    db: Session = Depends(auth.get_db)
):
    """Получить типы задач по роли (публичный эндпоинт для бота)"""
    task_types = {
        'designer': [
            {'name': 'Motion', 'icon': '🎞️'},
            {'name': 'Статика', 'icon': '🖼️'},
            {'name': 'Видео', 'icon': '🎬'},
            {'name': 'Карусель', 'icon': '🖼️'},
            {'name': 'Другое', 'icon': '📌'}
        ],
        'smm_manager': [
            {'name': 'Публикация', 'icon': '[INFO]'},
            {'name': 'Контент план', 'icon': '[INFO]'},
            {'name': 'Отчет', 'icon': '📊'},
            {'name': 'Съемка', 'icon': '📹'},
            {'name': 'Встреча', 'icon': '🤝'},
            {'name': 'Стратегия', 'icon': '📈'},
            {'name': 'Презентация', 'icon': '🎤'},
            {'name': 'Админ задачи', 'icon': '🗂️'},
            {'name': 'Анализ', 'icon': '🔎'},
            {'name': 'Брифинг', 'icon': '[DB]'},
            {'name': 'Сценарий', 'icon': '📜'},
            {'name': 'Другое', 'icon': '📌'}
        ],
        'digital': [
            {'name': 'Настройка рекламы', 'icon': '🎯'},
            {'name': 'Анализ эффективности', 'icon': '📈'},
            {'name': 'A/B тестирование', 'icon': '🧪'},
            {'name': 'Настройка аналитики', 'icon': '📊'},
            {'name': 'Оптимизация конверсий', 'icon': '[DB]'},
            {'name': 'Email-маркетинг', 'icon': '📧'},
            {'name': 'Контекстная реклама', 'icon': '🔍'},
            {'name': 'Таргетированная реклама', 'icon': '🎯'},
            {'name': 'SEO оптимизация', 'icon': '🔍'},
            {'name': 'Веб-аналитика', 'icon': '📊'},
            {'name': 'Другое', 'icon': '📌'}
        ],
        'admin': [
            {'name': 'Публикация', 'icon': '[INFO]'},
            {'name': 'Съемки', 'icon': '🎥'},
            {'name': 'Стратегия', 'icon': '📈'},
            {'name': 'Отчет', 'icon': '📊'},
            {'name': 'Бухгалтерия', 'icon': '[DB]'},
            {'name': 'Встреча', 'icon': '🤝'},
            {'name': 'Документы', 'icon': '📄'},
            {'name': 'Работа с кадрами', 'icon': '👥'},
            {'name': 'Планерка', 'icon': '🗓️'},
            {'name': 'Администраторские задачи', 'icon': '🛠️'},
            {'name': 'Собеседование', 'icon': '🧑‍💼'},
            {'name': 'Договор', 'icon': '✍️'},
            {'name': 'Другое', 'icon': '📌'}
        ]
    }

    if role:
        return task_types.get(role, [])
    return task_types


@app.get("/tasks/formats")
def get_task_formats(
    db: Session = Depends(auth.get_db)
):
    """Получить форматы задач для дизайнеров (публичный эндпоинт для бота)"""
    return [
        {'name': '9:16', 'icon': '📱'},
        {'name': '1:1', 'icon': '🔲'},
        {'name': '4:5', 'icon': '🖼️'},
        {'name': '16:9', 'icon': '🎞️'},
        {'name': 'Другое', 'icon': '📌'}
    ]


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
    return user.role in [models.RoleEnum.smm_manager, models.RoleEnum.admin]


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
    
    # Статистика задач (исключаем экземпляры повторяющихся задач)
    total_tasks = db.query(models.Task).filter(models.Task.original_task_id.is_(None)).count()
    completed_tasks = db.query(models.Task).filter(
        and_(models.Task.status == "done", models.Task.original_task_id.is_(None))
    ).count()
    in_progress_tasks = db.query(models.Task).filter(
        and_(models.Task.status == "in_progress", models.Task.original_task_id.is_(None))
    ).count()
    overdue_tasks = db.query(models.Task).filter(
        and_(
            models.Task.deadline < datetime.utcnow(),
            models.Task.status != "done",
            models.Task.original_task_id.is_(None)
        )
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
                models.Task.finished_at >= start_date,
                models.Task.original_task_id.is_(None)  # Исключаем повторяющиеся задачи
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


@app.get("/admin/import-status")
async def get_import_status(
    current: models.User = Depends(auth.get_current_active_user),
):
    """Получить статус текущего импорта"""
    if current.role != models.RoleEnum.admin:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    return import_status


@app.post("/admin/import-database")
async def import_database(
    file: UploadFile = File(...),
    filter_by_roles: bool = True,
    db: Session = Depends(auth.get_db),
    current: models.User = Depends(auth.get_current_active_user),
):
    """Импорт данных из загруженной БД с файлами (асинхронный запуск)"""
    if current.role != models.RoleEnum.admin:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    # Проверяем, не запущен ли уже импорт
    if import_status["is_running"]:
        raise HTTPException(status_code=409, detail="Import is already running")

    if not file.filename or not (file.filename.endswith('.db') or file.filename.endswith('.zip')):
        raise HTTPException(status_code=400, detail="Only .db or .zip files are allowed")

    import zipfile

    # Сохраняем файл и запускаем импорт в фоновом потоке
    original_cwd = os.getcwd()
    app_dir = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.dirname(app_dir)

    # Сохраняем загруженный файл во временную директорию
    tmp_upload_path = None
    tmp_dir = None

    if file.filename.endswith('.zip'):
        with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as tmp_zip:
            shutil.copyfileobj(file.file, tmp_zip)
            tmp_upload_path = tmp_zip.name
    else:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as tmp_file:
            shutil.copyfileobj(file.file, tmp_file)
            tmp_upload_path = tmp_file.name

    # Сбрасываем статус и запускаем фоновую задачу
    import_status["is_running"] = True
    import_status["progress"] = 0
    import_status["message"] = "Начинается импорт..."
    import_status["imported_data"] = {}
    import_status["error"] = None
    import_status["started_at"] = datetime.utcnow().isoformat()
    import_status["completed_at"] = None

    # Запускаем импорт в отдельном потоке
    def run_import_in_background():
        db_session = SessionLocal()
        try:
            perform_database_import(
                tmp_upload_path,
                filter_by_roles,
                db_session,
                backend_dir,
                original_cwd
            )
        except Exception as e:
            import_status["error"] = str(e)
            import_status["message"] = f"Ошибка импорта: {str(e)}"
            print(f"Background import error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            import_status["is_running"] = False
            import_status["completed_at"] = datetime.utcnow().isoformat()
            db_session.close()

    # Запускаем в отдельном потоке
    import_thread = threading.Thread(target=run_import_in_background, daemon=True)
    import_thread.start()

    # Немедленно возвращаем ответ клиенту
    return {
        "success": True,
        "message": "Import started in background. Use /admin/import-status to check progress",
        "started_at": import_status["started_at"]
    }


def perform_database_import(tmp_upload_path, filter_by_roles, db, backend_dir, original_cwd):
    """Выполняет импорт базы данных (запускается в фоновом потоке)"""
    import zipfile

    os.chdir(backend_dir)
    print(f"Импорт: текущая директория: {os.getcwd()}")
    print(f"Импорт: backend директория: {backend_dir}")

    tmp_path = None
    tmp_dir = None

    try:
        import_status["message"] = "Распаковка файлов..."
        import_status["progress"] = 5

        if tmp_upload_path.endswith('.zip'):
            # Обрабатываем ZIP архив
            tmp_dir = tempfile.mkdtemp()

            with zipfile.ZipFile(tmp_upload_path, 'r') as zip_ref:
                zip_ref.extractall(tmp_dir)

            # Находим файл базы данных
            db_files = []
            for root, dirs, files in os.walk(tmp_dir):
                for file_name in files:
                    if file_name.endswith('.db'):
                        db_files.append(os.path.join(root, file_name))

            if not db_files:
                raise HTTPException(status_code=400, detail="No .db file found in ZIP archive")

            tmp_path = db_files[0]  # Используем первый найденный .db файл

            # Восстанавливаем файлы из архива
            print("Восстанавливаем файлы из архива...")
            file_directories = [
                "uploads/leads",      # CRM файлы заявок
                "static/projects",    # логотипы проектов
                "static/digital",     # логотипы digital проектов
                "files",              # ресурсные файлы
                "contracts"           # контракты пользователей
            ]

            restored_files = 0
            for dir_path in file_directories:
                # Пытаемся найти папки с учетом того, что экспорт мог быть сделан из корня проекта
                possible_paths = [
                    os.path.join(tmp_dir, dir_path),                    # uploads/leads
                    os.path.join(tmp_dir, "agency_backend", dir_path),  # agency_backend/uploads/leads
                ]

                extracted_dir = None
                for path in possible_paths:
                    if os.path.exists(path):
                        extracted_dir = path
                        print(f"Найдена папка: {path}")
                        break

                if extracted_dir:
                    # Создаем целевую папку если её нет
                    os.makedirs(dir_path, exist_ok=True)

                    # Копируем файлы
                    files_in_dir = 0
                    for root, dirs, files in os.walk(extracted_dir):
                        for file_name in files:
                            src_file = os.path.join(root, file_name)
                            # Вычисляем относительный путь от извлеченной папки
                            rel_path = os.path.relpath(src_file, extracted_dir)
                            dst_file = os.path.join(dir_path, rel_path)

                            # Создаем папку назначения если нужно
                            os.makedirs(os.path.dirname(dst_file), exist_ok=True)

                            # Копируем файл
                            print(f"Копируем файл: {src_file} -> {dst_file}")
                            shutil.copy2(src_file, dst_file)
                            files_in_dir += 1
                            restored_files += 1

                    print(f"Восстановлено файлов из {dir_path}: {files_in_dir}")
                else:
                    print(f"Папка {dir_path} не найдена в архиве (проверены пути: {possible_paths})")

            print(f"Всего файлов восстановлено: {restored_files}")

        else:
            # Обрабатываем обычный .db файл
            tmp_path = tmp_upload_path

        import_status["message"] = "Подключение к базе данных..."
        import_status["progress"] = 15
        # Подключаемся к загруженной БД
        source_engine = create_engine(f"sqlite:///{tmp_path}")
        
        # Проверяем существование таблиц
        source_inspector = inspect(source_engine)
        available_tables = source_inspector.get_table_names()
        
        if not available_tables:
            raise HTTPException(status_code=400, detail="Database file appears to be empty or corrupted")
        
        SourceSession = sessionmaker(bind=source_engine)
        source_session = SourceSession()
        
        imported_data = {
            "users": 0,
            "projects": 0,
            "project_posts": 0,
            "tasks": 0,
            "digital_projects": 0,
            "operators": 0,
            "expense_items": 0,
            "taxes": 0,
            "leads": 0,
            "lead_notes": 0,
            "lead_attachments": 0,
            "lead_history": 0,
            "expense_categories": 0,
            "project_expenses": 0,
            "common_expenses": 0,
            "project_client_expenses": 0,
            "digital_project_expenses": 0,
            "employee_expenses": 0,
            "project_reports": 0
        }
        
        # Импортируем пользователей
        import_status["message"] = "Импорт пользователей..."
        import_status["progress"] = 20

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
                            name=user_data.get('name', 'Unknown'),
                            hashed_password=user_data.get('hashed_password', 'imported_user_password'),
                            role=user_data.get('role', 'designer'),
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
        import_status["message"] = "Импорт проектов..."
        import_status["progress"] = 30

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

        # Импортируем посты проектов
        if "project_posts" in available_tables:
            try:
                cursor = source_session.connection().connection.cursor()
                cursor.execute("SELECT * FROM project_posts")
                rows = cursor.fetchall()

                cursor.execute("PRAGMA table_info(project_posts)")
                columns = [col[1] for col in cursor.fetchall()]

                for row in rows:
                    post_data = dict(zip(columns, row))

                    # Проверяем, что проект существует (используем project_mapping для маппинга ID)
                    old_project_id = post_data.get('project_id')
                    new_project_id = project_mapping.get(old_project_id, old_project_id)

                    project = db.query(models.Project).filter(models.Project.id == new_project_id).first()
                    if not project:
                        print(f"Skipping post for non-existent project ID: {new_project_id}")
                        continue

                    # Парсим дату
                    post_date = None
                    if post_data.get('date'):
                        try:
                            post_date = datetime.fromisoformat(str(post_data['date']).replace('Z', '+00:00'))
                        except ValueError:
                            try:
                                post_date = datetime.strptime(str(post_data['date']), '%Y-%m-%d')
                            except ValueError:
                                post_date = datetime.utcnow()

                    # Создаем новый пост (проверяем на дубликаты по project_id + date)
                    existing_post = db.query(models.ProjectPost).filter(
                        models.ProjectPost.project_id == new_project_id,
                        models.ProjectPost.date == post_date
                    ).first()

                    if not existing_post:
                        # Validate enum values
                        post_type = post_data.get('post_type', 'static')
                        if post_type == 'story':  # Convert legacy 'story' to 'static'
                            post_type = 'static'
                        elif post_type not in ['video', 'static', 'carousel']:
                            post_type = 'static'  # Default fallback

                        status = post_data.get('status', 'in_progress')
                        if status not in ['in_progress', 'cancelled', 'approved', 'overdue']:
                            status = 'in_progress'  # Default fallback

                        new_post = models.ProjectPost(
                            project_id=new_project_id,
                            date=post_date or datetime.utcnow(),
                            posts_per_day=post_data.get('posts_per_day', 1),
                            post_type=post_type,
                            status=status
                        )
                        db.add(new_post)
                        imported_data["project_posts"] += 1

            except Exception as e:
                print(f"Error importing project posts: {e}")
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
                # Находим разумных дефолтных пользователей
                default_manager = db.query(models.User).filter(models.User.role == 'smm_manager').first()
                default_designer = db.query(models.User).filter(models.User.role == 'designer').first()
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
                        # Если нет автора - пропускаем задачу с предупреждением вместо назначения дефолтного
                        print(f"[WARN] Пропускаем задачу '{task_data.get('description', '')[:30]}...' - не найден автор")
                        continue
                    
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
        
        # Создаем общий маппинг пользователей для любого импорта с таблицей users
        user_mapping = {}  # old_id -> new_id
        if "users" in available_tables:
            # Получаем всех пользователей из импортированной БД
            cursor = source_session.connection().connection.cursor()
            cursor.execute("SELECT * FROM users")
            user_rows = cursor.fetchall()

            cursor.execute("PRAGMA table_info(users)")
            user_columns = [col[1] for col in cursor.fetchall()]

            print(f"Создаем маппинг пользователей: {len(user_rows)} пользователей")

            # Маппинг устаревших ролей на актуальные
            role_mapping = {
                'digital': 'admin',  # Устаревшая роль digital -> admin
            }

            for user_row in user_rows:
                user_data = dict(zip(user_columns, user_row))
                old_user_id = user_data.get('id')
                username = user_data.get('telegram_username') or user_data.get('login')

                if old_user_id and username:
                    # Используем прямой SQL запрос для проверки существования пользователя
                    # Это избегает проблем с десериализацией enum в SQLAlchemy
                    result = db.execute(
                        text("SELECT id FROM users WHERE telegram_username = :username"),
                        {"username": username}
                    ).fetchone()

                    if result:
                        existing_user_id = result[0]
                        user_mapping[old_user_id] = existing_user_id
                        print(f"Маппинг пользователя: {old_user_id} -> {existing_user_id} ({username})")
                    else:
                        # Создаем недостающего пользователя
                        user_name = user_data.get('name', username)
                        user_role = user_data.get('role', 'designer')

                        # Преобразуем устаревшие роли
                        user_role = role_mapping.get(user_role, user_role)

                        # Проверяем, что роль допустима
                        valid_roles = ['designer', 'smm_manager', 'admin', 'inactive']
                        if user_role not in valid_roles:
                            print(f"[WARN] Недопустимая роль '{user_role}' для пользователя {username}, используем 'designer'")
                            user_role = 'designer'

                        new_user = models.User(
                            telegram_username=username,
                            name=user_name,
                            hashed_password='$2b$12$imported_user_needs_password_reset',
                            role=user_role,
                            is_active=True
                        )
                        db.add(new_user)
                        db.flush()
                        user_mapping[old_user_id] = new_user.id
                        imported_data["users"] += 1
                        print(f"Создан пользователь: {old_user_id} -> {new_user.id} ({username}, {user_name}, {user_role})")

        # Улучшенный импорт задач с правильным маппингом пользователей для любой БД
        if "tasks" in available_tables:
            try:

                # Получаем задачи из экспорта
                cursor.execute("SELECT * FROM tasks")  # Импортируем все задачи из экспорта
                rows = cursor.fetchall()

                # Получаем названия колонок
                cursor.execute("PRAGMA table_info(tasks)")
                columns = [col[1] for col in cursor.fetchall()]

                import_status["message"] = f"Импорт задач ({len(rows)} задач)..."
                import_status["progress"] = 50
                print(f"Импортируем задачи из экспорта приложения: {len(rows)} задач")

                for row in rows:
                    # Создаем словарь из строки
                    task_data = dict(zip(columns, row))

                    # Находим автора и исполнителя по ID из экспорта через маппинг
                    author_id = None
                    executor_id = None

                    if task_data.get('author_id'):
                        old_author_id = task_data['author_id']
                        author_id = user_mapping.get(old_author_id)
                        if author_id:
                            print(f"Найден автор: {old_author_id} -> {author_id}")
                        else:
                            print(f"Автор не найден для ID {old_author_id}")

                    if task_data.get('executor_id'):
                        old_executor_id = task_data['executor_id']
                        executor_id = user_mapping.get(old_executor_id)
                        if executor_id:
                            print(f"Найден исполнитель: {old_executor_id} -> {executor_id}")
                        else:
                            print(f"Исполнитель не найден для ID {old_executor_id}")

                    # Если не найдены пользователи, пропускаем задачу с предупреждением
                    if not author_id and task_data.get('author_id'):
                        print(f"[WARN] Пропускаем задачу '{task_data.get('title', '')[:30]}...' - не найден автор с ID {task_data.get('author_id')}")
                        continue

                    if not executor_id and task_data.get('executor_id'):
                        print(f"[WARN] Пропускаем задачу '{task_data.get('title', '')[:30]}...' - не найден исполнитель с ID {task_data.get('executor_id')}")
                        continue

                    # Если в исходной БД нет author_id/executor_id, используем разумные дефолты
                    if not author_id and not task_data.get('author_id'):
                        # Назначаем на первого доступного СММ менеджера
                        default_manager = db.query(models.User).filter(models.User.role == 'smm_manager').first()
                        if default_manager:
                            author_id = default_manager.id
                            print(f"Назначаем дефолтного менеджера как автора: {default_manager.telegram_username}")

                    if not executor_id and not task_data.get('executor_id'):
                        # Назначаем на первого доступного дизайнера или того же автора
                        default_designer = db.query(models.User).filter(models.User.role == 'designer').first()
                        if default_designer:
                            executor_id = default_designer.id
                            print(f"Назначаем дефолтного дизайнера как исполнителя: {default_designer.telegram_username}")
                        elif author_id:
                            executor_id = author_id
                            print(f"Назначаем автора как исполнителя")

                    if author_id and executor_id:
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

                            # Парсим next_run_at для повторяющихся задач
                            next_run_at = None
                            if task_data.get('next_run_at'):
                                try:
                                    if isinstance(task_data['next_run_at'], str):
                                        next_run_at = datetime.fromisoformat(task_data['next_run_at'].replace(' ', 'T'))
                                    else:
                                        next_run_at = task_data['next_run_at']
                                except:
                                    next_run_at = None

                            new_task = models.Task(
                                title=task_data['title'],
                                description=task_data.get('description', ''),
                                project=task_data.get('project', ''),  # Сохраняем все проекты
                                deadline=deadline,
                                status=task_data.get('status', 'in_progress'),
                                task_type=task_data.get('task_type'),
                                task_format=task_data.get('task_format'),
                                high_priority=bool(task_data.get('high_priority', False)),
                                author_id=author_id,
                                executor_id=executor_id,
                                finished_at=finished_at,
                                created_at=created_at,
                                # Поля для повторяющихся задач
                                is_recurring=bool(task_data.get('is_recurring', False)),
                                recurrence_type=task_data.get('recurrence_type'),
                                recurrence_time=task_data.get('recurrence_time'),
                                recurrence_days=task_data.get('recurrence_days'),
                                next_run_at=next_run_at,
                                original_task_id=task_data.get('original_task_id'),
                                resume_count=task_data.get('resume_count', 0),
                                overdue_count=task_data.get('overdue_count', 0)
                            )
                            db.add(new_task)
                            imported_data["tasks"] += 1
                            recurring_status = f" [ПОВТОРЯЮЩАЯСЯ: {task_data.get('recurrence_type')}]" if task_data.get('is_recurring') else ""
                            print(f"Создана задача: '{task_data['title']}' автор_id={author_id}, исполнитель_id={executor_id}{recurring_status}")
                        else:
                            print(f"Задача уже существует: '{task_data['title']}'")
                    else:
                        print(f"Пропускаем задачу '{task_data.get('title', 'БЕЗ НАЗВАНИЯ')}' - не найдены автор ({author_id}) или исполнитель ({executor_id})")
                            
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

                    # Используем правильный маппинг для исполнителя
                    executor_id = None
                    if digital_data.get('executor_id'):
                        old_executor_id = digital_data['executor_id']
                        executor_id = user_mapping.get(old_executor_id)
                        if not executor_id:
                            # Используем подходящего пользователя (дизайнер > СММ)
                            default_designer = db.query(models.User).filter(models.User.role == 'designer').first()
                            default_manager = db.query(models.User).filter(models.User.role == 'smm_manager').first()

                            if default_designer:
                                executor_id = default_designer.id
                                print(f"Назначаем дефолтного дизайнера для digital_project: {default_designer.telegram_username}")
                            elif default_manager:
                                executor_id = default_manager.id
                                print(f"Назначаем дефолтного менеджера для digital_project: {default_manager.telegram_username}")
                            else:
                                print(f"[WARN] Пропускаем digital_project - не найден исполнитель с ID {old_executor_id}")
                                continue

                    service = db.query(models.DigitalService).first()  # Используем первый доступный сервис

                    if project_id and executor_id:
                        # Проверяем, не существует ли уже такой цифровой проект
                        existing = db.query(models.DigitalProject).filter(
                            models.DigitalProject.project_id == project_id,
                            models.DigitalProject.executor_id == executor_id
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
                                executor_id=executor_id,
                                deadline=deadline,
                                monthly=bool(digital_data.get('monthly', False)),
                                logo=digital_data.get('logo'),
                                status=digital_data.get('status', 'in_progress')
                            )
                            db.add(new_digital)
                            imported_data["digital_projects"] += 1
                            print(f"Создан цифровой проект: project_id={project_id}, исполнитель_id={executor_id}")
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

        # Импортируем CRM заявки (leads)
        lead_mapping = {}  # old_lead_id -> new_lead_id
        import_status["message"] = "Импорт CRM заявок..."
        import_status["progress"] = 70

        if "leads" in available_tables:
            try:
                cursor = source_session.connection().connection.cursor()
                cursor.execute("SELECT * FROM leads")
                rows = cursor.fetchall()

                cursor.execute("PRAGMA table_info(leads)")
                columns = [col[1] for col in cursor.fetchall()]

                for row in rows:
                    lead_data = dict(zip(columns, row))

                    # Парсим даты
                    created_at = None
                    if lead_data.get('created_at'):
                        try:
                            if isinstance(lead_data['created_at'], str):
                                created_at = datetime.fromisoformat(lead_data['created_at'].replace(' ', 'T'))
                            else:
                                created_at = lead_data['created_at']
                        except:
                            created_at = None

                    # Проверяем, существует ли заявка
                    # Проверяем по ID, если есть, или по уникальной комбинации
                    existing = None
                    if lead_data.get('phone') and lead_data.get('email'):
                        existing = db.query(models.Lead).filter(
                            models.Lead.client_contact == lead_data.get('phone')
                        ).first()
                        if not existing:
                            existing = db.query(models.Lead).filter(
                                models.Lead.client_contact == lead_data.get('email')
                            ).first()
                    elif lead_data.get('id'):
                        existing = db.query(models.Lead).filter(models.Lead.id == lead_data.get('id')).first()

                    if not existing:
                        # Обработка дат для этапа КП
                        proposal_date = None
                        if lead_data.get('proposal_date'):
                            try:
                                if isinstance(lead_data['proposal_date'], str):
                                    proposal_date = datetime.fromisoformat(lead_data['proposal_date'].replace(' ', 'T'))
                                else:
                                    proposal_date = lead_data['proposal_date']
                            except:
                                proposal_date = None

                        # Обработка даты напоминания
                        reminder_date = None
                        if lead_data.get('reminder_date'):
                            try:
                                if isinstance(lead_data['reminder_date'], str):
                                    reminder_date = datetime.fromisoformat(lead_data['reminder_date'].replace(' ', 'T'))
                                else:
                                    reminder_date = lead_data['reminder_date']
                            except:
                                reminder_date = None

                        # Обработка даты начала ожидания
                        waiting_started_at = None
                        if lead_data.get('waiting_started_at'):
                            try:
                                if isinstance(lead_data['waiting_started_at'], str):
                                    waiting_started_at = datetime.fromisoformat(lead_data['waiting_started_at'].replace(' ', 'T'))
                                else:
                                    waiting_started_at = lead_data['waiting_started_at']
                            except:
                                waiting_started_at = None

                        # Обработка updated_at
                        updated_at = None
                        if lead_data.get('updated_at'):
                            try:
                                if isinstance(lead_data['updated_at'], str):
                                    updated_at = datetime.fromisoformat(lead_data['updated_at'].replace(' ', 'T'))
                                else:
                                    updated_at = lead_data['updated_at']
                            except:
                                updated_at = None

                        # Обработка last_activity_at
                        last_activity_at = None
                        if lead_data.get('last_activity_at'):
                            try:
                                if isinstance(lead_data['last_activity_at'], str):
                                    last_activity_at = datetime.fromisoformat(lead_data['last_activity_at'].replace(' ', 'T'))
                                else:
                                    last_activity_at = lead_data['last_activity_at']
                            except:
                                last_activity_at = None

                        new_lead = models.Lead(
                            title=lead_data.get('title', lead_data.get('company_name', 'Импортированная заявка')),
                            source=lead_data.get('source', 'import'),
                            status=lead_data.get('status', 'new'),
                            manager_id=lead_data.get('assigned_to_id', lead_data.get('manager_id')),

                            # Основные поля
                            client_name=lead_data.get('contact_person', lead_data.get('client_name')),
                            client_contact=lead_data.get('phone', lead_data.get('email', lead_data.get('client_contact'))),
                            company_name=lead_data.get('company_name'),
                            description=lead_data.get('description'),

                            # Поля для этапа КП
                            proposal_amount=float(lead_data.get('proposal_amount', 0)) if lead_data.get('proposal_amount') else None,
                            proposal_date=proposal_date,

                            # Поля для финального этапа
                            deal_amount=float(lead_data.get('deal_amount', 0)) if lead_data.get('deal_amount') else None,
                            rejection_reason=lead_data.get('rejection_reason'),

                            # Даты и таймеры
                            created_at=created_at or datetime.utcnow(),
                            updated_at=updated_at or datetime.utcnow(),
                            last_activity_at=last_activity_at or datetime.utcnow(),
                            reminder_date=reminder_date,
                            waiting_started_at=waiting_started_at
                        )
                        db.add(new_lead)
                        db.flush()  # Чтобы получить ID новой заявки

                        # Сохраняем соответствие старого и нового ID
                        old_lead_id = lead_data.get('id')
                        if old_lead_id:
                            lead_mapping[old_lead_id] = new_lead.id
                            print(f"Маппинг заявки: {old_lead_id} -> {new_lead.id}")

                        imported_data["leads"] += 1
            except Exception as e:
                print(f"Error importing leads: {e}")
                db.rollback()
                pass

        # Импортируем заметки к заявкам
        if "lead_notes" in available_tables:
            try:
                cursor = source_session.connection().connection.cursor()
                cursor.execute("SELECT * FROM lead_notes")
                rows = cursor.fetchall()

                cursor.execute("PRAGMA table_info(lead_notes)")
                columns = [col[1] for col in cursor.fetchall()]

                for row in rows:
                    note_data = dict(zip(columns, row))

                    # Находим соответствующую заявку через маппинг
                    old_lead_id = note_data.get('lead_id')
                    new_lead_id = lead_mapping.get(old_lead_id, old_lead_id)  # Используем старый ID как fallback

                    lead = db.query(models.Lead).filter(models.Lead.id == new_lead_id).first()
                    if lead:
                        created_at = None
                        if note_data.get('created_at'):
                            try:
                                if isinstance(note_data['created_at'], str):
                                    created_at = datetime.fromisoformat(note_data['created_at'].replace(' ', 'T'))
                                else:
                                    created_at = note_data['created_at']
                            except:
                                created_at = None

                        new_note = models.LeadNote(
                            lead_id=lead.id,
                            user_id=note_data.get('user_id') or note_data.get('created_by_id'),
                            content=note_data.get('content'),
                            lead_status=note_data.get('lead_status'),
                            created_at=created_at or datetime.utcnow()
                        )
                        db.add(new_note)
                        imported_data["lead_notes"] += 1
            except Exception as e:
                print(f"Error importing lead notes: {e}")
                db.rollback()
                pass

        # Импортируем категории расходов
        if "expense_categories" in available_tables:
            try:
                cursor = source_session.connection().connection.cursor()
                cursor.execute("SELECT * FROM expense_categories")
                rows = cursor.fetchall()

                cursor.execute("PRAGMA table_info(expense_categories)")
                columns = [col[1] for col in cursor.fetchall()]

                for row in rows:
                    category_data = dict(zip(columns, row))
                    existing = db.query(models.ExpenseCategory).filter(
                        models.ExpenseCategory.name == category_data.get('name')
                    ).first()

                    if not existing:
                        new_category = models.ExpenseCategory(
                            name=category_data.get('name'),
                            description=category_data.get('description'),
                            is_active=category_data.get('is_active', True)
                        )
                        db.add(new_category)
                        imported_data["expense_categories"] += 1
            except Exception as e:
                print(f"Error importing expense categories: {e}")
                db.rollback()
                pass

        # Импортируем расходы по проектам
        if "project_expenses" in available_tables:
            try:
                cursor = source_session.connection().connection.cursor()
                cursor.execute("SELECT * FROM project_expenses")
                rows = cursor.fetchall()

                cursor.execute("PRAGMA table_info(project_expenses)")
                columns = [col[1] for col in cursor.fetchall()]

                for row in rows:
                    expense_data = dict(zip(columns, row))

                    # Парсим дату
                    date = None
                    if expense_data.get('date'):
                        try:
                            if isinstance(expense_data['date'], str):
                                date = datetime.fromisoformat(expense_data['date'].replace(' ', 'T')).date()
                            else:
                                date = expense_data['date']
                        except:
                            date = None

                    # Находим проект
                    project = db.query(models.Project).filter(models.Project.id == expense_data.get('project_id')).first()
                    if project:
                        new_expense = models.ProjectExpense(
                            project_id=project.id,
                            category_id=expense_data.get('category_id'),
                            name=expense_data.get('name', expense_data.get('description', 'Импортированный расход')),
                            description=expense_data.get('description'),
                            amount=float(expense_data.get('amount', 0)),
                            date=date or datetime.utcnow().date(),
                            created_by=expense_data.get('created_by_id')
                        )
                        db.add(new_expense)
                        imported_data["project_expenses"] += 1
            except Exception as e:
                print(f"Error importing project expenses: {e}")
                db.rollback()
                pass

        # Импортируем общие расходы
        if "common_expenses" in available_tables:
            try:
                cursor = source_session.connection().connection.cursor()
                cursor.execute("SELECT * FROM common_expenses")
                rows = cursor.fetchall()

                cursor.execute("PRAGMA table_info(common_expenses)")
                columns = [col[1] for col in cursor.fetchall()]

                for row in rows:
                    expense_data = dict(zip(columns, row))

                    # Парсим дату
                    date = None
                    if expense_data.get('date'):
                        try:
                            if isinstance(expense_data['date'], str):
                                date = datetime.fromisoformat(expense_data['date'].replace(' ', 'T')).date()
                            else:
                                date = expense_data['date']
                        except:
                            date = None

                    new_expense = models.CommonExpense(
                        category_id=expense_data.get('category_id'),
                        name=expense_data.get('name', expense_data.get('description', 'Импортированный расход')),
                        description=expense_data.get('description'),
                        amount=float(expense_data.get('amount', 0)),
                        date=date or datetime.utcnow().date(),
                        created_by=expense_data.get('created_by_id')
                    )
                    db.add(new_expense)
                    imported_data["common_expenses"] += 1
            except Exception as e:
                print(f"Error importing common expenses: {e}")
                db.rollback()
                pass

        # Импортируем расходы по цифровым проектам
        if "digital_project_expenses" in available_tables:
            try:
                cursor = source_session.connection().connection.cursor()
                cursor.execute("SELECT * FROM digital_project_expenses")
                rows = cursor.fetchall()

                cursor.execute("PRAGMA table_info(digital_project_expenses)")
                columns = [col[1] for col in cursor.fetchall()]

                for row in rows:
                    expense_data = dict(zip(columns, row))

                    # Парсим дату
                    date = None
                    if expense_data.get('date'):
                        try:
                            if isinstance(expense_data['date'], str):
                                date = datetime.fromisoformat(expense_data['date'].replace(' ', 'T')).date()
                            else:
                                date = expense_data['date']
                        except:
                            date = None

                    # Находим цифровой проект
                    digital_project = db.query(models.DigitalProject).filter(
                        models.DigitalProject.id == expense_data.get('digital_project_id')
                    ).first()
                    if digital_project:
                        new_expense = models.DigitalProjectExpense(
                            digital_project_id=digital_project.id,
                            category_id=expense_data.get('category_id'),
                            description=expense_data.get('description'),
                            amount=float(expense_data.get('amount', 0)),
                            date=date or datetime.utcnow().date(),
                            receipt_path=expense_data.get('receipt_path'),
                            notes=expense_data.get('notes')
                        )
                        db.add(new_expense)
                        imported_data["digital_project_expenses"] += 1
            except Exception as e:
                print(f"Error importing digital project expenses: {e}")
                db.rollback()
                pass

        # Импортируем расходы сотрудников
        if "employee_expenses" in available_tables:
            try:
                cursor = source_session.connection().connection.cursor()
                cursor.execute("SELECT * FROM employee_expenses")
                rows = cursor.fetchall()

                cursor.execute("PRAGMA table_info(employee_expenses)")
                columns = [col[1] for col in cursor.fetchall()]

                for row in rows:
                    expense_data = dict(zip(columns, row))

                    # Парсим дату
                    date = None
                    if expense_data.get('date'):
                        try:
                            if isinstance(expense_data['date'], str):
                                date = datetime.fromisoformat(expense_data['date'].replace(' ', 'T')).date()
                            else:
                                date = expense_data['date']
                        except:
                            date = None

                    # Проверяем существование проекта если указан project_id
                    project_id = expense_data.get('project_id')
                    if project_id:
                        # Проверяем есть ли такой проект в целевой БД
                        existing_project = db.query(models.Project).filter(models.Project.id == project_id).first()
                        if not existing_project:
                            # Проект не существует, устанавливаем None
                            print(f"Warning: Project ID {project_id} not found for employee expense, setting to NULL")
                            project_id = None

                    new_expense = models.EmployeeExpense(
                        user_id=expense_data.get('employee_id'),
                        name=expense_data.get('name', expense_data.get('description', 'Импортированный расход')),
                        description=expense_data.get('description'),
                        amount=float(expense_data.get('amount', 0)),
                        date=date or datetime.utcnow().date(),
                        project_id=project_id
                    )
                    db.add(new_expense)
                    imported_data["employee_expenses"] += 1
            except Exception as e:
                print(f"Error importing employee expenses: {e}")
                db.rollback()
                pass

        # Импортируем отчеты по проектам
        if "project_reports" in available_tables:
            try:
                cursor = source_session.connection().connection.cursor()
                cursor.execute("SELECT * FROM project_reports")
                rows = cursor.fetchall()

                cursor.execute("PRAGMA table_info(project_reports)")
                columns = [col[1] for col in cursor.fetchall()]

                for row in rows:
                    report_data = dict(zip(columns, row))

                    # Парсим даты
                    start_date = None
                    end_date = None
                    created_at = None

                    if report_data.get('start_date'):
                        try:
                            if isinstance(report_data['start_date'], str):
                                start_date = datetime.fromisoformat(report_data['start_date'].replace(' ', 'T')).date()
                            else:
                                start_date = report_data['start_date']
                        except:
                            start_date = None

                    if report_data.get('end_date'):
                        try:
                            if isinstance(report_data['end_date'], str):
                                end_date = datetime.fromisoformat(report_data['end_date'].replace(' ', 'T')).date()
                            else:
                                end_date = report_data['end_date']
                        except:
                            end_date = None

                    if report_data.get('created_at'):
                        try:
                            if isinstance(report_data['created_at'], str):
                                created_at = datetime.fromisoformat(report_data['created_at'].replace(' ', 'T'))
                            else:
                                created_at = report_data['created_at']
                        except:
                            created_at = None

                    # Находим проект
                    project = db.query(models.Project).filter(models.Project.id == report_data.get('project_id')).first()
                    if project:
                        # Получаем месяц и год из данных или используем текущие
                        month = report_data.get('month', datetime.utcnow().month)
                        year = report_data.get('year', datetime.utcnow().year)

                        new_report = models.ProjectReport(
                            project_id=project.id,
                            month=month,
                            year=year,
                            contract_amount=int(report_data.get('contract_amount', 0)),
                            receipts=int(report_data.get('receipts', 0))
                        )
                        db.add(new_report)
                        imported_data["project_reports"] += 1
            except Exception as e:
                print(f"Error importing project reports: {e}")
                db.rollback()
                pass

        # Импортируем вложения к заявкам
        if "lead_attachments" in available_tables:
            try:
                cursor = source_session.connection().connection.cursor()
                cursor.execute("SELECT * FROM lead_attachments")
                rows = cursor.fetchall()

                cursor.execute("PRAGMA table_info(lead_attachments)")
                columns = [col[1] for col in cursor.fetchall()]

                for row in rows:
                    attachment_data = dict(zip(columns, row))

                    # Находим соответствующую заявку через маппинг
                    old_lead_id = attachment_data.get('lead_id')
                    new_lead_id = lead_mapping.get(old_lead_id, old_lead_id)  # Используем старый ID как fallback

                    lead = db.query(models.Lead).filter(models.Lead.id == new_lead_id).first()
                    if lead:
                        uploaded_at = None
                        if attachment_data.get('uploaded_at'):
                            try:
                                if isinstance(attachment_data['uploaded_at'], str):
                                    uploaded_at = datetime.fromisoformat(attachment_data['uploaded_at'].replace(' ', 'T'))
                                else:
                                    uploaded_at = attachment_data['uploaded_at']
                            except:
                                uploaded_at = None

                        new_attachment = models.LeadAttachment(
                            lead_id=lead.id,
                            filename=attachment_data.get('filename'),
                            file_path=attachment_data.get('file_path'),
                            file_size=attachment_data.get('file_size'),
                            mime_type=attachment_data.get('mime_type'),
                            uploaded_at=uploaded_at or datetime.utcnow(),
                            user_id=attachment_data.get('user_id')
                        )
                        db.add(new_attachment)
                        imported_data["lead_attachments"] += 1
            except Exception as e:
                print(f"Error importing lead attachments: {e}")
                db.rollback()
                pass

        # Импортируем историю заявок
        if "lead_history" in available_tables:
            try:
                cursor = source_session.connection().connection.cursor()
                cursor.execute("SELECT * FROM lead_history")
                rows = cursor.fetchall()

                cursor.execute("PRAGMA table_info(lead_history)")
                columns = [col[1] for col in cursor.fetchall()]

                for row in rows:
                    history_data = dict(zip(columns, row))

                    # Находим соответствующую заявку через маппинг
                    old_lead_id = history_data.get('lead_id')
                    new_lead_id = lead_mapping.get(old_lead_id, old_lead_id)  # Используем старый ID как fallback

                    lead = db.query(models.Lead).filter(models.Lead.id == new_lead_id).first()
                    if lead:
                        changed_at = None
                        if history_data.get('changed_at'):
                            try:
                                if isinstance(history_data['changed_at'], str):
                                    changed_at = datetime.fromisoformat(history_data['changed_at'].replace(' ', 'T'))
                                else:
                                    changed_at = history_data['changed_at']
                            except:
                                changed_at = None

                        new_history = models.LeadHistory(
                            lead_id=lead.id,
                            user_id=history_data.get('user_id') or history_data.get('changed_by_id'),
                            action=history_data.get('action') or history_data.get('field_name') or 'status_changed',
                            old_value=history_data.get('old_value'),
                            new_value=history_data.get('new_value'),
                            description=history_data.get('description'),
                            created_at=changed_at or datetime.utcnow()
                        )
                        db.add(new_history)
                        imported_data["lead_history"] += 1
            except Exception as e:
                print(f"Error importing lead history: {e}")
                db.rollback()
                pass

        # Сохраняем изменения
        db.commit()

        # Закрываем сессию источника
        source_session.close()

        # Подсчитываем повторяющиеся задачи
        recurring_tasks_count = db.query(models.Task).filter(models.Task.is_recurring == True).count()
        print(f"📋 Всего повторяющихся задач в БД: {recurring_tasks_count}")

        # Update database version after successful import
        import_status["message"] = "Обновление версии базы данных..."
        import_status["progress"] = 95

        try:
            # Create or update database version record
            version_timestamp = datetime.utcnow().isoformat()
            version_record = db.query(models.DatabaseVersion).first()
            if version_record:
                version_record.version = version_timestamp
                version_record.description = "Database imported"
            else:
                version_record = models.DatabaseVersion(
                    version=version_timestamp,
                    description="Database imported"
                )
                db.add(version_record)
            db.commit()
            print(f"🔄 Database version updated to: {version_timestamp}")
        except Exception as e:
            print(f"Warning: Could not update database version: {e}")
            version_timestamp = datetime.utcnow().isoformat()

        # Обновляем глобальный статус
        import_status["message"] = "Импорт завершен успешно!"
        import_status["progress"] = 100
        import_status["imported_data"] = imported_data

        print(f"✅ Импорт завершен успешно! Импортировано: {imported_data}")

    except Exception as e:
        print(f"Import database error: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        import_status["error"] = str(e)
        import_status["message"] = f"Ошибка: {str(e)}"
        raise
    finally:
        # Закрываем источник сессии если она была создана
        if 'source_session' in locals():
            source_session.close()
        # Удаляем временный файл БД
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)
        # Удаляем загруженный файл
        if tmp_upload_path and os.path.exists(tmp_upload_path):
            os.remove(tmp_upload_path)
        # Удаляем временную папку если была создана
        if tmp_dir and os.path.exists(tmp_dir):
            shutil.rmtree(tmp_dir)
        # Восстанавливаем рабочую директорию
        os.chdir(original_cwd)
        print(f"Импорт: восстановлена рабочая директория: {os.getcwd()}")


# Database version endpoint (public, no auth required)
@app.get("/database/version")
async def get_database_version(db: Session = Depends(auth.get_db)):
    """Get current database version for cache invalidation"""
    try:
        version_record = db.query(models.DatabaseVersion).first()
        if version_record:
            return {
                "version": version_record.version,
                "updated_at": version_record.updated_at.isoformat() if version_record.updated_at else None,
                "description": version_record.description
            }
        else:
            # If no version record exists, create one
            initial_version = datetime.utcnow().isoformat()
            version_record = models.DatabaseVersion(
                version=initial_version,
                description="Initial version"
            )
            db.add(version_record)
            db.commit()
            return {
                "version": initial_version,
                "updated_at": None,
                "description": "Initial version"
            }
    except Exception as e:
        print(f"Error getting database version: {e}")
        # Return a fallback version based on current time
        return {
            "version": datetime.utcnow().isoformat(),
            "updated_at": None,
            "description": "Fallback version"
        }


@app.get("/admin/export-database")
async def export_database(
    db: Session = Depends(auth.get_db),
    current: models.User = Depends(auth.get_current_active_user),
):
    """Экспорт текущей базы данных с файлами"""
    if current.role != models.RoleEnum.admin:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    import datetime
    import sqlite3
    import tempfile
    import zipfile
    import glob

    # Создаем временные файлы для экспорта
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    temp_dir = tempfile.gettempdir()
    export_db_path = os.path.join(temp_dir, f"database_export_{timestamp}.db")
    export_zip_path = os.path.join(temp_dir, f"database_export_{timestamp}.zip")

    # Сохраняем текущую рабочую директорию и переходим в agency_backend
    original_cwd = os.getcwd()

    # Определяем папку agency_backend
    app_dir = os.path.dirname(os.path.abspath(__file__))  # Папка app
    backend_dir = os.path.dirname(app_dir)  # Папка agency_backend

    print(f"Текущая директория: {original_cwd}")
    print(f"Переходим в: {backend_dir}")
    os.chdir(backend_dir)

    try:
        # Путь к текущей БД
        source_db_url = str(db.bind.url).replace('sqlite:///', '')

        if not os.path.exists(source_db_url):
            raise HTTPException(status_code=404, detail="Database file not found")

        # Подключаемся к текущей БД
        source_conn = sqlite3.connect(source_db_url)

        # Создаем новую БД для экспорта
        export_conn = sqlite3.connect(export_db_path)

        # Экспортируем схему и данные всех таблиц
        print(f"Начинаем экспорт базы данных в {export_db_path}")

        # Получаем список всех таблиц
        tables_query = source_conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in tables_query.fetchall()]

        print(f"Найдено таблиц для экспорта: {len(tables)}")
        print(f"Таблицы: {tables}")

        # Экспортируем каждую таблицу
        for table_name in tables:
            if table_name.startswith('sqlite_'):
                continue  # Пропускаем системные таблицы

            print(f"Экспортируем таблицу: {table_name}")

            # Получаем схему таблицы
            schema_query = source_conn.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{table_name}'")
            schema = schema_query.fetchone()

            if schema and schema[0]:
                # Создаем таблицу в новой БД
                export_conn.execute(schema[0])

                # Копируем данные
                data_query = source_conn.execute(f"SELECT * FROM {table_name}")
                rows = data_query.fetchall()

                if rows:
                    # Получаем информацию о столбцах
                    columns_info = source_conn.execute(f"PRAGMA table_info({table_name})")
                    columns = [col[1] for col in columns_info.fetchall()]

                    # Формируем запрос для вставки
                    placeholders = ','.join(['?' for _ in columns])
                    insert_query = f"INSERT INTO {table_name} VALUES ({placeholders})"

                    # Вставляем данные
                    export_conn.executemany(insert_query, rows)
                    print(f"Скопировано {len(rows)} строк в таблицу {table_name}")
                else:
                    print(f"Таблица {table_name} пуста")

        # Сохраняем изменения
        export_conn.commit()

        # Закрываем соединения
        source_conn.close()
        export_conn.close()

        print(f"Экспорт базы данных завершен: {export_db_path}")

        # Создаем ZIP архив с БД и файлами
        print("Создаем ZIP архив с файлами...")
        with zipfile.ZipFile(export_zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Добавляем базу данных
            zipf.write(export_db_path, f"database_{timestamp}.db")
            print("База данных добавлена в архив")

            # Определяем папки с файлами для экспорта
            file_directories = [
                "uploads/leads",      # CRM файлы заявок
                "static/projects",    # логотипы проектов
                "static/digital",     # логотипы digital проектов
                "files",              # ресурсные файлы
                "contracts"           # контракты пользователей
            ]

            total_files = 0
            for dir_path in file_directories:
                if os.path.exists(dir_path):
                    print(f"Архивируем папку: {dir_path}")
                    for root, dirs, files in os.walk(dir_path):
                        for file in files:
                            file_path = os.path.join(root, file)
                            # Сохраняем относительный путь в архиве
                            arcname = os.path.relpath(file_path, '.')
                            zipf.write(file_path, arcname)
                            total_files += 1
                    files_in_dir = 0
                    for root, dirs, files in os.walk(dir_path):
                        files_in_dir += len(files)
                    print(f"Папка {dir_path}: добавлено {files_in_dir} файлов")
                else:
                    print(f"Папка {dir_path} не существует, пропускаем")

            print(f"Всего файлов добавлено в архив: {total_files}")

        # Удаляем временную БД
        if os.path.exists(export_db_path):
            os.remove(export_db_path)

        print(f"Экспорт завершен успешно: {export_zip_path}")

        filename = f"database_export_{timestamp}.zip"

        return FileResponse(
            path=export_zip_path,
            filename=filename,
            media_type='application/zip'
        )

    except Exception as e:
        print(f"Ошибка при экспорте базы данных: {e}")
        # Очищаем временные файлы при ошибке
        for temp_file in [export_db_path, export_zip_path]:
            if os.path.exists(temp_file):
                os.remove(temp_file)
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")
    finally:
        # Восстанавливаем рабочую директорию
        os.chdir(original_cwd)
        print(f"Восстановлена рабочая директория: {os.getcwd()}")


@app.post("/admin/clear-cache")
async def clear_global_cache(
    db: Session = Depends(auth.get_db),
    current: models.User = Depends(auth.get_current_active_user),
):
    """Глобальная очистка кеша и временных файлов (только для администраторов)"""
    if current.role != models.RoleEnum.admin:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    import os
    import tempfile
    import shutil
    import time

    cleared_items = []
    total_space_freed = 0

    try:
        # 1. Очистка системного временного каталога
        temp_dir = tempfile.gettempdir()
        temp_files_count = 0
        temp_space_freed = 0

        for filename in os.listdir(temp_dir):
            if filename.startswith('tmp') or filename.startswith('temp'):
                file_path = os.path.join(temp_dir, filename)
                try:
                    if os.path.isfile(file_path):
                        size = os.path.getsize(file_path)
                        os.remove(file_path)
                        temp_files_count += 1
                        temp_space_freed += size
                    elif os.path.isdir(file_path):
                        size = sum(os.path.getsize(os.path.join(dirpath, filename))
                                 for dirpath, dirnames, filenames in os.walk(file_path)
                                 for filename in filenames)
                        shutil.rmtree(file_path)
                        temp_files_count += 1
                        temp_space_freed += size
                except (PermissionError, FileNotFoundError):
                    pass

        if temp_files_count > 0:
            cleared_items.append(f"Временные файлы: {temp_files_count} файлов ({temp_space_freed / 1024 / 1024:.2f} МБ)")
            total_space_freed += temp_space_freed

        # 2. Очистка старых ZIP архивов экспорта (старше 24 часов)
        export_files_count = 0
        export_space_freed = 0

        current_dir = os.path.dirname(os.path.abspath(__file__))

        for filename in os.listdir(current_dir):
            if filename.endswith('.zip') and ('export' in filename.lower() or 'backup' in filename.lower()):
                file_path = os.path.join(current_dir, filename)
                try:
                    # Проверяем возраст файла
                    file_age = time.time() - os.path.getmtime(file_path)
                    if file_age > 86400:  # 24 часа
                        size = os.path.getsize(file_path)
                        os.remove(file_path)
                        export_files_count += 1
                        export_space_freed += size
                except (PermissionError, FileNotFoundError):
                    pass

        if export_files_count > 0:
            cleared_items.append(f"Старые архивы: {export_files_count} файлов ({export_space_freed / 1024 / 1024:.2f} МБ)")
            total_space_freed += export_space_freed

        # 3. Очистка логов и кеша приложения (если есть)
        log_files_count = 0
        log_space_freed = 0

        for log_pattern in ['*.log', '*.log.*', '__pycache__']:
            if log_pattern == '__pycache__':
                # Очистка Python кеша
                for root, dirs, files in os.walk(current_dir):
                    if '__pycache__' in dirs:
                        cache_dir = os.path.join(root, '__pycache__')
                        try:
                            size = sum(os.path.getsize(os.path.join(dirpath, filename))
                                     for dirpath, dirnames, filenames in os.walk(cache_dir)
                                     for filename in filenames)
                            shutil.rmtree(cache_dir)
                            log_files_count += 1
                            log_space_freed += size
                        except (PermissionError, FileNotFoundError):
                            pass
            else:
                # Очистка лог файлов
                import glob
                for log_file in glob.glob(os.path.join(current_dir, log_pattern)):
                    try:
                        size = os.path.getsize(log_file)
                        os.remove(log_file)
                        log_files_count += 1
                        log_space_freed += size
                    except (PermissionError, FileNotFoundError):
                        pass

        if log_files_count > 0:
            cleared_items.append(f"Логи и кеш: {log_files_count} элементов ({log_space_freed / 1024 / 1024:.2f} МБ)")
            total_space_freed += log_space_freed

        # 4. Очистка неиспользуемых uploads (файлы без записей в БД)
        uploads_cleaned = 0
        uploads_space_freed = 0

        uploads_dir = os.path.join(current_dir, 'uploads')
        if os.path.exists(uploads_dir):
            for root, dirs, files in os.walk(uploads_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    relative_path = os.path.relpath(file_path, uploads_dir)

                    # Проверяем, есть ли файл в базе данных
                    file_in_db = db.query(models.ResourceFile).filter(
                        models.ResourceFile.file_path.like(f"%{file}")
                    ).first()

                    lead_attachment = db.query(models.LeadAttachment).filter(
                        models.LeadAttachment.file_path.like(f"%{file}")
                    ).first()

                    if not file_in_db and not lead_attachment:
                        try:
                            # Файл не найден в БД, можно удалить
                            file_age = time.time() - os.path.getmtime(file_path)
                            if file_age > 7200:  # Старше 2 часов
                                size = os.path.getsize(file_path)
                                os.remove(file_path)
                                uploads_cleaned += 1
                                uploads_space_freed += size
                        except (PermissionError, FileNotFoundError):
                            pass

        if uploads_cleaned > 0:
            cleared_items.append(f"Неиспользуемые файлы: {uploads_cleaned} файлов ({uploads_space_freed / 1024 / 1024:.2f} МБ)")
            total_space_freed += uploads_space_freed

        if not cleared_items:
            cleared_items.append("Кеш уже чист - ненужных файлов не найдено")

        message = "Кеш успешно очищен!\n" + "\n".join(cleared_items)
        if total_space_freed > 0:
            message += f"\n\nВсего освобождено: {total_space_freed / 1024 / 1024:.2f} МБ"

        return {
            "message": message,
            "timestamp": datetime.now(),
            "cleared_by": current.name,
            "space_freed_mb": round(total_space_freed / 1024 / 1024, 2),
            "items_cleared": cleared_items
        }

    except Exception as e:
        print(f"Error during cache clearing: {e}")
        return {
            "message": f"Частичная очистка кеша выполнена. Ошибка: {str(e)}",
            "timestamp": datetime.now(),
            "cleared_by": current.name,
            "space_freed_mb": round(total_space_freed / 1024 / 1024, 2) if total_space_freed > 0 else 0,
            "items_cleared": cleared_items if cleared_items else ["Очистка прервана из-за ошибки"]
        }

@app.delete("/admin/clear-database")
async def clear_database(
    db: Session = Depends(auth.get_db),
    current: models.User = Depends(auth.get_current_active_user),
):
    """Полная очистка базы данных (кроме текущего админа)"""
    if current.role != models.RoleEnum.admin:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    # Счетчики для отчета
    deleted_counts = {}

    def safe_delete(entity_name, delete_func):
        """Безопасное удаление с обработкой ошибок"""
        try:
            count = delete_func()
            db.commit()  # Коммитим каждую операцию отдельно
            deleted_counts[entity_name] = count
            return count
        except Exception as e:
            db.rollback()
            print(f"Error deleting {entity_name}: {e}")
            deleted_counts[entity_name] = 0
            return 0

    try:
        # Удаляем задачи
        safe_delete("tasks", lambda: db.query(models.Task).delete() if hasattr(models, 'Task') else 0)

        # Удаляем посты проектов
        safe_delete("posts", lambda: db.query(models.ProjectPost).delete() if hasattr(models, 'ProjectPost') else 0)

        # Удаляем съемки
        safe_delete("shootings", lambda: db.query(models.Shooting).delete() if hasattr(models, 'Shooting') else 0)

        # Удаляем все типы расходов
        safe_delete("project_expenses", lambda: db.query(models.ProjectExpense).delete() if hasattr(models, 'ProjectExpense') else 0)
        safe_delete("project_client_expenses", lambda: db.query(models.ProjectClientExpense).delete() if hasattr(models, 'ProjectClientExpense') else 0)
        safe_delete("employee_expenses", lambda: db.query(models.EmployeeExpense).delete() if hasattr(models, 'EmployeeExpense') else 0)
        safe_delete("digital_project_expenses", lambda: db.query(models.DigitalProjectExpense).delete() if hasattr(models, 'DigitalProjectExpense') else 0)

        # Удаляем поступления
        safe_delete("receipts", lambda: db.query(models.ProjectReceipt).delete() if hasattr(models, 'ProjectReceipt') else 0)

        # Удаляем отчеты по проектам
        safe_delete("project_reports", lambda: db.query(models.ProjectReport).delete() if hasattr(models, 'ProjectReport') else 0)

        # Удаляем цифровые проекты и связанные данные
        safe_delete("digital_project_tasks", lambda: db.query(models.DigitalProjectTask).delete() if hasattr(models, 'DigitalProjectTask') else 0)
        safe_delete("digital_project_finance", lambda: db.query(models.DigitalProjectFinance).delete() if hasattr(models, 'DigitalProjectFinance') else 0)
        safe_delete("digital_projects", lambda: db.query(models.DigitalProject).delete() if hasattr(models, 'DigitalProject') else 0)
        safe_delete("digital_services", lambda: db.query(models.DigitalService).delete() if hasattr(models, 'DigitalService') else 0)

        # Удаляем проекты
        safe_delete("projects", lambda: db.query(models.Project).delete() if hasattr(models, 'Project') else 0)

        # Удаляем операторов
        safe_delete("operators", lambda: db.query(models.Operator).delete() if hasattr(models, 'Operator') else 0)

        # Удаляем заявки и связанные данные
        safe_delete("lead_history", lambda: db.execute(text("DELETE FROM lead_history")).rowcount)
        safe_delete("lead_attachments", lambda: db.execute(text("DELETE FROM lead_attachments")).rowcount)
        safe_delete("lead_notes", lambda: db.execute(text("DELETE FROM lead_notes")).rowcount)
        safe_delete("leads", lambda: db.execute(text("DELETE FROM leads")).rowcount)

        # Удаляем повторяющиеся задачи
        safe_delete("recurring_tasks", lambda: db.execute(text("DELETE FROM recurring_tasks")).rowcount)

        # Удаляем всех пользователей кроме текущего админа
        safe_delete("users", lambda: db.query(models.User).filter(models.User.id != current.id).delete() if hasattr(models, 'User') else 0)

        # Удаляем настройки (кроме timezone)
        safe_delete("settings", lambda: db.query(models.Setting).filter(models.Setting.key.notin_(["timezone"])).delete() if hasattr(models, 'Setting') else 0)

        # Очищаем все папки с файлами
        file_directories = [
            "uploads/leads",
            "static/projects",
            "static/digital",
            "files",
            "contracts"
        ]

        cleared_files = 0
        for dir_path in file_directories:
            if os.path.exists(dir_path):
                try:
                    for root, dirs, files in os.walk(dir_path):
                        for file_name in files:
                            file_path = os.path.join(root, file_name)
                            try:
                                os.remove(file_path)
                                cleared_files += 1
                            except:
                                pass
                except:
                    pass

        deleted_counts["files"] = cleared_files

        # Удаляем налоги
        safe_delete("taxes", lambda: db.query(models.Tax).delete() if hasattr(models, 'Tax') else 0)

        # Пересоздаем дефолтные налоги в отдельной транзакции
        try:
            if hasattr(crud, 'create_tax'):
                crud.create_tax(db, "ЯТТ", 0.95)
                crud.create_tax(db, "ООО", 0.83)
                crud.create_tax(db, "Нал", 1.0)
                db.commit()
        except Exception as e:
            db.rollback()
            print(f"Error creating default taxes: {e}")

        return {
            "success": True,
            "message": "Database cleared successfully (some operations may have failed)",
            "deleted": deleted_counts
        }

    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"[ERROR] Clear database failed: {error_details}")
        return {
            "success": False,
            "message": f"Clear failed: {str(e)}",
            "deleted": deleted_counts
        }

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
    all_users: bool = Query(False, description="Get expenses for all users (admin only)"),
    db: Session = Depends(auth.get_db),
    current: models.User = Depends(auth.get_current_active_user)
):
    """Get employee expenses with filters"""
    print(f"[DEBUG /employee-expenses] user_id={user_id}, start_date={start_date}, end_date={end_date}, all_users={all_users}")
    from sqlalchemy.orm import joinedload

    query = db.query(models.EmployeeExpense).options(
        joinedload(models.EmployeeExpense.project),
        joinedload(models.EmployeeExpense.user)
    )

    if user_id:
        query = query.filter(models.EmployeeExpense.user_id == user_id)
    elif all_users and current.role == models.RoleEnum.admin:
        # Admin can request all users' expenses for reports
        pass
    else:
        # Always show only current user's own expenses when user_id is not specified
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


# ========== PROJECT EXPENSES SUMMARY ==========
@app.get("/expense-reports/projects")
def get_project_expenses_summary(
    project_id: Optional[int] = Query(None, description="Filter by project ID"),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    db: Session = Depends(auth.get_db),
    current: models.User = Depends(auth.get_current_active_user)
):
    """Get project expenses summary including all types of expenses per project"""
    print(f"[DEBUG /expense-reports/projects] project_id={project_id}, start_date={start_date}, end_date={end_date}")
    return crud.get_project_expenses_summary(db, project_id, start_date, end_date)


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


# ========== SETTINGS ENDPOINTS ==========
@app.get("/api/settings/{key}")
async def get_setting(key: str, db: Session = Depends(get_db)):
    """Получить настройку"""
    setting = db.query(models.Setting).filter(models.Setting.key == key).first()
    if not setting:
        raise HTTPException(status_code=404, detail="Setting not found")
    return {"key": setting.key, "value": setting.value}

@app.put("/api/settings/{key}")
async def update_setting(key: str, value: str = Form(...), db: Session = Depends(get_db)):
    """Обновить настройку"""
    setting = db.query(models.Setting).filter(models.Setting.key == key).first()
    if not setting:
        setting = models.Setting(key=key, value=value)
        db.add(setting)
    else:
        setting.value = value
    db.commit()
    return {"key": key, "value": value}

@app.get("/api/settings")
async def get_all_settings(db: Session = Depends(get_db)):
    """Получить все настройки"""
    settings = db.query(models.Setting).all()
    return {setting.key: setting.value for setting in settings}


# ========== RECURRING TASKS SETTINGS ==========
# Удалено: глобальная настройка времени генерации
# Время генерации теперь устанавливается индивидуально для каждой задачи


# =============================================================================
# Канбан-доска заявок (CRM)
# =============================================================================

@app.get("/leads/", response_model=List[schemas.Lead])
def get_leads(
    skip: int = 0,
    limit: int = 100,
    manager_id: Optional[int] = None,
    status: Optional[str] = None,
    source: Optional[str] = None,
    created_from: Optional[str] = None,
    created_to: Optional[str] = None,
    db: Session = Depends(auth.get_db),
    current: models.User = Depends(auth.get_current_user)
):
    """Получить список заявок с фильтрацией"""
    leads = crud.get_leads(
        db=db,
        skip=skip,
        limit=limit,
        manager_id=manager_id,
        status=status,
        source=source,
        created_from=created_from,
        created_to=created_to
    )
    return leads


@app.post("/leads/", response_model=schemas.Lead)
def create_lead(
    lead: schemas.LeadCreate,
    db: Session = Depends(auth.get_db),
    current: models.User = Depends(auth.get_current_user)
):
    """Создать новую заявку"""
    # Если менеджер не указан, назначаем текущего пользователя
    if not lead.manager_id:
        lead.manager_id = current.id
    
    db_lead = crud.create_lead(db=db, lead=lead, creator_id=current.id)
    return db_lead


@app.get("/leads/{lead_id}", response_model=schemas.Lead)
def get_lead(
    lead_id: int,
    db: Session = Depends(auth.get_db),
    current: models.User = Depends(auth.get_current_user)
):
    """Получить заявку по ID"""
    lead = crud.get_lead(db, lead_id=lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead


@app.put("/leads/{lead_id}", response_model=schemas.Lead)
def update_lead(
    lead_id: int,
    lead_update: schemas.LeadUpdate,
    db: Session = Depends(auth.get_db),
    current: models.User = Depends(auth.get_current_user)
):
    """Обновить заявку"""
    lead = crud.update_lead(db=db, lead_id=lead_id, lead_update=lead_update, user_id=current.id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead


@app.delete("/leads/{lead_id}")
def delete_lead(
    lead_id: int,
    db: Session = Depends(auth.get_db),
    current: models.User = Depends(auth.get_current_admin_user)
):
    """Удалить заявку (только админы)"""
    success = crud.delete_lead(db=db, lead_id=lead_id)
    if not success:
        raise HTTPException(status_code=404, detail="Lead not found")
    return {"message": "Lead deleted successfully"}


# Заметки к заявкам
@app.get("/leads/{lead_id}/notes/", response_model=List[schemas.LeadNote])
def get_lead_notes(
    lead_id: int,
    db: Session = Depends(auth.get_db),
    current: models.User = Depends(auth.get_current_user)
):
    """Получить список заметок к заявке"""
    notes = db.query(models.LeadNote).filter(models.LeadNote.lead_id == lead_id).options(
        joinedload(models.LeadNote.user)
    ).order_by(models.LeadNote.created_at.desc()).all()
    return notes


@app.post("/leads/{lead_id}/notes/", response_model=schemas.LeadNote)
def add_lead_note(
    lead_id: int,
    note: schemas.LeadNoteCreate,
    db: Session = Depends(auth.get_db),
    current: models.User = Depends(auth.get_current_user)
):
    """Добавить заметку к заявке"""
    db_note = crud.create_lead_note(db=db, lead_id=lead_id, note=note, user_id=current.id)
    return db_note


@app.delete("/leads/notes/{note_id}")
def delete_lead_note(
    note_id: int,
    db: Session = Depends(auth.get_db),
    current: models.User = Depends(auth.get_current_user)
):
    """Удалить заметку"""
    success = crud.delete_lead_note(db=db, note_id=note_id, user_id=current.id)
    if not success:
        raise HTTPException(status_code=404, detail="Note not found or access denied")
    return {"message": "Note deleted successfully"}


# Файлы к заявкам
@app.post("/leads/{lead_id}/attachments/")
def upload_lead_attachment(
    lead_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(auth.get_db),
    current: models.User = Depends(auth.get_current_user)
):
    """Загрузить файл к заявке"""
    # Проверяем существование заявки
    lead = crud.get_lead(db, lead_id=lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    # Создаем папку для файлов заявок
    upload_dir = "uploads/leads"
    os.makedirs(upload_dir, exist_ok=True)
    
    # Генерируем уникальное имя файла
    file_extension = os.path.splitext(file.filename)[1] if file.filename else ""
    safe_filename = f"lead_{lead_id}_{int(time.time())}{file_extension}"
    file_path = os.path.join(upload_dir, safe_filename)
    
    # Сохраняем файл
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Создаем запись в базе данных
    attachment_data = {
        "filename": file.filename or safe_filename,
        "file_path": file_path,
        "file_size": os.path.getsize(file_path),
        "mime_type": file.content_type
    }
    
    db_attachment = crud.create_lead_attachment(
        db=db,
        lead_id=lead_id,
        attachment=attachment_data,
        user_id=current.id
    )
    
    return db_attachment


@app.get("/leads/attachments/{attachment_id}/download")
def download_lead_attachment(
    attachment_id: int,
    db: Session = Depends(auth.get_db),
    current: models.User = Depends(auth.get_current_user)
):
    """Скачать файл заявки"""
    attachment = crud.get_lead_attachment(db, attachment_id=attachment_id)
    if not attachment:
        raise HTTPException(status_code=404, detail="Attachment not found")
    
    if not os.path.exists(attachment.file_path):
        raise HTTPException(status_code=404, detail="File not found on disk")
    
    return FileResponse(
        path=attachment.file_path,
        filename=attachment.filename,
        media_type=attachment.mime_type or 'application/octet-stream'
    )


@app.delete("/leads/attachments/{attachment_id}")
def delete_lead_attachment(
    attachment_id: int,
    db: Session = Depends(auth.get_db),
    current: models.User = Depends(auth.get_current_user)
):
    """Удалить файл заявки"""
    success = crud.delete_lead_attachment(db=db, attachment_id=attachment_id, user_id=current.id)
    if not success:
        raise HTTPException(status_code=404, detail="Attachment not found or access denied")
    return {"message": "Attachment deleted successfully"}


# Аналитика канбан-доски
@app.get("/leads/analytics/", response_model=schemas.LeadAnalytics)
def get_leads_analytics(
    db: Session = Depends(auth.get_db),
    current: models.User = Depends(auth.get_current_user)
):
    """Получить аналитику по заявкам"""
    analytics = crud.get_leads_analytics(db=db)
    return analytics


@app.get("/analytics/service-types", response_model=schemas.ServiceTypesAnalytics)
def get_service_types_analytics(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    employee_id: Optional[int] = None,
    db: Session = Depends(auth.get_db),
    current: models.User = Depends(auth.get_current_user)
):
    """Получить аналитику по типам услуг для сотрудников"""
    analytics = crud.get_service_types_analytics(
        db=db,
        start_date=start_date,
        end_date=end_date,
        employee_id=employee_id
    )
    return analytics


@app.get("/analytics/recurring-tasks")
def get_recurring_tasks_analytics(
    time_range: str = "30d",
    employee_id: Optional[int] = None,
    db: Session = Depends(auth.get_db),
    current: models.User = Depends(auth.get_current_active_user),
):
    """Получение аналитики по повторяющимся задачам"""
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

    # Базовый фильтр для повторяющихся задач (только экземпляры)
    base_filter = and_(
        models.Task.original_task_id.isnot(None),
        models.Task.created_at >= start_date,
        models.Task.created_at <= end_date
    )

    # Дополнительный фильтр по сотруднику
    if employee_id:
        base_filter = and_(base_filter, models.Task.executor_id == employee_id)

    # Статистика повторяющихся задач
    total_recurring_instances = db.query(models.Task).filter(base_filter).count()
    completed_recurring = db.query(models.Task).filter(
        and_(base_filter, models.Task.status == "done")
    ).count()
    in_progress_recurring = db.query(models.Task).filter(
        and_(base_filter, models.Task.status == "in_progress")
    ).count()

    # Статистика по типам задач среди повторяющихся
    task_types_stats = db.query(
        models.Task.task_type,
        func.count(models.Task.id).label('count')
    ).filter(base_filter).group_by(models.Task.task_type).all()

    # Статистика по исполнителям
    executor_stats = db.query(
        models.User.name,
        func.count(models.Task.id).label('total_tasks'),
        func.sum(func.case((models.Task.status == 'done', 1), else_=0)).label('completed_tasks')
    ).join(models.Task, models.Task.executor_id == models.User.id)\
     .filter(base_filter)\
     .group_by(models.User.id, models.User.name).all()

    # Количество активных повторяющихся шаблонов
    active_templates = db.query(models.Task).filter(
        models.Task.is_recurring == True,
        models.Task.next_run_at.isnot(None)
    ).count()

    return {
        "total_recurring_instances": total_recurring_instances,
        "completed_recurring": completed_recurring,
        "in_progress_recurring": in_progress_recurring,
        "active_templates": active_templates,
        "task_types": [{"type": stat.task_type, "count": stat.count} for stat in task_types_stats if stat.task_type],
        "executors": [
            {
                "name": stat.name,
                "total_tasks": stat.total_tasks,
                "completed_tasks": stat.completed_tasks,
                "completion_rate": round((stat.completed_tasks / stat.total_tasks * 100) if stat.total_tasks > 0 else 0, 1)
            } for stat in executor_stats
        ]
    }


# =============================================================================
# Интерактивная доска (Whiteboard)
# =============================================================================

@app.get("/whiteboard/projects/", response_model=List[schemas.WhiteboardProject])
def get_whiteboard_projects(
    db: Session = Depends(auth.get_db),
    current: models.User = Depends(auth.get_current_user)
):
    """Получить проекты интерактивной доски, доступные пользователю"""
    projects = crud.get_user_accessible_whiteboard_projects(
        db=db, 
        user_id=current.id, 
        user_role=current.role
    )
    return projects


@app.get("/whiteboard/projects/{project_id}", response_model=schemas.WhiteboardProject)
def get_whiteboard_project(
    project_id: int,
    db: Session = Depends(auth.get_db),
    current: models.User = Depends(auth.get_current_user)
):
    """Получить конкретный проект интерактивной доски"""
    # Проверяем права доступа
    if not crud.check_user_whiteboard_permission(db, project_id, current.id, "view"):
        raise HTTPException(status_code=403, detail="Нет доступа к этому проекту")
    
    project = crud.get_whiteboard_project(db, project_id=project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Проект не найден")
    
    return project


@app.post("/whiteboard/projects/", response_model=schemas.WhiteboardProject)
def create_whiteboard_project(
    project: schemas.WhiteboardProjectCreate,
    db: Session = Depends(auth.get_db),
    current: models.User = Depends(auth.get_current_user)
):
    """Создать новый проект интерактивной доски"""
    # Проверяем, что все указанные пользователи существуют
    for permission in project.permissions:
        user = db.query(models.User).filter(models.User.id == permission.user_id).first()
        if not user:
            raise HTTPException(
                status_code=404, 
                detail=f"Пользователь с ID {permission.user_id} не найден"
            )
    
    db_project = crud.create_whiteboard_project(
        db=db, 
        project=project, 
        creator_id=current.id, 
        creator_role=current.role
    )
    return db_project


@app.put("/whiteboard/projects/{project_id}", response_model=schemas.WhiteboardProject)
def update_whiteboard_project(
    project_id: int,
    project_update: schemas.WhiteboardProjectUpdate,
    db: Session = Depends(auth.get_db),
    current: models.User = Depends(auth.get_current_user)
):
    """Обновить проект интерактивной доски"""
    # Проверяем права на управление
    if not crud.check_user_whiteboard_permission(db, project_id, current.id, "manage"):
        raise HTTPException(status_code=403, detail="Нет прав на управление этим проектом")
    
    project = crud.update_whiteboard_project(db, project_id=project_id, project_update=project_update)
    if not project:
        raise HTTPException(status_code=404, detail="Проект не найден")
    
    return project


@app.get("/whiteboard/projects/{project_id}/boards/{board_id}", response_model=schemas.WhiteboardBoard)
def get_whiteboard_board(
    project_id: int,
    board_id: int,
    db: Session = Depends(auth.get_db),
    current: models.User = Depends(auth.get_current_user)
):
    """Получить доску проекта"""
    # Проверяем права доступа к проекту
    if not crud.check_user_whiteboard_permission(db, project_id, current.id, "view"):
        raise HTTPException(status_code=403, detail="Нет доступа к этому проекту")
    
    board = crud.get_whiteboard_board(db, board_id=board_id)
    if not board or board.project_id != project_id:
        raise HTTPException(status_code=404, detail="Доска не найдена")
    
    return board


@app.put("/whiteboard/projects/{project_id}/boards/{board_id}/data")
def update_whiteboard_board_data(
    project_id: int,
    board_id: int,
    data: str = Body(..., embed=True),
    db: Session = Depends(auth.get_db),
    current: models.User = Depends(auth.get_current_user)
):
    """Обновить данные доски"""
    # Проверяем права на редактирование
    if not crud.check_user_whiteboard_permission(db, project_id, current.id, "edit"):
        raise HTTPException(status_code=403, detail="Нет прав на редактирование этого проекта")
    
    board = crud.update_whiteboard_board_data(db, board_id=board_id, data=data)
    if not board or board.project_id != project_id:
        raise HTTPException(status_code=404, detail="Доска не найдена")
    
    return {"message": "Данные доски обновлены", "updated_at": board.updated_at}


@app.get("/whiteboard/users", response_model=List[schemas.User])
def get_whiteboard_users(
    db: Session = Depends(auth.get_db),
    current: models.User = Depends(auth.get_current_user)
):
    """Получить список всех пользователей для назначения прав доступа"""
    users = crud.get_all_users(db)
    return users


@app.post("/whiteboard/projects/{project_id}/users/{user_id}")
def add_user_to_whiteboard_project(
    project_id: int,
    user_id: int,
    permissions: schemas.WhiteboardProjectPermissionCreate,
    db: Session = Depends(auth.get_db),
    current: models.User = Depends(auth.get_current_user)
):
    """Добавить пользователя к проекту доски"""
    # Проверяем права на управление
    if not crud.check_user_whiteboard_permission(db, project_id, current.id, "manage"):
        raise HTTPException(status_code=403, detail="Нет прав на управление этим проектом")
    
    # Проверяем, что пользователь существует
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    
    permission = crud.add_user_to_whiteboard_project(
        db, project_id, user_id, 
        permissions.can_view, permissions.can_edit, permissions.can_manage
    )
    
    if not permission:
        raise HTTPException(status_code=400, detail="Пользователь уже добавлен к проекту")
    
    return {"message": "Пользователь добавлен к проекту", "permission": permission}


@app.delete("/whiteboard/projects/{project_id}/users/{user_id}")
def remove_user_from_whiteboard_project(
    project_id: int,
    user_id: int,
    db: Session = Depends(auth.get_db),
    current: models.User = Depends(auth.get_current_user)
):
    """Удалить пользователя из проекта доски"""
    # Проверяем права на управление
    if not crud.check_user_whiteboard_permission(db, project_id, current.id, "manage"):
        raise HTTPException(status_code=403, detail="Нет прав на управление этим проектом")
    
    # Нельзя удалить создателя проекта
    project = crud.get_whiteboard_project(db, project_id)
    if project and project.created_by == user_id:
        raise HTTPException(status_code=400, detail="Нельзя удалить создателя проекта")
    
    success = crud.remove_user_from_whiteboard_project(db, project_id, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Пользователь не найден в проекте")
    
    return {"message": "Пользователь удален из проекта"}


@app.delete("/whiteboard/projects/{project_id}")
def delete_whiteboard_project(
    project_id: int,
    db: Session = Depends(auth.get_db),
    current: models.User = Depends(auth.get_current_user)
):
    """Удалить проект доски. Может удалить только создатель проекта."""
    success = crud.delete_whiteboard_project(db, project_id, current.id)
    if not success:
        # Проверяем, существует ли проект
        project = crud.get_whiteboard_project(db, project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Проект не найден")
        else:
            raise HTTPException(status_code=403, detail="Только создатель проекта может его удалить")
    
    return {"message": "Проект доски удален"}


@app.put("/whiteboard/projects/{project_id}/users/{user_id}")
def update_user_whiteboard_permissions(
    project_id: int,
    user_id: int,
    permissions: schemas.WhiteboardProjectPermissionCreate,
    db: Session = Depends(auth.get_db),
    current: models.User = Depends(auth.get_current_user)
):
    """Обновить права пользователя в проекте доски"""
    # Проверяем права на управление
    if not crud.check_user_whiteboard_permission(db, project_id, current.id, "manage"):
        raise HTTPException(status_code=403, detail="Нет прав на управление этим проектом")
    
    permission = crud.update_user_whiteboard_permissions(
        db, project_id, user_id,
        permissions.can_view, permissions.can_edit, permissions.can_manage
    )
    
    if not permission:
        raise HTTPException(status_code=404, detail="Пользователь не найден в проекте")
    
    return {"message": "Права пользователя обновлены", "permission": permission}






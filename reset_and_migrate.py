#!/usr/bin/env python3
import sqlite3
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import sys
import os
sys.path.append('./agency_backend')

from agency_backend.app.models import Base, Task, TaskStatus, User, RoleEnum
from agency_backend.app.database import engine

# Mapping of names and their roles
USER_MAPPING = {
    # Дизайнеры
    'Маша': {'role': RoleEnum.designer, 'active': True},
    'Мария': {'role': RoleEnum.designer, 'active': True},
    'Улугбек': {'role': RoleEnum.inactive, 'active': False},  # Не работает
    'Нил': {'role': RoleEnum.designer, 'active': True},
    'Мухаммед': {'role': RoleEnum.designer, 'active': True},
    
    # SMM Менеджеры
    'Сабина': {'role': RoleEnum.head_smm, 'active': True},
    'Севинч': {'role': RoleEnum.smm_manager, 'active': True},
    'Амалия': {'role': RoleEnum.smm_manager, 'active': True},
    'Зарина': {'role': RoleEnum.smm_manager, 'active': True},
    
    # Другие
    'Эльдорбек': {'role': RoleEnum.inactive, 'active': False},  # Не указан в списке
    'Сергей': {'role': RoleEnum.admin, 'active': True},  # Предполагаю админ
}

def clean_database():
    """Clean existing users and tasks except Administrator"""
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    
    try:
        # Delete all tasks
        session.query(Task).delete()
        
        # Delete all users except Administrator
        session.query(User).filter(User.login != 'admin').delete()
        
        session.commit()
        print("Database cleaned successfully")
    except Exception as e:
        print(f"Error cleaning database: {e}")
        session.rollback()
    finally:
        session.close()

def parse_deadline(deadline_str):
    """Parse deadline string from telegram bot format"""
    if not deadline_str:
        return None
    try:
        # Format: "20.03.2025 15:00"
        return datetime.strptime(deadline_str, "%d.%m.%Y %H:%M")
    except:
        return None

def get_or_create_user(session, name):
    """Get existing user or create new one based on mapping"""
    if not name:
        return None
    
    # Check mapping
    user_info = USER_MAPPING.get(name)
    if not user_info:
        # Unknown user - make inactive
        user_info = {'role': RoleEnum.inactive, 'active': False}
    
    # Check if user exists
    user = session.query(User).filter(User.name == name).first()
    if not user:
        # Create user
        login = name.lower().replace(' ', '_')
        # Inactive users get a random password (they can't login)
        if user_info['active']:
            password_hash = '$2b$12$LQv3c1yqBWVHxkd0LHAaeOu0Ztgffq5ew8jJlif7DfI3JY0Jvh5yy'  # 123456
        else:
            password_hash = '$2b$12$' + os.urandom(22).hex()  # Random password for inactive
        
        user = User(
            name=name,
            login=login,
            hashed_password=password_hash,
            role=user_info['role']
        )
        session.add(user)
        session.commit()
        print(f"Created user: {name} with role {user_info['role']}")
    return user

def get_admin_user(session):
    """Get or create admin user for admin tasks"""
    admin = session.query(User).filter(User.login == 'admin').first()
    if not admin:
        admin = User(
            name='Administrator',
            login='admin',
            hashed_password='$2b$12$LQv3c1yqBWVHxkd0LHAaeOu0Ztgffq5ew8jJlif7DfI3JY0Jvh5yy',  # 123456
            role=RoleEnum.admin
        )
        session.add(admin)
        session.commit()
    return admin

def map_status(old_status):
    """Map old status to new TaskStatus enum"""
    status_map = {
        'completed': TaskStatus.done,
        'in_progress': TaskStatus.in_progress,
        'pending': TaskStatus.in_progress,
        'cancelled': TaskStatus.done,
    }
    return status_map.get(old_status, TaskStatus.in_progress)

def migrate_tasks():
    """Migrate tasks from telegram bot database to application database"""
    
    # Connect to telegram bot database
    telegram_db = '/mnt/c/Users/Господин/Downloads/tasks.db'
    if not os.path.exists(telegram_db):
        print(f"Error: Database file not found: {telegram_db}")
        return
    
    conn = sqlite3.connect(telegram_db)
    cursor = conn.cursor()
    
    # Create session for application database
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    
    try:
        # Get admin user for admin tasks
        admin_user = get_admin_user(session)
        
        # Get all tasks from telegram bot
        cursor.execute("""
            SELECT id, designer, project, description, content_type, 
                   format, deadline, reference, files, status, 
                   created_at, updated_at, manager, admin
            FROM tasks
        """)
        
        tasks = cursor.fetchall()
        print(f"Found {len(tasks)} tasks to migrate")
        
        migrated_count = 0
        skipped_count = 0
        admin_tasks_count = 0
        
        for task_data in tasks:
            (task_id, designer, project, description, content_type,
             format_type, deadline, reference, files, status,
             created_at, updated_at, manager, admin) = task_data
            
            # Determine executor
            executor = None
            if designer:
                # Normalize Маша to Мария
                if designer == 'Маша':
                    designer = 'Мария'
                executor = get_or_create_user(session, designer)
            elif admin:  # If no designer but has admin field - assign to admin
                executor = admin_user
                admin_tasks_count += 1
            else:
                skipped_count += 1
                continue
            
            # Get or create author (manager or admin)
            author = None
            if manager:
                author = get_or_create_user(session, manager)
            elif admin:
                author = get_or_create_user(session, admin)
            
            # Parse deadline
            deadline_dt = parse_deadline(deadline)
            
            # Prepare task title
            title = description[:200] if description else f"Task #{task_id}"
            
            # Prepare full description
            full_description = description or ""
            if reference:
                full_description += f"\n\nReference: {reference}"
            if files:
                full_description += f"\n\nFiles: {files}"
            
            # Parse timestamps
            try:
                created_dt = datetime.fromisoformat(created_at.replace(' ', 'T')) if created_at else datetime.utcnow()
            except:
                created_dt = datetime.utcnow()
            
            # Determine finished_at for completed tasks
            finished_at = None
            if status == 'completed':
                try:
                    finished_at = datetime.fromisoformat(updated_at.replace(' ', 'T')) if updated_at else None
                except:
                    finished_at = None
            
            # Create new task
            new_task = Task(
                title=title,
                description=full_description,
                project=project or "Unknown",
                deadline=deadline_dt,
                status=map_status(status),
                task_type=content_type,
                task_format=format_type,
                high_priority=False,
                executor_id=executor.id if executor else None,
                author_id=author.id if author else None,
                created_at=created_dt,
                finished_at=finished_at
            )
            
            session.add(new_task)
            migrated_count += 1
            
            if migrated_count % 100 == 0:
                session.commit()
                print(f"Migrated {migrated_count} tasks...")
        
        # Final commit
        session.commit()
        print(f"\nMigration completed!")
        print(f"Successfully migrated: {migrated_count} tasks")
        print(f"Admin tasks: {admin_tasks_count}")
        print(f"Skipped (no assignee): {skipped_count} tasks")
        
    except Exception as e:
        print(f"Error during migration: {e}")
        session.rollback()
        raise
    finally:
        conn.close()
        session.close()

if __name__ == "__main__":
    print("Cleaning database and starting migration...")
    clean_database()
    migrate_tasks()
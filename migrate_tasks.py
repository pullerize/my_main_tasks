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
    """Get existing user or create new one"""
    if not name:
        return None
    
    user = session.query(User).filter(User.name == name).first()
    if not user:
        # Create user with default login and password
        user = User(
            name=name,
            login=name.lower().replace(' ', '_'),
            hashed_password='$2b$12$LQv3c1yqBWVHxkd0LHAaeOu0Ztgffq5ew8jJlif7DfI3JY0Jvh5yy',  # default password: 123456
            role=RoleEnum.designer
        )
        session.add(user)
        session.commit()
    return user

def map_status(old_status):
    """Map old status to new TaskStatus enum"""
    status_map = {
        'completed': TaskStatus.done,
        'in_progress': TaskStatus.in_progress,
        'pending': TaskStatus.in_progress,
        'cancelled': TaskStatus.done,  # Treat cancelled as done
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
        
        for task_data in tasks:
            (task_id, designer, project, description, content_type,
             format_type, deadline, reference, files, status,
             created_at, updated_at, manager, admin) = task_data
            
            # Skip if no designer assigned
            if not designer:
                skipped_count += 1
                continue
            
            # Get or create designer user
            executor = get_or_create_user(session, designer)
            
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
        print(f"Skipped (no designer): {skipped_count} tasks")
        
    except Exception as e:
        print(f"Error during migration: {e}")
        session.rollback()
        raise
    finally:
        conn.close()
        session.close()

if __name__ == "__main__":
    print("Starting task migration from Telegram bot to application...")
    migrate_tasks()
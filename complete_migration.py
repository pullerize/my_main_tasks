#!/usr/bin/env python3
import sqlite3
from datetime import datetime
import sys
sys.path.append('./agency_backend')

from agency_backend.app.models import Base, Task, TaskStatus, User, RoleEnum
from agency_backend.app.database import engine
from sqlalchemy.orm import sessionmaker

def parse_deadline(deadline_str):
    """Parse deadline string from telegram bot format"""
    if not deadline_str:
        return None
    try:
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
            hashed_password='$2b$12$LQv3c1yqBWVHxkd0LHAaeOu0Ztgffq5ew8jJlif7DfI3JY0Jvh5yy',  # 123456
            role=RoleEnum.inactive  # New users are inactive by default
        )
        session.add(user)
        session.commit()
    return user

def get_admin_user(session):
    """Get admin user for admin tasks"""
    admin = session.query(User).filter(User.login == 'admin').first()
    if not admin:
        admin = User(
            name='Administrator',
            login='admin',
            hashed_password='$2b$12$LQv3c1yqBWVHxkd0LHAaeOu0Ztgffq5ew8jJlif7DfI3JY0Jvh5yy',
            role=RoleEnum.admin
        )
        session.add(admin)
        session.commit()
    return admin

def map_status(old_status):
    """Map old status to new TaskStatus enum"""
    status_map = {
        'completed': TaskStatus.done,
        'cancelled': TaskStatus.cancelled,
        'active': TaskStatus.in_progress,
    }
    return status_map.get(old_status, TaskStatus.in_progress)

def complete_migration():
    """Complete migration of ALL tasks from telegram bot"""
    
    # Connect to telegram bot database
    telegram_db = '/mnt/c/Users/Господин/Downloads/tasks.db'
    conn = sqlite3.connect(telegram_db)
    cursor = conn.cursor()
    
    # Create session for application database
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    
    try:
        # Clear existing tasks
        print("Clearing existing tasks...")
        session.query(Task).delete()
        session.commit()
        
        # Get admin user for admin tasks
        admin_user = get_admin_user(session)
        
        # Get ALL tasks from telegram bot
        cursor.execute("""
            SELECT id, designer, project, description, content_type, 
                   format, deadline, reference, files, status, 
                   created_at, updated_at, assigned_at, manager, admin
            FROM tasks
            ORDER BY id
        """)
        
        tasks = cursor.fetchall()
        print(f"Found {len(tasks)} tasks to migrate")
        
        # Count statuses
        status_counts = {'completed': 0, 'cancelled': 0, 'active': 0, 'other': 0}
        
        migrated_count = 0
        
        for task_data in tasks:
            (task_id, designer, project, description, content_type,
             format_type, deadline, reference, files, status,
             created_at, updated_at, assigned_at, manager, admin) = task_data
            
            # Count original statuses
            if status in status_counts:
                status_counts[status] += 1
            else:
                status_counts['other'] += 1
            
            # Determine executor
            executor = None
            if designer:
                # Normalize Маша to Мария
                if designer == 'Маша':
                    designer = 'Мария'
                executor = get_or_create_user(session, designer)
            
            # If no designer but has admin field - assign to admin
            if not executor and admin:
                executor = admin_user
            
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
            
            # Determine finished_at for completed/cancelled tasks
            finished_at = None
            if status in ['completed', 'cancelled']:
                try:
                    finished_at = datetime.fromisoformat(updated_at.replace(' ', 'T')) if updated_at else created_dt
                except:
                    finished_at = created_dt
            
            # Create new task with exact status mapping
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
        
        # Verify results
        final_in_progress = session.query(Task).filter(Task.status == TaskStatus.in_progress).count()
        final_done = session.query(Task).filter(Task.status == TaskStatus.done).count()
        final_cancelled = session.query(Task).filter(Task.status == TaskStatus.cancelled).count()
        total_final = final_in_progress + final_done + final_cancelled
        
        print(f"\n✅ COMPLETE MIGRATION RESULTS:")
        print(f"📊 Original Telegram Bot:")
        print(f"   completed: {status_counts['completed']}")
        print(f"   cancelled: {status_counts['cancelled']}")
        print(f"   active: {status_counts['active']}")
        print(f"   other: {status_counts['other']}")
        print(f"   TOTAL: {sum(status_counts.values())}")
        
        print(f"\n🎯 Application Database:")
        print(f"   done: {final_done}")
        print(f"   cancelled: {final_cancelled}")
        print(f"   in_progress: {final_in_progress}")
        print(f"   TOTAL: {total_final}")
        
        print(f"\n✨ Successfully migrated ALL {migrated_count} tasks!")
        print(f"📈 Coverage: {total_final}/{sum(status_counts.values())} = {total_final/sum(status_counts.values())*100:.1f}%")
        
    except Exception as e:
        print(f"Error during complete migration: {e}")
        session.rollback()
        raise
    finally:
        conn.close()
        session.close()

if __name__ == "__main__":
    print("Starting COMPLETE migration of ALL tasks from Telegram bot...")
    complete_migration()
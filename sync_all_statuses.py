#!/usr/bin/env python3
import sqlite3
from datetime import datetime
import sys
sys.path.append('./agency_backend')

from agency_backend.app.models import Task, TaskStatus
from agency_backend.app.database import engine
from sqlalchemy.orm import sessionmaker

def sync_all_statuses():
    """Sync all task statuses with original telegram bot database"""
    
    # Connect to telegram bot database
    telegram_db = '/mnt/c/Users/Господин/Downloads/tasks.db'
    conn = sqlite3.connect(telegram_db)
    cursor = conn.cursor()
    
    # Get all tasks from telegram bot with their statuses
    cursor.execute("""
        SELECT description, status, updated_at, created_at, designer, project
        FROM tasks 
        ORDER BY id
    """)
    
    telegram_tasks = cursor.fetchall()
    conn.close()
    
    print(f"Found {len(telegram_tasks)} tasks in telegram bot")
    
    # Count statuses in telegram bot
    status_counts = {}
    for _, status, _, _, _, _ in telegram_tasks:
        status_counts[status] = status_counts.get(status, 0) + 1
    
    print("Telegram bot status distribution:")
    for status, count in status_counts.items():
        print(f"  {status}: {count}")
    
    # Create session for application database
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    
    try:
        # First, reset all tasks to in_progress
        print("\nResetting all tasks to in_progress...")
        all_tasks = session.query(Task).all()
        for task in all_tasks:
            task.status = TaskStatus.in_progress
            task.finished_at = None
        session.commit()
        
        # Create dictionaries for fast lookup
        completed_signatures = {}  # signature -> (status, updated_at)
        active_signatures = {}
        cancelled_signatures = {}
        
        for description, status, updated_at, created_at, designer, project in telegram_tasks:
            if description and project and designer:
                signature = f"{description}|{project}|{designer}".lower()
                
                if status == 'completed':
                    completed_signatures[signature] = (status, updated_at)
                elif status == 'active':
                    active_signatures[signature] = (status, updated_at)
                elif status == 'cancelled':
                    cancelled_signatures[signature] = (status, updated_at)
        
        print(f"Created {len(completed_signatures)} completed signatures")
        print(f"Created {len(active_signatures)} active signatures")
        print(f"Created {len(cancelled_signatures)} cancelled signatures")
        
        # Update task statuses
        completed_count = 0
        active_count = 0
        cancelled_count = 0
        
        for task in all_tasks:
            # Create signature for this task
            title = task.title or ""
            project = task.project or ""
            
            # Get executor name
            executor_name = ""
            if task.executor_id:
                from agency_backend.app.models import User
                executor = session.query(User).filter(User.id == task.executor_id).first()
                if executor:
                    executor_name = executor.name
            
            signature = f"{title}|{project}|{executor_name}".lower()
            
            # Check status and update accordingly
            if signature in completed_signatures:
                task.status = TaskStatus.done
                # Set finished_at from telegram bot data
                _, updated_at = completed_signatures[signature]
                if updated_at:
                    try:
                        task.finished_at = datetime.fromisoformat(updated_at.replace(' ', 'T'))
                    except:
                        task.finished_at = task.created_at
                else:
                    task.finished_at = task.created_at
                completed_count += 1
                
            elif signature in cancelled_signatures:
                # Treat cancelled as done too
                task.status = TaskStatus.done
                _, updated_at = cancelled_signatures[signature]
                if updated_at:
                    try:
                        task.finished_at = datetime.fromisoformat(updated_at.replace(' ', 'T'))
                    except:
                        task.finished_at = task.created_at
                else:
                    task.finished_at = task.created_at
                cancelled_count += 1
                
            elif signature in active_signatures:
                # Keep as in_progress (already set above)
                active_count += 1
                
            # If no match found, keep as in_progress (default)
        
        session.commit()
        
        # Check final counts
        final_in_progress = session.query(Task).filter(Task.status == TaskStatus.in_progress).count()
        final_done = session.query(Task).filter(Task.status == TaskStatus.done).count()
        
        print(f"\nStatus updates:")
        print(f"  Matched completed: {completed_count}")
        print(f"  Matched cancelled: {cancelled_count}")  
        print(f"  Matched active: {active_count}")
        print(f"  Total matched: {completed_count + cancelled_count + active_count}")
        
        print(f"\nFinal database counts:")
        print(f"  In progress: {final_in_progress}")
        print(f"  Done: {final_done}")
        print(f"  Total: {final_in_progress + final_done}")
        
        # Show some examples
        print(f"\nExamples of completed tasks:")
        done_tasks = session.query(Task).filter(Task.status == TaskStatus.done).limit(5).all()
        for task in done_tasks:
            print(f"  - {task.title[:40]}... | {task.project}")
            
        print(f"\nExamples of active tasks:")
        active_tasks = session.query(Task).filter(Task.status == TaskStatus.in_progress).limit(5).all()
        for task in active_tasks:
            print(f"  - {task.title[:40]}... | {task.project}")
        
    except Exception as e:
        print(f"Error syncing statuses: {e}")
        session.rollback()
        raise
    finally:
        session.close()

if __name__ == "__main__":
    print("Syncing all task statuses with telegram bot...")
    sync_all_statuses()
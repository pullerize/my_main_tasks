#!/usr/bin/env python3
import sqlite3
from datetime import datetime
import sys
sys.path.append('./agency_backend')

from agency_backend.app.models import Task, TaskStatus
from agency_backend.app.database import engine
from sqlalchemy.orm import sessionmaker

def fix_completed_tasks_precise():
    """Fix task statuses by matching with original telegram bot database"""
    
    # Connect to telegram bot database
    telegram_db = '/mnt/c/Users/Господин/Downloads/tasks.db'
    conn = sqlite3.connect(telegram_db)
    cursor = conn.cursor()
    
    # Get all completed/cancelled tasks from telegram bot with details
    cursor.execute("""
        SELECT description, status, updated_at, created_at, designer, project
        FROM tasks 
        WHERE status IN ('completed', 'cancelled')
        ORDER BY id
    """)
    
    completed_tasks = cursor.fetchall()
    conn.close()
    
    print(f"Found {len(completed_tasks)} completed tasks in telegram bot")
    
    # Create session for application database
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    
    try:
        updated_count = 0
        
        # Create a set of completed task signatures for fast lookup
        completed_signatures = set()
        for description, status, updated_at, created_at, designer, project in completed_tasks:
            # Create signature from description + project + designer
            signature = f"{description}|{project}|{designer}".lower() if description and project and designer else None
            if signature:
                completed_signatures.add(signature)
        
        print(f"Created {len(completed_signatures)} unique signatures")
        
        # Check all tasks in app database
        all_tasks = session.query(Task).all()
        
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
            
            # Check if this task should be completed
            if signature in completed_signatures and task.status == TaskStatus.in_progress:
                task.status = TaskStatus.done
                # Set finished_at if not already set
                if not task.finished_at:
                    task.finished_at = task.created_at  # Approximate
                updated_count += 1
                
                if updated_count <= 5:  # Show first 5 for verification
                    print(f"  Updating: {task.title[:50]}... -> DONE")
        
        session.commit()
        
        # Check final counts
        final_in_progress = session.query(Task).filter(Task.status == TaskStatus.in_progress).count()
        final_done = session.query(Task).filter(Task.status == TaskStatus.done).count()
        
        print(f"\nUpdated {updated_count} tasks to completed status")
        print(f"Final counts:")
        print(f"  In progress: {final_in_progress}")
        print(f"  Done: {final_done}")
        print(f"  Total: {final_in_progress + final_done}")
        
    except Exception as e:
        print(f"Error updating tasks: {e}")
        session.rollback()
        raise
    finally:
        session.close()

if __name__ == "__main__":
    print("Fixing completed task statuses (v2 - precise matching)...")
    fix_completed_tasks_precise()
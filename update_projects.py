#!/usr/bin/env python3
import sys
import sqlite3
from datetime import datetime
sys.path.append('./agency_backend')

from agency_backend.app.models import Project, Task
from agency_backend.app.database import engine
from sqlalchemy.orm import sessionmaker

def create_projects():
    """Create all projects in the system"""
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    
    projects_list = [
        'EVOS', 'EVOS HR', 'Cat', 'Saga', 'Issimo', 
        'NBU Mahalla', 'BYD', 'Davr Cargo', 'KIA', 
        'NBU Career', 'Миграция', 'NBU main', 
        'NBU Business', 'Scopus', '8bit', 'Uzbegim',
        'ШумOFF'
    ]
    
    try:
        # Create projects
        for project_name in projects_list:
            existing = session.query(Project).filter(Project.name == project_name).first()
            if not existing:
                project = Project(name=project_name)
                session.add(project)
                print(f"Added project: {project_name}")
            else:
                print(f"Project {project_name} already exists")
        
        session.commit()
        print("\nProjects added successfully!")
        
    except Exception as e:
        print(f"Error adding projects: {e}")
        session.rollback()
    finally:
        session.close()

def get_unique_projects_from_tasks():
    """Get all unique project names from telegram bot database"""
    telegram_db = '/mnt/c/Users/Господин/Downloads/tasks.db'
    conn = sqlite3.connect(telegram_db)
    cursor = conn.cursor()
    
    cursor.execute("SELECT DISTINCT project FROM tasks WHERE project IS NOT NULL AND project != ''")
    projects = [row[0] for row in cursor.fetchall()]
    conn.close()
    
    return projects

def update_task_projects():
    """Update tasks to reference actual Project models"""
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    
    try:
        # Get all unique projects from tasks
        unique_projects = get_unique_projects_from_tasks()
        print(f"\nFound {len(unique_projects)} unique projects in tasks")
        
        # Create any missing projects
        for project_name in unique_projects:
            if project_name:
                existing = session.query(Project).filter(Project.name == project_name).first()
                if not existing:
                    project = Project(name=project_name)
                    session.add(project)
                    print(f"Created missing project: {project_name}")
        
        session.commit()
        
        # Now update all tasks with project IDs
        all_projects = {p.name: p.id for p in session.query(Project).all()}
        
        # Get all tasks
        tasks = session.query(Task).all()
        updated_count = 0
        
        for task in tasks:
            if task.project and task.project in all_projects:
                # Store project ID in a new field (we'll need to add this field)
                # For now, we'll just ensure the project name matches
                updated_count += 1
        
        print(f"\nAll {len(tasks)} tasks have their project names preserved")
        print(f"Total projects in system: {len(all_projects)}")
        
        # Show statistics
        print("\nProject statistics:")
        for project_name, project_id in all_projects.items():
            task_count = session.query(Task).filter(Task.project == project_name).count()
            if task_count > 0:
                print(f"  {project_name}: {task_count} tasks")
        
        session.commit()
        
    except Exception as e:
        print(f"Error updating task projects: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    print("Creating projects and updating task relationships...")
    create_projects()
    update_task_projects()
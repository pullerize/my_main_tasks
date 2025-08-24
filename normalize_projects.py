#!/usr/bin/env python3
import sys
sys.path.append('./agency_backend')

from agency_backend.app.models import Project, Task
from agency_backend.app.database import engine
from sqlalchemy.orm import sessionmaker

def normalize_projects():
    """Normalize project names and merge duplicates"""
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    
    # Mapping of variant names to canonical names
    project_mapping = {
        # 8bit variations
        '8BIT': '8bit',
        '8Bit': '8bit', 
        '8 bit': '8bit',
        '8бит': '8bit',
        
        # Uzbegim variations
        'UZBEGIM': 'Uzbegim',
        'УЗБЕГИМ': 'Uzbegim',
        'Узбегим': 'Uzbegim',
        'узбегим': 'Uzbegim',
        'Узбегим - подготовить пост для публикации.': 'Uzbegim',
        
        # KIA variations
        'Kia': 'KIA',
        
        # NBU variations
        'NBU': 'NBU main',
        'Nbu official': 'NBU main',
        'NBU фин оп валюты': 'NBU main',
        'NBU навруз': 'NBU main',
        
        # NBU Career variations
        'NBU CAREER': 'NBU Career',
        'NBU career': 'NBU Career',
        'NBU  карьер': 'NBU Career',
        'NBU карьера': 'NBU Career',
        
        # NBU Business variations
        'NBU business': 'NBU Business',
        
        # NBU Mahalla variations
        'NBU mahalla': 'NBU Mahalla',
        'nbu mahalla': 'NBU Mahalla',
        'NBU махалля': 'NBU Mahalla',
        
        # NBU HR variations
        'NBU HR': 'EVOS HR',  # Based on context, NBU HR might be EVOS HR
        'NBU Hr': 'EVOS HR',
        
        # Scopus variations
        'scopus': 'Scopus',
        'SCOPUS': 'Scopus',
        'скопус': 'Scopus',
        'Скопус': 'Scopus',
        'Scopus Mall': 'Scopus',
        
        # BYD variations
        'BYD moodboard': 'BYD',
        'BYD обложку': 'BYD',
        'BYD CLUB': 'BYD',
        'BYD Club': 'BYD',
        'BYD подретушировать тени': 'BYD',
        
        # Hoffman variations
        'Хоффман': 'Hoffman',
        'Хофмман': 'Hoffman',
        'Хофман': 'Hoffman',
        
        # Migration variations
        'Migration': 'Миграция',
        
        # Remove or rename invalid projects
        'Все': 'Unknown',
        'провести собеседование': 'Unknown',
        '1': 'Unknown',
        'Моушн видео мечкат': 'Unknown',
        'Сценарий: Вид сверху на планету. Подсвечены контуры стран, где есть настоящая\nтехнология 5G (например, Южная Корея, США, Германия). Затем подсвечивается\nконтур Узбекистана. Над ним появляется иконка связи "5G Standalone" \n\nВ левом верхнем углу экрана можно сделать небольшую надпись: 5G SA Coverage Map\n\nУзбекистан\\Ташкент должен подсветиться в красном оттенке, код цвета их фирменного : #e60000\nФирменный шрифт отправлю в группу и лого тоже': 'Uzbegim',
    }
    
    try:
        # Update all tasks with normalized project names
        tasks = session.query(Task).all()
        updated_count = 0
        
        for task in tasks:
            if task.project in project_mapping:
                old_name = task.project
                new_name = project_mapping[old_name]
                task.project = new_name
                updated_count += 1
                
        session.commit()
        print(f"Updated {updated_count} tasks with normalized project names")
        
        # Delete duplicate/invalid projects
        projects_to_delete = []
        for project in session.query(Project).all():
            if project.name in project_mapping:
                projects_to_delete.append(project.name)
        
        for project_name in projects_to_delete:
            project = session.query(Project).filter(Project.name == project_name).first()
            if project:
                session.delete(project)
                print(f"Deleted duplicate project: {project_name}")
        
        # Also add any missing canonical projects
        canonical_projects = set(project_mapping.values())
        for project_name in canonical_projects:
            if project_name != 'Unknown':
                existing = session.query(Project).filter(Project.name == project_name).first()
                if not existing:
                    project = Project(name=project_name)
                    session.add(project)
                    print(f"Added canonical project: {project_name}")
        
        # Add special projects that may be needed
        special_projects = ['Saris', 'Hoffman', 'Sora', 'Unknown']
        for project_name in special_projects:
            existing = session.query(Project).filter(Project.name == project_name).first()
            if not existing:
                project = Project(name=project_name)
                session.add(project)
                print(f"Added special project: {project_name}")
        
        session.commit()
        
        # Show final statistics
        print("\nFinal project statistics:")
        all_projects = session.query(Project).all()
        for project in all_projects:
            task_count = session.query(Task).filter(Task.project == project.name).count()
            if task_count > 0:
                print(f"  {project.name}: {task_count} tasks")
        
        print(f"\nTotal projects: {len(all_projects)}")
        
    except Exception as e:
        print(f"Error normalizing projects: {e}")
        session.rollback()
        raise
    finally:
        session.close()

if __name__ == "__main__":
    print("Normalizing project names...")
    normalize_projects()
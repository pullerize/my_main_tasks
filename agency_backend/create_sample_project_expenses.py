#!/usr/bin/env python3
"""Create sample project expenses"""

from app.database import SessionLocal
from app import models
from datetime import date, timedelta
import random

db = SessionLocal()

try:
    # Get existing projects
    projects = db.query(models.Project).all()
    print(f"Found {len(projects)} projects")
    
    # Get existing categories
    categories = db.query(models.ExpenseCategory).all()
    print(f"Found {len(categories)} categories")
    
    # Get admin user
    admin = db.query(models.User).filter(models.User.telegram_username == "admin").first()
    
    if not projects:
        print("No projects found, cannot create expenses")
        exit()
    
    # Sample expenses data
    sample_expenses = [
        {"name": "Дизайн логотипа", "amount": 500000, "description": "Создание фирменного стиля"},
        {"name": "Видеосъемка", "amount": 1200000, "description": "Съемка рекламного ролика"},
        {"name": "Транспорт на съемку", "amount": 80000, "description": "Аренда автомобиля"},
        {"name": "Аренда оборудования", "amount": 350000, "description": "Камера и свет"},
        {"name": "Монтаж видео", "amount": 400000, "description": "Постпродакшн"},
        {"name": "Печать баннеров", "amount": 250000, "description": "Рекламные материалы"},
        {"name": "SMM продвижение", "amount": 600000, "description": "Реклама в соцсетях"},
        {"name": "Хостинг сайта", "amount": 120000, "description": "Месячная оплата"},
    ]
    
    # Create expenses for each project
    for project in projects:
        print(f"\nCreating expenses for project: {project.name}")
        
        # Create 3-5 random expenses for each project
        num_expenses = random.randint(3, 5)
        selected_expenses = random.sample(sample_expenses, num_expenses)
        
        for expense_data in selected_expenses:
            expense = models.ProjectExpense(
                project_id=project.id,
                category_id=categories[0].id if categories else None,  # Use first category
                name=expense_data["name"],
                amount=expense_data["amount"],
                description=expense_data["description"],
                date=date.today() - timedelta(days=random.randint(1, 30)),
                created_by=admin.id if admin else None
            )
            db.add(expense)
            print(f"  + {expense_data['name']}: {expense_data['amount']:,} сум")
    
    db.commit()
    print("\n✅ Sample project expenses created successfully!")
    
    # Show summary
    total_expenses = db.query(models.ProjectExpense).count()
    print(f"Total project expenses in database: {total_expenses}")
    
except Exception as e:
    print(f"Error: {e}")
    db.rollback()
finally:
    db.close()
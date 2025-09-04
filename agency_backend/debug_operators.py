#!/usr/bin/env python3
"""Debug operators data"""

from app.database import SessionLocal
from app import models

db = SessionLocal()

try:
    # Check all operators
    operators = db.query(models.Operator).all()
    print(f"Total operators: {len(operators)}")
    
    for operator in operators:
        print(f"\nID: {operator.id}")
        print(f"Name: {operator.name}")
        print(f"Role: {operator.role}")
        print(f"Is salaried: {operator.is_salaried}")
        print(f"Monthly salary: {operator.monthly_salary}")
        print(f"Price per video: {operator.price_per_video}")
        
        # Count completed videos
        completed_videos = db.query(models.Shooting).filter(
            models.Shooting.operator_id == operator.id,
            models.Shooting.completed == True
        ).all()
        
        videos_count = sum(s.completed_quantity or 0 for s in completed_videos)
        print(f"Completed videos: {videos_count}")
        
        # Calculate total like in the report
        if operator.is_salaried:
            total_amount = float(operator.monthly_salary or 0)
        else:
            total_amount = float(videos_count * (operator.price_per_video or 0))
        
        print(f"Total amount: {total_amount}")
        
except Exception as e:
    print(f"Error: {e}")
finally:
    db.close()
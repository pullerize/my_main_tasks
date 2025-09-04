#!/usr/bin/env python3
"""Fix Anastasia's salary data"""

from app.database import SessionLocal
from app import models

db = SessionLocal()

try:
    # Find Anastasia
    anastasia = db.query(models.Operator).filter(models.Operator.name == "Анастасия").first()
    
    if anastasia:
        print(f"Found Anastasia (ID: {anastasia.id})")
        print(f"Before: is_salaried={anastasia.is_salaried}, monthly_salary={anastasia.monthly_salary}, price_per_video={anastasia.price_per_video}")
        
        # Update her salary info
        anastasia.is_salaried = True
        anastasia.monthly_salary = 5000000  # 5,000,000 so'm
        anastasia.price_per_video = 0  # Not needed for salaried employee
        
        db.commit()
        
        print(f"After: is_salaried={anastasia.is_salaried}, monthly_salary={anastasia.monthly_salary}, price_per_video={anastasia.price_per_video}")
        print("✅ Anastasia's salary data updated successfully!")
        
        # Test calculation
        if anastasia.is_salaried:
            total_amount = float(anastasia.monthly_salary or 0)
            print(f"Total amount should be: {total_amount}")
    else:
        print("❌ Anastasia not found")
        
except Exception as e:
    print(f"Error: {e}")
    db.rollback()
finally:
    db.close()
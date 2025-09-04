#!/usr/bin/env python3
"""Check database for employee expenses with NULL dates"""

from app.database import SessionLocal
from app import models

db = SessionLocal()

try:
    # Check all employee expenses
    expenses = db.query(models.EmployeeExpense).all()
    print(f"Total EmployeeExpense records: {len(expenses)}")
    
    for expense in expenses:
        print(f"ID: {expense.id}, Name: {expense.name}, Date: {expense.date}, User: {expense.user_id}")
        
    # Check for NULL dates specifically
    null_date_expenses = db.query(models.EmployeeExpense).filter(models.EmployeeExpense.date.is_(None)).all()
    print(f"\nRecords with NULL dates: {len(null_date_expenses)}")
    
    for expense in null_date_expenses:
        print(f"NULL date record - ID: {expense.id}, Name: {expense.name}")
        
except Exception as e:
    print(f"Error: {e}")
finally:
    db.close()
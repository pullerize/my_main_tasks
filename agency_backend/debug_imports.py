#!/usr/bin/env python3
"""Debug imports and schema definitions"""

print("=== Testing imports ===")
from datetime import datetime, date
from typing import Optional

print(f"date type: {date}")
print(f"Optional[date]: {Optional[date]}")

# Test basic schema definition
from pydantic import BaseModel

class TestSchema(BaseModel):
    test_date: Optional[date] = None

print(f"TestSchema date field: {TestSchema.model_fields['test_date']}")

# Now test the actual schema
print("\n=== Testing actual schema in isolation ===")
from app.schemas import EmployeeExpenseBase

print(f"EmployeeExpenseBase definition: {EmployeeExpenseBase}")
print(f"EmployeeExpenseBase source: {EmployeeExpenseBase.__module__}")

# Check if there's a global date variable interfering
import app.schemas
print(f"\nChecking app.schemas namespace:")
if hasattr(app.schemas, 'date'):
    print(f"app.schemas.date = {app.schemas.date}")
else:
    print("No 'date' attribute in app.schemas")
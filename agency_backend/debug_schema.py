#!/usr/bin/env python3
"""Debug schema validation"""

from datetime import date
from app.schemas import EmployeeExpense

# Test schema validation
test_data = {
    "id": 1,
    "user_id": 1,
    "name": "Test",
    "amount": 100.0,
    "description": "Test description",
    "date": date(2024, 1, 1),  # Pass actual date object
    "created_at": "2024-01-01T00:00:00",
    "user": None
}

try:
    expense = EmployeeExpense(**test_data)
    print(f"✅ Schema validation successful: {expense}")
except Exception as e:
    print(f"❌ Schema validation failed: {e}")

# Print schema info
print(f"EmployeeExpense model fields: {EmployeeExpense.model_fields}")
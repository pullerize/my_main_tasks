#!/usr/bin/env python3
"""Debug current schema state"""

from app.schemas import EmployeeExpense, EmployeeExpenseBase, EmployeeExpenseCreate
import json

print("=== Schema Field Analysis ===")
print(f"EmployeeExpenseBase fields: {EmployeeExpenseBase.model_fields}")
print(f"EmployeeExpenseCreate fields: {EmployeeExpenseCreate.model_fields}")
print(f"EmployeeExpense fields: {EmployeeExpense.model_fields}")

print("\n=== Date Field Details ===")
if 'date' in EmployeeExpense.model_fields:
    date_field = EmployeeExpense.model_fields['date']
    print(f"EmployeeExpense date field: {date_field}")
    print(f"Date field annotation: {date_field.annotation}")
    print(f"Date field required: {date_field.is_required()}")
    
print("\n=== Schema JSON Schema ===")
schema = EmployeeExpense.model_json_schema()
if 'properties' in schema and 'date' in schema['properties']:
    print(f"Date property in JSON schema: {schema['properties']['date']}")
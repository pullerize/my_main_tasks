#!/usr/bin/env python3
"""Test employee expense API endpoints"""

import requests
import json

BASE_URL = "http://127.0.0.1:8000"

def test_login():
    """Test login and get token"""
    response = requests.post(f"{BASE_URL}/token", data={
        "username": "admin",
        "password": "admin123"
    })
    if response.status_code == 200:
        return response.json()["access_token"]
    else:
        print(f"Login failed: {response.status_code} - {response.text}")
        return None

def test_get_employee_expenses(token):
    """Test getting employee expenses"""
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/employee-expenses/", headers=headers)
    print(f"GET /employee-expenses/ - Status: {response.status_code}")
    if response.status_code == 200:
        expenses = response.json()
        print(f"Employee expenses count: {len(expenses)}")
        if expenses:
            print(f"First expense: {expenses[0]}")
    else:
        print(f"Error: {response.text}")
    return response

def test_create_employee_expense(token):
    """Test creating employee expense"""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    data = {
        "name": "Test Expense from Frontend", 
        "amount": 150.0,
        "description": "Test description with date string",
        "date": "2024-01-15"  # Frontend sends date as string
    }
    response = requests.post(f"{BASE_URL}/employee-expenses/", 
                           headers=headers, 
                           json=data)
    print(f"POST /employee-expenses/ - Status: {response.status_code}")
    if response.status_code == 200:
        print(f"Created expense: {response.json()}")
        return response.json()["id"]
    else:
        print(f"Error: {response.text}")
    return None

if __name__ == "__main__":
    print("Testing Employee Expense API...")
    
    # Login
    token = test_login()
    if not token:
        exit(1)
    
    print(f"✅ Login successful, token: {token[:20]}...")
    
    # Test endpoints
    test_get_employee_expenses(token)
    test_create_employee_expense(token)
    
    print("Test completed!")
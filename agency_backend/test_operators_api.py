#!/usr/bin/env python3
"""Test operators API to check salary display"""

import requests

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

def test_get_operators(token):
    """Test getting operators"""
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/operators/", headers=headers)
    print(f"GET /operators/ - Status: {response.status_code}")
    if response.status_code == 200:
        operators = response.json()
        print(f"Operators count: {len(operators)}")
        for op in operators:
            print(f"\nOperator: {op['name']}")
            print(f"  Role: {op['role']}")
            print(f"  Is salaried: {op['is_salaried']}")
            print(f"  Monthly salary: {op.get('monthly_salary', 'N/A')}")
            print(f"  Price per video: {op['price_per_video']}")
    else:
        print(f"Error: {response.text}")
    return response

def test_get_operator_report(token):
    """Test getting operator expense report"""
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/expense-reports/operators", headers=headers)
    print(f"\nGET /expense-reports/operators - Status: {response.status_code}")
    if response.status_code == 200:
        reports = response.json()
        print(f"Operator reports count: {len(reports)}")
        for report in reports:
            print(f"\nOperator: {report['operator_name']}")
            print(f"  Role: {report['role']}")
            print(f"  Is salaried: {report['is_salaried']}")
            print(f"  Monthly salary: {report.get('monthly_salary', 'N/A')}")
            print(f"  Price per video: {report['price_per_video']}")
            print(f"  Videos completed: {report['videos_completed']}")
            print(f"  Total amount: {report['total_amount']}")
    else:
        print(f"Error: {response.text}")
    return response

if __name__ == "__main__":
    print("Testing Operators API...")
    
    # Login
    token = test_login()
    if not token:
        exit(1)
    
    print(f"✅ Login successful, token: {token[:20]}...")
    
    # Test endpoints
    test_get_operators(token)
    test_get_operator_report(token)
    
    print("\nTest completed!")
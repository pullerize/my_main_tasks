#!/usr/bin/env python3
"""Test project expenses detailed API"""

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

def test_get_project_expenses_detailed(token):
    """Test getting detailed project expenses"""
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/project-expenses/detailed", headers=headers)
    print(f"GET /project-expenses/detailed - Status: {response.status_code}")
    if response.status_code == 200:
        expenses = response.json()
        print(f"Project expenses count: {len(expenses)}")
        for expense in expenses[:3]:  # Show first 3
            print(f"\nExpense: {expense['name']}")
            print(f"  Project: {expense['project_name']}")
            print(f"  Category: {expense.get('category_name', 'N/A')}")
            print(f"  Amount: {expense['amount']}")
            print(f"  Date: {expense['date']}")
            print(f"  Created by: {expense.get('creator_name', 'N/A')}")
    else:
        print(f"Error: {response.text}")
    return response

def test_get_projects(token):
    """Test getting projects to see what's available"""
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/projects/", headers=headers)
    print(f"\nGET /projects/ - Status: {response.status_code}")
    if response.status_code == 200:
        projects = response.json()
        print(f"Projects count: {len(projects)}")
        for project in projects[:3]:  # Show first 3
            print(f"  Project: {project['name']} (ID: {project['id']})")
    else:
        print(f"Error: {response.text}")
    return response

if __name__ == "__main__":
    print("Testing Project Expenses Detailed API...")
    
    # Login
    token = test_login()
    if not token:
        exit(1)
    
    print(f"✅ Login successful, token: {token[:20]}...")
    
    # Test endpoints
    test_get_projects(token)
    test_get_project_expenses_detailed(token)
    
    print("\nTest completed!")
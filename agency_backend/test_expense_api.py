#!/usr/bin/env python3
"""Test expense API endpoints"""

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

def test_get_categories(token):
    """Test getting expense categories"""
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/expense-categories/", headers=headers)
    print(f"GET /expense-categories/ - Status: {response.status_code}")
    if response.status_code == 200:
        print(f"Categories: {response.json()}")
    else:
        print(f"Error: {response.text}")
    return response

def test_create_category(token):
    """Test creating expense category"""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    data = {
        "name": "Test Category",
        "description": "Test description",
        "is_active": True
    }
    response = requests.post(f"{BASE_URL}/expense-categories/", 
                           headers=headers, 
                           json=data)
    print(f"POST /expense-categories/ - Status: {response.status_code}")
    if response.status_code == 200:
        print(f"Created category: {response.json()}")
        return response.json()["id"]
    else:
        print(f"Error: {response.text}")
    return None

def test_delete_category(token, category_id):
    """Test deleting expense category"""
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.delete(f"{BASE_URL}/expense-categories/{category_id}", headers=headers)
    print(f"DELETE /expense-categories/{category_id} - Status: {response.status_code}")
    print(f"Response: {response.text}")
    return response

def test_expense_reports(token):
    """Test expense reports endpoint"""
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/expense-reports/", headers=headers)
    print(f"GET /expense-reports/ - Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Total amount: {data['total_amount']}")
        print(f"Items count: {len(data['items'])}")
        print(f"Categories: {list(data['categories_breakdown'].keys())}")
    else:
        print(f"Error: {response.text}")
    return response

if __name__ == "__main__":
    print("Testing Expense API...")
    
    # Login
    token = test_login()
    if not token:
        exit(1)
    
    print(f"✅ Login successful, token: {token[:20]}...")
    
    # Test endpoints
    test_get_categories(token)
    
    # Test expense reports
    test_expense_reports(token)
    
    # Create and delete a test category
    category_id = test_create_category(token)
    if category_id:
        test_delete_category(token, category_id)
    
    print("Test completed!")
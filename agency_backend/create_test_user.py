#!/usr/bin/env python3
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
from app import models
from app.auth import get_password_hash

def main():
    db = SessionLocal()
    
    try:
        # Create test user
        test_user = models.User(
            name="Test User",
            telegram_username="testuser", 
            hashed_password=get_password_hash("test123"),
            role=models.RoleEnum.designer,
            is_active=True
        )
        db.add(test_user)
        db.commit()
        db.refresh(test_user)
        print(f"Created test user: testuser / test123 (ID: {test_user.id})")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    main()
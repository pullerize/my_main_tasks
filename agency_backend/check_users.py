#!/usr/bin/env python3
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
from app import models, crud, schemas
from app.auth import get_password_hash

def main():
    db = SessionLocal()
    
    try:
        # Check if any users exist
        users = db.query(models.User).all()
        print(f"Found {len(users)} users in database")
        
        for user in users:
            print(f"- {user.name} (@{user.telegram_username or 'no_username'}) - Role: {user.role}")
        
        # If no users, create admin user
        if len(users) == 0:
            print("\nNo users found. Creating admin user...")
            admin_user = models.User(
                name="Admin",
                telegram_username="admin",
                hashed_password=get_password_hash("admin123"),
                role=models.RoleEnum.admin,
                is_active=True
            )
            db.add(admin_user)
            db.commit()
            db.refresh(admin_user)
            print(f"Created admin user: admin / admin123")
            
            # Create test user too
            test_user = models.User(
                name="Test User",
                telegram_username="test", 
                hashed_password=get_password_hash("test123"),
                role=models.RoleEnum.manager,
                is_active=True
            )
            db.add(test_user)
            db.commit()
            db.refresh(test_user)
            print(f"Created test user: test / test123")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    main()
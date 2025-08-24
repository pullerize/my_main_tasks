#!/usr/bin/env python3
import sys
sys.path.append('./agency_backend')

from agency_backend.app.models import User, RoleEnum
from agency_backend.app.database import engine
from sqlalchemy.orm import sessionmaker

def add_smm_managers():
    """Add SMM managers to the database"""
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    
    # Default password hash for '123456'
    password_hash = '$2b$12$LQv3c1yqBWVHxkd0LHAaeOu0Ztgffq5ew8jJlif7DfI3JY0Jvh5yy'
    
    smm_users = [
        {'name': 'Сабина', 'login': 'sabina', 'role': RoleEnum.head_smm},
        {'name': 'Севинч', 'login': 'sevinch', 'role': RoleEnum.smm_manager},
        {'name': 'Амалия', 'login': 'amaliya', 'role': RoleEnum.smm_manager},
        {'name': 'Зарина', 'login': 'zarina', 'role': RoleEnum.smm_manager},
    ]
    
    try:
        for user_data in smm_users:
            # Check if user already exists
            existing = session.query(User).filter(User.login == user_data['login']).first()
            if not existing:
                user = User(
                    name=user_data['name'],
                    login=user_data['login'],
                    hashed_password=password_hash,
                    role=user_data['role']
                )
                session.add(user)
                print(f"Added {user_data['name']} as {user_data['role'].value}")
            else:
                print(f"{user_data['name']} already exists")
        
        session.commit()
        print("\nSMM managers added successfully!")
        
        # Show all users
        print("\nAll users in the system:")
        users = session.query(User).all()
        for u in users:
            print(f"  {u.name} - Role: {u.role.value}, Login: {u.login}")
            
    except Exception as e:
        print(f"Error: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    add_smm_managers()
from datetime import datetime, timedelta
from typing import Optional
import os
import secrets

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from . import models, schemas
from .database import SessionLocal

# Load from environment or generate secure random key
SECRET_KEY = os.getenv("SECRET_KEY", secrets.token_urlsafe(32))
if SECRET_KEY == "CHANGE_ME" or len(SECRET_KEY) < 32:
    raise ValueError("SECRET_KEY must be set to a secure random string of at least 32 characters")

ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))

# Используем Argon2 и PBKDF2 (без bcrypt из-за проблем совместимости)
pwd_context = CryptContext(
    schemes=["argon2", "pbkdf2_sha256"],
    deprecated="auto",
    argon2__memory_cost=65536,
    argon2__time_cost=3,
    argon2__parallelism=4,
)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def verify_password(plain_password, hashed_password):
    try:
        if not hashed_password:
            return False
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        print(f"Password verification error: {e}")
        print(f"Hash format: '{hashed_password}'")
        return False


def get_password_hash(password):
    # bcrypt has 72 byte limit - truncate if necessary
    if len(password.encode('utf-8')) > 72:
        password = password[:72]
    return pwd_context.hash(password)


def get_user(db: Session, username: str):
    return db.query(models.User).filter(models.User.telegram_username == username).first()


def authenticate_user(db: Session, username: str, password: str):
    # Validate input
    if not username or not password:
        return None
    if len(username) > 100 or len(password) > 200:
        return None
    
    user = get_user(db, username)
    if not user:
        # Perform dummy password verification to prevent timing attacks
        pwd_context.verify("dummy_password", "$2b$12$dummy.hash.to.prevent.timing.attacks")
        return None
    
    if not verify_password(password, user.hashed_password):
        return None
    
    # Check if user is inactive
    if user.role == models.RoleEnum.inactive or not user.is_active:
        return None
    
    return user


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "iat": datetime.utcnow()})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = get_user(db, username)
    if user is None:
        raise credentials_exception
    return user


def get_current_active_user(current_user: models.User = Depends(get_current_user)):
    # Check if user is inactive (either by role or is_active flag)
    if current_user.role == models.RoleEnum.inactive or not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    return current_user


def get_current_admin_user(current_user: models.User = Depends(get_current_active_user)):
    # Check if user is admin
    if current_user.role != models.RoleEnum.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user

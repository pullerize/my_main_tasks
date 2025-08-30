import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

def get_database_url():
    """Динамически формируем DATABASE_URL на основе DB_ENGINE"""
    db_engine = os.getenv("DB_ENGINE", "sqlite")
    
    if db_engine == "postgresql":
        # PostgreSQL для продакшена
        host = os.getenv("POSTGRES_HOST", "db")
        port = os.getenv("POSTGRES_PORT", "5432")
        db = os.getenv("POSTGRES_DB", "agency")
        user = os.getenv("POSTGRES_USER", "agency")
        password = os.getenv("POSTGRES_PASSWORD", "")
        return f"postgresql://{user}:{password}@{host}:{port}/{db}"
    else:
        # SQLite для разработки
        sqlite_path = os.getenv("SQLITE_PATH", "/data/agency/db/app.db")
        # Создаем директорию если не существует
        os.makedirs(os.path.dirname(sqlite_path), exist_ok=True)
        return f"sqlite:///{sqlite_path}"

SQLALCHEMY_DATABASE_URL = get_database_url()

# Настройки подключения в зависимости от типа БД
if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL, 
        connect_args={"check_same_thread": False}
    )
else:
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

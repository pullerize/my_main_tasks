#!/usr/bin/env python3
"""
Миграция: Добавление поля project_id в таблицу employee_expenses

Использование:
    python3 migrate_add_project_id.py
"""
import os
import sys
from pathlib import Path

# Добавляем путь к модулям backend
sys.path.insert(0, str(Path(__file__).parent / "agency_backend"))

from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

DB_ENGINE = os.getenv("DB_ENGINE", "sqlite")

if DB_ENGINE == "postgresql":
    import psycopg2
    from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

    # PostgreSQL подключение
    conn = psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=os.getenv("POSTGRES_PORT", "5432"),
        dbname=os.getenv("POSTGRES_DB", "agency"),
        user=os.getenv("POSTGRES_USER", "agency"),
        password=os.getenv("POSTGRES_PASSWORD", "")
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cursor = conn.cursor()

    # Проверяем, есть ли поле project_id
    cursor.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'employee_expenses' AND column_name = 'project_id'
    """)

    if cursor.fetchone():
        print("✅ Поле project_id уже существует в таблице employee_expenses (PostgreSQL)")
    else:
        print("❌ Поле project_id отсутствует. Добавляем... (PostgreSQL)")
        cursor.execute("""
            ALTER TABLE employee_expenses
            ADD COLUMN project_id INTEGER REFERENCES projects(id)
        """)
        print("✅ Поле project_id успешно добавлено! (PostgreSQL)")

    cursor.close()
    conn.close()

else:
    import sqlite3

    # SQLite подключение
    db_path = os.getenv("SQLITE_PATH", "/home/pullerize/8bit_db/shared_database.db")
    conn = sqlite3.connect(db_path)

    try:
        # Проверяем, есть ли уже поле project_id
        cursor = conn.execute("PRAGMA table_info(employee_expenses)")
        columns = [col[1] for col in cursor.fetchall()]

        if 'project_id' in columns:
            print("✅ Поле project_id уже существует в таблице employee_expenses (SQLite)")
        else:
            print("❌ Поле project_id отсутствует. Добавляем... (SQLite)")

            # Добавляем поле project_id
            conn.execute("""
                ALTER TABLE employee_expenses
                ADD COLUMN project_id INTEGER REFERENCES projects(id)
            """)
            conn.commit()

            print("✅ Поле project_id успешно добавлено! (SQLite)")

            # Проверяем результат
            cursor = conn.execute("PRAGMA table_info(employee_expenses)")
            print("\nОбновленная структура таблицы:")
            for col in cursor.fetchall():
                print(f"  {col[1]}: {col[2]}")

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()

print("\n✅ Миграция завершена!")

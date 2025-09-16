#!/usr/bin/env python3

"""
Комплексное исправление всех таблиц CRM (leads)
"""

import sqlite3
import os
from datetime import datetime

# Путь к базе данных
DB_PATH = "shared_database.db"

def fix_leads_tables():
    """Исправляет все таблицы связанные с CRM"""

    if not os.path.exists(DB_PATH):
        print(f"❌ База данных {DB_PATH} не найдена!")
        return False

    print(f"🔄 Исправляем все CRM таблицы в базе данных {DB_PATH}...")

    # Создаем резервную копию
    backup_path = f"{DB_PATH}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    try:
        import shutil
        shutil.copy2(DB_PATH, backup_path)
        print(f"✅ Создана резервная копия: {backup_path}")
    except Exception as e:
        print(f"⚠️  Не удалось создать резервную копию: {e}")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Проверяем существование основных таблиц
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'lead%'")
        existing_tables = [row[0] for row in cursor.fetchall()]
        print(f"📋 Найденные CRM таблицы: {existing_tables}")

        # Создаем недостающие таблицы, если они отсутствуют
        tables_to_create = [
            ('leads', '''
            CREATE TABLE IF NOT EXISTS leads (
                id INTEGER PRIMARY KEY,
                title VARCHAR NOT NULL,
                source VARCHAR NOT NULL,
                status VARCHAR DEFAULT 'new',
                manager_id INTEGER,
                client_name VARCHAR,
                client_contact VARCHAR,
                company_name VARCHAR,
                description TEXT,
                proposal_amount FLOAT,
                proposal_date DATETIME,
                deal_amount FLOAT,
                rejection_reason TEXT,
                created_at DATETIME,
                updated_at DATETIME,
                last_activity_at DATETIME,
                reminder_date DATETIME,
                waiting_started_at DATETIME,
                FOREIGN KEY (manager_id) REFERENCES users (id)
            )
            '''),
            ('lead_notes', '''
            CREATE TABLE IF NOT EXISTS lead_notes (
                id INTEGER PRIMARY KEY,
                lead_id INTEGER,
                user_id INTEGER,
                content TEXT NOT NULL,
                lead_status VARCHAR,
                created_at DATETIME,
                FOREIGN KEY (lead_id) REFERENCES leads (id),
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
            '''),
            ('lead_attachments', '''
            CREATE TABLE IF NOT EXISTS lead_attachments (
                id INTEGER PRIMARY KEY,
                lead_id INTEGER,
                user_id INTEGER,
                filename VARCHAR NOT NULL,
                file_path VARCHAR NOT NULL,
                file_size INTEGER,
                mime_type VARCHAR,
                uploaded_at DATETIME,
                FOREIGN KEY (lead_id) REFERENCES leads (id),
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
            '''),
            ('lead_history', '''
            CREATE TABLE IF NOT EXISTS lead_history (
                id INTEGER PRIMARY KEY,
                lead_id INTEGER,
                user_id INTEGER,
                action VARCHAR NOT NULL,
                old_value VARCHAR,
                new_value VARCHAR,
                description TEXT,
                created_at DATETIME,
                FOREIGN KEY (lead_id) REFERENCES leads (id),
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
            ''')
        ]

        for table_name, create_sql in tables_to_create:
            print(f"🔧 Создаем/проверяем таблицу {table_name}...")
            cursor.execute(create_sql)

        # Добавляем недостающие поля в существующие таблицы
        tables_and_fields = [
            ('lead_notes', 'lead_status', 'VARCHAR'),
            ('lead_attachments', 'user_id', 'INTEGER'),
            ('lead_attachments', 'file_size', 'INTEGER'),
            ('lead_attachments', 'mime_type', 'VARCHAR'),
        ]

        for table_name, field_name, field_type in tables_and_fields:
            # Проверяем, есть ли уже поле
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = [column[1] for column in cursor.fetchall()]

            if field_name not in columns:
                try:
                    print(f"📝 Добавляем поле {field_name} в таблицу {table_name}...")
                    cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {field_name} {field_type}")
                except Exception as e:
                    print(f"⚠️  Ошибка при добавлении поля {field_name}: {e}")
            else:
                print(f"✅ Поле {field_name} уже существует в таблице {table_name}")

        # Сохраняем изменения
        conn.commit()

        print("✅ Все CRM таблицы исправлены!")

        # Проверяем финальные структуры таблиц
        for table_name in ['leads', 'lead_notes', 'lead_attachments', 'lead_history']:
            print(f"\n📋 Структура таблицы {table_name}:")
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            for col in columns:
                print(f"  - {col[1]} ({col[2]})")

        return True

    except Exception as e:
        print(f"❌ Ошибка при выполнении исправления: {e}")
        conn.rollback()
        return False

    finally:
        conn.close()

if __name__ == "__main__":
    print("🚀 Запуск комплексного исправления CRM таблиц")

    if fix_leads_tables():
        print("\n🎉 Исправление завершено успешно!")
        print("\nТеперь можно перезапустить сервер:")
        print("cd agency_backend && python3 -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000")
    else:
        print("\n💥 Исправление завершилось с ошибкой!")
        print("Проверьте логи выше для получения подробной информации.")
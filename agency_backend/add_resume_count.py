"""
Добавление колонки resume_count в таблицу tasks
"""
import sqlite3
import os
import sys

# Fix encoding for Windows console
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'ignore')

# Путь к базе данных
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'shared_database.db')

def add_resume_count_column():
    """Добавить колонку resume_count в таблицу tasks"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Проверить, существует ли колонка
        cursor.execute("PRAGMA table_info(tasks)")
        columns = [col[1] for col in cursor.fetchall()]

        if 'resume_count' in columns:
            print("[OK] Колонка resume_count уже существует")
            return

        # Добавить колонку
        cursor.execute("ALTER TABLE tasks ADD COLUMN resume_count INTEGER DEFAULT 0")
        conn.commit()

        print("[OK] Колонка resume_count успешно добавлена в таблицу tasks")

    except Exception as e:
        print(f"[ERROR] Ошибка при добавлении колонки: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    print("[START] Начинаем миграцию базы данных...\n")
    add_resume_count_column()
import sqlite3
import os

# Путь к базе данных
db_path = "shared_database.db"

if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Проверяем, существует ли уже поле created_by_id
        cursor.execute("PRAGMA table_info(leads)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'created_by_id' not in columns:
            # Добавляем поле created_by_id
            cursor.execute("ALTER TABLE leads ADD COLUMN created_by_id INTEGER")
            print("Поле created_by_id успешно добавлено в таблицу leads")
        else:
            print("Поле created_by_id уже существует в таблице leads")
        
        conn.commit()
        
    except Exception as e:
        print(f"Ошибка при добавлении поля: {e}")
        conn.rollback()
    
    finally:
        conn.close()
else:
    print("База данных не найдена")
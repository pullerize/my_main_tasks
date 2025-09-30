"""
Миграция ролей: обновление устаревших ролей head_smm и digital
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

def migrate_roles():
    """Обновить устаревшие роли пользователей"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Получить список пользователей с устаревшими ролями
        cursor.execute("SELECT id, name, role FROM users WHERE role IN ('head_smm', 'digital')")
        users = cursor.fetchall()

        if not users:
            print("✅ Нет пользователей с устаревшими ролями")
            return

        print(f"Найдено {len(users)} пользователей с устаревшими ролями:")
        for user_id, name, role in users:
            print(f"  - {name} (ID: {user_id}): {role}")

        # Обновить роли
        # head_smm -> smm_manager (главный SMM становится обычным менеджером)
        # digital -> admin (digital специалисты становятся админами для доступа ко всем функциям)

        cursor.execute("UPDATE users SET role = 'smm_manager' WHERE role = 'head_smm'")
        head_smm_updated = cursor.rowcount

        cursor.execute("UPDATE users SET role = 'admin' WHERE role = 'digital'")
        digital_updated = cursor.rowcount

        conn.commit()

        print(f"\n✅ Миграция завершена:")
        print(f"   - head_smm -> smm_manager: {head_smm_updated} пользователей")
        print(f"   - digital -> admin: {digital_updated} пользователей")

        # Проверка результата
        cursor.execute("SELECT id, name, role FROM users WHERE role IN ('head_smm', 'digital')")
        remaining = cursor.fetchall()

        if remaining:
            print(f"\n⚠️ Остались пользователи с устаревшими ролями: {remaining}")
        else:
            print("\n✅ Все устаревшие роли успешно обновлены")

    except Exception as e:
        print(f"❌ Ошибка при миграции: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    print("🔧 Начинаем миграцию ролей пользователей...\n")
    migrate_roles()
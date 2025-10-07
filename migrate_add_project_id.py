#!/usr/bin/env python3
"""
Миграция: Добавление поля project_id в таблицу employee_expenses

Использование:
    python3 migrate_add_project_id.py [--db-type=sqlite|postgresql] [--db-path=/path/to/db]
"""
import os
import sys
import argparse

# Парсим аргументы командной строки
parser = argparse.ArgumentParser(description='Миграция базы данных: добавление project_id')
parser.add_argument('--db-type', default='sqlite', choices=['sqlite', 'postgresql'],
                    help='Тип базы данных (по умолчанию: sqlite)')
parser.add_argument('--db-path', default='/var/lib/8bit-codex/shared_database.db',
                    help='Путь к SQLite базе данных (по умолчанию: /var/lib/8bit-codex/shared_database.db)')
parser.add_argument('--postgres-host', default='localhost', help='PostgreSQL host')
parser.add_argument('--postgres-port', default='5432', help='PostgreSQL port')
parser.add_argument('--postgres-db', default='agency', help='PostgreSQL database name')
parser.add_argument('--postgres-user', default='agency', help='PostgreSQL username')
parser.add_argument('--postgres-password', default='', help='PostgreSQL password')

args = parser.parse_args()

DB_ENGINE = args.db_type

if DB_ENGINE == "postgresql":
    import psycopg2
    from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

    # PostgreSQL подключение
    conn = psycopg2.connect(
        host=args.postgres_host,
        port=args.postgres_port,
        dbname=args.postgres_db,
        user=args.postgres_user,
        password=args.postgres_password
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

    # SQLite подключение - пробуем найти базу данных
    possible_paths = [
        args.db_path,
        "/var/lib/8bit-codex/shared_database.db",
        "/opt/8bit-codex/shared_database.db",
        "/home/pullerize/8bit_db/shared_database.db",
        "./shared_database.db",
        "../shared_database.db",
    ]

    db_path = None
    for path in possible_paths:
        if os.path.exists(path):
            db_path = path
            break

    if not db_path:
        print("❌ Файл базы данных не найден!")
        print("\nПроверены следующие пути:")
        for path in possible_paths:
            print(f"  - {path}")
        print("\nПожалуйста, укажите правильный путь с помощью --db-path")
        sys.exit(1)

    print(f"✓ Найдена SQLite база: {db_path}")
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

import sqlite3

# SQL для создания таблиц лидов
create_leads_table = """
CREATE TABLE IF NOT EXISTS leads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title VARCHAR NOT NULL,
    source VARCHAR NOT NULL,
    status VARCHAR DEFAULT 'new',
    manager_id INTEGER,
    created_by_id INTEGER,
    client_name VARCHAR,
    client_contact VARCHAR,
    company_name VARCHAR,
    description TEXT,
    proposal_amount REAL,
    proposal_date DATETIME,
    deal_amount REAL,
    rejection_reason TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_activity_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    reminder_date DATETIME,
    waiting_started_at DATETIME,
    FOREIGN KEY (manager_id) REFERENCES users(id),
    FOREIGN KEY (created_by_id) REFERENCES users(id)
);
"""

create_lead_notes_table = """
CREATE TABLE IF NOT EXISTS lead_notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lead_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    content TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (lead_id) REFERENCES leads(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
"""

create_lead_attachments_table = """
CREATE TABLE IF NOT EXISTS lead_attachments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lead_id INTEGER NOT NULL,
    filename VARCHAR NOT NULL,
    original_filename VARCHAR NOT NULL,
    file_size INTEGER,
    mime_type VARCHAR,
    uploaded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (lead_id) REFERENCES leads(id) ON DELETE CASCADE
);
"""

create_lead_history_table = """
CREATE TABLE IF NOT EXISTS lead_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lead_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    action VARCHAR NOT NULL,
    old_value VARCHAR,
    new_value VARCHAR,
    description VARCHAR,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (lead_id) REFERENCES leads(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
"""

# Подключение к базе данных и выполнение SQL
conn = sqlite3.connect('shared_database.db')
cursor = conn.cursor()

try:
    cursor.execute(create_leads_table)
    cursor.execute(create_lead_notes_table)
    cursor.execute(create_lead_attachments_table)
    cursor.execute(create_lead_history_table)
    
    conn.commit()
    print("✅ Все таблицы лидов созданы успешно!")
    
    # Проверяем созданные таблицы
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%lead%'")
    lead_tables = cursor.fetchall()
    print("📋 Созданные таблицы лидов:", [table[0] for table in lead_tables])
    
except Exception as e:
    print(f"❌ Ошибка при создании таблиц: {e}")
    conn.rollback()

finally:
    conn.close()
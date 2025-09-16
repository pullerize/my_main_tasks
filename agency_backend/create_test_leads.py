import sqlite3
from datetime import datetime

# Подключение к базе данных
conn = sqlite3.connect('shared_database.db')
cursor = conn.cursor()

try:
    # Сначала получаем пользователей для связи
    cursor.execute("SELECT id, name FROM users LIMIT 3")
    users = cursor.fetchall()
    
    if not users:
        print("❌ В базе данных нет пользователей. Создайте пользователя сначала.")
        exit()
    
    print(f"📋 Найдено пользователей: {len(users)}")
    
    # Создаем тестовые лиды
    test_leads = [
        {
            'title': 'Заявка от ООО Рога и Копыта',
            'source': 'instagram',
            'status': 'new',
            'manager_id': users[0][0],
            'created_by_id': users[0][0],  # тот же пользователь создал и менеджерит
            'client_name': 'Иван Петров',
            'client_contact': '+998 90 123 45 67',
            'company_name': 'ООО Рога и Копыта',
            'description': 'Нужна разработка корпоративного сайта'
        },
        {
            'title': 'Заявка от Барбершоп Лев',
            'source': 'facebook',
            'status': 'in_progress',
            'manager_id': users[0][0] if len(users) > 1 else users[0][0],
            'created_by_id': users[1][0] if len(users) > 1 else users[0][0],  # другой пользователь создал
            'client_name': 'Алексей Смирнов',
            'client_contact': '+998 91 234 56 78',
            'company_name': 'Барбершоп Лев',
            'description': 'SMM продвижение в соц.сетях'
        },
        {
            'title': 'Заявка от Кафе Уют',
            'source': 'telegram',
            'status': 'negotiation',
            'manager_id': users[0][0],
            'created_by_id': users[2][0] if len(users) > 2 else users[0][0],  # третий пользователь создал
            'client_name': 'Мария Козлова',
            'client_contact': '+998 92 345 67 89',
            'company_name': 'Кафе Уют',
            'description': 'Создание инстаграм контента'
        },
        {
            'title': 'Заявка от IT-Центр',
            'source': 'referral',
            'status': 'proposal',
            'manager_id': users[0][0],
            'created_by_id': users[1][0] if len(users) > 1 else users[0][0],
            'client_name': 'Сергей Волков',
            'client_contact': '+998 93 456 78 90',
            'company_name': 'IT-Центр',
            'description': 'Разработка мобильного приложения'
        },
        {
            'title': 'Заявка от Спортзал Титан',
            'source': 'search',
            'status': 'waiting',
            'manager_id': users[0][0],
            'created_by_id': users[0][0],
            'client_name': 'Дмитрий Орлов',
            'client_contact': '+998 94 567 89 01',
            'company_name': 'Спортзал Титан',
            'description': 'Создание лендинга'
        },
        {
            'title': 'Заявка от Медицинский центр',
            'source': 'instagram', 
            'status': 'new',
            'manager_id': users[0][0],
            'created_by_id': users[2][0] if len(users) > 2 else users[0][0],
            'client_name': 'Елена Сидорова', 
            'client_contact': '+998 95 678 90 12',
            'company_name': 'Медицинский центр Здоровье',
            'description': 'Таргетированная реклама'
        }
    ]
    
    # Вставляем тестовые данные
    for lead in test_leads:
        cursor.execute("""
            INSERT INTO leads (
                title, source, status, manager_id, created_by_id,
                client_name, client_contact, company_name, description,
                created_at, updated_at, last_activity_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            lead['title'], lead['source'], lead['status'], 
            lead['manager_id'], lead['created_by_id'],
            lead['client_name'], lead['client_contact'], 
            lead['company_name'], lead['description'],
            datetime.now(), datetime.now(), datetime.now()
        ))
    
    conn.commit()
    print(f"✅ Создано {len(test_leads)} тестовых лидов!")
    
    # Проверяем созданные лиды
    cursor.execute("""
        SELECT l.id, l.company_name, l.status, u1.name as manager, u2.name as creator
        FROM leads l 
        LEFT JOIN users u1 ON l.manager_id = u1.id
        LEFT JOIN users u2 ON l.created_by_id = u2.id
        ORDER BY l.id
    """)
    
    leads = cursor.fetchall()
    print("\n📋 Созданные лиды:")
    for lead in leads:
        print(f"  ID: {lead[0]}, Компания: {lead[1]}, Статус: {lead[2]}, Менеджер: {lead[3]}, Создал: {lead[4]}")
        
except Exception as e:
    print(f"❌ Ошибка: {e}")
    conn.rollback()

finally:
    conn.close()
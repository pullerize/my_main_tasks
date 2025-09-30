"""
Исправляет функцию clear_database, упрощая её и убирая проблемные места
"""

import re

# Читаем файл
with open('app/main.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Заменяем все проблемные паттерны на простые версии без scalar()
# Паттерн 1: result = db.execute(text("SELECT COUNT(*) FROM table_name"))
#            deleted_counts["key"] = result.scalar() or 0
pattern1 = r'result = db\.execute\(text\("SELECT COUNT\(\*\) FROM (\w+)"\)\)\s+deleted_counts\["([^"]+)"\] = result\.scalar\(\) or 0'
replacement1 = r'try:\n                    deleted_counts["\2"] = db.execute(text("SELECT COUNT(*) FROM \1")).fetchone()[0]\n                except:\n                    deleted_counts["\2"] = 0'

content = re.sub(pattern1, replacement1, content)

# Паттерн 2: count = result.scalar()
#            deleted_counts["key"] = count if count else 0
pattern2 = r'result = db\.execute\(text\("SELECT COUNT\(\*\) FROM (\w+)"\)\)\s+count = result\.scalar\(\)\s+deleted_counts\["([^"]+)"\] = count if count else 0'
replacement2 = r'try:\n                    deleted_counts["\2"] = db.execute(text("SELECT COUNT(*) FROM \1")).fetchone()[0]\n                except:\n                    deleted_counts["\2"] = 0'

content = re.sub(pattern2, replacement2, content)

# Сохраняем исправленный файл
with open('app/main.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("[OK] Файл main.py исправлен")
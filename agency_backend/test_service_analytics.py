#!/usr/bin/env python3
import sys
import os
import json
sys.path.append('.')

# Настраиваем переменную окружения для базы данных
os.environ['SQLITE_PATH'] = '/mnt/c/Users/Господин/Desktop/Мои проекты/8bit_tasks/8bit-codex/agency_backend/shared_database.db'

from app import crud, models
from app.database import SessionLocal

def test_service_analytics():
    """Тестируем функцию аналитики типов услуг"""
    db = SessionLocal()

    try:
        print('🧪 Testing service types analytics function...')

        # Тестируем функцию без фильтров
        result = crud.get_service_types_analytics(db)

        print(f'📊 Raw analytics result:')
        print(json.dumps(result, indent=2, ensure_ascii=False))

        # Проверяем структуру данных
        if 'employees' in result:
            for employee in result['employees']:
                print(f'\n👤 Employee: {employee["employee_name"]} (ID: {employee["employee_id"]})')
                print(f'   Total: {employee["total_created"]} created, {employee["total_completed"]} completed')
                print(f'   Efficiency: {employee["overall_efficiency"]}%')

                for service in employee['service_types']:
                    print(f'   📋 Service "{service["service_type"]}": {service["created"]} created, {service["completed"]} completed ({service["efficiency"]}%)')

    except Exception as e:
        print(f'❌ Error: {e}')
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == '__main__':
    test_service_analytics()
"""
Создаёт упрощённую версию функции clear_database
"""

clear_database_simplified = '''
@app.delete("/admin/clear-database")
async def clear_database(
    db: Session = Depends(auth.get_db),
    current: models.User = Depends(auth.get_current_active_user),
):
    """Полная очистка базы данных (кроме текущего админа)"""
    if current.role != models.RoleEnum.admin:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    try:
        # Простая версия - удаляем данные без подсчёта

        # Удаляем задачи
        db.query(models.Task).delete()

        # Удаляем проекты
        if hasattr(models, 'Project'):
            db.query(models.Project).delete()

        # Удаляем digital проекты
        if hasattr(models, 'DigitalProject'):
            db.query(models.DigitalProject).delete()

        # Удаляем операторов
        if hasattr(models, 'Operator'):
            db.query(models.Operator).delete()

        # Удаляем расходы
        if hasattr(models, 'Expense'):
            db.query(models.Expense).delete()

        # Удаляем всех пользователей кроме текущего админа
        db.query(models.User).filter(models.User.id != current.id).delete()

        # Сохраняем изменения
        db.commit()

        return {
            "success": True,
            "message": "Database cleared successfully"
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Clear failed: {str(e)}")
'''

print(clear_database_simplified)
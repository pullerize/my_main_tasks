"""
Новая упрощённая версия функции clear_database
"""

NEW_FUNCTION = '''@app.delete("/admin/clear-database")
async def clear_database(
    db: Session = Depends(auth.get_db),
    current: models.User = Depends(auth.get_current_active_user),
):
    """Полная очистка базы данных (кроме текущего админа)"""
    if current.role != models.RoleEnum.admin:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    try:
        # Счетчики для отчета (упрощённая версия)
        deleted_counts = {}

        # Удаляем задачи
        if hasattr(models, 'Task'):
            count = db.query(models.Task).count()
            deleted_counts["tasks"] = count
            db.query(models.Task).delete()

        # Удаляем посты проектов
        if hasattr(models, 'ProjectPost'):
            count = db.query(models.ProjectPost).count()
            deleted_counts["posts"] = count
            db.query(models.ProjectPost).delete()

        # Удаляем съемки
        if hasattr(models, 'Shooting'):
            count = db.query(models.Shooting).count()
            deleted_counts["shootings"] = count
            db.query(models.Shooting).delete()

        # Удаляем все типы расходов
        if hasattr(models, 'ProjectExpense'):
            count = db.query(models.ProjectExpense).count()
            deleted_counts["project_expenses"] = count
            db.query(models.ProjectExpense).delete()

        if hasattr(models, 'ProjectClientExpense'):
            count = db.query(models.ProjectClientExpense).count()
            deleted_counts["project_client_expenses"] = count
            db.query(models.ProjectClientExpense).delete()

        if hasattr(models, 'EmployeeExpense'):
            count = db.query(models.EmployeeExpense).count()
            deleted_counts["employee_expenses"] = count
            db.query(models.EmployeeExpense).delete()

        if hasattr(models, 'DigitalProjectExpense'):
            count = db.query(models.DigitalProjectExpense).count()
            deleted_counts["digital_project_expenses"] = count
            db.query(models.DigitalProjectExpense).delete()

        # Удаляем поступления
        if hasattr(models, 'ProjectReceipt'):
            count = db.query(models.ProjectReceipt).count()
            deleted_counts["receipts"] = count
            db.query(models.ProjectReceipt).delete()

        # Удаляем отчеты по проектам
        if hasattr(models, 'ProjectReport'):
            count = db.query(models.ProjectReport).count()
            deleted_counts["project_reports"] = count
            db.query(models.ProjectReport).delete()

        # Удаляем цифровые проекты и связанные данные
        if hasattr(models, 'DigitalProjectTask'):
            db.query(models.DigitalProjectTask).delete()
        if hasattr(models, 'DigitalProjectFinance'):
            db.query(models.DigitalProjectFinance).delete()
        if hasattr(models, 'DigitalProject'):
            count = db.query(models.DigitalProject).count()
            deleted_counts["digital_projects"] = count
            db.query(models.DigitalProject).delete()
        if hasattr(models, 'DigitalService'):
            db.query(models.DigitalService).delete()

        # Удаляем проекты
        if hasattr(models, 'Project'):
            count = db.query(models.Project).count()
            deleted_counts["projects"] = count
            db.query(models.Project).delete()

        # Удаляем операторов
        if hasattr(models, 'Operator'):
            count = db.query(models.Operator).count()
            deleted_counts["operators"] = count
            db.query(models.Operator).delete()

        # Удаляем заявки и связанные данные (используем прямые SQL запросы для таблиц с проблемами)
        try:
            # Удаляем историю заявок
            db.execute(text("DELETE FROM lead_history"))
            deleted_counts["lead_history"] = 0
        except:
            pass

        try:
            # Удаляем вложения заявок
            db.execute(text("DELETE FROM lead_attachments"))
            deleted_counts["lead_attachments"] = 0
        except:
            pass

        try:
            # Удаляем заметки заявок
            db.execute(text("DELETE FROM lead_notes"))
            deleted_counts["lead_notes"] = 0
        except:
            pass

        try:
            # Удаляем заявки
            db.execute(text("DELETE FROM leads"))
            deleted_counts["leads"] = 0
        except:
            pass

        # Удаляем повторяющиеся задачи
        try:
            db.execute(text("DELETE FROM recurring_tasks"))
            deleted_counts["recurring_tasks"] = 0
        except:
            pass

        # Удаляем всех пользователей кроме текущего админа
        if hasattr(models, 'User'):
            count = db.query(models.User).filter(models.User.id != current.id).count()
            deleted_counts["users"] = count
            db.query(models.User).filter(models.User.id != current.id).delete()

        # Удаляем настройки (кроме timezone)
        if hasattr(models, 'Setting'):
            db.query(models.Setting).filter(
                models.Setting.key.notin_(["timezone"])
            ).delete()

        # Очищаем все папки с файлами
        file_directories = [
            "uploads/leads",
            "static/projects",
            "static/digital",
            "files",
            "contracts"
        ]

        cleared_files = 0
        for dir_path in file_directories:
            if os.path.exists(dir_path):
                try:
                    for root, dirs, files in os.walk(dir_path):
                        for file_name in files:
                            file_path = os.path.join(root, file_name)
                            try:
                                os.remove(file_path)
                                cleared_files += 1
                            except:
                                pass
                except:
                    pass

        deleted_counts["files"] = cleared_files

        # Сохраняем изменения
        db.commit()

        # Пересоздаем дефолтные налоги
        if hasattr(crud, 'create_tax'):
            crud.create_tax(db, "ЯТТ", 0.95)
            crud.create_tax(db, "ООО", 0.83)
            crud.create_tax(db, "Нал", 1.0)

        return {
            "success": True,
            "message": "Database cleared successfully",
            "deleted": deleted_counts
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Clear failed: {str(e)}")'''

print(NEW_FUNCTION)
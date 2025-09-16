from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from datetime import datetime, timedelta
import json

from . import models, schemas, auth
from .models import get_local_time_utc5


def get_setting(db: Session, key: str, default: str = None) -> Optional[str]:
    """Получить значение настройки по ключу"""
    setting = db.query(models.Setting).filter(models.Setting.key == key).first()
    return setting.value if setting else default


def set_setting(db: Session, key: str, value: str):
    """Установить значение настройки"""
    setting = db.query(models.Setting).filter(models.Setting.key == key).first()
    if setting:
        setting.value = value
    else:
        setting = models.Setting(key=key, value=value)
        db.add(setting)
    db.commit()


def calculate_next_run_at(recurrence_type: str, db: Session = None, generation_time: str = None, recurrence_days: str = None) -> datetime:
    """Рассчитывает следующее время запуска для повторяющихся задач"""
    base_date = datetime.now()
    
    # Получаем время генерации
    target_time = generation_time
    if not target_time and db:
        target_time = get_setting(db, 'recurring_task_generation_time', '11:19')
    
    # Парсим время
    target_hour, target_minute = 11, 19  # значение по умолчанию
    if target_time:
        try:
            target_hour, target_minute = map(int, target_time.split(':'))
        except (ValueError, AttributeError):
            pass
    
    # Парсим дни
    allowed_days = []
    if recurrence_days:
        try:
            allowed_days = [int(d.strip()) for d in recurrence_days.split(',') if d.strip()]
        except ValueError:
            pass
    
    if recurrence_type == "daily":
        # Для ежедневных задач учитываем дни недели (1=Понедельник, 7=Воскресенье)
        current_date = base_date.replace(hour=target_hour, minute=target_minute, second=0, microsecond=0)
        
        if allowed_days:
            # Ищем следующий подходящий день
            for i in range(7):  # Максимум 7 дней проверяем
                check_date = current_date + timedelta(days=i)
                weekday = check_date.isoweekday()  # 1=Monday, 7=Sunday
                
                if weekday in allowed_days:
                    if check_date > base_date:  # Время еще не прошло
                        return check_date
        else:
            # Если дни не указаны, работаем как раньше - каждый день
            if base_date < current_date:
                return current_date
            else:
                return current_date + timedelta(days=1)
    
    elif recurrence_type == "weekly":
        # Для еженедельных задач тоже учитываем дни недели
        current_date = base_date.replace(hour=target_hour, minute=target_minute, second=0, microsecond=0)
        
        if allowed_days:
            # Ищем следующий подходящий день в пределах недели
            for i in range(7):
                check_date = current_date + timedelta(days=i)
                weekday = check_date.isoweekday()
                
                if weekday in allowed_days and check_date > base_date:
                    return check_date
            
            # Если не найден в этой неделе, ищем в следующей
            for i in range(7, 14):
                check_date = current_date + timedelta(days=i)
                weekday = check_date.isoweekday()
                
                if weekday in allowed_days:
                    return check_date
        else:
            # Если дни не указаны, каждую неделю
            if base_date < current_date:
                return current_date
            else:
                return current_date + timedelta(weeks=1)
    
    elif recurrence_type == "monthly":
        # Для месячных задач учитываем день месяца
        if allowed_days and len(allowed_days) > 0:
            target_day = allowed_days[0]  # Берем первый день из списка
            
            # Попробуем этот месяц
            try:
                current_month_date = base_date.replace(day=target_day, hour=target_hour, minute=target_minute, second=0, microsecond=0)
                if current_month_date > base_date:
                    return current_month_date
            except ValueError:
                pass  # День не существует в текущем месяце
            
            # Попробуем следующий месяц
            if base_date.month == 12:
                next_month = base_date.replace(year=base_date.year + 1, month=1)
            else:
                next_month = base_date.replace(month=base_date.month + 1)
            
            try:
                next_month_date = next_month.replace(day=target_day, hour=target_hour, minute=target_minute, second=0, microsecond=0)
                return next_month_date
            except ValueError:
                # Если день не существует (например, 31 число в феврале), берем последний день месяца
                import calendar
                last_day = calendar.monthrange(next_month.year, next_month.month)[1]
                return next_month.replace(day=min(target_day, last_day), hour=target_hour, minute=target_minute, second=0, microsecond=0)
        else:
            # Если день не указан, каждый месяц в тот же день
            current_date = base_date.replace(hour=target_hour, minute=target_minute, second=0, microsecond=0)
            if base_date < current_date:
                return current_date
            else:
                return current_date + timedelta(days=30)
    
    return None


def get_user(db: Session, user_id: int) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.id == user_id).first()


def get_user_by_login(db: Session, login: str) -> Optional[models.User]:
    # Now using telegram_username instead of login
    return db.query(models.User).filter(models.User.telegram_username == login).first()


def create_user(db: Session, user: schemas.UserCreate) -> models.User:
    hashed_password = auth.get_password_hash(user.password)
    # Нормализуем telegram_username к нижнему регистру для корректной работы с Telegram ботом
    telegram_username = user.telegram_username.lower() if user.telegram_username else None
    db_user = models.User(
        telegram_username=telegram_username,
        name=user.name,
        hashed_password=hashed_password,
        role=user.role,
        birth_date=user.birth_date,
        is_active=True,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def get_users(db: Session) -> List[models.User]:
    return db.query(models.User).all()


def update_user(db: Session, user_id: int, user: schemas.UserUpdate) -> Optional[models.User]:
    db_user = get_user(db, user_id)
    if not db_user:
        return None
    if user.telegram_username is not None:
        db_user.telegram_username = user.telegram_username
    if user.name is not None:
        db_user.name = user.name
    if user.password is not None:
        db_user.hashed_password = auth.get_password_hash(user.password)
    if user.role is not None:
        db_user.role = user.role
    if user.birth_date is not None:
        db_user.birth_date = user.birth_date
    db.commit()
    db.refresh(db_user)
    return db_user


def delete_user(db: Session, user_id: int) -> None:
    user = get_user(db, user_id)
    if user:
        db.delete(user)
        db.commit()


def authorize_telegram_user(db: Session, telegram_id: int, username: Optional[str] = None) -> Optional[models.User]:
    """Авторизация пользователя Telegram через API (только по @username)"""
    user = None

    if username:
        # Сначала ищем по точному совпадению telegram_username
        user = db.query(models.User).filter(
            models.User.telegram_username == username.lower(),
            models.User.is_active == True
        ).first()

        # Если не найден, ищем case-insensitive
        if not user:
            user = db.query(models.User).filter(
                models.User.telegram_username.ilike(username),
                models.User.is_active == True
            ).first()

    # Если пользователь найден по @username - даем доступ
    if user:
        # Обновляем telegram_id если он изменился
        if user.telegram_id != telegram_id:
            user.telegram_id = telegram_id
            user.telegram_registered_at = models.get_local_time_utc5()
            db.commit()
            db.refresh(user)
        return user

    return None


def check_telegram_user_status(db: Session, telegram_id: Optional[int] = None, username: Optional[str] = None) -> Optional[models.User]:
    """Проверить текущий статус пользователя в реальном времени (только по @username)"""
    if not username:
        return None

    # Поиск только по telegram_username
    user = db.query(models.User).filter(
        models.User.telegram_username == username.lower(),
        models.User.is_active == True
    ).first()

    # Case-insensitive поиск если точное совпадение не найдено
    if not user:
        user = db.query(models.User).filter(
            models.User.telegram_username.ilike(username),
            models.User.is_active == True
        ).first()

    return user


def get_operators(db: Session) -> List[models.Operator]:
    return db.query(models.Operator).all()


def create_operator(db: Session, operator: schemas.OperatorCreate) -> models.Operator:
    op = models.Operator(
        name=operator.name,
        role=operator.role,
        color=operator.color or "#ff0000",
        price_per_video=operator.price_per_video or 0,
        is_salaried=operator.is_salaried or False,
        monthly_salary=operator.monthly_salary,
    )
    db.add(op)
    db.commit()
    db.refresh(op)
    return op


def update_operator(db: Session, operator_id: int, operator: schemas.OperatorCreate) -> Optional[models.Operator]:
    op = db.query(models.Operator).filter(models.Operator.id == operator_id).first()
    if not op:
        return None
    op.name = operator.name
    op.role = operator.role
    if operator.color is not None:
        op.color = operator.color
    if operator.price_per_video is not None:
        op.price_per_video = operator.price_per_video
    if operator.is_salaried is not None:
        op.is_salaried = operator.is_salaried
    if operator.monthly_salary is not None:
        op.monthly_salary = operator.monthly_salary
    db.commit()
    db.refresh(op)
    return op


def delete_operator(db: Session, operator_id: int) -> None:
    op = db.query(models.Operator).filter(models.Operator.id == operator_id).first()
    if op:
        db.delete(op)
        db.commit()


def get_tasks(db: Session, skip: int = 0, limit: int = 100) -> List[models.Task]:
    return db.query(models.Task).offset(skip).limit(limit).all()


def get_tasks_for_user(db: Session, user: models.User, skip: int = 0, limit: int = 100) -> List[models.Task]:
    q = db.query(models.Task).join(models.User, models.Task.executor_id == models.User.id)
    if user.role == models.RoleEnum.admin:
        pass
    elif user.role == models.RoleEnum.smm_manager:
        q = q.filter(
            models.User.role.in_(
                [models.RoleEnum.designer, models.RoleEnum.smm_manager]
            )
        )
    elif user.role == models.RoleEnum.designer:
        q = q.filter(models.User.role == models.RoleEnum.designer)
    return q.order_by(models.Task.created_at.desc()).offset(skip).limit(limit).all()



def create_task(db: Session, task: schemas.TaskCreate, author_id: int) -> models.Task:
    deadline = task.deadline
    
    # Рассчитываем next_run_at для повторяющихся задач
    next_run_at = None
    if task.is_recurring and task.recurrence_type:
        next_run_at = calculate_next_run_at(task.recurrence_type, db, task.recurrence_time, task.recurrence_days)
    
    db_task = models.Task(
        title=task.title,
        description=task.description,
        project=task.project,
        deadline=deadline,
        executor_id=task.executor_id,
        author_id=author_id,
        task_type=task.task_type,
        task_format=task.task_format,
        high_priority=task.high_priority or False,
        is_recurring=task.is_recurring or False,
        recurrence_type=task.recurrence_type,
        recurrence_time=task.recurrence_time,
        recurrence_days=task.recurrence_days,
        next_run_at=next_run_at,
        created_at=datetime.utcnow(),
        status=models.TaskStatus.new,  # Новая задача всегда создается со статусом "new"
    )
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    
    return db_task



def update_task(db: Session, task_id: int, data: schemas.TaskCreate) -> Optional[models.Task]:
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not task:
        return None
    deadline = data.deadline
    task.title = data.title
    task.description = data.description
    task.project = data.project
    task.deadline = deadline
    task.executor_id = data.executor_id
    task.task_type = data.task_type
    task.task_format = data.task_format
    if data.high_priority is not None:
        task.high_priority = data.high_priority
    if data.is_recurring is not None:
        task.is_recurring = data.is_recurring
    if data.recurrence_type is not None:
        task.recurrence_type = data.recurrence_type
    if data.recurrence_time is not None:
        task.recurrence_time = data.recurrence_time
    if data.recurrence_days is not None:
        task.recurrence_days = data.recurrence_days
        
        # Пересчитываем next_run_at если изменился тип повторения, время или дни
        if task.is_recurring and task.recurrence_type:
            task.next_run_at = calculate_next_run_at(task.recurrence_type, db, task.recurrence_time, task.recurrence_days)
        else:
            task.next_run_at = None
    
    db.commit()
    db.refresh(task)
    return task


def delete_task(db: Session, task_id: int) -> None:
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if task:
        db.delete(task)
        db.commit()


def update_task_status(db: Session, task_id: int, status: str):
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if task:
        old_status = task.status

        # Преобразуем строку в TaskStatus enum
        if status == "done":
            task.status = models.TaskStatus.done
            task.finished_at = get_local_time_utc5()
        elif status == "cancelled":
            task.status = models.TaskStatus.cancelled
            task.finished_at = None
        elif status == "in_progress":
            task.status = models.TaskStatus.in_progress
            task.finished_at = None
            # Увеличиваем счетчик возобновлений если задача была завершена или отменена
            if old_status in [models.TaskStatus.done, models.TaskStatus.cancelled]:
                if task.resume_count is None:
                    task.resume_count = 0
                task.resume_count += 1
        else:
            task.status = models.TaskStatus.in_progress
            task.finished_at = None
            # Увеличиваем счетчик возобновлений если задача была завершена или отменена
            if old_status in [models.TaskStatus.done, models.TaskStatus.cancelled]:
                if task.resume_count is None:
                    task.resume_count = 0
                task.resume_count += 1

        db.commit()
        db.refresh(task)
    return task


def get_projects(db: Session, include_archived: bool = False) -> List[models.Project]:
    query = db.query(models.Project)
    if not include_archived:
        from sqlalchemy import or_
        query = query.filter(or_(models.Project.is_archived == False, models.Project.is_archived == None))
    return query.all()


def create_project(db: Session, project: schemas.ProjectCreate) -> models.Project:
    proj = models.Project(name=project.name, high_priority=project.high_priority)
    db.add(proj)
    db.commit()
    db.refresh(proj)
    return proj


def delete_project(db: Session, project_id: int) -> None:
    proj = db.query(models.Project).filter(models.Project.id == project_id).first()
    if proj:
        db.delete(proj)
        db.commit()


def update_project(db: Session, project_id: int, project: schemas.ProjectCreate) -> Optional[models.Project]:
    proj = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not proj:
        return None
    proj.name = project.name
    proj.high_priority = project.high_priority
    db.commit()
    db.refresh(proj)
    return proj


def set_project_logo(db: Session, project_id: int, logo: str | None) -> Optional[models.Project]:
    proj = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not proj:
        return None
    proj.logo = logo
    db.commit()
    db.refresh(proj)
    return proj


def update_project_info(db: Session, project_id: int, info: schemas.ProjectUpdate) -> Optional[models.Project]:
    proj = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not proj:
        return None
    if info.posts_count is not None:
        proj.posts_count = info.posts_count
    if info.start_date is not None:
        proj.start_date = info.start_date
    if info.end_date is not None:
        proj.end_date = info.end_date
    db.commit()
    db.refresh(proj)
    return proj


def get_shootings(db: Session) -> List[models.Shooting]:
    return db.query(models.Shooting).all()


def create_shooting(db: Session, shooting: schemas.ShootingCreate) -> models.Shooting:
    mlist = ','.join(map(str, shooting.managers or []))
    sh = models.Shooting(
        title=shooting.title,
        project=shooting.project,
        quantity=shooting.quantity,
        operator_id=shooting.operator_id,
        managers=mlist,
        datetime=shooting.datetime,
        end_datetime=shooting.end_datetime,
    )
    db.add(sh)
    db.commit()
    db.refresh(sh)
    return sh


def update_shooting(db: Session, sid: int, shooting: schemas.ShootingCreate) -> Optional[models.Shooting]:
    sh = db.query(models.Shooting).filter(models.Shooting.id == sid).first()
    if not sh:
        return None
    sh.title = shooting.title
    sh.project = shooting.project
    sh.quantity = shooting.quantity
    sh.operator_id = shooting.operator_id
    sh.managers = ','.join(map(str, shooting.managers or []))
    sh.datetime = shooting.datetime
    sh.end_datetime = shooting.end_datetime
    db.commit()
    db.refresh(sh)
    return sh


def delete_shooting(db: Session, sid: int) -> None:
    sh = db.query(models.Shooting).filter(models.Shooting.id == sid).first()
    if sh:
        db.delete(sh)
        db.commit()

def complete_shooting(
    db: Session,
    sid: int,
    quantity: int,
    managers: Optional[List[int]] = None,
    operators: Optional[List[int]] = None,
) -> Optional[models.Shooting]:
    sh = db.query(models.Shooting).filter(models.Shooting.id == sid).first()
    if not sh:
        return None
    sh.completed = True
    sh.completed_quantity = quantity
    sh.completed_managers = ','.join(map(str, managers or []))
    sh.completed_operators = ','.join(map(str, operators or []))
    db.commit()
    db.refresh(sh)
    return sh


def get_or_create_report(
    db: Session, project_id: int, month: int | None = None, year: int | None = None
) -> models.ProjectReport:
    now = datetime.utcnow()
    m = month or now.month
    y = year or now.year
    report = (
        db.query(models.ProjectReport)
        .filter(
            models.ProjectReport.project_id == project_id,
            models.ProjectReport.month == m,
            models.ProjectReport.year == y,
        )
        .first()
    )
    if not report:
        last = (
            db.query(models.ProjectReport)
            .filter(models.ProjectReport.project_id == project_id)
            .order_by(models.ProjectReport.year.desc(), models.ProjectReport.month.desc())
            .first()
        )
        contract_amount = last.contract_amount if last else 0
        report = models.ProjectReport(
            project_id=project_id,
            month=m,
            year=y,
            contract_amount=contract_amount,
            receipts=0,
        )
        db.add(report)
        db.commit()
        db.refresh(report)
    return report


def update_report(
    db: Session,
    project_id: int,
    data: schemas.ProjectReportUpdate,
    month: int | None = None,
    year: int | None = None,
) -> models.ProjectReport:
    report = get_or_create_report(db, project_id, month, year)
    if data.contract_amount is not None:
        report.contract_amount = data.contract_amount
    if data.receipts is not None:
        report.receipts = data.receipts
    db.commit()
    db.refresh(report)
    return report


def get_expenses(db: Session, project_id: int, start: datetime | None = None, end: datetime | None = None) -> List[models.ProjectExpense]:
    q = db.query(models.ProjectExpense).filter(models.ProjectExpense.project_id == project_id)
    if start:
        q = q.filter(models.ProjectExpense.created_at >= start)
    if end:
        q = q.filter(models.ProjectExpense.created_at < end)
    return q.all()


def create_expense(
    db: Session,
    project_id: int,
    exp: schemas.ExpenseCreate,
    month: int | None = None,
    year: int | None = None,
) -> models.ProjectExpense:
    created = datetime.utcnow()
    if month:
        y = year or created.year
        created = datetime(y, month, 1)
    e = models.ProjectExpense(
        project_id=project_id,
        name=exp.name,
        amount=exp.amount,
        description=exp.comment,
        created_at=created,
    )
    db.add(e)
    db.commit()
    db.refresh(e)
    return e


def delete_expense(db: Session, expense_id: int) -> None:
    e = db.query(models.ProjectExpense).filter(models.ProjectExpense.id == expense_id).first()
    if e:
        db.delete(e)
        db.commit()


def update_expense(db: Session, expense_id: int, exp: schemas.ExpenseCreate) -> Optional[models.ProjectExpense]:
    e = db.query(models.ProjectExpense).filter(models.ProjectExpense.id == expense_id).first()
    if not e:
        return None
    e.name = exp.name
    e.amount = exp.amount
    e.comment = exp.comment
    db.commit()
    db.refresh(e)
    return e


def get_receipts(db: Session, project_id: int, start: datetime | None = None, end: datetime | None = None) -> List[models.ProjectReceipt]:
    q = db.query(models.ProjectReceipt).filter(models.ProjectReceipt.project_id == project_id)
    if start:
        q = q.filter(models.ProjectReceipt.created_at >= start)
    if end:
        q = q.filter(models.ProjectReceipt.created_at < end)
    return q.all()


def create_receipt(
    db: Session,
    project_id: int,
    rec: schemas.ReceiptCreate,
    month: int | None = None,
    year: int | None = None,
) -> models.ProjectReceipt:
    created = datetime.utcnow()
    if month:
        y = year or created.year
        created = datetime(y, month, 1)
    r = models.ProjectReceipt(
        project_id=project_id,
        name=rec.name,
        amount=rec.amount,
        comment=rec.comment,
        created_at=created,
    )
    db.add(r)
    db.commit()
    db.refresh(r)
    report = get_or_create_report(db, project_id, r.created_at.month, r.created_at.year)
    report.receipts += rec.amount
    db.commit()
    db.refresh(report)
    return r


def delete_receipt(db: Session, receipt_id: int) -> None:
    r = db.query(models.ProjectReceipt).filter(models.ProjectReceipt.id == receipt_id).first()
    if r:
        report = get_or_create_report(db, r.project_id, r.created_at.month, r.created_at.year)
        report.receipts -= r.amount
        db.delete(r)
        db.commit()


def update_receipt(db: Session, receipt_id: int, rec: schemas.ReceiptCreate) -> Optional[models.ProjectReceipt]:
    r = db.query(models.ProjectReceipt).filter(models.ProjectReceipt.id == receipt_id).first()
    if not r:
        return None
    report = get_or_create_report(db, r.project_id, r.created_at.month, r.created_at.year)
    report.receipts += rec.amount - r.amount
    r.name = rec.name
    r.amount = rec.amount
    r.comment = rec.comment
    db.commit()
    db.refresh(r)
    db.refresh(report)
    return r


def get_client_expenses(db: Session, project_id: int, start: datetime | None = None, end: datetime | None = None) -> List[models.ProjectClientExpense]:
    q = db.query(models.ProjectClientExpense).filter(models.ProjectClientExpense.project_id == project_id)
    if start:
        q = q.filter(models.ProjectClientExpense.created_at >= start)
    if end:
        q = q.filter(models.ProjectClientExpense.created_at < end)
    return q.all()


def create_client_expense(
    db: Session,
    project_id: int,
    exp: schemas.ClientExpenseCreate,
    month: int | None = None,
    year: int | None = None,
) -> models.ProjectClientExpense:
    created = datetime.utcnow()
    if month:
        y = year or created.year
        created = datetime(y, month, 1)
    e = models.ProjectClientExpense(
        project_id=project_id,
        name=exp.name,
        amount=exp.amount,
        comment=exp.comment,
        created_at=created,
    )
    db.add(e)
    db.commit()
    db.refresh(e)
    return e


def update_client_expense(db: Session, expense_id: int, exp: schemas.ClientExpenseCreate) -> Optional[models.ProjectClientExpense]:
    e = db.query(models.ProjectClientExpense).filter(models.ProjectClientExpense.id == expense_id).first()
    if not e:
        return None
    e.name = exp.name
    e.amount = exp.amount
    e.comment = exp.comment
    db.commit()
    db.refresh(e)
    return e


def delete_client_expense(db: Session, expense_id: int) -> None:
    e = db.query(models.ProjectClientExpense).filter(models.ProjectClientExpense.id == expense_id).first()
    if e:
        db.delete(e)
        db.commit()


def close_client_expense(db: Session, expense_id: int, amount: float, comment: Optional[str] = None) -> Optional[models.ProjectClientExpense]:
    e = db.query(models.ProjectClientExpense).filter(models.ProjectClientExpense.id == expense_id).first()
    if not e:
        return None
    e.amount -= amount
    if comment is not None:
        e.comment = comment
    if e.amount <= 0:
        db.delete(e)
        db.commit()
        return None
    db.commit()
    db.refresh(e)
    return e


def get_project_posts(db: Session, project_id: int, start: datetime | None = None, end: datetime | None = None) -> List[models.ProjectPost]:
    q = db.query(models.ProjectPost).filter(models.ProjectPost.project_id == project_id)
    if start:
        q = q.filter(models.ProjectPost.date >= start)
    if end:
        q = q.filter(models.ProjectPost.date <= end)
    posts = q.all()
    
    # Auto-set overdue status for posts with past dates and in_progress status
    today = datetime.utcnow().date()
    for p in posts:
        if p.date.date() < today and p.status == models.PostStatus.in_progress:
            p.status = models.PostStatus.overdue
            db.commit()
    
    return posts


def create_project_post(db: Session, project_id: int, data: schemas.ProjectPostCreate) -> models.ProjectPost:
    # Determine appropriate status based on date
    today = datetime.utcnow().date()
    post_date = data.date.date()
    
    if data.status:
        # Validate provided status
        if post_date < today and data.status == models.PostStatus.in_progress:
            # Past date with in_progress -> auto-set to overdue
            status = models.PostStatus.overdue
        elif post_date >= today and data.status == models.PostStatus.overdue:
            # Future/today date cannot be overdue -> default to in_progress
            status = models.PostStatus.in_progress
        else:
            status = data.status
    else:
        # No status provided - auto-determine
        if post_date < today:
            status = models.PostStatus.overdue
        else:
            status = models.PostStatus.in_progress
    
    post = models.ProjectPost(
        project_id=project_id,
        date=data.date,
        posts_per_day=data.posts_per_day,
        post_type=data.post_type,
        status=status,
    )
    db.add(post)
    db.commit()
    db.refresh(post)
    return post


def update_project_post(db: Session, post_id: int, data: schemas.ProjectPostCreate) -> Optional[models.ProjectPost]:
    post = db.query(models.ProjectPost).filter(models.ProjectPost.id == post_id).first()
    if not post:
        return None
    
    post.date = data.date
    post.posts_per_day = data.posts_per_day
    post.post_type = data.post_type
    
    # Validate status based on date
    if data.status is not None:
        today = datetime.utcnow().date()
        post_date = data.date.date() if data.date else post.date.date()
        
        if post_date < today:
            # Past dates can only have: overdue, approved, or cancelled
            if data.status == models.PostStatus.in_progress:
                post.status = models.PostStatus.overdue  # Auto-set to overdue
            else:
                post.status = data.status
        else:
            # Today or future dates cannot be overdue
            if data.status != models.PostStatus.overdue:
                post.status = data.status
            # If trying to set overdue for future date, keep current status
    
    db.commit()
    db.refresh(post)
    return post


def delete_project_post(db: Session, post_id: int) -> None:
    post = db.query(models.ProjectPost).filter(models.ProjectPost.id == post_id).first()
    if post:
        db.delete(post)
        db.commit()


def get_expense_categories(db: Session, active_only: bool = False) -> List[models.ExpenseCategory]:
    q = db.query(models.ExpenseCategory)
    if active_only:
        q = q.filter(models.ExpenseCategory.is_active == True)
    return q.all()


def create_expense_category(db: Session, name: str, description: str = None, is_active: bool = True) -> models.ExpenseCategory:
    category = models.ExpenseCategory(name=name, description=description, is_active=is_active)
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


def update_expense_category(db: Session, category_id: int, name: str = None, description: str = None, is_active: bool = None) -> Optional[models.ExpenseCategory]:
    category = db.query(models.ExpenseCategory).filter(models.ExpenseCategory.id == category_id).first()
    if not category:
        return None
    if name is not None:
        category.name = name
    if description is not None:
        category.description = description
    if is_active is not None:
        category.is_active = is_active
    db.commit()
    db.refresh(category)
    return category


def delete_expense_category(db: Session, category_id: int) -> bool:
    category = db.query(models.ExpenseCategory).filter(models.ExpenseCategory.id == category_id).first()
    if not category:
        return False
    db.delete(category)
    db.commit()
    return True


# Common Expenses CRUD
def get_common_expenses(db: Session, skip: int = 0, limit: int = 100, 
                       start_date=None, end_date=None, category_id: int = None) -> List[models.CommonExpense]:
    query = db.query(models.CommonExpense)
    
    if start_date:
        query = query.filter(models.CommonExpense.date >= start_date)
    if end_date:
        query = query.filter(models.CommonExpense.date <= end_date)
    if category_id:
        query = query.filter(models.CommonExpense.category_id == category_id)
    
    return query.order_by(models.CommonExpense.date.desc()).offset(skip).limit(limit).all()


def create_common_expense(db: Session, expense_data: dict, created_by: int = None) -> models.CommonExpense:
    expense = models.CommonExpense(**expense_data, created_by=created_by)
    db.add(expense)
    db.commit()
    db.refresh(expense)
    return expense


def update_common_expense(db: Session, expense_id: int, update_data: dict) -> Optional[models.CommonExpense]:
    expense = db.query(models.CommonExpense).filter(models.CommonExpense.id == expense_id).first()
    if not expense:
        return None
    
    for field, value in update_data.items():
        setattr(expense, field, value)
    
    db.commit()
    db.refresh(expense)
    return expense


def delete_common_expense(db: Session, expense_id: int) -> bool:
    expense = db.query(models.CommonExpense).filter(models.CommonExpense.id == expense_id).first()
    if not expense:
        return False
    db.delete(expense)
    db.commit()
    return True


def get_taxes(db: Session) -> List[models.Tax]:
    return db.query(models.Tax).all()


def create_tax(db: Session, name: str, rate: float) -> models.Tax:
    tax = models.Tax(name=name, rate=rate)
    db.add(tax)
    db.commit()
    db.refresh(tax)
    return tax


def update_tax(db: Session, tax_id: int, name: str, rate: float) -> Optional[models.Tax]:
    tax = db.query(models.Tax).filter(models.Tax.id == tax_id).first()
    if not tax:
        return None
    tax.name = name
    tax.rate = rate
    db.commit()
    db.refresh(tax)
    return tax


def delete_tax(db: Session, tax_id: int) -> None:
    tax = db.query(models.Tax).filter(models.Tax.id == tax_id).first()
    if tax:
        db.delete(tax)
        db.commit()


def get_expenses_report(
    db: Session,
    start: datetime,
    end: datetime,
    project_id: int | None = None,
) -> List[tuple[str, int, float]]:
    q = db.query(models.ProjectExpense)
    if project_id:
        q = q.filter(models.ProjectExpense.project_id == project_id)
    q = q.filter(models.ProjectExpense.created_at >= start).filter(models.ProjectExpense.created_at < end)
    rows: dict[str, list[float]] = {}
    for e in q.all():
        rows.setdefault(e.name, []).append(e.amount)

    # include completed shootings cost
    sq = db.query(models.Shooting).join(models.Operator)
    sq = sq.filter(models.Shooting.completed == True)
    sq = sq.filter(models.Shooting.datetime >= start).filter(models.Shooting.datetime < end)
    if project_id:
        proj = db.query(models.Project).filter(models.Project.id == project_id).first()
        if proj:
            sq = sq.filter(models.Shooting.project == proj.name)
    video_totals = {"Видеография": [0, 0.0], "Мобилография": [0, 0.0]}
    for sh in sq.all():
        qty = sh.completed_quantity or sh.quantity or 0
        price = sh.operator.price_per_video or 0
        role = sh.operator.role
        key = "Видеография" if role == models.OperatorRole.video else "Мобилография"
        video_totals[key][0] += qty
        video_totals[key][1] += qty * price

    result = []
    for name, amounts in rows.items():
        qty = len(amounts)
        total = sum(amounts)
        avg = total / qty if qty else 0
        result.append((name, qty, avg))

    # add video/mobilography totals separately using correct calc
    for key, (qty, total) in video_totals.items():
        if qty:
            result.append((key, qty, total / qty if qty else 0))

    # include common expenses with quantity 1 and their unit cost
    common_items = get_expense_items(db, True)
    for it in common_items:
        result.append((it.name, 1, float(it.unit_cost)))

    return result


def get_digital_services(db: Session) -> List[models.DigitalService]:
    return db.query(models.DigitalService).all()


def create_digital_service(db: Session, name: str) -> models.DigitalService:
    service = models.DigitalService(name=name)
    db.add(service)
    db.commit()
    db.refresh(service)
    return service


def delete_digital_service(db: Session, service_id: int) -> None:
    service = db.query(models.DigitalService).filter(models.DigitalService.id == service_id).first()
    if service:
        db.delete(service)
        db.commit()


def get_digital_projects(db: Session) -> List[dict]:
    q = (
        db.query(
            models.DigitalProject,
            models.Project.name,
            models.DigitalService.name,
            models.User.name,
            models.Project.logo,
            models.Project.high_priority,
        )
        .join(models.Project, models.DigitalProject.project_id == models.Project.id)
        .join(models.DigitalService, models.DigitalProject.service_id == models.DigitalService.id)
        .join(models.User, models.DigitalProject.executor_id == models.User.id)
    )
    items: list[dict] = []
    for dp, proj_name, serv_name, exec_name, logo, high_priority in q.all():
        items.append(
            {
                "id": dp.id,
                "project": proj_name,
                "service": serv_name,
                "executor": exec_name,
                "project_id": dp.project_id,
                "service_id": dp.service_id,
                "executor_id": dp.executor_id,
                "created_at": dp.created_at,
                "deadline": dp.deadline,
                "monthly": dp.monthly,
                "logo": logo,
                "high_priority": high_priority,
                "status": dp.status,
            }
        )
    return items


def create_digital_project(db: Session, data: schemas.DigitalProjectCreate) -> models.DigitalProject:
    proj = models.DigitalProject(
        project_id=data.project_id,
        service_id=data.service_id,
        executor_id=data.executor_id,
        deadline=data.deadline,
        monthly=data.monthly,
        status=data.status,
    )
    db.add(proj)
    db.commit()
    db.refresh(proj)
    return proj


def update_digital_project(db: Session, project_id: int, data: schemas.DigitalProjectCreate) -> Optional[models.DigitalProject]:
    proj = db.query(models.DigitalProject).filter(models.DigitalProject.id == project_id).first()
    if not proj:
        return None
    proj.project_id = data.project_id
    proj.service_id = data.service_id
    proj.executor_id = data.executor_id
    proj.deadline = data.deadline
    proj.monthly = data.monthly
    proj.status = data.status
    db.commit()
    db.refresh(proj)
    return proj


def update_digital_project_status(db: Session, project_id: int, status: str) -> Optional[models.DigitalProject]:
    proj = db.query(models.DigitalProject).filter(models.DigitalProject.id == project_id).first()
    if not proj:
        return None
    proj.status = status
    db.commit()
    db.refresh(proj)
    return proj


def delete_digital_project(db: Session, project_id: int) -> None:
    proj = db.query(models.DigitalProject).filter(models.DigitalProject.id == project_id).first()
    if proj:
        # Delete all related tasks first
        db.query(models.DigitalProjectTask).filter(models.DigitalProjectTask.project_id == project_id).delete()
        # Delete all related finances
        db.query(models.DigitalProjectFinance).filter(models.DigitalProjectFinance.project_id == project_id).delete()
        # Delete all related expenses
        db.query(models.DigitalProjectExpense).filter(models.DigitalProjectExpense.project_id == project_id).delete()
        # Finally delete the project itself
        db.delete(proj)
        db.commit()


def set_digital_project_logo(db: Session, project_id: int, logo: str | None) -> Optional[models.DigitalProject]:
    proj = db.query(models.DigitalProject).filter(models.DigitalProject.id == project_id).first()
    if not proj:
        return None
    proj.logo = logo
    db.commit()
    db.refresh(proj)
    return proj


def get_digital_tasks(db: Session, project_id: int) -> List[models.DigitalProjectTask]:
    return (
        db.query(models.DigitalProjectTask)
        .filter(models.DigitalProjectTask.project_id == project_id)
        .order_by(models.DigitalProjectTask.high_priority.desc(), models.DigitalProjectTask.deadline)
        .all()
    )


def create_digital_task(
    db: Session, project_id: int, data: schemas.DigitalTaskCreate
) -> models.DigitalProjectTask:
    task = models.DigitalProjectTask(
        project_id=project_id,
        title=data.title,
        description=data.description,
        links=json.dumps([l.dict() for l in data.links]),
        deadline=data.deadline,
        high_priority=data.high_priority or False,
        status=data.status or "in_progress",
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def update_digital_task(db: Session, task_id: int, data: schemas.DigitalTaskCreate) -> Optional[models.DigitalProjectTask]:
    task = db.query(models.DigitalProjectTask).filter(models.DigitalProjectTask.id == task_id).first()
    if not task:
        return None
    task.title = data.title
    task.description = data.description
    task.links = json.dumps([l.dict() for l in data.links])
    task.deadline = data.deadline
    if data.high_priority is not None:
        task.high_priority = data.high_priority
    if data.status is not None:
        task.status = data.status
    db.commit()
    db.refresh(task)
    return task


def delete_digital_task(db: Session, task_id: int) -> None:
    task = db.query(models.DigitalProjectTask).filter(models.DigitalProjectTask.id == task_id).first()
    if task:
        db.delete(task)
        db.commit()


# Digital Project Finance CRUD
def get_digital_project_finance(db: Session, project_id: int) -> Optional[models.DigitalProjectFinance]:
    return db.query(models.DigitalProjectFinance).filter(models.DigitalProjectFinance.project_id == project_id).first()


def create_digital_project_finance(db: Session, finance_data: schemas.DigitalProjectFinanceCreate) -> models.DigitalProjectFinance:
    finance = models.DigitalProjectFinance(**finance_data.dict())
    db.add(finance)
    db.commit()
    db.refresh(finance)
    return finance


def update_digital_project_finance(db: Session, project_id: int, finance_data: schemas.DigitalProjectFinanceUpdate) -> Optional[models.DigitalProjectFinance]:
    finance = get_digital_project_finance(db, project_id)
    if not finance:
        return None
    
    for field, value in finance_data.dict(exclude_unset=True).items():
        setattr(finance, field, value)
    
    finance.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(finance)
    return finance


# Digital Project Expense CRUD
def get_digital_project_expenses(db: Session, project_id: int) -> List[models.DigitalProjectExpense]:
    return (
        db.query(models.DigitalProjectExpense)
        .filter(models.DigitalProjectExpense.project_id == project_id)
        .order_by(models.DigitalProjectExpense.date.desc())
        .all()
    )


def create_digital_project_expense(db: Session, expense_data: schemas.DigitalProjectExpenseCreate) -> models.DigitalProjectExpense:
    expense_dict = expense_data.dict()
    
    # Convert date string to date object if provided
    if expense_dict.get('date'):
        from datetime import datetime as dt
        expense_dict['date'] = dt.strptime(expense_dict['date'], '%Y-%m-%d').date()
    else:
        expense_dict['date'] = datetime.utcnow().date()
    
    expense = models.DigitalProjectExpense(**expense_dict)
    db.add(expense)
    db.commit()
    db.refresh(expense)
    return expense


def delete_digital_project_expense(db: Session, expense_id: int) -> None:
    expense = db.query(models.DigitalProjectExpense).filter(models.DigitalProjectExpense.id == expense_id).first()
    if expense:
        db.delete(expense)
        db.commit()


# Resource File CRUD
def get_resource_files(db: Session, category: Optional[str] = None, project_id: Optional[int] = None) -> List[models.ResourceFile]:
    query = db.query(models.ResourceFile)
    
    if category == "general":
        query = query.filter(models.ResourceFile.category == models.FileCategoryEnum.general)
    elif category == "project":
        query = query.filter(models.ResourceFile.category == models.FileCategoryEnum.project)
        if project_id:
            query = query.filter(models.ResourceFile.project_id == project_id)
    
    return query.order_by(models.ResourceFile.uploaded_at.desc()).all()


def get_resource_file(db: Session, file_id: int) -> Optional[models.ResourceFile]:
    return db.query(models.ResourceFile).filter(models.ResourceFile.id == file_id).first()


def create_resource_file(db: Session, file_data: schemas.ResourceFileCreate, filename: str, file_path: str, size: int, mime_type: str, user_id: int) -> models.ResourceFile:
    category_enum = models.FileCategoryEnum.project if file_data.category == "project" else models.FileCategoryEnum.general
    
    resource_file = models.ResourceFile(
        name=file_data.name,
        filename=filename,
        file_path=file_path,
        size=size,
        mime_type=mime_type,
        category=category_enum,
        project_id=file_data.project_id if file_data.category == "project" else None,
        uploaded_by=user_id,
        is_favorite=file_data.is_favorite
    )
    
    db.add(resource_file)
    db.commit()
    db.refresh(resource_file)
    return resource_file


def update_resource_file(db: Session, file_id: int, file_data: schemas.ResourceFileUpdate) -> Optional[models.ResourceFile]:
    resource_file = get_resource_file(db, file_id)
    if not resource_file:
        return None
    
    if file_data.name is not None:
        resource_file.name = file_data.name
    if file_data.category is not None:
        resource_file.category = models.FileCategoryEnum.project if file_data.category == "project" else models.FileCategoryEnum.general
    if file_data.project_id is not None:
        resource_file.project_id = file_data.project_id if file_data.category == "project" else None
    if file_data.is_favorite is not None:
        resource_file.is_favorite = file_data.is_favorite
    
    db.commit()
    db.refresh(resource_file)
    return resource_file


def delete_resource_file(db: Session, file_id: int) -> None:
    resource_file = get_resource_file(db, file_id)
    if resource_file:
        db.delete(resource_file)
        db.commit()


def increment_file_download_count(db: Session, file_id: int) -> None:
    resource_file = get_resource_file(db, file_id)
    if resource_file:
        resource_file.download_count += 1
        db.commit()


# User Statistics Functions
from datetime import datetime, timedelta
from sqlalchemy import func, distinct, case, and_


def get_user_statistics(db: Session, user_id: int) -> Optional[schemas.UserStats]:
    """Получить статистику пользователя"""
    user = get_user(db, user_id)
    if not user:
        return None
    
    # Общее количество задач пользователя
    total_tasks_query = db.query(models.Task).filter(models.Task.executor_id == user_id)
    total_assigned_tasks = total_tasks_query.count()
    
    # Выполненные задачи
    completed_tasks = total_tasks_query.filter(models.Task.status == models.TaskStatus.done).count()
    
    # Незавершенные задачи
    pending_tasks = total_tasks_query.filter(models.Task.status == models.TaskStatus.in_progress).count()
    
    # Процент выполнения
    completion_rate = (completed_tasks / total_assigned_tasks * 100) if total_assigned_tasks > 0 else 0
    
    # Проекты где пользователь выполнил хотя бы 1 задачу
    projects_with_completed_tasks = db.query(distinct(models.Task.project)).filter(
        and_(
            models.Task.executor_id == user_id,
            models.Task.status == models.TaskStatus.done,
            models.Task.project.isnot(None)
        )
    ).count()
    
    # Задачи за текущий месяц
    now = datetime.utcnow()
    month_start = datetime(now.year, now.month, 1)
    month_end = datetime(now.year, now.month + 1, 1) if now.month < 12 else datetime(now.year + 1, 1, 1)
    
    this_month_tasks = total_tasks_query.filter(
        models.Task.created_at >= month_start,
        models.Task.created_at < month_end
    ).count()
    
    this_month_completions = total_tasks_query.filter(
        models.Task.created_at >= month_start,
        models.Task.created_at < month_end,
        models.Task.status == models.TaskStatus.done
    ).count()
    
    # Активность за текущую неделю (понедельник - воскресенье)
    today = datetime.now().date()
    # Найти понедельник текущей недели
    days_since_monday = today.weekday()
    monday = today - timedelta(days=days_since_monday)
    
    weekly_activity = []
    day_names = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']
    
    for i in range(7):
        day = monday + timedelta(days=i)
        day_start = datetime.combine(day, datetime.min.time())
        day_end = datetime.combine(day, datetime.max.time())
        
        # Задачи поставленные в этот день
        assigned_count = total_tasks_query.filter(
            models.Task.created_at >= day_start,
            models.Task.created_at <= day_end
        ).count()
        
        # Задачи завершенные в этот день
        completed_count = total_tasks_query.filter(
            models.Task.finished_at >= day_start,
            models.Task.finished_at <= day_end,
            models.Task.status == models.TaskStatus.done
        ).count()
        
        weekly_activity.append(schemas.WeeklyActivity(
            day=day_names[i],
            completed_tasks=completed_count,
            assigned_tasks=assigned_count
        ))
    
    # Последние выполненные задачи
    recent_tasks_query = total_tasks_query.filter(
        models.Task.status == models.TaskStatus.done
    ).order_by(models.Task.finished_at.desc()).limit(5)
    
    recent_tasks = []
    for task in recent_tasks_query:
        time_diff = datetime.utcnow() - (task.finished_at or task.created_at)
        if time_diff.days == 0:
            if time_diff.seconds < 3600:
                time_str = f"{time_diff.seconds // 60} минут назад"
            else:
                time_str = f"{time_diff.seconds // 3600} часов назад"
        elif time_diff.days == 1:
            time_str = "1 день назад"
        else:
            time_str = f"{time_diff.days} дней назад"
        
        recent_tasks.append(schemas.RecentTask(
            title=task.title,
            project=task.project or "Без проекта",
            completed_at=time_str,
            status=task.status
        ))
    
    # Продуктивность
    # Среднее количество задач в день за последние 30 дней
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    tasks_last_30_days = total_tasks_query.filter(
        models.Task.finished_at >= thirty_days_ago,
        models.Task.status == models.TaskStatus.done
    ).count()
    average_tasks_per_day = tasks_last_30_days / 30.0
    
    # Лучшая серия - максимальное количество задач завершенное за один день
    best_day_query = db.query(func.date(models.Task.finished_at), func.count(models.Task.id)).filter(
        models.Task.executor_id == user_id,
        models.Task.status == models.TaskStatus.done,
        models.Task.finished_at.isnot(None)
    ).group_by(func.date(models.Task.finished_at)).order_by(func.count(models.Task.id).desc()).first()
    
    best_streak = best_day_query[1] if best_day_query else 0
    
    # Задачи завершенные сегодня
    today_start = datetime.combine(today, datetime.min.time())
    today_end = datetime.combine(today, datetime.max.time())
    current_day_tasks = total_tasks_query.filter(
        models.Task.finished_at >= today_start,
        models.Task.finished_at <= today_end,
        models.Task.status == models.TaskStatus.done
    ).count()
    
    # Подсчет активных дней (дни когда пользователь завершал задачи)
    # Это приблизительная метрика - в будущем можно добавить отдельную таблицу для отслеживания активности
    active_days_count = db.query(func.count(distinct(func.date(models.Task.finished_at)))).filter(
        models.Task.executor_id == user_id,
        models.Task.status == models.TaskStatus.done,
        models.Task.finished_at.isnot(None)
    ).scalar() or 0
    
    productivity = schemas.ProductivityMetrics(
        average_tasks_per_day=round(average_tasks_per_day, 1),
        best_streak=best_streak,
        current_day_tasks=current_day_tasks
    )
    
    return schemas.UserStats(
        total_projects=projects_with_completed_tasks,
        completed_tasks=completed_tasks,
        active_days=active_days_count,
        total_assigned_tasks=total_assigned_tasks,
        pending_tasks=pending_tasks,
        completion_rate=round(completion_rate, 1),
        this_month_tasks=this_month_tasks,
        this_month_completions=this_month_completions,
        weekly_activity=weekly_activity,
        recent_tasks=recent_tasks,
        productivity=productivity
    )


# =============================================================================
# CRUD для канбан-доски заявок
# =============================================================================

def get_leads(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    manager_id: Optional[int] = None,
    status: Optional[str] = None,
    source: Optional[str] = None,
    created_from: Optional[str] = None,
    created_to: Optional[str] = None
):
    """Получить список заявок с фильтрацией"""
    query = db.query(models.Lead).options(
        joinedload(models.Lead.manager),
        joinedload(models.Lead.notes).joinedload(models.LeadNote.user),
        joinedload(models.Lead.attachments),
        joinedload(models.Lead.history).joinedload(models.LeadHistory.user)
    )

    if manager_id:
        query = query.filter(models.Lead.manager_id == manager_id)
    if status:
        query = query.filter(models.Lead.status == status)
    if source:
        query = query.filter(models.Lead.source.ilike(f"%{source}%"))
    if created_from:
        from datetime import datetime
        try:
            from_date = datetime.strptime(created_from, "%Y-%m-%d")
            query = query.filter(models.Lead.created_at >= from_date)
        except ValueError:
            pass  # Игнорируем некорректные даты
    if created_to:
        from datetime import datetime, timedelta
        try:
            to_date = datetime.strptime(created_to, "%Y-%m-%d")
            # Добавляем один день, чтобы включить весь день "до"
            to_date = to_date + timedelta(days=1)
            query = query.filter(models.Lead.created_at < to_date)
        except ValueError:
            pass  # Игнорируем некорректные даты

    return query.order_by(models.Lead.last_activity_at.desc()).offset(skip).limit(limit).all()


def get_lead(db: Session, lead_id: int):
    """Получить заявку по ID"""
    return db.query(models.Lead).options(
        joinedload(models.Lead.manager),
        joinedload(models.Lead.notes).joinedload(models.LeadNote.user),
        joinedload(models.Lead.attachments),
        joinedload(models.Lead.history).joinedload(models.LeadHistory.user)
    ).filter(models.Lead.id == lead_id).first()


def create_lead(db: Session, lead: schemas.LeadCreate, creator_id: int):
    """Создать новую заявку"""
    db_lead = models.Lead(
        title=lead.title,
        source=lead.source,
        manager_id=lead.manager_id,
        client_name=lead.client_name,
        client_contact=lead.client_contact,
        company_name=lead.company_name,
        description=lead.description,
        status=models.LeadStatusEnum.new
    )
    
    db.add(db_lead)
    db.commit()
    db.refresh(db_lead)
    
    # Добавляем запись в историю
    _create_lead_history(
        db=db,
        lead_id=db_lead.id,
        user_id=creator_id,
        action="lead_created",
        description=f"Заявка '{lead.title}' создана"
    )
    
    return db_lead


def update_lead(db: Session, lead_id: int, lead_update: schemas.LeadUpdate, user_id: int):
    """Обновить заявку"""
    lead = db.query(models.Lead).filter(models.Lead.id == lead_id).first()
    if not lead:
        return None
    
    old_status = lead.status
    
    # Обновляем поля
    update_data = lead_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(lead, field, value)
    
    # Обновляем время последней активности
    lead.last_activity_at = models.get_local_time_utc5()
    
    # Обрабатываем изменение статуса
    if hasattr(lead_update, 'status') and lead_update.status and lead_update.status != old_status:
        if lead_update.status == models.LeadStatusEnum.waiting:
            lead.waiting_started_at = models.get_local_time_utc5()
        
        # Добавляем запись в историю
        _create_lead_history(
            db=db,
            lead_id=lead_id,
            user_id=user_id,
            action="status_changed",
            old_value=old_status,
            new_value=lead_update.status,
            description=f"Статус изменен с '{old_status}' на '{lead_update.status}'"
        )
    
    db.commit()
    db.refresh(lead)
    return lead


def delete_lead(db: Session, lead_id: int):
    """Удалить заявку"""
    lead = db.query(models.Lead).filter(models.Lead.id == lead_id).first()
    if not lead:
        return False
    
    db.delete(lead)
    db.commit()
    return True


# Заметки к заявкам
def create_lead_note(db: Session, lead_id: int, note: schemas.LeadNoteCreate, user_id: int):
    """Создать заметку к заявке"""
    # Сначала получаем текущий статус заявки
    lead = db.query(models.Lead).filter(models.Lead.id == lead_id).first()
    
    db_note = models.LeadNote(
        lead_id=lead_id,
        user_id=user_id,
        content=note.content,
        lead_status=lead.status if lead else None  # Сохраняем текущий статус
    )
    
    db.add(db_note)
    
    # Обновляем время последней активности заявки
    if lead:
        lead.last_activity_at = models.get_local_time_utc5()
    
    # Добавляем запись в историю
    _create_lead_history(
        db=db,
        lead_id=lead_id,
        user_id=user_id,
        action="note_added",
        description=f"Добавлена заметка: {note.content[:50]}..."
    )
    
    db.commit()
    db.refresh(db_note)
    return db_note


def delete_lead_note(db: Session, note_id: int, user_id: int):
    """Удалить заметку (только автор может удалить свою заметку)"""
    note = db.query(models.LeadNote).filter(
        models.LeadNote.id == note_id,
        models.LeadNote.user_id == user_id
    ).first()
    
    if not note:
        return False
    
    lead_id = note.lead_id
    db.delete(note)
    
    # Добавляем запись в историю
    _create_lead_history(
        db=db,
        lead_id=lead_id,
        user_id=user_id,
        action="note_deleted",
        description="Заметка удалена"
    )
    
    db.commit()
    return True


# Файлы к заявкам
def create_lead_attachment(db: Session, lead_id: int, attachment: dict, user_id: int):
    """Создать вложение к заявке"""
    db_attachment = models.LeadAttachment(
        lead_id=lead_id,
        user_id=user_id,
        **attachment
    )
    
    db.add(db_attachment)
    
    # Обновляем время последней активности заявки
    lead = db.query(models.Lead).filter(models.Lead.id == lead_id).first()
    if lead:
        lead.last_activity_at = models.get_local_time_utc5()
    
    # Добавляем запись в историю
    _create_lead_history(
        db=db,
        lead_id=lead_id,
        user_id=user_id,
        action="file_attached",
        description=f"Прикреплен файл: {attachment['filename']}"
    )
    
    db.commit()
    db.refresh(db_attachment)
    return db_attachment


def get_lead_attachment(db: Session, attachment_id: int):
    """Получить вложение по ID"""
    return db.query(models.LeadAttachment).filter(
        models.LeadAttachment.id == attachment_id
    ).first()


def delete_lead_attachment(db: Session, attachment_id: int, user_id: int):
    """Удалить вложение (только автор может удалить свой файл)"""
    attachment = db.query(models.LeadAttachment).filter(
        models.LeadAttachment.id == attachment_id,
        models.LeadAttachment.user_id == user_id
    ).first()
    
    if not attachment:
        return False
    
    lead_id = attachment.lead_id
    filename = attachment.filename
    file_path = attachment.file_path
    
    db.delete(attachment)
    
    # Удаляем файл с диска
    import os
    if os.path.exists(file_path):
        os.remove(file_path)
    
    # Добавляем запись в историю
    _create_lead_history(
        db=db,
        lead_id=lead_id,
        user_id=user_id,
        action="file_deleted",
        description=f"Удален файл: {filename}"
    )
    
    db.commit()
    return True


def _create_lead_history(db: Session, lead_id: int, user_id: int, action: str, old_value: str = None, new_value: str = None, description: str = None):
    """Создать запись в истории заявки"""
    history = models.LeadHistory(
        lead_id=lead_id,
        user_id=user_id,
        action=action,
        old_value=old_value,
        new_value=new_value,
        description=description
    )
    
    db.add(history)
    # Не делаем commit здесь, это делается в вызывающей функции


def get_leads_analytics(db: Session):
    """Получить аналитику по заявкам"""
    from sqlalchemy import func, case
    from datetime import datetime, timedelta
    
    # Общая статистика
    total_leads = db.query(models.Lead).count()
    
    active_leads = db.query(models.Lead).filter(
        models.Lead.status.in_([
            models.LeadStatusEnum.new,
            models.LeadStatusEnum.in_progress,
            models.LeadStatusEnum.negotiation,
            models.LeadStatusEnum.proposal,
            models.LeadStatusEnum.waiting
        ])
    ).count()
    
    success_leads = db.query(models.Lead).filter(
        models.Lead.status == models.LeadStatusEnum.success
    ).count()
    
    rejected_leads = db.query(models.Lead).filter(
        models.Lead.status == models.LeadStatusEnum.rejected
    ).count()
    
    conversion_rate = (success_leads / total_leads * 100) if total_leads > 0 else 0
    
    # Среднее время обработки (для завершенных заявок)
    completed_leads = db.query(models.Lead).filter(
        models.Lead.status.in_([models.LeadStatusEnum.success, models.LeadStatusEnum.rejected])
    ).all()
    
    if completed_leads:
        processing_times = []
        for lead in completed_leads:
            # Рассчитываем время в секундах для более точного расчета
            time_diff = (lead.updated_at - lead.created_at).total_seconds()
            processing_times.append(time_diff)
        average_processing_time = sum(processing_times) / len(processing_times)
    else:
        average_processing_time = 0
    
    # Статистика по статусам
    status_counts = db.query(
        models.Lead.status,
        func.count(models.Lead.id)
    ).group_by(models.Lead.status).all()
    
    leads_by_status = {
        'new': 0,
        'in_progress': 0,
        'negotiation': 0,
        'proposal': 0,
        'waiting': 0,
        'success': 0,
        'rejected': 0
    }
    
    for status, count in status_counts:
        leads_by_status[status] = count
    
    # Статистика по источникам
    source_counts = db.query(
        models.Lead.source,
        func.count(models.Lead.id)
    ).group_by(models.Lead.source).all()
    
    leads_by_source = {source: count for source, count in source_counts}
    
    # Причины отказов
    rejection_reasons = db.query(
        models.Lead.rejection_reason,
        func.count(models.Lead.id)
    ).filter(
        models.Lead.rejection_reason.isnot(None)
    ).group_by(models.Lead.rejection_reason).all()
    
    rejection_reasons_dict = {reason: count for reason, count in rejection_reasons if reason}
    
    # Топ менеджеров по успешным сделкам
    top_managers = db.query(
        models.User.name,
        func.count(models.Lead.id)
    ).join(
        models.Lead, models.User.id == models.Lead.manager_id
    ).filter(
        models.Lead.status == models.LeadStatusEnum.success
    ).group_by(models.User.name).order_by(
        func.count(models.Lead.id).desc()
    ).limit(5).all()
    
    top_managers_dict = {name: count for name, count in top_managers}
    
    return schemas.LeadAnalytics(
        stats=schemas.LeadStats(
            total_leads=total_leads,
            active_leads=active_leads,
            success_leads=success_leads,
            rejected_leads=rejected_leads,
            conversion_rate=round(conversion_rate, 1),
            average_processing_time=int(average_processing_time)
        ),
        leads_by_status=schemas.LeadsByStatus(**leads_by_status),
        leads_by_source=leads_by_source,
        rejection_reasons=rejection_reasons_dict,
        top_managers=top_managers_dict
    )


# CRUD операции для интерактивной доски

def get_user_accessible_whiteboard_projects(db: Session, user_id: int, user_role: str) -> List[models.WhiteboardProject]:
    """Получить проекты доски, доступные пользователю"""
    # Получаем проекты, где пользователь имеет права доступа или является создателем
    query = db.query(models.WhiteboardProject).outerjoin(
        models.WhiteboardProjectPermission,
        models.WhiteboardProject.id == models.WhiteboardProjectPermission.project_id
    ).filter(
        models.WhiteboardProject.is_archived == False,
        (
            (models.WhiteboardProjectPermission.user_id == user_id) & 
            (models.WhiteboardProjectPermission.can_view == True)
        ) | 
        (models.WhiteboardProject.created_by == user_id)
    ).options(
        joinedload(models.WhiteboardProject.creator),
        joinedload(models.WhiteboardProject.permissions).joinedload(models.WhiteboardProjectPermission.user)
    ).distinct()
    
    return query.all()


def get_whiteboard_project(db: Session, project_id: int) -> Optional[models.WhiteboardProject]:
    """Получить проект доски по ID"""
    return db.query(models.WhiteboardProject).options(
        joinedload(models.WhiteboardProject.creator),
        joinedload(models.WhiteboardProject.permissions).joinedload(models.WhiteboardProjectPermission.user),
        joinedload(models.WhiteboardProject.boards)
    ).filter(models.WhiteboardProject.id == project_id).first()


def create_whiteboard_project(db: Session, project: schemas.WhiteboardProjectCreate, creator_id: int, creator_role: str) -> models.WhiteboardProject:
    """Создать новый проект доски"""
    db_project = models.WhiteboardProject(
        name=project.name,
        created_by=creator_id
    )
    
    db.add(db_project)
    db.flush()  # Получаем ID проекта
    
    # Создаем права доступа для выбранных пользователей
    for permission in project.permissions:
        db_permission = models.WhiteboardProjectPermission(
            project_id=db_project.id,
            user_id=permission.user_id,
            can_view=permission.can_view,
            can_edit=permission.can_edit,
            can_manage=permission.can_manage
        )
        db.add(db_permission)
    
    # Создаем основную доску для проекта
    main_board = models.WhiteboardBoard(
        project_id=db_project.id,
        name="Основная доска",
        created_by=creator_id,
        data="{}"  # Пустые данные изначально
    )
    db.add(main_board)
    
    db.commit()
    db.refresh(db_project)
    return db_project


def update_whiteboard_project(db: Session, project_id: int, project_update: schemas.WhiteboardProjectUpdate) -> Optional[models.WhiteboardProject]:
    """Обновить проект доски"""
    db_project = db.query(models.WhiteboardProject).filter(models.WhiteboardProject.id == project_id).first()
    if not db_project:
        return None
    
    update_data = project_update.model_dump(exclude_unset=True)
    if update_data:
        update_data['updated_at'] = get_local_time_utc5()
        for field, value in update_data.items():
            setattr(db_project, field, value)
    
    db.commit()
    db.refresh(db_project)
    return db_project


def check_user_whiteboard_permission(db: Session, project_id: int, user_id: int, permission_type: str = "view") -> bool:
    """Проверить права пользователя на проект доски"""
    # Проверяем, является ли пользователь создателем проекта
    project = db.query(models.WhiteboardProject).filter(models.WhiteboardProject.id == project_id).first()
    if project and project.created_by == user_id:
        return True  # Создатель имеет все права
    
    # Проверяем явные права пользователя
    permission = db.query(models.WhiteboardProjectPermission).filter(
        models.WhiteboardProjectPermission.project_id == project_id,
        models.WhiteboardProjectPermission.user_id == user_id
    ).first()
    
    if not permission:
        return False
    
    if permission_type == "view":
        return permission.can_view
    elif permission_type == "edit":
        return permission.can_edit
    elif permission_type == "manage":
        return permission.can_manage
    
    return False


def get_whiteboard_board(db: Session, board_id: int) -> Optional[models.WhiteboardBoard]:
    """Получить доску по ID"""
    return db.query(models.WhiteboardBoard).options(
        joinedload(models.WhiteboardBoard.project),
        joinedload(models.WhiteboardBoard.creator)
    ).filter(models.WhiteboardBoard.id == board_id).first()


def update_whiteboard_board_data(db: Session, board_id: int, data: str) -> Optional[models.WhiteboardBoard]:
    """Обновить данные доски"""
    db_board = db.query(models.WhiteboardBoard).filter(models.WhiteboardBoard.id == board_id).first()
    if not db_board:
        return None
    
    db_board.data = data
    db_board.updated_at = get_local_time_utc5()
    
    db.commit()
    db.refresh(db_board)
    return db_board


def get_all_users(db: Session) -> List[models.User]:
    """Получить список всех активных пользователей"""
    return db.query(models.User).filter(models.User.is_active == True).all()


def add_user_to_whiteboard_project(db: Session, project_id: int, user_id: int, can_view: bool = True, can_edit: bool = False, can_manage: bool = False) -> Optional[models.WhiteboardProjectPermission]:
    """Добавить пользователя к проекту доски"""
    # Проверяем, нет ли уже такого пользователя в проекте
    existing = db.query(models.WhiteboardProjectPermission).filter(
        models.WhiteboardProjectPermission.project_id == project_id,
        models.WhiteboardProjectPermission.user_id == user_id
    ).first()
    
    if existing:
        return None  # Пользователь уже добавлен
    
    permission = models.WhiteboardProjectPermission(
        project_id=project_id,
        user_id=user_id,
        can_view=can_view,
        can_edit=can_edit,
        can_manage=can_manage
    )
    
    db.add(permission)
    db.commit()
    db.refresh(permission)
    return permission


def remove_user_from_whiteboard_project(db: Session, project_id: int, user_id: int) -> bool:
    """Удалить пользователя из проекта доски"""
    permission = db.query(models.WhiteboardProjectPermission).filter(
        models.WhiteboardProjectPermission.project_id == project_id,
        models.WhiteboardProjectPermission.user_id == user_id
    ).first()
    
    if permission:
        db.delete(permission)
        db.commit()
        return True
    
    return False


def update_user_whiteboard_permissions(db: Session, project_id: int, user_id: int, can_view: bool = True, can_edit: bool = False, can_manage: bool = False) -> Optional[models.WhiteboardProjectPermission]:
    """Обновить права пользователя в проекте доски"""
    permission = db.query(models.WhiteboardProjectPermission).filter(
        models.WhiteboardProjectPermission.project_id == project_id,
        models.WhiteboardProjectPermission.user_id == user_id
    ).first()
    
    if permission:
        permission.can_view = can_view
        permission.can_edit = can_edit
        permission.can_manage = can_manage
        db.commit()
        db.refresh(permission)
        return permission
    
    return None


def delete_whiteboard_project(db: Session, project_id: int, user_id: int) -> bool:
    """Удалить проект доски. Может удалить только создатель проекта."""
    project = db.query(models.WhiteboardProject).filter(models.WhiteboardProject.id == project_id).first()
    
    if not project:
        return False
    
    # Проверяем, что пользователь является создателем проекта
    if project.created_by != user_id:
        return False
    
    try:
        # Удаляем все связанные boards
        db.query(models.WhiteboardBoard).filter(models.WhiteboardBoard.project_id == project_id).delete()
        
        # Удаляем все permissions
        db.query(models.WhiteboardProjectPermission).filter(models.WhiteboardProjectPermission.project_id == project_id).delete()
        
        # Удаляем сам проект
        db.delete(project)
        db.commit()
        return True
        
    except Exception as e:
        db.rollback()
        return False


# =============================================================================
# Аналитика по типам услуг
# =============================================================================

def get_service_types_analytics(
    db: Session,
    start_date: str = None,
    end_date: str = None,
    employee_id: int = None
):
    """Получить аналитику по типам услуг для сотрудников"""
    from datetime import datetime, timedelta
    from sqlalchemy import func, and_, or_

    # Определяем период анализа
    if not start_date:
        # По умолчанию - текущий месяц
        now = datetime.now()
        start_date = now.replace(day=1).strftime('%Y-%m-%d')

    if not end_date:
        now = datetime.now()
        end_date = now.strftime('%Y-%m-%d')

    try:
        start_datetime = datetime.strptime(start_date, '%Y-%m-%d')
        end_datetime = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
    except ValueError:
        # Если даты некорректные, используем текущий месяц
        now = datetime.now()
        start_datetime = now.replace(day=1)
        end_datetime = now

    # Получаем всех активных сотрудников или конкретного сотрудника
    users_query = db.query(models.User).filter(
        models.User.is_active == True
    )

    if employee_id:
        users_query = users_query.filter(models.User.id == employee_id)

    users = users_query.all()

    # Получаем все уникальные типы услуг
    all_service_types = db.query(models.Task.task_type).filter(
        models.Task.task_type.isnot(None),
        models.Task.task_type != ''
    ).distinct().all()
    total_service_types = [st[0] for st in all_service_types]

    employees_analytics = []

    for user in users:
        # Получаем статистику созданных задач (author_id = user.id)
        created_query = db.query(
            models.Task.task_type,
            func.count(models.Task.id).label('created_count')
        ).filter(
            models.Task.author_id == user.id,
            models.Task.created_at >= start_datetime,
            models.Task.created_at < end_datetime,
            models.Task.task_type.isnot(None),
            models.Task.task_type != ''
        ).group_by(models.Task.task_type)

        created_data = {row.task_type: row.created_count for row in created_query.all()}

        # Получаем статистику назначенных задач (executor_id = user.id - все задачи, назначенные на исполнителя)
        assigned_query = db.query(
            models.Task.task_type,
            func.count(models.Task.id).label('assigned_count')
        ).filter(
            models.Task.executor_id == user.id,
            models.Task.created_at >= start_datetime,
            models.Task.created_at < end_datetime,
            models.Task.task_type.isnot(None),
            models.Task.task_type != ''
        ).group_by(models.Task.task_type)

        assigned_data = {row.task_type: row.assigned_count for row in assigned_query.all()}

        # Получаем статистику завершенных задач (executor_id = user.id и status = done)
        completed_query = db.query(
            models.Task.task_type,
            func.count(models.Task.id).label('completed_count')
        ).filter(
            models.Task.executor_id == user.id,
            models.Task.status == models.TaskStatus.done,
            models.Task.created_at >= start_datetime,
            models.Task.created_at < end_datetime,
            models.Task.task_type.isnot(None),
            models.Task.task_type != ''
        ).group_by(models.Task.task_type)

        completed_data = {row.task_type: row.completed_count for row in completed_query.all()}

        # Объединяем данные по типам услуг
        service_types_data = []
        total_created = 0
        total_completed = 0

        # Получаем все типы услуг, которые есть у этого пользователя (созданные им или назначенные на него)
        user_service_types = set(created_data.keys()) | set(assigned_data.keys()) | set(completed_data.keys())

        for service_type in user_service_types:
            created_count = created_data.get(service_type, 0)
            assigned_count = assigned_data.get(service_type, 0)
            completed_count = completed_data.get(service_type, 0)

            # Для отображения используем созданные задачи, но если пользователь не создавал задачи,
            # а только выполняет их, показываем назначенные задачи
            display_created = created_count if created_count > 0 else assigned_count

            # Рассчитываем эффективность на основе назначенных задач
            efficiency = (completed_count / assigned_count * 100) if assigned_count > 0 else 0

            service_types_data.append({
                'service_type': service_type,
                'created': display_created,
                'completed': completed_count,
                'efficiency': round(efficiency, 1)
            })

            total_created += display_created
            total_completed += completed_count

        # Рассчитываем общую эффективность сотрудника
        overall_efficiency = (total_completed / total_created * 100) if total_created > 0 else 0

        # Добавляем данные сотрудника только если у него есть активность
        if total_created > 0 or total_completed > 0:
            employees_analytics.append({
                'employee_id': user.id,
                'employee_name': user.name,
                'service_types': service_types_data,
                'total_created': total_created,
                'total_completed': total_completed,
                'overall_efficiency': round(overall_efficiency, 1)
            })

    return {
        'employees': employees_analytics,
        'period_start': start_date,
        'period_end': end_date,
        'total_service_types': total_service_types
    }


# =============================================================================
# Расходы по проектам - агрегированная аналитика
# =============================================================================

def get_project_expenses_summary(db: Session, project_id: int = None):
    """Получить сводку расходов по проектам"""
    from sqlalchemy import func

    # Базовый запрос проектов
    projects_query = db.query(models.Project)
    if project_id:
        projects_query = projects_query.filter(models.Project.id == project_id)

    projects = projects_query.all()
    project_summaries = []

    for project in projects:
        # Затраты на проект (из project_expenses)
        project_costs = db.query(func.sum(models.ProjectExpense.amount)).filter(
            models.ProjectExpense.project_id == project.id
        ).scalar() or 0

        # Расходы сотрудников на проект (из employee_expenses с project_id)
        employee_expenses = db.query(func.sum(models.EmployeeExpense.amount)).filter(
            models.EmployeeExpense.project_id == project.id
        ).scalar() or 0

        # Расходы операторов (из calendar событий съемок для проекта)
        # Пока оставим как 0, так как нужна дополнительная логика для календаря
        operator_expenses = 0

        total_expenses = project_costs + employee_expenses + operator_expenses

        project_summaries.append({
            'project_id': project.id,
            'project_name': project.name,
            'project_costs': project_costs,
            'employee_expenses': employee_expenses,
            'operator_expenses': operator_expenses,
            'total_expenses': total_expenses
        })

    return project_summaries

from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import json

from . import models, schemas, auth


def get_user(db: Session, user_id: int) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.id == user_id).first()


def get_user_by_login(db: Session, login: str) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.login == login).first()


def create_user(db: Session, user: schemas.UserCreate) -> models.User:
    hashed_password = auth.get_password_hash(user.password)
    db_user = models.User(
        login=user.login,
        name=user.name,
        hashed_password=hashed_password,
        role=user.role,
        birth_date=user.birth_date,
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
    if user.login is not None:
        db_user.login = user.login
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


def get_operators(db: Session) -> List[models.Operator]:
    return db.query(models.Operator).all()


def create_operator(db: Session, operator: schemas.OperatorCreate) -> models.Operator:
    op = models.Operator(
        name=operator.name,
        role=operator.role,
        color=operator.color or "#ff0000",
        price_per_video=operator.price_per_video or 0,
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
        created_at=datetime.utcnow(),
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
        task.status = status
        if status == models.TaskStatus.done:
            task.finished_at = datetime.utcnow()
        else:
            task.finished_at = None
        db.commit()
        db.refresh(task)
    return task


def get_projects(db: Session) -> List[models.Project]:
    return db.query(models.Project).all()


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
        comment=exp.comment,
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
    today = datetime.utcnow().date()
    for p in posts:
        if p.date.date() == today and p.status == models.PostStatus.overdue:
            p.status = models.PostStatus.in_progress
        elif p.status == models.PostStatus.in_progress and p.date.date() < today:
            p.status = models.PostStatus.overdue
    return posts


def create_project_post(db: Session, project_id: int, data: schemas.ProjectPostCreate) -> models.ProjectPost:
    post = models.ProjectPost(
        project_id=project_id,
        date=data.date,
        posts_per_day=data.posts_per_day,
        post_type=data.post_type,
        status=data.status or models.PostStatus.in_progress,
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
    post.status = data.status or post.status
    db.commit()
    db.refresh(post)
    return post


def delete_project_post(db: Session, post_id: int) -> None:
    post = db.query(models.ProjectPost).filter(models.ProjectPost.id == post_id).first()
    if post:
        db.delete(post)
        db.commit()


def get_expense_items(db: Session, is_common: bool | None = None) -> List[models.ExpenseItem]:
    q = db.query(models.ExpenseItem)
    if is_common is not None:
        q = q.filter(models.ExpenseItem.is_common == is_common)
    return q.all()


def create_expense_item(db: Session, name: str, is_common: bool = False, unit_cost: int = 0) -> models.ExpenseItem:
    item = models.ExpenseItem(name=name, is_common=is_common, unit_cost=unit_cost)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def update_expense_item(db: Session, item_id: int, name: str, is_common: bool | None = None, unit_cost: int | None = None) -> Optional[models.ExpenseItem]:
    item = db.query(models.ExpenseItem).filter(models.ExpenseItem.id == item_id).first()
    if not item:
        return None
    item.name = name
    if is_common is not None:
        item.is_common = is_common
    if unit_cost is not None:
        item.unit_cost = unit_cost
    db.commit()
    db.refresh(item)
    return item


def delete_expense_item(db: Session, item_id: int) -> None:
    item = db.query(models.ExpenseItem).filter(models.ExpenseItem.id == item_id).first()
    if item:
        db.delete(item)
        db.commit()


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

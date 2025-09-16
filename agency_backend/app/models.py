from sqlalchemy import (
    Column,
    Integer,
    String,
    ForeignKey,
    DateTime,
    Text,
    Enum,
    Boolean,
    UniqueConstraint,
    Date,
    Float,
    BigInteger,
)
from sqlalchemy.orm import relationship
from datetime import datetime, timedelta, timezone
import enum

from .database import Base

# Функция для получения текущего времени в UTC+5
def get_local_time_utc5():
    """Получить текущее время с учетом UTC+5"""
    return datetime.now(timezone.utc) + timedelta(hours=5)

class RoleEnum(str, enum.Enum):
    designer = "designer"
    smm_manager = "smm_manager"
    head_smm = "head_smm"
    admin = "admin"
    digital = "digital"
    inactive = "inactive"  # Для бывших сотрудников

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    telegram_username = Column(String, unique=True, index=True, nullable=True)  # Заменили login на telegram_username
    telegram_id = Column(BigInteger, unique=True, index=True, nullable=True)  # Telegram ID пользователя
    name = Column(String, index=True)
    hashed_password = Column(String)
    role = Column(Enum(RoleEnum), default=RoleEnum.designer)
    birth_date = Column(Date, nullable=True)
    contract_path = Column(String, nullable=True)
    telegram_registered_at = Column(DateTime, nullable=True)  # Когда зарегистрировался в Telegram
    is_active = Column(Boolean, default=True)  # Активен ли пользователь

    tasks = relationship(
        "Task",
        foreign_keys="Task.executor_id",
        back_populates="executor",
    )

    authored_tasks = relationship(
        "Task",
        foreign_keys="Task.author_id",
        back_populates="author",
    )
    
    expenses = relationship("EmployeeExpense", back_populates="user")

class TaskStatus(str, enum.Enum):
    new = "new"  # Новая задача, еще не принята в работу
    in_progress = "in_progress"  # Задача принята в работу
    done = "done"  # Задача завершена
    cancelled = "cancelled"  # Задача отменена

class RecurrenceType(str, enum.Enum):
    daily = "daily"
    weekly = "weekly"
    monthly = "monthly"

class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(Text)
    project = Column(String, index=True)
    deadline = Column(DateTime)
    status = Column(Enum(TaskStatus), default=TaskStatus.new)
    task_type = Column(String, nullable=True)
    task_format = Column(String, nullable=True)
    high_priority = Column(Boolean, default=False, nullable=True)
    executor_id = Column(Integer, ForeignKey("users.id"))
    author_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=get_local_time_utc5)
    accepted_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    resume_count = Column(Integer, default=0)  # Количество возобновлений задачи
    
    # Поля для повторяющихся задач
    is_recurring = Column(Boolean, default=False, nullable=True)  # Является ли задача повторяющейся
    recurrence_type = Column(Enum(RecurrenceType), nullable=True)  # daily, weekly, monthly
    recurrence_time = Column(String, nullable=True)  # Время повтора в формате HH:MM
    recurrence_days = Column(String, nullable=True)  # Дни недели/месяца для повтора (1,2,3,4,5 или 15)
    next_run_at = Column(DateTime, nullable=True)  # Когда создать следующую копию
    

    executor = relationship(
        "User",
        foreign_keys=[executor_id],
        back_populates="tasks",
    )
    author = relationship(
        "User",
        foreign_keys=[author_id],
        back_populates="authored_tasks",
    )

class OperatorRole(str, enum.Enum):
    mobile = "mobile"
    video = "video"

class Operator(Base):
    __tablename__ = "operators"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    role = Column(Enum(OperatorRole))
    color = Column(String, default="#ff0000")
    price_per_video = Column(Integer, default=0)
    is_salaried = Column(Boolean, default=False)  # Работает за зарплату
    monthly_salary = Column(Integer, nullable=True)  # Месячная зарплата

def first_day_current_month() -> datetime:
    now = datetime.utcnow()
    return datetime(now.year, now.month, 1)


def first_day_next_month() -> datetime:
    now = datetime.utcnow()
    year = now.year + (1 if now.month == 12 else 0)
    month = 1 if now.month == 12 else now.month + 1
    return datetime(year, month, 1)

def last_day_current_month() -> datetime:
    start_next = first_day_next_month()
    return start_next - timedelta(days=1)


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    logo = Column(String, nullable=True)
    posts_count = Column(Integer, default=0)
    start_date = Column(DateTime, default=first_day_current_month)
    end_date = Column(DateTime, default=last_day_current_month)
    high_priority = Column(Boolean, default=False, nullable=True)
    is_archived = Column(Boolean, default=False)

class Shooting(Base):
    __tablename__ = "shootings"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    project = Column(String, nullable=True)
    quantity = Column(Integer, nullable=True)
    operator_id = Column(Integer, ForeignKey("operators.id"))
    managers = Column(String, nullable=True)
    datetime = Column(DateTime)
    end_datetime = Column(DateTime)
    completed = Column(Boolean, default=False)
    completed_quantity = Column(Integer, nullable=True)
    completed_managers = Column(String, nullable=True)
    completed_operators = Column(String, nullable=True)

    operator = relationship("Operator")


class ExpenseCategory(Base):
    __tablename__ = "expense_categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    project_expenses = relationship("ProjectExpense", back_populates="category")
    common_expenses = relationship("CommonExpense", back_populates="category")



class Tax(Base):
    __tablename__ = "taxes"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True)
    rate = Column(Float)



class ProjectReport(Base):
    __tablename__ = "project_reports"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    month = Column(Integer, default=datetime.utcnow().month)
    year = Column(Integer, default=datetime.utcnow().year)
    contract_amount = Column(Integer, default=0)
    receipts = Column(Integer, default=0)

    project = relationship("Project")

    __table_args__ = (UniqueConstraint("project_id", "month", "year"),)


class ProjectExpense(Base):
    __tablename__ = "project_expenses"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    category_id = Column(Integer, ForeignKey("expense_categories.id"), nullable=True)
    name = Column(String)
    amount = Column(Float)
    description = Column(Text, nullable=True)
    date = Column(Date, default=datetime.utcnow().date)
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    project = relationship("Project")
    category = relationship("ExpenseCategory", back_populates="project_expenses")
    creator = relationship("User")


class CommonExpense(Base):
    __tablename__ = "common_expenses"

    id = Column(Integer, primary_key=True, index=True)
    category_id = Column(Integer, ForeignKey("expense_categories.id"), nullable=True)
    name = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    description = Column(Text, nullable=True)
    date = Column(Date, default=datetime.utcnow().date)
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    category = relationship("ExpenseCategory", back_populates="common_expenses")
    creator = relationship("User")


class ProjectReceipt(Base):
    __tablename__ = "project_receipts"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    name = Column(String)
    amount = Column(Integer)
    comment = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project")


class ProjectClientExpense(Base):
    __tablename__ = "project_client_expenses"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    name = Column(String)
    amount = Column(Integer)
    comment = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project")


class PostType(str, enum.Enum):
    video = "video"
    static = "static"
    carousel = "carousel"


class PostStatus(str, enum.Enum):
    in_progress = "in_progress"
    cancelled = "cancelled"
    approved = "approved"
    overdue = "overdue"


class ProjectPost(Base):
    __tablename__ = "project_posts"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    date = Column(DateTime)
    posts_per_day = Column(Integer, default=1)
    post_type = Column(Enum(PostType))
    status = Column(Enum(PostStatus), default=PostStatus.in_progress)

    project = relationship("Project")


class DigitalProjectStatus(str, enum.Enum):
    in_progress = "in_progress"
    completed = "completed"
    overdue = "overdue"


class DigitalService(Base):
    __tablename__ = "digital_services"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True)


class DigitalProject(Base):
    __tablename__ = "digital_projects"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    service_id = Column(Integer, ForeignKey("digital_services.id"))
    executor_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    deadline = Column(DateTime, nullable=True)
    monthly = Column(Boolean, default=False)
    logo = Column(String, nullable=True)
    status = Column(Enum(DigitalProjectStatus), default=DigitalProjectStatus.in_progress)

    project = relationship("Project")
    service = relationship("DigitalService")
    executor = relationship("User")
    
    # Add cascade delete relationships
    tasks = relationship("DigitalProjectTask", back_populates="project", cascade="all, delete-orphan")
    finances = relationship("DigitalProjectFinance", back_populates="project", cascade="all, delete-orphan")
    expenses = relationship("DigitalProjectExpense", back_populates="project", cascade="all, delete-orphan")


class DigitalProjectTask(Base):
    __tablename__ = "digital_project_tasks"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("digital_projects.id", ondelete="CASCADE"))
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    links = Column(Text, nullable=True)
    deadline = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    high_priority = Column(Boolean, default=False, nullable=True)
    status = Column(String, default="in_progress")  # in_progress, completed

    project = relationship("DigitalProject", back_populates="tasks")


class DigitalProjectFinance(Base):
    __tablename__ = "digital_project_finances"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("digital_projects.id", ondelete="CASCADE"), unique=True)
    tax_id = Column(Integer, ForeignKey("taxes.id"), nullable=True)
    cost_without_tax = Column(Float, nullable=True)
    cost_with_tax = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project = relationship("DigitalProject", back_populates="finances")
    tax = relationship("Tax")


class DigitalProjectExpense(Base):
    __tablename__ = "digital_project_expenses"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("digital_projects.id", ondelete="CASCADE"))
    description = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    date = Column(Date, default=datetime.utcnow().date)
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("DigitalProject", back_populates="expenses")


class FileCategoryEnum(str, enum.Enum):
    general = "general"
    project = "project"

class ResourceFile(Base):
    __tablename__ = "resource_files"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    size = Column(Integer, default=0)
    mime_type = Column(String, nullable=True)
    category = Column(Enum(FileCategoryEnum), default=FileCategoryEnum.general)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    uploaded_by = Column(Integer, ForeignKey("users.id"))
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    download_count = Column(Integer, default=0)
    is_favorite = Column(Boolean, default=False)

    project = relationship("Project")
    uploader = relationship("User")


class EmployeeExpense(Base):
    __tablename__ = "employee_expenses"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    name = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    description = Column(Text, nullable=True)
    date = Column(Date, default=datetime.utcnow().date)
    created_at = Column(DateTime, default=datetime.utcnow)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)

    user = relationship("User", back_populates="expenses")
    project = relationship("Project")


class Setting(Base):
    __tablename__ = "settings"

    key = Column(String, primary_key=True)
    value = Column(String, nullable=False)


# Модели для канбан-доски заявок
class LeadStatusEnum(str, enum.Enum):
    new = "new"  # Новая заявка
    in_progress = "in_progress"  # Взят в обработку
    negotiation = "negotiation"  # Созвон / переговоры
    proposal = "proposal"  # К.П.
    waiting = "waiting"  # Ожидание ответа
    success = "success"  # Успешно
    rejected = "rejected"  # Отказ


class Lead(Base):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    source = Column(String, nullable=False)  # Источник заявки
    status = Column(Enum(LeadStatusEnum), default=LeadStatusEnum.new)
    manager_id = Column(Integer, ForeignKey("users.id"))
    
    # Основные поля
    client_name = Column(String, nullable=True)
    client_contact = Column(String, nullable=True)
    company_name = Column(String, nullable=True)  # Название компании клиента
    description = Column(Text, nullable=True)
    
    # Поля для этапа КП
    proposal_amount = Column(Float, nullable=True)  # Сумма предложения
    proposal_date = Column(DateTime, nullable=True)
    
    # Поля для финального этапа
    deal_amount = Column(Float, nullable=True)  # Сумма сделки
    rejection_reason = Column(Text, nullable=True)  # Причина отказа
    
    # Даты и таймеры
    created_at = Column(DateTime, default=get_local_time_utc5)
    updated_at = Column(DateTime, default=get_local_time_utc5, onupdate=get_local_time_utc5)
    last_activity_at = Column(DateTime, default=get_local_time_utc5)
    reminder_date = Column(DateTime, nullable=True)  # Дата напоминания
    waiting_started_at = Column(DateTime, nullable=True)  # Начало ожидания ответа
    
    # Relationships
    manager = relationship("User", backref="leads")
    notes = relationship("LeadNote", back_populates="lead", cascade="all, delete-orphan")
    attachments = relationship("LeadAttachment", back_populates="lead", cascade="all, delete-orphan")
    history = relationship("LeadHistory", back_populates="lead", cascade="all, delete-orphan")


class LeadNote(Base):
    __tablename__ = "lead_notes"

    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(Integer, ForeignKey("leads.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    content = Column(Text, nullable=False)
    lead_status = Column(String, nullable=True)  # Статус заявки на момент создания комментария
    created_at = Column(DateTime, default=get_local_time_utc5)
    
    lead = relationship("Lead", back_populates="notes")
    user = relationship("User")


class LeadAttachment(Base):
    __tablename__ = "lead_attachments"

    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(Integer, ForeignKey("leads.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    file_size = Column(Integer, nullable=True)
    mime_type = Column(String, nullable=True)
    uploaded_at = Column(DateTime, default=get_local_time_utc5)
    
    lead = relationship("Lead", back_populates="attachments")
    user = relationship("User")


class LeadHistory(Base):
    __tablename__ = "lead_history"

    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(Integer, ForeignKey("leads.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    action = Column(String, nullable=False)  # Например: status_changed, note_added, file_attached
    old_value = Column(String, nullable=True)
    new_value = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=get_local_time_utc5)
    
    lead = relationship("Lead", back_populates="history")
    user = relationship("User")


# Модели для интерактивной доски
class WhiteboardProject(Base):
    __tablename__ = "whiteboard_projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=get_local_time_utc5)
    updated_at = Column(DateTime, default=get_local_time_utc5, onupdate=get_local_time_utc5)
    is_archived = Column(Boolean, default=False)
    
    # Relationships
    creator = relationship("User", backref="created_whiteboard_projects")
    permissions = relationship("WhiteboardProjectPermission", back_populates="project", cascade="all, delete-orphan")
    boards = relationship("WhiteboardBoard", back_populates="project", cascade="all, delete-orphan")


class WhiteboardProjectPermission(Base):
    __tablename__ = "whiteboard_project_permissions"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("whiteboard_projects.id"))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    can_view = Column(Boolean, default=True)
    can_edit = Column(Boolean, default=False)
    can_manage = Column(Boolean, default=False)  # Управление правами доступа
    created_at = Column(DateTime, default=get_local_time_utc5)
    
    # Relationships
    project = relationship("WhiteboardProject", back_populates="permissions")
    user = relationship("User", backref="whiteboard_permissions")
    
    # Уникальность по проекту и пользователю
    __table_args__ = (UniqueConstraint("project_id", "user_id"),)


class WhiteboardBoard(Base):
    __tablename__ = "whiteboard_boards"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("whiteboard_projects.id"))
    name = Column(String, nullable=False)
    data = Column(Text, nullable=True)  # JSON данные доски (рисунки, комментарии, стикеры и т.д.)
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=get_local_time_utc5)
    updated_at = Column(DateTime, default=get_local_time_utc5, onupdate=get_local_time_utc5)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    project = relationship("WhiteboardProject", back_populates="boards")
    creator = relationship("User", backref="created_whiteboard_boards")

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
from datetime import datetime, timedelta
import enum

from .database import Base

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
    in_progress = "in_progress"
    done = "done" 
    cancelled = "cancelled"

class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(Text)
    project = Column(String, index=True)
    deadline = Column(DateTime)
    status = Column(Enum(TaskStatus), default=TaskStatus.in_progress)
    task_type = Column(String, nullable=True)
    task_format = Column(String, nullable=True)
    high_priority = Column(Boolean, default=False, nullable=True)
    executor_id = Column(Integer, ForeignKey("users.id"))
    author_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)

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
    
    user = relationship("User", back_populates="expenses")


class Setting(Base):
    __tablename__ = "settings"

    key = Column(String, primary_key=True)
    value = Column(String, nullable=False)

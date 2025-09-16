from datetime import datetime
from datetime import date as DateType  # Rename to avoid conflicts
from typing import Optional, List, Union
from pydantic import BaseModel, field_validator, ConfigDict

class UserBase(BaseModel):
    telegram_username: Optional[str] = None  # Изменили с login на telegram_username
    name: str
    role: str
    birth_date: Optional[DateType] = None

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    telegram_username: Optional[str] = None  # Изменили с login на telegram_username
    name: Optional[str] = None
    password: Optional[str] = None
    role: Optional[str] = None
    birth_date: Optional[DateType] = None

class User(UserBase):
    id: int
    telegram_id: Optional[int] = None
    contract_path: Optional[str] = None
    telegram_registered_at: Optional[datetime] = None
    is_active: bool = True
    model_config = ConfigDict(from_attributes=True)

class TaskBase(BaseModel):
    title: str
    description: Optional[str] = None
    project: Optional[str] = None
    deadline: Optional[datetime] = None
    task_type: Optional[str] = None
    task_format: Optional[str] = None
    high_priority: Optional[bool] = None
    is_recurring: Optional[bool] = None
    recurrence_type: Optional[str] = None  # daily, weekly, monthly
    recurrence_time: Optional[str] = None  # Время повтора в формате HH:MM
    recurrence_days: Optional[str] = None  # Дни недели для daily/weekly (1,2,3,4,5) или день месяца для monthly (15)

class TaskCreate(TaskBase):
    executor_id: Optional[int] = None

class Task(TaskBase):
    id: int
    status: str
    executor_id: Optional[int]
    author_id: Optional[int]
    created_at: datetime
    accepted_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    resume_count: Optional[int] = 0
    high_priority: Optional[bool] = None
    is_recurring: Optional[bool] = None
    recurrence_type: Optional[str] = None
    next_run_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

class TaskWithDetails(Task):
    created_by: Optional[str] = None  # Имя создателя задачи
    project_name: Optional[str] = None  # Название проекта для отображения
    model_config = ConfigDict(from_attributes=True)

class OperatorBase(BaseModel):
    name: str
    role: str
    color: Optional[str] = None
    price_per_video: Optional[float] = None
    is_salaried: Optional[bool] = False
    monthly_salary: Optional[int] = None

class OperatorCreate(OperatorBase):
    pass

class OperatorUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    color: Optional[str] = None
    price_per_video: Optional[float] = None
    is_salaried: Optional[bool] = None
    monthly_salary: Optional[int] = None

class Operator(OperatorBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

class Project(BaseModel):
    id: int
    name: str
    logo: str | None = None
    posts_count: int = 0
    start_date: datetime | None = None
    end_date: datetime | None = None
    high_priority: bool = False
    is_archived: bool | None = False

    model_config = ConfigDict(from_attributes=True)

class ProjectCreate(BaseModel):
    name: str
    high_priority: bool = False


class ProjectUpdate(BaseModel):
    posts_count: Optional[int] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    high_priority: Optional[bool] = None


class ProjectPostBase(BaseModel):
    date: datetime
    posts_per_day: int = 1
    post_type: str
    status: Optional[str] = None


class ProjectPostCreate(ProjectPostBase):
    pass


class ProjectPost(ProjectPostBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

class ShootingBase(BaseModel):
    title: str
    project: Optional[str] = None
    quantity: Optional[int] = None
    operator_id: int
    managers: Optional[List[int]] = None
    datetime: datetime
    end_datetime: datetime

class ShootingComplete(BaseModel):
    quantity: int
    managers: Optional[List[int]] = None
    operators: Optional[List[int]] = None

class ShootingCreate(ShootingBase):
    pass

class Shooting(ShootingBase):
    id: int
    completed: bool = False
    completed_quantity: Optional[int] = None
    completed_managers: Optional[List[int]] = None
    completed_operators: Optional[List[int]] = None

    @field_validator('managers', 'completed_managers', 'completed_operators', mode='before')
    def parse_managers(cls, v):
        if isinstance(v, str):
            if not v:
                return []
            return [int(x) for x in v.split(',') if x]
        return v
    model_config = ConfigDict(from_attributes=True)


class ExpenseBase(BaseModel):
    name: str
    amount: float
    comment: Optional[str] = None


class ExpenseCreate(ExpenseBase):
    pass


class Expense(ExpenseBase):
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ClientExpenseBase(BaseModel):
    name: str
    amount: float
    comment: Optional[str] = None


class ClientExpenseCreate(ClientExpenseBase):
    pass


class ClientExpense(ClientExpenseBase):
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ClientExpenseClose(BaseModel):
    amount: float
    comment: Optional[str] = None


class TaxBase(BaseModel):
    name: str
    rate: float


class TaxCreate(TaxBase):
    pass


class Tax(TaxBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


class ExpenseReportRow(BaseModel):
    name: str
    quantity: int
    unit_avg: float


class ReceiptBase(BaseModel):
    name: str
    amount: float
    comment: Optional[str] = None


class ReceiptCreate(ReceiptBase):
    pass


class Receipt(ReceiptBase):
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ProjectReportBase(BaseModel):
    contract_amount: Optional[float] = None
    receipts: Optional[float] = None


class ProjectReportUpdate(ProjectReportBase):
    pass


class ProjectReport(ProjectReportBase):
    project_id: int
    total_expenses: float
    receipts_list: List[Receipt]
    client_expenses: List[ClientExpense]
    debt: float
    positive_balance: float
    expenses: List[Expense]
    model_config = ConfigDict(from_attributes=True)


class DigitalServiceBase(BaseModel):
    name: str


class DigitalServiceCreate(DigitalServiceBase):
    pass


class DigitalService(DigitalServiceBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


class DigitalProjectCreate(BaseModel):
    project_id: int
    service_id: int
    executor_id: int
    deadline: datetime | None = None
    monthly: bool = False
    status: str = "in_progress"


class DigitalProject(BaseModel):
    id: int
    project: str
    service: str
    executor: str
    project_id: int
    service_id: int
    executor_id: int
    created_at: datetime
    deadline: datetime | None = None
    monthly: bool
    logo: str | None = None
    high_priority: bool = False
    status: str = "in_progress"

    model_config = ConfigDict(from_attributes=True)


class LinkItem(BaseModel):
    name: str
    url: str


class DigitalTaskCreate(BaseModel):
    title: str
    description: str | None = None
    deadline: datetime | None = None
    links: list[LinkItem] = []
    high_priority: bool = False
    status: str = "in_progress"


class DigitalTask(DigitalTaskCreate):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TimezoneUpdate(BaseModel):
    timezone: str


class DigitalProjectFinanceBase(BaseModel):
    tax_id: Optional[int] = None
    cost_without_tax: Optional[float] = None
    cost_with_tax: Optional[float] = None


class DigitalProjectFinanceCreate(DigitalProjectFinanceBase):
    project_id: int


class DigitalProjectFinanceUpdate(DigitalProjectFinanceBase):
    pass


class DigitalProjectFinance(DigitalProjectFinanceBase):
    id: int
    project_id: int
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class DigitalProjectExpenseBase(BaseModel):
    description: str
    amount: float
    date: Optional[str] = None


class DigitalProjectExpenseCreate(DigitalProjectExpenseBase):
    project_id: int


class DigitalProjectExpense(DigitalProjectExpenseBase):
    id: int
    project_id: int
    created_at: datetime
    
    @field_validator('date', mode='before')
    def serialize_date(cls, v):
        if isinstance(v, date):
            return v.strftime('%Y-%m-%d')
        return v
    
    model_config = ConfigDict(from_attributes=True)


class ResourceFileBase(BaseModel):
    name: str
    category: str = "general"
    project_id: Optional[int] = None
    is_favorite: bool = False


class ResourceFileCreate(ResourceFileBase):
    pass


class ResourceFile(ResourceFileBase):
    id: int
    filename: str
    file_path: str
    size: int
    mime_type: Optional[str] = None
    uploaded_by: int
    uploaded_at: datetime
    download_count: int = 0
    project: Optional[Project] = None
    uploader: Optional[User] = None
    
    model_config = ConfigDict(from_attributes=True)


class ResourceFileUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    project_id: Optional[int] = None
    is_favorite: Optional[bool] = None


# User Statistics Schemas
class WeeklyActivity(BaseModel):
    day: str
    completed_tasks: int
    assigned_tasks: int


class ProductivityMetrics(BaseModel):
    average_tasks_per_day: float
    best_streak: int
    current_day_tasks: int


class RecentTask(BaseModel):
    title: str
    project: str
    completed_at: str
    status: str


class UserStats(BaseModel):
    total_projects: int
    completed_tasks: int
    active_days: int
    total_assigned_tasks: int
    pending_tasks: int
    completion_rate: float
    this_month_tasks: int
    this_month_completions: int
    weekly_activity: List[WeeklyActivity]
    recent_tasks: List[RecentTask]


# Expense Category Schemas
class ExpenseCategoryBase(BaseModel):
    name: str
    description: Optional[str] = None
    is_active: bool = True


class ExpenseCategoryCreate(ExpenseCategoryBase):
    pass


class ExpenseCategoryUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class ExpenseCategory(ExpenseCategoryBase):
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# Common Expense Schemas
class CommonExpenseBase(BaseModel):
    name: str
    amount: float
    description: Optional[str] = None
    category_id: Optional[int] = None
    date: Optional[DateType] = None


class CommonExpenseCreate(CommonExpenseBase):
    pass


class CommonExpenseUpdate(BaseModel):
    name: Optional[str] = None
    amount: Optional[float] = None
    description: Optional[str] = None
    category_id: Optional[int] = None
    date: Optional[DateType] = None


class CommonExpense(CommonExpenseBase):
    id: int
    created_at: datetime
    created_by: Optional[int] = None
    category: Optional[ExpenseCategory] = None
    creator: Optional[User] = None
    date: Optional[DateType] = None
    
    model_config = ConfigDict(from_attributes=True)


# Project Expense Create Schema
class ProjectExpenseCreate(BaseModel):
    name: str
    amount: float
    description: Optional[str] = None
    project_id: int
    category_id: Optional[int] = None
    date: Optional[DateType] = None

# Project Expense Update Schema
class ProjectExpenseUpdate(BaseModel):
    name: Optional[str] = None
    amount: Optional[float] = None
    description: Optional[str] = None
    category_id: Optional[int] = None
    date: Optional[DateType] = None


class ProjectExpense(BaseModel):
    id: int
    project_id: int
    category_id: Optional[int] = None
    name: str
    amount: float
    description: Optional[str] = None
    date: DateType
    created_at: datetime
    created_by: Optional[int] = None
    category: Optional[ExpenseCategory] = None
    creator: Optional[User] = None
    model_config = ConfigDict(from_attributes=True)

# Extended Project Expense Schema for the new page
class ProjectExpenseDetailed(BaseModel):
    id: int
    project_id: int
    project_name: str
    category_id: Optional[int] = None
    category_name: Optional[str] = None
    name: str
    amount: float
    description: Optional[str] = None
    date: DateType
    created_at: datetime
    created_by: Optional[int] = None
    creator_name: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


# Expense Report Schemas
class ExpenseReportItem(BaseModel):
    id: int
    name: str
    amount: float
    description: Optional[str] = None
    date: DateType
    category_name: Optional[str] = None
    project_name: Optional[str] = None
    expense_type: str  # "project" or "common"
    created_by_name: Optional[str] = None


class ExpenseReport(BaseModel):
    total_amount: float
    project_expenses: float
    common_expenses: float
    items: List[ExpenseReportItem]
    categories_breakdown: dict  # category_name -> total_amount


# Employee Expense Schemas
class EmployeeExpenseBase(BaseModel):
    name: str
    amount: float
    description: Optional[str] = None
    date: Optional[DateType] = None
    project_id: Optional[int] = None

class EmployeeExpenseCreate(EmployeeExpenseBase):
    pass

class EmployeeExpenseUpdate(BaseModel):
    name: Optional[str] = None
    amount: Optional[float] = None
    description: Optional[str] = None
    date: Optional[DateType] = None
    project_id: Optional[int] = None

class EmployeeExpense(EmployeeExpenseBase):
    id: int
    user_id: Optional[int] = None
    created_at: datetime
    date: DateType  # Override the optional date from base class
    user: Optional[User] = None
    project: Optional["Project"] = None
    model_config = ConfigDict(from_attributes=True)


# Expense Report Schemas for the new expense reports page
class ExpenseReportSummary(BaseModel):
    total_expenses: float  # Общие расходы
    project_expenses: float  # Проектные расходы
    employee_expenses: float  # Расходы сотрудников
    
class EmployeeExpenseReport(BaseModel):
    user_id: int
    user_name: str
    role: str
    total_amount: float
    expenses: List[EmployeeExpense]
    
class OperatorExpenseReport(BaseModel):
    operator_id: int
    operator_name: str
    role: str  # mobile/video
    is_salaried: bool
    monthly_salary: Optional[int]
    price_per_video: Optional[int]
    videos_completed: int
    total_amount: float  # Общая сумма за завершенные видео или зарплата


# Схемы для канбан-доски заявок
class LeadBase(BaseModel):
    title: str
    source: str
    client_name: Optional[str] = None
    client_contact: Optional[str] = None
    company_name: Optional[str] = None
    description: Optional[str] = None


class LeadCreate(LeadBase):
    manager_id: Optional[int] = None


class LeadUpdate(BaseModel):
    title: Optional[str] = None
    source: Optional[str] = None
    status: Optional[str] = None
    manager_id: Optional[int] = None
    client_name: Optional[str] = None
    client_contact: Optional[str] = None
    company_name: Optional[str] = None
    description: Optional[str] = None
    proposal_amount: Optional[float] = None
    proposal_date: Optional[datetime] = None
    deal_amount: Optional[float] = None
    rejection_reason: Optional[str] = None
    reminder_date: Optional[datetime] = None
    waiting_started_at: Optional[datetime] = None


class LeadNoteBase(BaseModel):
    content: str


class LeadNoteCreate(LeadNoteBase):
    pass


class LeadNote(LeadNoteBase):
    id: int
    lead_id: int
    user_id: int
    lead_status: Optional[str] = None
    created_at: datetime
    user: Optional[User] = None
    model_config = ConfigDict(from_attributes=True)


class LeadAttachmentBase(BaseModel):
    filename: str


class LeadAttachment(LeadAttachmentBase):
    id: int
    lead_id: int
    user_id: int
    file_path: str
    file_size: Optional[int] = None
    mime_type: Optional[str] = None
    uploaded_at: datetime
    user: Optional[User] = None
    model_config = ConfigDict(from_attributes=True)


class LeadHistoryItem(BaseModel):
    id: int
    action: str
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    description: Optional[str] = None
    created_at: datetime
    user: Optional[User] = None
    model_config = ConfigDict(from_attributes=True)


class Lead(LeadBase):
    id: int
    status: str
    manager_id: Optional[int] = None
    proposal_amount: Optional[float] = None
    proposal_date: Optional[datetime] = None
    deal_amount: Optional[float] = None
    rejection_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    last_activity_at: datetime
    reminder_date: Optional[datetime] = None
    waiting_started_at: Optional[datetime] = None
    
    manager: Optional[User] = None
    notes: List[LeadNote] = []
    attachments: List[LeadAttachment] = []
    history: List[LeadHistoryItem] = []
    
    model_config = ConfigDict(from_attributes=True)


# Схемы для аналитики канбан-доски
class LeadStats(BaseModel):
    total_leads: int
    active_leads: int
    success_leads: int
    rejected_leads: int
    conversion_rate: float
    average_processing_time: int  # В секундах
    
    
class LeadsByStatus(BaseModel):
    new: int
    in_progress: int
    negotiation: int
    proposal: int
    waiting: int
    success: int
    rejected: int


class LeadAnalytics(BaseModel):
    stats: LeadStats
    leads_by_status: LeadsByStatus
    leads_by_source: dict  # source -> count
    rejection_reasons: dict  # reason -> count
    top_managers: dict  # manager_name -> successful_deals_count


# Схемы для аналитики по типам услуг
class ServiceTypeData(BaseModel):
    service_type: str
    created: int
    completed: int
    efficiency: float  # процент завершенных от созданных

class EmployeeServiceAnalytics(BaseModel):
    employee_id: int
    employee_name: str
    service_types: List[ServiceTypeData]
    total_created: int
    total_completed: int
    overall_efficiency: float

class ServiceTypesAnalytics(BaseModel):
    employees: List[EmployeeServiceAnalytics]
    period_start: str
    period_end: str
    total_service_types: List[str]


# Схемы для интерактивной доски
class WhiteboardProjectPermissionBase(BaseModel):
    user_id: int
    can_view: bool = True
    can_edit: bool = False
    can_manage: bool = False


class WhiteboardProjectPermissionCreate(WhiteboardProjectPermissionBase):
    pass


class WhiteboardProjectPermission(WhiteboardProjectPermissionBase):
    id: int
    project_id: int
    created_at: datetime
    user: Optional[User] = None
    model_config = ConfigDict(from_attributes=True)


class WhiteboardProjectBase(BaseModel):
    name: str
    description: Optional[str] = None


class WhiteboardProjectCreate(WhiteboardProjectBase):
    permissions: List[WhiteboardProjectPermissionCreate] = []


class WhiteboardProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_archived: Optional[bool] = None


class WhiteboardProject(WhiteboardProjectBase):
    id: int
    created_by: int
    created_at: datetime
    updated_at: datetime
    is_archived: bool = False
    creator: Optional[User] = None
    permissions: List[WhiteboardProjectPermission] = []
    model_config = ConfigDict(from_attributes=True)


class WhiteboardBoardBase(BaseModel):
    name: str
    data: Optional[str] = None


class WhiteboardBoardCreate(WhiteboardBoardBase):
    project_id: int


class WhiteboardBoardUpdate(BaseModel):
    name: Optional[str] = None
    data: Optional[str] = None
    is_active: Optional[bool] = None


class WhiteboardBoard(WhiteboardBoardBase):
    id: int
    project_id: int
    created_by: int
    created_at: datetime
    updated_at: datetime
    is_active: bool = True
    creator: Optional[User] = None
    project: Optional[WhiteboardProject] = None
    model_config = ConfigDict(from_attributes=True)


# Схемы для Telegram авторизации
class TelegramAuthRequest(BaseModel):
    telegram_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None


class TelegramAuthResponse(BaseModel):
    success: bool
    message: str
    user: Optional[User] = None


class TelegramStatusRequest(BaseModel):
    telegram_id: Optional[int] = None
    username: Optional[str] = None


class TelegramStatusResponse(BaseModel):
    has_access: bool
    user: Optional[User] = None
    message: str

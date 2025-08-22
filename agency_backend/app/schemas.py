from datetime import datetime, date
from typing import Optional, List
from pydantic import BaseModel, field_validator, ConfigDict

class UserBase(BaseModel):
    login: str
    name: str
    role: str
    birth_date: Optional[date] = None

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    login: Optional[str] = None
    name: Optional[str] = None
    password: Optional[str] = None
    role: Optional[str] = None
    birth_date: Optional[date] = None

class User(UserBase):
    id: int
    contract_path: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

class TaskBase(BaseModel):
    title: str
    description: Optional[str] = None
    project: Optional[str] = None
    deadline: Optional[datetime] = None
    task_type: Optional[str] = None
    task_format: Optional[str] = None
    high_priority: Optional[bool] = False

class TaskCreate(TaskBase):
    executor_id: Optional[int] = None

class Task(TaskBase):
    id: int
    status: str
    executor_id: Optional[int]
    author_id: Optional[int]
    created_at: datetime
    finished_at: Optional[datetime] = None
    high_priority: bool = False
    model_config = ConfigDict(from_attributes=True)

class OperatorBase(BaseModel):
    name: str
    role: str
    color: Optional[str] = None
    price_per_video: Optional[float] = None

class OperatorCreate(OperatorBase):
    pass

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


class ExpenseItemBase(BaseModel):
    name: str
    is_common: bool = False
    unit_cost: int | None = None


class ExpenseItemCreate(ExpenseItemBase):
    pass


class ExpenseItem(ExpenseItemBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


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

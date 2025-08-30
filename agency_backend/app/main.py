from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import inspect, text, create_engine
from dotenv import load_dotenv
from datetime import datetime
from typing import List, Optional
import os
from fastapi.staticfiles import StaticFiles
import json
import shutil
import tempfile

from . import models, schemas, crud, auth
from .database import engine, Base, SessionLocal

load_dotenv()
Base.metadata.create_all(bind=engine)


def ensure_digital_task_priority_column():
    with engine.connect() as conn:
        inspector = inspect(conn)
        cols = [c["name"] for c in inspector.get_columns("digital_project_tasks")]
        if "high_priority" not in cols:
            conn.execute(text(
                "ALTER TABLE digital_project_tasks "
                "ADD COLUMN high_priority BOOLEAN DEFAULT 0"
            ))
        if "status" not in cols:
            conn.execute(text(
                "ALTER TABLE digital_project_tasks "
                "ADD COLUMN status VARCHAR(50) DEFAULT 'in_progress'"
            ))
        conn.commit()


ensure_digital_task_priority_column()


def create_default_admin():
    db = SessionLocal()
    try:
        if not crud.get_user_by_login(db, "admin"):
            admin = schemas.UserCreate(
                login="admin",
                name="Administrator",
                password="admin123",
                role=models.RoleEnum.admin,
            )
            crud.create_user(db, admin)
    finally:
        db.close()

def create_default_taxes():
    db = SessionLocal()
    try:
        if not crud.get_taxes(db):
            crud.create_tax(db, "ЯТТ", 0.95)
            crud.create_tax(db, "ООО", 0.83)
            crud.create_tax(db, "Нал", 1.0)
    finally:
        db.close()


def create_default_timezone():
    db = SessionLocal()
    try:
        if not db.query(models.Setting).filter(models.Setting.key == "timezone").first():
            db.add(models.Setting(key="timezone", value="Asia/Tashkent"))
            db.commit()
    finally:
        db.close()


create_default_admin()
create_default_taxes()
create_default_timezone()

# Ensure the static directory exists before mounting it
os.makedirs("static", exist_ok=True)

app = FastAPI(title="Agency API")
app.mount("/static", StaticFiles(directory="static"), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(auth.get_db)):
    user = auth.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    access_token = auth.create_access_token(data={"sub": user.login})
    return {"access_token": access_token, "token_type": "bearer"}


@app.post("/users/", response_model=schemas.User)
def create_user(user: schemas.UserCreate, db: Session = Depends(auth.get_db), current: models.User = Depends(auth.get_current_active_user)):
    if current.role != models.RoleEnum.admin:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    db_user = crud.get_user_by_login(db, user.login)
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    return crud.create_user(db, user)


@app.get("/users/", response_model=list[schemas.User])
def list_users(db: Session = Depends(auth.get_db), current: models.User = Depends(auth.get_current_active_user)):
    return crud.get_users(db)


@app.get("/users/me", response_model=schemas.User)
def read_current_user(current: models.User = Depends(auth.get_current_active_user)):
    return current


@app.put("/users/{user_id}", response_model=schemas.User)
def update_user(user_id: int, user: schemas.UserUpdate, db: Session = Depends(auth.get_db), current: models.User = Depends(auth.get_current_active_user)):
    if current.role != models.RoleEnum.admin:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    updated = crud.update_user(db, user_id, user)
    if not updated:
        raise HTTPException(status_code=404, detail="User not found")
    return updated


@app.delete("/users/{user_id}")
def delete_user(user_id: int, db: Session = Depends(auth.get_db), current: models.User = Depends(auth.get_current_active_user)):
    if current.role != models.RoleEnum.admin:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    crud.delete_user(db, user_id)
    return {"ok": True}


@app.put("/users/{user_id}/toggle-status")
def toggle_user_status(user_id: int, db: Session = Depends(auth.get_db), current: models.User = Depends(auth.get_current_active_user)):
    if current.role != models.RoleEnum.admin:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    user = crud.get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Toggle between inactive and the user's previous role (default to designer)
    if user.role == models.RoleEnum.inactive:
        # Reactivate user - default to designer role
        user.role = models.RoleEnum.designer
    else:
        # Deactivate user
        user.role = models.RoleEnum.inactive
    
    db.commit()
    db.refresh(user)
    return user


@app.post("/users/{user_id}/contract")
def upload_contract(
    user_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(auth.get_db),
    current: models.User = Depends(auth.get_current_active_user),
):
    if current.role != models.RoleEnum.admin:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    user = crud.get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    os.makedirs("contracts", exist_ok=True)
    path = os.path.join("contracts", f"{user_id}_{file.filename}")
    with open(path, "wb") as f:
        f.write(file.file.read())
    user.contract_path = path
    db.commit()
    db.refresh(user)
    return {"contract_path": path}


@app.get("/users/{user_id}/contract")
def download_contract(
    user_id: int,
    db: Session = Depends(auth.get_db),
    current: models.User = Depends(auth.get_current_active_user),
):
    user = crud.get_user(db, user_id)
    if not user or not user.contract_path:
        raise HTTPException(status_code=404, detail="Contract not found")
    return FileResponse(user.contract_path, filename=os.path.basename(user.contract_path))


@app.delete("/users/{user_id}/contract")
def delete_contract(
    user_id: int,
    db: Session = Depends(auth.get_db),
    current: models.User = Depends(auth.get_current_active_user),
):
    if current.role != models.RoleEnum.admin:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    user = crud.get_user(db, user_id)
    if not user or not user.contract_path:
        raise HTTPException(status_code=404, detail="Contract not found")
    try:
        os.remove(user.contract_path)
    except FileNotFoundError:
        pass
    user.contract_path = None
    db.commit()
    db.refresh(user)
    return {"ok": True}


@app.get("/tasks/", response_model=list[schemas.Task])
def read_tasks(skip: int = 0, limit: int = 10000, db: Session = Depends(auth.get_db), current: models.User = Depends(auth.get_current_active_user)):
    return crud.get_tasks_for_user(db, current, skip=skip, limit=limit)


@app.get("/tasks/all", response_model=list[schemas.Task])
def read_all_tasks(skip: int = 0, limit: int = 10000, db: Session = Depends(auth.get_db), current: models.User = Depends(auth.get_current_active_user)):
    # Only admins and smm_managers can access all tasks for reports
    if current.role not in [models.RoleEnum.admin, models.RoleEnum.smm_manager]:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return crud.get_tasks(db, skip=skip, limit=limit)


@app.post("/tasks/", response_model=schemas.Task)
def create_task(task: schemas.TaskCreate, db: Session = Depends(auth.get_db), current: models.User = Depends(auth.get_current_active_user)):
    return crud.create_task(db, task, author_id=current.id)


@app.put("/tasks/{task_id}", response_model=schemas.Task)
def update_task(task_id: int, task: schemas.TaskCreate, db: Session = Depends(auth.get_db), current: models.User = Depends(auth.get_current_active_user)):
    updated = crud.update_task(db, task_id, task)
    if not updated:
        raise HTTPException(status_code=404, detail="Task not found")
    return updated


@app.delete("/tasks/{task_id}")
def delete_task(task_id: int, db: Session = Depends(auth.get_db), current: models.User = Depends(auth.get_current_active_user)):
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if current.id not in [task.author_id, task.executor_id]:
        raise HTTPException(status_code=403, detail="Not allowed")
    crud.delete_task(db, task_id)
    return {"ok": True}


@app.patch("/tasks/{task_id}/status", response_model=schemas.Task)
def update_task_status(
    task_id: int,
    status: str,
    db: Session = Depends(auth.get_db),
    current: models.User = Depends(auth.get_current_active_user),
):
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if current.id not in [task.executor_id, task.author_id]:
        raise HTTPException(status_code=403, detail="Not allowed")
    return crud.update_task_status(db, task_id, status)


@app.get("/operators/", response_model=list[schemas.Operator])
def list_operators(db: Session = Depends(auth.get_db), current: models.User = Depends(auth.get_current_active_user)):
    return crud.get_operators(db)


@app.post("/operators/", response_model=schemas.Operator)
def create_operator(op: schemas.OperatorCreate, db: Session = Depends(auth.get_db), current: models.User = Depends(auth.get_current_active_user)):
    if current.role != models.RoleEnum.admin:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return crud.create_operator(db, op)


@app.put("/operators/{op_id}", response_model=schemas.Operator)
def update_operator(op_id: int, op: schemas.OperatorCreate, db: Session = Depends(auth.get_db), current: models.User = Depends(auth.get_current_active_user)):
    if current.role != models.RoleEnum.admin:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    updated = crud.update_operator(db, op_id, op)
    if not updated:
        raise HTTPException(status_code=404, detail="Operator not found")
    return updated


@app.delete("/operators/{op_id}")
def delete_operator(op_id: int, db: Session = Depends(auth.get_db), current: models.User = Depends(auth.get_current_active_user)):
    if current.role != models.RoleEnum.admin:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    crud.delete_operator(db, op_id)
    return {"ok": True}


@app.get("/projects/", response_model=list[schemas.Project])
def list_projects(db: Session = Depends(auth.get_db), current: models.User = Depends(auth.get_current_active_user), include_archived: bool = False):
    return crud.get_projects(db, include_archived=include_archived)


@app.post("/projects/", response_model=schemas.Project)
def create_project(project: schemas.ProjectCreate, db: Session = Depends(auth.get_db), current: models.User = Depends(auth.get_current_active_user)):
    if current.role != models.RoleEnum.admin:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return crud.create_project(db, project)


@app.get("/projects/{project_id}", response_model=schemas.Project)
def get_project(project_id: int, db: Session = Depends(auth.get_db), current: models.User = Depends(auth.get_current_active_user)):
    proj = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")
    return proj


@app.put("/projects/{project_id}", response_model=schemas.Project)
def update_project(project_id: int, project: schemas.ProjectCreate, db: Session = Depends(auth.get_db), current: models.User = Depends(auth.get_current_active_user)):
    if current.role != models.RoleEnum.admin:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    updated = crud.update_project(db, project_id, project)
    if not updated:
        raise HTTPException(status_code=404, detail="Project not found")
    return updated


@app.put("/projects/{project_id}/info", response_model=schemas.Project)
def update_project_info(project_id: int, data: schemas.ProjectUpdate, db: Session = Depends(auth.get_db), current: models.User = Depends(auth.get_current_active_user)):
    updated = crud.update_project_info(db, project_id, data)
    if not updated:
        raise HTTPException(status_code=404, detail="Project not found")
    return updated


@app.delete("/projects/{project_id}")
def delete_project(project_id: int, db: Session = Depends(auth.get_db), current: models.User = Depends(auth.get_current_active_user)):
    if current.role != models.RoleEnum.admin:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    crud.delete_project(db, project_id)
    return {"ok": True}


@app.put("/projects/{project_id}/toggle-archive")
def toggle_project_archive(project_id: int, db: Session = Depends(auth.get_db), current: models.User = Depends(auth.get_current_active_user)):
    if current.role != models.RoleEnum.admin:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    project.is_archived = not project.is_archived
    db.commit()
    db.refresh(project)
    return project


@app.post("/projects/{project_id}/logo")
async def upload_project_logo(
    project_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(auth.get_db),
    current: models.User = Depends(auth.get_current_active_user),
):
    if current.role != models.RoleEnum.admin:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    os.makedirs("static/projects", exist_ok=True)
    path = f"static/projects/{project_id}_{file.filename}"
    with open(path, "wb") as f:
        f.write(await file.read())
    proj = crud.set_project_logo(db, project_id, path)
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"logo": path}


@app.delete("/projects/{project_id}/logo")
def delete_project_logo(
    project_id: int,
    db: Session = Depends(auth.get_db),
    current: models.User = Depends(auth.get_current_active_user),
):
    if current.role != models.RoleEnum.admin:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    proj = crud.set_project_logo(db, project_id, None)
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"ok": True}


@app.get("/projects/{project_id}/report", response_model=schemas.ProjectReport)
def get_project_report(
    project_id: int,
    month: int | None = None,
    db: Session = Depends(auth.get_db),
    current: models.User = Depends(auth.get_current_active_user),
):
    today = datetime.utcnow()
    m = month or today.month
    start = datetime(today.year, m, 1)
    end_month = m + 1
    end_year = today.year
    if end_month > 12:
        end_month = 1
        end_year += 1
    end = datetime(end_year, end_month, 1)
    report = crud.get_or_create_report(db, project_id, m, today.year)
    expenses = crud.get_expenses(db, project_id, start, end)
    client_expenses = crud.get_client_expenses(db, project_id, start, end)
    receipts_list = crud.get_receipts(db, project_id, start, end)
    receipts_sum = sum(r.amount for r in receipts_list)
    client_sum = sum(e.amount for e in client_expenses)
    total_expenses = sum(e.amount for e in expenses) + client_sum
    debt = report.contract_amount - receipts_sum + client_sum
    positive_balance = receipts_sum - total_expenses
    return schemas.ProjectReport(
        project_id=project_id,
        contract_amount=report.contract_amount,
        receipts=receipts_sum,
        receipts_list=receipts_list,
        client_expenses=client_expenses,
        total_expenses=total_expenses,
        debt=debt,
        positive_balance=positive_balance,
        expenses=expenses,
    )


@app.put("/projects/{project_id}/report", response_model=schemas.ProjectReport)
def update_project_report(
    project_id: int,
    data: schemas.ProjectReportUpdate,
    month: int | None = None,
    db: Session = Depends(auth.get_db),
    current: models.User = Depends(auth.get_current_active_user),
):
    today = datetime.utcnow()
    m = month or today.month
    start = datetime(today.year, m, 1)
    end_month = m + 1
    end_year = today.year
    if end_month > 12:
        end_month = 1
        end_year += 1
    end = datetime(end_year, end_month, 1)
    report = crud.update_report(db, project_id, data, m, today.year)
    expenses = crud.get_expenses(db, project_id, start, end)
    client_expenses = crud.get_client_expenses(db, project_id, start, end)
    receipts_list = crud.get_receipts(db, project_id, start, end)
    receipts_sum = sum(r.amount for r in receipts_list)
    client_sum = sum(e.amount for e in client_expenses)
    total_expenses = sum(e.amount for e in expenses) + client_sum
    debt = report.contract_amount - receipts_sum + client_sum
    positive_balance = receipts_sum - total_expenses
    return schemas.ProjectReport(
        project_id=project_id,
        contract_amount=report.contract_amount,
        receipts=receipts_sum,
        receipts_list=receipts_list,
        client_expenses=client_expenses,
        total_expenses=total_expenses,
        debt=debt,
        positive_balance=positive_balance,
        expenses=expenses,
    )


@app.get("/projects/{project_id}/expenses", response_model=list[schemas.Expense])
def list_expenses(
    project_id: int,
    month: int | None = None,
    db: Session = Depends(auth.get_db),
    current: models.User = Depends(auth.get_current_active_user),
):
    today = datetime.utcnow()
    m = month or today.month
    start = datetime(today.year, m, 1)
    end_month = m + 1
    end_year = today.year
    if end_month > 12:
        end_month = 1
        end_year += 1
    end = datetime(end_year, end_month, 1)
    return crud.get_expenses(db, project_id, start, end)


@app.post("/projects/{project_id}/expenses", response_model=schemas.Expense)
def add_expense(
    project_id: int,
    exp: schemas.ExpenseCreate,
    month: int | None = None,
    db: Session = Depends(auth.get_db),
    current: models.User = Depends(auth.get_current_active_user),
):
    today = datetime.utcnow()
    return crud.create_expense(db, project_id, exp, month or today.month, today.year)


@app.put("/expenses/{expense_id}", response_model=schemas.Expense)
def edit_expense(expense_id: int, exp: schemas.ExpenseCreate, db: Session = Depends(auth.get_db), current: models.User = Depends(auth.get_current_active_user)):
    updated = crud.update_expense(db, expense_id, exp)
    if not updated:
        raise HTTPException(status_code=404, detail="Expense not found")
    return updated


@app.delete("/expenses/{expense_id}")
def remove_expense(expense_id: int, db: Session = Depends(auth.get_db), current: models.User = Depends(auth.get_current_active_user)):
    crud.delete_expense(db, expense_id)
    return {"ok": True}


@app.get("/projects/{project_id}/client_expenses", response_model=list[schemas.ClientExpense])
def list_client_expenses(
    project_id: int,
    month: int | None = None,
    db: Session = Depends(auth.get_db),
    current: models.User = Depends(auth.get_current_active_user),
):
    today = datetime.utcnow()
    m = month or today.month
    start = datetime(today.year, m, 1)
    end_month = m + 1
    end_year = today.year
    if end_month > 12:
        end_month = 1
        end_year += 1
    end = datetime(end_year, end_month, 1)
    return crud.get_client_expenses(db, project_id, start, end)


@app.post("/projects/{project_id}/client_expenses", response_model=schemas.ClientExpense)
def add_client_expense(
    project_id: int,
    exp: schemas.ClientExpenseCreate,
    month: int | None = None,
    db: Session = Depends(auth.get_db),
    current: models.User = Depends(auth.get_current_active_user),
):
    today = datetime.utcnow()
    return crud.create_client_expense(db, project_id, exp, month or today.month, today.year)


@app.put("/client_expenses/{expense_id}", response_model=schemas.ClientExpense)
def edit_client_expense(expense_id: int, exp: schemas.ClientExpenseCreate, db: Session = Depends(auth.get_db), current: models.User = Depends(auth.get_current_active_user)):
    updated = crud.update_client_expense(db, expense_id, exp)
    if not updated:
        raise HTTPException(status_code=404, detail="Client expense not found")
    return updated


@app.post("/client_expenses/{expense_id}/close", response_model=schemas.ClientExpense | None)
def close_client_expense(expense_id: int, data: schemas.ClientExpenseClose, db: Session = Depends(auth.get_db), current: models.User = Depends(auth.get_current_active_user)):
    return crud.close_client_expense(db, expense_id, data.amount, data.comment)


@app.delete("/client_expenses/{expense_id}")
def remove_client_expense(expense_id: int, db: Session = Depends(auth.get_db), current: models.User = Depends(auth.get_current_active_user)):
    crud.delete_client_expense(db, expense_id)
    return {"ok": True}


@app.get("/projects/{project_id}/receipts", response_model=list[schemas.Receipt])
def list_receipts(
    project_id: int,
    month: int | None = None,
    db: Session = Depends(auth.get_db),
    current: models.User = Depends(auth.get_current_active_user),
):
    today = datetime.utcnow()
    m = month or today.month
    start = datetime(today.year, m, 1)
    end_month = m + 1
    end_year = today.year
    if end_month > 12:
        end_month = 1
        end_year += 1
    end = datetime(end_year, end_month, 1)
    return crud.get_receipts(db, project_id, start, end)


@app.post("/projects/{project_id}/receipts", response_model=schemas.Receipt)
def add_receipt(
    project_id: int,
    rec: schemas.ReceiptCreate,
    month: int | None = None,
    db: Session = Depends(auth.get_db),
    current: models.User = Depends(auth.get_current_active_user),
):
    today = datetime.utcnow()
    return crud.create_receipt(db, project_id, rec, month or today.month, today.year)


@app.put("/receipts/{receipt_id}", response_model=schemas.Receipt)
def edit_receipt(receipt_id: int, rec: schemas.ReceiptCreate, db: Session = Depends(auth.get_db), current: models.User = Depends(auth.get_current_active_user)):
    updated = crud.update_receipt(db, receipt_id, rec)
    if not updated:
        raise HTTPException(status_code=404, detail="Receipt not found")
    return updated


@app.delete("/receipts/{receipt_id}")
def remove_receipt(receipt_id: int, db: Session = Depends(auth.get_db), current: models.User = Depends(auth.get_current_active_user)):
    crud.delete_receipt(db, receipt_id)
    return {"ok": True}


@app.get("/expense_items/", response_model=list[schemas.ExpenseItem])
def list_expense_items(is_common: bool | None = None, db: Session = Depends(auth.get_db), current: models.User = Depends(auth.get_current_active_user)):
    return crud.get_expense_items(db, is_common)


@app.post("/expense_items/", response_model=schemas.ExpenseItem)
def create_expense_item(item: schemas.ExpenseItemCreate, db: Session = Depends(auth.get_db), current: models.User = Depends(auth.get_current_active_user)):
    if current.role != models.RoleEnum.admin:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return crud.create_expense_item(db, item.name, item.is_common, item.unit_cost or 0)


@app.put("/expense_items/{item_id}", response_model=schemas.ExpenseItem)
def update_expense_item(item_id: int, item: schemas.ExpenseItemCreate, db: Session = Depends(auth.get_db), current: models.User = Depends(auth.get_current_active_user)):
    if current.role != models.RoleEnum.admin:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    updated = crud.update_expense_item(db, item_id, item.name, item.is_common, item.unit_cost)
    if not updated:
        raise HTTPException(status_code=404, detail="Expense item not found")
    return updated


@app.delete("/expense_items/{item_id}")
def delete_expense_item(item_id: int, db: Session = Depends(auth.get_db), current: models.User = Depends(auth.get_current_active_user)):
    if current.role != models.RoleEnum.admin:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    crud.delete_expense_item(db, item_id)
    return {"ok": True}


@app.get("/taxes/", response_model=list[schemas.Tax])
def list_taxes(db: Session = Depends(auth.get_db), current: models.User = Depends(auth.get_current_active_user)):
    return crud.get_taxes(db)


@app.post("/taxes/", response_model=schemas.Tax)
def create_tax(tax: schemas.TaxCreate, db: Session = Depends(auth.get_db), current: models.User = Depends(auth.get_current_active_user)):
    if current.role != models.RoleEnum.admin:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return crud.create_tax(db, tax.name, tax.rate)


@app.put("/taxes/{tax_id}", response_model=schemas.Tax)
def update_tax(tax_id: int, tax: schemas.TaxCreate, db: Session = Depends(auth.get_db), current: models.User = Depends(auth.get_current_active_user)):
    if current.role != models.RoleEnum.admin:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    updated = crud.update_tax(db, tax_id, tax.name, tax.rate)
    if not updated:
        raise HTTPException(status_code=404, detail="Tax not found")
    return updated


@app.delete("/taxes/{tax_id}")
def delete_tax(tax_id: int, db: Session = Depends(auth.get_db), current: models.User = Depends(auth.get_current_active_user)):
    if current.role != models.RoleEnum.admin:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    crud.delete_tax(db, tax_id)
    return {"ok": True}


@app.get("/expenses/report", response_model=list[schemas.ExpenseReportRow])
def expenses_report(
    start: str | None = None,
    end: str | None = None,
    project_id: int | None = None,
    db: Session = Depends(auth.get_db),
    current: models.User = Depends(auth.get_current_active_user),
):
    now = datetime.utcnow()
    if not start or not end:
        start_dt = datetime(now.year, now.month, 1)
        next_month = now.month + 1
        next_year = now.year
        if next_month > 12:
            next_month = 1
            next_year += 1
        end_dt = datetime(next_year, next_month, 1)
    else:
        start_dt = datetime.fromisoformat(start)
        end_dt = datetime.fromisoformat(end)
    rows = crud.get_expenses_report(db, start_dt, end_dt, project_id)
    return [schemas.ExpenseReportRow(name=n, quantity=q, unit_avg=a) for n, q, a in rows]


@app.get("/projects/{project_id}/posts", response_model=list[schemas.ProjectPost])
def list_project_posts(
    project_id: int,
    month: int | None = None,
    year: int | None = None,
    db: Session = Depends(auth.get_db),
    current: models.User = Depends(auth.get_current_active_user),
):
    if month:
        y = year or datetime.utcnow().year
        start = datetime(y, month, 1)
        end_month = month + 1
        end_year = y
        if end_month > 12:
            end_month = 1
            end_year += 1
        end = datetime(end_year, end_month, 1)
        return crud.get_project_posts(db, project_id, start, end)
    return crud.get_project_posts(db, project_id)


@app.post("/projects/{project_id}/posts", response_model=schemas.ProjectPost)
def create_project_post(project_id: int, data: schemas.ProjectPostCreate, db: Session = Depends(auth.get_db), current: models.User = Depends(auth.get_current_active_user)):
    return crud.create_project_post(db, project_id, data)


@app.put("/project_posts/{post_id}", response_model=schemas.ProjectPost)
def update_project_post(post_id: int, data: schemas.ProjectPostCreate, db: Session = Depends(auth.get_db), current: models.User = Depends(auth.get_current_active_user)):
    updated = crud.update_project_post(db, post_id, data)
    if not updated:
        raise HTTPException(status_code=404, detail="Post not found")
    return updated


@app.delete("/project_posts/{post_id}")
def delete_project_post(post_id: int, db: Session = Depends(auth.get_db), current: models.User = Depends(auth.get_current_active_user)):
    crud.delete_project_post(db, post_id)
    return {"ok": True}


@app.get("/shootings/", response_model=list[schemas.Shooting])
def list_shootings(db: Session = Depends(auth.get_db), current: models.User = Depends(auth.get_current_active_user)):
    return crud.get_shootings(db)


def _shoot_perm(user: models.User):
    return user.role in [models.RoleEnum.smm_manager, models.RoleEnum.head_smm, models.RoleEnum.admin]


@app.post("/shootings/", response_model=schemas.Shooting)
def create_shooting(shooting: schemas.ShootingCreate, db: Session = Depends(auth.get_db), current: models.User = Depends(auth.get_current_active_user)):
    if not _shoot_perm(current):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return crud.create_shooting(db, shooting)


@app.put("/shootings/{sid}", response_model=schemas.Shooting)
def update_shooting(sid: int, shooting: schemas.ShootingCreate, db: Session = Depends(auth.get_db), current: models.User = Depends(auth.get_current_active_user)):
    if not _shoot_perm(current):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    updated = crud.update_shooting(db, sid, shooting)
    if not updated:
        raise HTTPException(status_code=404, detail="Shooting not found")
    return updated


@app.delete("/shootings/{sid}")
def delete_shooting(sid: int, db: Session = Depends(auth.get_db), current: models.User = Depends(auth.get_current_active_user)):
    if not _shoot_perm(current):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    crud.delete_shooting(db, sid)
    return {"ok": True}


@app.post("/shootings/{sid}/complete", response_model=schemas.Shooting)
def complete_shooting(sid: int, data: schemas.ShootingComplete, db: Session = Depends(auth.get_db), current: models.User = Depends(auth.get_current_active_user)):
    if not _shoot_perm(current):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    sh = crud.complete_shooting(db, sid, data.quantity, data.managers, data.operators)
    if not sh:
        raise HTTPException(status_code=404, detail="Shooting not found")
    return sh


@app.get("/settings/timezone")
def get_timezone(db: Session = Depends(auth.get_db), current: models.User = Depends(auth.get_current_active_user)):
    setting = db.query(models.Setting).filter(models.Setting.key == "timezone").first()
    return {"timezone": setting.value if setting else "Asia/Tashkent"}


@app.put("/settings/timezone")
def set_timezone(data: schemas.TimezoneUpdate, db: Session = Depends(auth.get_db), current: models.User = Depends(auth.get_current_active_user)):
    if current.role != models.RoleEnum.admin:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    setting = db.query(models.Setting).filter(models.Setting.key == "timezone").first()
    if not setting:
        setting = models.Setting(key="timezone", value=data.timezone)
        db.add(setting)
    else:
        setting.value = data.timezone
    db.commit()
    return {"timezone": setting.value}


@app.get("/digital/services", response_model=list[schemas.DigitalService])
def list_digital_services(db: Session = Depends(auth.get_db), current: models.User = Depends(auth.get_current_active_user)):
    return crud.get_digital_services(db)


@app.post("/digital/services", response_model=schemas.DigitalService)
def create_digital_service(service: schemas.DigitalServiceCreate, db: Session = Depends(auth.get_db), current: models.User = Depends(auth.get_current_active_user)):
    if current.role != models.RoleEnum.admin:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return crud.create_digital_service(db, service.name)


@app.delete("/digital/services/{service_id}")
def delete_digital_service(service_id: int, db: Session = Depends(auth.get_db), current: models.User = Depends(auth.get_current_active_user)):
    if current.role != models.RoleEnum.admin:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    crud.delete_digital_service(db, service_id)
    return {"ok": True}


@app.get("/digital/projects", response_model=list[schemas.DigitalProject])
def list_digital_projects(db: Session = Depends(auth.get_db), current: models.User = Depends(auth.get_current_active_user)):
    return [schemas.DigitalProject(**item) for item in crud.get_digital_projects(db)]


@app.post("/digital/projects", response_model=schemas.DigitalProject)
def create_digital_project(proj: schemas.DigitalProjectCreate, db: Session = Depends(auth.get_db), current: models.User = Depends(auth.get_current_active_user)):
    dp = crud.create_digital_project(db, proj)
    for item in crud.get_digital_projects(db):
        if item["id"] == dp.id:
            return schemas.DigitalProject(**item)
    raise HTTPException(status_code=500, detail="Creation failed")


@app.put("/digital/projects/{project_id}", response_model=schemas.DigitalProject)
def update_digital_project(
    project_id: int,
    proj: schemas.DigitalProjectCreate,
    db: Session = Depends(auth.get_db),
    current: models.User = Depends(auth.get_current_active_user),
):
    dp = crud.update_digital_project(db, project_id, proj)
    if not dp:
        raise HTTPException(status_code=404, detail="Project not found")
    for item in crud.get_digital_projects(db):
        if item["id"] == project_id:
            return schemas.DigitalProject(**item)
    raise HTTPException(status_code=500, detail="Update failed")


@app.put("/digital/projects/{project_id}/status")
def update_digital_project_status(
    project_id: int,
    status: str = Query(...),
    db: Session = Depends(auth.get_db),
    current: models.User = Depends(auth.get_current_active_user),
):
    dp = crud.update_digital_project_status(db, project_id, status)
    if not dp:
        raise HTTPException(status_code=404, detail="Project not found")
    for item in crud.get_digital_projects(db):
        if item["id"] == project_id:
            return schemas.DigitalProject(**item)
    raise HTTPException(status_code=500, detail="Update failed")


@app.delete("/digital/projects/{project_id}")
def delete_digital_project(
    project_id: int,
    db: Session = Depends(auth.get_db),
    current: models.User = Depends(auth.get_current_active_user),
):
    crud.delete_digital_project(db, project_id)
    return {"ok": True}


@app.post("/digital/projects/{project_id}/logo")
async def upload_digital_logo(
    project_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(auth.get_db),
    current: models.User = Depends(auth.get_current_active_user),
):
    os.makedirs("static/digital", exist_ok=True)
    path = f"static/digital/{project_id}_{file.filename}"
    with open(path, "wb") as f:
        f.write(await file.read())
    proj = crud.set_digital_project_logo(db, project_id, path)
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"logo": path}


@app.delete("/digital/projects/{project_id}/logo")
def delete_digital_logo(
    project_id: int,
    db: Session = Depends(auth.get_db),
    current: models.User = Depends(auth.get_current_active_user),
):
    proj = crud.set_digital_project_logo(db, project_id, None)
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"ok": True}


@app.get("/digital/projects/{project_id}/tasks", response_model=list[schemas.DigitalTask])
def list_digital_tasks(
    project_id: int,
    db: Session = Depends(auth.get_db),
    current: models.User = Depends(auth.get_current_active_user),
):
    return [
        schemas.DigitalTask(
            id=t.id,
            title=t.title,
            description=t.description,
            deadline=t.deadline,
            created_at=t.created_at,
            high_priority=t.high_priority,
            status=t.status or "in_progress",
            links=json.loads(t.links or "[]"),
        )
        for t in crud.get_digital_tasks(db, project_id)
    ]


@app.post("/digital/projects/{project_id}/tasks", response_model=schemas.DigitalTask)
def create_digital_task(
    project_id: int,
    task: schemas.DigitalTaskCreate,
    db: Session = Depends(auth.get_db),
    current: models.User = Depends(auth.get_current_active_user),
):
    t = crud.create_digital_task(db, project_id, task)
    return schemas.DigitalTask(
        id=t.id,
        title=t.title,
        description=t.description,
        deadline=t.deadline,
        created_at=t.created_at,
        high_priority=t.high_priority,
        status=t.status or "in_progress",
        links=task.links,
    )


@app.put("/digital/projects/{project_id}/tasks/{task_id}", response_model=schemas.DigitalTask)
def update_digital_task(
    project_id: int,
    task_id: int,
    task: schemas.DigitalTaskCreate,
    db: Session = Depends(auth.get_db),
    current: models.User = Depends(auth.get_current_active_user),
):
    t = crud.update_digital_task(db, task_id, task)
    if not t or t.project_id != project_id:
        raise HTTPException(status_code=404, detail="Task not found")
    return schemas.DigitalTask(
        id=t.id,
        title=t.title,
        description=t.description,
        deadline=t.deadline,
        created_at=t.created_at,
        high_priority=t.high_priority,
        status=t.status or "in_progress",
        links=json.loads(t.links or "[]"),
    )


@app.delete("/digital/projects/{project_id}/tasks/{task_id}")
def delete_digital_task(
    project_id: int,
    task_id: int,
    db: Session = Depends(auth.get_db),
    current: models.User = Depends(auth.get_current_active_user),
):
    crud.delete_digital_task(db, task_id)
    return {"ok": True}


# Digital Project Finance Endpoints
@app.get("/digital/projects/{project_id}/finance", response_model=schemas.DigitalProjectFinance)
def get_digital_project_finance(
    project_id: int,
    db: Session = Depends(auth.get_db),
    current: models.User = Depends(auth.get_current_active_user),
):
    finance = crud.get_digital_project_finance(db, project_id)
    if not finance:
        return schemas.DigitalProjectFinance(
            id=0,
            project_id=project_id,
            tax_id=None,
            cost_without_tax=None,
            cost_with_tax=None,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
    return finance


@app.post("/digital/projects/{project_id}/finance", response_model=schemas.DigitalProjectFinance)
def create_or_update_digital_project_finance(
    project_id: int,
    finance_data: schemas.DigitalProjectFinanceUpdate,
    db: Session = Depends(auth.get_db),
    current: models.User = Depends(auth.get_current_active_user),
):
    finance = crud.get_digital_project_finance(db, project_id)
    if finance:
        return crud.update_digital_project_finance(db, project_id, finance_data)
    else:
        finance_create = schemas.DigitalProjectFinanceCreate(
            project_id=project_id,
            **finance_data.dict()
        )
        return crud.create_digital_project_finance(db, finance_create)


@app.get("/digital/projects/{project_id}/expenses", response_model=List[schemas.DigitalProjectExpense])
def get_digital_project_expenses(
    project_id: int,
    db: Session = Depends(auth.get_db),
    current: models.User = Depends(auth.get_current_active_user),
):
    return crud.get_digital_project_expenses(db, project_id)


@app.post("/digital/projects/{project_id}/expenses", response_model=schemas.DigitalProjectExpense)
def create_digital_project_expense(
    project_id: int,
    expense_data: schemas.DigitalProjectExpenseBase,
    db: Session = Depends(auth.get_db),
    current: models.User = Depends(auth.get_current_active_user),
):
    expense_create = schemas.DigitalProjectExpenseCreate(
        project_id=project_id,
        **expense_data.dict()
    )
    return crud.create_digital_project_expense(db, expense_create)


@app.delete("/digital/projects/{project_id}/expenses/{expense_id}")
def delete_digital_project_expense(
    project_id: int,
    expense_id: int,
    db: Session = Depends(auth.get_db),
    current: models.User = Depends(auth.get_current_active_user),
):
    crud.delete_digital_project_expense(db, expense_id)
    return {"ok": True}


@app.get("/analytics")
def get_analytics(
    time_range: str = "30d",
    db: Session = Depends(auth.get_db),
    current: models.User = Depends(auth.get_current_active_user),
):
    """Получение аналитических данных"""
    from datetime import datetime, timedelta
    from sqlalchemy import func, and_
    
    # Определяем период для анализа
    end_date = datetime.utcnow()
    if time_range == "7d":
        start_date = end_date - timedelta(days=7)
    elif time_range == "30d":
        start_date = end_date - timedelta(days=30)
    elif time_range == "90d":
        start_date = end_date - timedelta(days=90)
    elif time_range == "1y":
        start_date = end_date - timedelta(days=365)
    else:
        start_date = end_date - timedelta(days=30)
    
    # Статистика задач
    total_tasks = db.query(models.Task).count()
    completed_tasks = db.query(models.Task).filter(models.Task.status == "done").count()
    in_progress_tasks = db.query(models.Task).filter(models.Task.status == "in_progress").count()
    overdue_tasks = db.query(models.Task).filter(
        and_(models.Task.deadline < datetime.utcnow(), models.Task.status != "done")
    ).count()
    
    # Статистика проектов
    total_projects = db.query(models.Project).count()
    # Упрощаем логику - считаем проекты по датам
    current_date = datetime.utcnow()
    active_projects = db.query(models.Project).filter(
        and_(models.Project.start_date <= current_date, models.Project.end_date >= current_date)
    ).count()
    completed_projects = db.query(models.Project).filter(models.Project.end_date < current_date).count()
    
    # Производительность команды (упрощенная версия)
    users = db.query(models.User).filter(models.User.role != models.RoleEnum.admin).all()
    team_productivity = []
    for user in users:
        tasks_completed = db.query(models.Task).filter(
            and_(
                models.Task.executor_id == user.id,
                models.Task.status == "done",
                models.Task.finished_at >= start_date
            )
        ).count()
        
        # Простая формула эффективности (можно улучшить)
        efficiency = min(95, max(50, 70 + (tasks_completed * 2)))
        
        team_productivity.append({
            "name": user.name,
            "tasksCompleted": tasks_completed,
            "efficiency": efficiency
        })
    
    # Задачи по месяцам (последние 5 месяцев)
    tasks_by_month = []
    for i in range(5):
        month_start = datetime.utcnow().replace(day=1) - timedelta(days=30 * i)
        month_end = month_start.replace(day=28) + timedelta(days=4)  # переходим к концу месяца
        month_end = month_end - timedelta(days=month_end.day - 1) + timedelta(days=31)
        month_end = min(month_end, month_start.replace(day=28) + timedelta(days=4))
        
        created_count = db.query(models.Task).filter(
            and_(models.Task.created_at >= month_start, models.Task.created_at < month_end)
        ).count()
        
        completed_count = db.query(models.Task).filter(
            and_(
                models.Task.finished_at >= month_start,
                models.Task.finished_at < month_end,
                models.Task.status == "done"
            )
        ).count()
        
        tasks_by_month.append({
            "month": month_start.strftime("%b"),
            "created": created_count,
            "completed": completed_count
        })
    
    tasks_by_month.reverse()  # Сортируем по возрастанию
    
    # Задачи по типам (упрощенная версия)
    task_types = [
        {"name": "Дизайн", "value": 35, "color": "#8B5CF6"},
        {"name": "Контент", "value": 28, "color": "#06B6D4"},
        {"name": "Съемки", "value": 20, "color": "#10B981"},
        {"name": "Стратегия", "value": 17, "color": "#F59E0B"}
    ]
    
    return {
        "tasksStats": {
            "total": total_tasks,
            "completed": completed_tasks,
            "inProgress": in_progress_tasks,
            "overdue": overdue_tasks
        },
        "projectsStats": {
            "total": total_projects,
            "active": active_projects,
            "completed": completed_projects
        },
        "teamProductivity": team_productivity,
        "tasksByMonth": tasks_by_month,
        "tasksByType": task_types
    }



# Resource Files Endpoints
@app.get("/resource-files/", response_model=List[schemas.ResourceFile])
def list_resource_files(
    category: Optional[str] = None,
    project_id: Optional[int] = None,
    db: Session = Depends(auth.get_db),
    current: models.User = Depends(auth.get_current_active_user),
):
    return crud.get_resource_files(db, category=category, project_id=project_id)


@app.get("/resource-files/{file_id}", response_model=schemas.ResourceFile)
def get_resource_file(
    file_id: int,
    db: Session = Depends(auth.get_db),
    current: models.User = Depends(auth.get_current_active_user),
):
    file = crud.get_resource_file(db, file_id)
    if not file:
        raise HTTPException(status_code=404, detail="File not found")
    return file


@app.post("/resource-files/", response_model=schemas.ResourceFile)
async def upload_resource_file(
    name: str = Form(...),
    category: str = Form("general"),
    project_id: Optional[int] = Form(None),
    is_favorite: bool = Form(False),
    file: UploadFile = File(...),
    db: Session = Depends(auth.get_db),
    current: models.User = Depends(auth.get_current_active_user),
):
    # Ensure the files directory exists
    os.makedirs("files", exist_ok=True)
    
    # Generate unique filename to avoid conflicts
    import uuid
    unique_id = uuid.uuid4()
    file_extension = file.filename.split('.')[-1] if '.' in file.filename else ''
    unique_filename = f"{unique_id}.{file_extension}" if file_extension else str(unique_id)
    file_path = os.path.join("files", unique_filename)
    
    # Save file to disk
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)
    
    file_data = schemas.ResourceFileCreate(
        name=name,
        category=category,
        project_id=project_id,
        is_favorite=is_favorite
    )
    
    return crud.create_resource_file(
        db=db,
        file_data=file_data,
        filename=file.filename,
        file_path=file_path,
        size=len(content),
        mime_type=file.content_type or "application/octet-stream",
        user_id=current.id
    )


@app.put("/resource-files/{file_id}", response_model=schemas.ResourceFile)
def update_resource_file(
    file_id: int,
    file_data: schemas.ResourceFileUpdate,
    db: Session = Depends(auth.get_db),
    current: models.User = Depends(auth.get_current_active_user),
):
    updated_file = crud.update_resource_file(db, file_id, file_data)
    if not updated_file:
        raise HTTPException(status_code=404, detail="File not found")
    return updated_file


@app.delete("/resource-files/{file_id}")
def delete_resource_file(
    file_id: int,
    db: Session = Depends(auth.get_db),
    current: models.User = Depends(auth.get_current_active_user),
):
    file = crud.get_resource_file(db, file_id)
    if not file:
        raise HTTPException(status_code=404, detail="File not found")
    
    # Delete file from disk
    try:
        if os.path.exists(file.file_path):
            os.remove(file.file_path)
    except Exception as e:
        print(f"Error deleting file {file.file_path}: {e}")
    
    crud.delete_resource_file(db, file_id)
    return {"ok": True}


@app.get("/resource-files/{file_id}/download")
def download_resource_file(
    file_id: int,
    db: Session = Depends(auth.get_db),
    current: models.User = Depends(auth.get_current_active_user),
):
    file = crud.get_resource_file(db, file_id)
    if not file:
        raise HTTPException(status_code=404, detail="File not found")
    
    if not os.path.exists(file.file_path):
        raise HTTPException(status_code=404, detail="File not found on disk")
    
    # Increment download count
    crud.increment_file_download_count(db, file_id)
    
    return FileResponse(
        file.file_path,
        filename=file.filename,
        media_type=file.mime_type
    )


@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy", 
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }


@app.post("/admin/import-database")
async def import_database(
    file: UploadFile = File(...),
    db: Session = Depends(auth.get_db),
    current: models.User = Depends(auth.get_current_active_user),
):
    """Импорт данных из загруженной БД"""
    if current.role != models.RoleEnum.admin:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    if not file.filename.endswith('.db'):
        raise HTTPException(status_code=400, detail="Only .db files are allowed")
    
    # Сохраняем временный файл
    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as tmp_file:
        shutil.copyfileobj(file.file, tmp_file)
        tmp_path = tmp_file.name
    
    try:
        # Подключаемся к загруженной БД
        source_engine = create_engine(f"sqlite:///{tmp_path}")
        
        # Проверяем существование таблиц
        source_inspector = inspect(source_engine)
        available_tables = source_inspector.get_table_names()
        
        if not available_tables:
            raise HTTPException(status_code=400, detail="Database file appears to be empty or corrupted")
        
        source_session = Session(bind=source_engine)
        
        imported_data = {
            "users": 0,
            "projects": 0,
            "tasks": 0,
            "digital_projects": 0,
            "operators": 0,
            "expense_items": 0,
            "taxes": 0
        }
        
        # Импортируем пользователей
        if "users" in available_tables:
            try:
                # Используем прямой SQL запрос для большей гибкости
                cursor = source_session.connection().connection.cursor()
                cursor.execute("SELECT * FROM users")
                rows = cursor.fetchall()
                
                # Получаем названия колонок
                cursor.execute("PRAGMA table_info(users)")
                columns = [col[1] for col in cursor.fetchall()]
                
                for row in rows:
                    # Создаем словарь из строки
                    user_data = dict(zip(columns, row))
                    
                    # Проверяем, существует ли пользователь
                    existing_user = db.query(models.User).filter(models.User.login == user_data['login']).first()
                    if not existing_user:
                        new_user = models.User(
                            login=user_data['login'],
                            name=user_data['name'],
                            hashed_password=user_data['hashed_password'],
                            role=user_data['role'],
                            birth_date=user_data.get('birth_date'),
                            contract_path=user_data.get('contract_path')
                        )
                        db.add(new_user)
                        imported_data["users"] += 1
                        
            except Exception as e:
                print(f"Error importing users: {e}")
                db.rollback()
                pass
        
        # Импортируем проекты
        project_mapping = {}
        if "projects" in available_tables:
            try:
                # Используем прямой SQL запрос для большей гибкости
                cursor = source_session.connection().connection.cursor()
                cursor.execute("SELECT * FROM projects")
                rows = cursor.fetchall()
                
                # Получаем названия колонок
                cursor.execute("PRAGMA table_info(projects)")
                columns = [col[1] for col in cursor.fetchall()]
                
                for row in rows:
                    # Создаем словарь из строки
                    project_data = dict(zip(columns, row))
                    
                    # Проверяем, существует ли проект с таким названием
                    existing_project = db.query(models.Project).filter(models.Project.name == project_data['name']).first()
                    if not existing_project:
                        # Парсим даты
                        start_date = None
                        end_date = None
                        
                        if project_data.get('start_date'):
                            try:
                                if isinstance(project_data['start_date'], str):
                                    start_date = datetime.fromisoformat(project_data['start_date'].replace(' ', 'T'))
                                else:
                                    start_date = project_data['start_date']
                            except:
                                start_date = None
                        
                        if project_data.get('end_date'):
                            try:
                                if isinstance(project_data['end_date'], str):
                                    end_date = datetime.fromisoformat(project_data['end_date'].replace(' ', 'T'))
                                else:
                                    end_date = project_data['end_date']
                            except:
                                end_date = None
                        
                        new_project = models.Project(
                            name=project_data['name'],
                            logo=project_data.get('logo'),
                            start_date=start_date,
                            end_date=end_date,
                            is_archived=bool(project_data.get('is_archived', False))
                        )
                        db.add(new_project)
                        db.flush()  # Чтобы получить ID
                        imported_data["projects"] += 1
                        
                        # Сохраняем соответствие старого и нового ID
                        project_mapping[project_data['id']] = new_project.id
                    else:
                        project_mapping[project_data['id']] = existing_project.id
                        
            except Exception as e:
                print(f"Error importing projects: {e}")
                db.rollback()
                pass
        
        # Специальный импорт для БД tasks.db из Downloads
        if "tasks" in available_tables and len(available_tables) <= 2:  # Только tasks и sqlite_sequence
            try:
                cursor = source_session.connection().connection.cursor()
                cursor.execute("SELECT * FROM tasks")
                rows = cursor.fetchall()
                
                cursor.execute("PRAGMA table_info(tasks)")
                columns = [col[1] for col in cursor.fetchall()]
                
                # Сначала создаем пользователей на основе уникальных дизайнеров/менеджеров/админов
                all_users = set()
                for row in rows:
                    task_data = dict(zip(columns, row))
                    if task_data.get('designer') and task_data['designer'].strip():
                        all_users.add(task_data['designer'].strip())
                    if task_data.get('manager') and task_data['manager'].strip():
                        all_users.add(task_data['manager'].strip())
                    if task_data.get('admin') and task_data['admin'].strip():
                        all_users.add(task_data['admin'].strip())
                
                user_mapping = {}
                for username in all_users:
                    if username and username.strip():
                        # Проверяем, не существует ли уже пользователь
                        existing_user = db.query(models.User).filter(models.User.login == username.lower().replace(' ', '_')).first()
                        if not existing_user:
                            new_user = models.User(
                                login=username.lower().replace(' ', '_'),
                                name=username,
                                hashed_password='$2b$12$imported_user_needs_password_reset',
                                role='designer'
                            )
                            db.add(new_user)
                            db.flush()
                            user_mapping[username] = new_user.id
                            imported_data["users"] += 1
                        else:
                            user_mapping[username] = existing_user.id
                
                # Создаем проекты на основе уникальных названий проектов
                all_projects = set()
                for row in rows:
                    task_data = dict(zip(columns, row))
                    if task_data.get('project') and task_data['project'].strip():
                        all_projects.add(task_data['project'].strip())
                
                project_mapping = {}
                for project_name in all_projects:
                    if project_name and project_name.strip():
                        existing_project = db.query(models.Project).filter(models.Project.name == project_name).first()
                        if not existing_project:
                            new_project = models.Project(
                                name=project_name
                            )
                            db.add(new_project)
                            db.flush()
                            project_mapping[project_name] = new_project.id
                            imported_data["projects"] += 1
                        else:
                            project_mapping[project_name] = existing_project.id
                
                # Теперь импортируем все задачи
                default_admin = db.query(models.User).filter(models.User.role == 'admin').first()
                
                for row in rows:
                    task_data = dict(zip(columns, row))
                    
                    # Определяем автора и исполнителя
                    designer = (task_data.get('designer') or '').strip()
                    manager = (task_data.get('manager') or '').strip()
                    admin = (task_data.get('admin') or '').strip()
                    
                    executor_id = user_mapping.get(designer) if designer else None
                    author_id = user_mapping.get(manager or admin) if (manager or admin) else None
                    
                    # Если не найден исполнитель или автор, используем дефолтного админа
                    if not executor_id and default_admin:
                        executor_id = default_admin.id
                    if not author_id and default_admin:
                        author_id = default_admin.id
                    
                    if executor_id and author_id:
                        # Конвертируем статус
                        status_mapping = {
                            'completed': 'done',
                            'cancelled': 'cancelled',
                            'in_progress': 'in_progress',
                            'pending': 'in_progress'
                        }
                        status = status_mapping.get(task_data.get('status', ''), 'in_progress')
                        
                        # Конвертируем дату
                        deadline_str = task_data.get('deadline', '')
                        deadline = None
                        if deadline_str:
                            try:
                                # Попробуем разные форматы даты
                                if '.' in deadline_str and ':' in deadline_str:
                                    deadline = datetime.strptime(deadline_str, '%d.%m.%Y %H:%M')
                                elif '.' in deadline_str:
                                    deadline = datetime.strptime(deadline_str, '%d.%m.%Y')
                            except:
                                pass
                        
                        # Создаем задачу
                        new_task = models.Task(
                            title=task_data.get('description', 'Импортированная задача')[:255],  # Ограничиваем длину
                            description=task_data.get('description', ''),
                            project=task_data.get('project', ''),
                            deadline=deadline,
                            status=status,
                            task_type=task_data.get('content_type'),
                            task_format=task_data.get('format'),
                            high_priority=False,
                            author_id=author_id,
                            executor_id=executor_id,
                            finished_at=datetime.fromisoformat(task_data['updated_at']) if status == 'done' and task_data.get('updated_at') else None,
                            created_at=datetime.fromisoformat(task_data['created_at']) if task_data.get('created_at') else datetime.utcnow()
                        )
                        db.add(new_task)
                        imported_data["tasks"] += 1
                        
            except Exception as e:
                print(f"Error importing from Downloads tasks.db: {e}")
                db.rollback()
                pass
        
        # Стандартный импорт задач для других БД
        elif "tasks" in available_tables:
            try:
                # Используем прямой SQL запрос для большей гибкости  
                cursor = source_session.connection().connection.cursor()
                cursor.execute("SELECT * FROM tasks")  # Импортируем все задачи
                rows = cursor.fetchall()
                
                # Получаем названия колонок
                cursor.execute("PRAGMA table_info(tasks)")
                columns = [col[1] for col in cursor.fetchall()]
                
                for row in rows:
                    # Создаем словарь из строки
                    task_data = dict(zip(columns, row))
                    
                    # Находим автора и исполнителя
                    author = None
                    executor = None
                    
                    if task_data.get('author_id'):
                        # Пытаемся найти пользователя с тем же ID (если он уже импортирован)
                        author = db.query(models.User).filter(models.User.id == task_data['author_id']).first()
                        # Если не найден, берем первого админа
                        if not author:
                            author = db.query(models.User).filter(models.User.role == 'admin').first()
                    
                    if task_data.get('executor_id'):
                        # Пытаемся найти пользователя с тем же ID (если он уже импортирован)
                        executor = db.query(models.User).filter(models.User.id == task_data['executor_id']).first()
                        # Если не найден, берем первого доступного пользователя
                        if not executor:
                            executor = db.query(models.User).first()
                    
                    if author and executor:
                        # Проверяем, не существует ли уже такая задача
                        existing_task = db.query(models.Task).filter(
                            models.Task.title == task_data['title'],
                            models.Task.deadline == task_data.get('deadline')
                        ).first()
                        
                        if not existing_task:
                            # Парсим даты
                            deadline = None
                            if task_data.get('deadline'):
                                try:
                                    if isinstance(task_data['deadline'], str):
                                        deadline = datetime.fromisoformat(task_data['deadline'].replace(' ', 'T'))
                                    else:
                                        deadline = task_data['deadline']
                                except:
                                    deadline = None
                            
                            finished_at = None
                            if task_data.get('finished_at'):
                                try:
                                    if isinstance(task_data['finished_at'], str):
                                        finished_at = datetime.fromisoformat(task_data['finished_at'].replace(' ', 'T'))
                                    else:
                                        finished_at = task_data['finished_at']
                                except:
                                    finished_at = None
                            
                            created_at = datetime.utcnow()
                            if task_data.get('created_at'):
                                try:
                                    if isinstance(task_data['created_at'], str):
                                        created_at = datetime.fromisoformat(task_data['created_at'].replace(' ', 'T'))
                                    else:
                                        created_at = task_data['created_at']
                                except:
                                    created_at = datetime.utcnow()
                            
                            new_task = models.Task(
                                title=task_data['title'],
                                description=task_data.get('description', ''),
                                project=task_data.get('project', ''),
                                deadline=deadline,
                                status=task_data.get('status', 'in_progress'),
                                task_type=task_data.get('task_type'),
                                task_format=task_data.get('task_format'),
                                high_priority=bool(task_data.get('high_priority', False)),
                                author_id=author.id,
                                executor_id=executor.id,
                                finished_at=finished_at,
                                created_at=created_at
                            )
                            db.add(new_task)
                            imported_data["tasks"] += 1
                            
            except Exception as e:
                print(f"Error importing tasks: {e}")
                db.rollback()
                pass
        
        # Импортируем цифровые проекты
        if "digital_projects" in available_tables:
            try:
                cursor = source_session.connection().connection.cursor()
                cursor.execute("SELECT * FROM digital_projects")
                rows = cursor.fetchall()
                
                cursor.execute("PRAGMA table_info(digital_projects)")
                columns = [col[1] for col in cursor.fetchall()]
                
                for row in rows:
                    digital_data = dict(zip(columns, row))
                    
                    # Находим проект и исполнителя
                    project_id = project_mapping.get(digital_data.get('project_id'))
                    executor = db.query(models.User).first()  # Используем первого доступного пользователя
                    service = db.query(models.DigitalService).first()  # Используем первый доступный сервис
                    
                    if project_id and executor:
                        # Проверяем, не существует ли уже такой цифровой проект
                        existing = db.query(models.DigitalProject).filter(
                            models.DigitalProject.project_id == project_id,
                            models.DigitalProject.executor_id == executor.id
                        ).first()
                        
                        if not existing:
                            # Парсим дату deadline
                            deadline = None
                            if digital_data.get('deadline'):
                                try:
                                    if isinstance(digital_data['deadline'], str):
                                        deadline = datetime.fromisoformat(digital_data['deadline'].replace(' ', 'T'))
                                    else:
                                        deadline = digital_data['deadline']
                                except:
                                    deadline = None
                            
                            new_digital = models.DigitalProject(
                                project_id=project_id,
                                service_id=service.id if service else None,
                                executor_id=executor.id,
                                deadline=deadline,
                                monthly=bool(digital_data.get('monthly', False)),
                                logo=digital_data.get('logo'),
                                status=digital_data.get('status', 'in_progress')
                            )
                            db.add(new_digital)
                            imported_data["digital_projects"] += 1
            except Exception as e:
                print(f"Error importing digital projects: {e}")
                db.rollback()
                pass
        
        # Импортируем операторов
        if "operators" in available_tables:
            try:
                cursor = source_session.connection().connection.cursor()
                cursor.execute("SELECT * FROM operators")
                rows = cursor.fetchall()
                
                cursor.execute("PRAGMA table_info(operators)")
                columns = [col[1] for col in cursor.fetchall()]
                
                for row in rows:
                    operator_data = dict(zip(columns, row))
                    existing = db.query(models.Operator).filter(models.Operator.name == operator_data['name']).first()
                    if not existing:
                        new_operator = models.Operator(
                            name=operator_data['name'],
                            role=operator_data.get('role', 'mobile'),
                            color=operator_data.get('color', '#ff0000'),
                            price_per_video=operator_data.get('price_per_video', 0)
                        )
                        db.add(new_operator)
                        imported_data["operators"] += 1
            except Exception as e:
                print(f"Error importing operators: {e}")
                db.rollback()
                pass
        
        # Импортируем статьи расходов
        if "expense_items" in available_tables:
            try:
                cursor = source_session.connection().connection.cursor()
                cursor.execute("SELECT * FROM expense_items")
                rows = cursor.fetchall()
                
                cursor.execute("PRAGMA table_info(expense_items)")
                columns = [col[1] for col in cursor.fetchall()]
                
                for row in rows:
                    item_data = dict(zip(columns, row))
                    existing = db.query(models.ExpenseItem).filter(models.ExpenseItem.name == item_data['name']).first()
                    if not existing:
                        new_item = models.ExpenseItem(
                            name=item_data['name'],
                            is_common=bool(item_data.get('is_common', True)),
                            unit_cost=item_data.get('unit_cost', 0)
                        )
                        db.add(new_item)
                        imported_data["expense_items"] += 1
            except Exception as e:
                print(f"Error importing expense items: {e}")
                db.rollback()
                pass
        
        # Импортируем налоги
        if "taxes" in available_tables:
            try:
                cursor = source_session.connection().connection.cursor()
                cursor.execute("SELECT * FROM taxes")
                rows = cursor.fetchall()
                
                cursor.execute("PRAGMA table_info(taxes)")
                columns = [col[1] for col in cursor.fetchall()]
                
                for row in rows:
                    tax_data = dict(zip(columns, row))
                    existing = db.query(models.Tax).filter(models.Tax.name == tax_data['name']).first()
                    if not existing:
                        new_tax = models.Tax(
                            name=tax_data['name'],
                            rate=float(tax_data.get('rate', 1.0))
                        )
                        db.add(new_tax)
                        imported_data["taxes"] += 1
            except Exception as e:
                print(f"Error importing taxes: {e}")
                db.rollback()
                pass
        
        # Сохраняем изменения
        db.commit()
        
        # Закрываем сессию источника
        source_session.close()
        
        return {
            "success": True,
            "message": "Database imported successfully",
            "imported": imported_data,
            "available_tables": available_tables
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")
    finally:
        # Удаляем временный файл
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


@app.get("/admin/export-database")
async def export_database(
    db: Session = Depends(auth.get_db),
    current: models.User = Depends(auth.get_current_active_user),
):
    """Экспорт текущей базы данных"""
    if current.role != models.RoleEnum.admin:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    # Путь к текущей БД
    db_url = str(db.bind.url).replace('sqlite:///', '')
    
    if not os.path.exists(db_url):
        raise HTTPException(status_code=404, detail="Database file not found")
    
    # Создаем имя файла с датой
    import datetime
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"database_export_{timestamp}.db"
    
    return FileResponse(
        path=db_url,
        filename=filename,
        media_type='application/octet-stream'
    )


@app.delete("/admin/clear-database")
async def clear_database(
    db: Session = Depends(auth.get_db),
    current: models.User = Depends(auth.get_current_active_user),
):
    """Полная очистка базы данных (кроме текущего админа)"""
    if current.role != models.RoleEnum.admin:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    try:
        # Счетчики для отчета
        deleted_counts = {
            "tasks": 0,
            "projects": 0,
            "users": 0,
            "digital_projects": 0,
            "operators": 0,
            "expenses": 0,
            "receipts": 0,
            "shootings": 0,
            "posts": 0,
            "files": 0,
            "taxes": 0,
            "expense_items": 0
        }
        
        # Безопасное удаление с проверкой существования моделей
        
        # Удаляем задачи
        if hasattr(models, 'Task'):
            deleted_counts["tasks"] = db.query(models.Task).count()
            db.query(models.Task).delete()
        
        # Удаляем посты проектов
        if hasattr(models, 'ProjectPost'):
            deleted_counts["posts"] = db.query(models.ProjectPost).count()
            db.query(models.ProjectPost).delete()
        
        # Удаляем съемки
        if hasattr(models, 'Shooting'):
            deleted_counts["shootings"] = db.query(models.Shooting).count()
            db.query(models.Shooting).delete()
        
        # Удаляем расходы и поступления
        expenses_count = 0
        if hasattr(models, 'ProjectExpense'):
            expenses_count += db.query(models.ProjectExpense).count()
            db.query(models.ProjectExpense).delete()
        if hasattr(models, 'ProjectClientExpense'):
            expenses_count += db.query(models.ProjectClientExpense).count()
            db.query(models.ProjectClientExpense).delete()
        deleted_counts["expenses"] = expenses_count
        
        if hasattr(models, 'ProjectReceipt'):
            deleted_counts["receipts"] = db.query(models.ProjectReceipt).count()
            db.query(models.ProjectReceipt).delete()
        
        # Удаляем отчеты
        if hasattr(models, 'ProjectReport'):
            db.query(models.ProjectReport).delete()
        
        # Удаляем цифровые проекты и связанные данные
        if hasattr(models, 'DigitalProjectTask'):
            db.query(models.DigitalProjectTask).delete()
        if hasattr(models, 'DigitalProjectFinance'):
            db.query(models.DigitalProjectFinance).delete()
        if hasattr(models, 'DigitalProjectExpense'):
            db.query(models.DigitalProjectExpense).delete()
        if hasattr(models, 'DigitalProject'):
            deleted_counts["digital_projects"] = db.query(models.DigitalProject).count()
            db.query(models.DigitalProject).delete()
        if hasattr(models, 'DigitalService'):
            db.query(models.DigitalService).delete()
        
        # Удаляем проекты
        if hasattr(models, 'Project'):
            deleted_counts["projects"] = db.query(models.Project).count()
            db.query(models.Project).delete()
        
        # Удаляем файлы ресурсов
        if hasattr(models, 'ResourceFile'):
            deleted_counts["files"] = db.query(models.ResourceFile).count()
            # Удаляем физические файлы
            files = db.query(models.ResourceFile).all()
            for file in files:
                if file.file_path and os.path.exists(file.file_path):
                    try:
                        os.remove(file.file_path)
                    except:
                        pass
            db.query(models.ResourceFile).delete()
        
        # Удаляем операторов
        if hasattr(models, 'Operator'):
            deleted_counts["operators"] = db.query(models.Operator).count()
            db.query(models.Operator).delete()
        
        # Удаляем статьи расходов
        if hasattr(models, 'ExpenseItem'):
            deleted_counts["expense_items"] = db.query(models.ExpenseItem).count()
            db.query(models.ExpenseItem).delete()
        
        # Удаляем налоги
        if hasattr(models, 'Tax'):
            deleted_counts["taxes"] = db.query(models.Tax).count()
            db.query(models.Tax).delete()
        
        # Удаляем всех пользователей кроме текущего админа
        if hasattr(models, 'User'):
            deleted_counts["users"] = db.query(models.User).filter(models.User.id != current.id).count()
            db.query(models.User).filter(models.User.id != current.id).delete()
        
        # Удаляем настройки (кроме timezone)
        if hasattr(models, 'Setting'):
            db.query(models.Setting).filter(models.Setting.key != "timezone").delete()
        
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
        raise HTTPException(status_code=500, detail=f"Clear failed: {str(e)}")

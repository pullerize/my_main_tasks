# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**8Bit Codex** is a full-stack task management and agency operations platform with three main components:
- **Frontend** (React + TypeScript + Vite): Multi-role SPA for task management, project tracking, expenses, and analytics
- **Backend** (FastAPI + SQLAlchemy): REST API with JWT authentication and role-based access control
- **Telegram Bot** (Python): Provides task notifications and mobile access to the system

The system is designed for a digital agency with multiple user roles (designer, smm_manager, admin) and supports both SQLite (development) and PostgreSQL (production).

## Architecture

### Multi-Role System
The application has 3 distinct user roles with different permissions:
- `designer`: Basic task execution, personal expense tracking
- `smm_manager`: SMM project management, lead tracking
- `admin`: Full system access, user management
- `inactive`: Archived users (for former employees)

### Database Architecture
- **Flexible database engine**: Uses SQLite for development (default), PostgreSQL for production (configured via `DB_ENGINE` env var)
- **Shared database**: The Telegram bot and backend share the same database instance
- **Key tables**:
  - `users`: User accounts with Telegram integration (telegram_id, telegram_username)
  - `tasks`: Task management with recurrence support (daily/weekly/monthly)
  - `projects`: Project tracking with client, budget, and timeline info
  - `leads`: Lead/client management with status tracking
  - `project_expenses`, `common_expenses`, `employee_expenses`: Three-tier expense tracking system
  - `operators`: External operators/freelancers management
  - `service_types`: Categorization of services offered

### Frontend Architecture
- **React Router**: Role-based routing with protected routes
- **Context API**: Global state management for sidebar, authentication, toast notifications
- **API Layer**: Centralized in `src/utils/api.ts` with JWT token handling
- **Role-specific pages**: Each role has tailored views (e.g., `/smm-projects`, `/digital`, `/admin`)
- **Date handling**: Custom date utilities in `src/utils/dateUtils.ts` accounting for UTC+5 timezone

### Backend Architecture
- **FastAPI main app**: `agency_backend/app/main.py` contains all API endpoints and middleware
- **Models**: SQLAlchemy models in `models.py` with UTC+5 timezone support
- **CRUD operations**: Separated in `crud.py` for database operations
- **Authentication**: JWT-based auth in `auth.py` with password hashing
- **File uploads**: Supports file attachments for tasks and contracts
- **Recurring tasks**: Background task generation based on recurrence rules

### Telegram Bot
- **Single-instance protection**: Uses file locking (`fcntl` on Linux, `msvcrt` on Windows) to prevent multiple bot instances
- **Database integration**: Direct SQLite/PostgreSQL access via shared connection
- **Admin handlers**: Separate module `admin_task_handlers.py` for admin-specific commands
- **Expense tracking**: `expense_handlers.py` for recording expenses via Telegram
- **Process manager**: `process_manager.py` manages bot lifecycle
- **Keyboard layouts**: Uses `ReplyKeyboardMarkup` with specific button arrangements:
  - Main menu: "Управление задачами" (full width), "Расходы" and "Отчеты" (same row)
  - Task types/formats/users: 3 buttons per row
  - Projects: 2 buttons per row
  - Roles: 3 buttons per row

## Development Commands

### Backend (FastAPI)
```bash
# Development
cd agency_backend
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# Production
uvicorn app.main:app --host 0.0.0.0 --port 8000

# Install dependencies
pip install -r requirements.txt
```

### Frontend (React + Vite)
```bash
# Development server
cd agency_frontend
npm run dev

# Production build
npm run build

# Preview build
npm run preview

# Install dependencies
npm install
```

### Telegram Bot
```bash
# Run bot (single instance protection included)
cd telegram_bot
python3 bot.py

# Clear bot webhooks before running
python3 clear_bot.py
```

### Docker Deployment
```bash
# Development with docker-compose
docker-compose up -d

# Production deployment
docker-compose -f docker-compose.production.yml up -d

# View logs
docker-compose logs -f backend
docker-compose logs -f frontend
```

## Environment Configuration

The `.env` file in the project root is shared across all components. Key variables:

```bash
# Database (switches between SQLite and PostgreSQL)
DB_ENGINE=sqlite  # or 'postgresql' for production
SQLITE_PATH=/path/to/shared_database.db
DATABASE_URL=sqlite:////path/to/shared_database.db

# PostgreSQL (for production)
POSTGRES_HOST=db
POSTGRES_PORT=5432
POSTGRES_DB=agency
POSTGRES_USER=agency
POSTGRES_PASSWORD=secure_password

# JWT Authentication
SECRET_KEY=your-secret-key-here

# Telegram Bot
BOT_TOKEN=your-telegram-bot-token

# CORS (for local development)
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

## Key Implementation Details

### Task Status System
Tasks have the following statuses:
- `new`: Just created
- `in_progress`: Being worked on (combined with `new` in frontend filter "В работе")
- `overdue`: Past deadline
- `done`: Completed
- Frontend default filter is `in_progress` which shows both `new` and `in_progress` tasks

### Task Recurrence System
Tasks can be configured to recur (daily/weekly/monthly) with specific times and days. The backend automatically:
1. Creates the next task instance at the specified `next_run_at` time
2. Tracks `overdue_count` and `resume_count` for recurring tasks (these fields must NOT be commented out in models.py)
3. Maintains parent-child relationships via `parent_task_id`

Location: `agency_backend/app/main.py` in the task creation endpoints and background worker threads.

### Expense Tracking
Three-tier expense system:
1. **Employee Expenses**: Personal expenses (salary, benefits) tracked per user
2. **Project Expenses**: Costs attributed to specific projects
3. **Common Expenses**: Shared operational costs (office, utilities)

All expenses support categorization via `ExpenseCategory` and require approval workflows for admin roles.

### Role-Based Access Control
Implemented at both frontend and backend:
- **Frontend**: Route guards in `App.tsx` check `localStorage.getItem('role')`
- **Backend**: `get_current_active_user()` dependency in endpoints validates JWT payload role
- **Telegram Bot**: Role-based command visibility and permissions

### Lead Management
CRM-like lead tracking system with:
- Multiple lead sources (telegram, instagram, website, call, referral, other)
- Status pipeline (new, contact_made, meeting_set, proposal_sent, negotiation, won, lost)
- Notes and comments system via `LeadNote` model
- Integration with project creation workflow

### File Upload System
Files are stored in `agency_backend/files/` and `agency_backend/contracts/` directories:
- Task attachments use UUID-based filenames
- Contracts linked to user accounts
- File serving via FastAPI's `FileResponse`

Location: `/files/{filename}` and `/contracts/{filename}` endpoints in `main.py`.

### Date/Time Handling
The system uses **UTC+5 timezone** throughout:
- Backend: `get_local_time_utc5()` function in `models.py` stores all dates in UTC+5
- Frontend: Two types of date formatters in `dateUtils.ts`:
  - `formatDateAsIs()`: Use for dates already stored in UTC+5 (accepted_at, deadline, finished_at)
  - `formatDateUTC5()`: Use only when converting from true UTC timestamps
- **Critical**: Always use `formatDateAsIs()` for displaying task dates to avoid double-offset issues
- All datetime comparisons must account for this offset

## Database Migrations

**Important**: This project does not use Alembic or automated migrations. Schema changes are handled manually:

1. Modify models in `models.py`
2. Backend automatically creates missing tables on startup via `Base.metadata.create_all()`
3. For column additions to existing tables, add manual `ALTER TABLE` statements in `ensure_expense_tables()` function in `main.py`
4. Test migrations on development SQLite database first

## Testing

No automated test suite currently exists. Manual testing workflow:

1. Start backend: `uvicorn app.main:app --reload`
2. Start frontend: `npm run dev`
3. Test via browser at `http://localhost:5173`
4. API docs available at `http://localhost:8000/docs` (Swagger UI)

## Common Development Tasks

### Adding a New User Role
1. Update `RoleEnum` in `agency_backend/app/models.py`
2. Add role-specific routes in `agency_frontend/src/App.tsx`
3. Create role-specific page components
4. Update permission checks in backend endpoints

### Adding a New Table/Model
1. Define SQLAlchemy model in `agency_backend/app/models.py`
2. Add Pydantic schemas in `agency_backend/app/schemas.py`
3. Create CRUD operations in `agency_backend/app/crud.py`
4. Add API endpoints in `agency_backend/app/main.py`
5. Backend will auto-create table on next startup

### Adding API Endpoints
All endpoints are in `agency_backend/app/main.py`. Follow the pattern:
```python
@app.post("/endpoint", response_model=schemas.Response)
def endpoint_handler(
    data: schemas.RequestData,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    # Implement endpoint logic
    pass
```

### Frontend API Integration
Add API calls to `agency_frontend/src/utils/api.ts`:
```typescript
export const apiMethod = async (data: Type): Promise<ReturnType> => {
  const response = await fetch(`${API_BASE_URL}/endpoint`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${localStorage.getItem('token')}`
    },
    body: JSON.stringify(data)
  });
  return response.json();
};
```

## Deployment

The project is configured for deployment with Docker Compose + Nginx:
- **Nginx**: Reverse proxy configuration in `nginx.conf`
- **SSL/TLS**: Certbot integration for Let's Encrypt certificates
- **Production domain**: 8bit-task.site
- **Backend**: Proxied from `/api/*` to `backend:8000`
- **Frontend**: Served from root `/` with SPA fallback

## Important Notes

- **Time zone**: All date/time operations use UTC+5 (Uzbekistan time)
- **Date formatting**: Always use `formatDateAsIs()` for displaying dates from backend to avoid double-offset
- **Database path**: Must be absolute path, shared between backend and Telegram bot
- **Telegram registration**: Users must link their accounts via `/start` command in bot
- **File permissions**: Ensure `files/` and `contracts/` directories have write permissions
- **Single bot instance**: The bot uses file locking to prevent duplicate instances
- **JWT tokens**: Default expiry is 1440 minutes (24 hours)
- **Database relationships**: When fixing orphaned foreign keys (lead_notes, leads manager_id), always check for existing user relationships before operations
- **Task model fields**: `resume_count` and `overdue_count` must remain uncommented in Task model - they are actively used by CRUD operations
- **Bot menu consistency**: Main menu layout must be preserved across all handler contexts (after task creation, viewing tasks, etc.)

## Communication Language

Ты должен общаться на русском языке (You must communicate in Russian language)
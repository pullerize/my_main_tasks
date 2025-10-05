# 8BIT Codex - Система управления агентством

Полнофункциональная система для управления задачами, проектами и ресурсами digital-агентства.

## Возможности

- **Управление пользователями** с ролевой моделью доступа
- **Управление задачами** с приоритетами и дедлайнами  
- **SMM проекты** с планированием контента
- **Digital проекты** с отслеживанием финансов
- **Календарь съемок** для планирования
- **Финансовая отчетность** с учетом налогов
- **Файловое хранилище** для ресурсов
- **Telegram интеграция** для уведомлений

## Технологии

**Backend:**
- FastAPI (Python 3.9+)
- SQLAlchemy ORM
- PostgreSQL / SQLite
- JWT авторизация

**Frontend:**
- React 18 с TypeScript
- Vite для сборки
- TailwindCSS для стилей
- Recharts для графиков

## Быстрый старт (локальная разработка)

### Предварительные требования

- Python 3.9 или выше
- Node.js 16 или выше
- Git

### 1. Клонирование репозитория

```bash
git clone https://github.com/your-repo/8bit-codex.git
cd 8bit-codex
```

### 2. Настройка окружения

Скопируйте пример конфигурации:

```bash
cp .env.example .env
```

Отредактируйте `.env` файл и установите безопасный SECRET_KEY:

```bash
# Генерация случайного ключа (Linux/Mac)
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# или для Windows PowerShell
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 3. Запуск Backend

#### Вариант A: С виртуальным окружением (рекомендуется)

```bash
# Создание виртуального окружения
cd agency_backend
python3 -m venv venv

# Активация (Linux/Mac)
source venv/bin/activate

# Активация (Windows)
venv\Scripts\activate

# Установка зависимостей
pip install -r requirements.txt

# Запуск сервера
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### Вариант B: Без виртуального окружения

```bash
cd agency_backend
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Backend будет доступен по адресу: http://localhost:8000
API документация: http://localhost:8000/docs

### 4. Запуск Frontend

В новом терминале:

```bash
cd agency_frontend

# Установка зависимостей
npm install

# Запуск dev-сервера
npm run dev
```

Frontend будет доступен по адресу: http://localhost:5173

### 5. Первый вход

По умолчанию создается администратор:
- **Логин:** admin
- **Пароль:** admin123

**ВАЖНО:** Смените пароль администратора после первого входа!

## Структура проекта

```
8bit-codex/
├── agency_backend/       # Backend приложение
│   ├── app/
│   │   ├── main.py      # Точка входа FastAPI
│   │   ├── auth.py      # Аутентификация
│   │   ├── models.py    # SQLAlchemy модели
│   │   ├── schemas.py   # Pydantic схемы
│   │   ├── crud.py      # CRUD операции
│   │   └── database.py  # Подключение к БД
│   ├── static/          # Статические файлы
│   └── requirements.txt # Python зависимости
│
├── agency_frontend/      # Frontend приложение
│   ├── src/
│   │   ├── pages/       # Страницы приложения
│   │   ├── components/  # React компоненты
│   │   ├── utils/       # Утилиты и хелперы
│   │   └── api.ts       # API клиент
│   └── package.json     # Node.js зависимости
│
├── .env.example         # Пример конфигурации
├── docker-compose.yml   # Docker конфигурация
└── README.md           # Документация
```

## Docker запуск

Для запуска через Docker Compose:

```bash
# Сборка и запуск контейнеров
docker-compose up --build

# Остановка
docker-compose down
```

## Настройка базы данных

### SQLite (по умолчанию для разработки)

База данных создается автоматически в файле `shared_database.db`

### PostgreSQL (рекомендуется для продакшена)

1. Установите PostgreSQL
2. Создайте базу данных и пользователя:

```sql
CREATE DATABASE agency;
CREATE USER agency_user WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE agency TO agency_user;
```

3. Обновите `.env` файл:

```env
DB_ENGINE=postgresql
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=agency
POSTGRES_USER=agency_user
POSTGRES_PASSWORD=your_secure_password
```

## API Endpoints

### Аутентификация
- `POST /token` - Получение JWT токена
- `GET /users/me` - Текущий пользователь

### Пользователи
- `GET /users/` - Список пользователей
- `POST /users/` - Создание пользователя
- `PUT /users/{id}` - Обновление пользователя

### Задачи
- `GET /tasks/` - Список задач
- `POST /tasks/` - Создание задачи
- `PUT /tasks/{id}` - Обновление задачи
- `POST /tasks/{id}/complete` - Завершение задачи

### Проекты
- `GET /projects/` - Список проектов
- `POST /projects/` - Создание проекта
- `PUT /projects/{id}` - Обновление проекта

Полная документация API доступна по адресу `/docs` после запуска backend.

## Решение проблем

### Ошибка подключения к БД

Проверьте:
- Правильность пути к SQLite файлу
- Доступность PostgreSQL сервера
- Корректность учетных данных в `.env`

### CORS ошибки

Убедитесь, что в `.env` указан правильный `CORS_ORIGINS`:
```env
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
```

### Ошибка авторизации

1. Проверьте наличие и корректность `SECRET_KEY` в `.env`
2. Очистите localStorage в браузере
3. Попробуйте войти заново

## Безопасность

1. **ОБЯЗАТЕЛЬНО** измените `SECRET_KEY` в продакшене
2. Используйте сильные пароли
3. Настройте HTTPS для продакшена
4. Регулярно обновляйте зависимости
5. Ограничьте CORS origins для продакшена

## Разработка

### Миграции базы данных

```bash
# Создание миграции
alembic revision --autogenerate -m "Description"

# Применение миграций
alembic upgrade head
```

### Тестирование

```bash
# Backend тесты
cd agency_backend
pytest

# Frontend тесты
cd agency_frontend
npm test
```

### Линтинг

```bash
# Backend
flake8 app/
black app/

# Frontend  
npm run lint
```

## Развертывание в продакшене

Подробная инструкция по развертыванию находится в файле `DEPLOYMENT.md`

## Лицензия

Proprietary - Все права защищены

## Поддержка

Для получения поддержки создайте issue в репозитории или свяжитесь с командой разработки.# my_main_tasks

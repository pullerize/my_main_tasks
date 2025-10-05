# 🚀 Инструкция по развертыванию 8Bit Codex

## Требования к серверу

- Ubuntu 20.04 LTS или новее
- Docker 20.10+
- Docker Compose 2.0+
- Минимум 2GB RAM
- 20GB свободного места на диске
- Доменное имя (для SSL)

## Подготовка сервера

### 1. Обновление системы
```bash
sudo apt update && sudo apt upgrade -y
```

### 2. Установка Docker
```bash
# Установка зависимостей
sudo apt install -y apt-transport-https ca-certificates curl software-properties-common

# Добавление официального GPG ключа Docker
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# Добавление репозитория Docker
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Установка Docker
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Добавление пользователя в группу docker
sudo usermod -aG docker $USER
newgrp docker
```

### 3. Проверка установки
```bash
docker --version
docker compose version
```

## Развертывание приложения

### 1. Клонирование репозитория
```bash
cd /opt
sudo git clone https://github.com/your-username/8bit-codex.git
cd 8bit-codex
sudo chown -R $USER:$USER .
```

### 2. Настройка окружения
```bash
# Копирование примера конфигурации
cp .env.example .env

# Редактирование конфигурации
nano .env
```

Обязательно измените следующие параметры:
```env
# Database
POSTGRES_DB=8bit_tasks
POSTGRES_USER=8bit_user
POSTGRES_PASSWORD=YOUR_SECURE_PASSWORD_HERE

# JWT Secret (сгенерируйте новый: openssl rand -hex 32)
SECRET_KEY=YOUR_SECURE_SECRET_KEY_HERE

# Telegram Bot Token (получите у @BotFather)
BOT_TOKEN=your_telegram_bot_token

# CORS (укажите ваш домен)
CORS_ORIGINS=https://your-domain.com,https://www.your-domain.com
```

### 3. Настройка Nginx для SSL

Создайте файл `nginx.conf`:
```nginx
server {
    listen 80;
    listen [::]:80;
    server_name your-domain.com www.your-domain.com;

    # Для Certbot
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    # Редирект на HTTPS
    location / {
        return 301 https://$host$request_uri;
    }
}

server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name your-domain.com www.your-domain.com;

    # SSL сертификаты
    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

    # Безопасность SSL
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;

    # Frontend
    location / {
        proxy_pass http://frontend:80;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Backend API
    location /api {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # WebSocket для уведомлений (если используется)
    location /ws {
        proxy_pass http://backend:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }

    # Максимальный размер загружаемых файлов
    client_max_body_size 50M;
}
```

### 4. Получение SSL сертификата

```bash
# Сначала запустите только nginx и certbot
docker compose -f docker-compose.production.yml up -d nginx certbot

# Получите сертификат
docker compose exec certbot certbot certonly --webroot \
  --webroot-path=/var/www/certbot \
  --email your-email@example.com \
  --agree-tos \
  --no-eff-email \
  -d your-domain.com \
  -d www.your-domain.com

# Перезапустите nginx
docker compose restart nginx
```

### 5. Запуск всех сервисов

```bash
# Сборка и запуск всех контейнеров
docker compose -f docker-compose.production.yml up -d --build

# Проверка статуса
docker compose ps

# Просмотр логов
docker compose logs -f
```

### 6. Инициализация базы данных

```bash
# База данных создается автоматически при первом запуске
# Проверьте логи backend для подтверждения
docker compose logs backend | grep "Database tables created"
```

### 7. Создание первого администратора

По умолчанию создается пользователь:
- **Логин**: `admin`
- **Пароль**: `admin123`

⚠️ **ВАЖНО**: Смените пароль сразу после первого входа!

## Управление приложением

### Просмотр логов
```bash
# Все сервисы
docker compose logs -f

# Конкретный сервис
docker compose logs -f backend
docker compose logs -f telegram_bot
```

### Перезапуск сервисов
```bash
# Все сервисы
docker compose restart

# Конкретный сервис
docker compose restart backend
```

### Обновление приложения
```bash
# Получить последние изменения
git pull origin main

# Пересобрать и перезапустить
docker compose -f docker-compose.production.yml up -d --build

# Удалить неиспользуемые образы
docker image prune -f
```

### Резервное копирование

```bash
# Создать бэкап базы данных
docker compose exec db pg_dump -U 8bit_user 8bit_tasks > backup_$(date +%Y%m%d).sql

# Создать бэкап через веб-интерфейс
# Админ панель -> Настройки -> Экспорт БД (включает файлы)
```

### Восстановление из бэкапа

```bash
# Остановить приложение
docker compose down

# Восстановить базу данных
cat backup_20250101.sql | docker compose exec -T db psql -U 8bit_user 8bit_tasks

# Запустить приложение
docker compose up -d
```

## Мониторинг

### Проверка здоровья сервисов
```bash
# Статус контейнеров
docker compose ps

# Использование ресурсов
docker stats

# Место на диске
df -h
docker system df
```

### Проверка работы API
```bash
curl https://your-domain.com/api/health
```

## Безопасность

### 1. Настройка файрвола
```bash
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

### 2. Регулярные обновления
```bash
# Настройте cron для автоматических обновлений безопасности
sudo apt install unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades
```

### 3. Ротация SSL сертификатов
Certbot автоматически обновляет сертификаты. Проверьте настройку:
```bash
docker compose exec certbot certbot renew --dry-run
```

## Решение проблем

### Backend не запускается
```bash
# Проверьте логи
docker compose logs backend

# Проверьте подключение к БД
docker compose exec backend python -c "from app.database import engine; print(engine.connect())"
```

### Telegram бот не отвечает
```bash
# Проверьте логи
docker compose logs telegram_bot

# Проверьте токен
docker compose exec telegram_bot python -c "import os; print(os.getenv('BOT_TOKEN'))"
```

### Проблемы с SSL
```bash
# Проверьте сертификаты
docker compose exec certbot certbot certificates

# Принудительное обновление
docker compose exec certbot certbot renew --force-renewal
```

### Очистка места на диске
```bash
# Удаление неиспользуемых Docker объектов
docker system prune -a --volumes

# Удаление старых логов
sudo journalctl --vacuum-time=7d
```

## Производительность

### Оптимизация PostgreSQL
Добавьте в `docker-compose.production.yml` под `db`:
```yaml
command:
  - "postgres"
  - "-c"
  - "max_connections=200"
  - "-c"
  - "shared_buffers=256MB"
  - "-c"
  - "effective_cache_size=1GB"
```

### Кэширование статики в Nginx
Добавьте в `nginx.conf`:
```nginx
location ~* \.(jpg|jpeg|png|gif|ico|css|js)$ {
    expires 1y;
    add_header Cache-Control "public, immutable";
}
```

## Контакты поддержки

При возникновении проблем:
1. Проверьте логи: `docker compose logs`
2. Посмотрите документацию в README.md
3. Создайте issue на GitHub

---

✅ Приложение готово к production использованию!

# 🚀 Подробная инструкция по развертыванию Agency Management System

## 📋 Что вам понадобится

- **VPS/сервер** с Ubuntu 20.04+ 
- **Доменное имя** (например: `agency.yourcompany.com`)
- **SSH доступ** к серверу
- **Root или sudo права** на сервере

## 🔧 Шаг 1: Подготовка сервера

### 1.1 Подключение к серверу
```bash
# Подключаемся к серверу
ssh root@your-server-ip
# или с пользователем
ssh username@your-server-ip
```

### 1.2 Обновление системы
```bash
# Обновляем систему
sudo apt update && sudo apt upgrade -y

# Устанавливаем базовые пакеты
sudo apt install -y curl wget git htop nano unzip
```

### 1.3 Создание пользователя (если нужно)
```bash
# Создаем пользователя для приложения
sudo adduser agency
sudo usermod -aG sudo agency

# Переключаемся на нового пользователя
su - agency
```

## 🐳 Шаг 2: Установка Docker

### 2.1 Установка Docker
```bash
# Устанавливаем Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Добавляем пользователя в группу docker
sudo usermod -aG docker $USER

# Включаем автозапуск Docker
sudo systemctl enable docker
sudo systemctl start docker
```

### 2.2 Установка Docker Compose
```bash
# Устанавливаем Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose

# Делаем исполняемым
sudo chmod +x /usr/local/bin/docker-compose

# Проверяем установку
docker --version
docker-compose --version
```

### 2.3 Применение прав Docker
```bash
# Перезаходим или применяем права
newgrp docker
# или
exit
ssh username@your-server-ip
```

## 📁 Шаг 3: Загрузка приложения на сервер

### 3.1 Создание директории
```bash
# Создаем директорию для приложения
sudo mkdir -p /opt/agency-app
sudo chown $USER:$USER /opt/agency-app
cd /opt/agency-app
```

### 3.2 Загрузка файлов (Вариант A: Git)
```bash
# Если у вас есть Git репозиторий
git clone https://your-git-repo.com/agency-management.git .

# Или скачать конкретную ветку
git clone -b main https://your-git-repo.com/agency-management.git .
```

### 3.3 Загрузка файлов (Вариант B: Архив)
```bash
# На локальном компьютере создаем архив
cd "/mnt/c/Users/Господин/Desktop/Мои проекты/8bit_tasks/8bit-codex"
tar -czf agency-app.tar.gz --exclude='node_modules' --exclude='venv' --exclude='*.db' .

# Загружаем на сервер через scp
scp agency-app.tar.gz username@your-server-ip:/opt/agency-app/

# На сервере распаковываем
cd /opt/agency-app
tar -xzf agency-app.tar.gz
rm agency-app.tar.gz
```

### 3.4 Загрузка файлов (Вариант C: rsync)
```bash
# На локальном компьютере синхронизируем папку
rsync -avz --exclude='node_modules' --exclude='venv' --exclude='*.db' \
  "/mnt/c/Users/Господин/Desktop/Мои проекты/8bit_tasks/8bit-codex/" \
  username@your-server-ip:/opt/agency-app/
```

## ⚙️ Шаг 4: Настройка окружения

### 4.1 Создание .env файла
```bash
cd /opt/agency-app

# Копируем пример конфигурации
cp .env.example .env

# Редактируем настройки
nano .env
```

### 4.2 Настройка .env для продакшена
```env
# ========== APP ==========
APP_NAME=agency-management
ENV=production
SECRET_KEY=ваш-очень-длинный-секретный-ключ-минимум-32-символа
ALLOWED_HOSTS=agency.yourcompany.com,your-server-ip
CORS_ORIGINS=https://agency.yourcompany.com

# ========== AUTH ==========
ACCESS_TOKEN_EXPIRE_MINUTES=1440
PASSWORD_HASH_ROUNDS=12

# ========== DB (SQLite для начала) ==========
DB_ENGINE=sqlite
SQLITE_PATH=/data/agency/db/app.db

# ========== DB (PostgreSQL для высоких нагрузок) ==========
# DB_ENGINE=postgresql
# POSTGRES_HOST=db
# POSTGRES_PORT=5432
# POSTGRES_DB=agency
# POSTGRES_USER=agency
# POSTGRES_PASSWORD=очень-сложный-пароль

# ========== BACKUP ==========
BACKUP_DIR=/data/agency/backups
BACKUP_RETENTION_DAYS=30

# ========== NGINX / TLS ==========
NGINX_SERVER_NAME=agency.yourcompany.com
ENABLE_TLS=true
```

**🔑 ВАЖНО:** Замените:
- `agency.yourcompany.com` на ваш домен
- `your-server-ip` на IP вашего сервера  
- `ваш-очень-длинный-секретный-ключ` на случайную строку 32+ символов
- `очень-сложный-пароль` на сложный пароль для БД

### 4.3 Создание директорий
```bash
# Создаем директории для данных
sudo mkdir -p /data/agency/{db,backups,static,contracts,files}
sudo chown -R $USER:$USER /data/agency
chmod -R 755 /data/agency
```

## 🌐 Шаг 5: Настройка домена

### 5.1 DNS настройка
В панели управления доменом добавьте A-запись:
```
Имя: agency (или @)
Тип: A
Значение: your-server-ip
TTL: 3600
```

### 5.2 Проверка DNS
```bash
# Проверяем, что домен указывает на сервер
dig agency.yourcompany.com
ping agency.yourcompany.com
```

## 🔥 Шаг 6: Настройка firewall

### 6.1 Настройка UFW
```bash
# Включаем firewall
sudo ufw --force enable

# Разрешаем SSH
sudo ufw allow ssh

# Разрешаем HTTP и HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Проверяем статус
sudo ufw status
```

## 🚀 Шаг 7: Запуск приложения

### 7.1 Первый запуск
```bash
cd /opt/agency-app

# Делаем скрипты исполняемыми
chmod +x *.sh

# Запускаем развертывание для продакшена
./deploy.sh production
```

### 7.2 Мониторинг запуска
```bash
# Следим за логами
docker-compose -f docker-compose.production.yml logs -f

# В новом терминале проверяем статус
docker-compose -f docker-compose.production.yml ps
```

### 7.3 Проверка работоспособности
```bash
# Проверяем health check
curl http://localhost:8000/health

# Проверяем frontend (если домен еще не работает)
curl http://localhost/

# Проверяем API
curl http://localhost:8000/docs
```

## 🔒 Шаг 8: Настройка SSL

### 8.1 Установка Certbot
```bash
# Устанавливаем Certbot
sudo apt install -y certbot

# Устанавливаем плагин для nginx
sudo apt install -y python3-certbot-nginx
```

### 8.2 Остановка nginx для получения сертификата
```bash
# Временно останавливаем приложение
docker-compose -f docker-compose.production.yml stop nginx

# Получаем SSL сертификат
sudo certbot certonly --standalone \
  -d agency.yourcompany.com \
  --agree-tos \
  --email your-email@example.com

# Запускаем приложение обратно
docker-compose -f docker-compose.production.yml start nginx
```

### 8.3 Автоматическое обновление SSL
```bash
# Добавляем задачу в cron для обновления сертификатов
sudo crontab -e

# Добавляем строку (обновление каждый день в 2:30)
30 2 * * * /usr/bin/certbot renew --quiet --deploy-hook "cd /opt/agency-app && docker-compose -f docker-compose.production.yml restart nginx"
```

## 🔧 Шаг 9: Настройка автозапуска

### 9.1 Создание systemd сервиса
```bash
# Создаем сервис файл
sudo nano /etc/systemd/system/agency-app.service
```

Добавьте содержимое:
```ini
[Unit]
Description=Agency Management System
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/agency-app
ExecStart=/usr/local/bin/docker-compose -f docker-compose.production.yml up -d
ExecStop=/usr/local/bin/docker-compose -f docker-compose.production.yml down
TimeoutStartSec=300
User=agency
Group=agency

[Install]
WantedBy=multi-user.target
```

### 9.2 Активация сервиса
```bash
# Перезагружаем systemd
sudo systemctl daemon-reload

# Включаем автозапуск
sudo systemctl enable agency-app

# Проверяем статус
sudo systemctl status agency-app
```

## 💾 Шаг 10: Настройка бэкапов

### 10.1 Создание скрипта бэкапа
```bash
sudo nano /usr/local/bin/agency-backup.sh
```

Добавьте содержимое:
```bash
#!/bin/bash
set -e

BACKUP_DIR="/data/agency/backups"
APP_DIR="/opt/agency-app"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="agency_backup_${TIMESTAMP}"

# Создаем директорию для бэкапов
mkdir -p "${BACKUP_DIR}"

echo "Создание бэкапа: ${BACKUP_NAME}"

# Останавливаем приложение для консистентного бэкапа
cd "${APP_DIR}"
docker-compose -f docker-compose.production.yml stop backend

# Создаем архив данных
cd /data/agency
tar -czf "${BACKUP_DIR}/${BACKUP_NAME}.tar.gz" \
    --exclude="backups" \
    --exclude="*.log" \
    db/ static/ contracts/ files/

# Запускаем приложение обратно
cd "${APP_DIR}"
docker-compose -f docker-compose.production.yml start backend

# Удаляем старые бэкапы (старше 30 дней)
find "${BACKUP_DIR}" -name "agency_backup_*.tar.gz" -mtime +30 -delete

echo "Бэкап создан: ${BACKUP_DIR}/${BACKUP_NAME}.tar.gz"
```

```bash
# Делаем скрипт исполняемым
sudo chmod +x /usr/local/bin/agency-backup.sh

# Тестируем скрипт
sudo /usr/local/bin/agency-backup.sh
```

### 10.2 Автоматические бэкапы
```bash
# Добавляем в cron
crontab -e

# Добавляем строку (бэкап каждый день в 3:00)
0 3 * * * /usr/local/bin/agency-backup.sh >> /var/log/agency-backup.log 2>&1
```

## ✅ Шаг 11: Финальная проверка

### 11.1 Проверка всех сервисов
```bash
# Проверяем статус контейнеров
docker-compose -f docker-compose.production.yml ps

# Проверяем логи
docker-compose -f docker-compose.production.yml logs --tail=20

# Проверяем health check всех сервисов
curl https://agency.yourcompany.com/api/health
curl https://agency.yourcompany.com/
```

### 11.2 Первый вход в систему
1. Откройте `https://agency.yourcompany.com` в браузере
2. Войдите с логином: `admin` и паролем: `admin123`
3. **Обязательно смените пароль** в настройках профиля

### 11.3 Импорт существующих данных
1. Перейдите в `Настройки` → `Импорт базы данных`
2. Загрузите ваш файл `tasks.db`
3. Дождитесь завершения импорта

## 🔄 Управление приложением

### Основные команды
```bash
cd /opt/agency-app

# Просмотр статуса
docker-compose -f docker-compose.production.yml ps

# Просмотр логов
docker-compose -f docker-compose.production.yml logs -f

# Перезапуск всех сервисов
docker-compose -f docker-compose.production.yml restart

# Перезапуск конкретного сервиса
docker-compose -f docker-compose.production.yml restart backend

# Остановка
docker-compose -f docker-compose.production.yml down

# Запуск
docker-compose -f docker-compose.production.yml up -d

# Обновление (после загрузки новой версии)
docker-compose -f docker-compose.production.yml down
docker-compose -f docker-compose.production.yml build --no-cache
docker-compose -f docker-compose.production.yml up -d
```

### Системные команды
```bash
# Управление через systemctl
sudo systemctl start agency-app
sudo systemctl stop agency-app
sudo systemctl restart agency-app
sudo systemctl status agency-app

# Просмотр системных логов
sudo journalctl -u agency-app -f
```

## 🚨 Решение проблем

### Проблема: Контейнеры не запускаются
```bash
# Проверяем логи
docker-compose -f docker-compose.production.yml logs

# Проверяем права на директории
ls -la /data/agency/
sudo chown -R $USER:$USER /data/agency

# Пересобираем контейнеры
docker-compose -f docker-compose.production.yml build --no-cache
```

### Проблема: Нет доступа к сайту
```bash
# Проверяем DNS
dig agency.yourcompany.com

# Проверяем firewall
sudo ufw status

# Проверяем nginx
docker-compose -f docker-compose.production.yml logs nginx

# Проверяем SSL сертификат
sudo certbot certificates
```

### Проблема: База данных не работает
```bash
# Проверяем health check
curl http://localhost:8000/health

# Проверяем логи backend
docker-compose -f docker-compose.production.yml logs backend

# Проверяем файл БД
ls -la /data/agency/db/
```

### Проблема: Нехватка места
```bash
# Проверяем место на диске
df -h

# Очищаем Docker
docker system prune -af
docker volume prune -f

# Удаляем старые бэкапы
find /data/agency/backups -name "*.tar.gz" -mtime +7 -delete
```

## 📞 Поддержка

- **Логи приложения**: `/var/log/agency-backup.log`
- **Конфигурация**: `/opt/agency-app/.env`
- **Данные**: `/data/agency/`
- **Бэкапы**: `/data/agency/backups/`

## 🎉 Готово!

Ваше приложение Agency Management System успешно развернуто и готово к работе!

**Доступ к приложению**: `https://agency.yourcompany.com`

**Не забудьте:**
- ✅ Сменить пароль администратора
- ✅ Настроить регулярные бэкапы
- ✅ Мониторить логи приложения
- ✅ Обновлять систему и приложение
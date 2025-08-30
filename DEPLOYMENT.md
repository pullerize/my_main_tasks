# 🚀 Руководство по развертыванию Agency Management System

## 📋 Системные требования

### Минимальные требования
- **ОС**: Ubuntu 20.04+ / CentOS 8+ / Debian 11+
- **RAM**: 2 GB
- **Диск**: 10 GB свободного места
- **CPU**: 1 vCPU

### Рекомендуемые требования
- **ОС**: Ubuntu 22.04 LTS
- **RAM**: 4 GB+
- **Диск**: 20 GB+ SSD
- **CPU**: 2+ vCPU
- **Сеть**: Стабильное интернет-соединение

## 🔧 Подготовка сервера

### 1. Подключение к серверу
```bash
ssh username@your-server-ip
```

### 2. Автоматическая настройка сервера
```bash
# Скачиваем и запускаем скрипт настройки
curl -fsSL https://raw.githubusercontent.com/your-repo/agency-management/main/setup_server.sh | bash

# Или если файлы уже на сервере
chmod +x setup_server.sh
./setup_server.sh
```

### 3. Ручная настройка (если нужно)
```bash
# Обновляем систему
sudo apt update && sudo apt upgrade -y

# Устанавливаем Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Устанавливаем Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Перезаходим для применения прав
newgrp docker
```

## 📦 Развертывание приложения

### 1. Получение исходного кода
```bash
# Создаем директорию для приложения
sudo mkdir -p /opt/agency-app
sudo chown $USER:$USER /opt/agency-app
cd /opt/agency-app

# Клонируем репозиторий (замените на свой URL)
git clone https://github.com/your-repo/agency-management.git .

# Или загружаем архив
wget https://github.com/your-repo/agency-management/archive/main.zip
unzip main.zip
mv agency-management-main/* .
```

### 2. Настройка переменных окружения
```bash
# Копируем пример конфигурации
cp .env.example .env

# Редактируем настройки
nano .env
```

**Важные параметры в .env:**
```bash
# База данных - путь для продакшена
SQLALCHEMY_DATABASE_URL=sqlite:////data/app.db

# Секретный ключ - ОБЯЗАТЕЛЬНО измените в продакшене!
SECRET_KEY=your-very-secret-key-change-me

# Настройки безопасности
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Данные администратора по умолчанию
ADMIN_LOGIN=admin
ADMIN_PASSWORD=your-secure-password
ADMIN_NAME=Administrator
```

### 3. Развертывание

#### Быстрый запуск для разработки:
```bash
./start.sh
```

#### Полное развертывание для продакшена:
```bash
./deploy.sh production
```

### 4. Проверка развертывания
```bash
# Проверяем состояние контейнеров
docker-compose ps

# Проверяем логи
docker-compose logs -f

# Проверяем доступность
curl http://localhost/
curl http://localhost:8000/
```

## 🌐 Доступ к приложению

После успешного развертывания:

- **Frontend**: http://your-server-ip/ 
- **Backend API**: http://your-server-ip:8000/
- **API Documentation**: http://your-server-ip:8000/docs

### Первый вход в систему
1. Откройте http://your-server-ip/ в браузере
2. Войдите с данными администратора из .env файла
3. Смените пароль в настройках профиля

## 🔒 SSL и доменное имя

### 1. Настройка домена
Добавьте A-запись в DNS, указывающую на IP вашего сервера:
```
your-domain.com -> your-server-ip
```

### 2. Установка SSL-сертификата (Let's Encrypt)
```bash
# Устанавливаем Certbot
sudo apt install certbot python3-certbot-nginx

# Получаем сертификат
sudo certbot --nginx -d your-domain.com

# Автоматическое обновление
sudo crontab -e
# Добавьте: 0 12 * * * /usr/bin/certbot renew --quiet
```

### 3. Обновление nginx.conf для HTTPS
Обновите файл `nginx.conf` для поддержки SSL.

## 🔧 Управление приложением

### Основные команды
```bash
# Запуск
docker-compose up -d

# Остановка
docker-compose down

# Перезапуск
docker-compose restart

# Просмотр логов
docker-compose logs -f

# Обновление образов
docker-compose pull && docker-compose up -d
```

### Мониторинг
```bash
# Статус контейнеров
docker ps

# Использование ресурсов
docker stats

# Логи отдельного сервиса
docker-compose logs backend
docker-compose logs frontend
```

## 💾 Резервное копирование

### Автоматические бэкапы
Скрипт `setup_server.sh` настраивает автоматические ежедневные бэкапы.

### Ручное создание бэкапа
```bash
# Создать бэкап
/usr/local/bin/agency-backup.sh

# Или вручную
cd /data/agency
tar -czf backup_$(date +%Y%m%d_%H%M%S).tar.gz \
    --exclude="backups" \
    --exclude="*.log" \
    .
```

### Восстановление из бэкапа
```bash
# Остановите приложение
docker-compose down

# Восстановите данные
cd /data/agency
tar -xzf backup_YYYYMMDD_HHMMSS.tar.gz

# Запустите приложение
docker-compose up -d
```

## 🔄 Обновление приложения

### 1. Создание бэкапа перед обновлением
```bash
/usr/local/bin/agency-backup.sh
```

### 2. Получение обновлений
```bash
cd /opt/agency-app

# Если используете Git
git pull origin main

# Если используете архив
wget https://github.com/your-repo/agency-management/archive/main.zip
```

### 3. Применение обновлений
```bash
# Пересобираем контейнеры
docker-compose build --no-cache

# Перезапускаем приложение
docker-compose down
docker-compose up -d
```

## 🚨 Устранение неполадок

### Проблемы с контейнерами
```bash
# Проверка состояния
docker-compose ps

# Перезапуск неисправного контейнера
docker-compose restart backend
docker-compose restart frontend

# Просмотр подробных логов
docker-compose logs --tail=100 backend
```

### Проблемы с базой данных
```bash
# Проверка файла БД
ls -la /data/agency/

# Проверка прав доступа
sudo chown -R $USER:$USER /data/agency
```

### Проблемы с портами
```bash
# Проверка занятых портов
sudo netstat -tulpn | grep :80
sudo netstat -tulpn | grep :8000

# Освобождение порта (замените PID)
sudo kill -9 PID
```

### Недостаток места на диске
```bash
# Проверка места
df -h

# Очистка Docker
docker system prune -af
docker volume prune -f

# Удаление старых логов
sudo journalctl --vacuum-time=7d
```

## 📞 Поддержка

При возникновении проблем:

1. **Проверьте логи**: `docker-compose logs -f`
2. **Проверьте статус**: `docker-compose ps`
3. **Проверьте конфигурацию**: `.env` файл
4. **Создайте issue** в репозитории проекта

## 📚 Дополнительные ресурсы

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [Let's Encrypt](https://letsencrypt.org/)
- [Ubuntu Server Guide](https://ubuntu.com/server/docs)

---

**Удачного развертывания! 🚀**
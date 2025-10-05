# ⚡ Быстрый старт для 8bit-task.site

## 📋 Чек-лист перед развертыванием

- [ ] DNS настроен (8bit-task.site → 185.207.64.109)
- [ ] Сервер с Ubuntu 20.04+ готов
- [ ] Есть доступ по SSH к серверу
- [ ] Telegram Bot Token получен у @BotFather
- [ ] Email для SSL сертификата

## 🚀 Развертывание за 5 минут

### 1. Подключитесь к серверу

```bash
ssh root@185.207.64.109
# или
ssh ваш_пользователь@185.207.64.109
```

### 2. Установите Docker (если не установлен)

```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
newgrp docker
```

### 3. Клонируйте проект

```bash
cd /opt
sudo git clone https://github.com/your-username/8bit-codex.git
cd 8bit-codex
sudo chown -R $USER:$USER .
```

### 4. Настройте окружение

```bash
# Копируем пример конфигурации
cp .env.example .env

# Редактируем конфигурацию
nano .env
```

**Обязательно измените:**

```env
# Пароль базы данных (придумайте надежный)
POSTGRES_PASSWORD=ваш_надежный_пароль_123

# JWT ключ (сгенерируйте: openssl rand -hex 32)
SECRET_KEY=сгенерированный_ключ_64_символа

# Токен Telegram бота (от @BotFather)
BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
```

Сохраните: `Ctrl+X`, затем `Y`, затем `Enter`

### 5. Запустите автоматический деплой

```bash
chmod +x deploy.sh
./deploy.sh
```

Выберите **1** (Первичное развертывание) и следуйте инструкциям.

### 6. Проверьте работу

```bash
# Статус всех сервисов
docker compose ps

# Логи (если нужно)
docker compose logs -f
```

## ✅ Готово!

Ваше приложение доступно по адресу:
- **Сайт**: https://8bit-task.site
- **API**: https://8bit-task.site/docs
- **Логин**: admin
- **Пароль**: admin123 (⚠️ СМЕНИТЕ СРАЗУ!)

## 🔧 Полезные команды

```bash
# Перезапуск
./deploy.sh  # выберите опцию 3

# Обновление
git pull origin main
./deploy.sh  # выберите опцию 2

# Логи конкретного сервиса
docker compose logs -f backend
docker compose logs -f telegram_bot

# Остановка
docker compose down

# Резервная копия БД
docker compose exec db pg_dump -U 8bit_user 8bit_tasks > backup.sql
```

## 🆘 Проблемы?

### SSL сертификат не получается

1. Проверьте, что DNS настроен правильно:
   ```bash
   nslookup 8bit-task.site
   # Должен вернуть 185.207.64.109
   ```

2. Убедитесь, что порты открыты:
   ```bash
   sudo ufw allow 80/tcp
   sudo ufw allow 443/tcp
   ```

### Backend не запускается

```bash
# Проверьте логи
docker compose logs backend

# Проверьте подключение к БД
docker compose exec backend python -c "from app.database import engine; print('OK')"
```

### Telegram бот не работает

```bash
# Проверьте токен в .env
grep BOT_TOKEN .env

# Проверьте логи
docker compose logs telegram_bot
```

## 📚 Дополнительная документация

- **Полная инструкция**: [DEPLOYMENT.md](./DEPLOYMENT.md)
- **Настройка DNS**: [DNS_SETUP.md](./DNS_SETUP.md)
- **README проекта**: [README.md](./README.md)

---

Удачного деплоя! 🚀

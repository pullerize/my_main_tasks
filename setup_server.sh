#!/bin/bash

# Скрипт настройки сервера для Agency Management System
# Запускайте от имени пользователя с sudo правами

set -e

echo "🔧 Настройка сервера для Agency Management System"

# Обновляем систему
echo "📦 Обновление системы..."
sudo apt update && sudo apt upgrade -y

# Устанавливаем необходимые пакеты
echo "📦 Установка базовых пакетов..."
sudo apt install -y \
    curl \
    wget \
    git \
    htop \
    nano \
    unzip \
    software-properties-common \
    apt-transport-https \
    ca-certificates \
    gnupg \
    lsb-release

# Устанавливаем Docker
if ! command -v docker &> /dev/null; then
    echo "🐳 Установка Docker..."
    
    # Добавляем официальный GPG ключ Docker
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
    
    # Добавляем репозиторий Docker
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    
    # Устанавливаем Docker
    sudo apt update
    sudo apt install -y docker-ce docker-ce-cli containerd.io
    
    # Добавляем пользователя в группу docker
    sudo usermod -aG docker $USER
    
    echo "✅ Docker установлен"
else
    echo "✅ Docker уже установлен"
fi

# Устанавливаем Docker Compose
if ! command -v docker-compose &> /dev/null; then
    echo "🔧 Установка Docker Compose..."
    
    DOCKER_COMPOSE_VERSION="v2.20.2"
    sudo curl -L "https://github.com/docker/compose/releases/download/${DOCKER_COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
    
    echo "✅ Docker Compose установлен"
else
    echo "✅ Docker Compose уже установлен"
fi

# Настраиваем firewall
echo "🔥 Настройка firewall..."
sudo ufw --force enable
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
echo "✅ Firewall настроен"

# Создаем директории для приложения
echo "📁 Создание директорий..."
sudo mkdir -p /data/agency/{static,contracts,files,backups}
sudo chown -R $USER:$USER /data/agency
chmod -R 755 /data/agency

# Создаем пользователя для приложения (опционально)
if ! id "agency" &>/dev/null; then
    echo "👤 Создание пользователя приложения..."
    sudo useradd -r -s /bin/false -d /data/agency agency
fi

# Настраиваем systemd service для автозапуска
echo "⚙️  Создание systemd service..."
sudo tee /etc/systemd/system/agency-app.service > /dev/null <<EOF
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
TimeoutStartSec=0
User=$USER
Group=$USER

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload

# Настраиваем логротацию
echo "📋 Настройка логротации..."
sudo tee /etc/logrotate.d/agency-app > /dev/null <<EOF
/var/log/agency-app/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 $USER $USER
    postrotate
        docker-compose -f /opt/agency-app/docker-compose.production.yml restart
    endscript
}
EOF

# Создаем скрипт бэкапа
echo "💾 Создание скрипта бэкапа..."
sudo tee /usr/local/bin/agency-backup.sh > /dev/null <<'EOF'
#!/bin/bash
BACKUP_DIR="/data/agency/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="agency_backup_${TIMESTAMP}.tar.gz"

# Создаем бэкап
cd /data/agency
tar -czf "${BACKUP_DIR}/${BACKUP_FILE}" \
    --exclude="backups" \
    --exclude="*.log" \
    .

# Удаляем старые бэкапы (старше 30 дней)
find "${BACKUP_DIR}" -name "agency_backup_*.tar.gz" -mtime +30 -delete

echo "Бэкап создан: ${BACKUP_DIR}/${BACKUP_FILE}"
EOF

sudo chmod +x /usr/local/bin/agency-backup.sh

# Добавляем cron задачу для бэкапа
echo "⏰ Настройка автоматического бэкапа..."
(crontab -l 2>/dev/null; echo "0 2 * * * /usr/local/bin/agency-backup.sh") | crontab -

echo ""
echo "🎉 Настройка сервера завершена!"
echo ""
echo "📋 Что дальше:"
echo "1. Перезайдите в систему или выполните: newgrp docker"
echo "2. Склонируйте репозиторий приложения в /opt/agency-app"
echo "3. Настройте .env файл"
echo "4. Запустите ./deploy.sh production"
echo ""
echo "🔧 Полезные команды:"
echo "  Статус сервиса:     sudo systemctl status agency-app"
echo "  Запуск сервиса:     sudo systemctl start agency-app"
echo "  Автозапуск:         sudo systemctl enable agency-app"
echo "  Создать бэкап:      /usr/local/bin/agency-backup.sh"
echo "  Просмотр логов:     sudo journalctl -u agency-app -f"
EOF
#!/bin/bash

# Скрипт для создания суперпользователя Django
# Использование: ./create-admin.sh [username] [email] [password]

set -e

PROJECT_DIR="/root/gestalt"
DOCKER_DIR="$PROJECT_DIR/docker"

# Параметры из аргументов или .env
USERNAME=${1:-admin}
EMAIL=${2:-admin@gestalt.local}
PASSWORD=${3:-}

# Если пароль не указан, генерируем случайный
if [ -z "$PASSWORD" ]; then
    if [ -f "$PROJECT_DIR/.env" ] && grep -q "DJANGO_ADMIN_PASSWORD" "$PROJECT_DIR/.env"; then
        PASSWORD=$(grep "DJANGO_ADMIN_PASSWORD" "$PROJECT_DIR/.env" | cut -d '=' -f2 | tr -d '"' | tr -d "'" | xargs)
    else
        PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)
        echo "Сгенерирован пароль: $PASSWORD"
        echo "Добавьте в .env: DJANGO_ADMIN_PASSWORD=$PASSWORD"
    fi
fi

cd "$DOCKER_DIR"

echo "Создание суперпользователя..."
echo "Username: $USERNAME"
echo "Email: $EMAIL"

# Создаем суперпользователя через Django shell
docker-compose exec -T geshtalt python manage.py shell << PYEOF
from django.contrib.auth.models import User
import sys

username = "$USERNAME"
email = "$EMAIL"
password = "$PASSWORD"

# Проверяем, существует ли пользователь
if User.objects.filter(username=username).exists():
    user = User.objects.get(username=username)
    user.is_superuser = True
    user.is_staff = True
    user.set_password(password)
    user.save()
    print(f'Пользователь {username} обновлен как суперпользователь')
else:
    User.objects.create_superuser(username, email, password)
    print(f'Создан суперпользователь: {username}')

print(f'Пароль: {password}')
PYEOF

echo ""
echo "Суперпользователь создан/обновлен!"
echo "Логин: $USERNAME"
echo "Пароль: $PASSWORD"
echo ""
echo "Для доступа к админке: https://kpalch.ru/admin/"







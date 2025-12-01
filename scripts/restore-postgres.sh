#!/bin/bash
# Скрипт для восстановления PostgreSQL из бэкапа

set -e

# Путь к директории бэкапов
BACKUP_DIR="/mnt/yandex/backup"

# Проверяем, что Яндекс.Облако смонтировано
if [ ! -d "$BACKUP_DIR" ]; then
    echo "Ошибка: директория $BACKUP_DIR не существует. Проверьте монтирование Яндекс.Облако."
    exit 1
fi

# Получаем переменные окружения из .env
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

if [ -f "$PROJECT_DIR/.env" ]; then
    source "$PROJECT_DIR/.env"
elif [ -f "/root/gestalt/.env" ]; then
    source /root/gestalt/.env
fi

# Параметры PostgreSQL из переменных окружения
POSTGRES_DB="${POSTGRES_DB:-gestalt}"
POSTGRES_USER="${POSTGRES_USER:-gestalt}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-}"

# Если указан файл бэкапа как аргумент, используем его
if [ -n "$1" ]; then
    BACKUP_FILE="$1"
    if [ ! -f "$BACKUP_FILE" ]; then
        echo "Ошибка: файл бэкапа не найден: $BACKUP_FILE"
        exit 1
    fi
else
    # Ищем последний бэкап
    LATEST_BACKUP=$(ls -t "$BACKUP_DIR"/postgres_*.sql.gz 2>/dev/null | head -1)
    if [ -z "$LATEST_BACKUP" ]; then
        echo "Ошибка: бэкапы PostgreSQL не найдены в $BACKUP_DIR"
        exit 1
    fi
    BACKUP_FILE="$LATEST_BACKUP"
    echo "Используется последний бэкап: $(basename $BACKUP_FILE)"
fi

# Проверяем, запущен ли PostgreSQL в Docker
DOCKER_COMPOSE_DIR="$PROJECT_DIR/docker"
if [ ! -d "$DOCKER_COMPOSE_DIR" ]; then
    echo "Ошибка: директория docker-compose не найдена: $DOCKER_COMPOSE_DIR"
    exit 1
fi

cd "$DOCKER_COMPOSE_DIR"

if ! docker-compose ps postgres | grep -q "Up"; then
    echo "Ошибка: PostgreSQL контейнер не запущен"
    exit 1
fi

echo "ВНИМАНИЕ: Это действие перезапишет текущую базу данных!"
echo "Бэкап для восстановления: $BACKUP_FILE"
read -p "Продолжить? (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo "Восстановление отменено"
    exit 0
fi

echo "Восстановление базы данных из бэкапа..."

# Восстанавливаем из бэкапа
if [ -z "$POSTGRES_PASSWORD" ]; then
    gunzip -c "$BACKUP_FILE" | docker-compose exec -T postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"
else
    gunzip -c "$BACKUP_FILE" | docker-compose exec -T -e PGPASSWORD="$POSTGRES_PASSWORD" postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"
fi

if [ $? -eq 0 ]; then
    echo "База данных успешно восстановлена из $BACKUP_FILE"
else
    echo "Ошибка при восстановлении базы данных!"
    exit 1
fi


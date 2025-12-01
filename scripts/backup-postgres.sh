#!/bin/bash
# Скрипт для бэкапа PostgreSQL в Яндекс.Облако
# Запускается каждый день в 2:00 через cron

set -e

# Путь к директории бэкапов
BACKUP_DIR="/mnt/yandex/backup"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/postgres_${TIMESTAMP}.sql.gz"
BACKUP_LOG="$BACKUP_DIR/postgres_backup.log"

# Проверяем, что Яндекс.Облако смонтировано
if [ ! -d "$BACKUP_DIR" ]; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') - Ошибка: директория $BACKUP_DIR не существует. Проверьте монтирование Яндекс.Облако." | tee -a "$BACKUP_LOG"
    exit 1
fi

# Создаем директорию, если её нет
mkdir -p "$BACKUP_DIR"

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
POSTGRES_HOST="${POSTGRES_HOST:-postgres}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"

# Проверяем, запущен ли PostgreSQL в Docker
DOCKER_COMPOSE_DIR="$PROJECT_DIR/docker"
if [ -d "$DOCKER_COMPOSE_DIR" ]; then
    cd "$DOCKER_COMPOSE_DIR"
    if docker-compose ps postgres | grep -q "Up"; then
        echo "$(date '+%Y-%m-%d %H:%M:%S') - Создание бэкапа PostgreSQL из Docker контейнера..." | tee -a "$BACKUP_LOG"
        
        # Создаем бэкап через docker-compose exec
        # Используем переменную окружения PGPASSWORD для передачи пароля
        if [ -z "$POSTGRES_PASSWORD" ]; then
            docker-compose exec -T -e PGPASSWORD postgres pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" | gzip > "$BACKUP_FILE"
        else
            docker-compose exec -T -e PGPASSWORD="$POSTGRES_PASSWORD" postgres pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" | gzip > "$BACKUP_FILE"
        fi
        
        if [ $? -eq 0 ]; then
            BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
            echo "$(date '+%Y-%m-%d %H:%M:%S') - Бэкап успешно создан: $BACKUP_FILE (размер: $BACKUP_SIZE)" | tee -a "$BACKUP_LOG"
            
            # Удаляем старые бэкапы (оставляем последние 30 дней)
            find "$BACKUP_DIR" -name "postgres_*.sql.gz" -type f -mtime +30 -delete
            echo "$(date '+%Y-%m-%d %H:%M:%S') - Старые бэкапы (старше 30 дней) удалены" | tee -a "$BACKUP_LOG"
        else
            echo "$(date '+%Y-%m-%d %H:%M:%S') - Ошибка при создании бэкапа!" | tee -a "$BACKUP_LOG"
            exit 1
        fi
    else
        echo "$(date '+%Y-%m-%d %H:%M:%S') - Ошибка: PostgreSQL контейнер не запущен" | tee -a "$BACKUP_LOG"
        exit 1
    fi
else
    echo "$(date '+%Y-%m-%d %H:%M:%S') - Ошибка: директория docker-compose не найдена: $DOCKER_COMPOSE_DIR" | tee -a "$BACKUP_LOG"
    exit 1
fi


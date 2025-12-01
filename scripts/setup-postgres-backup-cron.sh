#!/bin/bash
# Скрипт для настройки автоматического бэкапа PostgreSQL через cron

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_SCRIPT="$SCRIPT_DIR/backup-postgres.sh"

# Проверка, что скрипт существует
if [ ! -f "$BACKUP_SCRIPT" ]; then
    echo "Ошибка: скрипт $BACKUP_SCRIPT не найден"
    exit 1
fi

# Делаем скрипт исполняемым
chmod +x "$BACKUP_SCRIPT"

# Проверяем, не добавлена ли уже задача в cron
CRON_JOB="0 2 * * * $BACKUP_SCRIPT >> /mnt/yandex/backup/postgres_backup.log 2>&1"

if crontab -l 2>/dev/null | grep -q "$BACKUP_SCRIPT"; then
    echo "Задача бэкапа PostgreSQL уже добавлена в cron:"
    crontab -l | grep "$BACKUP_SCRIPT"
else
    # Добавляем задачу в cron
    (crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -
    echo "Задача бэкапа PostgreSQL добавлена в cron:"
    echo "$CRON_JOB"
fi

echo ""
echo "Бэкап PostgreSQL будет выполняться каждый день в 2:00"
echo "Логи бэкапа будут сохраняться в /mnt/yandex/backup/postgres_backup.log"


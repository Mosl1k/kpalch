#!/bin/bash

set -e  # Остановка при ошибке

echo "========================================="
echo "Миграция на Django + PostgreSQL"
echo "========================================="

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Функция для вывода сообщений
info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Переменные
PROJECT_DIR="/root/gestalt"
BACKUP_DIR="/mnt/yandex/backup"
BACKUP_DATE="20251126_020004"  # Позавчерашний бэкап
DOCKER_DIR="$PROJECT_DIR/docker"

# Шаг 1: Остановка старых контейнеров (кроме amnezia)
info "Остановка старых контейнеров (кроме amnezia)..."
cd "$DOCKER_DIR"

# Останавливаем все контейнеры кроме amnezia
docker ps -a --format "{{.Names}}" | grep -v "amnezia" | while read container; do
    if [ ! -z "$container" ]; then
        info "Остановка контейнера: $container"
        docker stop "$container" 2>/dev/null || true
        docker rm "$container" 2>/dev/null || true
    fi
done

# Шаг 2: Копирование нового docker-compose.yaml
info "Копирование нового docker-compose.yaml..."
if [ -f "$DOCKER_DIR/docker-compose.yaml.new" ]; then
    cp "$DOCKER_DIR/docker-compose.yaml.new" "$DOCKER_DIR/docker-compose.yaml"
    info "docker-compose.yaml обновлен"
elif [ -f "$PROJECT_DIR/docker/docker-compose.yaml" ]; then
    cp "$PROJECT_DIR/docker/docker-compose.yaml" "$DOCKER_DIR/docker-compose.yaml"
    info "docker-compose.yaml обновлен"
else
    error "Новый docker-compose.yaml не найден"
    exit 1
fi

# Шаг 3: Временный запуск Redis для миграции данных
info "Временный запуск Redis с бэкапом для миграции..."

# Создаем временный docker-compose с Redis
cat > "$DOCKER_DIR/docker-compose-redis-temp.yaml" <<EOF
services:
  redis-temp:
    image: redis:latest
    container_name: redis-temp
    volumes:
      - redis_temp_data:/data
      - $BACKUP_DIR:/backup:ro
    networks:
      - default
    command: >
      sh -c "
        if [ -f /backup/dump_${BACKUP_DATE}.rdb ]; then
          cp /backup/dump_${BACKUP_DATE}.rdb /data/dump.rdb
        fi
        if [ -d /backup/appendonlydir_${BACKUP_DATE} ]; then
          mkdir -p /data/appendonlydir
          cp -r /backup/appendonlydir_${BACKUP_DATE}/* /data/appendonlydir/ 2>/dev/null || true
        fi
        redis-server --appendonly yes --appendfsync everysec
      "
    restart: "no"

volumes:
  redis_temp_data:

networks:
  default:
    name: gestalt_network
    external: true
EOF

# Создаем сеть, если её нет
if ! docker network inspect gestalt_network >/dev/null 2>&1; then
    info "Создание сети gestalt_network..."
    docker network create gestalt_network
fi

# Запускаем временный Redis
info "Запуск временного Redis..."
cd "$DOCKER_DIR"
docker-compose -f docker-compose-redis-temp.yaml up -d redis-temp

# Ждем запуска Redis
info "Ожидание запуска Redis..."
sleep 5

# Проверяем, что Redis запустился
if ! docker ps | grep -q redis-temp; then
    error "Не удалось запустить временный Redis"
    exit 1
fi

# Шаг 4: Запуск PostgreSQL и Django
info "Запуск PostgreSQL и Django..."
docker-compose up -d postgres

# Ждем готовности PostgreSQL
info "Ожидание готовности PostgreSQL..."
for i in {1..30}; do
    if docker-compose exec -T postgres pg_isready -U gestalt >/dev/null 2>&1; then
        info "PostgreSQL готов"
        break
    fi
    if [ $i -eq 30 ]; then
        error "PostgreSQL не запустился за 30 секунд"
        exit 1
    fi
    sleep 1
done

# Запускаем Django для миграций
info "Запуск Django для выполнения миграций..."
docker-compose build geshtalt
docker-compose up -d geshtalt

# Ждем запуска Django
info "Ожидание запуска Django..."
sleep 10

# Шаг 5: Выполнение миграций БД
info "Выполнение миграций БД..."
docker-compose exec -T geshtalt python manage.py migrate --noinput

# Шаг 6: Миграция данных из Redis в PostgreSQL
info "Миграция данных из Redis в PostgreSQL..."

# Получаем SERVICE_USER_IDS из .env или используем дефолтные
SERVICE_USER_IDS="77415476,1179386959"
if [ -f "$PROJECT_DIR/.env" ]; then
    if grep -q "SERVICE_USER_IDS" "$PROJECT_DIR/.env"; then
        SERVICE_USER_IDS=$(grep "SERVICE_USER_IDS" "$PROJECT_DIR/.env" | cut -d '=' -f2 | tr -d '"' | tr -d "'")
    fi
fi

# Получаем пароль Redis из .env (если есть)
REDIS_PASSWORD=""
if [ -f "$PROJECT_DIR/.env" ]; then
    if grep -q "^REDIS_PASSWORD" "$PROJECT_DIR/.env"; then
        REDIS_PASSWORD=$(grep "^REDIS_PASSWORD" "$PROJECT_DIR/.env" | cut -d '=' -f2 | tr -d '"' | tr -d "'" | xargs)
    fi
fi

info "Миграция данных из Redis (redis-temp) в PostgreSQL..."
if [ -z "$REDIS_PASSWORD" ]; then
    info "Миграция без пароля Redis..."
    docker-compose exec -T geshtalt python manage.py migrate_from_redis \
        --redis-host=redis-temp \
        --redis-port=6379 \
        --service-user-ids="$SERVICE_USER_IDS"
else
    info "Миграция с паролем Redis..."
    docker-compose exec -T geshtalt python manage.py migrate_from_redis \
        --redis-host=redis-temp \
        --redis-port=6379 \
        --redis-password="$REDIS_PASSWORD" \
        --service-user-ids="$SERVICE_USER_IDS"
fi

# Шаг 7: Остановка временного Redis
info "Остановка временного Redis..."
docker-compose -f docker-compose-redis-temp.yaml down -v
rm -f "$DOCKER_DIR/docker-compose-redis-temp.yaml"

# Шаг 8: Запуск всех остальных сервисов
info "Запуск всех сервисов..."
docker-compose up -d

# Шаг 9: Ожидание запуска всех сервисов
info "Ожидание запуска всех сервисов..."
sleep 10

# Шаг 10: Проверка статуса
info "Проверка статуса контейнеров..."
docker-compose ps

# Шаг 11: Показ логов
info "Последние логи (Ctrl+C для выхода)..."
docker-compose logs --tail=50

echo ""
info "========================================="
info "Миграция завершена!"
info "========================================="
info "Проект находится в: $PROJECT_DIR"
info "Логи: cd $DOCKER_DIR && docker-compose logs -f"
info "Остановка: cd $DOCKER_DIR && docker-compose down"
info "Перезапуск: cd $DOCKER_DIR && docker-compose restart"
echo ""
warn "Не забудьте:"
warn "1. Проверить, что все данные мигрированы корректно"
warn "2. Создать суперпользователя: docker-compose exec geshtalt python manage.py createsuperuser"
warn "3. Проверить работу всех сервисов"
warn "4. Удалить старые volumes Redis, если они больше не нужны: docker volume ls | grep redis"


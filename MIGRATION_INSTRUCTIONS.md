# Инструкция по миграции на Django + PostgreSQL

## Что было сделано

1. ✅ Скачаны бэкапы Redis за 26 ноября (позавчера) из `/mnt/yandex/backup/`
   - `dump_20251126_020004.rdb`
   - `appendonlydir_20251126_020004/`
   - Сохранены в `data/backup/redis_20251126/`

2. ✅ Подготовлен скрипт миграции `scripts/migrate-to-postgres.sh`
   - Останавливает старые контейнеры (кроме amnezia)
   - Запускает временный Redis с бэкапом
   - Запускает PostgreSQL и Django
   - Мигрирует данные из Redis в PostgreSQL
   - Запускает все сервисы

3. ✅ Обновлен `docker-compose.yaml` с PostgreSQL вместо Redis
4. ✅ Исправлен `Dockerfile.django` для правильной структуры проекта

## Запуск миграции на сервере

### Подготовка

1. Убедитесь, что на сервере есть все необходимые файлы:
   ```bash
   ssh root@vdska
   cd ~/gestalt
   ls -la docker/docker-compose.yaml.new
   ls -la docker/Dockerfile.django
   ls -la scripts/migrate-to-postgres.sh
   ```

2. Проверьте наличие бэкапа:
   ```bash
   ls -la /mnt/yandex/backup/dump_20251126_020004.rdb
   ls -la /mnt/yandex/backup/appendonlydir_20251126_020004/
   ```

3. Убедитесь, что `.env` файл содержит необходимые переменные:
   - `POSTGRES_PASSWORD` - пароль для PostgreSQL
   - `REDIS_PASSWORD` - пароль для Redis (для миграции)
   - `SERVICE_USER_IDS` - ID пользователей через запятую (опционально)

### Запуск

```bash
ssh root@vdska
cd ~/gestalt
./scripts/migrate-to-postgres.sh
```

Скрипт выполнит следующие шаги:
1. Остановит все контейнеры кроме amnezia
2. Запустит временный Redis с бэкапом за 26 ноября
3. Запустит PostgreSQL и Django
4. Выполнит миграции БД
5. Мигрирует данные из Redis в PostgreSQL
6. Остановит временный Redis
7. Запустит все сервисы (nginx, alice, telegram-bot)

### После миграции

1. Проверьте статус контейнеров:
   ```bash
   cd ~/gestalt/docker
   docker-compose ps
   ```

2. Проверьте логи:
   ```bash
   docker-compose logs -f geshtalt
   ```

3. Создайте суперпользователя для админки Django:
   ```bash
   docker-compose exec geshtalt python manage.py createsuperuser
   ```

4. Проверьте, что данные мигрированы:
   ```bash
   docker-compose exec geshtalt python manage.py shell
   ```
   ```python
   from shopping_list.models import ShoppingItem, Category
   print(f"Категорий: {Category.objects.count()}")
   print(f"Элементов: {ShoppingItem.objects.count()}")
   ```

5. Проверьте работу API:
   ```bash
   curl http://localhost:8080/internal/api/list?category=купить
   ```

### Откат (если что-то пошло не так)

Если нужно вернуться к старой версии:

```bash
cd ~/gestalt/docker
docker-compose down
# Восстановите старый docker-compose.yaml
mv docker-compose.yaml docker-compose.yaml.new
# Восстановите старый docker-compose.yaml из бэкапа или git
docker-compose up -d
```

## Что изменилось

- **Backend**: Go + Redis → Django + PostgreSQL
- **Контейнеры**: 
  - Убран `redis` (больше не нужен)
  - Добавлен `postgres` (PostgreSQL 16)
  - Обновлен `geshtalt` (теперь Django вместо Go)
- **Данные**: Все данные из Redis мигрированы в PostgreSQL
- **API**: Полностью совместимо, никаких изменений в боте и Алисе не требуется

## Проверка работы

1. Проверьте, что все контейнеры запущены:
   ```bash
   docker ps | grep -E "postgres|geshtalt|nginx|alice|telegram-bot"
   ```

2. Проверьте доступность веб-интерфейса:
   ```bash
   curl -I http://localhost:8080
   ```

3. Проверьте работу Telegram бота и Алисы (они должны работать без изменений)

## Удаление старых данных

После успешной миграции можно удалить старые volumes Redis:

```bash
docker volume ls | grep redis
# Удалите ненужные volumes (будьте осторожны!)
docker volume rm <volume_name>
```


# Миграция на Django + PostgreSQL

## Что изменилось

- **Backend**: Go + Redis → Django + PostgreSQL
- **Админка**: Теперь доступна встроенная админка Django по `/admin/`
- **Шаблоны**: Статический HTML → Jinja2 шаблоны
- **API**: Полностью совместимо с текущими реализациями

## API Endpoints (без изменений)

Telegram бот и Алиса продолжают работать с теми же endpoints:
- `GET /internal/api/list?category=<name>`
- `POST /internal/api/add`
- `PUT /internal/api/buy/<name>?category=<name>`
- `DELETE /internal/api/delete/<name>?category=<name>`
- `PUT /internal/api/edit/<name>?category=<name>`

**Никаких изменений в коде бота и Алисы не требуется!**

## Шаги миграции

1. **Добавить переменные окружения в `.env`:**
   ```bash
   POSTGRES_PASSWORD=your_secure_password
   ```

2. **Запустить новые сервисы:**
   ```bash
   cd docker
   docker-compose up -d postgres geshtalt
   ```

3. **Выполнить миграции БД:**
   ```bash
   docker-compose exec geshtalt python manage.py migrate
   ```

4. **Создать категории и мигрировать данные из Redis:**
   ```bash
   # Сначала создаем категории (они создадутся автоматически при миграции)
   docker-compose exec geshtalt python manage.py migrate_from_redis \
       --redis-host=redis \
       --redis-password="s!mpleRed1sP@$" \
       --service-user-ids="user1,user2"
   ```

5. **Создать суперпользователя для админки:**
   ```bash
   docker-compose exec geshtalt python manage.py createsuperuser
   ```

6. **Перезапустить все сервисы:**
   ```bash
   docker-compose restart
   ```

## Проверка

- Веб-интерфейс: https://kpalch.ru/
- Админка: https://kpalch.ru/admin/
- Telegram бот: должен работать без изменений
- Алиса: должна работать без изменений

## Откат

Если что-то пошло не так, можно вернуться к старой версии:
```bash
cd docker
docker-compose stop geshtalt postgres
docker-compose rm geshtalt postgres
# Изменить docker-compose.yaml обратно на Go версию
docker-compose up -d
```


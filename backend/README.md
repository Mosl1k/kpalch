# Django Backend для Gestalt

Миграция с Go + Redis на Django + PostgreSQL.

## Структура проекта

```
backend_django/
├── gestalt/              # Основной проект Django
│   ├── settings.py      # Настройки
│   ├── urls.py          # URL маршруты
│   └── wsgi.py          # WSGI приложение
├── shopping_list/       # Приложение списков покупок
│   ├── models.py        # Модели (Category, ShoppingItem, UserProfile)
│   ├── views.py         # Views для веб-интерфейса
│   ├── internal_views.py # Views для Telegram бота и Алисы
│   ├── serializers.py   # Сериализаторы для API
│   ├── middleware.py    # Middleware для проверки Docker сети
│   └── admin.py         # Админка Django
└── templates/           # Jinja2 шаблоны
    └── shopping_list/
        ├── welcome.html # Приветственная страница
        └── index.html   # Основной интерфейс
```

## API Endpoints

### Публичные (требуют авторизации)
- `GET /list?category=<name>` - получить список
- `POST /add` - добавить элемент
- `PUT /buy/<name>?category=<name>` - отметить как купленный
- `DELETE /delete/<name>?category=<name>` - удалить элемент
- `PUT /edit/<name>?category=<name>` - редактировать элемент
- `POST /reorder` - изменить порядок

### Внутренние (для Telegram бота и Алисы, только из Docker сети)
- `GET /internal/api/list?category=<name>` - получить список
- `POST /internal/api/add` - добавить элемент
- `PUT /internal/api/buy/<name>?category=<name>` - отметить как купленный
- `DELETE /internal/api/delete/<name>?category=<name>` - удалить элемент
- `PUT /internal/api/edit/<name>?category=<name>` - редактировать элемент

## Миграция данных из Redis

```bash
python manage.py migrate_from_redis \
    --redis-host=redis \
    --redis-password="s!mpleRed1sP@$" \
    --service-user-ids="77415476,1179386959"
```

## Переменные окружения

- `POSTGRES_DB` - имя базы данных (по умолчанию: gestalt)
- `POSTGRES_USER` - пользователь БД (по умолчанию: gestalt)
- `POSTGRES_PASSWORD` - пароль БД
- `POSTGRES_HOST` - хост БД (по умолчанию: postgres)
- `SESSION_SECRET` - секретный ключ Django
- `YANDEX_CLIENT_ID` - ID приложения Yandex
- `YANDEX_CLIENT_SECRET` - секрет приложения Yandex
- `YANDEX_CALLBACK_URL` - URL для callback OAuth
- `SERVICE_USER_ID` - ID пользователя для сервисов
- `SERVICE_USER_IDS` - список ID пользователей через запятую

## Запуск

```bash
# Миграции БД
python manage.py migrate

# Создание суперпользователя (для админки)
python manage.py createsuperuser

# Запуск сервера разработки
python manage.py runserver

# Или через Gunicorn (для продакшена)
gunicorn --bind 0.0.0.0:8080 gestalt.wsgi:application
```

## Админка Django

Доступна по адресу `/admin/` после создания суперпользователя.

## Совместимость с Telegram ботом и Алисой

API endpoints полностью совместимы с текущими реализациями:
- Telegram бот использует `http://geshtalt:8080/internal/api/*`
- Алиса использует `http://geshtalt:8080/internal/api/*`

Никаких изменений в коде бота и Алисы не требуется!


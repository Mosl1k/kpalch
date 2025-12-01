# Gestalt - Список покупок

Система управления списками покупок с веб-интерфейсом, Telegram ботом и навыком для Yandex Алисы.

## Архитектура

- **Backend**: Django + PostgreSQL
- **Frontend**: Jinja2 шаблоны
- **Telegram Bot**: Python (python-telegram-bot)
- **Alice Skill**: Python (Flask)
- **Reverse Proxy**: Nginx
- **Database**: PostgreSQL

## Структура проекта

```
.
├── backend/              # Django приложение
│   ├── gestalt/         # Основной проект Django
│   ├── shopping_list/   # Приложение списков покупок
│   └── templates/       # Jinja2 шаблоны
├── services/            # Внешние сервисы
│   ├── alice/          # Навык Алисы
│   └── telegram-bot/   # Telegram бот
├── docker/              # Docker конфигурация
│   ├── Dockerfile.django
│   └── docker-compose.yaml
├── infra/               # Инфраструктура
│   ├── nginx/          # Nginx конфигурация
│   └── redis/          # Redis конфигурация (для кеширования, опционально)
└── scripts/             # Скрипты деплоя
    ├── smart-deploy.sh # Умный деплой (пересборка только измененных сервисов)
    └── deploy.sh       # Полный деплой
```

## Быстрый старт

### Локальная разработка

```bash
# Клонировать репозиторий
git clone https://github.com/Mosl1k/kpalch.git
cd kpalch

# Создать .env файл
cp .env.example .env
# Заполнить переменные окружения

# Запустить через Docker Compose
cd docker
docker-compose up -d

# Выполнить миграции
docker-compose exec geshtalt python manage.py migrate

# Создать суперпользователя
docker-compose exec geshtalt python manage.py createsuperuser
```

### Деплой на сервер

```bash
# Умный деплой (пересобирает только измененные сервисы)
./scripts/smart-deploy.sh

# Полный деплой
./scripts/deploy.sh
```

## API Endpoints

### Публичные (требуют авторизации)
- `GET /list?category=<name>` - получить список
- `POST /add` - добавить элемент
- `PUT /buy/<name>?category=<name>` - отметить как купленный
- `DELETE /delete/<name>?category=<name>` - удалить элемент
- `PUT /edit/<name>?category=<name>` - редактировать элемент
- `POST /reorder` - изменить порядок

### Внутренние (для Telegram бота и Алисы)
- `GET /internal/api/list?category=<name>`
- `POST /internal/api/add`
- `PUT /internal/api/buy/<name>?category=<name>`
- `DELETE /internal/api/delete/<name>?category=<name>`
- `PUT /internal/api/edit/<name>?category=<name>`

## Переменные окружения

См. `.env.example` или `.github/SECRETS.md`

## Миграция с Go + Redis

См. `MIGRATION_DJANGO.md`

## Админка Django

Доступна по адресу `/admin/` после создания суперпользователя.

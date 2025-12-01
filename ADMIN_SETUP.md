# Настройка администратора Django

## Создание суперпользователя

### Вариант 1: Через скрипт (рекомендуется)

```bash
ssh root@vdska
cd ~/gestalt
./scripts/create-admin.sh
```

Скрипт:
- Создаст суперпользователя с именем `admin`
- Использует пароль из `.env` (переменная `DJANGO_ADMIN_PASSWORD`), если она есть
- Или сгенерирует случайный пароль

### Вариант 2: Вручную через Django shell

```bash
ssh root@vdska
cd ~/gestalt/docker
docker-compose exec geshtalt python manage.py createsuperuser
```

### Вариант 3: Через переменные окружения

Добавьте в `~/gestalt/.env`:

```bash
DJANGO_ADMIN_USERNAME=admin
DJANGO_ADMIN_EMAIL=admin@gestalt.local
DJANGO_ADMIN_PASSWORD=your_secure_password_here
```

Затем запустите:

```bash
cd ~/gestalt
./scripts/create-admin.sh admin admin@gestalt.local
```

Пароль будет взят из `.env` файла.

## Доступ к админке

После создания суперпользователя админка доступна по адресу:
- https://kpalch.ru/admin/

## Проверка существующих суперпользователей

```bash
cd ~/gestalt/docker
docker-compose exec geshtalt python manage.py shell -c "
from django.contrib.auth.models import User
admins = User.objects.filter(is_superuser=True)
for admin in admins:
    print(f'Admin: {admin.username} ({admin.email})')
"
```


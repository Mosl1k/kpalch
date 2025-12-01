# Исправление ошибки 500 при OAuth callback

## Проблема
При авторизации через Yandex возникает ошибка 500 на `/auth/complete/yandex-oauth2/`.

## Причина
Yandex редиректит на стандартный URL `/auth/complete/yandex-oauth2/` вместо кастомного `/auth/yandex/callback`.

## Решение

### 1. Проверьте настройки в Yandex OAuth

**ВАЖНО:** В настройках приложения на https://oauth.yandex.ru/ должен быть указан:
```
https://kpalch.ru/auth/yandex/callback
```

**НЕ** `https://kpalch.ru/auth/complete/yandex-oauth2/`

### 2. Текущая конфигурация

- **Callback URL в коде:** `https://kpalch.ru/auth/yandex/callback`
- **Маршрут в Django:** `/auth/yandex/callback` → редирект на `/auth/complete/yandex-oauth2/`
- **Обработчик:** `/auth/complete/yandex-oauth2/` (стандартный обработчик social-auth-app-django)

### 3. Как это работает

1. Пользователь нажимает "Войти через Yandex"
2. Django формирует URL авторизации с `redirect_uri=https://kpalch.ru/auth/yandex/callback`
3. Yandex редиректит на `https://kpalch.ru/auth/yandex/callback`
4. Django редиректит на `/auth/complete/yandex-oauth2/` (внутренний обработчик)
5. social-auth-app-django обрабатывает callback и завершает авторизацию

### 4. Если ошибка 500 все еще возникает

Проверьте логи:
```bash
ssh root@vdska
cd ~/gestalt/docker
docker-compose logs geshtalt | tail -50
```

Частые причины:
- Отсутствие параметра `state` (нормально при прямом обращении, но не при редиректе от Yandex)
- Неправильный callback URL в настройках Yandex OAuth
- Проблемы с сессией (SESSION_COOKIE_SECURE, SESSION_COOKIE_HTTPONLY)

### 5. Проверка настроек

```bash
ssh root@vdska
cd ~/gestalt/docker
docker-compose exec geshtalt python -c "
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gestalt.settings')
import django
django.setup()
from django.conf import settings
print('YANDEX_CALLBACK_URL:', getattr(settings, 'YANDEX_CALLBACK_URL', 'Not set'))
print('SOCIAL_AUTH_YANDEX_OAUTH2_REDIRECT_URI:', getattr(settings, 'SOCIAL_AUTH_YANDEX_OAUTH2_REDIRECT_URI', 'Not set'))
"
```







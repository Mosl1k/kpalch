# Исправление ошибки OAuth "redirect_uri does not match"

## Проблема
Ошибка `redirect_uri does not match the Callback URL defined for the client` возникает, когда URL callback в Django не совпадает с тем, что указан в настройках приложения Yandex OAuth.

## Решение

### ✅ Исправлено автоматически

Callback URL в коде и `.env` обновлен на: `https://kpalch.ru/auth/yandex/callback`

### 1. Текущий callback URL в Django

В `backend/gestalt/settings.py` указан:
```python
YANDEX_CALLBACK_URL = os.getenv('YANDEX_CALLBACK_URL', 'https://kpalch.ru/auth/yandex/callback')
```

### 2. Маршрут в urls.py

Добавлен редирект с `/auth/yandex/callback` на `/auth/complete/yandex-oauth2/` (стандартный обработчик social-auth-app-django):
```python
path('auth/yandex/callback', RedirectView.as_view(url='/auth/complete/yandex-oauth2/', permanent=False), name='yandex_callback'),
```

### 3. Проверка .env на сервере

```bash
ssh root@vdska
cd ~/gestalt
grep YANDEX_CALLBACK_URL .env
```

Должно быть:
```bash
YANDEX_CALLBACK_URL=https://kpalch.ru/auth/yandex/callback
```

### 4. В настройках Yandex OAuth

В настройках приложения на https://oauth.yandex.ru/ должен быть указан:
```
https://kpalch.ru/auth/yandex/callback
```

### 4. Перезапустите контейнер

```bash
cd ~/gestalt/docker
docker-compose restart geshtalt
```

### 5. Проверка

После настройки проверьте:
```bash
cd ~/gestalt/docker
docker-compose exec geshtalt python -c "
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gestalt.settings')
import django
django.setup()
from django.conf import settings
print('Callback URL:', getattr(settings, 'YANDEX_CALLBACK_URL', 'Not set'))
"
```

## Альтернативные варианты callback URL

Если нужно использовать другой URL, можно указать в `.env`:
```bash
YANDEX_CALLBACK_URL=https://kpalch.ru/auth/yandex/callback
```

Но тогда нужно:
1. Обновить настройки в Yandex OAuth
2. Возможно, обновить маршруты в `backend/gestalt/urls.py`

## Примечание

Библиотека `social-auth-app-django` по умолчанию использует URL вида:
- `/auth/complete/<backend-name>/` - для завершения авторизации
- `/auth/login/<backend-name>/` - для начала авторизации

Где `<backend-name>` для Yandex - это `yandex-oauth2`.


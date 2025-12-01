# Исправление ошибки "Unknown client with such client_id"

## Проблема
Ошибка `Unknown client with such client_id` возникает, когда `YANDEX_CLIENT_ID` не установлен или неправильный в `.env` на сервере.

## Решение

### 1. Проверьте .env на сервере

```bash
ssh root@vdska
cd ~/gestalt
grep YANDEX .env
```

### 2. Добавьте переменные в .env

Если переменных нет, добавьте их:

```bash
ssh root@vdska
cd ~/gestalt
nano .env
```

Добавьте (замените на ваши реальные значения):
```bash
YANDEX_CLIENT_ID=ваш_client_id_из_oauth.yandex.ru
YANDEX_CLIENT_SECRET=ваш_client_secret_из_oauth.yandex.ru
YANDEX_CALLBACK_URL=https://kpalch.ru/auth/yandex/callback
```

### 3. Где взять CLIENT_ID и CLIENT_SECRET

1. Зайдите на https://oauth.yandex.ru/
2. Выберите ваше приложение (или создайте новое)
3. Скопируйте:
   - **ID приложения** → это `YANDEX_CLIENT_ID`
   - **Пароль** → это `YANDEX_CLIENT_SECRET`

### 4. Проверьте Callback URL в настройках Yandex

В настройках приложения на https://oauth.yandex.ru/ должен быть указан:
```
https://kpalch.ru/auth/yandex/callback
```

### 5. Перезапустите контейнер

```bash
ssh root@vdska
cd ~/gestalt/docker
docker-compose restart geshtalt
```

### 6. Проверка

```bash
ssh root@vdska
cd ~/gestalt/docker
docker-compose exec geshtalt python -c "
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gestalt.settings')
import django
django.setup()
from django.conf import settings
print('CLIENT_ID:', settings.SOCIAL_AUTH_YANDEX_OAUTH2_KEY or 'NOT SET')
print('CLIENT_SECRET:', 'SET' if settings.SOCIAL_AUTH_YANDEX_OAUTH2_SECRET else 'NOT SET')
"
```

Должно показать:
```
CLIENT_ID: ваш_client_id
CLIENT_SECRET: SET
```

## Важно

- `.env` файл не должен быть в git (он в `.gitignore`)
- Переменные окружения загружаются при старте контейнера
- После изменения `.env` нужно перезапустить контейнер


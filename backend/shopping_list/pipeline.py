"""
Custom pipeline для social-auth-app-django
Создает UserProfile при авторизации через Yandex
"""
from shopping_list.models import UserProfile


def get_username_from_yandex(strategy, details, backend, user=None, *args, **kwargs):
    """Получает username из Yandex login или email"""
    if backend.name == 'yandex-oauth2':
        response = kwargs.get('response', {})
        # Пробуем получить login из response
        login = response.get('login')
        if login:
            return {'username': login}
        
        # Если login нет, используем часть email до @
        email = response.get('default_email') or details.get('email')
        if email and '@' in email:
            username = email.split('@')[0]
            return {'username': username}
    
    return None


def create_user_profile(backend, user, response, *args, **kwargs):
    """Создает или обновляет UserProfile при авторизации через Yandex"""
    # Получаем пользователя из kwargs, если он не передан напрямую
    if not user:
        user = kwargs.get('user')
    
    # Проверяем, что пользователь существует (он должен быть создан на предыдущих шагах pipeline)
    if not user:
        return None
    
    if backend.name == 'yandex-oauth2':
        yandex_id = response.get('id')
        if yandex_id:
            # Получаем или создаем профиль
            profile, created = UserProfile.objects.get_or_create(
                user=user,
                defaults={'yandex_id': str(yandex_id)}
            )
            
            # Сохраняем Yandex ID
            profile.yandex_id = str(yandex_id)
            
            # Аватар
            avatar_id = response.get('default_avatar_id')
            if avatar_id:
                profile.avatar_url = f"https://avatars.yandex.net/get-yapic/{avatar_id}/islands-200"
            
            # Дата рождения (требует login:birthday в SCOPE)
            birthday = response.get('birthday')
            if birthday:
                try:
                    from datetime import datetime
                    # Yandex возвращает дату в формате 'YYYY-MM-DD' или может быть другой формат
                    date_formats = ['%Y-%m-%d', '%d.%m.%Y', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%dT%H:%M:%S.%fZ']
                    date_parsed = None
                    for date_format in date_formats:
                        try:
                            date_parsed = datetime.strptime(str(birthday), date_format).date()
                            break
                        except (ValueError, TypeError):
                            continue
                    
                    if date_parsed:
                        profile.date_of_birth = date_parsed
                    else:
                        # Если это строка вида "YYYY-MM-DD", пробуем разобрать вручную
                        birthday_str = str(birthday)
                        if len(birthday_str) >= 10 and '-' in birthday_str:
                            try:
                                parts = birthday_str[:10].split('-')
                                if len(parts) == 3:
                                    year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
                                    profile.date_of_birth = datetime(year, month, day).date()
                            except (ValueError, TypeError):
                                pass
                except Exception as e:
                    # Логируем ошибку для отладки
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.warning(f'Ошибка парсинга даты рождения: {birthday}, ошибка: {e}')
                    pass
            
            # Пол
            sex = response.get('sex')
            if sex in ['male', 'female']:
                profile.gender = sex
            
            # Телефон
            default_phone = response.get('default_phone', {})
            phone_number = default_phone.get('number') if isinstance(default_phone, dict) else None
            if phone_number:
                profile.phone_number = phone_number
            
            profile.save()
            
            # Обновляем данные пользователя Django: email, ФИО, username
            if response.get('first_name'):
                user.first_name = response.get('first_name', '')
            if response.get('last_name'):
                user.last_name = response.get('last_name', '')
            if response.get('default_email'):
                user.email = response.get('default_email')
            
            # Обновляем username из Yandex login
            login = response.get('login')
            if login and user.username != login:
                # Проверяем, не занят ли этот username другим пользователем
                from django.contrib.auth.models import User
                if not User.objects.filter(username=login).exclude(pk=user.pk).exists():
                    user.username = login
            
            user.save()
    
    return None


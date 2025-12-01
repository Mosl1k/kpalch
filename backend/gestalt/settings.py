"""
Django settings for gestalt project.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('SESSION_SECRET', 'django-insecure-change-me-in-production')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'

ALLOWED_HOSTS = ['*']  # В продакшене указать конкретные домены

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_jinja',
    'rest_framework',
    'social_django',
    'shopping_list',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'shopping_list.middleware.InternalNetworkMiddleware',  # Проверка Docker сети для /internal/api/
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'shopping_list.middleware.UserProfileMiddleware',  # Автоматическое создание UserProfile
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# CSRF настройки
CSRF_TRUSTED_ORIGINS = [
    'https://kpalch.ru',
    'https://www.kpalch.ru',
    'http://localhost:8080',
]

# Исключения для CSRF (OAuth callback обрабатывается через social-auth-app-django)
CSRF_EXEMPT_URLS = [
    r'^/auth/complete/',
    r'^/auth/yandex/callback',
]

ROOT_URLCONF = 'gestalt.urls'

TEMPLATES = [
    {
        'BACKEND': 'django_jinja.backend.Jinja2',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'environment': 'gestalt.jinja2_config.environment',
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'gestalt.wsgi.application'

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('POSTGRES_DB', 'gestalt'),
        'USER': os.getenv('POSTGRES_USER', 'gestalt'),
        'PASSWORD': os.getenv('POSTGRES_PASSWORD', 'gestalt'),
        'HOST': os.getenv('POSTGRES_HOST', 'postgres'),
        'PORT': os.getenv('POSTGRES_PORT', '5432'),
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'ru-ru'
TIME_ZONE = 'Europe/Moscow'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Session settings
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_ENGINE = 'django.contrib.sessions.backends.db'
# Домены для кук
# Временно отключаем домен для кук, чтобы избежать проблем с OAuth сессиями
# SESSION_COOKIE_DOMAIN = '.kpalch.ru'
# CSRF_COOKIE_DOMAIN = '.kpalch.ru'
CSRF_COOKIE_SECURE = True

# OAuth2 settings
AUTHENTICATION_BACKENDS = (
    'shopping_list.backends.CustomYandexOAuth2',  # Кастомный бэкенд с правильным redirect_uri
    'django.contrib.auth.backends.ModelBackend',
)

SOCIAL_AUTH_YANDEX_OAUTH2_KEY = os.getenv('YANDEX_CLIENT_ID')
SOCIAL_AUTH_YANDEX_OAUTH2_SECRET = os.getenv('YANDEX_CLIENT_SECRET')
SOCIAL_AUTH_YANDEX_OAUTH2_SCOPE = ['login:email', 'login:info', 'login:avatar', 'login:birthday']

# URL для callback
YANDEX_CALLBACK_URL = os.getenv('YANDEX_CALLBACK_URL', 'https://kpalch.ru/auth/yandex/callback')
SOCIAL_AUTH_YANDEX_OAUTH2_REDIRECT_URI = YANDEX_CALLBACK_URL

LOGIN_URL = '/login'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'

# Настройки редиректа для social-auth-app-django
SOCIAL_AUTH_LOGIN_REDIRECT_URL = '/'
SOCIAL_AUTH_NEW_USER_REDIRECT_URL = '/'
SOCIAL_AUTH_LOGIN_ERROR_URL = '/'
SOCIAL_AUTH_NEW_ASSOCIATION_REDIRECT_URL = '/'
SOCIAL_AUTH_DISCONNECT_REDIRECT_URL = '/'

SOCIAL_AUTH_PIPELINE = (
    'social_core.pipeline.social_auth.social_details',
    'social_core.pipeline.social_auth.social_uid',
    'social_core.pipeline.social_auth.auth_allowed',
    'social_core.pipeline.social_auth.social_user',
    'shopping_list.pipeline.get_username_from_yandex',  # Кастомный pipeline для получения username из Yandex
    'social_core.pipeline.user.get_username',
    'social_core.pipeline.user.create_user',
    'social_core.pipeline.social_auth.associate_user',
    'social_core.pipeline.social_auth.load_extra_data',
    'social_core.pipeline.user.user_details',
    'shopping_list.pipeline.create_user_profile',  # Кастомный pipeline для создания профиля (после создания пользователя)
)

# REST Framework settings
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
}

# Internal API settings (для Telegram бота и Алисы)
SERVICE_USER_ID = os.getenv('SERVICE_USER_ID', '')
SERVICE_USER_IDS = os.getenv('SERVICE_USER_IDS', '').split(',') if os.getenv('SERVICE_USER_IDS') else []

# Redis для кеширования (опционально)
REDIS_URL = os.getenv('REDIS_URL', 'redis://redis:6379/0')


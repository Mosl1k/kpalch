"""
Кастомный бэкенд для Yandex OAuth с правильным redirect_uri
"""
from social_core.backends.yandex import YandexOAuth2


class CustomYandexOAuth2(YandexOAuth2):
    """Кастомный бэкенд Yandex OAuth с фиксированным redirect_uri"""
    
    def get_redirect_uri(self, state=None):
        """Переопределяем метод для использования кастомного redirect_uri"""
        from django.conf import settings
        
        # Используем кастомный redirect_uri из настроек
        redirect_uri = getattr(settings, 'SOCIAL_AUTH_YANDEX_OAUTH2_REDIRECT_URI', None)
        if redirect_uri:
            return redirect_uri
        
        # Если не задан, используем стандартный метод
        return super().get_redirect_uri(state)
    
    def auth_url(self):
        """Переопределяем метод для использования правильного redirect_uri в URL авторизации"""
        from django.conf import settings
        
        # Получаем redirect_uri из настроек
        redirect_uri = getattr(settings, 'SOCIAL_AUTH_YANDEX_OAUTH2_REDIRECT_URI', None)
        if redirect_uri:
            # Сохраняем redirect_uri в настройках бэкенда
            self.REDIRECT_URI = redirect_uri
        
        return super().auth_url()


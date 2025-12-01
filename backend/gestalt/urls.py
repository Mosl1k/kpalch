"""
URL configuration for gestalt project.
"""
from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from django.contrib.auth import views as auth_views
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponseRedirect
from urllib.parse import urlencode
from django.contrib.auth.views import LoginView

# Кастомный callback для Yandex OAuth на /auth/yandex/callback
# Используем стандартный подход social-auth-app-django (аналог goth в Go)
# Прямо вызываем complete view с правильным backend
@csrf_exempt
def yandex_callback(request):
    """Обработчик callback для Yandex OAuth на кастомном URL"""
    from social_django.views import complete
    # Вызываем стандартный обработчик complete с указанием backend
    return complete(request, 'yandex-oauth2')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('login', LoginView.as_view(template_name='shopping_list/login.html'), name='login'),
    path('auth/yandex', RedirectView.as_view(url='/auth/login/yandex-oauth2/', permanent=False), name='yandex_auth'),
    # Кастомный callback URL для Yandex OAuth (аналог goth в Go)
    path('auth/yandex/callback', yandex_callback, name='yandex_callback'),
    path('auth/', include('social_django.urls', namespace='social')),
    path('logout', auth_views.LogoutView.as_view(next_page='/'), name='logout'),
    # API endpoints - включаем с префиксом /api/
    path('api/', include('shopping_list.api_urls')),
    path('internal/api/', include('shopping_list.internal_urls')),
    # Страницы - включаем без префикса
    path('', include('shopping_list.urls')),
]


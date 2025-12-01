"""
Middleware для проверки, что запросы к внутреннему API идут из Docker сети
"""
from django.http import JsonResponse
from django.conf import settings
import ipaddress


class InternalNetworkMiddleware:
    """
    Проверяет, что запрос к /internal/api/ идет из Docker сети
    Разрешенные сети: 172.16.0.0/12, 192.168.0.0/16, 10.0.0.0/8
    """
    def __init__(self, get_response):
        self.get_response = get_response
        # Docker сети
        self.allowed_networks = [
            ipaddress.ip_network('172.16.0.0/12'),
            ipaddress.ip_network('192.168.0.0/16'),
            ipaddress.ip_network('10.0.0.0/8'),
        ]

    def __call__(self, request):
        # Проверяем только запросы к внутреннему API
        if request.path.startswith('/internal/api/'):
            # Получаем IP адрес клиента
            client_ip = self.get_client_ip(request)
            
            if not self.is_allowed_ip(client_ip):
                return JsonResponse(
                    {'error': 'Access denied. Internal API is only available from Docker network.'},
                    status=403
                )
        
        response = self.get_response(request)
        return response

    def get_client_ip(self, request):
        """Получить IP адрес клиента"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', '')
        
        # Убираем порт если есть
        if ':' in ip:
            ip = ip.split(':')[0]
        
        return ip

    def is_allowed_ip(self, ip):
        """Проверить, разрешен ли IP адрес"""
        try:
            ip_obj = ipaddress.ip_address(ip)
            for network in self.allowed_networks:
                if ip_obj in network:
                    return True
            return False
        except ValueError:
            return False


class UserProfileMiddleware:
    """Middleware для автоматического создания UserProfile, если его нет"""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            try:
                # Проверяем наличие профиля
                request.user.profile
            except:
                # Если профиля нет, создаем его
                from .models import UserProfile
                try:
                    import time
                    unique_id = f"local-{request.user.id}-{int(time.time() * 1000)}"
                    UserProfile.objects.create(
                        user=request.user,
                        yandex_id=unique_id
                    )
                except Exception:
                    # Игнорируем ошибки создания профиля, чтобы не блокировать запрос
                    # Профиль будет создан при следующем запросе или через view
                    pass
        
        response = self.get_response(request)
        return response


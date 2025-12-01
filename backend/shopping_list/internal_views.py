"""
Внутренние views для Telegram бота и Алисы
Доступны без авторизации, но только из Docker сети
"""
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.contrib.auth.models import User
from .models import ShoppingItem, Category
import json


def get_service_user_ids(request):
    """Получить список user_id для сервисов (с учетом заголовка X-User-ID)"""
    # Сначала проверяем заголовок X-User-ID (как в Go версии)
    x_user_id = request.headers.get('X-User-ID', '')
    if x_user_id:
        return [x_user_id.strip()]
    
    # Если заголовка нет, используем переменные окружения
    user_ids = []
    if settings.SERVICE_USER_ID:
        user_ids.append(settings.SERVICE_USER_ID)
    if settings.SERVICE_USER_IDS:
        user_ids.extend([uid.strip() for uid in settings.SERVICE_USER_IDS if uid.strip()])
    return user_ids if user_ids else ['service']


def get_service_users(request):
    """Получить пользователей для сервисов"""
    user_ids = get_service_user_ids(request)
    users = User.objects.filter(username__in=user_ids)
    return users


@csrf_exempt
@require_http_methods(["GET"])
def internal_list(request):
    """Получить список элементов (объединенный для всех сервисных пользователей)"""
    category_name = request.GET.get('category')
    if not category_name:
        return JsonResponse({'error': 'Category is required'}, status=400)
    
    try:
        category = Category.objects.get(name=category_name)
    except Category.DoesNotExist:
        return JsonResponse({'error': 'Category not found'}, status=404)
    
    users = get_service_users(request)
    items = ShoppingItem.objects.filter(
        user__in=users,
        category=category
    ).order_by('user__username', 'order', '-priority', 'name')
    
    # Формируем ответ в формате старого API
    result = []
    
    for item in items:
        # Убираем префикс с логином - показываем только имя элемента
        result.append({
            'name': item.name,
            'category': category.name,
            'bought': item.bought,
            'priority': item.priority,
        })
    
    return JsonResponse(result, safe=False)


@csrf_exempt
@require_http_methods(["POST"])
def internal_add(request):
    """Добавить элемент"""
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    
    category_name = data.get('category')
    name = data.get('name', '').strip()
    priority = int(data.get('priority', 2))
    
    if not category_name or not name:
        return JsonResponse({'error': 'Category and name are required'}, status=400)
    
    try:
        category = Category.objects.get(name=category_name)
    except Category.DoesNotExist:
        return JsonResponse({'error': 'Category not found'}, status=404)
    
    # Используем первого сервисного пользователя для добавления
    users = get_service_users(request)
    if not users.exists():
        return JsonResponse({'error': 'No service users configured'}, status=500)
    
    user = users.first()
    
    # Проверяем, не существует ли уже такой элемент
    if ShoppingItem.objects.filter(user=user, name=name, category=category).exists():
        return JsonResponse({'error': 'Item already exists'}, status=400)
    
    # Определяем порядок
    from django.db.models import Max
    max_order = ShoppingItem.objects.filter(
        user=user,
        category=category
    ).aggregate(Max('order'))['order__max'] or 0
    
    item = ShoppingItem.objects.create(
        user=user,
        name=name,
        category=category,
        priority=priority,
        order=max_order + 1
    )
    
    return JsonResponse({
        'name': item.name,
        'category': category.name,
        'bought': item.bought,
        'priority': item.priority,
    }, status=201)


@csrf_exempt
@require_http_methods(["PUT"])
def internal_buy(request, name):
    """Отметить элемент как купленный"""
    category_name = request.GET.get('category')
    if not category_name:
        return JsonResponse({'error': 'Category is required'}, status=400)
    
    try:
        category = Category.objects.get(name=category_name)
        users = get_service_users(request)
        item = ShoppingItem.objects.get(user__in=users, name=name, category=category)
    except (Category.DoesNotExist, ShoppingItem.DoesNotExist):
        return JsonResponse({'error': 'Item not found'}, status=404)
    
    try:
        data = json.loads(request.body)
        item.bought = data.get('bought', not item.bought)
    except json.JSONDecodeError:
        item.bought = not item.bought
    
    item.save()
    
    return JsonResponse({
        'name': item.name,
        'category': category.name,
        'bought': item.bought,
        'priority': item.priority,
    })


@csrf_exempt
@require_http_methods(["DELETE"])
def internal_delete(request, name):
    """Удалить элемент"""
    category_name = request.GET.get('category')
    if not category_name:
        return JsonResponse({'error': 'Category is required'}, status=400)
    
    try:
        category = Category.objects.get(name=category_name)
        users = get_service_users(request)
        item = ShoppingItem.objects.get(user__in=users, name=name, category=category)
    except (Category.DoesNotExist, ShoppingItem.DoesNotExist):
        return JsonResponse({'error': 'Item not found'}, status=404)
    
    item.delete()
    return JsonResponse({'message': 'Item deleted'}, status=200)


@csrf_exempt
@require_http_methods(["PUT"])
def internal_edit(request, name):
    """Редактировать элемент"""
    category_name = request.GET.get('oldCategory') or request.GET.get('category')
    if not category_name:
        return JsonResponse({'error': 'Category is required'}, status=400)
    
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    
    try:
        category = Category.objects.get(name=category_name)
        users = get_service_users(request)
        item = ShoppingItem.objects.get(user__in=users, name=name, category=category)
    except (Category.DoesNotExist, ShoppingItem.DoesNotExist):
        return JsonResponse({'error': 'Item not found'}, status=404)
    
    # Обновляем название
    if 'name' in data:
        item.name = data['name'].strip()
    
    # Обновляем категорию
    if 'category' in data:
        try:
            new_category = Category.objects.get(name=data['category'])
            item.category = new_category
        except Category.DoesNotExist:
            return JsonResponse({'error': 'New category not found'}, status=404)
    
    # Обновляем приоритет
    if 'priority' in data:
        item.priority = int(data['priority'])
    
    item.save()
    
    return JsonResponse({
        'name': item.name,
        'category': item.category.name,
        'bought': item.bought,
        'priority': item.priority,
    })


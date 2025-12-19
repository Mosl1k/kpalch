"""
Внутренние views для Telegram бота и Алисы
Доступны без авторизации, но только из Docker сети
"""
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.contrib.auth.models import User
from .models import ShoppingItem, Category, SharedListConnection
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
    """Получить список элементов (объединенный для всех сервисных пользователей, учитывая общие списки)"""
    category_name = request.GET.get('category')
    if not category_name:
        return JsonResponse({'error': 'Category is required'}, status=400)
    
    try:
        category = Category.objects.get(name=category_name)
    except Category.DoesNotExist:
        return JsonResponse({'error': 'Category not found'}, status=404)
    
    users = get_service_users(request)
    
    # Если пользователи не найдены, возвращаем пустой список
    if not users.exists():
        import logging
        logger = logging.getLogger(__name__)
        user_ids = get_service_user_ids(request)
        logger.warning(f"No service users found for IDs: {user_ids}")
        return JsonResponse([], safe=False)
    
    # Собираем пользователей, элементы которых нужно показать
    # Если у пользователя категория общая, берем владельца
    owner_users = set()
    for user in users:
        connection = SharedListConnection.objects.filter(
            shared_user=user,
            category=category
        ).first()
        if connection:
            owner_users.add(connection.owner_user)
        else:
            owner_users.add(user)
    
    # Если не нашли владельцев, возвращаем пустой список
    if not owner_users:
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"No owner users found for category: {category_name}, service users: {list(users.values_list('username', flat=True))}")
        return JsonResponse([], safe=False)
    
    items = ShoppingItem.objects.filter(
        user__in=owner_users,
        category=category
    ).order_by('order', '-priority', 'name')
    
    # Логирование для отладки
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"internal_list: category={category_name}, owner_users={[u.username for u in owner_users]}, items_count={items.count()}")
    
    # Формируем ответ в формате старого API
    result = []
    
    for item in items:
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
    
    # Проверяем, является ли категория общей для этого пользователя
    connection = SharedListConnection.objects.filter(
        shared_user=user,
        category=category
    ).first()
    target_user = connection.owner_user if connection else user
    
    # Проверяем, не существует ли уже такой элемент
    if ShoppingItem.objects.filter(user=target_user, name=name, category=category).exists():
        return JsonResponse({'error': 'Item already exists'}, status=400)
    
    # Определяем порядок
    from django.db.models import Max
    max_order = ShoppingItem.objects.filter(
        user=target_user,
        category=category
    ).aggregate(Max('order'))['order__max'] or 0
    
    item = ShoppingItem.objects.create(
        user=target_user,
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
        
        # Для каждого пользователя проверяем общие списки
        owner_users = set()
        for user in users:
            connection = SharedListConnection.objects.filter(
                shared_user=user,
                category=category
            ).first()
            if connection:
                owner_users.add(connection.owner_user)
            else:
                owner_users.add(user)
        
        item = ShoppingItem.objects.get(user__in=owner_users, name=name, category=category)
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
        
        # Для каждого пользователя проверяем общие списки
        owner_users = set()
        for user in users:
            connection = SharedListConnection.objects.filter(
                shared_user=user,
                category=category
            ).first()
            if connection:
                owner_users.add(connection.owner_user)
            else:
                owner_users.add(user)
        
        item = ShoppingItem.objects.get(user__in=owner_users, name=name, category=category)
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
        
        # Для каждого пользователя проверяем общие списки
        owner_users = set()
        for user in users:
            connection = SharedListConnection.objects.filter(
                shared_user=user,
                category=category
            ).first()
            if connection:
                owner_users.add(connection.owner_user)
            else:
                owner_users.add(user)
        
        item = ShoppingItem.objects.get(user__in=owner_users, name=name, category=category)
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


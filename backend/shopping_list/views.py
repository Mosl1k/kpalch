from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Max, Q
from .models import ShoppingItem, Category, Friendship, SharedList
from .serializers import ShoppingItemSerializer, CategorySerializer, UserSerializer, FriendshipSerializer, SharedListSerializer
from django.contrib.auth.models import User
import json


def friends(request):
    """Страница управления друзьями"""
    if not request.user.is_authenticated:
        return redirect('login')
    
    return render(request, 'shopping_list/friends.html', {
        'user': request.user,
    })


def index(request):
    """Главная страница со списками покупок"""
    if not request.user.is_authenticated:
        return render(request, 'shopping_list/welcome.html')
    
    # Получаем все категории
    categories = Category.objects.all()
    
    # Получаем текущую категорию из GET параметра
    category_name = request.GET.get('category', 'купить')
    current_category = None
    
    try:
        current_category = Category.objects.get(name=category_name)
    except Category.DoesNotExist:
        # Если категория не найдена, используем первую доступную
        if categories.exists():
            current_category = categories.first()
            category_name = current_category.name
    
    # Получаем элементы для текущей категории
    # Если пользователь - админ, показываем все элементы, иначе только свои
    items = []
    if current_category:
        if request.user.is_superuser:
            # Админ видит все элементы
            items = ShoppingItem.objects.filter(
                category=current_category
            ).order_by('order', '-priority', 'name')
        else:
            # Обычный пользователь видит только свои элементы
            items = ShoppingItem.objects.filter(
                user=request.user,
                category=current_category
            ).order_by('order', '-priority', 'name')
    
    # Передаем информацию о том, какие категории можно удалять
    categories_with_deletable = []
    for category in categories:
        categories_with_deletable.append({
            'category': category,
            'can_delete': category.can_be_deleted_by(request.user)
        })
    
    return render(request, 'shopping_list/index.html', {
        'user': request.user,
        'categories_with_deletable': categories_with_deletable,
        'categories': categories,  # Для обратной совместимости
        'current_category': category_name,
        'items': items,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_items(request):
    """Получить список элементов по категории"""
    category_name = request.GET.get('category')
    if not category_name:
        return Response({'error': 'Category is required'}, status=400)
    
    try:
        category = Category.objects.get(name=category_name)
    except Category.DoesNotExist:
        return Response({'error': 'Category not found'}, status=404)
    
    items = ShoppingItem.objects.filter(
        user=request.user,
        category=category
    ).order_by('order', '-priority', 'name')
    
    serializer = ShoppingItemSerializer(items, many=True)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_category(request):
    """Добавить новую категорию (список)"""
    data = request.data
    category_name = data.get('name', '').strip().lower()
    display_name = data.get('display_name', '').strip()
    
    if not category_name:
        return Response({'error': 'Category name is required'}, status=400)
    
    if not display_name:
        display_name = category_name.capitalize()
    
    # Проверяем, не существует ли уже такая категория
    if Category.objects.filter(name=category_name).exists():
        return Response({'error': 'Category already exists'}, status=400)
    
    category = Category.objects.create(
        name=category_name,
        display_name=display_name,
        created_by=request.user  # Сохраняем создателя категории
    )
    
    serializer = CategorySerializer(category)
    return Response(serializer.data, status=201)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_category(request, category_name):
    """Удалить категорию (список) и все её элементы"""
    try:
        category = Category.objects.get(name=category_name)
    except Category.DoesNotExist:
        return Response({'error': 'Category not found'}, status=404)
    
    # Проверяем, может ли пользователь удалить эту категорию
    if not category.can_be_deleted_by(request.user):
        return Response({'error': 'Нельзя удалить эту категорию'}, status=403)
    
    # Подсчитываем количество элементов в категории
    items_count = ShoppingItem.objects.filter(category=category).count()
    
    # Удаляем все элементы категории
    ShoppingItem.objects.filter(category=category).delete()
    
    # Удаляем саму категорию
    category.delete()
    
    return Response({
        'message': f'Category deleted. {items_count} items removed.'
    }, status=200)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_item(request):
    """Добавить элемент в список"""
    data = request.data
    category_name = data.get('category')
    name = data.get('name', '').strip()
    priority = int(data.get('priority', 2))
    
    if not category_name or not name:
        return Response({'error': 'Category and name are required'}, status=400)
    
    try:
        category = Category.objects.get(name=category_name)
    except Category.DoesNotExist:
        return Response({'error': 'Category not found'}, status=404)
    
    # Проверяем, не существует ли уже такой элемент
    if ShoppingItem.objects.filter(user=request.user, name=name, category=category).exists():
        return Response({'error': 'Item already exists'}, status=400)
    
    # Определяем порядок (максимальный + 1)
    max_order = ShoppingItem.objects.filter(
        user=request.user,
        category=category
    ).aggregate(Max('order'))['order__max'] or 0
    
    item = ShoppingItem.objects.create(
        user=request.user,
        name=name,
        category=category,
        priority=priority,
        order=max_order + 1
    )
    
    serializer = ShoppingItemSerializer(item)
    return Response(serializer.data, status=201)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def buy_item(request, name):
    """Отметить элемент как купленный/некупленный"""
    category_name = request.GET.get('category')
    if not category_name:
        return Response({'error': 'Category is required'}, status=400)
    
    try:
        category = Category.objects.get(name=category_name)
        # Если админ, ищем элемент без фильтра по user
        if request.user.is_superuser:
            item = ShoppingItem.objects.get(name=name, category=category)
        else:
            item = ShoppingItem.objects.get(user=request.user, name=name, category=category)
    except (Category.DoesNotExist, ShoppingItem.DoesNotExist):
        return Response({'error': 'Item not found'}, status=404)
    
    data = request.data
    item.bought = data.get('bought', not item.bought)
    item.save()
    
    serializer = ShoppingItemSerializer(item)
    return Response(serializer.data)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_item(request, name):
    """Удалить элемент"""
    category_name = request.GET.get('category')
    if not category_name:
        return Response({'error': 'Category is required'}, status=400)
    
    try:
        category = Category.objects.get(name=category_name)
        # Если админ, ищем элемент без фильтра по user
        if request.user.is_superuser:
            item = ShoppingItem.objects.get(name=name, category=category)
        else:
            item = ShoppingItem.objects.get(user=request.user, name=name, category=category)
    except (Category.DoesNotExist, ShoppingItem.DoesNotExist):
        return Response({'error': 'Item not found'}, status=404)
    
    item.delete()
    return Response({'message': 'Item deleted'}, status=200)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def edit_item(request, name):
    """Редактировать элемент"""
    category_name = request.GET.get('oldCategory') or request.GET.get('category')
    if not category_name:
        return Response({'error': 'Category is required'}, status=400)
    
    try:
        category = Category.objects.get(name=category_name)
        item = ShoppingItem.objects.get(user=request.user, name=name, category=category)
    except (Category.DoesNotExist, ShoppingItem.DoesNotExist):
        return Response({'error': 'Item not found'}, status=404)
    
    data = request.data
    
    # Обновляем название, если указано
    if 'name' in data:
        item.name = data['name'].strip()
    
    # Обновляем категорию, если указано
    if 'category' in data:
        try:
            new_category = Category.objects.get(name=data['category'])
            item.category = new_category
        except Category.DoesNotExist:
            return Response({'error': 'New category not found'}, status=404)
    
    # Обновляем приоритет, если указан
    if 'priority' in data:
        item.priority = int(data['priority'])
    
    item.save()
    
    serializer = ShoppingItemSerializer(item)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def reorder_items(request):
    """Изменить порядок элементов"""
    items = request.data
    if not isinstance(items, list):
        return Response({'error': 'Items must be a list'}, status=400)
    
    for index, item_data in enumerate(items):
        try:
            item = ShoppingItem.objects.get(
                user=request.user,
                name=item_data.get('name'),
                category__name=item_data.get('category')
            )
            item.order = index
            item.save()
        except ShoppingItem.DoesNotExist:
            continue
    
    return Response({'message': 'Order updated'}, status=200)


# ========== API для друзей ==========

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_users(request):
    """Получить список всех пользователей, авторизованных через Yandex"""
    # Получаем только пользователей с Yandex профилем
    users = User.objects.filter(profile__yandex_id__isnull=False).exclude(id=request.user.id)
    
    # Получаем список друзей (принятые запросы)
    friendships = Friendship.objects.filter(
        status='accepted'
    ).filter(
        Q(from_user=request.user) | Q(to_user=request.user)
    )
    friend_ids = set()
    for friendship in friendships:
        if friendship.from_user == request.user:
            friend_ids.add(friendship.to_user.id)
        else:
            friend_ids.add(friendship.from_user.id)
    
    # Получаем список пользователей, которым МЫ отправили запрос (исходящие pending)
    # НЕ исключаем тех, кто отправил запрос нам - они должны быть видны в разделе "Входящие запросы"
    outgoing_pending = Friendship.objects.filter(
        from_user=request.user,
        status='pending'
    )
    pending_user_ids = set()
    for friendship in outgoing_pending:
        pending_user_ids.add(friendship.to_user.id)
    
    # Исключаем друзей и пользователей, которым мы уже отправили запрос
    users = users.exclude(id__in=friend_ids).exclude(id__in=pending_user_ids)
    
    serializer = UserSerializer(users, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_friends(request):
    """Получить список друзей (принятые запросы)"""
    # Друзья - это принятые запросы, где пользователь либо отправитель, либо получатель
    friendships = Friendship.objects.filter(
        status='accepted'
    ).filter(
        Q(from_user=request.user) | Q(to_user=request.user)
    )
    
    # Получаем друзей (не самого пользователя)
    friends = []
    for friendship in friendships:
        if friendship.from_user == request.user:
            friends.append(friendship.to_user)
        else:
            friends.append(friendship.from_user)
    
    serializer = UserSerializer(friends, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_friend_requests(request):
    """Получить список входящих и исходящих запросов на дружбу"""
    incoming = Friendship.objects.filter(to_user=request.user, status='pending')
    outgoing = Friendship.objects.filter(from_user=request.user, status='pending')
    
    return Response({
        'incoming': FriendshipSerializer(incoming, many=True).data,
        'outgoing': FriendshipSerializer(outgoing, many=True).data,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_friend_request(request):
    """Отправить запрос на дружбу"""
    to_user_id = request.data.get('user_id')
    if not to_user_id:
        return Response({'error': 'user_id is required'}, status=400)
    
    try:
        to_user = User.objects.get(id=to_user_id)
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=404)
    
    if to_user == request.user:
        return Response({'error': 'Cannot send friend request to yourself'}, status=400)
    
    # Проверяем, не существует ли уже запрос
    friendship, created = Friendship.objects.get_or_create(
        from_user=request.user,
        to_user=to_user,
        defaults={'status': 'pending'}
    )
    
    if not created:
        if friendship.status == 'accepted':
            return Response({'error': 'Already friends'}, status=400)
        elif friendship.status == 'pending':
            return Response({'error': 'Friend request already sent'}, status=400)
        else:
            # Если был отклонен, обновляем статус
            friendship.status = 'pending'
            friendship.save()
    
    serializer = FriendshipSerializer(friendship)
    return Response(serializer.data, status=201)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def accept_friend_request(request, friendship_id):
    """Принять запрос на дружбу"""
    try:
        friendship = Friendship.objects.get(id=friendship_id, to_user=request.user, status='pending')
    except Friendship.DoesNotExist:
        return Response({'error': 'Friend request not found'}, status=404)
    
    friendship.status = 'accepted'
    friendship.save()
    
    serializer = FriendshipSerializer(friendship)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def reject_friend_request(request, friendship_id):
    """Отклонить запрос на дружбу"""
    try:
        friendship = Friendship.objects.get(id=friendship_id, to_user=request.user, status='pending')
    except Friendship.DoesNotExist:
        return Response({'error': 'Friend request not found'}, status=404)
    
    friendship.status = 'rejected'
    friendship.save()
    
    return Response({'message': 'Friend request rejected'}, status=200)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def remove_friend(request, friendship_id):
    """Удалить друга (удалить дружбу)"""
    try:
        friendship = Friendship.objects.filter(
            id=friendship_id,
            status='accepted'
        ).filter(
            Q(from_user=request.user) | Q(to_user=request.user)
        ).first()
        
        if not friendship:
            return Response({'error': 'Friendship not found'}, status=404)
    except Friendship.DoesNotExist:
        return Response({'error': 'Friendship not found'}, status=404)
    
    friendship.delete()
    return Response({'message': 'Friend removed'}, status=200)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def remove_friend_by_user(request):
    """Удалить друга по user_id"""
    user_id = request.data.get('user_id')
    if not user_id:
        return Response({'error': 'user_id is required'}, status=400)
    
    try:
        friend_user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=404)
    
    friendship = Friendship.objects.filter(
        status='accepted'
    ).filter(
        (Q(from_user=request.user) & Q(to_user=friend_user)) |
        (Q(from_user=friend_user) & Q(to_user=request.user))
    ).first()
    
    if not friendship:
        return Response({'error': 'Friendship not found'}, status=404)
    
    friendship.delete()
    return Response({'message': 'Friend removed'}, status=200)


# ========== API для шаринга списков ==========

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def share_list(request):
    """Отправить список другу"""
    to_user_id = request.data.get('user_id')
    category_name = request.data.get('category')
    message = request.data.get('message', '')
    
    if not to_user_id or not category_name:
        return Response({'error': 'user_id and category are required'}, status=400)
    
    try:
        to_user = User.objects.get(id=to_user_id)
        category = Category.objects.get(name=category_name)
    except (User.DoesNotExist, Category.DoesNotExist):
        return Response({'error': 'User or category not found'}, status=404)
    
    # Проверяем, что пользователь - друг
    friendship = Friendship.objects.filter(
        status='accepted'
    ).filter(
        (Q(from_user=request.user) & Q(to_user=to_user)) |
        (Q(from_user=to_user) & Q(to_user=request.user))
    ).first()
    
    if not friendship:
        return Response({'error': 'User is not your friend'}, status=400)
    
    # Проверяем, что у отправителя есть элементы в этой категории
    items_count = ShoppingItem.objects.filter(user=request.user, category=category).count()
    if items_count == 0:
        return Response({'error': 'No items in this category to share'}, status=400)
    
    # Создаем или обновляем запрос на шаринг
    shared_list, created = SharedList.objects.get_or_create(
        from_user=request.user,
        to_user=to_user,
        category=category,
        defaults={'status': 'pending', 'message': message}
    )
    
    if not created:
        if shared_list.status == 'accepted':
            return Response({'error': 'List already shared and accepted'}, status=400)
        shared_list.status = 'pending'
        shared_list.message = message
        shared_list.save()
    
    serializer = SharedListSerializer(shared_list)
    return Response(serializer.data, status=201)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_shared_lists(request):
    """Получить список отправленных и полученных шарингов"""
    sent = SharedList.objects.filter(from_user=request.user)
    received = SharedList.objects.filter(to_user=request.user, status='pending')
    
    return Response({
        'sent': SharedListSerializer(sent, many=True).data,
        'received': SharedListSerializer(received, many=True).data,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def accept_shared_list(request, shared_list_id):
    """Принять шаринг списка"""
    try:
        shared_list = SharedList.objects.get(id=shared_list_id, to_user=request.user, status='pending')
    except SharedList.DoesNotExist:
        return Response({'error': 'Shared list not found'}, status=404)
    
    # Копируем элементы из списка отправителя в список получателя
    source_items = ShoppingItem.objects.filter(user=shared_list.from_user, category=shared_list.category)
    
    for source_item in source_items:
        # Проверяем, не существует ли уже такой элемент
        if not ShoppingItem.objects.filter(
            user=request.user,
            name=source_item.name,
            category=source_item.category
        ).exists():
            ShoppingItem.objects.create(
                user=request.user,
                name=source_item.name,
                category=source_item.category,
                priority=source_item.priority,
                bought=False,  # Новые элементы не куплены
                order=source_item.order
            )
    
    shared_list.status = 'accepted'
    shared_list.save()
    
    serializer = SharedListSerializer(shared_list)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def reject_shared_list(request, shared_list_id):
    """Отклонить шаринг списка"""
    try:
        shared_list = SharedList.objects.get(id=shared_list_id, to_user=request.user, status='pending')
    except SharedList.DoesNotExist:
        return Response({'error': 'Shared list not found'}, status=404)
    
    shared_list.status = 'rejected'
    shared_list.save()
    
    return Response({'message': 'Shared list rejected'}, status=200)

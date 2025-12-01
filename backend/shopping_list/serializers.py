from rest_framework import serializers
from django.contrib.auth.models import User
from .models import ShoppingItem, Category, Friendship, SharedList, UserProfile


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['name', 'display_name']


class ShoppingItemSerializer(serializers.ModelSerializer):
    category = serializers.CharField(source='category.name', read_only=True)
    
    class Meta:
        model = ShoppingItem
        fields = ['name', 'category', 'bought', 'priority']
        # Не включаем 'order' в ответ, чтобы формат совпадал со старым API


class UserSerializer(serializers.ModelSerializer):
    """Сериализатор для пользователя с профилем"""
    full_name = serializers.SerializerMethodField()
    avatar_url = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'full_name', 'avatar_url']
    
    def get_full_name(self, obj):
        return obj.get_full_name() or obj.username
    
    def get_avatar_url(self, obj):
        if hasattr(obj, 'profile') and obj.profile.avatar_url:
            return obj.profile.avatar_url
        return None


class FriendshipSerializer(serializers.ModelSerializer):
    """Сериализатор для дружбы"""
    from_user = UserSerializer(read_only=True)
    to_user = UserSerializer(read_only=True)
    
    class Meta:
        model = Friendship
        fields = ['id', 'from_user', 'to_user', 'status', 'created_at']


class SharedListSerializer(serializers.ModelSerializer):
    """Сериализатор для шаринга списка"""
    from_user = UserSerializer(read_only=True)
    to_user = UserSerializer(read_only=True)
    category = CategorySerializer(read_only=True)
    
    class Meta:
        model = SharedList
        fields = ['id', 'from_user', 'to_user', 'category', 'status', 'message', 'created_at']


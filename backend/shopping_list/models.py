from django.db import models
from django.contrib.auth.models import User


class Category(models.Model):
    """Категории списков покупок"""
    name = models.CharField(max_length=50, unique=True, verbose_name='Название')
    display_name = models.CharField(max_length=100, verbose_name='Отображаемое название')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_categories', verbose_name='Создатель')
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True, verbose_name='Создано')
    
    class Meta:
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'
        ordering = ['name']
    
    def __str__(self):
        return self.display_name
    
    def is_system_category(self):
        """Проверяет, является ли категория системной (стандартной для всех)"""
        SYSTEM_CATEGORIES = ['купить', 'дом', 'работа', 'другое', 'не-забыть', 'не забыть', 'холодос', 'холодильник', 'машина']
        return self.name in SYSTEM_CATEGORIES
    
    def can_be_deleted_by(self, user):
        """Проверяет, может ли пользователь удалить эту категорию"""
        # Системные категории нельзя удалять
        if self.is_system_category():
            return False
        # Категории, созданные пользователем, можно удалять
        if self.created_by == user:
            return True
        # Если created_by не указан (старые категории), разрешаем удаление только админам
        if self.created_by is None:
            return user.is_superuser
        return False


class ShoppingItem(models.Model):
    """Элемент списка покупок"""
    PRIORITY_CHOICES = [
        (1, 'Низкий'),
        (2, 'Средний'),
        (3, 'Высокий'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='shopping_items', verbose_name='Пользователь')
    name = models.CharField(max_length=200, verbose_name='Название')
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='items', verbose_name='Категория')
    bought = models.BooleanField(default=False, verbose_name='Куплено')
    priority = models.IntegerField(choices=PRIORITY_CHOICES, default=2, verbose_name='Приоритет')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создано')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Обновлено')
    order = models.IntegerField(default=0, verbose_name='Порядок')
    
    class Meta:
        verbose_name = 'Элемент списка'
        verbose_name_plural = 'Элементы списка'
        ordering = ['order', '-priority', 'name']
        unique_together = [['user', 'name', 'category']]
        indexes = [
            models.Index(fields=['user', 'category', 'bought']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.category.display_name})"


class UserProfile(models.Model):
    """Профиль пользователя"""
    GENDER_CHOICES = [
        ('male', 'Мужской'),
        ('female', 'Женский'),
        ('other', 'Другой'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    yandex_id = models.CharField(max_length=50, unique=True, null=True, blank=True, verbose_name='Yandex ID')
    avatar_url = models.URLField(blank=True, null=True, verbose_name='URL аватара')
    date_of_birth = models.DateField(blank=True, null=True, verbose_name='Дата рождения')
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, blank=True, null=True, verbose_name='Пол')
    phone_number = models.CharField(max_length=20, blank=True, null=True, verbose_name='Номер телефона')
    
    class Meta:
        verbose_name = 'Профиль пользователя'
        verbose_name_plural = 'Профили пользователей'
    
    def __str__(self):
        return f"{self.user.username} ({self.yandex_id})"


class Friendship(models.Model):
    """Система друзей между пользователями"""
    STATUS_CHOICES = [
        ('pending', 'Ожидает подтверждения'),
        ('accepted', 'Принято'),
        ('rejected', 'Отклонено'),
    ]
    
    from_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='friendship_requests_sent', verbose_name='От пользователя')
    to_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='friendship_requests_received', verbose_name='К пользователю')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending', verbose_name='Статус')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создано')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Обновлено')
    
    class Meta:
        verbose_name = 'Дружба'
        verbose_name_plural = 'Дружбы'
        unique_together = [['from_user', 'to_user']]
        indexes = [
            models.Index(fields=['from_user', 'status']),
            models.Index(fields=['to_user', 'status']),
        ]
    
    def __str__(self):
        return f"{self.from_user.username} -> {self.to_user.username} ({self.status})"


class SharedList(models.Model):
    """Шаринг списка покупок между пользователями"""
    STATUS_CHOICES = [
        ('pending', 'Ожидает принятия'),
        ('accepted', 'Принято'),
        ('rejected', 'Отклонено'),
    ]
    
    from_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='lists_shared', verbose_name='От пользователя')
    to_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='lists_received', verbose_name='К пользователю')
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='shared_lists', verbose_name='Категория')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending', verbose_name='Статус')
    message = models.TextField(blank=True, null=True, verbose_name='Сообщение')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создано')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Обновлено')
    
    class Meta:
        verbose_name = 'Шаринг списка'
        verbose_name_plural = 'Шаринги списков'
        unique_together = [['from_user', 'to_user', 'category']]
        indexes = [
            models.Index(fields=['from_user', 'status']),
            models.Index(fields=['to_user', 'status']),
        ]
    
    def __str__(self):
        return f"{self.from_user.username} -> {self.to_user.username} ({self.category.display_name})"


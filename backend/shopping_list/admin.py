from django.contrib import admin
from django.utils.html import format_html
from .models import Category, ShoppingItem, UserProfile, Friendship, SharedList


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'display_name']
    search_fields = ['name', 'display_name']


@admin.register(ShoppingItem)
class ShoppingItemAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'category', 'bought', 'priority', 'created_at']
    list_filter = ['category', 'bought', 'priority', 'created_at']
    search_fields = ['name', 'user__username']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'created_at'


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'yandex_id', 'email', 'full_name', 'phone_number', 'gender', 'date_of_birth', 'avatar_preview']
    list_filter = ['gender', 'date_of_birth']
    search_fields = ['user__username', 'user__email', 'user__first_name', 'user__last_name', 'yandex_id', 'phone_number']
    readonly_fields = ['avatar_url', 'avatar_preview']
    fieldsets = (
        ('Основная информация', {
            'fields': ('user', 'yandex_id', 'full_name')
        }),
        ('Контактная информация', {
            'fields': ('email', 'phone_number')
        }),
        ('Аватар', {
            'fields': ('avatar_url', 'avatar_preview')
        }),
        ('Личная информация', {
            'fields': ('gender', 'date_of_birth')
        }),
    )
    
    def email(self, obj):
        return obj.user.email if obj.user else ''
    email.short_description = 'Email'
    
    def full_name(self, obj):
        if obj.user:
            full_name = obj.user.get_full_name()
            return full_name if full_name else f"{obj.user.first_name} {obj.user.last_name}".strip() or obj.user.username
        return ''
    full_name.short_description = 'ФИО'
    
    def avatar_preview(self, obj):
        if obj.avatar_url:
            return format_html('<img src="{}" style="max-width: 100px; max-height: 100px; border-radius: 50%;" />', obj.avatar_url)
        return 'Нет аватара'
    avatar_preview.short_description = 'Превью аватара'


@admin.register(Friendship)
class FriendshipAdmin(admin.ModelAdmin):
    list_display = ['from_user', 'to_user', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['from_user__username', 'to_user__username']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(SharedList)
class SharedListAdmin(admin.ModelAdmin):
    list_display = ['from_user', 'to_user', 'category', 'status', 'created_at']
    list_filter = ['status', 'category', 'created_at']
    search_fields = ['from_user__username', 'to_user__username', 'category__name']
    readonly_fields = ['created_at', 'updated_at']


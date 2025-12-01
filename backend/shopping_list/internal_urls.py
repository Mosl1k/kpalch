"""
Внутренние API endpoints для Telegram бота и Алисы (без авторизации)
"""
from django.urls import path
from . import internal_views

urlpatterns = [
    path('list', internal_views.internal_list, name='internal_list'),
    path('add', internal_views.internal_add, name='internal_add'),
    path('buy/<str:name>', internal_views.internal_buy, name='internal_buy'),
    path('delete/<str:name>', internal_views.internal_delete, name='internal_delete'),
    path('edit/<str:name>', internal_views.internal_edit, name='internal_edit'),
]


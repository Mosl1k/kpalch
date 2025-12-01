from django.urls import path
from . import views

# URL для API endpoints (используются через path('api/', include('shopping_list.api_urls')) в gestalt/urls.py)
urlpatterns = [
    path('list', views.list_items, name='list'),
    path('category/add', views.add_category, name='add_category'),
    path('category/delete/<str:category_name>', views.delete_category, name='delete_category'),
    path('add', views.add_item, name='add'),
    path('buy/<str:name>', views.buy_item, name='buy'),
    path('delete/<str:name>', views.delete_item, name='delete'),
    path('edit/<str:name>', views.edit_item, name='edit'),
    path('reorder', views.reorder_items, name='reorder'),
    # API для пользователя
    path('user', views.get_current_user, name='get_current_user'),
    # API для друзей
    path('users', views.list_users, name='list_users'),
    path('friends', views.list_friends, name='list_friends'),
    path('friend-requests', views.list_friend_requests, name='list_friend_requests'),
    path('friend-request', views.send_friend_request, name='send_friend_request'),
    path('friend-request/<int:friendship_id>/accept', views.accept_friend_request, name='accept_friend_request'),
    path('friend-request/<int:friendship_id>/reject', views.reject_friend_request, name='reject_friend_request'),
    path('friend/<int:friendship_id>', views.remove_friend, name='remove_friend'),
    path('friend/remove', views.remove_friend_by_user, name='remove_friend_by_user'),
    # API для шаринга списков
    path('share-list', views.share_list, name='share_list'),
    path('shared-lists', views.list_shared_lists, name='list_shared_lists'),
    path('shared-list/<int:shared_list_id>/accept', views.accept_shared_list, name='accept_shared_list'),
    path('shared-list/<int:shared_list_id>/reject', views.reject_shared_list, name='reject_shared_list'),
]


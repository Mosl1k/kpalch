from django.urls import path
from . import views

# URL для страниц (используются через path('', include(...)) в gestalt/urls.py)
urlpatterns = [
    path('', views.index, name='index'),
    path('friends', views.friends, name='friends'),
    path('register', views.register, name='register'),
]


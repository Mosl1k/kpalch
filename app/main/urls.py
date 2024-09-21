from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='home'),
    path('about', views.about, name='about'),
    path('create', views.create, name='create'),
    path('geshtalt', views.geshtalt, name='geshtalt'),
    path('node-status', views.get_nodes_status, name='node_status'),
]

from django.shortcuts import render, redirect
from .models import Task
from .forms import TaskForm
from kubernetes import client, config
# from bs4 import BeautifulSoup
# import requests
# import subprocess, sys

def index(request):
    tasks = Task.objects.order_by('-id')
    return render(request, 'main/index.html', {'title': 'Главная страница', 'tasks': tasks})


def about(request):
    # Подключение через config, который находится внутри контейнера
    config.load_incluster_config()

    v1 = client.CoreV1Api()
    nodes = v1.list_node()

    node_status = []
    for node in nodes.items:
        status = {
            "name": node.metadata.name,
            "status": node.status.conditions[-1].type,
            "addresses": [addr.address for addr in node.status.addresses if addr.type == "InternalIP"],
            "ready": any(
                condition.type == "Ready" and condition.status == "True" for condition in node.status.conditions),
        }
        node_status.append(status)

    # Передаем данные о нодах в шаблон
    return render(request, 'main/about.html', {'node_status': node_status})


def create(request):
    error = ''
    if request.method == 'POST':
        form = TaskForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('home')
        else:
            error = 'Форма была неверной'

    form = TaskForm()
    context = {
        'form': form,
        'error': error
    }
    return render(request, 'main/create.html', context)

def geshtalt(request):
    return render(request, 'main/geshtalt.html')

# def rub():
#     url = 'https://www.calc.ru/Bitcoin-k-rublyu-online.html'
#     page = requests.get(url)
#     news = []
#     new_news = []
#     soup = BeautifulSoup(page.text, "html.parser")
#     news = soup.findAll(class_='t18', style="font-size: 24px;")
#     for tag in soup.find_all(class_='t18'):
#         bt = tag.text[0:21]
#     return (bt)

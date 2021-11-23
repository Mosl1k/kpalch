from django.shortcuts import render, redirect
from .models import Task
from .forms import TaskForm
from bs4 import BeautifulSoup
import requests
import subprocess, sys

def index(request):
    tasks = Task.objects.order_by('-id')
    return render(request, 'main/index.html', {'title': 'Главная страница', 'tasks': tasks})


def about(request):
    subprocess.Popen(['kill', '-9', 'run.py']) 
    subprocess.Popen(['python3', 'run.py'])
    return render(request, 'main/about.html', {'bt': rub})


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

def rub():
    url = 'https://www.calc.ru/Bitcoin-k-rublyu-online.html'
    page = requests.get(url)
    news = []
    new_news = []
    soup = BeautifulSoup(page.text, "html.parser")
    news = soup.findAll(class_='t18', style="font-size: 24px;")
    for tag in soup.find_all(class_='t18'):
        bt = tag.text[0:21]
    return (bt)

from jinja2 import Environment, FileSystemLoader
from django.conf import settings
from django.contrib.staticfiles.storage import staticfiles_storage
from django.urls import reverse
from pathlib import Path


def environment(**options):
    # Убеждаемся, что загрузчик настроен правильно
    if 'loader' not in options:
        base_dir = Path(settings.BASE_DIR)
        templates_dir = base_dir / 'templates'
        options['loader'] = FileSystemLoader(str(templates_dir))
    
    env = Environment(**options)
    env.globals.update({
        'static': staticfiles_storage.url,
        'url': reverse,
    })
    return env


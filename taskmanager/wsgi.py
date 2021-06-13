"""
WSGI config for taskmanager project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/3.2/howto/deployment/wsgi/
"""
import os

from django.core.wsgi import get_wsgi_application
# os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'taskmanager.settings')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'taskmanager.settings')
application = get_wsgi_application()
# path = '/home/technewsandblog/blog/blog_project/mysite'
# if path not in sys.path:
# sys.path.append(path)

# os.environ['DJANGO_SETTINGS_MODULE'] = 'taskmanager.settings'

# then:

# from django.core.wsgi import get_wsgi_application

# application = get_wsgi_application()

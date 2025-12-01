"""
WSGI config for gestalt project.
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gestalt.settings')

application = get_wsgi_application()


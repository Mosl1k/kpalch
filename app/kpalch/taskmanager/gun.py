# command = 'gunicorn'
# pythonpath = '/home/hostgeek/myapps/parser/siteparser'
bind = '0.0.0.0:8000'
workers = 3
user = 'moslik'
limit_request_fields = 32000
limit_request_field_size = 0
raw_env = 'DJANGO_SETTINGS_MODULE=taskmanager.settings'

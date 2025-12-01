"""
Команда для миграции данных из Redis в PostgreSQL
"""
import json
import redis
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from shopping_list.models import Category, ShoppingItem, UserProfile


class Command(BaseCommand):
    help = 'Мигрирует данные из Redis в PostgreSQL'

    def add_arguments(self, parser):
        parser.add_argument('--redis-host', type=str, default='redis', help='Redis host')
        parser.add_argument('--redis-port', type=int, default=6379, help='Redis port')
        parser.add_argument('--redis-password', type=str, default=None, help='Redis password (optional)')
        parser.add_argument('--service-user-ids', type=str, help='Comma-separated list of service user IDs')

    def handle(self, *args, **options):
        redis_host = options['redis_host']
        redis_port = options['redis_port']
        redis_password = options.get('redis_password')
        service_user_ids = options.get('service_user_ids', '').split(',') if options.get('service_user_ids') else []

        # Подключаемся к Redis (password передаем только если указан)
        redis_kwargs = {
            'host': redis_host,
            'port': redis_port,
            'decode_responses': False
        }
        if redis_password:
            redis_kwargs['password'] = redis_password
        
        r = redis.Redis(**redis_kwargs)

        self.stdout.write('Подключение к Redis...')
        
        # Создаем категории
        categories_data = {
            'купить': 'Купить',
            'не-забыть': 'Не забыть',
            'дом': 'Дом',
            'машина': 'Машина',
            'холодос': 'Холодильник',
        }
        
        for cat_name, cat_display in categories_data.items():
            Category.objects.get_or_create(
                name=cat_name,
                defaults={'display_name': cat_display}
            )
            self.stdout.write(f'Категория "{cat_display}" создана/найдена')

        # Получаем все ключи shoppingList
        keys = r.keys('shoppingList:*')
        self.stdout.write(f'Найдено {len(keys)} ключей в Redis')
        self.stdout.write(f'Тип keys: {type(keys)}')
        self.stdout.write(f'Keys: {keys}')
        
        if len(keys) == 0:
            self.stdout.write(self.style.WARNING('Ключи не найдены!'))
            return

        migrated_count = 0
        
        for i, key in enumerate(keys):
            self.stdout.write(f'Итерация {i+1}/{len(keys)}: Начало обработки ключа: {key} (тип: {type(key)})')
            try:
                key_str = key.decode('utf-8') if isinstance(key, bytes) else key
                self.stdout.write(f'Обработка ключа: {key_str}')
                
                # Формат может быть: shoppingList:user_id:category или shoppingList:category
                parts = key_str.split(':')
                
                if len(parts) == 3:
                    # Новый формат: shoppingList:user_id:category
                    user_id_str = parts[1]
                    category_name = parts[2]
                    self.stdout.write(f'  Формат: новый (user_id={user_id_str}, category={category_name})')
                elif len(parts) == 2:
                    # Старый формат: shoppingList:category (без user_id)
                    category_name = parts[1]
                    # Используем первого service user или создаем дефолтного
                    if service_user_ids and len(service_user_ids) > 0:
                        user_id_str = service_user_ids[0].strip()
                        self.stdout.write(f'  Формат: старый, используется пользователь {user_id_str} для категории {category_name}')
                    else:
                        user_id_str = '77415476'  # Дефолтный пользователь
                        self.stdout.write(self.style.WARNING(f'  Формат: старый, используется дефолтный пользователь {user_id_str} для категории {category_name}'))
                else:
                    self.stdout.write(self.style.WARNING(f'  Неизвестный формат ключа: {key_str} (частей: {len(parts)}), пропускаем'))
                    continue
                
                # Получаем или создаем пользователя
                user, created = User.objects.get_or_create(
                    username=user_id_str,
                    defaults={
                        'email': f'{user_id_str}@gestalt.local',
                        'first_name': f'User {user_id_str}',
                    }
                )
                if created:
                    self.stdout.write(f'Создан пользователь: {user_id_str}')
                
                # Создаем профиль пользователя
                profile, _ = UserProfile.objects.get_or_create(
                    user=user,
                    defaults={'yandex_id': user_id_str}
                )
                
                # Получаем категорию
                try:
                    category = Category.objects.get(name=category_name)
                except Category.DoesNotExist:
                    self.stdout.write(self.style.WARNING(f'Категория {category_name} не найдена, пропускаем'))
                    continue
                
                # Получаем данные из Redis
                data = r.get(key)
                if not data:
                    self.stdout.write(self.style.WARNING(f'Пустые данные для ключа {key_str}'))
                    continue
                
                # Декодируем bytes в строку, если нужно
                if isinstance(data, bytes):
                    data_str = data.decode('utf-8')
                else:
                    data_str = data
                
                try:
                    items = json.loads(data_str)
                except json.JSONDecodeError as e:
                    self.stdout.write(self.style.ERROR(f'Ошибка парсинга JSON для {key_str}: {e}'))
                    continue
                
                if not isinstance(items, list):
                    self.stdout.write(self.style.WARNING(f'Данные для {key_str} не являются списком: {type(items)}'))
                    continue
                
                self.stdout.write(f'Обработка {len(items)} элементов для {user_id_str}:{category_name}')
                
                if len(items) == 0:
                    self.stdout.write(self.style.WARNING(f'Пустой список для {key_str}'))
                    continue
                
                # Мигрируем элементы
                for index, item_data in enumerate(items):
                    if not isinstance(item_data, dict):
                        self.stdout.write(self.style.WARNING(f'Пропущен элемент {index}: не является словарем'))
                        continue
                    
                    # Обрабатываем name с поддержкой пустых значений
                    item_name = item_data.get('name') or item_data.get('Name') or ''
                    if isinstance(item_name, str):
                        item_name = item_name.strip()
                    else:
                        item_name = str(item_name).strip() if item_name is not None else ''
                    
                    # Пропускаем пустые имена
                    if not item_name:
                        self.stdout.write(self.style.WARNING(f'Пропущен элемент {index}: пустое имя'))
                        continue
                    
                    # Обрабатываем bought с поддержкой None
                    bought = item_data.get('bought', False)
                    if bought is None:
                        bought = False
                    
                    # Обрабатываем priority с поддержкой None и пустых значений
                    priority = item_data.get('priority', 2)
                    if priority is None:
                        priority = 2
                    try:
                        priority = int(priority)
                    except (ValueError, TypeError):
                        priority = 2
                    
                    # Обрабатываем order (используем index если не указан)
                    order = item_data.get('order', index)
                    if order is None:
                        order = index
                    try:
                        order = int(order)
                    except (ValueError, TypeError):
                        order = index
                    
                    ShoppingItem.objects.update_or_create(
                        user=user,
                        name=item_name,
                        category=category,
                        defaults={
                            'bought': bool(bought),
                            'priority': priority,
                            'order': order,
                        }
                    )
                    migrated_count += 1
                
                self.stdout.write(f'Мигрировано {len(items)} элементов для {user_id_str}:{category_name}')
                
            except Exception as e:
                import traceback
                self.stdout.write(self.style.ERROR(f'Ошибка при обработке ключа {key}: {e}'))
                self.stdout.write(self.style.ERROR(f'Traceback: {traceback.format_exc()}'))
                continue

        self.stdout.write(self.style.SUCCESS(f'Миграция завершена. Мигрировано элементов: {migrated_count}'))


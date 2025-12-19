import os
import json
import base64
import requests
from datetime import datetime
from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters
import logging
import g4f  # Импортируем g4f для предложения блюд

# Настройка логирования
# В Docker логи должны идти в stdout/stderr для docker-compose logs
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()  # Вывод в stdout/stderr для Docker
    ]
)

# Уменьшаем уровень логирования для httpx и urllib3 (HTTP клиенты)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

# Загружаем переменные из .env (только для локальной разработки)
# В Kubernetes/Docker переменные передаются через Secrets/ConfigMaps
if not os.getenv("KUBERNETES_SERVICE_HOST"):
    load_dotenv(override=False)  # override=False - не перезаписывать существующие переменные окружения

# Конфигурация из переменных окружения
# В Docker переменные передаются через env_file, в локальной разработке - через .env
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
API_URL = os.getenv("API_URL", "http://geshtalt:8080/internal/api")
SERVICE_USER_ID = os.getenv("SERVICE_USER_ID", "")
SERVICE_USER_IDS = os.getenv("SERVICE_USER_IDS", "")

# Категории для списков
LISTS = {
    "купить": "Покупки",
    "не-забыть": "Не забыть",
    "холодос": "Холодильник",
    "дом": "Дом",
    "машина": "Машина"
}

# Эмодзи для приоритетов
PRIORITY_EMOJI = {
    3: "🔥",  # Высокий
    2: "🟡",  # Средний
    1: "🟢"   # Низкий
}

# Порядок категорий для переключения
CATEGORIES = list(LISTS.keys())

def get_main_keyboard():
    """Возвращает основную клавиатуру с категориями и кнопкой 'Что приготовить'."""
    keyboard = [
        [InlineKeyboardButton(name, callback_data=f"list:{key}")]
        for key, name in LISTS.items()
    ]
    keyboard.append([InlineKeyboardButton("Что приготовить 🍳", callback_data="suggest_dishes")])
    keyboard.append([InlineKeyboardButton("Рестарт", callback_data="restart")])
    return InlineKeyboardMarkup(keyboard)

def get_list_keyboard(current_category):
    """Возвращает клавиатуру для списка с кнопками Назад, Предыдущий, Следующий и Добавить."""
    current_index = CATEGORIES.index(current_category)
    prev_category = CATEGORIES[(current_index - 1) % len(CATEGORIES)]
    next_category = CATEGORIES[(current_index + 1) % len(CATEGORIES)]

    keyboard = [
        [InlineKeyboardButton("🔙 Назад", callback_data=f"back:{current_category}")],
        [
            InlineKeyboardButton("⬅️ Предыдущий", callback_data=f"list:{prev_category}"),
            InlineKeyboardButton("Следующий ➡️", callback_data=f"list:{next_category}")
        ],
        [InlineKeyboardButton("➕ Добавить", callback_data=f"add:{current_category}")]
    ]
    return InlineKeyboardMarkup(keyboard)

def encode_item_name(item_name):
    """Кодирует имя элемента в base64 для безопасной передачи в callback_data."""
    return base64.urlsafe_b64encode(item_name.encode('utf-8')).decode('ascii')

def decode_item_name(encoded_name):
    """Декодирует имя элемента из base64."""
    try:
        return base64.urlsafe_b64decode(encoded_name.encode('ascii')).decode('utf-8')
    except Exception as e:
        logging.error(f"Ошибка декодирования имени элемента: {e}")
        return ""

def get_service_headers():
    """Возвращает заголовки для API запросов с правильным X-User-ID"""
    headers = {}
    logger = logging.getLogger(__name__)
    # Если SERVICE_USER_IDS установлен, берем первого пользователя (для обратной совместимости с одним пользователем API ожидает один заголовок)
    if SERVICE_USER_IDS:
        first_user = SERVICE_USER_IDS.split(',')[0].strip()
        if first_user:
            headers["X-User-ID"] = first_user
            logger.debug(f"Using SERVICE_USER_IDS: {first_user} from {SERVICE_USER_IDS}")
    elif SERVICE_USER_ID:
        headers["X-User-ID"] = SERVICE_USER_ID
        logger.debug(f"Using SERVICE_USER_ID: {SERVICE_USER_ID}")
    else:
        logger.warning("SERVICE_USER_ID and SERVICE_USER_IDS are not set! API requests may fail.")
    return headers

def get_item_actions_keyboard(item_name, category):
    """Возвращает клавиатуру для действий с элементом."""
    encoded_name = encode_item_name(item_name)
    keyboard = []
    
    # Для категории "купить" добавляем кнопку "Отправить в холодильник"
    if category == "купить":
        keyboard.append([InlineKeyboardButton("❄️ Отправить в холодильник", callback_data=f"item_action:send_to_fridge:{encoded_name}:{category}")])
    
    keyboard.extend([
        [InlineKeyboardButton("Удалить", callback_data=f"item_action:delete:{encoded_name}:{category}")],
        [InlineKeyboardButton("Сменить категорию", callback_data=f"item_action:change_cat:{encoded_name}:{category}")],
        [InlineKeyboardButton("Сменить приоритет", callback_data=f"item_action:change_pri:{encoded_name}:{category}")],
        [InlineKeyboardButton("Назад", callback_data=f"list:{category}")]
    ])
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context):
    """Обработчик команды /start. Показывает основную клавиатуру."""
    reply_markup = get_main_keyboard()
    if update.message:
        await update.message.reply_text("Выберите категорию:", reply_markup=reply_markup)
    elif update.callback_query:
        try:
            await update.callback_query.message.edit_text("Выберите категорию:", reply_markup=reply_markup)
        except Exception:
            # Если не удалось отредактировать, отправляем новое сообщение
            await update.callback_query.message.reply_text("Выберите категорию:", reply_markup=reply_markup)

async def add_start(update: Update, context):
    """Обработчик кнопки Добавить. Запрашивает текст элемента."""
    query = update.callback_query
    await query.answer()
    data = query.data
    category = data.split(":")[1] if data.startswith("add:") else None
    context.user_data["awaiting_item"] = True
    context.user_data["category"] = category
    await query.message.reply_text(
        f"Введите название элемента для добавления в {LISTS[category]}:"
    )

async def handle_item_text(update: Update, context):
    """Обработчик ввода текста элемента."""
    if not context.user_data.get("awaiting_item"):
        return

    item_name = update.message.text
    context.user_data["item_name"] = item_name
    context.user_data["awaiting_item"] = False

    if context.user_data.get("category"):
        await add_to_category(update, context)
    else:
        context.user_data["awaiting_category"] = True
        keyboard = [
            [InlineKeyboardButton(name, callback_data=f"add_to:{key}")]
            for key, name in LISTS.items()
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(f"Куда добавить '{item_name}'?", reply_markup=reply_markup)

async def add_to_category(update: Update, context):
    """Обработчик выбора категории для добавления."""
    category = context.user_data.get("category")
    if not category:
        query = update.callback_query
        await query.answer()
        data = query.data
        if not data.startswith("add_to:"):
            return
        category = data.split(":")[1]

    if category not in LISTS:
        await update.message.reply_text(f"Неизвестная категория: {category}")
        return

    item_name = context.user_data.get("item_name")
    context.user_data["awaiting_category"] = False
    context.user_data.pop("item_name", None)
    context.user_data.pop("category", None)

    try:
        headers = {"Content-Type": "application/json"}
        headers.update(get_service_headers())

        data = {
            "name": item_name,
            "category": category,
            "bought": False,
            "priority": 2
        }

        response = requests.post(f"{API_URL}/add", headers=headers, json=data)
        if response.status_code != 201:
            error_msg = f"Ошибка добавления: {response.status_code} - {response.text}"
            logging.error(error_msg)
            await update.message.reply_text(error_msg)
            return

        reply_markup = get_list_keyboard(category)
        await update.message.reply_text(f"Добавлено '{item_name}' в {LISTS[category]}", reply_markup=reply_markup)
    except requests.RequestException as e:
        error_msg = f"Ошибка подключения к API: {e}"
        logging.error(error_msg)
        await update.message.reply_text(error_msg)
    except Exception as e:
        error_msg = f"Произошла ошибка: {str(e)}"
        logging.error(error_msg)
        await update.message.reply_text(error_msg)

async def show_item_actions(update: Update, context):
    """Показывает действия для выбранного элемента."""
    query = update.callback_query
    await query.answer()

    data = query.data
    if not data.startswith("item:"):
        return

    # Разбираем callback_data: item:encoded_name:category
    parts = data.split(":", 2)
    if len(parts) < 3:
        logging.error(f"Неверный формат callback_data: {data}")
        await query.message.reply_text("Ошибка: неверный формат данных")
        return
    
    encoded_name = parts[1]
    category = parts[2]
    item_name = decode_item_name(encoded_name)
    
    if not item_name:
        logging.error(f"Не удалось декодировать имя элемента из: {encoded_name}")
        await query.message.reply_text("Ошибка: не удалось декодировать данные")
        return
    
    context.user_data["item_name"] = item_name
    context.user_data["category"] = category

    reply_markup = get_item_actions_keyboard(item_name, category)
    await query.message.reply_text(f"Что сделать с '{item_name}' в {LISTS[category]}?", reply_markup=reply_markup)

async def handle_item_action(update: Update, context):
    """Обработчик действий с элементом."""
    query = update.callback_query
    await query.answer()

    data = query.data
    if not data.startswith("item_action:"):
        return

    # Разбираем callback_data: item_action:action:encoded_name:category
    parts = data.split(":", 3)
    if len(parts) < 4:
        logging.error(f"Неверный формат callback_data: {data}")
        await query.message.reply_text("Ошибка: неверный формат данных")
        return
    
    action = parts[1]
    encoded_name = parts[2]
    category = parts[3]
    item_name = decode_item_name(encoded_name)
    
    if not item_name:
        logging.error(f"Не удалось декодировать имя элемента из: {encoded_name}")
        await query.message.reply_text("Ошибка: не удалось декодировать данные")
        return
    
    context.user_data["item_name"] = item_name
    context.user_data["category"] = category

    if action == "delete":
        try:
            headers = {}
            if SERVICE_USER_ID:
                headers["X-User-ID"] = SERVICE_USER_ID

            response = requests.delete(f"{API_URL}/delete/{item_name}?category={category}", headers=headers)
            if response.status_code != 200:
                error_msg = f"Ошибка удаления: {response.status_code} - {response.text}"
                logging.error(error_msg)
                await query.message.reply_text(error_msg)
                return

            reply_markup = get_list_keyboard(category)
            await query.message.reply_text(f"Удалено '{item_name}' из {LISTS[category]}", reply_markup=reply_markup)
        except requests.RequestException as e:
            error_msg = f"Ошибка подключения к API: {e}"
            logging.error(error_msg)
            await query.message.reply_text(error_msg)
        except Exception as e:
            error_msg = f"Произошла ошибка: {str(e)}"
            logging.error(error_msg)
            await query.message.reply_text(error_msg)
    elif action == "change_cat":
        context.user_data["awaiting_new_category"] = True
        keyboard = [
            [InlineKeyboardButton(name, callback_data=f"change_cat_to:{key}")]
            for key, name in LISTS.items() if key != category
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text(f"В какую категорию перенести '{item_name}'?", reply_markup=reply_markup)
    elif action == "change_pri":
        context.user_data["awaiting_priority"] = True
        keyboard = [
            [InlineKeyboardButton(f"Высокий {PRIORITY_EMOJI[3]}", callback_data="pri:3")],
            [InlineKeyboardButton(f"Средний {PRIORITY_EMOJI[2]}", callback_data="pri:2")],
            [InlineKeyboardButton(f"Низкий {PRIORITY_EMOJI[1]}", callback_data="pri:1")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text(f"Выберите новый приоритет для '{item_name}' в {LISTS[category]}:", reply_markup=reply_markup)
    elif action == "send_to_fridge":
        # Отправка элемента из "купить" в "холодос" с добавлением даты
        if category != "купить":
            await query.message.reply_text("Эта функция доступна только для элементов из списка покупок")
            return
        
        try:
            headers = {"Content-Type": "application/json"}
            if SERVICE_USER_ID:
                headers["X-User-ID"] = SERVICE_USER_ID

            # Получаем элемент из категории "купить"
            response = requests.get(f"{API_URL}/list?category=купить", headers=headers)
            if response.status_code != 200:
                error_msg = f"Ошибка получения данных: {response.status_code} - {response.text}"
                logging.error(error_msg)
                await query.message.reply_text(error_msg)
                return

            try:
                items = response.json()
            except json.JSONDecodeError as e:
                error_msg = f"Ошибка парсинга JSON: {e}. Ответ: {response.text[:200]}"
                logging.error(error_msg)
                await query.message.reply_text(f"Ошибка подключения к API: {e}")
                return
            
            item = next((i for i in items if i["name"] == item_name), None)
            if not item:
                await query.message.reply_text(f"Элемент '{item_name}' не найден в {LISTS[category]}")
                return

            # Формируем новое имя с датой (формат: название (01.12.2025))
            current_date = datetime.now().strftime("%d.%m.%Y")
            new_item_name = f"{item_name} ({current_date})"
            
            # Создаем элемент в категории "холодос"
            new_item_data = {
                "name": new_item_name,
                "category": "холодос",
                "bought": False,
                "priority": item.get("priority", 2)
            }
            
            response = requests.post(f"{API_URL}/add", headers=headers, json=new_item_data)
            if response.status_code not in [200, 201]:
                error_msg = f"Ошибка добавления в холодильник: {response.status_code} - {response.text}"
                logging.error(error_msg)
                await query.message.reply_text(error_msg)
                return

            # Удаляем элемент из категории "купить"
            response = requests.delete(f"{API_URL}/delete/{item_name}?category=купить", headers=headers)
            if response.status_code != 200:
                error_msg = f"Ошибка удаления из покупок: {response.status_code} - {response.text}"
                logging.error(error_msg)
                await query.message.reply_text(error_msg)
                return

            reply_markup = get_list_keyboard("холодос")
            await query.message.reply_text(
                f"✅ '{item_name}' отправлен в холодильник с датой {current_date}",
                reply_markup=reply_markup
            )
        except requests.RequestException as e:
            error_msg = f"Ошибка подключения к API: {e}"
            logging.error(error_msg)
            await query.message.reply_text(error_msg)
        except Exception as e:
            error_msg = f"Произошла ошибка: {str(e)}"
            logging.error(error_msg)
            await query.message.reply_text(error_msg)

async def change_category_to(update: Update, context):
    """Обработчик выбора новой категории."""
    query = update.callback_query
    await query.answer()

    if not context.user_data.get("awaiting_new_category"):
        return

    data = query.data
    if not data.startswith("change_cat_to:"):
        return

    new_category = data.split(":")[1]
    if new_category not in LISTS:
        await query.message.reply_text(f"Неизвестная категория: {new_category}")
        return

    item_name = context.user_data.get("item_name")
    old_category = context.user_data.get("category")
    context.user_data["awaiting_new_category"] = False
    context.user_data.pop("item_name", None)
    context.user_data.pop("category", None)

    try:
        headers = {"Content-Type": "application/json"}
        if SERVICE_USER_ID:
            headers["X-User-ID"] = SERVICE_USER_ID

        response = requests.get(f"{API_URL}/list?category={old_category}", headers=headers)
        if response.status_code != 200:
            error_msg = f"Ошибка получения данных: {response.status_code} - {response.text}"
            logging.error(error_msg)
            await query.message.reply_text(error_msg)
            return

        try:
            items = response.json()
        except json.JSONDecodeError as e:
            error_msg = f"Ошибка парсинга JSON: {e}. Ответ: {response.text[:200]}"
            logging.error(error_msg)
            await query.message.reply_text(f"Ошибка подключения к API: {e}")
            return
        item = next((i for i in items if i["name"] == item_name), None)
        if not item:
            await query.message.reply_text(f"Элемент '{item_name}' не найден в {LISTS[old_category]}")
            return

        data = {
            "name": item_name,
            "category": new_category,
            "bought": item["bought"],
            "priority": item["priority"]
        }

        response = requests.put(f"{API_URL}/edit/{item_name}?oldCategory={old_category}", headers=headers, json=data)
        if response.status_code != 200:
            error_msg = f"Ошибка смены категории: {response.status_code} - {response.text}"
            logging.error(error_msg)
            await query.message.reply_text(error_msg)
            return

        reply_markup = get_list_keyboard(new_category)
        await query.message.reply_text(f"Элемент '{item_name}' перенесен из {LISTS[old_category]} в {LISTS[new_category]}", reply_markup=reply_markup)
    except requests.RequestException as e:
        error_msg = f"Ошибка подключения к API: {e}"
        logging.error(error_msg)
        await query.message.reply_text(error_msg)
    except Exception as e:
        error_msg = f"Произошла ошибка: {str(e)}"
        logging.error(error_msg)
        await query.message.reply_text(error_msg)

async def change_priority_to(update: Update, context):
    """Обработчик выбора нового приоритета."""
    query = update.callback_query
    await query.answer()

    if not context.user_data.get("awaiting_priority"):
        return

    data = query.data
    if not data.startswith("pri:"):
        return

    new_priority = int(data.split(":")[1])
    item_name = context.user_data.get("item_name")
    category = context.user_data.get("category")
    context.user_data["awaiting_priority"] = False
    context.user_data.pop("item_name", None)
    context.user_data.pop("category", None)

    try:
        headers = {"Content-Type": "application/json"}
        headers.update(get_service_headers())

        response = requests.get(f"{API_URL}/list?category={category}", headers=headers)
        if response.status_code != 200:
            error_msg = f"Ошибка получения данных: {response.status_code} - {response.text}"
            logging.error(error_msg)
            await query.message.reply_text(error_msg)
            return

        try:
            items = response.json()
        except json.JSONDecodeError as e:
            error_msg = f"Ошибка парсинга JSON: {e}. Ответ: {response.text[:200]}"
            logging.error(error_msg)
            await query.message.reply_text(f"Ошибка подключения к API: {e}")
            return
        item = next((i for i in items if i["name"] == item_name), None)
        if not item:
            await query.message.reply_text(f"Элемент '{item_name}' не найден в {LISTS[category]}")
            return

        data = {
            "name": item_name,
            "category": category,
            "bought": item["bought"],
            "priority": new_priority
        }

        response = requests.put(f"{API_URL}/edit/{item_name}?oldCategory={category}", headers=headers, json=data)
        if response.status_code != 200:
            error_msg = f"Ошибка смены приоритета: {response.status_code} - {response.text}"
            logging.error(error_msg)
            await query.message.reply_text(error_msg)
            return

        reply_markup = get_list_keyboard(category)
        await query.message.reply_text(f"Приоритет для '{item_name}' в {LISTS[category]} изменен на {PRIORITY_EMOJI[new_priority]}", reply_markup=reply_markup)
    except requests.RequestException as e:
        error_msg = f"Ошибка подключения к API: {e}"
        logging.error(error_msg)
        await query.message.reply_text(error_msg)
    except Exception as e:
        error_msg = f"Произошла ошибка: {str(e)}"
        logging.error(error_msg)
        await query.message.reply_text(error_msg)

async def suggest_dishes(update: Update, context):
    """Обработчик кнопки 'Что приготовить'. Предлагает блюда на основе содержимого холодильника."""
    query = update.callback_query
    await query.answer()

    try:
        headers = get_service_headers()

        response = requests.get(f"{API_URL}/list?category=холодос", headers=headers)
        if response.status_code != 200:
            error_msg = f"Ошибка получения данных: {response.status_code} - {response.text}"
            logging.error(error_msg)
            await query.message.reply_text(error_msg)
            return

        try:
            items = response.json()
        except json.JSONDecodeError as e:
            error_msg = f"Ошибка парсинга JSON: {e}. Ответ: {response.text[:200]}"
            logging.error(error_msg)
            await query.message.reply_text(f"Ошибка подключения к API: {e}")
            return
        items_in_fridge = [item['name'] for item in items if item.get('category', '').lower() == 'холодос' and item['name'].strip()]
        
        if not items_in_fridge:
            reply_markup = get_main_keyboard()
            await query.message.reply_text("В холодильнике пусто, нечего приготовить.", reply_markup=reply_markup)
            return

        prompt = f"Что можно приготовить из таких продуктов: {', '.join(items_in_fridge)}? Назови только 10 названий блюд. Желательно из русской, татарской, грузинской, итальянской, вьетнамской, узбекской, японской кухонь. Пример: лагман, манты, хинкали, мясо по-французски, очпочмак, шаурма, бургер, пицца, борщ, солянка, курица во фритюре, на мангале, на пару. Не повторяй, что я сказал, из этого списка - только как пример,от силы 1 повторенье."
        try:
            response_from_gpt = g4f.ChatCompletion.create(model='gpt-4', messages=[{"role": "user", "content": prompt}])
            response_text = f"{response_from_gpt}"
            reply_markup = get_main_keyboard()  # Возвращаемся в главное меню
            await query.message.reply_text(response_text, reply_markup=reply_markup)
        except Exception as e:
            error_msg = f"Ошибка при обращении к GPT: {e}"
            logging.error(error_msg)
            await query.message.reply_text("Извините, произошла ошибка при запросе рецепта.", reply_markup=get_main_keyboard())
    except requests.RequestException as e:
        error_msg = f"Ошибка подключения к API: {e}"
        logging.error(error_msg)
        await query.message.reply_text(error_msg, reply_markup=get_main_keyboard())
    except Exception as e:
        error_msg = f"Произошла ошибка: {str(e)}"
        logging.error(error_msg)
        await query.message.reply_text(error_msg, reply_markup=get_main_keyboard())

async def button_callback(update: Update, context):
    """Обработчик нажатий на кнопки."""
    query = update.callback_query
    await query.answer()

    data = query.data
    if data == "restart":
        await start(update, context)
        return
    if data == "suggest_dishes":
        await suggest_dishes(update, context)
        return
    if data.startswith("add:"):
        await add_start(update, context)
        return
    if data.startswith("add_to:"):
        await add_to_category(update, context)
        return
    if data.startswith("item:"):
        await show_item_actions(update, context)
        return
    if data.startswith("item_idx:"):
        # Обработка callback_data с индексом элемента (для длинных имен)
        parts = data.split(":", 2)
        if len(parts) >= 3:
            item_index = int(parts[1])
            category = parts[2]
            item_key = f"{category}:{item_index}"
            item_name = context.user_data.get('item_indices', {}).get(item_key)
            if item_name:
                encoded_name = encode_item_name(item_name)
                # Создаем временный callback_data для show_item_actions
                query.data = f"item:{encoded_name}:{category}"
                await show_item_actions(update, context)
            else:
                await query.message.reply_text("Ошибка: элемент не найден")
        return
    if data.startswith("item_action:"):
        await handle_item_action(update, context)
        return
    if data.startswith("change_cat_to:"):
        await change_category_to(update, context)
        return
    if data.startswith("pri:"):
        await change_priority_to(update, context)
        return
    if data.startswith("back:"):
        # Кнопка "Назад" возвращает в главное меню
        await start(update, context)
        return
    if data.startswith("list:"):
        list_type = data.split(":")[1]
        await show_list(update, context, list_type)
        return

async def show_list(update: Update, context, list_type):
    """Показывает содержимое указанного списка."""
    if list_type not in LISTS:
        if update.callback_query:
            await update.callback_query.message.reply_text(f"Неизвестная категория: {list_type}")
        return

    try:
        headers = get_service_headers()

        url = f"{API_URL}/list?category={list_type}"
        logger = logging.getLogger(__name__)
        logger.info(f"[TELEGRAM BOT] Запрос списка: category={list_type}, headers={headers}, url={url}")
        
        response = requests.get(url, headers=headers)
        logger.info(f"[TELEGRAM BOT] Ответ API: status={response.status_code}, text_length={len(response.text)}, text_preview={response.text[:200]}")
        
        if response.status_code != 200:
            error_msg = f"Ошибка API: {response.status_code} - {response.text}"
            logger.error(f"[TELEGRAM BOT] {error_msg}")
            if update.callback_query:
                await update.callback_query.message.reply_text(error_msg)
            return

        # Проверяем, что ответ не пустой и является JSON
        if not response.text or response.text.strip() == "":
            error_msg = "Пустой ответ от API"
            logger.error(f"[TELEGRAM BOT] {error_msg}")
            if update.callback_query:
                await update.callback_query.message.reply_text(error_msg)
            return

        try:
            items = response.json()
            logger.info(f"[TELEGRAM BOT] Распарсено элементов: {len(items) if items else 0}")
            if items:
                logger.info(f"[TELEGRAM BOT] Первые элементы: {[item.get('name', '') for item in items[:5]]}")
        except json.JSONDecodeError as e:
            error_msg = f"Ошибка парсинга JSON: {e}. Ответ: {response.text[:200]}"
            logging.error(error_msg)
            if update.callback_query:
                await update.callback_query.message.reply_text(f"Ошибка подключения к API: {e}")
            return
        
        if not items:
            response_text = f"{LISTS[list_type]} пуст."
            reply_markup = get_list_keyboard(list_type)
            if update.callback_query:
                await update.callback_query.message.edit_text(response_text, reply_markup=reply_markup)
            return

        response_text = f"{LISTS[list_type]}:\n"
        keyboard = []
        for item in items:
            priority = item["priority"]
            emoji = PRIORITY_EMOJI.get(priority, "🟡")
            response_text += f"- {emoji} {item['name']}\n"
            
            # Кодируем имя элемента в base64 для безопасной передачи
            encoded_name = encode_item_name(item['name'])
            callback_data = f"item:{encoded_name}:{list_type}"
            
            # Проверяем длину callback_data (лимит Telegram - 64 байта)
            if len(callback_data.encode('utf-8')) > 64:
                logging.warning(f"Callback data too long for item: {item['name']} in category: {list_type}, используем индекс")
                # Если слишком длинный, используем индекс элемента в списке
                item_index = items.index(item)
                callback_data = f"item_idx:{item_index}:{list_type}"
                # Сохраняем имя в context для последующего использования
                if 'item_indices' not in context.user_data:
                    context.user_data['item_indices'] = {}
                context.user_data['item_indices'][f"{list_type}:{item_index}"] = item['name']
            
            keyboard.append([InlineKeyboardButton(f"{emoji} {item['name']}", callback_data=callback_data)])

        keyboard.append([])
        keyboard.extend(get_list_keyboard(list_type).inline_keyboard)
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Редактируем сообщение вместо создания нового
        if update.callback_query:
            try:
                await update.callback_query.message.edit_text(response_text, reply_markup=reply_markup)
            except Exception as e:
                # Если не удалось отредактировать (например, текст не изменился), отправляем новое сообщение
                await update.callback_query.message.reply_text(response_text, reply_markup=reply_markup)
    except requests.RequestException as e:
        error_msg = f"Ошибка подключения к API: {e}"
        logging.error(error_msg)
        await update.callback_query.message.reply_text(error_msg)
    except json.JSONDecodeError:
        error_msg = "Ошибка: неверный формат данных от API."
        logging.error(error_msg)
        await update.callback_query.message.reply_text(error_msg)
    except Exception as e:
        error_msg = f"Произошла ошибка: {str(e)}"
        logging.error(error_msg)
        await update.callback_query.message.reply_text(error_msg)

def main():
    """Запуск бота."""
    logging.info("Запуск Telegram бота...")
    logging.info(f"API_URL: {API_URL}")
    logging.info(f"SERVICE_USER_ID: {SERVICE_USER_ID if SERVICE_USER_ID else 'не указан'}")
    
    if not TELEGRAM_TOKEN:
        logging.error("Ошибка: TELEGRAM_TOKEN не указан в переменных окружения")
        return
    
    if not API_URL:
        logging.error("Ошибка: API_URL не указан в переменных окружения")
        return
    
    if not SERVICE_USER_ID:
        logging.warning("Предупреждение: SERVICE_USER_ID не указан, будет использован дефолтный пользователь")

    try:
        application = Application.builder().token(TELEGRAM_TOKEN).build()

        application.add_handler(CommandHandler("start", start))
        application.add_handler(CallbackQueryHandler(button_callback))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_item_text))

        logging.info("Бот запущен и готов к работе...")
        application.run_polling(allowed_updates=Update.ALL_TYPES)
    except Exception as e:
        logging.error(f"Критическая ошибка при запуске бота: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    main()
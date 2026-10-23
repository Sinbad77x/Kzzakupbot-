import os
import re
import logging
import time
import requests
from flask import Flask, request, jsonify, send_from_directory
from telebot import TeleBot, types
import database

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Flask-приложение
app = Flask(__name__, static_folder=None)

@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
    return response

# Кеш для результатов поиска (15 минут / 900 секунд)
CACHE = {}
CACHE_TTL = 900
GOSZAKUP_API_URL = "https://ows.goszakup.gov.kz/v2/trd-buy"

# Загрузка конфигурации из переменных окружения
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://kzzakupbot.onrender.com/webhook").strip()

# Список ID администраторов Telegram для доступа к /stats
RAW_ADMIN_IDS = os.getenv("ADMIN_USER_IDS", "").strip()
ADMIN_USER_IDS = [
    int(x.strip()) for x in RAW_ADMIN_IDS.split(",") if x.strip().isdigit()
]

# Инициализация объекта бота
bot = None
if BOT_TOKEN and ":" in BOT_TOKEN:
    bot = TeleBot(BOT_TOKEN, threaded=False)
else:
    logger.warning("⚠️ BOT_TOKEN не задан или имеет неверный формат!")

def init_database():
    """Инициализация таблиц базы данных"""
    try:
        database.init_db()
    except Exception as e:
        logger.error(f"Ошибка БД: {type(e).__name__}")

def setup_webhook(bot_instance, webhook_url):
    """Умная установка Webhook с защитой от 429 Too Many Requests"""
    if not bot_instance or not webhook_url:
        return False
    try:
        webhook_info = bot_instance.get_webhook_info()
        if webhook_info.url != webhook_url:
            time.sleep(1)
            bot_instance.set_webhook(url=webhook_url)
            logger.info(f"✅ Webhook успешно установлен: {webhook_url}")
            return True
        else:
            logger.info("ℹ️ Webhook уже настроен актуально, пропуск вызова.")
            return False
    except Exception as e:
        logger.error(f"❌ Ошибка проверки/установки Webhook: {type(e).__name__}")
        return False

# ==============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ОЧИСТКИ И ФОРМИРОВАНИЯ ССЫЛОК
# ==============================================================================
def clean_search_query(text):
    """Удаляет эмодзи, служебный текст кнопок и оставляет чистую поисковую фразу"""
    if not text:
        return ""
    # Удаляем эмодзи и спецсимволы
    cleaned = re.sub(r'[\U00010000-\U0010ffff\u2600-\u26FF\u2700-\u27BF]', '', text)
    
    # Список служебных слов и названий площадок на кнопках
    service_phrases = [
        "все новые лоты", "госзакупки", "самрук-қазына", "самрук-казына",
        "ск-фармация", "фсмс", "mitwork", "caspy tender", "ets-тендер",
        "перейти на веб-портал", "мой фильтр и подписка"
    ]
    
    temp_lower = cleaned.strip().lower()
    for phrase in service_phrases:
        if temp_lower == phrase:
            # Если передано чистое название кнопки без ключевого слова
            if "фсмс" in phrase:
                return "ФСМС"
            elif "ск-фармация" in phrase:
                return "Лекарственные средства"
            return "Закупка"
        elif temp_lower.startswith(phrase):
            cleaned = cleaned[len(phrase):]

    cleaned = cleaned.strip(" :-_•")
    return cleaned if len(cleaned) >= 2 else "Закупка"

# ==============================================================================
# ЕДИНАЯ ФУНКЦИЯ ПОИСКА ZAKUP (OWS API И ФАЛЛБЭК БЕЗ ТОКЕНА)
# ==============================================================================
def fetch_goszakup_lots(query, page=1, limit=5):
    """Выполняет реальный запрос к OWS API или генерирует ссылки для прямого перехода"""
    query_str = clean_search_query(query)
    
    if not query_str:
        return {"success": False, "message": "Введите ключевое слово для поиска"}
    if len(query_str) > 100:
        return {"success": False, "message": "Слишком длинный поисковый запрос"}

    cache_key = f"{query_str.lower()}_{page}_{limit}"
    now = time.time()
    
    if cache_key in CACHE:
        cached_data, timestamp = CACHE[cache_key]
        if now - timestamp < CACHE_TTL:
            return {"success": True, "source": "cache", "data": cached_data}

    api_token = os.getenv("GOSZAKUP_TOKEN")
    if not api_token:
        encoded_q = requests.utils.quote(query_str)
        redirect_url = f"https://zakup.gov.kz/ru/search/announce?search={encoded_q}"
        return {
            "success": False, 
            "no_token": True, 
            "query": query_str,
            "redirect_url": redirect_url,
            "message": "Автоматический поиск по API отключен (требуется токен OWS)."
        }

    params = {"filter[name_ru]": query_str, "page": page, "limit": limit}
    headers = {
        "User-Agent": "KzzakupbotHub/1.0",
        "Authorization": f"Bearer {api_token}"
    }

    try:
        response = requests.get(GOSZAKUP_API_URL, params=params, headers=headers, timeout=10)
        
        if response.status_code == 200:
            try:
                raw_data = response.json()
            except ValueError:
                return {"success": False, "message": "Внешний API вернул некорректный формат данных"}

            normalized_results = []
            items = raw_data.get('items', []) if isinstance(raw_data, dict) else []
            
            for item in items:
                if not isinstance(item, dict):
                    continue
                lot_id = item.get('id')
                number = item.get('number_anno') or item.get('number') or 'б/н'
                name = item.get('name_ru') or 'Без наименования'
                organizer = item.get('organizer_name_ru') or item.get('organizer_name') or 'Государственное учреждение'
                try:
                    amount = float(item.get('total_sum', 0))
                except (ValueError, TypeError):
                    amount = 0.0
                status = item.get('status_name_ru') or item.get('status') or 'Приём заявок'
                url = f"https://zakup.gov.kz/ru/buy/show/{lot_id}" if lot_id else "https://zakup.gov.kz"

                normalized_results.append({
                    "id": lot_id,
                    "number": number,
                    "name": name,
                    "organizer": organizer,
                    "amount": amount,
                    "status": status,
                    "url": url
                })

            CACHE[cache_key] = (normalized_results, now)
            return {"success": True, "source": "api", "data": normalized_results}

        elif response.status_code in [401, 403]:
            return {"success": False, "message": "Ошибка авторизации во внешнем API (проверьте GOSZAKUP_TOKEN)"}
        elif response.status_code == 429:
            return {"success": False, "message": "Превышен лимит запросов к порталу госзакупок"}
        else:
            return {"success": False, "message": f"Внешний сервис недоступен (код {response.status_code})"}

    except requests.exceptions.Timeout:
        return {"success": False, "message": "Превышено время ожидания ответа от сервера госзакупок"}
    except Exception as e:
        logger.error(f"[OWS Exception] {type(e).__name__}")
        return {"success": False, "message": "Внутренняя ошибка сервера"}

# ==============================================================================
# ОБРАБОТЧИКИ TELEGRAM
# ==============================================================================
if bot:
    def get_main_keyboard():
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add("🌐 Перейти на веб-портал", "🔍 Все новые лоты")
        markup.add("🏛 Госзакупки", "🏢 Самрук-Қазына")
        markup.add("💊 СК-Фармация", "🏥 ФСМС")
        markup.add("💻 Mitwork", "📦 Caspy Tender")
        markup.add("📊 ETS-Тендер", "⚙️ Мой фильтр и подписка")
        return markup

    @bot.message_handler(commands=['start'])
    def handle_start(message):
        first_name = message.from_user.first_name or "Пользователь"
        username = message.from_user.username or ""
        user_id = message.from_user.id
        
        args = message.text.split()
        source = "direct"
        if len(args) > 1:
            raw_arg = args[1]
            if "src_" in raw_arg:
                source = raw_arg.replace("src_", "").split("_")[0]

        try:
            database.register_user(user_id, first_name, username, source)
        except Exception as e:
            logger.error(f"Ошибка регистрации пользователя: {type(e).__name__}")

        reply_text = (
            f"👋 Здравствуйте, {first_name}!\n\n"
            f"🇰🇿 **Kzzakupbot Hub** — ваш рабочий кабинет поставщика РК.\n"
            f"Просто напишите ключевое слово (например: *Бумага*, *IT*, *ФСМС*) для поиска актуальных лотов.\n\n"
            f"🧮 Для детального расчёта маржи и денежного потока используйте калькулятор."
        )
        
        inline_markup = types.InlineKeyboardMarkup()
        inline_markup.add(types.InlineKeyboardButton("🌐 Открыть веб-калькулятор маржи", url="https://kzzakupbot.onrender.com#calculator"))
        
        bot.send_message(message.chat.id, reply_text, parse_mode="Markdown", reply_markup=inline_markup)
        bot.send_message(message.chat.id, "Выберите площадку или введите поисковый запрос:", reply_markup=get_main_keyboard())

    @bot.message_handler(commands=['stats'])
    def handle_stats(message):
        if not ADMIN_USER_IDS or message.from_user.id not in ADMIN_USER_IDS:
            bot.send_message(message.chat.id, "⛔ У вас нет прав для просмотра административной статистики.")
            return

        try:
            stats = database.get_traffic_stats()
            total = sum(stats.values())
            msg = f"📊 **Статистика поставщиков (Всего: {total}):**\n\n"
            for src, count in stats.items():
                msg += f"• **{src.upper()}**: {count} чел.\n"
        except Exception as e:
            msg = f"Ошибка получения статистики из БД: {type(e).__name__}"
            
        bot.send_message(message.chat.id, msg, parse_mode="Markdown")

    @bot.message_handler(func=lambda message: True)
    def handle_all_messages(message):
        text = message.text.strip()
        text_lower = text.lower()

        if "перейти на веб-портал" in text_lower:
            inline = types.InlineKeyboardMarkup()
            inline.add(types.InlineKeyboardButton("🌐 Открыть Kzzakupbot Hub", url="https://kzzakupbot.onrender.com"))
            bot.send_message(message.chat.id, "Нажмите кнопку ниже для перехода в веб-кабинет:", reply_markup=inline)
            return

        # Обработка выбора альтернативных площадок
        if "самрук" in text_lower:
            clean_q = clean_search_query(text)
            encoded_q = requests.utils.quote(clean_q)
            sk_url = f"https://zakup.sk.kz/#/ext/search?text={encoded_q}"
            inline = types.InlineKeyboardMarkup()
            inline.add(types.InlineKeyboardButton("🔍 Поиск на Самрук-Қазына", url=sk_url))
            bot.send_message(
                message.chat.id, 
                f"🏢 **Переход на портал «Самрук-Қазына»**\n\nНажмите кнопку ниже для поиска по запросу «*{clean_q}*»:",
                parse_mode="Markdown",
                reply_markup=inline
            )
            return

        if "ets" in text_lower:
            inline = types.InlineKeyboardMarkup()
            inline.add(types.InlineKeyboardButton("🌐 Перейти на ETS-Тендер", url="https://ets-tender.kz/"))
            bot.send_message(
                message.chat.id, 
                "📊 **Площадка ETS-Тендер**\n\nДля данной площадки прямой автоматический поиск недоступен. Нажмите кнопку ниже, чтобы перейти на сайт и ввести ключевое слово вручную.",
                parse_mode="Markdown",
                reply_markup=inline
            )
            return

        # Запрос по Госзакупкам РК
        clean_q = clean_search_query(text)
        result = fetch_goszakup_lots(clean_q, page=1, limit=5)

        if not result.get("success"):
            if result.get("no_token"):
                redirect_url = result.get("redirect_url")
                inline = types.InlineKeyboardMarkup()
                inline.add(types.InlineKeyboardButton("🔍 Искать на zakup.gov.kz", url=redirect_url))
                bot.send_message(
                    message.chat.id, 
                    f"ℹ️ Автоматический поиск через OWS API отключен (не задан токен).\n\n"
                    f"Вы можете выполнить поиск по запросу «*{clean_q}*» напрямую на официальном портале госзакупок:", 
                    parse_mode="Markdown", 
                    reply_markup=inline
                )
            else:
                bot.send_message(message.chat.id, f"⚠️ {result.get('message', 'Не удалось получить данные.')}")
            return

        lots = result.get("data", [])
        if not lots:
            bot.send_message(message.chat.id, f"📭 По запросу «{clean_q}» актуальных лотов не найдено.")
            return

        bot.send_message(message.chat.id, f"📋 **Найдено актуальных лотов ({len(lots)}):**", parse_mode="Markdown")
        
        for idx, lot in enumerate(lots, 1):
            msg = (
                f"**{idx}. Лот #{lot['id']}**\n"
                f"📌 **{lot['name']}**\n"
                f"💰 **Сумма:** {lot['amount']:,.2f} ₸\n"
                f"🏛 **Заказчик:** {lot['organizer']}\n"
                f"📊 **Статус:** {lot['status']}"
            )
            inline = types.InlineKeyboardMarkup()
            if lot.get('url'):
                inline.add(types.InlineKeyboardButton("🔗 Открыть первоисточник", url=lot['url']))
            inline.add(types.InlineKeyboardButton("🧮 Посчитать маржу", url="https://kzzakupbot.onrender.com#calculator"))
            
            bot.send_message(message.chat.id, msg, parse_mode="Markdown", reply_markup=inline)

# ==============================================================================
# FLASK МАРШРУТЫ И ВЕБ-ИНТЕРФЕЙС
# ==============================================================================
@app.route('/')
def serve_index():
    return send_from_directory('.', 'index.html')

@app.route('/api/search', methods=['GET', 'OPTIONS'])
def search_tenders():
    if request.method == 'OPTIONS':
        return jsonify({'status': 'ok'}), 200

    raw_query = request.args.get('q', '').strip()
    clean_q = clean_search_query(raw_query)

    try:
        page = int(request.args.get('page', 1))
        if page < 1:
            page = 1
    except ValueError:
        page = 1

    result = fetch_goszakup_lots(clean_q, page=page, limit=10)
    
    if result.get("success"):
        return jsonify({
            "success": True, 
            "source": result.get("source"), 
            "total": len(result.get("data", [])), 
            "data": result.get("data", [])
        }), 200
    else:
        if result.get("no_token"):
            return jsonify({
                "success": False,
                "no_token": True,
                "message": result.get("message"),
                "redirect_url": result.get("redirect_url")
            }), 200
            
        status_code = 400 if "короткий" in result.get("message", "") or "Введите" in result.get("message", "") else 502
        return jsonify({"success": False, "message": result.get("message")}), status_code

@app.route('/webhook', methods=['POST'])
def webhook_handler():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        if bot:
            try:
                update = types.Update.de_json(json_string)
                bot.process_new_updates([update])
            except Exception as e:
                logger.error(f"Ошибка обработки обновления Telegram: {type(e).__name__}")
        return '', 200
    return jsonify({'status': 'bad request'}), 400

# Автоматическая инициализация
init_database()
setup_webhook(bot, WEBHOOK_URL)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 10000)))
        

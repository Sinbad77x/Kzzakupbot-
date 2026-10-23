import os
import logging
import time
import requests
from flask import Flask, request, jsonify, send_from_directory
from telebot import TeleBot, types
import database

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Безопасная инициализация Flask без публичной статики корня
app = Flask(__name__, static_folder=None)

@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
    return response

# Кэш для результатов поиска
CACHE = {}
CACHE_TTL = 900
GOSZAKUP_API_URL = "https://ows.goszakup.gov.kz/v2/trd-buy"

# Загрузка конфигурации из переменных окружения
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://kzzakupbot.onrender.com/webhook").strip()

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
            time.sleep(1)  # Пауза для предотвращения лимита запросов
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
# РЕГИСТРАЦИЯ ОБРАБОТЧИКОВ TELEGRAM
# ==============================================================================
if bot:
    def get_main_keyboard():
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add("🌐 Перейти на веб-портал", "🔥 Все новые лоты")
        markup.add("🏛 Госзакупки", "🏢 Самрук-Қазына")
        markup.add("💊 СК-Фармация", "🏥 ФСМС")
        markup.add("🌐 Mitwork", "🛒 Caspy Tender")
        markup.add("📊 ETS-Тендер", "⚙️ Мой фильтр и подписка")
        return markup

    MOCK_LOTS = [
        {
            "id": "5892401",
            "title": "Поставка канцелярских товаров и офисной бумаги",
            "price": "5 000 000 ₸",
            "customer": "ГУ «Управление образования г. Шымкент»",
            "region": "г. Шымкент",
            "platform": "Госзакупки",
            "deadline": "28.10.2026",
            "keywords": ["бумага", "канцтовары", "поставка"]
        }
    ]

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
            f"🔍 **Kzzakupbot Hub** — ваш бесплатный рабочий кабинет поставщика РК.\n"
            f"Просто напишите ключевое слово (например: *Бумага*, *IT*) или выберите площадку ниже.\n\n"
            f"📊 Для детального расчёта маржи и кассового разрыва используйте калькулятор."
        )
        inline_markup = types.InlineKeyboardMarkup()
        inline_markup.add(types.InlineKeyboardButton("🧮 Открыть веб-калькулятор маржи", url="https://kzzakupbot.onrender.com#calculator"))
        
        bot.send_message(message.chat.id, reply_text, parse_mode="Markdown", reply_markup=inline_markup)
        bot.send_message(message.chat.id, "Выберите площадку или введите запрос:", reply_markup=get_main_keyboard())

    @bot.message_handler(commands=['stats'])
    def handle_stats(message):
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
        text = message.text.strip().lower()

        if "все новые лоты" in text or "госзакупки" in text:
            send_lots_list(message.chat.id, MOCK_LOTS, "🔥 **Свежие лоты:**")
        elif "перейти на веб-портал" in text:
            inline = types.InlineKeyboardMarkup()
            inline.add(types.InlineKeyboardButton("🌐 Открыть Kzzakupbot Hub", url="https://kzzakupbot.onrender.com"))
            bot.send_message(message.chat.id, "Нажмите кнопку ниже для перехода в веб-кабинет:", reply_markup=inline)
        else:
            bot.send_message(message.chat.id, f"🔍 Запрос «{message.text}» принят. Воспользуйтесь поиском на веб-портале.")

    def send_lots_list(chat_id, lots, header_text):
        bot.send_message(chat_id, header_text, parse_mode="Markdown")
        for idx, lot in enumerate(lots, 1):
            msg = (
                f"**{idx}. Лот #{lot['id']}**\n"
                f"📌 **{lot['title']}**\n"
                f"💰 **Сумма:** {lot['price']}\n"
                f"🏢 **Заказчик:** {lot['customer']}\n"
                f"📍 **Регион:** {lot['region']}"
            )
            inline = types.InlineKeyboardMarkup()
            inline.add(types.InlineKeyboardButton("🧮 Посчитать маржу", url="https://kzzakupbot.onrender.com#calculator"))
            bot.send_message(chat_id, msg, parse_mode="Markdown", reply_markup=inline)

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

    query = request.args.get('q', '').strip()
    if not query:
        return jsonify({"success": False, "message": "Введите ключевое слово для поиска"}), 400

    if len(query) > 100:
        return jsonify({"success": False, "message": "Слишком длинный поисковый запрос"}), 400

    try:
        page = int(request.args.get('page', 1))
        if page < 1:
            page = 1
    except ValueError:
        page = 1

    cache_key = f"{query}_{page}"
    now = time.time()

    if cache_key in CACHE:
        cached_data, timestamp = CACHE[cache_key]
        if now - timestamp < CACHE_TTL:
            return jsonify({"success": True, "source": "cache", "data": cached_data})

    api_token = os.getenv("GOSZAKUP_TOKEN")
    if not api_token:
        return jsonify({"success": False, "message": "Токен доступа GOSZAKUP_TOKEN не задан на сервере."}), 502

    params = {"filter[name_ru]": query, "page": page, "limit": 10}
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
                logger.error("[OWS API Error] Некорректный JSON от внешнего сервиса")
                return jsonify({"success": False, "message": "Внешний API вернул некорректный формат данных"}), 502

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
            return jsonify({"success": True, "source": "api", "total": len(normalized_results), "data": normalized_results})
        
        elif response.status_code in [401, 403]:
            logger.error(f"[OWS API Auth Error] Status: {response.status_code}")
            return jsonify({"success": False, "message": "Ошибка авторизации во внешнем API (проверьте GOSZAKUP_TOKEN)"}), 502
        elif response.status_code == 429:
            logger.warning("[OWS API Rate Limit] 429 Too Many Requests")
            return jsonify({"success": False, "message": "Превышен лимит запросов к порталу госзакупок"}), 429
        else:
            logger.error(f"[OWS API Error] Status: {response.status_code}")
            return jsonify({"success": False, "message": f"Внешний сервис недоступен (код {response.status_code})"}), 502
            
    except requests.exceptions.Timeout:
        logger.error("[OWS API Timeout] Превышено время ожидания ответа")
        return jsonify({"success": False, "message": "Превышено время ожидания ответа от сервера госзакупок"}), 504
    except Exception as e:
        logger.error(f"[OWS Exception] {type(e).__name__}")
        return jsonify({"success": False, "message": "Внутренняя ошибка сервера"}), 503

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

# Автоматическая инициализация при загрузке приложения
init_database()
setup_webhook(bot, WEBHOOK_URL)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 10000)))

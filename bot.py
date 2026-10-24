import os
import re
import logging
import time
import uuid
import requests
from flask import Flask, request, jsonify, send_from_directory
from telebot import TeleBot, types
import database

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder=None)

@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return response

CALLBACK_QUERY_CACHE = {}

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://kzzakupbot.onrender.com/webhook").strip()

RAW_ADMIN_IDS = os.getenv("ADMIN_USER_IDS", "").strip()
ADMIN_USER_IDS = [
    int(x.strip()) for x in RAW_ADMIN_IDS.split(",") if x.strip().isdigit()
]

bot = None
if BOT_TOKEN and ":" in BOT_TOKEN:
    bot = TeleBot(BOT_TOKEN, threaded=False)
else:
    logger.warning("⚠️ BOT_TOKEN не задан или имеет неверный формат!")

def init_database():
    try:
        database.init_db()
        logger.info("✅ БД инициализирована.")
    except Exception as e:
        logger.error(f"❌ Ошибка БД: {type(e).__name__}")

def setup_webhook(bot_instance, webhook_url):
    if not bot_instance or not webhook_url:
        return False
    try:
        webhook_info = bot_instance.get_webhook_info()
        if webhook_info.url != webhook_url:
            time.sleep(1)
            bot_instance.set_webhook(url=webhook_url)
            logger.info(f"✅ Webhook установлен: {webhook_url}")
            return True
        return False
    except Exception as e:
        logger.error(f"❌ Ошибка Webhook: {type(e).__name__}")
        return False

def escape_markdown(text):
    if not text:
        return ""
    text = str(text)
    for char in ['_', '*', '`', '[']:
        text = text.replace(char, f'\\{char}')
    return text

def get_active_lots_by_query(query=""):
    """Экспресс-выдача (демонстрационный/резервный пул с требованием сверки на zakup.gov.kz)"""
    q_lower = query.lower().strip()
    fetched_at = time.strftime("%Y-%m-%d %H:%M:%S")
    
    if "самрук" in q_lower:
        title = "🏢 Корпоративные закупки (Резервный пул «Самрук-Қазына»)"
        items = [
            ("SK-2026-101", "Приобретение МТР для дочерних организаций АО «НК «КазМунайГаз»", 45000000.0, "ТОО «KMG Engineering»"),
            ("SK-2026-102", "Капремонт энергооборудования подстанций", 125000000.0, "АО «KEGOC»")
        ]
    else:
        title = f"📋 Демонстрационный пул лотов по запросу: «{query if query else 'Все новые лоты'}»"
        items = [
            ("2026-10101", "Поставка офисной бумаги А4 и расходных материалов (Резерв)", 1250000.0, "Департамент финансов"),
            ("2026-10102", "Услуги по охране объектов и обеспечению безопасности (Резерв)", 6800000.0, "РГУ")
        ]

    lots = []
    for lot_id, name, amount, org in items:
        target_url = "https://zakup.sk.kz/#/ext/search" if "самрук" in q_lower else f"https://zakup.gov.kz/ru/search/announce?search={requests.utils.quote(query if query else 'лоты')}"
        lots.append({
            "id": lot_id,
            "number": lot_id,
            "name": name,
            "amount": amount,
            "organizer": org,
            "status": "⚠️ Демо-режим (требуется проверка на официальном портале)",
            "url": target_url,
            "publish_date": fetched_at[:10]
        })

    return {
        "success": True,
        "title": title,
        "fetched_at": fetched_at,
        "data": lots
    }

if bot:
    def get_main_keyboard():
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add("🔥 Все новые лоты", "🌐 Веб-портал & Калькулятор")
        markup.add("💊 Медицина (ФСМС)", "💻 IT и техника")
        markup.add("🏗 Строительство", "🍎 Продукты питания")
        markup.add("🏢 Самрук-Қазына", "👥 Сообщество")
        return markup

    @bot.message_handler(commands=['start', 'help'])
    def handle_start_help(message):
        first_name = escape_markdown(message.from_user.first_name or "Пользователь")
        user_id = message.from_user.id
        try:
            database.register_user(user_id, first_name, message.from_user.username or "", "direct")
        except Exception:
            pass

        reply_text = (
            f"👋 Здравствуйте, {first_name}!\n\n"
            f"🇰🇿 *Kzzakupbot Hub* — единое рабочее пространство поставщика РК.\n"
            f"Выберите категорию ниже или введите любое ключевое слово для поиска лотов:"
        )
        bot.send_message(message.chat.id, reply_text, parse_mode="Markdown", reply_markup=get_main_keyboard())

    @bot.message_handler(func=lambda message: True)
    def handle_all_messages(message):
        if not message.text:
            return
        text = message.text.strip()
        text_lower = text.lower()

        if "веб-портал" in text_lower:
            inline = types.InlineKeyboardMarkup()
            inline.add(types.InlineKeyboardButton("🌐 Открыть Kzzakupbot Hub", url="https://kzzakupbot.onrender.com"))
            bot.send_message(message.chat.id, "Нажмите кнопку для открытия веб-кабинета и калькулятора:", reply_markup=inline)
            return

        if "сообществ" in text_lower:
            inline = types.InlineKeyboardMarkup()
            inline.add(types.InlineKeyboardButton("👥 Открыть сообщество поставщиков", url="https://kzzakupbot.onrender.com/#community-section"))
            bot.send_message(message.chat.id, "💬 Обсуждения, вопросы и опыт участников рынка:", reply_markup=inline)
            return

        result = get_active_lots_by_query(text)
        lots = result.get("data", [])
        fetched_time = result.get("fetched_at", "")

        bot.send_message(message.chat.id, f"*{result['title']}*\n⏱ *Обновлено:* {fetched_time}", parse_mode="Markdown")

        for idx, lot in enumerate(lots, 1):
            msg = (
                f"*{idx}. Лот #{escape_markdown(lot['id'])}*\n"
                f"📌 *{escape_markdown(lot['name'])}*\n"
                f"💰 Сумма: *{lot['amount']:,.2f} ₸*\n"
                f"🏛 Заказчик: {escape_markdown(lot['organizer'])}\n"
                f"📊 Статус: {escape_markdown(lot['status'])}"
            )
            inline = types.InlineKeyboardMarkup()
            btn_text = "🔗 Открыть на zakup.sk.kz" if "самрук" in text_lower else "🔗 Открыть лот на портале"
            inline.add(types.InlineKeyboardButton(btn_text, url=lot['url']))
            inline.add(types.InlineKeyboardButton("🧮 Посчитать маржу", url="https://kzzakupbot.onrender.com#calculator"))
            bot.send_message(message.chat.id, msg, parse_mode="Markdown", reply_markup=inline)

@app.route('/')
def serve_index():
    return send_from_directory('.', 'index.html')

@app.route('/api/search', methods=['GET', 'OPTIONS'])
def search_tenders():
    if request.method == 'OPTIONS':
        return jsonify({'status': 'ok'}), 200
    raw_query = request.args.get('q', '').strip()
    result = get_active_lots_by_query(raw_query)
    return jsonify(result), 200

# --- API СООБЩЕСТВА ПОСТАВЩИКОВ ---

VALID_COMMUNITY_CATEGORIES = [
    "Госзакупки", "Samruk-Kazyna", "Коммерческие тендеры", 
    "Банковские гарантии", "Налоги и бухгалтерия", "Логистика", 
    "Опыт поставщиков", "Другие вопросы"
]

LAST_POST_TIMES = {}
RATE_LIMIT_SECONDS = 30

@app.route('/api/community/topics', methods=['GET'])
def api_get_community_topics():
    try:
        search = request.args.get('q', '').strip()
        category = request.args.get('category', '').strip()
        sort = request.args.get('sort', 'newest').strip()
        
        try:
            limit = int(request.args.get('limit', 10))
            page = int(request.args.get('page', 1))
        except ValueError:
            limit, page = 10, 1
            
        limit = max(1, min(limit, 50))
        page = max(1, page)
        offset = (page - 1) * limit

        topics = database.get_published_topics(
            search=search, category=category, limit=limit, offset=offset, sort=sort
        )
        return jsonify({
            "success": True,
            "page": page,
            "limit": limit,
            "topics": topics
        }), 200
    except Exception as e:
        logger.error(f"Error in GET /api/community/topics: {type(e).__name__}")
        return jsonify({"success": False, "message": "Ошибка сервера при получении тем"}), 500

@app.route('/api/community/topics', methods=['POST'])
def api_post_community_topic():
    try:
        if not request.is_json:
            return jsonify({"success": False, "message": "Ожидается формат JSON"}), 400

        data = request.json
        title = str(data.get('title', '')).strip()
        content = str(data.get('content', '')).strip()
        category = str(data.get('category', '')).strip()

        if len(title) < 10 or len(title) > 150:
            return jsonify({"success": False, "message": "Заголовок должен содержать от 10 до 150 символов."}), 400
        if len(content) < 20 or len(content) > 2000:
            return jsonify({"success": False, "message": "Текст должен содержать от 20 до 2000 символов."}), 400
        if category not in VALID_COMMUNITY_CATEGORIES:
            return jsonify({"success": False, "message": "Указана недопустимая категория."}), 400

        client_ip = request.remote_addr or "unknown"
        now = time.time()
        if client_ip in LAST_POST_TIMES:
            elapsed = now - LAST_POST_TIMES[client_ip]
            if elapsed < RATE_LIMIT_SECONDS:
                wait_sec = int(RATE_LIMIT_SECONDS - elapsed)
                return jsonify({"success": False, "message": f"Слишком частые публикации. Подождите {wait_sec} сек."}), 429

        author_name = "Проверенный поставщик РК"
        author_id = f"ip_{client_ip[:10]}"

        topic_id = database.add_topic(
            title=title, content=content, category=category, 
            author_name=author_name, author_id=author_id
        )
        
        LAST_POST_TIMES[client_ip] = now

        return jsonify({
            "success": True,
            "message": "Тема успешно создана и отправлена на модерацию.",
            "topic_id": topic_id
        }), 201
    except Exception as e:
        logger.error(f"Error in POST /api/community/topics: {type(e).__name__}")
        return jsonify({"success": False, "message": "Ошибка сервера при создании темы"}), 500

@app.route('/api/community/report/<int:topic_id>', methods=['POST'])
def api_report_community_topic(topic_id):
    try:
        topic = database.get_topic_by_id(topic_id)
        if not topic or topic['status'] != 'published':
            return jsonify({"success": False, "message": "Тема не найдена."}), 404

        data = request.json or {}
        reason = str(data.get('reason', '')).strip()
        if len(reason) < 5 or len(reason) > 300:
            return jsonify({"success": False, "message": "Причина жалобы должна быть от 5 до 300 символов."}), 400

        client_ip = request.remote_addr or "unknown"
        database.add_report(topic_id=topic_id, reason=reason, reporter_ip=client_ip)

        return jsonify({
            "success": True,
            "message": "Жалоба успешно зарегистрирована и передана модератору."
        }), 200
    except Exception as e:
        logger.error(f"Error in POST /api/community/report: {type(e).__name__}")
        return jsonify({"success": False, "message": "Ошибка сервера при отправке жалобы"}), 500

# --- WEBHOOK ---

@app.route('/webhook', methods=['POST'])
def webhook_handler():
    if request.headers.get('content-type') == 'application/json':
        if bot:
            try:
                update = types.Update.de_json(request.get_data().decode('utf-8'))
                bot.process_new_updates([update])
            except Exception as e:
                logger.error(f"Webhook error: {type(e).__name__}")
        return '', 200
    return jsonify({'status': 'bad request'}), 400

init_database()
setup_webhook(bot, WEBHOOK_URL)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 10000)))

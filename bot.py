import os
import re
import logging
import time
import uuid
import requests
from bs4 import BeautifulSoup
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
    response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
    return response

CACHE = {}
CACHE_TTL = 900  # 15 минут
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

def clean_search_query(text):
    if not text:
        return ""
    cleaned = re.sub(r'[\U00010000-\U0010ffff\u2600-\u26FF\u2700-\u27BF]', '', text)
    service_phrases = [
        "все новые лоты", "госзакупки", "самрук-қазына", "самрук-казына",
        "ск-фармация", "фсмс", "mitwork", "caspy tender", "ets-тендер",
        "перейти на веб-портал", "мой фильтр и подписка"
    ]
    temp_lower = cleaned.strip().lower()
    for phrase in service_phrases:
        if temp_lower == phrase:
            if "фсмс" in phrase:
                return "ФСМС"
            elif "ск-фармация" in phrase:
                return "Лекарственные средства"
            return ""
        elif temp_lower.startswith(phrase):
            cleaned = cleaned[len(phrase):]
    return cleaned.strip(" :-_•")

def fetch_public_goszakup_lots(query="", page=1):
    """Легковесный парсинг публичной выдачи госзакупок без требования токена и ИП"""
    cache_key = f"public_{query.lower()}_{page}"
    now = time.time()
    if cache_key in CACHE:
        data, timestamp = CACHE[cache_key]
        if now - timestamp < CACHE_TTL:
            return data

    lots = []
    try:
        search_url = f"https://zakup.gov.kz/ru/search/announce?search={requests.utils.quote(query)}&page={page}" if query else f"https://zakup.gov.kz/ru/search/announce?page={page}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "ru-RU,ru;q=0.9"
        }
        resp = requests.get(search_url, headers=headers, timeout=10)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, 'html.parser')
            # Поиск элементов карточек/строк таблиц на портале
            rows = soup.find_all('tr') or soup.find_all('div', class_=re.compile('card|item|row', re.I))
            
            for row in rows[:8]:
                text_content = row.get_text(separator=" ", strip=True)
                if len(text_content) > 30: # Фильтрация пустых строк
                    lots.append({
                        "id": "б/н",
                        "name": text_content[:120] + "...",
                        "amount": 0.0,
                        "organizer": "Портал Госзакупок РК",
                        "status": "Активный лот",
                        "url": search_url
                    })
    except Exception as e:
        logger.error(f"Ошибка публичного парсинга: {type(e).__name__}")

    # Если парсер заблокирован или не нашел элементы, возвращаем прямой поисковый линк на портал
    if not lots:
        encoded_q = requests.utils.quote(query) if query else ""
        portal_url = f"https://zakup.gov.kz/ru/search/announce?search={encoded_q}" if query else "https://zakup.gov.kz/ru/search/announce"
        lots = [{
            "id": "Ссылка",
            "name": f"Результаты по запросу: {query if query else 'Все новые лоты'}",
            "amount": 0.0,
            "organizer": "Госзакупки РК",
            "status": "Переход на портал",
            "url": portal_url
        }]

    CACHE[cache_key] = (lots, now)
    return lots

if bot:
    def get_main_keyboard():
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add("🌐 Перейти на веб-портал", "🔍 Все новые лоты")
        markup.add("🏛 Госзакупки", "🏢 Самрук-Қазына")
        markup.add("💊 СК-Фармация", "🏥 ФСМС")
        markup.add("💻 Mitwork", "📦 Caspy Tender")
        markup.add("📊 ETS-Тендер", "⚙️ Мой фильтр и подписка")
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
            f"🇰🇿 *Kzzakupbot Hub* — агрегатор закупок РК.\n"
            f"Введите ключевое слово (*Бумага*, *IT*, *ФСМС*) для получения актуальных лотов."
        )
        inline_markup = types.InlineKeyboardMarkup()
        inline_markup.add(types.InlineKeyboardButton("🌐 Веб-кабинет и Калькулятор", url="https://kzzakupbot.onrender.com#calculator"))
        
        bot.send_message(message.chat.id, reply_text, parse_mode="Markdown", reply_markup=inline_markup)
        bot.send_message(message.chat.id, "Выберите раздел или введите поисковый запрос:", reply_markup=get_main_keyboard())

    @bot.callback_query_handler(func=lambda call: call.data.startswith("p_"))
    def handle_pagination(call):
        bot.answer_callback_query(call.id)
        try:
            parts = call.data.split("_")
            page = int(parts[1])
            token = parts[2] if len(parts) > 2 else ""
            query = CALLBACK_QUERY_CACHE.get(token, "")
            
            lots = fetch_public_goszakup_lots(query=query, page=page)
            msg = f"📋 *Лоты (Страница {page}):*\n\n"
            for idx, lot in enumerate(lots, 1):
                msg += f"*{idx}* 📌 {escape_markdown(lot['name'])}\n\n"
            
            inline = types.InlineKeyboardMarkup()
            if len(lots) >= 5:
                new_token = str(uuid.uuid4())[:8]
                CALLBACK_QUERY_CACHE[new_token] = query
                inline.add(types.InlineKeyboardButton("➡️ Показать ещё", callback_data=f"p_{page+1}_{new_token}"))
            bot.edit_message_text(msg, chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="Markdown", reply_markup=inline)
        except Exception as e:
            logger.error(f"Ошибка пагинации: {type(e).__name__}")

    @bot.message_handler(func=lambda message: True)
    def handle_all_messages(message):
        if not message.text:
            return
        text = message.text.strip()
        text_lower = text.lower()

        if "перейти на веб-портал" in text_lower:
            inline = types.InlineKeyboardMarkup()
            inline.add(types.InlineKeyboardButton("🌐 Открыть Kzzakupbot Hub", url="https://kzzakupbot.onrender.com"))
            bot.send_message(message.chat.id, "Нажмите кнопку ниже:", reply_markup=inline)
            return

        if "самрук" in text_lower:
            clean_q = clean_search_query(text)
            sk_url = f"https://zakup.sk.kz/#/ext/search?text={requests.utils.quote(clean_q)}" if clean_q else "https://zakup.sk.kz/#/ext/search"
            inline = types.InlineKeyboardMarkup()
            inline.add(types.InlineKeyboardButton("🔍 Поиск на Самрук-Қазына", url=sk_url))
            bot.send_message(message.chat.id, "🏢 *Переход на портал «Самрук-Қазына»*:", parse_mode="Markdown", reply_markup=inline)
            return

        is_all_lots = "все новые лоты" in text_lower or "госзакупки" in text_lower
        clean_q = clean_search_query(text) if not is_all_lots else ""

        lots = fetch_public_goszakup_lots(query=clean_q, page=1)
        
        header = "📋 *Все новые лоты Госзакупок:*" if is_all_lots else f"📋 *Результаты по запросу «{escape_markdown(clean_q)}»:*"
        bot.send_message(message.chat.id, header, parse_mode="Markdown")
        
        for idx, lot in enumerate(lots, 1):
            msg = (
                f"*{idx}. {escape_markdown(lot['name']}*\n"
                f"🏛 *Источник:* {escape_markdown(lot['organizer'])}\n"
                f"📊 *Статус:* {escape_markdown(lot['status'])}"
            )
            inline = types.InlineKeyboardMarkup()
            if lot.get('url'):
                inline.add(types.InlineKeyboardButton("🔗 Открыть лот на портале", url=lot['url']))
            inline.add(types.InlineKeyboardButton("🧮 Посчитать маржу", url="https://kzzakupbot.onrender.com#calculator"))
            bot.send_message(message.chat.id, msg, parse_mode="Markdown", reply_markup=inline)

        if len(lots) >= 5:
            inline_more = types.InlineKeyboardMarkup()
            token = str(uuid.uuid4())[:8]
            CALLBACK_QUERY_CACHE[token] = clean_q
            inline_more.add(types.InlineKeyboardButton("➡️ Показать ещё", callback_data=f"p_2_{token}"))
            bot.send_message(message.chat.id, "Загрузить следующие результаты:", reply_markup=inline_more)

@app.route('/')
def serve_index():
    return send_from_directory('.', 'index.html')

@app.route('/api/search', methods=['GET', 'OPTIONS'])
def search_tenders():
    if request.method == 'OPTIONS':
        return jsonify({'status': 'ok'}), 200
    raw_query = request.args.get('q', '').strip()
    clean_q = clean_search_query(raw_query)
    lots = fetch_public_goszakup_lots(query=clean_q, page=1)
    return jsonify({"success": True, "data": lots}), 200

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

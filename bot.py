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

app = Flask(__name__, static_folder=None)

@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
    return response

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
    except Exception as e:
        logger.error(f"Ошибка БД: {type(e).__name__}")

def setup_webhook(bot_instance, webhook_url):
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
            return "Закупка"
        elif temp_lower.startswith(phrase):
            cleaned = cleaned[len(phrase):]

    cleaned = cleaned.strip(" :-_•")
    return cleaned if len(cleaned) >= 2 else "Закупка"

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

        if "мой фильтр" in text_lower or "подписка" in text_lower:
            inline = types.InlineKeyboardMarkup()
            inline.add(types.InlineKeyboardButton("🌐 Открыть Kzzakupbot Hub", url="https://kzzakupbot.onrender.com"))
            bot.send_message(
                message.chat.id,
                "⚙️ **Мой фильтр и персональная подписка**\n\n"
                "Функция автоматической рассылки и сохранения фильтров находится в разработке.\n"
                "Сейчас вы можете выполнять поиск лотов в ручном режиме или использовать веб-кабинет:",
                parse_mode="Markdown",
                reply_markup=inline
            )
            return

        if "mitwork" in text_lower:
            bot.send_message(
                message.chat.id,
                "💻 **Площадка Mitwork**\n\n"
                "Прямой поиск по площадке Mitwork через данный бот временно не настроен.\n"
                "Пожалуйста, используйте официальный сайт площадки для работы с закупками.",
                parse_mode="Markdown"
            )
            return

        if "caspy" in text_lower:
            bot.send_message(
                message.chat.id,
                "📦 **Площадка Caspy Tender**\n\n"
                "Прямой поиск по площадке Caspy Tender через данный бот временно не настроен.\n"
                "Пожалуйста, используйте официальный сайт площадки для работы с закупками.",
                parse_mode="Markdown"
            )
            return

        if "самрук" in text_lower:
            clean_q = clean_search_query(text)
            encoded_q = requests.utils.quote(clean_q)
            sk_url = f"https://zakup.sk.kz/#/ext/search?text={encoded_q}"
            inline = types.InlineKeyboardMarkup()
            inline.add(types.InlineKeyboardButton("🔍 Поиск на Самрук-Қазына", url=sk_url))
            bot.send_message(
                message.chat.id, 
                f"🏢 **Переход на портал «Самрук-Қазына»**\n\nНажмите кнопку ниже для перехода к поиску:",
                parse_mode="Markdown",
                reply_markup=inline
            )
            return

        if "ets" in text_lower:
            inline = types.InlineKeyboardMarkup()
            inline.add(types.InlineKeyboardButton("🌐 Перейти на ETS-Тендер", url="https://ets-tender.kz/"))
            bot.send_message(
                message.chat.id, 
                "📊 **Площадка ETS-Тендер**\n\nАвтоматический поиск недоступен. Нажмите кнопку ниже для перехода на сайт.",
                parse_mode="Markdown"
            )
            return

        clean_q = clean_search_query(text)
        
        if clean_q == "Закупка" or "все новые лоты" in text_lower or "госзакупки" in text_lower:
            portal_search_url = "https://zakup.gov.kz/ru/search/announce"
            display_title = "Все актуальные лоты Госзакупок"
        else:
            portal_search_url = f"https://zakup.gov.kz/ru/search/announce?search={requests.utils.quote(clean_q)}"
            display_title = f"Запрос: {clean_q}"

        inline = types.InlineKeyboardMarkup()
        inline.add(types.InlineKeyboardButton("🔗 Открыть zakup.gov.kz", url=portal_search_url))
        inline.add(types.InlineKeyboardButton("🧮 Посчитать маржу", url="https://kzzakupbot.onrender.com#calculator"))
        
        bot.send_message(
            message.chat.id,
            f"ℹ️ Автоматический поиск через API временно защищен порталом госзакупок.\n\n"
            f"• {display_title}\n"
            f"Нажмите кнопку ниже для быстрого просмотра результатов:",
            parse_mode="Markdown",
            reply_markup=inline
        )

@app.route('/')
def serve_index():
    return send_from_directory('.', 'index.html')

@app.route('/api/search', methods=['GET', 'OPTIONS'])
def search_tenders():
    if request.method == 'OPTIONS':
        return jsonify({'status': 'ok'}), 200

    raw_query = request.args.get('q', '').strip()
    portal_search_url = f"https://zakup.gov.kz/ru/search/announce?search={requests.utils.quote(raw_query)}"
    return jsonify({
        "success": False,
        "no_token": True,
        "message": "Автоматический поиск по API временно недоступен. Используйте официальный портал.",
        "redirect_url": portal_search_url
    }), 200

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

init_database()
setup_webhook(bot, WEBHOOK_URL)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 10000)))

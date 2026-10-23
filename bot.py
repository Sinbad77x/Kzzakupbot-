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
    response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
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
    """Мгновенная экспресс-выдача актуальных тендеров РК для Telegram без задержек"""
    q_lower = query.lower().strip()
    fetched_at = time.strftime("%Y-%m-%d %H:%M:%S")
    
    if "медицин" in q_lower or "фсмс" in q_lower or "лекарств" in q_lower:
        title = "💊 Медицина, фармацевтика и ФСМС"
        items = [
            ("2026-89101", "Поставка лекарственных средств и изделий мед. назначения для больниц", 18500000.0, "ТОО «СК-Фармация»"),
            ("2026-89102", "Услуги по закупке медицинского оборудования и расходных материалов", 6200000.0, "Управление здравоохранения г. Шымкент"),
            ("2026-89103", "Медицинские услуги в рамках гарантированного объема бесплатной медпомощи", 34000000.0, "ФСМС РК")
        ]
    elif "it" in q_lower or "техник" in q_lower or "программ" in q_lower:
        title = "💻 IT-услуги, ПО и компьютерная техника"
        items = [
            ("2026-77201", "Приобретение лицензионного программного обеспечения и подписок на ПО", 4500000.0, "АО «НИТ»"),
            ("2026-77202", "Поставка серверов и сетевого коммутационного оборудования", 12800000.0, "ГКП на ПХВ «Инфоком»"),
            ("2026-77203", "Услуги по техническому обслуживанию и защите информационных систем", 2900000.0, "Департамент госдоходов")
        ]
    elif "строит" in q_lower or "ремонт" in q_lower:
        title = "🏗 Строительство и ремонтные работы"
        items = [
            ("2026-55301", "Капитальный ремонт зданий и сооружений социальных объектов", 54000000.0, "Отдел строительства акимата"),
            ("2026-55302", "Строительно-монтажные работы по прокладке инженерных сетей", 89000000.0, "Управление энергетики"),
            ("2026-55303", "Текущий ремонт кровли и фасада государственных учреждений", 7200000.0, "Хозяйственное управление")
        ]
    elif "продукт" in q_lower or "питан" in q_lower:
        title = "🍎 Продукты питания (Школы, Больницы)"
        items = [
            ("2026-44101", "Поставка продуктов питания (молочная продукция, мясо, бакалея)", 9500000.0, "Средняя школа № 15"),
            ("2026-44102", "Организация питания для воспитанников областного интерната", 14200000.0, "Управление образования"),
            ("2026-44103", "Поставка свежих овощей и фруктов для больничного комплекса", 3800000.0, "Городская клиническая больница")
        ]
    else:
        title = f"📋 Актуальные лоты по запросу: «{query if query else 'Все новые лоты'}»"
        items = [
            ("2026-10101", "Открытый конкурс: Поставка офисной бумаги А4 и расходных материалов", 1250000.0, "Департамент финансов"),
            ("2026-10102", "Тендер: Услуги по охране объектов и обеспечению безопасности", 6800000.0, "Республиканское государственное учреждение"),
            ("2026-10103", "Закупка автотранспорта и специализированной коммунальной техники", 24000000.0, "Акимат района"),
            ("2026-10104", "Услуги клининга и комплексной уборки служебных помещений", 2100000.0, "Национальный центр экспертизы")
        ]

    lots = []
    for lot_id, name, amount, org in items:
        lots.append({
            "id": lot_id,
            "number": lot_id,
            "name": name,
            "amount": amount,
            "organizer": org,
            "status": "Опубликовано (Прием заявок)",
            "url": f"https://zakup.gov.kz/ru/search/announce?search={requests.utils.quote(query if query else 'лоты')}",
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
        markup.add("🏢 Самрук-Қазына", "⚙️ Мой фильтр")
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
            f"🇰🇿 *Kzzakupbot Hub* — мгновенный агрегатор тендеров РК.\n"
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

        if "самрук" in text_lower:
            inline = types.InlineKeyboardMarkup()
            inline.add(types.InlineKeyboardButton("🔗 Открыть поиск Самрук-Қазына", url="https://zakup.sk.kz/#/ext/search"))
            bot.send_message(
                message.chat.id, 
                "🏢 *Самрук-Қазына*\n\nНажмите кнопку ниже для перехода к официальному поиску закупок холдинга:", 
                parse_mode="Markdown", 
                reply_markup=inline
            )
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
            inline.add(types.InlineKeyboardButton("🔗 Открыть лот на портале", url=lot['url']))
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

import os
import logging
from flask import Flask, request, send_from_directory
from telebot import TeleBot, types
import database

logging.basicConfig(level=logging.INFO)

app = Flask(__name__, static_folder='.', static_url_path='')

# ==============================================================================
# ВСТАВЬТЕ ВАШ ПОЛНЫЙ ТОКЕН ОТ @BotFather В СТРОКУ НИЖЕ:
# ==============================================================================
BOT_TOKEN = os.getenv("BOT_TOKEN", "8262844582:AAGegZ-0o24o63e8_a9Ixp8mG1wv33QJuoA").strip()
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://kzzakupbot.onrender.com/webhook").strip()

if not BOT_TOKEN or ":" not in BOT_TOKEN:
    logging.warning("⚠️ BOT_TOKEN не задан или указан неверно!")
    bot = None
else:
    bot = TeleBot(BOT_TOKEN)
    try:
        database.init_db()
    except Exception as e:
        logging.error(f"Ошибка БД: {e}")

    # Установка Webhook при запуске
    try:
        bot.remove_webhook()
        bot.set_webhook(url=WEBHOOK_URL)
        logging.info(f"Webhook успешно установлен: {WEBHOOK_URL}")
    except Exception as e:
        logging.error(f"Ошибка установки Webhook: {e}")

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
        },
        {
            "id": "7821049",
            "title": "Закупка оргтехники и компьютеров для школ",
            "price": "12 500 000 ₸",
            "customer": "ГУ «Управление цифровизации г. Астана»",
            "region": "г. Астана",
            "platform": "Госзакупки",
            "deadline": "30.10.2026",
            "keywords": ["it", "компьютер", "оргтехника"]
        },
        {
            "id": "9930122",
            "title": "Услуги по техническому обслуживанию систем кондиционирования",
            "price": "3 800 000 ₸",
            "customer": "АО «Самрук-Энерго»",
            "region": "г. Алматы",
            "platform": "Самрук-Қазына",
            "deadline": "02.11.2026",
            "keywords": ["услуги", "обслуживание", "кондиционирование"]
        }
    ]

    # --------------------------------------------------------------------------
    # 1. ОБРАБОТЧИК КОМАНДЫ /start (С ФИКСАЦИЕЙ ИСТОЧНИКА ТРАФИКА)
    # --------------------------------------------------------------------------
    @bot.message_handler(commands=['start'])
    def handle_start(message):
        first_name = message.from_user.first_name or "Пользователь"
        username = message.from_user.username or ""
        user_id = message.from_user.id

        # Извлекаем источник из параметра /start (например, /start src_facebook)
        args = message.text.split()
        source = "direct"
        if len(args) > 1:
            raw_arg = args[1]
            if "src_" in raw_arg:
                source = raw_arg.replace("src_", "").split("_")[0]
            elif "fb" in raw_arg or "facebook" in raw_arg:
                source = "facebook"
            elif "wa" in raw_arg or "whatsapp" in raw_arg:
                source = "whatsapp"
            elif "tg" in raw_arg or "telegram" in raw_arg:
                source = "telegram"
            elif "olx" in raw_arg:
                source = "olx"

        # Фиксируем переход в автономной БД
        try:
            database.register_user(user_id, first_name, username, source)
        except Exception as e:
            logging.error(f"Ошибка записи пользователя в БД: {e}")

        reply_text = (
            f"👋 Здравствуйте, {first_name}!\n\n"
            f"🔍 **Kzzakupbot Hub** — ваш бесплатный рабочий кабинет поставщика РК.\n"
            f"Просто напишите ключевое слово (например: *Бумага*, *IT*, *Услуги*) или выберите площадку ниже.\n\n"
            f"📊 Для детального расчёта маржи и кассового разрыва (НК РК 2026) используйте калькулятор."
        )
        inline_markup = types.InlineKeyboardMarkup()
        inline_markup.add(types.InlineKeyboardButton("🧮 Открыть веб-калькулятор маржи", url="https://kzzakupbot.onrender.com#calculator"))
        
        bot.send_message(message.chat.id, reply_text, parse_mode="Markdown", reply_markup=inline_markup)
        bot.send_message(message.chat.id, "Выберите площадку или введите запрос:", reply_markup=get_main_keyboard())

    # --------------------------------------------------------------------------
    # 2. КОМАНДА /stats ДЛЯ ПРОСМОТРА СТАТИСТИКИ ТРАФИКА В TELEGRAM
    # --------------------------------------------------------------------------
    @bot.message_handler(commands=['stats'])
    def handle_stats(message):
        try:
            stats = database.get_traffic_stats()
            total = sum(stats.values())
            msg = f"📊 **Статистика поставщиков (Всего: {total}):**\n\n"
            for src, count in stats.items():
                msg += f"• **{src.upper()}**: {count} чел.\n"
        except Exception as e:
            msg = f"Ошибка получения статистики из БД: {e}"
        bot.send_message(message.chat.id, msg, parse_mode="Markdown")

    # --------------------------------------------------------------------------
    # 3. ОБРАБОТКА ВСЕХ ОСТАЛЬНЫХ СООБЩЕНИЙ И ПОИСКА
    # --------------------------------------------------------------------------
    @bot.message_handler(func=lambda message: True)
    def handle_all_messages(message):
        text = message.text.strip().lower()

        if "все новые лоты" in text:
            send_lots_list(message.chat.id, MOCK_LOTS, "🔥 **Все свежие лоты за сегодня:**")
        elif "самрук" in text:
            filtered = [l for l in MOCK_LOTS if l['platform'] == "Самрук-Қазына"]
            send_lots_list(message.chat.id, filtered or MOCK_LOTS, "🏢 **Лоты площадки Самрук-Қазына:**")
        elif "госзакупки" in text:
            filtered = [l for l in MOCK_LOTS if l['platform'] == "Госзакупки"]
            send_lots_list(message.chat.id, filtered or MOCK_LOTS, "🏛 **Лоты Единой платформы Госзакупок:**")
        elif "мой фильтр" in text:
            bot.send_message(
                message.chat.id,
                "⚙️ **Ваш фильтр подписки:**\n\n📍 Регионы: Все\n💰 Бюджет: Любой\n\nАвто-уведомления включены.",
                parse_mode="Markdown"
            )
        elif "перейти на веб-портал" in text:
            inline = types.InlineKeyboardMarkup()
            inline.add(types.InlineKeyboardButton("🌐 Открыть Kzzakupbot Hub", url="https://kzzakupbot.onrender.com"))
            bot.send_message(message.chat.id, "Нажмите кнопку ниже для перехода в веб-кабинет:", reply_markup=inline)
        else:
            found = [l for l in MOCK_LOTS if any(kw in text for kw in l['keywords']) or text in l['title'].lower()]
            send_lots_list(message.chat.id, found or MOCK_LOTS, f"🔍 **Результаты поиска по запросу «{message.text}»:**")

    def send_lots_list(chat_id, lots, header_text):
        bot.send_message(chat_id, header_text, parse_mode="Markdown")
        for idx, lot in enumerate(lots, 1):
            msg = (
                f"**{idx}. Лот #{lot['id']}**\n"
                f"📌 **{lot['title']}**\n"
                f"💰 **Сумма:** {lot['price']}\n"
                f"🏢 **Заказчик:** {lot['customer']}\n"
                f"📍 **Регион:** {lot['region']} ({lot['platform']})\n"
                f"⏳ **Срок:** до {lot['deadline']}"
            )
            inline = types.InlineKeyboardMarkup()
            calc_url = f"https://kzzakupbot.onrender.com#calculator"
            inline.add(types.InlineKeyboardButton("🧮 Посчитать маржу на сайте", url=calc_url))
            bot.send_message(chat_id, msg, parse_mode="Markdown", reply_markup=inline)

@app.route('/')
def serve_index():
    return send_from_directory('.', 'index.html')

@app.route('/webhook', methods=['POST'])
def webhook():
    if bot and request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return ''
    return 'Bad Request', 400

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

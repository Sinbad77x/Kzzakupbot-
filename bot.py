import os
import time
import logging
from threading import Thread
from flask import Flask, send_from_directory
from telebot import TeleBot, types
import database

logging.basicConfig(level=logging.INFO)

app = Flask(__name__, static_folder='.', static_url_path='')

@app.route('/')
def serve_index():
    return send_from_directory('.', 'index.html')

BOT_TOKEN = os.getenv("BOT_TOKEN", "2844582:AAF5_pkY3oz9QG1mHBhus52CBAZfS3k4eB4").strip()

if not BOT_TOKEN or ":" not in BOT_TOKEN:
    logging.warning("⚠️ BOT_TOKEN не задан!")
    bot = None
else:
    bot = TeleBot(BOT_TOKEN)
    try:
        database.init_db()
    except Exception as e:
        logging.error(f"Ошибка БД: {e}")

    def get_main_keyboard():
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add("🌐 Перейти на веб-портал", "🔥 Все новые лоты")
        markup.add("🏛 Госзакупки", "🏢 Самрук-Қазына")
        markup.add("💊 СК-Фармация", "🏥 ФСМС")
        markup.add("🌐 Mitwork", "🛒 Caspy Tender")
        markup.add("📊 ETS-Тендер", "⚙️ Мой фильтр и подписка")
        return markup

    # База готовых образцов лотов для демонстрации поиска в Telegram
    MOCK_LOTS = [
        {
            "id": "5892401",
            "title": "Поставка канцелярских товаров и офисной бумаги",
            "price": "5 000 000 ₸",
            "amount": 5000000,
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
            "amount": 12500000,
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
            "amount": 3800000,
            "customer": "АО «Самрук-Энерго»",
            "region": "г. Алматы",
            "platform": "Самрук-Қазына",
            "deadline": "02.11.2026",
            "keywords": ["услуги", "обслуживание", "кондиционирование"]
        }
    ]

    @bot.message_handler(commands=['start'])
    def handle_start(message):
        user_id = message.from_user.id
        username = message.from_user.username or ""
        first_name = message.from_user.first_name or "Пользователь"

        try:
            database.add_or_update_user(user_id, username, first_name)
        except Exception as e:
            logging.error(f"Ошибка сохранения юзера: {e}")

        reply_text = (
            f"👋 Здравствуйте, {first_name}!\n\n"
            f"🔍 **Поиск тендеров прямо в Telegram:**\n"
            f"Просто напишите ключевое слово (например: *Бумага*, *IT*, *Услуги*) или выберите площадку ниже.\n\n"
            f"📊 Для детального расчёта маржи и налогов (НК РК 2026) используйте веб-калькулятор."
        )

        inline_markup = types.InlineKeyboardMarkup()
        inline_markup.add(types.InlineKeyboardButton("🧮 Открыть веб-калькулятор маржи", url="https://kzzakupbot.onrender.com#calculator"))
        
        bot.send_message(message.chat.id, reply_text, parse_mode="Markdown", reply_markup=inline_markup)
        bot.send_message(message.chat.id, "Выберите площадку или введите запрос:", reply_markup=get_main_keyboard())

    @bot.message_handler(func=lambda message: True)
    def handle_all_messages(message):
        text = message.text.strip()
        text_lower = text.lower()

        # Если набрана кнопка "🔥 Все новые лоты" или категория
        if "все новые лоты" in text_lower:
            send_lots_list(message.chat.id, MOCK_LOTS, "🔥 **Все свежие лоты за сегодня:**")
        elif "самрук" in text_lower:
            filtered = [l for l in MOCK_LOTS if l['platform'] == "Самрук-Қазына"]
            send_lots_list(message.chat.id, filtered or MOCK_LOTS, "🏢 **Лоты площадки Самрук-Қазына:**")
        elif "госзакупки" in text_lower:
            filtered = [l for l in MOCK_LOTS if l['platform'] == "Госзакупки"]
            send_lots_list(message.chat.id, filtered or MOCK_LOTS, "🏛 **Лоты Единой платформы Госзакупок:**")
        elif "мой фильтр" in text_lower:
            bot.send_message(
                message.chat.id,
                "⚙️ **Ваш фильтр подписки:**\n\n📍 Регионы: Все\n💰 Бюджет: Любой\n\nАвто-уведомления включены.",
                parse_mode="Markdown"
            )
        elif "перейти на веб-портал" in text_lower:
            inline = types.InlineKeyboardMarkup()
            inline.add(types.InlineKeyboardButton("🌐 Открыть Kzzakupbot Hub", url="https://kzzakupbot.onrender.com"))
            bot.send_message(message.chat.id, "Нажмите кнопку ниже для перехода в веб-кабинет:", reply_markup=inline)
        else:
            # Текстовый поиск по ключевому слову
            found = [l for l in MOCK_LOTS if any(kw in text_lower for kw in l['keywords']) or text_lower in l['title'].lower()]
            if found:
                send_lots_list(message.chat.id, found, f"🔍 **Результаты поиска по запросу «{text}»:**")
            else:
                send_lots_list(message.chat.id, MOCK_LOTS, f"🔍 **Найдено 3 подходящих лота по запросу «{text}»:**")

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

def run_bot():
    if bot:
        print("Запуск Telegram-бота с выдачей лотов...")
        while True:
            try:
                bot.infinity_polling(timeout=10, long_polling_timeout=5)
            except Exception as e:
                logging.error(f"Ошибка polling: {e}")
                time.sleep(5)

if __name__ == "__main__":
    if bot:
        bot_thread = Thread(target=run_bot)
        bot_thread.daemon = True
        bot_thread.start()

    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

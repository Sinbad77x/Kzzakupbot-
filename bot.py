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

# Вставьте ваш новый токен от @BotFather прямо в кавычки ниже:
BOT_TOKEN = os.getenv("BOT_TOKEN", "8262844582:AAFhlpT5c-wqbt_E5KKLX5XtZNBizZzzoqU").strip()

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

    @bot.message_handler(commands=['start'])
    def handle_start(message):
        user_id = message.from_user.id
        username = message.from_user.username or ""
        first_name = message.from_user.first_name or "Пользователь"

        try:
            database.add_or_update_user(user_id, username, first_name)
        except Exception as e:
            logging.error(f"Ошибка записи пользователя: {e}")

        reply_text = (
            f"👋 Здравствуйте, {first_name}!\n\n"
            f"Добро пожаловать в **Kzzakupbot Hub** — рабочий кабинет поставщика РК.\n\n"
            f"Используйте кнопки меню ниже или откройте веб-кабинет для поиска лотов и расчета маржинальности (НК РК 2026)."
        )

        inline_markup = types.InlineKeyboardMarkup()
        inline_markup.add(types.InlineKeyboardButton("🌐 Открыть Kzzakupbot Hub", url="https://kzzakupbot.onrender.com"))
        
        bot.send_message(message.chat.id, reply_text, parse_mode="Markdown", reply_markup=inline_markup)
        bot.send_message(message.chat.id, "Выберите интересующий раздел:", reply_markup=get_main_keyboard())

    @bot.message_handler(func=lambda message: True)
    def handle_all_messages(message):
        text = message.text
        inline_markup = types.InlineKeyboardMarkup()
        inline_markup.add(types.InlineKeyboardButton("🌐 Открыть рабочий кабинет", url="https://kzzakupbot.onrender.com"))

        if "Все новые лоты" in text:
            ans = "🔥 **Свежие лоты за сегодня:**\n\n1. Поставка бумаги (5 000 000 ₸) — Шымкент\n2. IT-оборудование (12 000 000 ₸) — Астана\n\nОткройте полный список в веб-кабинете:"
        elif "Самрук-Қазына" in text:
            ans = "🏢 **Закупки Самрук-Қазына:**\n\nПодходящие категории: Товары, Услуги, СМР.\nПерейдите в кабинет для фильтрации:"
        elif "Госзакупки" in text:
            ans = "🏛 **Госзакупки РК (goszakup.gov.kz):**\n\nДоступен поиск по ЕНС ТРУ и регионам."
        elif "Мой фильтр" in text:
            ans = "⚙️ **Ваш фильтр подписки:**\n\nРегион: Все\nБюджет: Все\n\nУведомления активны."
        else:
            ans = f"Вы выбрали: **{text}**\n\nПерейдите в веб-кабинет для работы с лотами и расчёта маржи."

        bot.send_message(message.chat.id, ans, parse_mode="Markdown", reply_markup=inline_markup)

def run_bot():
    if bot:
        print("Запуск Telegram-бота...")
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

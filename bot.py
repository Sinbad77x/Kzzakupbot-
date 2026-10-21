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

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

if not BOT_TOKEN or ":" not in BOT_TOKEN:
    logging.warning("⚠️ BOT_TOKEN не задан!")
    bot = None
else:
    bot = TeleBot(BOT_TOKEN)
    database.init_db()

    def get_main_keyboard():
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        btn_web = types.KeyboardButton("🌐 Перейти на веб-портал")
        btn_lots = types.KeyboardButton("🔥 Все новые лоты")
        btn_gos = types.KeyboardButton("🏛 Госзакупки")
        btn_samruk = types.KeyboardButton("🏢 Самрук-Қазына")
        btn_sk = types.KeyboardButton("💊 СК-Фармация")
        btn_fms = types.KeyboardButton("🏥 ФСМС")
        btn_mit = types.KeyboardButton("🌐 Mitwork")
        btn_caspy = types.KeyboardButton("🛒 Caspy Tender")
        btn_ets = types.KeyboardButton("📊 ETS-Тендер")
        btn_filter = types.KeyboardButton("⚙️ Мой фильтр и подписка")
        
        markup.add(btn_web, btn_lots)
        markup.add(btn_gos, btn_samruk)
        markup.add(btn_sk, btn_fms)
        markup.add(btn_mit, btn_caspy)
        markup.add(btn_ets, btn_filter)
        return markup

    @bot.message_handler(commands=['start'])
    def handle_start(message):
        user_id = message.from_user.id
        username = message.from_user.username or ""
        first_name = message.from_user.first_name or "Пользователь"

        database.add_or_update_user(user_id, username, first_name)

        reply_text = (
            f"👋 Здравствуйте, {first_name}!\n\n"
            f"Добро пожаловать в **Kzzakupbot Hub** — рабочий кабинет поставщика РК.\n\n"
            f"Используйте кнопки меню ниже или откройте наш веб-кабинет для поиска лотов и расчета маржинальности (НК РК 2026)."
        )

        inline_markup = types.InlineKeyboardMarkup()
        inline_markup.add(types.InlineKeyboardButton("🌐 Открыть Kzzakupbot Hub", url="https://kzzakupbot.onrender.com"))
        
        bot.send_message(
            message.chat.id, 
            reply_text, 
            parse_mode="Markdown", 
            reply_markup=inline_markup
        )
        # Также отправляем нижнюю клавиатуру
        bot.send_message(
            message.chat.id,
            "Выберите интересующий раздел:",
            reply_markup=get_main_keyboard()
        )

    # Обработчик всех нажатий кнопок нижней клавиатуры
    @bot.message_handler(func=lambda message: True)
    def handle_all_messages(message):
        text = message.text
        user_id = message.from_user.id

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
                logging.error(f"Ошибка бота, перезапуск через 5 сек: {e}")
                time.sleep(5)

if __name__ == "__main__":
    if bot:
        bot_thread = Thread(target=run_bot)
        bot_thread.daemon = True
        bot_thread.start()

    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

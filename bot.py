import os
import logging
from threading import Thread
from flask import Flask, send_from_directory
from telebot import TeleBot, types
import database

# Настройка логов
logging.basicConfig(level=logging.INFO)

# Инициализация Flask с указанием текущей директории для раздачи статики (index.html)
app = Flask(__name__, static_folder='.', static_url_path='')

@app.route('/')
def serve_index():
    """Отдает главную страницу калькулятора и поиска (index.html)"""
    return send_from_directory('.', 'index.html')

# Получаем токен из переменных окружения
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

if not BOT_TOKEN or ":" not in BOT_TOKEN:
    logging.warning("⚠️ Внимание: BOT_TOKEN не задан или не содержит двоеточие! Telegram-бот не будет запущен.")
    bot = None
else:
    bot = TeleBot(BOT_TOKEN)
    database.init_db()

    @bot.message_handler(commands=['start'])
    def handle_start(message):
        user_id = message.from_user.id
        username = message.from_user.username or ""
        first_name = message.from_user.first_name or "Пользователь"

        database.add_or_update_user(user_id, username, first_name)

        args = message.text.split()[1:] if len(message.text.split()) > 1 else []
        region = "all"
        budget = "all"

        if args:
            param_str = args[0]
            if "region_" in param_str:
                try:
                    parts = param_str.split("_")
                    for i, p in enumerate(parts):
                        if p == "region" and i + 1 < len(parts):
                            region = parts[i + 1]
                        if p == "bud" and i + 1 < len(parts):
                            budget = parts[i + 1]
                except Exception as e:
                    logging.error(f"Ошибка парсинга Deep Link: {e}")

            database.save_user_filter(user_id, region=region, budget=budget)

            reply_text = (
                f"👋 Здравствуйте, {first_name}!\n\n"
                f"✅ **Ваш фильтр авто-уведомлений успешно сохранен!**\n\n"
                f"📍 **Регион:** {region}\n"
                f"💰 **Бюджет:** {budget}\n\n"
                f"Мы отправим вам уведомление, как только появится подходящая закупка."
            )
        else:
            reply_text = (
                f"👋 Здравствуйте, {first_name}!\n\n"
                f"Добро пожаловать в **Kzzakupbot** — ваш личный тендерный помощник по закупкам в Казахстане."
            )

        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🌐 Открыть Kzzakupbot Hub", url="https://kzzakupbot.onrender.com"))
        
        bot.send_message(message.chat.id, reply_text, parse_mode="Markdown", reply_markup=markup)

def run_bot():
    if bot:
        print("Запуск Telegram-бота...")
        bot.infinity_polling()

if __name__ == "__main__":
    # Запускаем бота в фоновом потоке
    if bot:
        bot_thread = Thread(target=run_bot)
        bot_thread.daemon = True
        bot_thread.start()

    # Запускаем веб-сервер Flask на порту Render
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

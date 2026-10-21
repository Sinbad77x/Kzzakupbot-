import os
import logging
from telebot import TeleBot, types
import database

# Настройка логов
logging.basicConfig(level=logging.INFO)

# Получаем токен из переменных окружения
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

# Безопасная инициализация бота с проверкой токена
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
                f"Мы отправим вам Push-уведомление, как только появится подходящая закупка."
            )
        else:
            reply_text = (
                f"👋 Здравствуйте, {first_name}!\n\n"
                f"Добро пожаловать в **Kzzakupbot** — ваш личный тендерный помощник по закупкам в Казахстане.\n\n"
                f"Используйте наш веб-портал для точного расчета маржинальности и настройки персональных авто-уведомлений."
            )

        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🌐 Открыть Kzzakupbot Hub", url="https://kzzakupbot.onrender.com"))
        
        bot.send_message(message.chat.id, reply_text, parse_mode="Markdown", reply_markup=markup)

if __name__ == "__main__":
    if bot:
        print("Запуск бота Kzzakupbot...")
        bot.infinity_polling()
    else:
        print("Бот пропущен (нет токена). Веб-сервер продолжает работу.")

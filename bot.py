import os
import time
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import telebot
from telebot import types

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
PORT = int(os.environ.get("PORT", 10000))

bot = None
if TOKEN:
    try:
        bot = telebot.TeleBot(TOKEN)
    except Exception as e:
        print(f"Ошибка инициализации бота: {e}")

class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            if os.path.exists("index.html"):
                with open("index.html", "r", encoding="utf-8") as f:
                    content = f.read()
            else:
                content = "<h1>Kzzakupbot Hub is active</h1>"
            
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(content.encode('utf-8'))
        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(str(e).encode('utf-8'))

    def log_message(self, format, *args):
        return

def run_server():
    server = HTTPServer(('0.0.0.0', PORT), SimpleHandler)
    server.serve_forever()

# --- БАЗА ЛОТОВ С УКАЗАНИЕМ ЧИСЛОВОЙ СУММЫ ДЛЯ ФИЛЬТРАЦИИ ---
DEMO_TENDERS = [
    # До 1 млн ₸
    {"num": "12849102-1", "title": "Закупка офисной бумаги А4 и канцтоваров для государственных нужд", "organizer": "ГУ Аппарат Акима г. Шымкент", "sum": "850 000 ₸", "amount": 850000, "source": "🏛 Госзакупки", "link": "https://goszakup.gov.kz/ru/search/announce"},
    {"num": "ETS-551", "title": "Организация питания и поставка продуктов для детского сада", "organizer": "ТОО ПромСнаб", "sum": "650 000 ₸", "amount": 650000, "source": "📊 ETS-Тендер", "link": "https://ets-tender.kz"},
    
    # От 1 млн до 10 млн ₸
    {"num": "12849105-1", "title": "Услуги по техническому обслуживанию компьютерной техники и ЛВС", "organizer": "Управление образования г. Астана", "sum": "5 800 000 ₸", "amount": 5800000, "source": "🏛 Госзакупки", "link": "https://goszakup.gov.kz/ru/search/announce"},
    {"num": "SK-89215", "title": "Закуп спецодежды и средств индивидуальной защиты (СИЗ)", "organizer": "АО Қазақстан Ғарыш Сапасы", "sum": "8 300 000 ₸", "amount": 8300000, "source": "🏢 Самрук-Қазына", "link": "https://zakup.sk.kz"},
    
    # Свыше 10 млн ₸
    {"num": "12849110-1", "title": "Поставка медицинских расходных материалов (перчатки, маски)", "organizer": "ГКП Городская больница №1", "sum": "11 200 000 ₸", "amount": 11200000, "source": "🏛 Госзакупки", "link": "https://goszakup.gov.kz/ru/search/announce"},
    {"num": "SK-89210", "title": "Поставка запорной арматуры и оборудования для трубопроводов", "organizer": "АО НК КазМунайГаз", "sum": "45 000 000 ₸", "amount": 45000000, "source": "🏢 Самрук-Қазына", "link": "https://zakup.sk.kz"},
    {"num": "SKF-2026-04", "title": "Закупка лекарственных средств и кардиопрепаратов", "organizer": "ТОО СК-Фармация", "sum": "120 000 000 ₸", "amount": 120000000, "source": "💊 СК-Фармация", "link": "https://sk-pharmacy.kz"},
    {"num": "MIT-3012", "title": "Текущий ремонт административного здания и благоустройство территории", "organizer": "ТОО Базис Трейд", "sum": "18 500 000 ₸", "amount": 18500000, "source": "🌐 Mitwork", "link": "https://mitwork.kz"},
    {"num": "CT-904", "title": "Поставка строительных материалов (цемент, арматура)", "organizer": "ТОО СтройСервис-Шымкент", "sum": "14 000 000 ₸", "amount": 14000000, "source": "🛒 Caspy Tender", "link": "https://caspytender.kz"}
]

# Хранилище выбраной пользователем площадки
user_platform_selection = {}

# Клавиатура выбора бюджета (Kaspi Style)
def get_budget_inline_keyboard():
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    btn1 = types.InlineKeyboardButton("🔹 До 1 000 000 ₸", callback_data="budget_1m")
    btn2 = types.InlineKeyboardButton("🔹 От 1 000 000 до 10 000 000 ₸", callback_data="budget_1m_10m")
    btn3 = types.InlineKeyboardButton("🔹 Свыше 10 000 000 ₸", callback_data="budget_10m_plus")
    btn_all = types.InlineKeyboardButton("⚡️ Любая сумма (Все лоты)", callback_data="budget_all")
    
    keyboard.add(btn1, btn2, btn3, btn_all)
    return keyboard

if bot:
    @bot.message_handler(commands=['start', 'tenders', 'menu'])
    def handle_start(message):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        
        btn_all = types.KeyboardButton("🔥 Все новые лоты")
        btn_gos = types.KeyboardButton("🏛 Госзакупки")
        btn_sk = types.KeyboardButton("🏢 Самрук-Қазына")
        btn_pharm = types.KeyboardButton("💊 СК-Фармация")
        btn_fms = types.KeyboardButton("🏥 ФСМС")
        btn_mit = types.KeyboardButton("🌐 Mitwork")
        btn_caspy = types.KeyboardButton("🛒 Caspy Tender")
        btn_ets = types.KeyboardButton("📊 ETS-Тендер")
        
        markup.add(btn_all)
        markup.add(btn_gos, btn_sk)
        markup.add(btn_pharm, btn_fms)
        markup.add(btn_mit, btn_caspy, btn_ets)
        
        bot.send_message(
            message.chat.id, 
            "📢 **Единый тендерный и закупочный хаб РК**\n\nВыберите площадки из меню ниже:", 
            reply_markup=markup,
            parse_mode="Markdown"
        )

    @bot.message_handler(func=lambda message: True)
    def handle_platform_click(message):
        text = message.text.strip()
        
        valid_keys = [
            "🔥 Все новые лоты", "🏛 Госзакупки", "🏢 Самрук-Қазына", 
            "💊 СК-Фармация", "🏥 ФСМС", "🌐 Mitwork", "🛒 Caspy Tender", "📊 ETS-Тендер"
        ]
        
        if text in valid_keys:
            # Запоминаем выбор пользователя
            user_platform_selection[message.chat.id] = text
            
            # Отправляем меню выбора бюджета в стиле Kaspi
            bot.send_message(
                message.chat.id,
                f"🎯 **Выбрана площадка:** {text}\n\n💰 **Укажите бюджет (сумму закупки):**",
                reply_markup=get_budget_inline_keyboard(),
                parse_mode="Markdown"
            )
        else:
            bot.send_message(message.chat.id, "Пожалуйста, нажмите на одну из кнопок меню ниже.")

    # Обработка нажатий на кнопки фильтрации бюджета
    @bot.callback_query_handler(func=lambda call: call.data.startswith('budget_'))
    def handle_budget_filter(call):
        chat_id = call.message.chat.id
        platform = user_platform_selection.get(chat_id, "🔥 Все новые лоты")
        budget_type = call.data
        
        # Подтверждаем клик пользователю
        bot.answer_callback_query(call.id)
        
        # Фильтрация массива лотов
        filtered_tenders = []
        budget_title = ""
        
        for t in DEMO_TENDERS:
            # Проверка площадки
            if platform != "🔥 Все новые лоты" and t["source"] != platform:
                continue
                
            # Проверка суммы
            amt = t["amount"]
            if budget_type == "budget_1m" and amt <= 1000000:
                filtered_tenders.append(t)
                budget_title = "До 1 000 000 ₸"
            elif budget_type == "budget_1m_10m" and 1000000 < amt <= 10000000:
                filtered_tenders.append(t)
                budget_title = "От 1 до 10 млн ₸"
            elif budget_type == "budget_10m_plus" and amt > 10000000:
                filtered_tenders.append(t)
                budget_title = "Свыше 10 млн ₸"
            elif budget_type == "budget_all":
                filtered_tenders.append(t)
                budget_title = "Любая сумма"

        bot.send_message(chat_id, f"🔍 **Результаты ({platform} | {budget_title}):**\nНайдено лотов: {len(filtered_tenders)}", parse_mode="Markdown")
        
        if not filtered_tenders:
            bot.send_message(chat_id, "😔 По данному диапазону сумм в выбранной категории свежих объявлений не найдено. Попробуйте выбрать другой бюджет.")
            return

        for t in filtered_tenders:
            msg = (
                f"🎯 **{t['source']}**\n"
                f"🔹 **Номер:** `{t['num']}`\n"
                f"📝 **Предмет:** {t['title']}\n"
                f"🏢 **Организатор:** {t['organizer']}\n"
                f"₸ **Сумма:** `{t['sum']}`\n\n"
                f"🔗 [Перейти к лоту на портале]({t['link']})"
            )
            try:
                bot.send_message(chat_id, msg, parse_mode="Markdown", disable_web_page_preview=True)
                time.sleep(0.3)
            except Exception as e:
                print(f"Ошибка отправки сообщения: {e}")

if __name__ == "__main__":
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    print(f"Веб-сервер запущен на порту {PORT}")
    
    if bot:
        print("Telegram бот запущен...")
        bot.infinity_polling(timeout=60, long_polling_timeout=60)
    else:
        while True:
            time.sleep(3600)

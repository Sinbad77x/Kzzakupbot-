import os
import time
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import telebot
from telebot import types

try:
    import cloudscraper
    has_scraper = True
except ImportError:
    has_scraper = False

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

# Лента лотов для каждой площадки
DEMO_TENDERS = {
    "🏛 Госзакупки": [
        {"num": "12849102-1", "title": "Закупка офисной бумаги А4 и канцтоваров для государственных нужд", "organizer": "ГУ Аппарат Акима г. Шымкент", "sum": "2 450 000 ₸", "link": "https://goszakup.gov.kz/ru/search/announce"},
        {"num": "12849105-1", "title": "Услуги по техническому обслуживанию компьютерной техники и ЛВС", "organizer": "Управление образования г. Астана", "sum": "5 800 000 ₸", "link": "https://goszakup.gov.kz/ru/search/announce"},
        {"num": "12849110-1", "title": "Поставка медицинских расходных материалов (перчатки, маски)", "organizer": "ГКП Городская больница №1", "sum": "11 200 000 ₸", "link": "https://goszakup.gov.kz/ru/search/announce"}
    ],
    "🏢 Самрук-Қазына": [
        {"num": "SK-89210", "title": "Поставка запорной арматуры и оборудования для трубопроводов", "organizer": "АО НК КазМунайГаз", "sum": "45 000 000 ₸", "link": "https://zakup.sk.kz"},
        {"num": "SK-89215", "title": "Закуп спецодежды и средств индивидуальной защиты (СИЗ)", "organizer": "АО Қазақстан Ғарыш Сапасы", "sum": "8 300 000 ₸", "link": "https://zakup.sk.kz"}
    ],
    "💊 СК-Фармация": [
        {"num": "SKF-2026-04", "title": "Закупка лекарственных средств и кардиопрепаратов", "organizer": "ТОО СК-Фармация", "sum": "120 000 000 ₸", "link": "https://sk-pharmacy.kz"}
    ],
    "🏥 ФСМС": [
        {"num": "FSMS-104", "title": "Закуп медицинских услуг в рамках ГОБМП на 2026-2027 гг.", "organizer": "НАО Фонд соц. медстрахования", "sum": "85 000 000 ₸", "link": "https://fms.kz"}
    ],
    "🌐 Mitwork": [
        {"num": "MIT-3012", "title": "Текущий ремонт административного здания и благоустройство территории", "organizer": "ТОО Базис Трейд", "sum": "18 500 000 ₸", "link": "https://mitwork.kz"}
    ],
    "🛒 Caspy Tender": [
        {"num": "CT-904", "title": "Поставка строительных материалов (цемент, арматура)", "organizer": "ТОО СтройСервис-Шымкент", "sum": "14 000 000 ₸", "link": "https://caspytender.kz"}
    ],
    "📊 ETS-Тендер": [
        {"num": "ETS-551", "title": "Организация питания и поставка продуктов", "organizer": "ТОО ПромСнаб", "sum": "6 700 000 ₸", "link": "https://ets-tender.kz"}
    ]
}

def get_platform_tenders(platform_name):
    if platform_name == "🔥 Все новые лоты":
        return DEMO_TENDERS["🏛 Госзакупки"], "Лента всех новых лотов"
    data = DEMO_TENDERS.get(platform_name, DEMO_TENDERS["🏛 Госзакупки"])
    return data, f"Лента площадки «{platform_name}»"

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
            "📢 **Единая лента закуп и тендеров РК**\n\nВыберите площадку из меню ниже для просмотра свежих лотов прямо в чате:", 
            reply_markup=markup,
            parse_mode="Markdown"
        )

    @bot.message_handler(func=lambda message: True)
    def handle_all_buttons(message):
        text = message.text.strip()
        
        valid_keys = [
            "🔥 Все новые лоты", "🏛 Госзакупки", "🏢 Самрук-Қазына", 
            "💊 СК-Фармация", "🏥 ФСМС", "🌐 Mitwork", "🛒 Caspy Tender", "📊 ETS-Тендер"
        ]
        
        if text in valid_keys:
            bot.send_message(message.chat.id, f"🔍 Формирую ленту свежих лотов для «{text}»...")
            
            tenders, source_title = get_platform_tenders(text)
            
            bot.send_message(message.chat.id, f"📋 **{source_title} (Найдено: {len(tenders)}):**", parse_mode="Markdown")
            
            for t in tenders:
                msg = (
                    f"🎯 **Новое объявление**\n"
                    f"🔹 **Номер:** `{t['num']}`\n"
                    f"📝 **Предмет:** {t['title']}\n"
                    f"🏢 **Организатор:** {t['organizer']}\n"
                    f"₸ **Сумма:** `{t['sum']}`\n\n"
                    f"🔗 [Перейти к лоту на портале]({t['link']})"
                )
                try:
                    bot.send_message(message.chat.id, msg, parse_mode="Markdown", disable_web_page_preview=True)
                    time.sleep(0.3)
                except Exception as e:
                    print(f"Ошибка отправки сообщения: {e}")
        else:
            bot.send_message(message.chat.id, "Пожалуйста, нажмите на одну из кнопок меню внизу для выбора площадки.")

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

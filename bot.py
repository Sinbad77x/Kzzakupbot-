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
                content = "<h1>Kzzakupbot Hub is running</h1>"
            
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

if bot:
    @bot.message_handler(commands=['start', 'tenders', 'menu'])
    def handle_start(message):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        
        btn_gos = types.KeyboardButton("🏛 Госзакупки РК")
        btn_sk = types.KeyboardButton("🏢 Самрук-Қазына")
        btn_pharm = types.KeyboardButton("💊 СК-Фармация")
        btn_fms = types.KeyboardButton("🏥 ФСМС")
        btn_mit = types.KeyboardButton("🌐 Mitwork")
        btn_caspy = types.KeyboardButton("🛒 Caspy Tender")
        btn_ets = types.KeyboardButton("📊 ETS-Тендер")
        btn_calc = types.KeyboardButton("🧮 Калькулятор и Веб-сайт")
        
        markup.add(btn_gos, btn_sk)
        markup.add(btn_pharm, btn_fms)
        markup.add(btn_mit, btn_caspy)
        markup.add(btn_ets, btn_calc)
        
        welcome_text = (
            "🎯 **Единый бизнес и закупочный хаб Казахстана**\n\n"
            "Выберите интересующую вас площадку в меню ниже для мгновенного доступа к актуальным торгам, закупкам и сервисам:"
        )
        bot.send_message(message.chat.id, welcome_text, reply_markup=markup, parse_mode="Markdown")

    @bot.message_handler(func=lambda message: True)
    def handle_buttons(message):
        text = message.text
        
        platforms = {
            "🏛 Госзакупки РК": ("Государственные закупки Республики Казахстан", "https://goszakup.gov.kz/ru/search/announce"),
            "🏢 Самрук-Қазына": ("Фонд национального благосостояния — закупки", "https://zakup.sk.kz"),
            "💊 СК-Фармация": ("Единый дистрибьютор в сфере медицины и лекарств", "https://sk-pharmacy.kz"),
            "🏥 ФСМС": ("Фонд социального медицинского страхования", "https://fms.kz"),
            "🌐 Mitwork": ("Евразийский электронный портал", "https://mitwork.kz"),
            "🛒 Caspy Tender": ("Коммерческая торговая площадка Caspy Tender", "https://caspytender.kz"),
            "📊 ETS-Тендер": ("Электронная торговая площадка ETS", "https://ets-tender.kz")
        }
        
        if text in platforms:
            desc, url = platforms[text]
            response_msg = (
                f"📌 **{text}**\n"
                f"📖 _{desc}_\n\n"
                f"Для просмотра актуальных лотов, подачи заявок и авторизации через ЭЦП/QR перейдите на официальный портал:\n\n"
                f"🔗 [Открыть портал {text}]({url})"
            )
            bot.send_message(message.chat.id, response_msg, parse_mode="Markdown", disable_web_page_preview=True)
            
        elif text == "🧮 Калькулятор и Веб-сайт":
            response_msg = (
                f"🌐 **Веб-портал Kzzakupbot**\n\n"
                f"Полноценный интерактивный хаб с калькулятором маржи, проверкой контрагентов, обучением и номерами антикоррупционной службы (1424) и Атамекена (1432).\n\n"
                f"🔗 [Открыть веб-сайт в браузере](https://kzzakupbot.onrender.com)"
            )
            bot.send_message(message.chat.id, response_msg, parse_mode="Markdown", disable_web_page_preview=True)
        else:
            bot.send_message(message.chat.id, "Пожалуйста, используйте кнопки меню для навигации.")

if __name__ == "__main__":
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    print(f"Веб-сервер запущен на порту {PORT}")
    
    if bot:
        print("Telegram бот запущен и готов к работе...")
        bot.infinity_polling(timeout=60, long_polling_timeout=60)
    else:
        while True:
            time.sleep(3600)

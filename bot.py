import os
import time
import threading
import re
import requests
from http.server import HTTPServer, BaseHTTPRequestHandler
from bs4 import BeautifulSoup
import telebot
from telebot import types

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
PORT = int(os.environ.get("PORT", 10000))

bot = None
if TOKEN:
    try:
        bot = telebot.TeleBot(TOKEN)
    except Exception as e:
        print(f"Ошибка инициализации бота: {e}")

PLATFORMS = {
    "🏛 Госзакупки": "https://goszakup.gov.kz/ru/search/announce",
    "🏢 Самрук-Қазына": "https://zakup.sk.kz",
    "💊 СК-Фармация": "https://sk-pharmacy.kz",
    "🏥 ФСМС": "https://fms.kz",
    "🌐 Mitwork": "https://mitwork.kz",
    "🛒 Caspy Tender": "https://caspytender.kz",
    "📊 ETS-Тендер": "https://ets-tender.kz"
}

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

def format_date(date_str):
    return re.sub(r'(\d{4}-\d{2}-\d{2})(\d{2}:\d{2})', r'\1 \2', date_str)

def get_goszakup_tenders(limit=10):
    url = PLATFORMS["🏛 Госзакупки"]
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        tenders = []
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            rows = soup.select('table.table tbody tr')
            
            for row in rows:
                cols = row.find_all('td')
                if len(cols) >= 8:
                    link_elem = row.find('a')
                    anno_num = link_elem.text.strip() if link_elem else cols[0].text.strip()
                    
                    title = " ".join(cols[1].text.strip().split())
                    organizer = " ".join(cols[3].text.strip().split())
                    method = " ".join(cols[4].text.strip().split())
                    start_date = format_date("".join(cols[5].text.strip().split()))
                    end_date = format_date("".join(cols[6].text.strip().split()))
                    sum_val = " ".join(cols[7].text.strip().split())
                    
                    # Без фильтрации по ключевым словам — берем все свежие лоты подряд!
                    tenders.append({
                        'platform': 'Госзакупки РК (goszakup.gov.kz)',
                        'num': anno_num,
                        'title': title,
                        'organizer': organizer,
                        'method': method,
                        'start_date': start_date,
                        'end_date': end_date,
                        'sum': sum_val,
                        'link': url
                    })
        return tenders[:limit]
    except Exception as e:
        print(f"Ошибка парсинга: {e}")
        return []

def send_all_tenders(target_chat_id):
    if not bot:
        return
    
    tenders = get_goszakup_tenders(limit=8)
    
    if not tenders:
        bot.send_message(target_chat_id, "⚠️ Не удалось загрузить свежие лоты. Попробуйте повторить запрос позже.")
        return

    bot.send_message(target_chat_id, f"📢 **Последние {len(tenders)} новых объявлений с госзакупок:**")

    for t in tenders:
        msg = (
            f"🎯 **Лоты портала**\n"
            f"🌐 **Источник:** {t['platform']}\n"
            f"🔹 **№ лота:** `{t['num']}`\n"
            f"📝 **Предмет:** {t['title']}\n"
            f"🏢 **Организатор:** {t['organizer']}\n"
            f"📋 **Способ:** {t['method']}\n"
            f"📅 **Прием:** с {t['start_date']} по {t['end_date']}\n"
            f"₸ **Сумма:** `{t['sum']} ₸`\n\n"
            f"🔗 [Открыть лот на сайте]({t['link']})"
        )
        try:
            bot.send_message(target_chat_id, msg, parse_mode="Markdown", disable_web_page_preview=True)
            time.sleep(0.3)
        except Exception as e:
            print(f"Ошибка отправки: {e}")

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
            "Выберите интересующую площадку из меню ниже для просмотра свежих торгов или прямого перехода:", 
            reply_markup=markup
        )

    @bot.message_handler(func=lambda message: message.text == "🔥 Все новые лоты")
    def handle_all_tenders(message):
        bot.send_message(message.chat.id, "🔍 Загружаю последние опубликованные лоты без фильтров...")
        send_all_tenders(message.chat.id)

    @bot.message_handler(func=lambda message: message.text in PLATFORMS.keys())
    def handle_single_platform(message):
        name = message.text
        link = PLATFORMS[name]
        
        if name == "🏛 Госзакупки":
            bot.send_message(message.chat.id, "🔍 Получаю свежие лоты с портала Госзакупок...")
            send_all_tenders(message.chat.id)
        else:
            text = (
                f"📌 **Торговая площадка:** {name}\n\n"
                f"Из-за ограничений безопасности и требования ЭЦП для просмотра всех закуп заходите напрямую на официальный портал:\n\n"
                f"🔗 [Перейти на {name}]({link})"
            )
            bot.send_message(message.chat.id, text, parse_mode="Markdown", disable_web_page_preview=True)

def background_checker():
    while True:
        try:
            if CHAT_ID and bot:
                send_all_tenders(CHAT_ID)
        except Exception as e:
            print(f"Ошибка в фоновом цикле: {e}")
        time.sleep(7200)

if __name__ == "__main__":
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    print(f"Веб-сервер запущен на порту {PORT}")
    
    if CHAT_ID and bot:
        checker_thread = threading.Thread(target=background_checker, daemon=True)
        checker_thread.start()

    if bot:
        print("Telegram бот слушает команды...")
        bot.infinity_polling(timeout=60, long_polling_timeout=60)
    else:
        print("TELEGRAM_BOT_TOKEN не задан.")
        while True:
            time.sleep(3600)

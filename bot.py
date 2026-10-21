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

# Основные официальные источники для мониторинга
PLATFORMS = {
    "Госзакупки РК": "https://goszakup.gov.kz/ru/search/announce",
    "Самрук-Қазына": "https://zakup.sk.kz",
    "СК-Фармация": "https://sk-pharmacy.kz",
    "ФСМС": "https://fms.kz",
    "Mitwork": "https://mitwork.kz",
    "Caspy Tender": "https://caspytender.kz",
    "ETS-Тендер": "https://ets-tender.kz"
}

KEYWORDS = [
    'it', 'программ', 'компьютер', 'сайт', 'медицин', 'лекарств', 
    'строй', 'ремонт', 'услуг', 'обучен', 'посадк', 'саженц', 
    'цветоч', 'композиц', 'отоплен', 'радиатор'
]

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

def get_goszakup_tenders():
    url = PLATFORMS["Госзакупки РК"]
    headers = {
        'User-Agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36'
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
                    
                    title_lower = title.lower()
                    if any(kw in title_lower for kw in KEYWORDS):
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
        return tenders[:5]
    except Exception as e:
        print(f"Ошибка парсинга госзакупок: {e}")
        return []

def send_tenders_to_chat(target_chat_id):
    if not bot:
        return
    
    tenders = get_goszakup_tenders()
    
    if not tenders:
        bot.send_message(target_chat_id, "📭 Новых актуальных лотов по вашим ключевым словам на основных порталах пока не найдено.")
        return

    for t in tenders:
        msg = (
            f"🎯 **Найден целевой тендер!**\n\n"
            f"🌐 **Платформа:** {t['platform']}\n"
            f"🔹 **№ лота:** `{t['num']}`\n"
            f"📝 **Предмет закупки:** {t['title']}\n"
            f"🏢 **Организатор:** {t['organizer']}\n"
            f"📋 **Способ:** {t['method']}\n"
            f"📅 **Начало приема:** {t['start_date']}\n"
            f"⏱ **Окончание приема:** {t['end_date']}\n"
            f"₸ **Сумма:** `{t['sum']} ₸`\n\n"
            f"🔗 [Перейти на торговую площадку]({t['link']})"
        )
        try:
            bot.send_message(target_chat_id, msg, parse_mode="Markdown", disable_web_page_preview=True)
            time.sleep(0.5)
        except Exception as e:
            print(f"Ошибка отправки сообщения: {e}")

if bot:
    @bot.message_handler(commands=['start', 'tenders'])
    def handle_start(message):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        btn_tenders = types.KeyboardButton("📋 Свежие тендеры")
        btn_platforms = types.KeyboardButton("🏛 Площадки РК")
        markup.add(btn_tenders, btn_platforms)
        
        bot.send_message(
            message.chat.id, 
            "Приветствую! Я ваш единый помощник по закупкам и бизнесу в Казахстане. Выберите действие:", 
            reply_markup=markup
        )

    @bot.message_handler(func=lambda message: message.text in ["Тендеры", "📋 Свежие тендеры"])
    def handle_button_tenders(message):
        bot.send_message(message.chat.id, "🔍 Сканирую официальные торговые площадки по ключевым словам...")
        send_tenders_to_chat(message.chat.id)

    @bot.message_handler(func=lambda message: message.text in ["Площадки РК", "🏛 Площадки РК"])
    def handle_button_platforms(message):
        text = "🏛 **Официальные реестры и площадки:**\n\n"
        for name, link in PLATFORMS.items():
            text += f"• [{name}]({link})\n"
        bot.send_message(message.chat.id, text, parse_mode="Markdown", disable_web_page_preview=True)

def background_checker():
    while True:
        try:
            if CHAT_ID and bot:
                send_tenders_to_chat(CHAT_ID)
        except Exception as e:
            print(f"Ошибка в фоновом цикле: {e}")
        time.sleep(7200) # Проверка каждые 2 часа

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
        print("TELEGRAM_BOT_TOKEN не задан. Работает только веб-сервер.")
        while True:
            time.sleep(3600)

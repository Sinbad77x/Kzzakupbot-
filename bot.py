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

bot = telebot.TeleBot(TOKEN)

URL = "https://goszakup.gov.kz/ru/search/announce"

# Список ваших ключевых слов (можно добавлять или изменять свои)
KEYWORDS = [
    'it', 'программ', 'компьютер', 'сайт', 'медицин', 'лекарств', 
    'строй', 'ремонт', 'услуг', 'обучен', 'посадк', 'саженц', 
    'цветоч', 'композиц', 'отоплен', 'радиатор'
]

class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Kzzakupbot is running!")

def run_server():
    server = HTTPServer(('0.0.0.0', PORT), SimpleHandler)
    server.serve_forever()

def format_date(date_str):
    # Автоматически разделяет слипшуюся дату и время пробелом
    return re.sub(r'(\d{4}-\d{2}-\d{2})(\d{2}:\d{2})', r'\1 \2', date_str)

def get_public_tenders():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36'
    }
    try:
        response = requests.get(URL, headers=headers, timeout=10)
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
                            'num': anno_num,
                            'title': title,
                            'organizer': organizer,
                            'method': method,
                            'start_date': start_date,
                            'end_date': end_date,
                            'sum': sum_val
                        })
        return tenders[:5]
    except Exception as e:
        print(f"Ошибка парсинга: {e}")
        return []

def send_tenders_to_chat(target_chat_id):
    tenders = get_public_tenders()
    if not tenders:
        bot.send_message(target_chat_id, "📭 Новых актуальных тендеров по вашим ключевым словам пока не найдено.")
        return

    for t in tenders:
        msg = (
            f"🎯 **Найден целевой тендер!**\n\n"
            f"🔹 **№ лота:** `{t['num']}`\n"
            f"📝 **Предмет закупки:** {t['title']}\n"
            f"🏢 **Организатор:** {t['organizer']}\n"
            f"📋 **Способ:** {t['method']}\n"
            f"📅 **Начало приема:** {t['start_date']}\n"
            f"⏱ **Окончание приема:** {t['end_date']}\n"
            f"₸ **Сумма:** `{t['sum']} ₸`\n\n"
            f"🔗 [Перейти на портал Госзакупок](https://goszakup.gov.kz/ru/search/announce)"
        )
        bot.send_message(target_chat_id, msg, parse_mode="Markdown", disable_web_page_preview=True)

@bot.message_handler(commands=['start', 'tenders'])
def handle_start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn = types.KeyboardButton("📋 Свежие тендеры")
    markup.add(btn)
    
    bot.send_message(
        message.chat.id, 
        "Привет! Нажмите кнопку ниже, чтобы проверить актуальные тендеры:", 
        reply_markup=markup
    )

@bot.message_handler(func=lambda message: message.text in ["Тендеры", "📋 Свежие тендеры"])
def handle_button_tenders(message):
    bot.send_message(message.chat.id, "🔍 Ищу свежие тендеры по списку ключевых слов...")
    send_tenders_to_chat(message.chat.id)

def background_checker():
    while True:
        try:
            if CHAT_ID:
                send_tenders_to_chat(CHAT_ID)
        except Exception as e:
            print(f"Ошибка в фоновом цикле: {e}")
        time.sleep(7200)

if __name__ == "__main__":
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    
    checker_thread = threading.Thread(target=background_checker, daemon=True)
    checker_thread.start()

    print("Telegram бот запущен и слушает команды...")
    bot.infinity_polling()

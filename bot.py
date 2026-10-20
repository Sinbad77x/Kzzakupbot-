import os
import time
import threading
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
KEYWORDS = ['it', 'программ', 'компьютер', 'сайт', 'медицин', 'лекарств', 'строй', 'ремонт', 'услуг', 'обучен', 'посадк', 'саженц', 'цветоч', 'композиц']

class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Kzzakupbot is running!")

def run_server():
    server = HTTPServer(('0.0.0.0', PORT), SimpleHandler)
    server.serve_forever()

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
                if len(cols) >= 4:
                    link_elem = row.find('a')
                    anno_num = link_elem.text.strip() if link_elem else cols[0].text.strip()
                    
                    # Собираем весь текст ячеек строки для умного анализа
                    cell_texts = [col.text.strip().replace('\n', ' ') for col in cols]
                    
                    title = ""
                    organizer = ""
                    method = ""
                    start_date = ""
                    end_date = ""
                    sum_val = "Не указана"
                    
                    # Ищем предмет закупки (обычно самая длинная ячейка или по ключевым словам)
                    for text in cell_texts:
                        cleaned = " ".join(text.split())
                        if any(kw in cleaned.lower() for kw in KEYWORDS):
                            title = cleaned
                            break
                    
                    if not title and len(cell_texts) > 1:
                        title = " ".join(cell_texts[1].split())

                    # Интеллектуальный поиск суммы, дат и организатора по содержимому
                    dates = []
                    for text in cell_texts:
                        # Поиск суммы (содержит цифры и запятые/точки, похожа на деньги)
                        if any(char.isdigit() for char in text) and ('₸' in text or '.' in text or ',' in text) and len(text) < 25 and not '-' in text[:5]:
                            sum_val = " ".join(text.split())
                        # Поиск дат (содержит года вроде 2026)
                        elif '2026' in text or '2027' in text:
                            dates.append(" ".join(text.split()))
                        elif "Запрос" in text or "Конкурс" in text or "Аукцион" in text or "Из одного источника" in text:
                            method = " ".join(text.split())
                        elif len(text) > 40 and "учреждение" in text.lower() or "аппарат" in text.lower() or "отдел" in text.lower():
                            organizer = " ".join(text.split())

                    if len(dates) >= 2:
                        start_date = dates[0]
                        end_date = dates[1]
                    elif len(dates) == 1:
                        start_date = dates[0]

                    if not organizer and len(cell_texts) > 2:
                        organizer = " ".join(cell_texts[2].split())

                    if not method and len(cell_texts) > 4:
                        method = " ".join(cell_texts[4].split())

                    title_lower = title.lower()
                    if any(kw in title_lower for kw in KEYWORDS):
                        tenders.append({
                            'num': anno_num,
                            'title': title,
                            'organizer': organizer,
                            'method': method,
                            'start_date': start_date or "Не указано",
                            'end_date': end_date or "Не указано",
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
            f"💰 **Сумма:** `{t['sum']}`\n\n"
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
            

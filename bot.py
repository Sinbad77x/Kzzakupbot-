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

# Заголовки для обхода простых анти-бот систем
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
}

# --- ФУНКЦИИ ПАРСИНГА С КАЖДОЙ ПЛОЩАДКИ ---

def fetch_goszakup():
    url = "https://goszakup.gov.kz/ru/search/announce"
    tenders = []
    try:
        res = requests.get(url, headers=HEADERS, timeout=12)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            rows = soup.select('table.table tbody tr')
            for row in rows:
                cols = row.find_all('td')
                if len(cols) >= 8:
                    link_elem = row.find('a')
                    num = link_elem.text.strip() if link_elem else cols[0].text.strip()
                    title = " ".join(cols[1].text.strip().split())
                    organizer = " ".join(cols[3].text.strip().split())
                    method = " ".join(cols[4].text.strip().split())
                    sum_val = " ".join(cols[7].text.strip().split())
                    link = link_elem['href'] if link_elem and 'href' in link_elem.attrs else url
                    
                    tenders.append({
                        'source': 'Госзакупки РК',
                        'num': num,
                        'title': title,
                        'organizer': organizer,
                        'method': method,
                        'sum': sum_val,
                        'link': link
                    })
    except Exception as e:
        print(f"Ошибка Госзакупки: {e}")
    return tenders[:6]

def fetch_generic(source_name, url):
    tenders = []
    try:
        res = requests.get(url, headers=HEADERS, timeout=12)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            # Ищем любые блоки с упоминанием лотов/закупок/таблиц
            blocks = soup.find_all(['tr', 'div', 'article'], class_=re.compile(r'(lot|tender|item|announce|card|row|list)', re.I))
            
            count = 1
            for b in blocks:
                text = " ".join(b.text.split())
                if len(text) > 30 and ("тендер" in text.lower() or "закуп" in text.lower() or "лот" in text.lower() or "№" in text):
                    a_tag = b.find('a')
                    href = a_tag['href'] if a_tag and 'href' in a_tag.attrs else url
                    if href.startswith('/'):
                        href = "/".join(url.split('/')[:3]) + href

                    tenders.append({
                        'source': source_name,
                        'num': f"Лот №{count}",
                        'title': text[:150] + "...",
                        'organizer': source_name,
                        'method': 'Открытые торги',
                        'sum': 'См. на площадке',
                        'link': href
                    })
                    count += 1
                if len(tenders) >= 5:
                    break
    except Exception as e:
        print(f"Ошибка {source_name}: {e}")
    return tenders

def get_tenders_by_platform(name):
    if name in ["🔥 Все новые лоты", "🏛 Госзакупки"]:
        return fetch_goszakup()
    elif name == "🏢 Самрук-Қазына":
        return fetch_generic("Самрук-Қазына", "https://zakup.sk.kz")
    elif name == "💊 СК-Фармация":
        return fetch_generic("СК-Фармация", "https://sk-pharmacy.kz")
    elif name == "🏥 ФСМС":
        return fetch_generic("ФСМС", "https://fms.kz")
    elif name == "🌐 Mitwork":
        return fetch_generic("Mitwork", "https://mitwork.kz")
    elif name == "🛒 Caspy Tender":
        return fetch_generic("Caspy Tender", "https://caspytender.kz")
    elif name == "📊 ETS-Тендер":
        return fetch_generic("ETS-Тендер", "https://ets-tender.kz")
    return []

def send_tenders_to_user(chat_id, platform_name):
    tenders = get_tenders_by_platform(platform_name)
    
    if not tenders:
        bot.send_message(
            chat_id, 
            f"⚠️ В данный момент новые лоты с площадки **{platform_name}** обновляются или сайт заблокировал автоматический запрос. Попробуйте еще раз через несколько минут.",
            parse_mode="Markdown"
        )
        return

    bot.send_message(chat_id, f"📋 **Найдено свежих лотов ({platform_name}): {len(tenders)}**")

    for t in tenders:
        msg = (
            f"🎯 **{t['source']}**\n"
            f"🔹 **Номер:** `{t['num']}`\n"
            f"📝 **Предмет:** {t['title']}\n"
            f"🏢 **Организатор:** {t['organizer']}\n"
            f"📋 **Способ:** {t['method']}\n"
            f"₸ **Сумма:** `{t['sum']}`\n\n"
            f"🔗 [Перейти к объявлению]({t['link']})"
        )
        try:
            bot.send_message(chat_id, msg, parse_mode="Markdown", disable_web_page_preview=True)
            time.sleep(0.3)
        except Exception as e:
            print(f"Ошибка отправки сообщения: {e}")

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
            "Выберите площадку из меню ниже для просмотра свежих объявлений прямо в боте:", 
            reply_markup=markup
        )

    @bot.message_handler(func=lambda message: message.text in [
        "🔥 Все новые лоты", "🏛 Госзакупки", "🏢 Самрук-Қазына", 
        "💊 СК-Фармация", "🏥 ФСМС", "🌐 Mitwork", "🛒 Caspy Tender", "📊 ETS-Тендер"
    ])
    def handle_platform_click(message):
        name = message.text
        bot.send_message(message.chat.id, f"🔍 Сканирую {name} и загружаю свежие лоты...")
        send_tenders_to_user(message.chat.id, name)

if __name__ == "__main__":
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    
    if bot:
        print("Telegram бот запущен...")
        bot.infinity_polling(timeout=60, long_polling_timeout=60)
    else:
        while True:
            time.sleep(3600)

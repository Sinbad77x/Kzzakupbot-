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

def format_date(date_str):
    return re.sub(r'(\d{4}-\d{2}-\d{2})(\d{2}:\d{2})', r'\1 \2', date_str)

# --- ПАРСЕРЫ ПЛОЩАДОК ---

def parse_goszakup(limit=5):
    url = "https://goszakup.gov.kz/ru/search/announce"
    headers = {'User-Agent': 'Mozilla/5.0'}
    tenders = []
    try:
        res = requests.get(url, headers=headers, timeout=10)
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
                    sum_val = " ".join(cols[7].text.strip().split())
                    tenders.append({
                        'num': num, 'title': title, 'organizer': organizer, 'sum': sum_val, 'link': url
                    })
    except Exception as e:
        print(f"Goszakup error: {e}")
    return tenders[:limit]

def parse_generic_platform(platform_name, url, limit=5):
    headers = {'User-Agent': 'Mozilla/5.0'}
    tenders = []
    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            # Поиск объявлений, лотов и карточек на странице
            items = soup.find_all(['div', 'tr', 'article'], class_=re.compile(r'(tender|lot|item|announce|card|row)', re.I))
            for idx, item in enumerate(items):
                text = " ".join(item.text.split())
                if len(text) > 20:
                    link_tag = item.find('a')
                    link = link_tag['href'] if link_tag and 'href' in link_tag.attrs else url
                    if link.startswith('/'):
                        domain = "/".join(url.split('/')[:3])
                        link = domain + link
                    
                    tenders.append({
                        'num': f"№{idx+1}",
                        'title': text[:120] + "..." if len(text) > 120 else text,
                        'organizer': platform_name,
                        'sum': 'Уточняется на портале',
                        'link': link
                    })
                if len(tenders) >= limit:
                    break
    except Exception as e:
        print(f"{platform_name} error: {e}")
    return tenders

def get_platform_tenders(platform_key):
    if platform_key == "🏛 Госзакупки":
        return parse_goszakup()
    elif platform_key == "🏢 Самрук-Қазына":
        return parse_generic_platform("Самрук-Қазына", "https://zakup.sk.kz")
    elif platform_key == "💊 СК-Фармация":
        return parse_generic_platform("СК-Фармация", "https://sk-pharmacy.kz")
    elif platform_key == "🏥 ФСМС":
        return parse_generic_platform("ФСМС", "https://fms.kz")
    elif platform_key == "🌐 Mitwork":
        return parse_generic_platform("Mitwork", "https://mitwork.kz")
    elif platform_key == "🛒 Caspy Tender":
        return parse_generic_platform("Caspy Tender", "https://caspytender.kz")
    elif platform_key == "📊 ETS-Тендер":
        return parse_generic_platform("ETS-Тендер", "https://ets-tender.kz")
    return []

def send_tenders(target_chat_id, platform_name):
    if not bot:
        return
    
    tenders = get_platform_tenders(platform_name)
    
    if not tenders:
        # Если автоматический парсер страницы вернул пустой список из-за скриптов/динамической загрузки
        text = (
            f"📢 **Площадка:** {platform_name}\n\n"
            f"Свежие публичные объявления проверяются напрямую.\n"
            f"🔗 [Открыть актуальный список лотов]({get_platform_url(platform_name)})"
        )
        bot.send_message(target_chat_id, text, parse_mode="Markdown", disable_web_page_preview=True)
        return

    bot.send_message(target_chat_id, f"📢 **Свежие закупки с площадки «{platform_name}»:**")

    for t in tenders:
        msg = (
            f"🎯 **Лоты и закупки**\n"
            f"🔹 **Обозначение:** `{t['num']}`\n"
            f"📝 **Предмет:** {t['title']}\n"
            f"🏢 **Организатор/Источник:** {t['organizer']}\n"
            f"₸ **Сумма:** `{t['sum']}`\n\n"
            f"🔗 [Перейти к лоту на портале]({t['link']})"
        )
        try:
            bot.send_message(target_chat_id, msg, parse_mode="Markdown", disable_web_page_preview=True)
            time.sleep(0.3)
        except Exception as e:
            print(f"Ошибка отправки: {e}")

def get_platform_url(key):
    urls = {
        "🏛 Госзакупки": "https://goszakup.gov.kz/ru/search/announce",
        "🏢 Самрук-Қазына": "https://zakup.sk.kz",
        "💊 СК-Фармация": "https://sk-pharmacy.kz",
        "🏥 ФСМС": "https://fms.kz",
        "🌐 Mitwork": "https://mitwork.kz",
        "🛒 Caspy Tender": "https://caspytender.kz",
        "📊 ETS-Тендер": "https://ets-tender.kz"
    }
    return urls.get(key, "https://goszakup.gov.kz")

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
            "Выберите интересующую площадку из меню ниже для мгновенного получения списка новых лотов:", 
            reply_markup=markup
        )

    @bot.message_handler(func=lambda message: message.text == "🔥 Все новые лоты")
    def handle_all_tenders(message):
        bot.send_message(message.chat.id, "🔍 Сканирую портал Госзакупок...")
        send_tenders(message.chat.id, "🏛 Госзакупки")

    @bot.message_handler(func=lambda message: message.text in [
        "🏛 Госзакупки", "🏢 Самрук-Қазына", "💊 СК-Фармация", 
        "🏥 ФСМС", "🌐 Mitwork", "🛒 Caspy Tender", "📊 ETS-Тендер"
    ])
    def handle_platform_click(message):
        name = message.text
        bot.send_message(message.chat.id, f"🔍 Получаю свежие закупки с площадки {name}...")
        send_tenders(message.chat.id, name)

if __name__ == "__main__":
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    
    if bot:
        print("Telegram бот слушает команды...")
        bot.infinity_polling(timeout=60, long_polling_timeout=60)
    else:
        while True:
            time.sleep(3600)

import os
import time
import threading
import requests
from http.server import HTTPServer, BaseHTTPRequestHandler
from bs4 import BeautifulSoup

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
PORT = int(os.environ.get("PORT", 10000))

URL = "https://goszakup.gov.kz/ru/search/announce"
KEYWORDS = ['it', 'программ', 'компьютер', 'сайт', 'медицин', 'лекарств', 'строй', 'ремонт', 'услуг', 'обучен']

# Заглушка веб-сервера, чтобы Render был доволен и не выключал приложение
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
                    
                    raw_text = cols[1].text.strip().replace('\n', ' ')
                    title = " ".join(raw_text.split())
                    
                    organizer = cols[2].text.strip().replace('\n', ' ')
                    organizer = " ".join(organizer.split())
                    
                    sum_val = cols[3].text.strip()
                    
                    title_lower = title.lower()
                    if any(kw in title_lower for kw in KEYWORDS):
                        tenders.append({
                            'num': anno_num,
                            'title': title,
                            'organizer': organizer,
                            'sum': sum_val
                        })
        return tenders[:5]
    except Exception as e:
        print(f"Ошибка парсинга: {e}")
        return []

def send_to_telegram():
    tenders = get_public_tenders()
    if not tenders:
        print("Новых лотов по вашим ключевым словам не найдено.")
        return

    for t in tenders:
        msg = (
            f"🎯 **Найден целевой тендер!**\n\n"
            f"🔹 **№ лота:** `{t['num']}`\n"
            f"📝 **Предмет закупки:** {t['title']}\n"
            f"🏢 **Заказчик/Организатор:** {t['organizer']}\n"
            f"💰 **Сумма:** `{t['sum']} ₸`\n\n"
            f"🔗 [Перейти на портал Госзакупок](https://goszakup.gov.kz/ru/search/announce)"
        )
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        payload = {
            "chat_id": CHAT_ID,
            "text": msg,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True
        }
        requests.post(url, json=payload)

def bot_loop():
    print("Бот запущен и работает в фоновом режиме...")
    while True:
        try:
            send_to_telegram()
        except Exception as e:
            print(f"Ошибка в цикле: {e}")
        time.sleep(7200)

if __name__ == "__main__":
    # Запускаем веб-сервер в отдельном потоке (нужно для Render)
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    
    # Запускаем бесконечный цикл бота
    bot_loop()

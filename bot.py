import os
import requests
from bs4 import BeautifulSoup

# Данные берутся из секретов GitHub Actions (безопасно)
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

URL = "https://goszakup.gov.kz/ru/search/announce"

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
            
            for row in rows[:3]:  # Берем первые 3 лота
                cols = row.find_all('td')
                if len(cols) >= 4:
                    anno_num = cols[0].text.strip()
                    title = cols[1].text.strip()
                    organizer = cols[2].text.strip()
                    sum_val = cols[3].text.strip()
                    
                    tenders.append({
                        'num': anno_num,
                        'title': title,
                        'organizer': organizer,
                        'sum': sum_val
                    })
        return tenders
    except Exception as e:
        print(f"Ошибка: {e}")
        return []

def send_to_telegram():
    tenders = get_public_tenders()
    if not tenders:
        print("Лоты не найдены.")
        return

    for t in tenders:
        msg = (
            f"📌 **Новый тендер РК (Госзакупки)**\n\n"
            f"🔹 **№:** {t['num']}\n"
            f"🔹 **Наименование:** {t['title']}\n"
            f"🔹 **Заказчик:** {t['organizer']}\n"
            f"💰 **Сумма:** {t['sum']}\n\n"
            f"🔗 [Перейти на портал](https://goszakup.gov.kz/ru/search/announce)"
        )
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        payload = {
            "chat_id": CHAT_ID,
            "text": msg,
            "parse_mode": "Markdown"
        }
        requests.post(url, json=payload)

if __name__ == "__main__":
    send_to_telegram()
  

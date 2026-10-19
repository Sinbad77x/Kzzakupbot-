import os
import requests
from bs4 import BeautifulSoup

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

URL = "https://goszakup.gov.kz/ru/search/announce"

def get_category_icon(title):
    title_lower = title.lower()
    if any(w in title_lower for w in ['it', 'программ', 'компьютер', 'сайт', 'по икт', 'поу', 'связь']):
        return "💻 IT и Оргтехника"
    elif any(w in title_lower for w in ['медицин', 'лекарств', 'больниц', 'фарм', 'препарат']):
        return "🏥 Медицина и Здоровье"
    elif any(w in title_lower for w in ['строй', 'ремонт', 'здани', 'сооружен', 'дорог', 'жилищ']):
        return "🏗️ Строительство и Недвижимость"
    elif any(w in title_lower for w in ['обучен', 'учебы', 'школ', 'курс', 'услуг']):
        return "📚 Услуги и Обучение"
    else:
        return "📦 Общая закупка"

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
            
            for row in rows[:3]:
                cols = row.find_all('td')
                if len(cols) >= 4:
                    link_elem = row.find('a')
                    anno_num = link_elem.text.strip() if link_elem else cols[0].text.strip()
                    
                    # Пытаемся вытащить ID из атрибута href ссылки на объявление
                    tender_link = "https://goszakup.gov.kz/ru/search/announce"
                    if link_elem and link_elem.has_attr('href'):
                        href = link_elem['href']
                        # Если в ссылке содержится ID объявления, формируем прямую ссылку
                        if 'announce/index' in href or 'show' in href:
                            tender_link = href if href.startswith('http') else f"https://goszakup.gov.kz{href}"
                        else:
                            # Альтернативный поиск ссылки в строке
                            links = row.find_all('a', href=True)
                            for l in links:
                                if 'announce' in l['href']:
                                    h = l['href']
                                    tender_link = h if h.startswith('http') else f"https://goszakup.gov.kz{h}"
                                    break

                    raw_text = cols[1].text.strip().replace('\n', ' ')
                    title = " ".join(raw_text.split())
                    
                    organizer = cols[2].text.strip().replace('\n', ' ')
                    organizer = " ".join(organizer.split())
                    
                    sum_val = cols[3].text.strip()
                    category = get_category_icon(title)
                    
                    tenders.append({
                        'num': anno_num,
                        'title': title,
                        'organizer': organizer,
                        'sum': sum_val,
                        'category': category,
                        'link': tender_link
                    })
        return tenders
    except Exception as e:
        print(f"Ошибка парсинга: {e}")
        return []

def send_to_telegram():
    tenders = get_public_tenders()
    if not tenders:
        print("Лоты не найдены.")
        return

    for t in tenders:
        msg = (
            f"📌 **Новый лот РК** [{t['category']}]\n\n"
            f"🔹 **№ лота:** `{t['num']}`\n"
            f"📝 **Предмет закупки:** {t['title']}\n"
            f"🏢 **Заказчик/Организатор:** {t['organizer']}\n"
            f"💰 **Сумма:** `{t['sum']} ₸`\n\n"
            f"🔗 [Открыть этот лот на портале]({t['link']})"
        )
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        payload = {
            "chat_id": CHAT_ID,
            "text": msg,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True
        }
        requests.post(url, json=payload)

if __name__ == "__main__":
    send_to_telegram()
                                

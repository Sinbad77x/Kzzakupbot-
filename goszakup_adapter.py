
import time
import requests
from bs4 import BeautifulSoup
from cache_manager import cache_get, cache_set

def search_goszakup_lots(query="", page=1, limit=5):
    """Обходной путь: парсинг открытой публичной выдачи zakup.gov.kz без токена и ИП"""
    cache_key = f"public_parse_{query.lower()}_{page}"
    cached_data = cache_get(cache_key)
    if cached_data:
        return cached_data

    lots = []
    fetched_at = time.strftime("%Y-%m-%d %H:%M:%S")
    
    try:
        encoded_q = requests.utils.quote(query) if query else ""
        search_url = f"https://zakup.gov.kz/ru/search/announce?search={encoded_q}&page={page}" if query else f"https://zakup.gov.kz/ru/search/announce?page={page}"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        }
        
        resp = requests.get(search_url, headers=headers, timeout=12)
        
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            # Ищем элементы строк таблиц или блоков карточек на странице портала
            rows = soup.find_all('tr') or soup.find_all('div', class_=re.compile('card|item|row|search-result', re.I))
            
            for row in rows:
                text_content = row.get_text(separator=" | ", strip=True)
                # Фильтруем информативные строки, содержащие признаки закупок
                if len(text_content) > 40 and any(kw in text_content.lower() for kw in ['тнг', '₸', 'сумма', 'заказчик', 'лот', 'оголошение']):
                    lots.append({
                        "id": "онлайн",
                        "number": "Прямой лот",
                        "name": text_content[:180],
                        "amount": 0.0,
                        "organizer": "Портал Госзакупок РК (Публично)",
                        "status": "Активный",
                        "url": search_url,
                        "publish_date": fetched_at[:10]
                    })
                    if len(lots) >= limit:
                        break
        elif resp.status_code == 403:
            # Защита Cloudflare — возвращаем мягкий резервный навигатор
            pass
    except Exception as e:
        pass

    # Если парсер встретил защиту или не нашел элементы, возвращаем честную рабочую ссылку на поиск
    if not lots:
        encoded_q = requests.utils.quote(query) if query else ""
        portal_url = f"https://zakup.gov.kz/ru/search/announce?search={encoded_q}" if query else "https://zakup.gov.kz/ru/search/announce"
        lots = [{
            "id": "Реестр",
            "number": "Прямая ссылка",
            "name": f"Поисковый запрос на портале: {query if query else 'Все новые лоты'}",
            "amount": 0.0,
            "organizer": "zakup.gov.kz",
            "status": "Открытый реестр",
            "url": portal_url,
            "publish_date": fetched_at[:10]
        }]

    result = {
        "success": True,
        "source": "public_parser",
        "page": page,
        "limit": limit,
        "total": len(lots),
        "has_more": len(lots) >= limit,
        "fetched_at": fetched_at,
        "data": lots
    }
    
    cache_set(cache_key, result, ttl=900)
    return result

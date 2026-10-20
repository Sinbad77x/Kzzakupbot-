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

KEYWORDS = [
    'it', 'программ', 'компьютер', 'сайт', 'медицин', 'лекарств', 
    'строй', 'ремонт', 'услуг', 'обучен', 'посадк', 'саженц', 
    'цветоч', 'композиц', 'отоплен', 'радиатор'
]

HTML_PAGE = """<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Kzzakupbot — Портал мониторинга госзакупок и инструкций РК</title>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        :root {
            --primary: #1e3a8a;
            --primary-light: #3b82f6;
            --accent: #06b6d4;
            --bg-dark: #0f172a;
            --card-bg: #1e293b;
            --text-light: #f8fafc;
            --text-muted: #94a3b8;
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
        }

        body {
            background-color: var(--bg-dark);
            color: var(--text-light);
            line-height: 1.6;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
        }

        header {
            background: linear-gradient(135deg, #1e1b4b 0%, #0f172a 100%);
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
            padding: 20px 0;
        }

        .container {
            max-width: 1100px;
            margin: 0 auto;
            padding: 0 20px;
        }

        .navbar {
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .logo {
            font-size: 24px;
            font-weight: 700;
            color: #fff;
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .logo i {
            color: var(--accent);
        }

        .status-badge {
            background: rgba(16, 185, 129, 0.15);
            color: #10b981;
            border: 1px solid rgba(16, 185, 129, 0.3);
            padding: 6px 14px;
            border-radius: 20px;
            font-size: 13px;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .status-dot {
            width: 8px;
            height: 8px;
            background-color: #10b981;
            border-radius: 50%;
            box-shadow: 0 0 8px #10b981;
        }

        .hero {
            padding: 50px 0 30px;
            text-align: center;
        }

        .hero h1 {
            font-size: 36px;
            font-weight: 800;
            margin-bottom: 15px;
            background: linear-gradient(to right, #ffffff, #93c5fd);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .hero p {
            font-size: 17px;
            color: var(--text-muted);
            max-width: 700px;
            margin: 0 auto 25px;
        }

        .btn-telegram {
            display: inline-flex;
            align-items: center;
            gap: 12px;
            background: linear-gradient(135deg, #2563eb, #0284c7);
            color: white;
            padding: 14px 32px;
            border-radius: 12px;
            text-decoration: none;
            font-weight: 700;
            font-size: 17px;
            box-shadow: 0 10px 25px -5px rgba(37, 99, 235, 0.4);
            transition: all 0.3s ease;
        }

        .btn-telegram:hover {
            transform: translateY(-2px);
            box-shadow: 0 15px 30px -5px rgba(37, 99, 235, 0.6);
        }

        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
            gap: 25px;
            margin: 30px 0;
        }

        .card {
            background: var(--card-bg);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 16px;
            padding: 25px;
        }

        .card-icon {
            width: 48px;
            height: 48px;
            background: rgba(59, 130, 246, 0.1);
            color: var(--primary-light);
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 20px;
            margin-bottom: 15px;
        }

        .card h3 {
            font-size: 19px;
            margin-bottom: 12px;
            color: #fff;
        }

        .card p {
            color: var(--text-muted);
            font-size: 14px;
            margin-bottom: 15px;
        }

        .step-list {
            list-style: none;
            padding: 0;
            margin: 0 0 15px 0;
        }

        .step-list li {
            position: relative;
            padding-left: 28px;
            margin-bottom: 10px;
            font-size: 14px;
            color: #cbd5e1;
        }

        .step-list li::before {
            content: "\f00c";
            font-family: "Font Awesome 6 Free";
            font-weight: 900;
            position: absolute;
            left: 0;
            color: var(--accent);
        }

        .auth-link-btn {
            display: block;
            text-align: center;
            background: rgba(59, 130, 246, 0.15);
            color: var(--primary-light);
            border: 1px solid rgba(59, 130, 246, 0.3);
            padding: 10px;
            border-radius: 8px;
            text-decoration: none;
            font-weight: 600;
            font-size: 14px;
            margin-top: 15px;
            transition: background 0.2s;
        }

        .auth-link-btn:hover {
            background: rgba(59, 130, 246, 0.25);
        }

        .course-item {
            display: flex;
            align-items: center;
            justify-content: space-between;
            background: rgba(15, 23, 42, 0.6);
            padding: 12px 16px;
            border-radius: 10px;
            margin-bottom: 10px;
            border: 1px solid rgba(255, 255, 255, 0.05);
        }

        .course-info h4 {
            font-size: 14px;
            color: #f1f5f9;
        }

        .course-info span {
            font-size: 12px;
            color: var(--accent);
        }

        .course-btn {
            color: var(--primary-light);
            text-decoration: none;
            font-size: 13px;
            font-weight: 600;
        }

        footer {
            margin-top: auto;
            border-top: 1px solid rgba(255, 255, 255, 0.08);
            padding: 20px 0;
            text-align: center;
            color: var(--text-muted);
            font-size: 13px;
            background: #090d16;
        }
    </style>
</head>
<body>

    <header>
        <div class="container navbar">
            <div class="logo">
                <i class="fa-solid fa-chart-line"></i> Kzzakupbot
            </div>
            <div class="status-badge">
                <div class="status-dot"></div>
                Сервер активен 24/7
            </div>
        </div>
    </header>

    <main class="container">
        <section class="hero">
            <h1>Мониторинг и Вход на Госзакупки РК</h1>
            <p>Автоматический поиск лотов, бесплатное обучение и руководства по авторизации на портале.</p>
            <a href="https://t.me/Kzzakupbot" target="_blank" class="btn-telegram">
                <i class="fa-brands fa-telegram"></i> Запустить Telegram-бота
            </a>
        </section>

        <section class="grid">
            <div class="card">
                <div class="card-icon"><i class="fa-solid fa-qrcode"></i></div>
                <h3>Быстрый вход по QR (eGov Mobile)</h3>
                <p>Вход без ключей ЭЦП и NCALayer с помощью смартфона:</p>
                <ul class="step-list">
                    <li>Нажмите кнопку ниже для перехода к QR-авторизации.</li>
                    <li>Откройте приложение <strong>eGov Mobile</strong> на телефоне.</li>
                    <li>Отсканируйте код и подтвердите вход по Face ID / Touch ID.</li>
                </ul>
                <a href="https://zakup.gov.kz/sso#qr" target="_blank" class="auth-link-btn" style="background: rgba(6, 182, 212, 0.2); border-color: var(--accent); color: #fff;">
                    <i class="fa-solid fa-qrcode"></i> Войти по QR-коду
                </a>
            </div>

            <div class="card">
                <div class="card-icon"><i class="fa-solid fa-key"></i></div>
                <h3>Вход по ЭЦП (NCALayer)</h3>
                <p>Классическая авторизация с помощью ключей ЭЦП:</p>
                <ul class="step-list">
                    <li>Запустите программу <strong>NCALayer</strong> на ПК.</li>
                    <li>Выберите модуль «Модуль Государственные закупки РК».</li>
                    <li>Выполните вход с помощью ключа AUTH.</li>
                </ul>
                <a href="https://zakup.gov.kz/sso" target="_blank" class="auth-link-btn">
                    <i class="fa-solid fa-key"></i> Войти по ЭЦП
                </a>
            </div>

            <div class="card" style="grid-column: 1 / -1;">
                <div class="card-icon"><i class="fa-solid fa-graduation-cap"></i></div>
                <h3>Обучение и Государственные Курсы</h3>
                <p>Полезные материалы и официальные программы подготовки для поставщиков:</p>
                
                <div class="course-item">
                    <div class="course-info">
                        <h4>Основы Госзакупок РК</h4>
                        <span>Skills Enbek • Курс №460</span>
                    </div>
                    <a href="https://skills.enbek.kz/ru/course-catalog/course/460" target="_blank" class="course-btn">Пройти курс <i class="fa-solid fa-arrow-right"></i></a>
                </div>

                <div class="course-item">
                    <div class="course-info">
                        <h4>Регламенты и инструкции Госзакупок</h4>
                        <span>Официальный портал РК</span>
                    </div>
                    <a href="https://goszakup.gov.kz" target="_blank" class="course-btn">Открыть <i class="fa-solid fa-arrow-right"></i></a>
                </div>
            </div>
        </section>
    </main>

    <footer>
        <div class="container">
            &copy; 2026 Kzzakupbot — Автоматизация поиска тендеров и обучение специалистов в Республики Казахстан.
        </div>
    </footer>

</body>
</html>
"""

class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(HTML_PAGE.encode('utf-8'))

def run_server():
    server = HTTPServer(('0.0.0.0', PORT), SimpleHandler)
    server.serve_forever()

def format_date(date_str):
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
            print(f"Ошибка в цикле: {e}")
        time.sleep(7200)

if __name__ == "__main__":
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    
    checker_thread = threading.Thread(target=background_checker, daemon=True)
    checker_thread.start()

    print("Telegram бот запущен и слушает команды...")
    bot.infinity_polling()

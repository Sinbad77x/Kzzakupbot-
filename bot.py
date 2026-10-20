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

# Безопасная инициализация бота
bot = None
if TOKEN:
    try:
        bot = telebot.TeleBot(TOKEN)
    except Exception as e:
        print(f"Ошибка инициализации Telegram бота: {e}")

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
    <title>Kzzakupbot — Портал Мониторинга Госзакупок РК и База Знаний</title>
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
            max-width: 750px;
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
            content: "\\f00c";
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

        .resource-item {
            display: flex;
            align-items: center;
            justify-content: space-between;
            background: rgba(15, 23, 42, 0.6);
            padding: 14px 18px;
            border-radius: 10px;
            margin-bottom: 12px;
            border: 1px solid rgba(255, 255, 255, 0.05);
        }

        .resource-info h4 {
            font-size: 15px;
            color: #f1f5f9;
            margin-bottom: 2px;
        }

        .resource-info span {
            font-size: 12px;
            color: var(--accent);
        }

        .resource-btn {
            color: var(--primary-light);
            text-decoration: none;
            font-size: 13px;
            font-weight: 600;
            white-space: nowrap;
            margin-left: 15px;
        }

        .resource-btn:hover {
            text-decoration: underline;
        }

        .calc-input {
            width: 100%;
            padding: 10px 14px;
            border-radius: 8px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            background: #0f172a;
            color: #fff;
            font-size: 15px;
            margin-bottom: 15px;
        }
        .calc-res-box {
            background: rgba(15, 23, 42, 0.8);
            padding: 15px;
            border-radius: 10px;
            border: 1px solid rgba(6, 182, 212, 0.2);
            margin-top: 10px;
        }
        .calc-res-item {
            display: flex;
            justify-content: space-between;
            font-size: 14px;
            margin-bottom: 8px;
            color: #cbd5e1;
        }
        .calc-res-item strong {
            color: var(--accent);
        }

        .comp-table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
        }
        .comp-table th, .comp-table td {
            padding: 12px 15px;
            text-align: left;
            border-bottom: 1px solid rgba(255, 255, 255, 0.08);
            font-size: 14px;
        }
        .comp-table th {
            background: rgba(15, 23, 42, 0.6);
            color: var(--accent);
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
            <h1>Умный Мониторинг и Инструменты Госзакупок РК</h1>
            <p>Автоматический поиск лотов, калькулятор маржинальности, пошаговые гайды, глоссарий и юридическая поддержка.</p>
            <a href="https://t.me/Kzzakupbot" target="_blank" class="btn-telegram">
                <i class="fa-brands fa-telegram"></i> Запустить Telegram-бота
            </a>
        </section>

        <section class="grid">

            <div class="card" style="grid-column: 1 / -1;">
                <div class="card-icon"><i class="fa-solid fa-calculator"></i></div>
                <h3>Интерактивный Калькулятор Расходов и Маржи</h3>
                <p>Введите запланированную сумму лота (в тенге) для автоматического расчета необходимых затрат:</p>
                <input type="number" id="lotSum" class="calc-input" placeholder="Введите сумму лота (например: 5000000)" oninput="calculateMargin()">
                <div class="calc-res-box">
                    <div class="calc-res-item">
                        <span>Обеспечение заявки (1%):</span>
                        <strong id="garantVal">0 ₸</strong>
                    </div>
                    <div class="calc-res-item">
                        <span>Обеспечение исполнения договора (3%):</span>
                        <strong id="contractVal">0 ₸</strong>
                    </div>
                    <div class="calc-res-item">
                        <span>Примерные налоги и сборы (~10%):</span>
                        <strong id="taxVal">0 ₸</strong>
                    </div>
                </div>
            </div>

            <div class="card">
                <div class="card-icon"><i class="fa-solid fa-list-check"></i></div>
                <h3>Гайд: Как новичку зайти в тендеры</h3>
                <ul class="step-list">
                    <li><strong>1. Получение ЭЦП:</strong> Оформите ЭЦП в ЦОНе или на pki.gov.kz.</li>
                    <li><strong>2. Регистрация:</strong> Зарегистрируйтесь на goszakup.gov.kz или Самрук-Казына.</li>
                    <li><strong>3. Гарантийный взнос:</strong> Внесите 1% обеспечения на электронный кошелек.</li>
                    <li><strong>4. Подача заявки:</strong> Подготовьте техспецификацию и отправьте цену.</li>
                </ul>
            </div>

            <div class="card">
                <div class="card-icon"><i class="fa-solid fa-bolt"></i></div>
                <h3>Почему выбирают KzZakupBot</h3>
                <table class="comp-table">
                    <thead>
                        <tr>
                            <th>Параметр</th>
                            <th>KzZakupBot</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td>Скорость</td>
                            <td><span style="color:#10b981;">Мгновенно в Telegram</span></td>
                        </tr>
                        <tr>
                            <td>Экономия времени</td>
                            <td><span style="color:#10b981;">До 3 часов в день</span></td>
                        </tr>
                        <tr>
                            <td>Фильтрация</td>
                            <td>Точно по ключевым словам</td>
                        </tr>
                    </tbody>
                </table>
            </div>

            <div class="card">
                <div class="card-icon"><i class="fa-solid fa-qrcode"></i></div>
                <h3>Быстрый вход по QR (eGov Mobile)</h3>
                <p>Вход на портал без использования флешки и ключей ЭЦП:</p>
                <a href="https://zakup.gov.kz/sso#qr" target="_blank" class="auth-link-btn" style="background: rgba(6, 182, 212, 0.2); border-color: var(--accent); color: #fff;">
                    <i class="fa-solid fa-qrcode"></i> Войти по QR-коду
                </a>
            </div>

            <div class="card">
                <div class="card-icon"><i class="fa-solid fa-key"></i></div>
                <h3>Вход по ЭЦП (NCALayer)</h3>
                <p>Классическая авторизация через программу NCALayer на ПК:</p>
                <a href="https://zakup.gov.kz/sso" target="_blank" class="auth-link-btn">
                    <i class="fa-solid fa-key"></i> Войти по ЭЦП
                </a>
            </div>

            <div class="card" style="grid-column: 1 / -1;">
                <div class="card-icon"><i class="fa-solid fa-shield-halved"></i></div>
                <h3>Реестр недобросовестных участников (РНУ) и Глоссарий</h3>
                <p>Как обезопасить свой бизнес от рисков и понимать профессиональные термины:</p>

                <div class="resource-item">
                    <div class="resource-info">
                        <h4>Что такое РНУ и как туда не попасть?</h4>
                        <span>Неуплата обеспечения, уклонение от договора, сорванные сроки поставки</span>
                    </div>
                </div>

                <div class="resource-item">
                    <div class="resource-info">
                        <h4>Глоссарий терминов</h4>
                        <span><strong>Демпинг:</strong> Снижение цены более чем на допустимый порог • <strong>ПКО:</strong> Предварительный квалификационный отбор • <strong>ЗЦП:</strong> Запрос ценовых предложений</span>
                    </div>
                </div>
            </div>

            <div class="card" style="grid-column: 1 / -1;">
                <div class="card-icon"><i class="fa-solid fa-scale-balanced"></i></div>
                <h3>Бесплатная Консультация и Защита Прав (НПП «Атамекен»)</h3>
                <p>Правовая и информационная поддержка предпринимателей в сфере тендеров:</p>

                <div class="resource-item">
                    <div class="resource-info">
                        <h4>Единый контакт-центр НПП «Атамекен»</h4>
                        <span>Бесплатный звонок по Казахстану: <strong>1432</strong></span>
                    </div>
                    <a href="tel:1432" class="resource-btn"><i class="fa-solid fa-phone"></i> Позвонить 1432</a>
                </div>

                <div class="resource-item">
                    <div class="resource-info">
                        <h4>Платформа "Government for Business" (G4B)</h4>
                        <span>Онлайн-база знаний и подачи запросов по тендерам</span>
                    </div>
                    <a href="https://services.atameken.kz" target="_blank" class="resource-btn">services.atameken.kz <i class="fa-solid fa-arrow-right"></i></a>
                </div>
            </div>

            <div class="card" style="grid-column: 1 / -1;">
                <div class="card-icon"><i class="fa-solid fa-book-open"></i></div>
                <h3>Законодательство и Обучение (2026)</h3>
                <p>Нормативные акты и государственные курсы:</p>

                <div class="resource-item">
                    <div class="resource-info">
                        <h4>Правила осуществления государственных закупок РК</h4>
                        <span>Параграф (PRG.kz) • Редакция 2026 года</span>
                    </div>
                    <a href="https://prg.kz/document/?doc_id=35520090" target="_blank" class="resource-btn">Читать документ <i class="fa-solid fa-arrow-right"></i></a>
                </div>

                <div class="resource-item">
                    <div class="resource-info">
                        <h4>Основы Государственных Закупок РК</h4>
                        <span>Skills Enbek • Курс №460</span>
                    </div>
                    <a href="https://skills.enbek.kz/ru/course-catalog/course/460" target="_blank" class="resource-btn">Пройти курс <i class="fa-solid fa-arrow-right"></i></a>
                </div>
            </div>

        </section>
    </main>

    <footer>
        <div class="container">
            &copy; 2026 Kzzakupbot — Поисковый сервис, аналитический калькулятор и консультационный центр РК.
        </div>
    </footer>

    <script>
        function calculateMargin() {
            var sum = parseFloat(document.getElementById('lotSum').value) || 0;
            var garant = sum * 0.01;
            var contract = sum * 0.03;
            var tax = sum * 0.10;

            document.getElementById('garantVal').innerText = garant.toLocaleString('ru-RU') + ' ₸';
            document.getElementById('contractVal').innerText = contract.toLocaleString('ru-RU') + ' ₸';
            document.getElementById('taxVal').innerText = tax.toLocaleString('ru-RU') + ' ₸';
        }
    </script>
</body>
</html>
"""

class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(HTML_PAGE.encode('utf-8'))

    def log_message(self, format, *args):
        return

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
      

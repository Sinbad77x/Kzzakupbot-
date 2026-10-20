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
    <title>Kzzakupbot — Единый портал закупок, маркетплейсов и сервисов РК</title>
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
            margin-top: 10px;
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
            padding: 12px 16px;
            border-radius: 10px;
            margin-bottom: 10px;
            border: 1px solid rgba(255, 255, 255, 0.05);
        }

        .resource-info h4 {
            font-size: 14px;
            color: #f1f5f9;
            margin-bottom: 2px;
        }

        .resource-info span {
            font-size: 11px;
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
            <h1>Единый Портал Закупок, Банков и Сервисов РК</h1>
            <p>Госзакупки, площадки квазигоссектора, коммерческие торги, маркетплейсы и финансовые инструменты в одном месте.</p>
            <a href="https://t.me/Kzzakupbot" target="_blank" class="btn-telegram">
                <i class="fa-brands fa-telegram"></i> Запустить Telegram-бота
            </a>
        </section>

        <section class="grid">

            <!-- 1. КАЛЬКУЛЯТОР МАРЖИНАЛЬНОСТИ -->
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

            <!-- 2. ВСЕ ПЛОЩАДКИ ЗАКУПОК И КВАЗИГОССЕКТОР -->
            <div class="card" style="grid-column: 1 / -1;">
                <div class="card-icon"><i class="fa-solid fa-network-wired"></i></div>
                <h3>Единый доступ к основным торговым площадкам РК</h3>
                <p>Официальные порталы государственных закупок, холдингов и недропользователей:</p>

                <div class="resource-item">
                    <div class="resource-info">
                        <h4>Государственные закупки РК</h4>
                        <span>Основной портал госзакупок (goszakup.gov.kz)</span>
                    </div>
                    <a href="https://goszakup.gov.kz" target="_blank" class="resource-btn">Перейти <i class="fa-solid fa-arrow-right"></i></a>
                </div>

                <div class="resource-item">
                    <div class="resource-info">
                        <h4>Портал закупок «Самрук-Қазына»</h4>
                        <span>Закупки фонда национального благосостояния (zakup.sk.kz)</span>
                    </div>
                    <a href="https://zakup.sk.kz" target="_blank" class="resource-btn">Перейти <i class="fa-solid fa-arrow-right"></i></a>
                </div>

                <div class="resource-item">
                    <div class="resource-info">
                        <h4>Портал «СК-Фармация» и ФСМС</h4>
                        <span>Закупки лекарственных средств и медицинских услуг</span>
                    </div>
                    <a href="https://sk-pharmacy.kz" target="_blank" class="resource-btn">Перейти <i class="fa-solid fa-arrow-right"></i></a>
                </div>

                <div class="resource-item">
                    <div class="resource-info">
                        <h4>Евразийский электронный портал</h4>
                        <span>Электронная площадка (mitwork.kz)</span>
                    </div>
                    <a href="https://mitwork.kz" target="_blank" class="resource-btn">Перейти <i class="fa-solid fa-arrow-right"></i></a>
                </div>
            </div>

            <!-- 3. ОБУЧЕНИЕ И БАЗА ЗНАНИЙ -->
            <div class="card" style="grid-column: 1 / -1;">
                <div class="card-icon"><i class="fa-solid fa-graduation-cap"></i></div>
                <h3>Бесплатное обучение тендерам и продажам в РК</h3>
                <p>Базовые курсы, официальные видеоинструкции площадок и разборы законов:</p>

                <div class="resource-item">
                    <div class="resource-info">
                        <h4>Центр электронных финансов (ЦЭФ)</h4>
                        <span>Видеоинструкции по настройке ЭЦП, NCALayer, актам и договорам</span>
                    </div>
                    <a href="https://www.youtube.com/results?search_query=%D0%A6%D0%B5%D0%BD%D1%82%D1%80+%D1%8D%D0%BB%D0%B5%D0%BA%D1%82%D1%80%D0%BE%D0%BD%D0%BD%D1%8B%D1%85+%D1%84%D0%B8%D0%BD%D0%B0%D0%BD%D1%81%D0%BE%D0%B2+%D0%B3%D0%BE%D1%81%D0%B7%D0%B0%D0%BA%D1%83%D0%BF%D0%BA%D0%B8" target="_blank" class="resource-btn">Смотреть YouTube <i class="fa-solid fa-arrow-right"></i></a>
                </div>

                <div class="resource-item">
                    <div class="resource-info">
                        <h4>Курс «Основы Госзакупок РК» (Skills Enbek)</h4>
                        <span>Государственный бесплатный онлайн-курс №460 с выдачей сертификата</span>
                    </div>
                    <a href="https://skills.enbek.kz/ru/course-catalog/course/460" target="_blank" class="resource-btn">Пройти курс <i class="fa-solid fa-arrow-right"></i></a>
                </div>

                <div class="resource-item">
                    <div class="resource-info">
                        <h4>Omarket.kz для поставщиков</h4>
                        <span>Руководство по быстрой выкладке товаров и прямым сделкам без конкурсов</span>
                    </div>
                    <a href="https://omarket.kz" target="_blank" class="resource-btn">omarket.kz <i class="fa-solid fa-arrow-right"></i></a>
                </div>
            </div>

            <!-- 4. ВНЕШНИЕ СЕРВИСЫ И ПРОВЕРКА КОНТРАГЕНТОВ -->
            <div class="card" style="grid-column: 1 / -1;">
                <div class="card-icon"><i class="fa-solid fa-shield-cat"></i></div>
                <h3>Полезные внешние сервисы и проверка бизнеса</h3>
                <p>Инструменты для проверки контрагентов, налогов и судебных дел:</p>

                <div class="resource-item">
                    <div class="resource-info">
                        <h4>ИС «ЭСФ» (Электронные счета-фактуры)</h4>
                        <span>Выписка и просмотр ЭСФ, проверка поставщиков</span>
                    </div>
                    <a href="https://esf.kgd.gov.kz" target="_blank" class="resource-btn">Использовать <i class="fa-solid fa-arrow-right"></i></a>
                </div>

                <div class="resource-item">
                    <div class="resource-info">
                        <h4>Судебный кабинет РК</h4>
                        <span>Проверка судебных дел и исков потенциальных партнеров</span>
                    </div>
                    <a href="https://office.sud.kz" target="_blank" class="resource-btn">Проверить <i class="fa-solid fa-arrow-right"></i></a>
                </div>

                <div class="resource-item">
                    <div class="resource-info">
                        <h4>Проверка признака «Плательщик НДС»</h4>
                        <span>Официальный сервис комитета госдоходов</span>
                    </div>
                    <a href="https://kgd.gov.kz/ru/services/nds_check" target="_blank" class="resource-btn">Проверить <i class="fa-solid fa-arrow-right"></i></a>
                </div>
            </div>

            <!-- 5. БАНКИ И МАРКЕТПЛЕЙСЫ -->
            <div class="card" style="grid-column: 1 / -1;">
                <div class="card-icon"><i class="fa-solid fa-building-columns"></i></div>
                <h3>Финансовые экосистемы и маркетплейсы</h3>
                <p>Банковские гарантии, счета для бизнеса и розничные продажи:</p>

                <div class="resource-item">
                    <div class="resource-info">
                        <h4>Freedom Bank</h4>
                        <span>Цифровые тендерные гарантии и кредиты для бизнеса (bankffin.kz)</span>
                    </div>
                    <a href="https://bankffin.kz" target="_blank" class="resource-btn">Сайт <i class="fa-solid fa-arrow-right"></i></a>
                </div>

                <div class="resource-item">
                    <div class="resource-info">
                        <h4>Halyk Bank (Halyk Business)</h4>
                        <span>Спецсчета для госзакупок и расчетные счета (halykbank.kz)</span>
                    </div>
                    <a href="https://halykbank.kz/business" target="_blank" class="resource-btn">Сайт <i class="fa-solid fa-arrow-right"></i></a>
                </div>

                <div class="resource-item">
                    <div class="resource-info">
                        <h4>Банк ЦентрКредит (BCC Business)</h4>
                        <span>Выгодные тарифы РКО и поддержка МСБ (bcc.kz)</span>
                    </div>
                    <a href="https://www.bcc.kz/business" target="_blank" class="resource-btn">Сайт <i class="fa-solid fa-arrow-right"></i></a>
                </div>

                <div class="resource-item">
                    <div class="resource-info">
                        <h4>Kaspi Магазин (Kaspi Pay)</h4>
                        <span>Продажа товаров физическим лицам в рассрочку и кредит</span>
                    </div>
                    <a href="https://kaspi.kz/merchant" target="_blank" class="resource-btn">Сайт <i class="fa-solid fa-arrow-right"></i></a>
                </div>
            </div>

            <!-- 6. ВХОД НА ПОРТАЛ -->
            <div class="card">
                <div class="card-icon"><i class="fa-solid fa-qrcode"></i></div>
                <h3>Вход на портал госзакупок</h3>
                <p>Быстрый доступ через QR или классический ЭЦП:</p>
                <a href="https://zakup.gov.kz/sso#qr" target="_blank" class="auth-link-btn" style="background: rgba(6, 182, 212, 0.2); border-color: var(--accent); color: #fff;">
                    <i class="fa-solid fa-qrcode"></i> Войти по QR (eGov Mobile)
                </a>
                <a href="https://zakup.gov.kz/sso" target="_blank" class="auth-link-btn">
                    <i class="fa-solid fa-key"></i> Войти по ЭЦП (NCALayer)
                </a>
            </div>

            <!-- 7. АНТИКОРРУПЦИОННАЯ СЛУЖБА И КОНТАКТЫ -->
            <div class="card">
                <div class="card-icon"><i class="fa-solid fa-phone-volume"></i></div>
                <h3>Горячие линии и Антикор</h3>
                <p>Защита прав предпринимателей и борьба с нарушениями:</p>

                <div class="resource-item">
                    <div class="resource-info">
                        <h4>Антикоррупционная служба</h4>
                        <span>Сообщить о коррупции и хищениях: <strong>1424</strong></span>
                    </div>
                    <a href="tel:1424" class="resource-btn"><i class="fa-solid fa-phone"></i> Позвонить</a>
                </div>

                <div class="resource-item">
                    <div class="resource-info">
                        <h4>НПП «Атамекен»</h4>
                        <span>Правовая поддержка бизнеса: <strong>1432</strong></span>
                    </div>
                    <a href="tel:1432" class="resource-btn"><i class="fa-solid fa-phone"></i> Позвонить</a>
                </div>
            </div>

        </section>
    </main>

    <footer>
        <div class="container">
            &copy; 2026 Kzzakupbot — Единый навигатор по закупкам, маркетплейсам и бизнес-сервисам РК.
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
                        })
        return tenders[:5]
    except Exception as e:
        print(f"Ошибка парсинга: {e}")
        return []

def send_tenders_to_chat(target_chat_id):
    if not bot:
        return
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
        try:
            bot.send_message(target_chat_id, msg, parse_mode="Markdown", disable_web_page_preview=True)
        except Exception as e:
            print(f"Ошибка отправки сообщения: {e}")

if bot:
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
            if CHAT_ID and bot:
                send_tenders_to_chat(CHAT_ID)
        except Exception as e:
            print(f"Ошибка в фоновом цикле: {e}")
        time.sleep(7200)

if __name__ == "__main__":
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    print(f"Веб-сервер запущен на порту {PORT}")
    
    if CHAT_ID and bot:
        checker_thread = threading.Thread(target=background_checker, daemon=True)
        checker_thread.start()

    if bot:
        print("Telegram бот слушает команды...")
        bot.infinity_polling(timeout=60, long_polling_timeout=60)
    else:
        print("TELEGRAM_BOT_TOKEN не задан. Работает только веб-сервер.")
        while True:
            time.sleep(3600)

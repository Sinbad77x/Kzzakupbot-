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
            <p>Госзакупки, официальные торговые площадки квазигоссектора, коммерческие торги и финансовые инструменты в одном месте.</p>
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

            <div class="card" style="grid-column: 1 / -1;">
                <div class="card-icon"><i class="fa-solid fa-network-wired"></i></div>
                <h3>Единый реестр торговых площадок и операторов РК</h3>
                <p>Прямой доступ к государственным и коммерческим электронным торговым площадкам:</p>

                <div class="resource-item">
                    <div class="resource-info">
                        <h4>Государственные закупки РК (goszakup.gov.kz)</h4>
                        <span>Основной портал государственных закупок</span>
                    </div>
                    <a href="https://goszakup.gov.kz" target="_blank" class="resource-btn">Открыть <i class="fa-solid fa-arrow-right"></i></a>
                </div>

                <div class="resource-item">
                    <div class="resource-info">
                        <h4>Портал закупок «Самрук-Қазына» (zakup.sk.kz)</h4>
                        <span>Фонд национального благосостояния</span>
                    </div>
                    <a href="https://zakup.sk.kz" target="_blank" class="resource-btn">Открыть <i class="fa-solid fa-arrow-right"></i></a>
                </div>

                <div class="resource-item">
                    <div class="resource-info">
                        <h4>Портал закупок ТОО «СК-Фармация»</h4>
                        <span>Единый дистрибьютор в сфере медицины и лекарств</span>
                    </div>
                    <a href="https://sk-pharmacy.kz" target="_blank" class="resource-btn">Открыть <i class="fa-solid fa-arrow-right"></i></a>
                </div>

                <div class="resource-item">
                    <div class="resource-info">
                        <h4>Фонд медицинского страхования (ФСМС)</h4>
                        <span>Закупки медицинских услуг</span>
                    </div>
                    <a href="https://fms.kz" target="_blank" class="resource-btn">Открыть <i class="fa-solid fa-arrow-right"></i></a>
                </div>

                <div class="resource-item">
                    <div class="resource-info">
                        <h4>Евразийский электронный портал (Mitwork)</h4>
                        <span>Электронная торговая площадка</span>
                    </div>
                    <a href="https://mitwork.kz" target="_blank" class="resource-btn">Открыть <i class="fa-solid fa-arrow-right"></i></a>
                </div>

                <div class="resource-item">
                    <div class="resource-info">
                        <h4>ЭТП «Caspy Tender» (Каспий Тендер)</h4>
                        <span>Коммерческие и корпоративные закупки</span>
                    </div>
                    <a href="https://caspy-tender.kz" target="_blank" class="resource-btn">Открыть <i class="fa-solid fa-arrow-right"></i></a>
                </div>

                <div class="resource-item">
                    <div class="resource-info">
                        <h4>ЭТП «ETS-Тендер»</h4>
                        <span>Электронная торговая площадка для бизнеса</span>
                    </div>
                    <a href="https://ets-tender.kz" target="_blank" class="resource-btn">Открыть <i class="fa-solid fa-arrow-right"></i></a>
                </div>
            </div>

            <div class="card" style="grid-column: 1 / -1;">
                <div class="card-icon"><i class="fa-solid fa-graduation-cap"></i></div>
                <h3>Бесплатное обучение тендерам и продажам в РК</h3>
                <p>Базовые курсы, официальные видеоинструкции площадок и разборы законов:</p>

                <div class="resource-item">
                    <div class="resource-info">
                        <h4>Центр электронных финансов (ЦЭФ)</h4>
                        <span>Видеоинструкции по настройке ЭЦП, NCALayer, актам и договорам</span>
                    </div>
                    <a href="https://www.youtube.com/results?search_query=Центр+электронных+финансов+госзакупки" target="_blank" class="resource-btn">Смотреть YouTube <i class="fa-solid fa-arrow-right"></i></a>
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
    

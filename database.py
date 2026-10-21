import sqlite3
from datetime import datetime

DB_NAME = "users_settings.db"

def init_db():
    """Инициализация таблиц базы данных."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Таблица пользователей
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active INTEGER DEFAULT 1
        )
    ''')

    # Таблица сохраненных поисковых фильтров (для Push-уведомлений)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_filters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            keywords TEXT,
            region TEXT DEFAULT 'all',
            budget_category TEXT DEFAULT 'all',
            ens_tru_code TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(user_id)
        )
    ''')

    # Таблица кэша лотов (для последующего парсинга/агрегации)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tenders_cache (
            tender_id TEXT PRIMARY KEY,
            title TEXT,
            organizer TEXT,
            sum_amount REAL,
            region TEXT,
            platform TEXT,
            url TEXT,
            published_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.commit()
    conn.close()

def add_or_update_user(user_id: int, username: str, first_name: str):
    """Регистрация или обновление данных пользователя."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO users (user_id, username, first_name)
        VALUES (?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            username=excluded.username,
            first_name=excluded.first_name,
            is_active=1
    ''', (user_id, username, first_name))
    conn.commit()
    conn.close()

def save_user_filter(user_id: int, region: str = 'all', budget: str = 'all', keywords: str = ''):
    """Сохранение фильтра поиска пользователя."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO user_filters (user_id, region, budget_category, keywords)
        VALUES (?, ?, ?, ?)
    ''', (user_id, region, budget, keywords))
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("База данных успешно инициализирована.")
  

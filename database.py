import sqlite3
import time

DB_NAME = 'kzzakupbot.db'

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Таблица пользователей
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            first_name TEXT,
            username TEXT,
            reg_date TEXT
        )
    ''')
    
    # Таблица тем сообщества
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS community_topics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            category TEXT NOT NULL,
            author_name TEXT NOT NULL,
            author_id TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            views_count INTEGER DEFAULT 0,
            reports_count INTEGER DEFAULT 0
        )
    ''')
    
    # Таблица жалоб на темы
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS community_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            topic_id INTEGER NOT NULL,
            reason TEXT NOT NULL,
            reporter_ip TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (topic_id) REFERENCES community_topics (id)
        )
    ''')
    
    conn.commit()
    conn.close()

def register_user(user_id, first_name, username, source):
    conn = get_db_connection()
    cursor = conn.cursor()
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute('''
        INSERT OR IGNORE INTO users (user_id, first_name, username, reg_date)
        VALUES (?, ?, ?, ?)
    ''', (user_id, first_name, username, now))
    conn.commit()
    conn.close()

def add_topic(title, content, category, author_name, author_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute('''
        INSERT INTO community_topics (title, content, category, author_name, author_id, status, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, 'pending', ?, ?)
    ''', (title, content, category, author_name, author_id, now, now))
    topic_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return topic_id

def get_published_topics(search="", category="", limit=10, offset=0, sort="newest"):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = "SELECT id, title, content, category, author_name, created_at, views_count FROM community_topics WHERE status = 'published'"
    params = []
    
    if search:
        query += " AND (title LIKE ? OR content LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%"])
        
    if category:
        query += " AND category = ?"
        params.append(category)
        
    if sort == "oldest":
        query += " ORDER BY created_at ASC"
    else:
        query += " ORDER BY created_at DESC"
        
    query += " LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_topic_by_id(topic_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM community_topics WHERE id = ?', (topic_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def add_report(topic_id, reason, reporter_ip):
    conn = get_db_connection()
    cursor = conn.cursor()
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute('''
        INSERT INTO community_reports (topic_id, reason, reporter_ip, created_at)
        VALUES (?, ?, ?, ?)
    ''', (topic_id, reason, reporter_ip, now))
    
    cursor.execute('UPDATE community_topics SET reports_count = reports_count + 1 WHERE id = ?', (topic_id,))
    conn.commit()
    conn.close()

def update_topic_status(topic_id, status):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE community_topics SET status = ?, updated_at = ? WHERE id = ?', 
                   (status, time.strftime("%Y-%m-%d %H:%M:%S"), topic_id))
    conn.commit()
    conn.close()

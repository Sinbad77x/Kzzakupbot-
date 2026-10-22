import sqlite3
import os

DB_NAME = "zakupbot.db"

def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                first_name TEXT,
                username TEXT,
                source TEXT DEFAULT 'direct',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()

def register_user(user_id, first_name, username, source='direct'):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO users (user_id, first_name, username, source)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                first_name=excluded.first_name,
                username=excluded.username
        ''', (user_id, first_name, username, source))
        conn.commit()

def get_traffic_stats():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT source, COUNT(*) as count 
            FROM users 
            GROUP BY source 
            ORDER BY count DESC
        ''')
        rows = cursor.fetchall()
        return {row['source']: row['count'] for row in rows}

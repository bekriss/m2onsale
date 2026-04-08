import sqlite3

DB_NAME = "apartments.db"

def create_tables():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_filters (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_user_id INTEGER UNIQUE,
        city TEXT,
        rooms INTEGER
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS apartments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source TEXT,
        title TEXT,
        location TEXT,
        price TEXT,
        rooms INTEGER,
        url TEXT UNIQUE
    )
    """)

    conn.commit()
    conn.close()

def save_user_filter(user_id, city, rooms):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
    INSERT OR REPLACE INTO user_filters (telegram_user_id, city, rooms)
    VALUES (?, ?, ?)
    """, (user_id, city, rooms))

    conn.commit()
    conn.close()

def get_user_filter(user_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("SELECT city, rooms FROM user_filters WHERE telegram_user_id = ?", (user_id,))
    result = cursor.fetchone()

    conn.close()
    return result

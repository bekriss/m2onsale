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

def save_apartment(apartment):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO apartments (source, title, location, price, rooms, url)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            apartment['source'],
            apartment['title'],
            apartment['location'],
            apartment['price'],
            apartment.get('rooms'),
            apartment['url']
        ))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()
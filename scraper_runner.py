import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from scraper_otodom import scrape_otodom
from database import DB_NAME, save_apartment, get_user_filter
import sqlite3
from aiogram import Bot
import os
from dotenv import load_dotenv

load_dotenv()
bot = Bot(token=os.getenv("BOT_TOKEN"))

async def send_apartments():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT telegram_user_id, city, rooms FROM user_filters")
    users = cursor.fetchall()
    cursor.execute("SELECT title, location, price, url FROM apartments")
    apartments = cursor.fetchall()
    conn.close()
for user_id, city, rooms in users:
        for title, location, price, url in apartments:
            if city.lower() in location.lower():
                msg = f"{title}\n{price}\nLocation: {location}\n{url}"
                try:
                    await bot.send_message(user_id, msg)
                except Exception as e:
                    print(f"Error sending to {user_id}: {e}")

async def scrape_and_send():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT telegram_user_id, city, rooms FROM user_filters")
    users = cursor.fetchall()
    conn.close()

    total_new = 0
    for user_id, city, rooms in users:
        results = scrape_otodom(city=city, min_rooms=rooms)
        for apt in results:
            if save_apartment(apt):
                total_new += 1
    print(f"{total_new} new apartments saved.")

    await send_apartments()

def start_scheduler():
    scheduler = AsyncIOScheduler()
    scheduler.add_job(lambda: asyncio.create_task(scrape_and_send()), "interval", minutes=60)
    scheduler.start()
    print("Scheduler started, scraping every 60 minutes.")

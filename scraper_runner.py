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

# Define start_scheduler
def start_scheduler():
    scheduler = AsyncIOScheduler()
    scheduler.add_job(lambda: asyncio.create_task(scrape_and_send()), "interval", minutes=60)
    scheduler.start()
    print("Scheduler started, scraping every 60 minutes")

# Define scraping function
async def scrape_and_send():
    # Your scraping + sending code here...
    pass
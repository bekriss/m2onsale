from aiogram import Bot, Dispatcher
from dotenv import load_dotenv
import asyncio
import os

from handlers import router
from database import create_tables
from scraper_runner import start_scheduler  # <-- import

load_dotenv()

bot = Bot(token=os.getenv("BOT_TOKEN"))
dp = Dispatcher()

dp.include_router(router)

async def main():
    create_tables()
    start_scheduler()  # <-- start the scraping scheduler
    print("Bot started")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
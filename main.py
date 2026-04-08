from aiogram import Bot, Dispatcher
from dotenv import load_dotenv
import asyncio
import os

from handlers import router
from database import create_tables

load_dotenv()

bot = Bot(token=os.getenv("BOT_TOKEN"))
dp = Dispatcher()

dp.include_router(router)

async def main():
    create_tables()
    print("Bot started")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

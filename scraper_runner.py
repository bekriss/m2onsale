from scraper_runner import start_scheduler

async def main():
    create_tables()
    start_scheduler()  # <- start automatic scraping
    print("Bot started")
    await dp.start_polling(bot)
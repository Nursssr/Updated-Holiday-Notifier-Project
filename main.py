import asyncio
from scheduler import start_scheduler
from bot import dp, bot

async def main():
    start_scheduler()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
import asyncio
from db import async_session, init_db
from models import Holiday

HOLIDAYS = [
    ("Новый год", 1, 1),
    ("Международный женский день", 8, 3),
    ("Наурыз мейрамы", 21, 3),
    ("День единства народа Казахстана", 1, 5),
    ("День Защитника Отечества", 7, 5),
    ("День победы", 9, 5),
    ("День столицы", 6, 7),
    ("День Конституции", 30, 8),
    ("День Республики", 25, 10),
    ("День независимости", 16, 12),
]

async def seed():
    await init_db()
    async with async_session() as session:
        for name, day, month in HOLIDAYS:
            holiday = Holiday(name=name, day=day, month=month)
            session.add(holiday)
        await session.commit()
        print("Holidays seeded!")

if __name__ == "__main__":
    asyncio.run(seed())

import asyncio
from datetime import date

from sqlalchemy import select
from db import async_session, init_db
from models import Holiday

async def add_today_holiday(name: str):
    await init_db()  # создаёт таблицы, если их нет
    today = date.today()
    async with async_session() as session:
        # Проверяем, есть ли уже такой праздник сегодня
        result = await session.execute(
            select(Holiday).where(Holiday.day == today.day, Holiday.month == today.month, Holiday.name == name)
        )
        existing = result.scalar_one_or_none()
        if existing:
            print(f"Праздник '{name}' на сегодня уже есть в базе.")
            return

        # Добавляем праздник
        holiday = Holiday(name=name, day=today.day, month=today.month)
        session.add(holiday)
        await session.commit()
        print(f"Добавлен праздник: '{name}' на {today}")

if __name__ == "__main__":
    import sys
    name = "Тестовый праздник"
    if len(sys.argv) > 1:
        name = " ".join(sys.argv[1:])
    asyncio.run(add_today_holiday(name))

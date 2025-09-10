import asyncio
from db import async_session, engine, Base
from models import Holiday, HolidayTranslation

BIRTHDAY = {
    "translations": {
        "ru": "День рождения",
        "kk": "Туған күн",
        "en": "Birthday"
    }
}

HOLIDAYS = [
    {"day": 1, "month": 1, "translations": {"ru": "Новый год", "kk": "Жаңа жыл", "en": "New Year"}},
    {"day": 8, "month": 3, "translations": {"ru": "Международный женский день", "kk": "Халықаралық әйелдер күні", "en": "International Women’s Day"}},
    {"day": 21, "month": 3, "translations": {"ru": "Праздник Наурыз", "kk": "Наурыз Мейрамы", "en": "Nauryz"}},
    {"day": 1, "month": 5, "translations": {"ru": "День единства народа Казахстана", "kk": "Қазақстан халқының бірлігі күні", "en": "Day of Unity of the People of Kazakhstan"}},
    {"day": 7, "month": 5, "translations": {"ru": "День Защитника Отечества", "kk": "Отан қорғаушылар күні", "en": "Defender of the Fatherland Day"}},
    {"day": 9, "month": 5, "translations": {"ru": "День победы", "kk": "Жеңіс күні", "en": "Victory Day"}},
    {"day": 6, "month": 7, "translations": {"ru": "День столицы", "kk": "Астана күні", "en": "Capital Day"}},
    {"day": 30, "month": 8, "translations": {"ru": "День Конституции", "kk": "Конституция күні", "en": "Constitution Day"}},
    {"day": 25, "month": 10, "translations": {"ru": "День Республики", "kk": "Республика күні", "en": "Republic Day"}},
    {"day": 12, "month": 16, "translations": {"ru": "День независимости", "kk": "Тәуелсіздік күні", "en": "Independence Day"}},
]

async def seed():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as session:
        # создаём специальный «праздник» для ДР
        q = await session.execute(Holiday.__table__.select().where(Holiday.type == "birthday"))
        exists = q.first()

        if not exists:
            holiday = Holiday(day=0, month=0, type="birthday")
            session.add(holiday)
            await session.flush()

            for lang, name in BIRTHDAY["translations"].items():
                session.add(
                    HolidayTranslation(holiday_id=holiday.id, lang=lang, name=name)
                )

        # обычные праздники
        for h in HOLIDAYS:
            q = await session.execute(
                Holiday.__table__.select().where(
                    Holiday.day == h["day"],
                    Holiday.month == h["month"],
                    Holiday.scope == "kz"
                )
            )
            if q.first():
                continue

            holiday = Holiday(day=h["day"], month=h["month"], type=h.get("type", "regular"))
            session.add(holiday)
            await session.flush()

            for lang, name in h["translations"].items():
                session.add(
                    HolidayTranslation(holiday_id=holiday.id, lang=lang, name=name)
                )

        await session.commit()
    print("Holidays seeded (idempotent).")

if __name__ == "__main__":
    asyncio.run(seed())

import asyncio, os, pytz
from datetime import datetime, date, timezone
from sched import scheduler
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv
from sqlalchemy import select, and_
from db import async_session
from models import Holiday, User, Notification
from bot import bot

load_dotenv()

TIMEZONE = os.getenv("TIMEZONE", "Asia/Almaty")
SEND_HOUR_START = int(os.getenv("SEND_HOUR_START", 9))
SEND_HOUR_END = int(os.getenv("SEND_HOUR_END", 21))
BATCH_SIZE = int(os.getenv("BATCH_SIZE", 50))


async def send_notification(user, text):
    tasks = []

    #Telegram
    if getattr(user, "tg_id", None):
        tasks.append(bot.send_message(user.tg_id, text))

    #ВEmail, Push, SMS:
    #if getattr(user, "email", None):
    #    tasks.append(send_email(user.email, text))

    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)

async def send_holiday_notifications():
    tz = pytz.timezone(TIMEZONE)
    now = datetime.now(tz)
    if not (SEND_HOUR_START <= now.hour < SEND_HOUR_END):
        return

    today = date.today()
    async with async_session() as session:
        holidays_result = await session.execute(
            select(Holiday).where(
                and_(Holiday.day == today.day, Holiday.month == today.month)
            )
        )
        holidays = holidays_result.scalars().all()
        if not holidays:
            return

        for holiday in holidays:
            last_id = 0
            while True:
                result = await session.execute(
                    select(User)
                    .outerjoin(
                        Notification,
                        and_(
                            User.id == Notification.user_id,
                            Notification.holiday_id == holiday.id
                        )
                    )
                    .where(Notification.id == None, User.id > last_id)
                    .order_by(User.id)
                    .limit(BATCH_SIZE)
                )
                batch = result.scalars().all()
                if not batch:
                    break

                tasks = [send_notification(user, f"🎉 Поздравляем с праздником: {holiday.name}!") for user in batch]
                if tasks:
                    await asyncio.gather(*tasks)
                    await asyncio.sleep(0.3)

                notifications_to_add = [Notification(user_id=user.id, holiday_id=holiday.id) for user in batch]
                session.add_all(notifications_to_add)
                await session.commit()

                last_id = batch[-1].id


async def send_birthday_notifications():
    tz = pytz.timezone(TIMEZONE)
    now = datetime.now(tz)
    if not (SEND_HOUR_START <= now.hour < SEND_HOUR_END):
        return

    today_str = date.today().strftime("%m-%d")

    async with async_session() as session:
        last_id = 0
        while True:
            result = await session.execute(
                select(User)
                .outerjoin(
                    Notification,
                    and_(
                        User.id == Notification.user_id,
                        Notification.holiday_id == None
                    )
                )
                .where(User.birthday.isnot(None), Notification.id == None, User.id > last_id)
                .order_by(User.id)
                .limit(BATCH_SIZE)
            )
            batch = result.scalars().all()
            if not batch:
                break

            tasks = []
            notifications_to_add = []

            for user in batch:
                if user.birthday.strftime("%m-%d") != today_str:
                    continue

                tasks.append(send_notification(user, f"🎂 С Днём рождения, {user.name}! 🎉"))
                notifications_to_add.append(Notification(user_id=user.id, holiday_id=None))

            if tasks:
                await asyncio.gather(*tasks)
                await asyncio.sleep(0.3)

            if notifications_to_add:
                session.add_all(notifications_to_add)
                await session.commit()

            if batch:
                last_id = batch[-1].id
            else:
                break

def start_scheduler():
    schedular = AsyncIOScheduler(timezone=TIMEZONE)
    schedular.add_job(send_holiday_notifications, "cron", minute="*")
    schedular.add_job(send_birthday_notifications, "cron", minute="*")
    schedular.start()
    print("Scheduler started!")
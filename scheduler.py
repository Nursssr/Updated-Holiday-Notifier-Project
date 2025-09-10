import asyncio, os, pytz
from datetime import datetime, date, time
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv
from sqlalchemy import select, and_, delete
from sqlalchemy.orm import selectinload
from db import async_session
from models import Holiday, User, Notification
from bot import bot, _format_holiday_name, t

load_dotenv()

TIMEZONE = os.getenv("TIMEZONE", "Asia/Almaty")
SEND_HOUR_START = int(os.getenv("SEND_HOUR_START", 9))
SEND_HOUR_END = int(os.getenv("SEND_HOUR_END", 21))
BATCH_SIZE = int(os.getenv("BATCH_SIZE", 50))


async def send_notification(user, text):
    if getattr(user, "tg_id", None):
        try:
            await bot.send_message(user.tg_id, text)
        except Exception:
            pass


async def send_holiday_notifications():
    tz = pytz.timezone(TIMEZONE)
    now = datetime.now(tz)
    if not (SEND_HOUR_START <= now.hour < SEND_HOUR_END):
        return

    today = date.today()
    async with async_session() as session:
        # Подгружаем переводы вместе с праздниками (EAGER LOADING)
        holidays_result = await session.execute(
            select(Holiday)
            .options(selectinload(Holiday.translations))
            .where(and_(Holiday.day == today.day, Holiday.month == today.month))
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

                tasks = []
                for user in batch:
                    holiday_name = _format_holiday_name(holiday, user.lang)
                    tasks.append(send_notification(user, f"🎉 {holiday_name}!"))
                if tasks:
                    await asyncio.gather(*tasks)
                    await asyncio.sleep(0.3)

                session.add_all([
                    Notification(user_id=user.id, holiday_id=holiday.id)
                    for user in batch
                ])
                await session.commit()
                last_id = batch[-1].id

async def check_birthdays():
    today = date.today()

    async with async_session() as session:
        # 1. Получаем id специального праздника "birthday"
        q = await session.execute(
            select(Holiday).where(Holiday.type == "birthday")
        )
        birthday_holiday = q.scalar_one()

        # 2. Чистим уведомления для тех, у кого дата рождения стерта
        # (например, пользователь очистил свой ДР)
        await session.execute(
            delete(Notification).where(
                Notification.holiday_id == birthday_holiday.id,
                Notification.user_id.in_(
                    select(User.id).where(User.birthday.is_(None))
                )
            )
        )
        await session.commit()

        # 3. Ищем всех пользователей, у кого совпадает день и месяц
        q = await session.execute(
            select(User).where(User.birthday.isnot(None))
        )
        users = q.scalars().all()

        for user in users:
            if (
                user.birthday
                and user.birthday.day == today.day
                and user.birthday.month == today.month
            ):
                # 4. Проверяем — было ли уже уведомление сегодня
                qn = await session.execute(
                    select(Notification).where(
                        Notification.user_id == user.id,
                        Notification.holiday_id == birthday_holiday.id,
                        Notification.sent_at >= datetime.combine(today, time.min),
                    )
                )
                exists = qn.first()
                if exists:
                    continue  # уже было сегодня

                # 5. Отправляем сообщение
                text = t("birthday_notifications", user.lang, user=user)
                try:
                    await bot.send_message(user.tg_id, text)
                except Exception as e:
                    print(f"Ошибка отправки ДР пользователя {user.id}: {e}")
                    continue

                # 6. Записываем новое уведомление
                notif = Notification(
                    user_id=user.id,
                    holiday_id=birthday_holiday.id,
                    sent_at=datetime.now(),
                )
                session.add(notif)

        await session.commit()

def start_scheduler():
    scheduler = AsyncIOScheduler(timezone=TIMEZONE)
    scheduler.add_job(send_holiday_notifications, "cron", minute="*")
    scheduler.add_job(check_birthdays, "cron", minute="*")
    scheduler.start()
    print("Scheduler started!")
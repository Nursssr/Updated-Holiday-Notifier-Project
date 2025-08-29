import os
import re
from datetime import date
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart, Command
from dotenv import load_dotenv
from sqlalchemy import select
from db import async_session
from models import User

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(BOT_TOKEN)
dp = Dispatcher()


def _parse_birthday_arg(arg: str) -> date:
    if not arg:
        raise ValueError("Не указана дата")

    cleaned = re.sub(r"[\/\.\-]", ".", arg.strip())
    parts = [p for p in cleaned.split(".") if p]

    if len(parts) == 2:
        d, m = parts
        y = 2000
    elif len(parts) == 3:
        d, m, y = parts
        if len(y) == 2:
            y = int(y)
            y = 2000 + y
        else:
            y = int(y)
    else:
        raise ValueError("Ожидаю формат DD-MM или DD-MM-YYYY")

    d = int(d)
    m = int(m)

    return date(year=y, month=m, day=d)


async def _get_or_create_user(tg_id: int, full_name: str) -> User:
    async with async_session() as session:
        res = await session.execute(select(User).where(User.tg_id == tg_id))
        user = res.scalar_one_or_none()
        if user:
            return user
        user = User(tg_id=tg_id, name=full_name)
        session.add(user)
        await session.commit()
        return user


@dp.message(CommandStart())
async def start(message: types.Message):
    await _get_or_create_user(message.from_user.id, message.from_user.full_name)
    await message.answer(
        "Привет! ✅ Ты зарегистрирован.\n\n"
        "Доступные команды:\n"
        "/set_birthday 28-08-2000 — установить ДР (год можно не указывать)\n"
        "/my_birthday — показать сохранённый ДР\n"
        "/clear_birthday — удалить ДР\n"
        "/help — справка"
    )


@dp.message(Command("help"))
async def help_cmd(message: types.Message):
    await message.answer(
        "ℹ️ Как пользоваться:\n"
        "• /set_birthday 28-08-2000 — сохранить дату рождения (можно 28-08 без года)\n"
        "• Поддерживаемые разделители: '.', '-', '/'\n"
        "• /my_birthday — показать текущую дату рождения\n"
        "• /clear_birthday — удалить дату рождения\n\n"
        "Бот пришлёт поздравление, когда совпадут день и месяц. "
        "Отправка идёт только в дневные часы (см. .env)."
    )


@dp.message(Command("set_birthday"))
async def set_birthday(message: types.Message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Укажи дату: например, `/set_birthday 28-08-2000` или `/set_birthday 28-08`",
                             parse_mode="Markdown")
        return

    raw_date = parts[1].strip()
    try:
        bday = _parse_birthday_arg(raw_date)
    except ValueError as e:
        await message.answer(f"❌ Неверная дата. {e}\nПримеры: `28-08-2000`, `28.08`, `28/08/05`",
                             parse_mode="Markdown")
        return

    async with async_session() as session:
        res = await session.execute(select(User).where(User.tg_id == message.from_user.id))
        user = res.scalar_one_or_none()
        if not user:
            # на всякий случай создадим, если не прошёл /start
            user = User(tg_id=message.from_user.id, name=message.from_user.full_name)
            session.add(user)
            await session.flush()

        user.birthday = bday
        await session.commit()

    shown = bday.strftime("%d.%m")
    await message.answer(f"🎉 Дата рождения сохранена: {shown}")


@dp.message(Command("my_birthday"))
async def my_birthday(message: types.Message):
    async with async_session() as session:
        res = await session.execute(select(User).where(User.tg_id == message.from_user.id))
        user = res.scalar_one_or_none()

        if not user or not user.birthday:
            await message.answer("Дата рождения не установлена. Введи: `/set_birthday 28-08-2000`",
                                 parse_mode="Markdown")
            return

        shown = user.birthday.strftime("%d.%m")
        await message.answer(f"📅 Твоя дата рождения: {shown}")


@dp.message(Command("clear_birthday"))
async def clear_birthday(message: types.Message):
    async with async_session() as session:
        res = await session.execute(select(User).where(User.tg_id == message.from_user.id))
        user = res.scalar_one_or_none()

        if not user or not user.birthday:
            await message.answer("У тебя и так не сохранён ДР 🙂")
            return

        user.birthday = None
        await session.commit()
    await message.answer("🧹 Дата рождения удалена.")


# точка входа, если запускать файл напрямую (для автономного теста без main.py)
if __name__ == "__main__":
    import asyncio
    async def _run():
        print("Bot polling started…")
        await dp.start_polling(bot)
    asyncio.run(_run())

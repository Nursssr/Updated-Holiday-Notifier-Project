import os, re
from datetime import date
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart, Command
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from dotenv import load_dotenv
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from db import async_session
from models import User, Holiday

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(BOT_TOKEN)
dp = Dispatcher()

# Локализация (добавлены кнопки и тексты для меню)
MESSAGES = {
    "start": {
        "ru": "Привет! ✅ Ты зарегистрирован.",
        "kk": "Сәлем! ✅ Сен тіркелдің.",
        "en": "Hello! ✅ You are registered."
    },
    "help": {
        "ru": "ℹ️ Команды:\n/next_holidays — 3 ближайших праздника\n/holidays — ближайший праздник\n/set_birthday DD-MM[(-YYYY)]\n/my_birthday\n/clear_birthday\n/set_lang ru|kk|en",
        "kk": "ℹ️ Командалар:\n/next_holidays — 3 жақын мереке\n/holidays — жақын мереке\n/set_birthday DD-MM[(-YYYY)]\n/my_birthday\n/clear_birthday\n/set_lang ru|kk|en",
        "en": "ℹ️ Commands:\n/next_holidays — 3 upcoming holidays\n/holidays — next holiday\n/set_birthday DD-MM[(-YYYY)]\n/my_birthday\n/clear_birthday\n/set_lang ru|kk|en"
    },
    "lang_saved": {
        "ru": "✅ Язык сохранён: {lang}",
        "kk": "✅ Тіл сақталды: {lang}",
        "en": "✅ Language saved: {lang}"
    },

    # ДР
    "birthday_saved": {
        "ru": "🎂 Дата рождения сохранена: {date}",
        "kk": "🎂 Туған күн сақталды: {date}",
        "en": "🎂 Birthday saved: {date}"
    },
    "birthday_show": {
        "ru": "📅 Твоя дата рождения: {date}",
        "kk": "📅 Сенің туған күнің: {date}",
        "en": "📅 Your birthday: {date}"
    },
    "birthday_cleared": {
        "ru": "❌ Дата рождения удалена",
        "kk": "❌ Туған күн өшірілді",
        "en": "❌ Birthday cleared"
    },
    "birthday_not_set": {
        "ru": "⚠️ Дата рождения не установлена",
        "kk": "⚠️ Туған күн орнатылмаған",
        "en": "⚠️ Birthday not set"
    },

    #next holidays
    "holiday_today": {"ru": "🎉 Сегодня праздник: {name}!",
                      "kk": "🎉 Бүгін мереке: {name}!",
                      "en": "🎉 Today is holiday: {name}!"},
    "holiday_tomorrow": {"ru": "🎊 Завтра праздник: {name}!",
                         "kk": "🎊 Ертең мереке: {name}!",
                         "en": "🎊 Tomorrow is holiday: {name}!"},
    "holiday_future": {"ru": "⏳ До праздника «{name}» осталось {delta} {days_word}\n📅 {date}",
                       "kk": "⏳ «{name}» мерекесіне дейін {delta} {days_word} қалды\n📅 {date}",
                       "en": "⏳ {delta} {days_word} left until «{name}»\n📅 {date}"},
    "next_holidays_header": {"ru": "📅 Ближайшие праздники:",
                             "kk": "📅 Жақын мерекелер:",
                             "en": "📅 Upcoming holidays:"},
    "no_holidays": {"ru": "⚠️ Нет ближайших праздников",
                    "kk": "⚠️ Жақын мерекелер жоқ",
                    "en": "⚠️ No upcoming holidays"},

    # Кнопки главного меню
    "btn_holidays": {"ru": "📅 Праздники", "kk": "📅 Мерекелер", "en": "📅 Holidays"},
    "btn_next3": {"ru": "🗓️ 3 ближайших", "kk": "🗓️ 3 жақын", "en": "🗓️ Next 3"},
    "btn_lang": {"ru": "🌐 Язык", "kk": "🌐 Тіл", "en": "🌐 Language"},
    "btn_birthday": {"ru": "🎂 Мой ДР", "kk": "🎂 Туған күнім", "en": "🎂 My bday"},

    # Меню по ДР (inline)
    "bday_menu_title": {"ru": "Управление ДР:", "kk": "Туған күн басқару:", "en": "Birthday menu:"},
    "btn_bday_set": {"ru": "Установить ДР", "kk": "Туған күн қою", "en": "Set birthday"},
    "btn_bday_view": {"ru": "Показать ДР", "kk": "Туған күн көрсету", "en": "View birthday"},
    "btn_bday_clear": {"ru": "Удалить ДР", "kk": "Жою", "en": "Clear birthday"},
    "bday_set_instructions": {
        "ru": "Чтобы установить ДР, используй команду: DD-MM или DD-MM-YYYY(год можно не указывать).",
        "kk": "Туған күнді орнату үшін: DD-MM немесе DD-MM-YYYY (жылды көрсетпеуге болады).",
        "en": "To set birthday: DD-MM or DD-MM-YYYY (year optional)."
    },

    # language chooser prompt
    "choose_language_prompt": {
        "ru": "Выберите язык:", "kk": "Тілді таңдаңыз:", "en": "Choose language:"},
    "birthday_notifications": {
        "ru": "🎉 Сегодня у тебя день рождения! С днём рождения, {user.name}! 🥳\n",
        "kk": "🎉 Бүгін сенің туған күнің! Құтты болсын, {user.name}! 🥳\n",
        "en": "🎉 Today is your birthday! Happy birthday, {user.name}! 🥳"
    },
}


def t(key, locale="ru", **kwargs):
    translations = MESSAGES.get(key, {})
    text = translations.get(locale) or translations.get("ru") or next(iter(translations.values()), "")
    try:
        return text.format(**kwargs)
    except Exception:
        return text


def _parse_birthday_arg(arg: str) -> date:
    cleaned = re.sub(r"[\/\.\-]", ".", arg.strip())
    parts = [p for p in cleaned.split(".") if p]
    if len(parts) == 2:
        d, m = parts
        y = 2000
    elif len(parts) == 3:
        d, m, y = parts
        y = int(y)
        if y < 100:
            y += 2000
    else:
        raise ValueError("Формат: DD-MM или DD-MM-YYYY")
    return date(year=int(y), month=int(m), day=int(d))


async def _get_or_create_user(tg_id: int, full_name: str) -> User:
    async with async_session() as session:
        res = await session.execute(select(User).where(User.tg_id == tg_id))
        user = res.scalar_one_or_none()
        if not user:
            user = User(tg_id=tg_id, name=full_name)
            session.add(user)
            await session.commit()
        return user


async def _get_holiday_translations():
    async with async_session() as session:
        res = await session.execute(
            select(Holiday).options(selectinload(Holiday.translations)).order_by(Holiday.month, Holiday.day)
        )
        return res.scalars().all()


def _format_holiday_name(holiday, lang: str) -> str:
    # 1. Ищем перевод на языке пользователя
    for tr in holiday.translations:
        if tr.lang == lang:
            return tr.name
    # 2. fallback по приоритету (ru → kk → en)
    fallback_priority = ["kk", "ru", "en"]
    for fb in fallback_priority:
        for tr in holiday.translations:
            if tr.lang == fb:
                return tr.name

    # 3. если вообще ничего нет — название "Holiday"
    return "Holiday"



def build_main_kb(locale: str):
    kb = ReplyKeyboardBuilder()
    kb.button(text=t("btn_holidays", locale))
    kb.button(text=t("btn_next3", locale))
    kb.button(text=t("btn_lang", locale))
    kb.button(text=t("btn_birthday", locale))
    kb.adjust(2)
    return kb.as_markup(resize_keyboard=True)


@dp.message(CommandStart())
async def start(message: types.Message):
    user = await _get_or_create_user(message.from_user.id, message.from_user.full_name)
    await message.answer(t("start", user.lang), reply_markup=build_main_kb(user.lang))


@dp.message(Command("help"))
async def help_cmd(message: types.Message):
    async with async_session() as session:
        res = await session.execute(select(User).where(User.tg_id == message.from_user.id))
        user = res.scalar_one_or_none()
        lang = user.lang if user else "ru"
    await message.answer(t("help", lang))


# Команда ближайшего праздника
@dp.message(Command("holidays"))
async def holidays_cmd(message: types.Message):
    # reuse logic (works both for command and button via default_handler)
    async with async_session() as session:
        res = await session.execute(select(User).where(User.tg_id == message.from_user.id))
        user = res.scalar_one()
    holidays = await _get_holiday_translations()
    if not holidays:
        await message.answer(t("no_holidays", user.lang))
        return

    today = date.today()
    next_item = None
    for h in holidays:
        # игнорируем некорректные даты
        if not (1 <= h.month <= 12 and 1 <= h.day <= 31):
            continue
        try:
            h_date = date(today.year, h.month, h.day)
        except ValueError:
            continue
        if h_date >= today:
            next_item = (h, h_date)
            break

    if not next_item:
        h = holidays[0]
        h_date = date(today.year + 1, h.month, h.day)
        next_item = (h, h_date)

    h, h_date = next_item
    delta = (h_date - today).days
    name = _format_holiday_name(h, user.lang)

    if delta == 0:
        text = t("holiday_today", user.lang, name=name)
    elif delta == 1:
        text = t("holiday_tomorrow", user.lang, name=name)
    else:
        # подставляем слово для дней
        if user.lang == "kk":
            day_word = "күн"
        elif user.lang == "en":
            day_word = "day" if delta == 1 else "days"
        else:
            day_word = "день" if delta == 1 else "дней"

        text = t("holiday_future", user.lang,
                 name=name,
                 delta=delta,
                 days_word=day_word,
                 date=h_date.strftime("%d-%m-%Y"))

    await message.answer(text)


# Callback для выбора языка
@dp.callback_query(lambda c: c.data and c.data.startswith("lang:"))
async def lang_callback(cb: types.CallbackQuery):
    lang = cb.data.split(":", 1)[1]
    user_id = cb.from_user.id
    async with async_session() as session:
        res = await session.execute(select(User).where(User.tg_id == user_id))
        user = res.scalar_one_or_none()
        if not user:
            user = User(tg_id=user_id, name=cb.from_user.full_name)
            session.add(user)
            await session.commit()
        user.lang = lang
        await session.commit()

    await cb.answer()  # убрать "loading"
    # удаляем старое inline-сообщение и высылаем подтверждение + новое главное меню на выбранном языке
    try:
        await cb.message.delete()
    except Exception:
        pass

    await bot.send_message(user_id, t("lang_saved", locale=lang, lang=lang), reply_markup=build_main_kb(lang))


# Callback для меню ДР
@dp.callback_query(lambda c: c.data and c.data.startswith("bday:"))
async def bday_callback(cb: types.CallbackQuery):
    action = cb.data.split(":", 1)[1]
    user_id = cb.from_user.id
    async with async_session() as session:
        res = await session.execute(select(User).where(User.tg_id == user_id))
        user = res.scalar_one_or_none()
        if not user:
            user = User(tg_id=user_id, name=cb.from_user.full_name)
            session.add(user)
            await session.commit()
        lang = user.lang if user else "ru"

    if action == "view":
        if user.birthday:
            await cb.message.edit_text(t("birthday_show", lang, date=user.birthday.strftime("%d-%m")))
        else:
            await cb.message.edit_text(t("birthday_not_set", lang))
    elif action == "set":
        await cb.message.edit_text(t("bday_set_instructions", lang))
    elif action == "clear":
        if user.birthday:
            async with async_session() as session:
                res = await session.execute(select(User).where(User.tg_id == user_id))
                u = res.scalar_one()
                u.birthday = None
                await session.commit()
            await cb.message.edit_text(t("birthday_cleared", lang))
        else:
            await cb.message.edit_text(t("birthday_not_set", lang))
    await cb.answer()

# 3 ближайших праздника
@dp.message(Command("next_holidays"))
async def next_holidays(message: types.Message):
    async with async_session() as session:
        res = await session.execute(select(User).where(User.tg_id == message.from_user.id))
        user = res.scalar_one()
    holidays = await _get_holiday_translations()
    if not holidays:
        await message.answer(t("no_holidays", user.lang))
        return

    today = date.today()
    upcoming = []
    for h in holidays:
        # проверяем корректность даты
        if not (1 <= h.month <= 12 and 1 <= h.day <= 31):
            continue
        try:
            h_date = date(today.year, h.month, h.day)
        except ValueError:
            continue
        if h_date < today:
            h_date = date(today.year + 1, h.month, h.day)
        upcoming.append((h, h_date))

    # сортируем по дате
    upcoming.sort(key=lambda x: x[1])
    top3 = upcoming[:3]

    lines = [t("next_holidays_header", user.lang)]
    for h, h_date in top3:
        delta = (h_date - today).days
        name = _format_holiday_name(h, user.lang)

        if delta == 0:
            lines.append(f"🎉 {t('holiday_today', user.lang, name=name)}")
        elif delta == 1:
            lines.append(f"🎊 {t('holiday_tomorrow', user.lang, name=name)}")
        else:
            if user.lang == "kk":
                day_word = "күн"
            elif user.lang == "en":
                day_word = "day" if delta == 1 else "days"
            else:
                day_word = "день" if delta == 1 else "дней"

            lines.append(
                t("holiday_future", user.lang,
                  name=name,
                  delta=delta,
                  days_word=day_word,
                  date=h_date.strftime("%d-%m-%Y"))
            )

    await message.answer("\n\n".join(lines))

# Стандартные команды для работы с ДР (как раньше)
@dp.message(Command("set_birthday"))
async def set_birthday_cmd(message: types.Message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("❌ Укажи дату: DD-MM или DD-MM-YYYY (точка и / тоже поддерживаются)")
        return

    try:
        birthday = _parse_birthday_arg(parts[1])
    except Exception:
        await message.answer("⚠️ Неверный формат. Пример: 28-08 или 28.08.2000")
        return

    async with async_session() as session:
        res = await session.execute(select(User).where(User.tg_id == message.from_user.id))
        user = res.scalar_one_or_none()

        if not user:
            user = User(tg_id=message.from_user.id, name=message.from_user.full_name)
            session.add(user)
            await session.commit()

        user.birthday = birthday
        await session.commit()

    await message.answer(t("birthday_saved", user.lang, date=birthday.strftime("%d-%m-%Y")))


@dp.message(Command("my_birthday"))
async def my_birthday_cmd(message: types.Message):
    async with async_session() as session:
        res = await session.execute(select(User).where(User.tg_id == message.from_user.id))
        user = res.scalar_one_or_none()
        if not user:
            user = User(tg_id=message.from_user.id, name=message.from_user.full_name)
            session.add(user)
            await session.commit()
        if user.birthday:
            await message.answer(t("birthday_show", user.lang, date=user.birthday.strftime("%d-%m-%Y")))
        else:
            await message.answer(t("birthday_not_set", user.lang))


@dp.message(Command("clear_birthday"))
async def clear_birthday_cmd(message: types.Message):
    async with async_session() as session:
        res = await session.execute(select(User).where(User.tg_id == message.from_user.id))
        user = res.scalar_one_or_none()
        if not user:
            user = User(tg_id=message.from_user.id, name=message.from_user.full_name)
            session.add(user)
            await session.commit()
        if user.birthday:
            user.birthday = None
            await session.commit()
            await message.answer(t("birthday_cleared", user.lang))
        else:
            await message.answer(t("birthday_not_set", user.lang))

@dp.message(lambda m: re.match(r"^\s*\d{1,2}[./-]\d{1,2}([./-]\d{2,4})?\s*$", m.text or ""))
async def catch_birthday(message: types.Message):
    """
    Позволяет пользователю указать дату рождения простым сообщением
    """
    raw = (message.text or "").strip()
    cleaned = re.sub(r"[\/\.\-]", ".", raw)
    parts = [p for p in cleaned.split(".") if p]
    try:
        if len(parts) == 2:
            d, m = parts
            y = 2000
        elif len(parts) == 3:
            d, m, y = parts
            y = int(y)
            if y < 100:
                y += 2000
        else:
            raise ValueError()
        birthday = date(year=int(y), month=int(m), day=int(d))
    except Exception:
        await message.answer("⚠️ Формат даты: 28-08 или 28-08-2000")
        return

    # ищем пользователя
    async with async_session() as session:
        res = await session.execute(select(User).where(User.tg_id == message.from_user.id))
        user = res.scalar_one_or_none()
        if not user:
            user = User(tg_id=message.from_user.id, name=message.from_user.full_name)
            session.add(user)
            await session.commit()

        user.birthday = birthday
        await session.commit()

    lang = user.lang if user else "ru"
    await message.answer(
        t("birthday_saved", lang, date=birthday.strftime("%d-%m-%Y"))
    )

# Показываем меню выбора языка (inline)
@dp.message()
async def default_handler(message: types.Message):
    text = (message.text or "").strip()

    # получаем user.lang (если есть)
    async with async_session() as session:
        res = await session.execute(select(User).where(User.tg_id == message.from_user.id))
        user = res.scalar_one_or_none()
    user_lang = user.lang if user else "ru"

    # Сопоставление локализованных кнопок с действиями
    btn_map = {
        t("btn_holidays", "ru"): holidays_cmd,
        t("btn_holidays", "kk"): holidays_cmd,
        t("btn_holidays", "en"): holidays_cmd,

        t("btn_next3", "ru"): next_holidays,
        t("btn_next3", "kk"): next_holidays,
        t("btn_next3", "en"): next_holidays,

        t("btn_lang", "ru"): "lang_menu",
        t("btn_lang", "kk"): "lang_menu",
        t("btn_lang", "en"): "lang_menu",

        t("btn_birthday", "ru"): "bday_menu",
        t("btn_birthday", "kk"): "bday_menu",
        t("btn_birthday", "en"): "bday_menu",
    }

    # если нажата одна из кнопок — вызовем соответствующий обработчик
    if text in btn_map:
        action = btn_map[text]
        if callable(action):
            await action(message)
            return
        if action == "lang_menu":
            # show inline language chooser
            kb = InlineKeyboardBuilder()
            kb.button(text="Русский 🇷🇺", callback_data="lang:ru")
            kb.button(text="Қазақша 🇰🇿", callback_data="lang:kk")
            kb.button(text="English 🇬🇧", callback_data="lang:en")
            kb.adjust(1)
            await message.answer(t("choose_language_prompt", user_lang) + "\n", reply_markup=kb.as_markup())
            return
        if action == "bday_menu":
            # show birthday inline menu
            kb = InlineKeyboardBuilder()
            kb.button(text=t("btn_bday_view", user_lang), callback_data="bday:view")
            kb.button(text=t("btn_bday_set", user_lang), callback_data="bday:set")
            kb.button(text=t("btn_bday_clear", user_lang), callback_data="bday:clear")
            kb.adjust(1)
            await message.answer(t("bday_menu_title", user_lang), reply_markup=kb.as_markup())
            return

    # если текст не обработан — показать help (локализованный)
    await message.answer(t("help", user_lang))

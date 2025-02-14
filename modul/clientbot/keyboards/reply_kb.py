import logging

from aiogram.types import KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder, ReplyKeyboardMarkup
from asgiref.sync import sync_to_async

from modul.clientbot import strings, shortcuts
from modul.clientbot.shortcuts import get_current_bot,  get_bot_by_token
from modul.models import Bot
from aiogram import Bot as CBot
from modul.config import settings_conf
logger = logging.getLogger(__name__)


MUSIC_MENU_BUTTONS_TEXT = [
    ("🎙Лучшая музыка"),
    ("🎧Новые песни"),
    ("🔥Чарт Музыка"),
    ("🔍Поиск")
]

CHATGPT_BUTTONS_TEXT = [
    ("☁ Чат с GPT-4"),
    ("☁ Чат с GPT-3.5"),
    ("🎨 Генератор фото [DALL-E]"),
    ("🗣️Голосовой помощник"),
    ("🗨️ Текст в аудио"),
    ("🔉 Аудио в текст"),
    ("🎥 Транскрипция ютуб"),
    ("🔍 Гугл поиск"),
    ("🔋 Баланс"),
    ("ℹ️ Помощь"),
]

HOROSCOPE_BUTTONS_TEXT = [
    ("🔮 Гороскоп на каждый день"),
    ("🔮 Гороскоп на завтра"),
    ("🔮 Гороскоп на месяц"),
    ("🏵 Восточный гороскоп"),
    ("🎩 Профиль"),
]


# ANON_MENU_BUTTONS_TEXT = [
#     ("☕ Искать собеседника"),
#     ("🍪 Профиль"),
#     "⭐ VIP",
# ]


def cancel():
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text=("Отмена")))
    return builder.as_markup(resize_keyboard=True)


def cancel_or_skip():
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text=("Отмена")),
        KeyboardButton(text=("Пропустить")),
        width=1
    )
    return builder.as_markup(resize_keyboard=True)


def yes_no():
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text=("Да")),
        KeyboardButton(text=("Нет")),
        width=2
    )
    return builder.as_markup(resize_keyboard=True)





async def turn_bot_data(attr: str, bot: CBot):
    bot = await get_current_bot()
    setattr(bot, attr, not getattr(bot, attr))
    await bot.save()


@sync_to_async
def get_bot_owner(bot):
    return bot.owner


@sync_to_async
def owner_bots_filter(owner):
    return owner.bots.filter(owner=owner, unauthorized=False).count()


async def gen_buttons(current_bot: Bot, uid: int):
    btns = []
    # Avval Django modeldan bot ma'lumotlarini olish
    bot_db = await shortcuts.get_bot(current_bot)
    if not bot_db:
        logger.error(f"Bot not found in database: {current_bot.token}")
        return btns

    # Endi bot_db orqali attributlarga murojaat qilamiz
    if bot_db.enable_promotion:
        btns.append(("⭐️ Социальные сети"))
        btns.append(("📋 Мои заказы"))
        btns.append(("💰 Баланс"))
        btns.append(("👤 Реферальная система"))
        btns.append(("🌍 Поменять язык"))
    if bot_db.enable_music:
        if have_one_module(bot_db, "music"):
            [btns.append(i) for i in MUSIC_MENU_BUTTONS_TEXT]
        else:
            btns.append(("🎧 Музыка"))
    if bot_db.enable_download:
        if not have_one_module(bot_db, "download"):
            btns.append(("🎥 Скачать видео"))
    if bot_db.enable_chatgpt:
        pass
    if bot_db.enable_leo:
        btns.append(("🫰 Знакомства"))
    if bot_db.enable_horoscope:
        if have_one_module(bot_db, "horoscope"):
            [btns.append(i) for i in HOROSCOPE_BUTTONS_TEXT]
        else:
            btns.append(("♈️ Гороскоп"))
    if bot_db.enable_promotion:
        btns.append(("ℹ️ Информация"))
    if bot_db.enable_anon:
        btns.append(("🚀Начать"))
        btns.append(("👋Изменить приветствие"))
        btns.append(("⭐️Ваша статистика"))
    btns.append(("💸Заработать"))
    return btns

# have_one_module funksiyasini ham o'zgartiramiz
def have_one_module(bot_db, module_name: str):
    modules = [
        "enable_promotion",
        "enable_music",
        "enable_download",
        "enable_leo",
        "enable_chatgpt",
        "enable_horoscope",
        "enable_anon",
        "enable_sms",
    ]
    if getattr(bot_db, f"enable_{module_name}"):
        return [getattr(bot_db, x) for x in modules].count(True) == 1
    return False

async def main_menu(uid: int, bot: Bot):
    builder = ReplyKeyboardBuilder()
    btns = await gen_buttons(bot, uid)

    for btn in btns:
        builder.add(KeyboardButton(text=btn))

    builder.adjust(2, 1, 1)
    return builder.as_markup(resize_keyboard=True)


async def refs_kb():
    buttons = [
        [KeyboardButton(text="💸Заработать"), ]
    ]
    kb = ReplyKeyboardMarkup(resize_keyboard=True, keyboard=buttons)
    return kb


def confirm():
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text=("Да, продолжить")),
        KeyboardButton(text=("Отмена")),
        width=1
    )
    return builder.as_markup(resize_keyboard=True)


def amount_kb():
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text=strings.CANCEL), width=1)
    builder.row(
        KeyboardButton(text="50"),
        KeyboardButton(text="100"),
        KeyboardButton(text="250"),
        KeyboardButton(text="500"),
        KeyboardButton(text="1000"),
        KeyboardButton(text="5000"),
        width=3
    )
    return builder.as_markup(resize_keyboard=True)


def withdraw_confirmation():
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text=("Перевести")),
        KeyboardButton(text=strings.CANCEL),
        width=1
    )
    return builder.as_markup(resize_keyboard=True)


async def download_main_menu() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text=("Назад")),
        width=1
    )
    return builder.as_markup(resize_keyboard=True)


async def ai_main_menu():
    keyboard = ReplyKeyboardBuilder()
    keyboard.row(
        KeyboardButton(text=("Назад",)),
        width=1,
    )
    return keyboard.as_markup(resize_keyboard=True)

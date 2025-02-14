import logging

from aiogram.types import KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder, ReplyKeyboardMarkup
from asgiref.sync import sync_to_async

from modul.clientbot import strings
from modul.clientbot.shortcuts import get_current_bot, have_one_module, get_bot_by_token
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
    try:
        btns = []

        if getattr(current_bot, "leo", False):
            btns.append("🫰 Знакомства")

        bot_instance = await get_bot_by_token(current_bot.token)

        if bot_instance and getattr(bot_instance, "enable_anon", False):
            btns.extend([
                "🚀Начать", "👋Изменить приветствие",
                "⭐️Ваша статистика", "💸Заработать"
            ])
            return btns
    except Exception as e:
        logger.error(f"Error in gen_buttons: {e}")

    return ["💸Заработать"]

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

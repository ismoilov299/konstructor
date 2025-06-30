# modul/clientbot/handlers/davinci_bot/keyboards/reply_kb.py

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from aiogram.utils.keyboard import ReplyKeyboardBuilder


async def main_menu_keyboard():
    """Asosiy menyu klaviaturasi"""
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text="🚀 Смотреть анкеты"),
        KeyboardButton(text="👑 Boost")
    )
    builder.row(
        KeyboardButton(text="👤 Моя анкета"),
        KeyboardButton(text="💎 VIP")
    )
    return builder.as_markup(resize_keyboard=True)


async def cancel_keyboard():
    """Bekor qilish klaviaturasi"""
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="❌ Отменить"))
    return builder.as_markup(resize_keyboard=True)


async def skip_keyboard():
    """O'tkazib yuborish klaviaturasi"""
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="⏭ Пропустить"))
    return builder.as_markup(resize_keyboard=True)


async def couple_menu_keyboard():
    """Juftlik menyusi klaviaturasi"""
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text="❤️"),
        KeyboardButton(text="💌/📹"),
        KeyboardButton(text="👎"),
        KeyboardButton(text="💤")
    )
    return builder.as_markup(resize_keyboard=True)


async def couple_next_keyboard():
    """Keyingi juftlik klaviaturasi"""
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text="В меню ⤴️"),
        KeyboardButton(text="Дальше ➡️")
    )
    return builder.as_markup(resize_keyboard=True)


async def rate_menu_keyboard():
    """Baholash menyusi klaviaturasi"""
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text="❤️"),
        KeyboardButton(text="💌/📹"),
        KeyboardButton(text="⚠️")
    )
    builder.row(
        KeyboardButton(text="👎"),
        KeyboardButton(text="💤")
    )
    return builder.as_markup(resize_keyboard=True)


async def warnings_keyboard():
    """Ogohlantirish klaviaturasi"""
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="👌 Понятно"))
    return builder.as_markup(resize_keyboard=True)


async def vip_keyboard():
    """VIP klaviaturasi"""
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text="Купить VIP 👑"),
        KeyboardButton(text="В меню ⤴️")
    )
    return builder.as_markup(resize_keyboard=True)


async def remove_keyboard():
    """Klaviaturani olib tashlash"""
    return ReplyKeyboardRemove()


# Dinamik klaviaturalar
async def get_numbers_keyboard(count, back_button=False):
    """Raqamlar klaviaturasi"""
    builder = ReplyKeyboardBuilder()

    # Raqamlarni qo'shish
    buttons = []
    for i in range(1, count + 1):
        buttons.append(KeyboardButton(text=str(i)))

        # Har 3 ta tugmadan keyin yangi qator
        if len(buttons) >= 3:
            builder.row(*buttons)
            buttons = []

    # Qolgan tugmalarni qo'shish
    if buttons:
        builder.row(*buttons)

    # Orqaga tugmasini qo'shish
    if back_button:
        builder.row(KeyboardButton(text="🔙 Назад"))

    return builder.as_markup(resize_keyboard=True)


async def custom_keyboard(buttons_list):
    """Maxsus klaviatura yaratish"""
    builder = ReplyKeyboardBuilder()

    for row in buttons_list:
        if isinstance(row, list):
            builder.row(*[KeyboardButton(text=btn) for btn in row])
        else:
            builder.row(KeyboardButton(text=row))

    return builder.as_markup(resize_keyboard=True)
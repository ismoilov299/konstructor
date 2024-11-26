from aiogram.types import (ReplyKeyboardMarkup, KeyboardButton,
                           InlineKeyboardMarkup, InlineKeyboardButton)
from aiogram.utils.keyboard import InlineKeyboardBuilder
async def channels_in(all_channels):
    keyboard_builder = InlineKeyboardBuilder()
    for i in all_channels:
        try:
            keyboard_builder.button(text="💎Спонсор", url=i[1])
        except:
            pass
    keyboard_builder.button(text="Проверить подписки", callback_data="check_chan")
    if len(all_channels) < 6:
        keyboard_builder.adjust(1)
    elif len(all_channels) > 6 <= 12:
        keyboard_builder.adjust(2)
    elif len(all_channels) > 12 <= 24:
        keyboard_builder.adjust(3)
    elif len(all_channels) > 24 <= 48:
        keyboard_builder.adjust(4)
    elif len(all_channels) > 48 <= 96:
        keyboard_builder.adjust(5)
    else:
        keyboard_builder.adjust(6)
    return keyboard_builder.as_markup()
async def main_menu_bt():
    buttons = [
        [KeyboardButton(text="🚀Начать"), KeyboardButton(text="👋Изменить приветствие")],
        [KeyboardButton(text="📛Изменить ссылку"), KeyboardButton(text="⭐️Ваша статистика")],
        [KeyboardButton(text="☕️Поддержать разработчика")],
	[KeyboardButton(text="💸Заработать")]
        ]
    kb = ReplyKeyboardMarkup(resize_keyboard=True, keyboard=buttons)
    return kb

async def cancel_in():
    buttons = [
        [InlineKeyboardButton(text="❌Отменить отправку", callback_data="cancel")]
    ]
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    return kb

async def again_in(id):
    buttons = [
        [InlineKeyboardButton(text="🔂Отправить еще", callback_data=f"again_{id}")]
    ]
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    return kb
async def payment_amount_keyboard():
    buttons = [
        [InlineKeyboardButton(text="10⭐️", callback_data="pay10"),
         InlineKeyboardButton(text="20⭐️", callback_data="pay20")],
        [InlineKeyboardButton(text="50⭐️", callback_data="pay50"),
         InlineKeyboardButton(text="100⭐️", callback_data="pay100")],
        [InlineKeyboardButton(text="500⭐️", callback_data="pay500")]
    ]
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    return kb

async def payment_keyboard(amount):
    builder = InlineKeyboardBuilder()
    builder.button(text=f"Заплатить {amount} ⭐️", pay=True)

    return builder.as_markup()

async def greeting_in():
    buttons = [
        [InlineKeyboardButton(text="↩️Не менять приветствие", callback_data="cancel")],
        [InlineKeyboardButton(text="❌Удалить приветствие", callback_data="greeting_rem")]

    ]
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    return kb
async def link_in():
    buttons = [
        [InlineKeyboardButton(text="↩️Не менять ссылку", callback_data="cancel")]
    ]
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    return kb

async def admin_menu_in():
    buttons = [
        [InlineKeyboardButton(text="✉️Рассылка", callback_data="mailing")],
        [InlineKeyboardButton(text="📧Обязательные подписки", callback_data="change_channels")],
        [InlineKeyboardButton(text="Закрыть", callback_data="cancel")]
    ]
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    return kb
async def admin_channels_in():
    buttons = [
        [InlineKeyboardButton(text="➕Добавить канал/группу", callback_data="add_channel")],
        [InlineKeyboardButton(text="➖Удалить канал/группу", callback_data="delete_channel")]
    ]
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    return kb
async def cancel_bt():
    buttons = [
        [KeyboardButton(text="❌Отменить")]
    ]
    kb = ReplyKeyboardMarkup(resize_keyboard=True, keyboard=buttons)
    return kb

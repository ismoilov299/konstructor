import logging

from aiogram.types import (ReplyKeyboardMarkup, KeyboardButton,
                           InlineKeyboardMarkup, InlineKeyboardButton)
from aiogram.utils.keyboard import InlineKeyboardBuilder
logger = logging.getLogger(__name__)

async def channels_in(all_channels, bot):
    keyboard_builder = InlineKeyboardBuilder()
    for channel_id, _ in all_channels:
        try:
            chat_info = await bot.get_chat(channel_id)
            invite_link = chat_info.invite_link or f"https://t.me/{chat_info.username}"
            keyboard_builder.button(text="💎Спонсор", url=invite_link)
        except Exception as e:
            logger.error(f"Error getting channel info {channel_id}: {e}")
            continue

    keyboard_builder.button(text="Проверить подписки", callback_data="check_chan")
    keyboard_builder.adjust(1)
    return keyboard_builder.as_markup()

async def main_menu_bt():
    buttons = [
        [KeyboardButton(text="🚀Начать"), KeyboardButton(text="👋Изменить приветствие")],
        [ KeyboardButton(text="⭐️Ваша статистика")],
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

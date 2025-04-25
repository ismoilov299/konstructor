import logging

from aiogram.types import (ReplyKeyboardMarkup, KeyboardButton,
                           InlineKeyboardMarkup, InlineKeyboardButton)
from aiogram.utils.keyboard import InlineKeyboardBuilder
logger = logging.getLogger(__name__)

async def main_menu_bt():
    buttons = [
        [KeyboardButton(text="💸Заработать"), KeyboardButton(text="📱Профиль")],
        [KeyboardButton(text="ℹ️Инфо")]
    ]
    kb = ReplyKeyboardMarkup(resize_keyboard=True, keyboard=buttons)
    return kb

async def main_menu_bt2():
    buttons = [
        [KeyboardButton(text="💸Заработать"), KeyboardButton(text="📱Профиль")],
        [KeyboardButton(text="ℹ️Инфо")],
        [KeyboardButton(text="🔙Назад в меню")]
    ]
    kb = ReplyKeyboardMarkup(resize_keyboard=True, keyboard=buttons)
    return kb



async def payment_in():
    buttons = [
        [InlineKeyboardButton(text="📤Вывести", callback_data="payment")]
    ]
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    return kb


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


#
# async def channels_in(all_channels):
#     if len(all_channels) > 6:
#         actual_channels = all_channels[0:6]
#         buttons = [
#             [InlineKeyboardButton(text="💎Спонсор", url=f"{i[1]}")] for i in actual_channels
#         ]
#
#         kb = InlineKeyboardMarkup(inline_keyboard=buttons)
#
#         return kb
#     buttons = [
#         [InlineKeyboardButton(text="💎Спонсор", url=f"{i[1]}")] for i in all_channels
#     ]
#     buttons.append([InlineKeyboardButton(text="Проверить подписки", callback_data="check_chan")])
#     kb = InlineKeyboardMarkup(inline_keyboard=buttons)
#     return kb

async def admin_in(admin_user):
    print(f"Received admin_user: '{admin_user}'")

    if admin_user and admin_user.strip():
        admin_user = admin_user.strip()
        admin_user = admin_user[1:] if admin_user.startswith("@") else admin_user
        admin_url = f"https://t.me/{admin_user}"
    else:
        admin_url = "https://t.me/"

    print(f"Generated URL: '{admin_url}'")

    buttons = [
        [InlineKeyboardButton(text="🧑‍💻Админ", url=admin_url)]
    ]
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    return kb


async def cancel_bt():
    buttons = [
        [KeyboardButton(text="❌Отменить")]
    ]
    kb = ReplyKeyboardMarkup(resize_keyboard=True, keyboard=buttons)
    return kb


async def admin_menu_in():
    buttons = [
        [InlineKeyboardButton(text="✉️Рассылка", callback_data="mailing")],
        [InlineKeyboardButton(text="🔎Управление", callback_data="imp"),
         InlineKeyboardButton(text="💳Выплаты", callback_data="all_payments")],
        [InlineKeyboardButton(text="💰Изменить награду за рефа", callback_data="change_money")],
        [InlineKeyboardButton(text="📕Изменить минимальный вывод", callback_data="change_min")],
        [InlineKeyboardButton(text="📧Обязательные подписки", callback_data="change_channels")],
        [InlineKeyboardButton(text="Закрыть", callback_data="cancel")]
    ]
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    return kb


async def payments_action_in(id):
    buttons = [
        [InlineKeyboardButton(text="✅Подтвердить", callback_data=f"accept_{id}")],
        [InlineKeyboardButton(text="❌Отклонить", callback_data=f"decline_{id}")],
        [InlineKeyboardButton(text="Закрыть", callback_data="cancel")]
    ]
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    return kb


async def accepted_in():
    buttons = [
        [InlineKeyboardButton(text="✅Заявка была подтверждена", callback_data="none")],
        [InlineKeyboardButton(text="Закрыть", callback_data="cancel")]
    ]
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    return kb


async def declined_in():
    buttons = [
        [InlineKeyboardButton(text="❌Заявка была отменена", callback_data="none")],
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


async def imp_menu_in(id, status):
    if status == True:
        buttons = [
            [InlineKeyboardButton(text="❇️Разбанить", callback_data=f"razb_{id}")],
            [InlineKeyboardButton(text="➕Баланс вывода", callback_data=f"addbalance_{id}"),
             InlineKeyboardButton(text="✏️Баланс вывода", callback_data=f"changebalance_{id}")],
            [InlineKeyboardButton(text="✏️Количество рефералов", callback_data=f"changerefs_{id}")],
            [InlineKeyboardButton(text="🔍Посмотреть рефералов", callback_data=f"showrefs_{id}")],
            [InlineKeyboardButton(text="Закрыть", callback_data="cancel")]

        ]
    elif status == False:
        buttons = [
            [InlineKeyboardButton(text="❌Забанить", callback_data=f"ban_{id}")],
            [InlineKeyboardButton(text="➕Баланс вывода", callback_data=f"addbalance_{id}"),
             InlineKeyboardButton(text="✏️Баланс вывода", callback_data=f"changebalance_{id}")],
            [InlineKeyboardButton(text="✏️Количество рефералов", callback_data=f"changerefs_{id}")],
            [InlineKeyboardButton(text="🔍Посмотреть рефералов", callback_data=f"showrefs_{id}")],
            [InlineKeyboardButton(text="Закрыть", callback_data="cancel")]

        ]
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    return kb


async def close_in():
    buttons = [
        [InlineKeyboardButton(text="Закрыть", callback_data="cancel")]
    ]
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    return kb


async def universal_in(text, url):
    buttons = [
        [InlineKeyboardButton(text=f"{text}", callback_data=f"{url}")]
    ]
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    return kb

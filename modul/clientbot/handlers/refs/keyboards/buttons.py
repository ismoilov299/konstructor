from aiogram.types import (ReplyKeyboardMarkup, KeyboardButton,
                           InlineKeyboardMarkup, InlineKeyboardButton)
from aiogram.utils.keyboard import InlineKeyboardBuilder


async def main_menu_bt():
    buttons = [
        [KeyboardButton(text="💸Заработать"), KeyboardButton(text="📱Профиль")],
        [KeyboardButton(text="ℹ️Инфо")]
    ]
    kb = ReplyKeyboardMarkup(resize_keyboard=True, keyboard=buttons)
    return kb


async def payment_in():
    buttons = [
        [InlineKeyboardButton(text="📤Вывести", callback_data="payment")]
    ]
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    return kb


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
    buttons = [
        [InlineKeyboardButton(text="🧑‍💻Админ", url=admin_user)]
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

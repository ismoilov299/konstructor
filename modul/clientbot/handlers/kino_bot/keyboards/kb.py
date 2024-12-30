from aiogram import types

search_kb = types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(
    text='🔍 Поиск',
    callback_data='start_search'
)]])

cancel_btn = types.InlineKeyboardButton(text='Отменить', callback_data='cancel')
cancel_kb = types.InlineKeyboardMarkup(
    inline_keyboard=[[types.InlineKeyboardButton(text='Отменить', callback_data='cancel')]])

btn = [
    [
        types.InlineKeyboardButton(
            text='📊 Статистика',
            callback_data='admin_get_stats'
        ),
        types.InlineKeyboardButton(
            text='📢 Рассылка',
            callback_data='admin_send_message'
        )
    ],
    [
        types.InlineKeyboardButton(
            text='➕ Добавить канал',
            callback_data='admin_add_channel'
        ),
        types.InlineKeyboardButton(
            text='➖ Удалить канал',
            callback_data='admin_delete_channel'
        )
    ],
    [
        types.InlineKeyboardButton(
            text='💳 Выплаты',
            callback_data='all_payments'
        )
    ],
    [
        types.InlineKeyboardButton(
            text='💰 Изменить награду за рефа',
            callback_data='change_money'
        )
    ],
    [
        types.InlineKeyboardButton(
            text='📕 Изменить минимальный вывод',
            callback_data='change_min'
        )
    ],
    [
        types.InlineKeyboardButton(
            text='🔎 Управление',
            callback_data='imp'
        )
    ]
]

admin_kb = types.InlineKeyboardMarkup(inline_keyboard=btn)






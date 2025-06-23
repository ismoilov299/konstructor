# modul/bot/main_bot/keyboards/main_kb.py
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


async def main_menu():
    buttons = [
        [InlineKeyboardButton(text="🤖 Мои боты", callback_data="my_bots")],
        [InlineKeyboardButton(text="➕ Создать нового бота", callback_data="create_bot")],
        [InlineKeyboardButton(text="📊 Статистика", callback_data="statistics")],
        [InlineKeyboardButton(text="💰 Баланс", callback_data="balance")],
        [InlineKeyboardButton(text="🔧 Настройки", callback_data="settings")],
        [InlineKeyboardButton(text="❓ Помощь", callback_data="help")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


async def create_bot_menu():
    """Устаревшая функция - теперь используется create_bot.py"""
    buttons = [
        [InlineKeyboardButton(text="📝 Ввести токен бота", callback_data="enter_token")],
        [InlineKeyboardButton(text="❓ Как получить токен?", callback_data="token_help")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


async def bot_modules_menu():
    """Устаревшая функция - теперь используется create_bot.py с новыми модулями"""
    modules = [
        ("refs", "Реферальный 👥"),
        ("leo", "Дайвинчик 💞"),
        ("asker", "Asker Бот 💬"),
        ("kino", "Кинотеатр 🎥"),
        ("download", "DownLoader 💾"),
        ("chatgpt", "ChatGPT 💡")
    ]

    buttons = []
    row = []
    for i, (module_key, module_name) in enumerate(modules):
        row.append(InlineKeyboardButton(
            text=f"⬜ {module_name}",
            callback_data=f"toggle_{module_key}"
        ))

        # Добавляем по 2 кнопки в ряд
        if len(row) == 2 or i == len(modules) - 1:
            buttons.append(row)
            row = []

    buttons.append([InlineKeyboardButton(text="✅ Сохранить", callback_data="save_bot_config")])
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)
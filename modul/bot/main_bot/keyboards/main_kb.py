# modul/bot/main_bot/keyboards/main_kb.py
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

async def main_menu():
    buttons = [
        [InlineKeyboardButton(text="🤖 Mening botlarim", callback_data="my_bots")],
        [InlineKeyboardButton(text="➕ Yangi bot yaratish", callback_data="create_bot")],
        [InlineKeyboardButton(text="📊 Statistika", callback_data="statistics")],
        [InlineKeyboardButton(text="💰 Balans", callback_data="balance")],
        [InlineKeyboardButton(text="🔧 Sozlamalar", callback_data="settings")],
        [InlineKeyboardButton(text="❓ Yordam", callback_data="help")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

async def create_bot_menu():
    buttons = [
        [InlineKeyboardButton(text="📝 Bot tokenini kiriting", callback_data="enter_token")],
        [InlineKeyboardButton(text="❓ Token qanday olish?", callback_data="token_help")],
        [InlineKeyboardButton(text="◀️ Orqaga", callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

async def bot_modules_menu():
    buttons = [
        [InlineKeyboardButton(text="💸 Referral tizimi", callback_data="toggle_refs")],
        [InlineKeyboardButton(text="🎬 Kino bot", callback_data="toggle_kino")],
        [InlineKeyboardButton(text="🎵 Musiqa bot", callback_data="toggle_music")],
        [InlineKeyboardButton(text="📥 Download bot", callback_data="toggle_download")],
        [InlineKeyboardButton(text="💬 ChatGPT", callback_data="toggle_chatgpt")],
        [InlineKeyboardButton(text="❤️ Tanishuv (Leo)", callback_data="toggle_leo")],
        [InlineKeyboardButton(text="🔮 Munajjimlik", callback_data="toggle_horoscope")],
        [InlineKeyboardButton(text="👤 Anonim chat", callback_data="toggle_anon")],
        [InlineKeyboardButton(text="📱 SMS yuborish", callback_data="toggle_sms")]
    ]
    buttons.append([InlineKeyboardButton(text="✅ Saqlash", callback_data="save_bot_config")])
    buttons.append([InlineKeyboardButton(text="◀️ Orqaga", callback_data="back_to_main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)
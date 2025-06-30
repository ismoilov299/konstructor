from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton


async def get_davinci_main_menu():
    """Main davinci menu keyboard"""
    buttons = [
        [InlineKeyboardButton(text="👤 Моя анкета", callback_data="my_profile")],
        [InlineKeyboardButton(text="🚀 Смотреть анкеты", callback_data="view_profiles")],
        [InlineKeyboardButton(text="💌 Мои лайки", callback_data="my_likes")],
        [InlineKeyboardButton(text="💖 Мои матчи", callback_data="my_matches")],
        [InlineKeyboardButton(text="👑 Boost", callback_data="boost_menu")],
        [InlineKeyboardButton(text="⚙️ Настройки", callback_data="settings")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


async def get_registration_kb():
    """Registration start keyboard"""
    buttons = [
        [InlineKeyboardButton(text="📝 Создать анкету", callback_data="start_registration")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


async def get_profile_kb():
    """Profile management keyboard"""
    buttons = [
        [InlineKeyboardButton(text="✏️ Редактировать", callback_data="edit_profile")],
        [InlineKeyboardButton(text="🔄 Обновить фото", callback_data="update_photo")],
        [InlineKeyboardButton(text="👁️ Включить/выключить поиск", callback_data="toggle_search")],
        [InlineKeyboardButton(text="🗑️ Удалить анкету", callback_data="delete_profile")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


async def get_rate_kb():
    """Rating keyboard for profiles"""
    buttons = [
        [
            InlineKeyboardButton(text="❤️ Лайк", callback_data="davinci_like"),
            InlineKeyboardButton(text="💔 Пропустить", callback_data="davinci_dislike")
        ],
        [InlineKeyboardButton(text="⭐ Супер-лайк", callback_data="davinci_super_like")],
        [InlineKeyboardButton(text="🚫 Пожаловаться", callback_data="davinci_report")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


async def get_boost_kb():
    """Boost options keyboard"""
    buttons = [
        [InlineKeyboardButton(text="🚀 Поднять анкету в топ", callback_data="boost_top")],
        [InlineKeyboardButton(text="⭐ Супер-лайки", callback_data="boost_super_likes")],
        [InlineKeyboardButton(text="👁️ Кто меня лайкнул", callback_data="boost_who_liked")],
        [InlineKeyboardButton(text="💫 VIP статус", callback_data="boost_vip")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


async def get_edit_profile_kb():
    """Edit profile keyboard"""
    buttons = [
        [InlineKeyboardButton(text="📝 Изменить имя", callback_data="edit_name")],
        [InlineKeyboardButton(text="🎂 Изменить возраст", callback_data="edit_age")],
        [InlineKeyboardButton(text="🏙️ Изменить город", callback_data="edit_city")],
        [InlineKeyboardButton(text="💭 Изменить описание", callback_data="edit_about")],
        [InlineKeyboardButton(text="📸 Изменить фото", callback_data="edit_photo")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_profile")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# Gender selection keyboard
def get_gender_kb():
    """Gender selection keyboard"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="👨 Мужской")],
            [KeyboardButton(text="👩 Женский")]
        ],
        resize_keyboard=True
    )


# Search preference keyboard
def get_search_preference_kb():
    """Search preference keyboard"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="👨 Парней")],
            [KeyboardButton(text="👩 Девушек")],
            [KeyboardButton(text="👥 Всех")]
        ],
        resize_keyboard=True
    )

import logging
from aiogram import Router, F, Bot
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from modul.clientbot import shortcuts
from modul.clientbot.handlers.davinci_bot.admin.admin_filters import AdminFilter
from modul.clientbot.handlers.davinci_bot.admin.admin_states import AdminDavinciStates
from modul.clientbot.handlers.davinci_bot.services.davinci_service import get_or_create_davinci_profile
from modul.clientbot.handlers.davinci_bot.admin.admin_service import (
    get_pending_profiles, approve_profile, reject_profile,
    get_davinci_stats, add_stop_word, remove_stop_word
)

logger = logging.getLogger(__name__)

admin_davinci_router = Router()


@admin_davinci_router.message(F.text == "/davinci_admin", AdminFilter())
async def davinci_admin_menu(message: Message):
    """Davinci admin menu"""
    buttons = [
        [InlineKeyboardButton(text="📋 Модерация анкет", callback_data="moderate_profiles")],
        [InlineKeyboardButton(text="📊 Статистика", callback_data="davinci_stats")],
        [InlineKeyboardButton(text="🚫 Стоп-слова", callback_data="stop_words")],
        [InlineKeyboardButton(text="👥 Поиск пользователя", callback_data="find_user")],
        [InlineKeyboardButton(text="❌ Закрыть", callback_data="cancel")]
    ]

    await message.answer(
        "🔧 Админ панель Davinci знакомств:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )


@admin_davinci_router.callback_query(F.data == "moderate_profiles", AdminFilter())
async def show_pending_profiles(callback: CallbackQuery, bot: Bot):
    """Show profiles pending moderation"""
    bot_db = await shortcuts.get_bot(bot)
    pending_profiles = await get_pending_profiles(bot_db.username)

    if not pending_profiles:
        await callback.message.edit_text(
            "✅ Нет анкет на модерации",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_admin")]
            ])
        )
        return

    profile = pending_profiles[0]

    profile_text = (
        f"👤 Анкета на модерации:\n\n"
        f"📝 Имя: {profile.full_name}\n"
        f"🎂 Возраст: {profile.age}\n"
        f"👥 Пол: {profile.sex}\n"
        f"🏙️ Город: {profile.city}\n"
        f"🔍 Ищет: {profile.which_search}\n"
        f"💭 О себе: {profile.about_me}\n\n"
        f"🆔 ID: {profile.id}\n"
        f"📅 Создана: {profile.created_at.strftime('%d.%m.%Y %H:%M')}"
    )

    buttons = [
        [
            InlineKeyboardButton(text="✅ Одобрить", callback_data=f"approve_{profile.id}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_{profile.id}")
        ],
        [InlineKeyboardButton(text="⏭️ Следующая", callback_data="next_profile")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_admin")]
    ]

    if profile.photo:
        await callback.message.edit_media(
            media=callback.message.photo[0] if callback.message.photo else None,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
        )
        await callback.message.edit_caption(
            caption=profile_text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
        )
    else:
        await callback.message.edit_text(
            profile_text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
        )


@admin_davinci_router.callback_query(F.data.startswith("approve_"), AdminFilter())
async def approve_profile_handler(callback: CallbackQuery, bot: Bot):
    """Approve profile"""
    profile_id = int(callback.data.split("_")[1])
    bot_db = await shortcuts.get_bot(bot)

    success = await approve_profile(profile_id, bot_db.username)

    if success:
        await callback.answer("✅ Анкета одобрена!")
        # Show next profile or go back
        await show_pending_profiles(callback, bot)
    else:
        await callback.answer("❌ Ошибка при одобрении", show_alert=True)


@admin_davinci_router.callback_query(F.data.startswith("reject_"), AdminFilter())
async def reject_profile_handler(callback: CallbackQuery, bot: Bot):
    """Reject profile"""
    profile_id = int(callback.data.split("_")[1])
    bot_db = await shortcuts.get_bot(bot)

    success = await reject_profile(profile_id, bot_db.username)

    if success:
        await callback.answer("❌ Анкета отклонена!")
        # Show next profile or go back
        await show_pending_profiles(callback, bot)
    else:
        await callback.answer("❌ Ошибка при отклонении", show_alert=True)


@admin_davinci_router.callback_query(F.data == "davinci_stats", AdminFilter())
async def show_davinci_stats(callback: CallbackQuery, bot: Bot):
    """Show davinci statistics"""
    bot_db = await shortcuts.get_bot(bot)
    stats = await get_davinci_stats(bot_db.username)

    stats_text = (
        f"📊 Статистика Davinci знакомств:\n\n"
        f"👥 Всего анкет: {stats.get('total_profiles', 0)}\n"
        f"✅ Одобренных: {stats.get('approved_profiles', 0)}\n"
        f"⏳ На модерации: {stats.get('pending_profiles', 0)}\n"
        f"🚫 Заблокированных: {stats.get('blocked_profiles', 0)}\n"
        f"🔍 Активно ищут: {stats.get('active_searchers', 0)}\n\n"
        f"❤️ Всего лайков: {stats.get('total_likes', 0)}\n"
        f"💖 Взаимных лайков: {stats.get('mutual_likes', 0)}\n"
        f"👨 Мужчин: {stats.get('male_profiles', 0)}\n"
        f"👩 Женщин: {stats.get('female_profiles', 0)}"
    )

    await callback.message.edit_text(
        stats_text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Обновить", callback_data="davinci_stats")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_admin")]
        ])
    )
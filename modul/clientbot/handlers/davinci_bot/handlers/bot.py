import asyncio
import json
import logging
import random
from datetime import datetime, timedelta

from aiogram import Router, F, Bot
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton
from asgiref.sync import sync_to_async

from modul.clientbot import shortcuts
from modul.clientbot.handlers.davinci_bot.handlers.states import (
    DavinciRegistration, DavinciEditProfile, DavinciBoostForm
)
from modul.clientbot.handlers.davinci_bot.keyboards.buttons import (
    get_davinci_main_menu, get_registration_kb, get_profile_kb,
    get_boost_kb, get_rate_kb, get_edit_profile_kb
)
from modul.clientbot.handlers.davinci_bot.services.davinci_service import (
    get_or_create_davinci_profile, update_davinci_profile,
    get_davinci_profiles_for_viewing, rate_profile, check_mutual_like,
    get_likes_received, get_matches
)
from modul.loader import client_bot_router
from modul.models import LeoMatchModel, LeoMatchLikesBasketModel, DavinciStopWords
from modul.clientbot.handlers.davinci_bot.utils.validators import (
    validate_age, validate_name, validate_about_me, check_stop_words
)

logger = logging.getLogger(__name__)




class DavinciBotFilter:

    """Filter for davinci bot functionality"""

    async def __call__(self, message: Message, bot: Bot) -> bool:
        bot_db = await shortcuts.get_bot(bot)
        print(bot_db," davinci bot filter")
        return shortcuts.have_one_module(bot_db, "davinci")

def davinchi_bot_handlers():
    @client_bot_router.message(F.text == "🫰 Знакомства", DavinciBotFilter())
    async def davinci_start(message: Message, bot: Bot, state: FSMContext):
        """Main davinci start handler"""
        print("Starting Davinci bot handler")
        await state.clear()

        bot_db = await shortcuts.get_bot(bot)
        user_profile = await get_or_create_davinci_profile(
            user_id=message.from_user.id,
            bot_username=bot_db.username
        )

        if not user_profile or not user_profile.admin_checked:
            # Redirect to registration if no profile or not approved
            await message.answer(
                "👋 Добро пожаловать в Davinci знакомства!\n\n"
                "Давайте создадим вашу анкету для поиска интересных людей.",
                reply_markup=await get_registration_kb()
            )
            await state.set_state(DavinciRegistration.waiting_for_start)
        else:
            # Show main menu
            await message.answer(
                f"🫰 Привет, {user_profile.full_name}!\n\n"
                "Добро пожаловать в Davinci знакомства! 💫\n"
                "Что будем делать?",
                reply_markup=await get_davinci_main_menu()
            )


@client_bot_router.message(F.text == "👤 Моя анкета", DavinciBotFilter())
async def show_my_profile(message: Message, bot: Bot):
    """Show user's profile"""
    bot_db = await shortcuts.get_bot(bot)
    user_profile = await get_or_create_davinci_profile(
        user_id=message.from_user.id,
        bot_username=bot_db.username
    )

    if not user_profile:
        await message.answer("❌ У вас нет анкеты. Создайте её сначала!")
        return

    profile_text = (
        f"👤 Ваша анкета:\n\n"
        f"📝 Имя: {user_profile.full_name}\n"
        f"🎂 Возраст: {user_profile.age}\n"
        f"👥 Пол: {user_profile.sex}\n"
        f"🏙️ Город: {user_profile.city}\n"
        f"🔍 Ищу: {user_profile.which_search}\n"
        f"💭 О себе: {user_profile.about_me}\n\n"
        f"❤️ Лайков получено: {user_profile.count_likes}\n"
        f"✅ Статус: {'Одобрена' if user_profile.admin_checked else 'На модерации'}"
    )

    if user_profile.photo:
        await message.answer_photo(
            photo=user_profile.photo,
            caption=profile_text,
            reply_markup=await get_profile_kb()
        )
    else:
        await message.answer(
            profile_text,
            reply_markup=await get_profile_kb()
        )


@client_bot_router.message(F.text == "🚀 Смотреть анкеты", DavinciBotFilter())
async def view_profiles(message: Message, bot: Bot, state: FSMContext):
    """Start viewing profiles"""
    bot_db = await shortcuts.get_bot(bot)
    user_profile = await get_or_create_davinci_profile(
        user_id=message.from_user.id,
        bot_username=bot_db.username
    )

    if not user_profile or not user_profile.admin_checked:
        await message.answer("❌ Ваша анкета не одобрена или не создана!")
        return

    profiles = await get_davinci_profiles_for_viewing(
        user_profile=user_profile,
        bot_username=bot_db.username
    )

    if not profiles:
        await message.answer(
            "😔 Больше нет анкет для просмотра.\n"
            "Попробуйте позже!"
        )
        return

    # Show first profile
    profile = profiles[0]
    await show_profile_for_rating(message, profile, state)


async def show_profile_for_rating(message: Message, profile: LeoMatchModel, state: FSMContext):
    """Show profile for rating"""
    await state.update_data(current_profile_id=profile.id)

    profile_text = (
        f"👤 {profile.full_name}, {profile.age}\n"
        f"🏙️ {profile.city}\n"
        f"💭 {profile.about_me}"
    )

    if profile.photo:
        await message.answer_photo(
            photo=profile.photo,
            caption=profile_text,
            reply_markup=await get_rate_kb()
        )
    else:
        await message.answer(
            profile_text,
            reply_markup=await get_rate_kb()
        )


@client_bot_router.message(F.text == "👑 Boost", DavinciBotFilter())
async def boost_menu(message: Message, bot: Bot):
    """Show boost options"""
    await message.answer(
        "👑 Boost функции:\n\n"
        "🚀 Поднять анкету в топ\n"
        "⭐ Супер-лайк\n"
        "👁️ Кто меня лайкнул\n"
        "💫 VIP статус",
        reply_markup=await get_boost_kb()
    )


# Registration handlers
@client_bot_router.message(StateFilter(DavinciRegistration.waiting_for_start))
async def start_registration(message: Message, state: FSMContext):
    """Start registration process"""
    await message.answer(
        "📝 Давайте создадим вашу анкету!\n\n"
        "Введите ваше имя (максимум 15 символов):"
    )
    await state.set_state(DavinciRegistration.waiting_for_name)


@client_bot_router.message(StateFilter(DavinciRegistration.waiting_for_name))
async def process_name(message: Message, state: FSMContext):
    """Process name input"""
    name = message.text.strip()

    if not validate_name(name):
        await message.answer(
            "❌ Имя должно содержать от 2 до 15 символов и состоять только из букв.\n"
            "Попробуйте еще раз:"
        )
        return

    if await check_stop_words(name):
        await message.answer(
            "❌ Имя содержит недопустимые слова.\n"
            "Попробуйте другое имя:"
        )
        return

    await state.update_data(full_name=name)
    await message.answer(
        "🎂 Укажите ваш возраст (от 16 до 100 лет):"
    )
    await state.set_state(DavinciRegistration.waiting_for_age)


@client_bot_router.message(StateFilter(DavinciRegistration.waiting_for_age))
async def process_age(message: Message, state: FSMContext):
    """Process age input"""
    try:
        age = int(message.text.strip())
        if not validate_age(age):
            raise ValueError
    except ValueError:
        await message.answer(
            "❌ Возраст должен быть числом от 16 до 100 лет.\n"
            "Попробуйте еще раз:"
        )
        return

    await state.update_data(age=age)

    # Gender selection keyboard
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="👨 Мужской")],
            [KeyboardButton(text="👩 Женский")]
        ],
        resize_keyboard=True
    )

    await message.answer(
        "👥 Выберите ваш пол:",
        reply_markup=kb
    )
    await state.set_state(DavinciRegistration.waiting_for_sex)


@client_bot_router.message(StateFilter(DavinciRegistration.waiting_for_sex))
async def process_sex(message: Message, state: FSMContext):
    """Process gender selection"""
    text = message.text.strip()

    if text == "👨 Мужской":
        sex = "male"
    elif text == "👩 Женский":
        sex = "female"
    else:
        await message.answer("❌ Выберите пол из предложенных вариантов.")
        return

    await state.update_data(sex=sex)

    # Search preference keyboard
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="👨 Парней")],
            [KeyboardButton(text="👩 Девушек")],
            [KeyboardButton(text="👥 Всех")]
        ],
        resize_keyboard=True
    )

    await message.answer(
        "🔍 Кого вы ищете?",
        reply_markup=kb
    )
    await state.set_state(DavinciRegistration.waiting_for_search_preference)


@client_bot_router.message(StateFilter(DavinciRegistration.waiting_for_search_preference))
async def process_search_preference(message: Message, state: FSMContext):
    """Process search preference"""
    text = message.text.strip()

    if text == "👨 Парней":
        which_search = "male"
    elif text == "👩 Девушек":
        which_search = "female"
    elif text == "👥 Всех":
        which_search = "all"
    else:
        await message.answer("❌ Выберите вариант из предложенных.")
        return

    await state.update_data(which_search=which_search)
    await message.answer(
        "🏙️ Введите ваш город:",
        # reply_markup=shortcuts.cancel()
    )
    await state.set_state(DavinciRegistration.waiting_for_city)


@client_bot_router.message(StateFilter(DavinciRegistration.waiting_for_city))
async def process_city(message: Message, state: FSMContext):
    """Process city input"""
    city = message.text.strip()

    if len(city) < 2 or len(city) > 50:
        await message.answer(
            "❌ Название города должно содержать от 2 до 50 символов.\n"
            "Попробуйте еще раз:"
        )
        return

    if await check_stop_words(city):
        await message.answer(
            "❌ Название города содержит недопустимые слова.\n"
            "Попробуйте другой город:"
        )
        return

    await state.update_data(city=city)
    await message.answer(
        "💭 Расскажите о себе (максимум 300 символов):"
    )
    await state.set_state(DavinciRegistration.waiting_for_about)


@client_bot_router.message(StateFilter(DavinciRegistration.waiting_for_about))
async def process_about(message: Message, state: FSMContext):
    """Process about me text"""
    about_me = message.text.strip()

    if not validate_about_me(about_me):
        await message.answer(
            "❌ Описание должно содержать от 10 до 300 символов.\n"
            "Попробуйте еще раз:"
        )
        return

    if await check_stop_words(about_me):
        await message.answer(
            "❌ Описание содержит недопустимые слова.\n"
            "Попробуйте другое описание:"
        )
        return

    await state.update_data(about_me=about_me)
    await message.answer(
        "📸 Отправьте ваше фото:"
    )
    await state.set_state(DavinciRegistration.waiting_for_photo)


@client_bot_router.message(StateFilter(DavinciRegistration.waiting_for_photo))
async def process_photo(message: Message, state: FSMContext, bot: Bot):
    """Process photo upload"""
    if not message.photo:
        await message.answer(
            "❌ Пожалуйста, отправьте фотографию."
        )
        return

    # Get the largest photo
    photo = message.photo[-1].file_id

    # Get registration data
    data = await state.get_data()

    # Create profile
    bot_db = await shortcuts.get_bot(bot)

    try:
        profile = await update_davinci_profile(
            user_id=message.from_user.id,
            bot_username=bot_db.username,
            **data,
            photo=photo,
            media_type="photo"
        )

        await state.clear()

        await message.answer(
            "✅ Анкета создана успешно!\n\n"
            "📋 Ваша анкета отправлена на модерацию.\n"
            "⏰ Обычно проверка занимает до 24 часов.\n\n"
            "Мы уведомим вас, когда анкета будет одобрена!",
            reply_markup=await get_davinci_main_menu()
        )

    except Exception as e:
        logger.error(f"Error creating davinci profile: {e}")
        await message.answer(
            "❌ Произошла ошибка при создании анкеты.\n"
            "Попробуйте еще раз позже."
        )
        await state.clear()


# Callback handlers
@client_bot_router.callback_query(F.data == "davinci_like")
async def process_like(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Process like action"""
    data = await state.get_data()
    profile_id = data.get('current_profile_id')

    if not profile_id:
        await callback.answer("❌ Ошибка: профиль не найден")
        return

    bot_db = await shortcuts.get_bot(bot)
    user_profile = await get_or_create_davinci_profile(
        user_id=callback.from_user.id,
        bot_username=bot_db.username
    )

    if not user_profile:
        await callback.answer("❌ У вас нет анкеты")
        return

    # Process like
    is_mutual = await rate_profile(
        from_user_profile=user_profile,
        to_profile_id=profile_id,
        like_type="like"
    )

    if is_mutual:
        await callback.answer("💖 Взаимная симпатия! Вы можете общаться!", show_alert=True)
    else:
        await callback.answer("👍 Лайк отправлен!")

    # Show next profile
    await show_next_profile(callback.message, user_profile, bot_db.username, state)


@client_bot_router.callback_query(F.data == "davinci_dislike")
async def process_dislike(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Process dislike action"""
    data = await state.get_data()
    profile_id = data.get('current_profile_id')

    if not profile_id:
        await callback.answer("❌ Ошибка: профиль не найден")
        return

    bot_db = await shortcuts.get_bot(bot)
    user_profile = await get_or_create_davinci_profile(
        user_id=callback.from_user.id,
        bot_username=bot_db.username
    )

    # Process dislike
    await rate_profile(
        from_user_profile=user_profile,
        to_profile_id=profile_id,
        like_type="dislike"
    )

    await callback.answer("👎 Пропущено")

    # Show next profile
    await show_next_profile(callback.message, user_profile, bot_db.username, state)


async def show_next_profile(message: Message, user_profile: LeoMatchModel, bot_username: str, state: FSMContext):
    """Show next profile for rating"""
    profiles = await get_davinci_profiles_for_viewing(
        user_profile=user_profile,
        bot_username=bot_username
    )

    if not profiles:
        await message.edit_text(
            "😔 Больше нет анкет для просмотра.\n"
            "Попробуйте позже!"
        )
        return

    # Show first profile
    profile = profiles[0]
    await state.update_data(current_profile_id=profile.id)

    profile_text = (
        f"👤 {profile.full_name}, {profile.age}\n"
        f"🏙️ {profile.city}\n"
        f"💭 {profile.about_me}"
    )

    try:
        if profile.photo:
            await message.edit_media(
                media=message.photo[0].file_id,
                reply_markup=await get_rate_kb()
            )
            await message.edit_caption(
                caption=profile_text,
                reply_markup=await get_rate_kb()
            )
        else:
            await message.edit_text(
                profile_text,
                reply_markup=await get_rate_kb()
            )
    except Exception as e:
        logger.error(f"Error editing message: {e}")
        # Fallback: send new message
        if profile.photo:
            await message.answer_photo(
                photo=profile.photo,
                caption=profile_text,
                reply_markup=await get_rate_kb()
            )
        else:
            await message.answer(
                profile_text,
                reply_markup=await get_rate_kb()
            )
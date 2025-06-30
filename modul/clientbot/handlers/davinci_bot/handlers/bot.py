from aiogram import Bot, types, F
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton, \
    ReplyKeyboardRemove
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

# Hozirgi loyiha imports
from modul.loader import client_bot_router, main_bot
from modul.models import User
from asgiref.sync import sync_to_async
import json
import time
import re
import datetime
import hashlib
import hmac
import requests
import urllib.request


# FSM States
class DavinciStates(StatesGroup):
    ANKET_SEX = State()
    ANKET_AGE = State()
    ANKET_SEARCH = State()
    ANKET_NAME = State()
    ANKET_CITY = State()
    ANKET_ABOUT_ME = State()
    ANKET_GALLERY = State()
    EDIT_AGE = State()
    EDIT_SEX = State()
    EDIT_SEARCH = State()
    EDIT_NAME = State()
    EDIT_CITY = State()
    EDIT_ABOUT_ME = State()
    EDIT_GALLERY = State()
    SEND_MESSAGE = State()
    RATE_VIEW = State()
    COUPLE_VIEW = State()


# Database functions (qisqartirilgan - to'liq versiyani keyin beramiz)
@sync_to_async
def get_user_davinci(user_id):
    """Davinci ma'lumotlarini olish"""
    try:
        user = User.objects.get(uid=user_id)
        return {
            'user_id': user.uid,
            'first_name': user.first_name or '',
            'username': user.username or '',
            'davinci_ban': getattr(user, 'davinci_ban', 0),
            'davinci_ban_list': getattr(user, 'davinci_ban_list', ''),
            'davinci_check': getattr(user, 'davinci_check', 0),
            'davinci_couple_stop': getattr(user, 'davinci_couple_stop', 0),
            'davinci_anket_active': getattr(user, 'davinci_anket_active', 0),
            'davinci_anket_name': getattr(user, 'davinci_anket_name', ''),
            'davinci_anket_sex': getattr(user, 'davinci_anket_sex', 0),
            'davinci_anket_search': getattr(user, 'davinci_anket_search', 0),
            'davinci_anket_age': getattr(user, 'davinci_anket_age', 0),
            'davinci_anket_city': getattr(user, 'davinci_anket_city', ''),
            'davinci_anket_aboutme': getattr(user, 'davinci_anket_aboutme', ''),
            'davinci_anket_gallary': getattr(user, 'davinci_anket_gallary', '[]'),
            'davinci_rate_list': getattr(user, 'davinci_rate_list', '|'),
        }
    except User.DoesNotExist:
        return None


@sync_to_async
def update_user_davinci(user_id, data):
    """Davinci ma'lumotlarini yangilash"""
    try:
        user = User.objects.get(uid=user_id)
        for key, value in data.items():
            setattr(user, key, value)
        user.save()
        return True
    except User.DoesNotExist:
        return False


# Helper functions
async def davinci_sex_my(sex, only_smile=False):
    sex = int(sex) if sex else 0
    if sex == 1:
        text = "🙎‍♂️ "
        if not only_smile:
            text += "Я парень"
    elif sex == 2:
        text = "🙍‍♀️ "
        if not only_smile:
            text += "Я девушка"
    else:
        text = "🚫 не указано"
    return text


async def davinci_search(search):
    search = int(search) if search else 0
    if search == 1:
        text = "🙎‍♂️ Парни"
    elif search == 2:
        text = "🙍‍♀️ Девушки"
    elif search == 3:
        text = "Всех"
    else:
        text = "🚫 не указано"
    return text


async def create_age_keyboard(age_range, next_page):
    """Возраст для выбора клавиатурасини yaratish"""
    builder = InlineKeyboardBuilder()
    age_list = age_range.split('-')

    buttons = []
    for i in range(int(age_list[0]), int(age_list[1]) + 1):
        buttons.append(InlineKeyboardButton(
            text=str(i),
            callback_data=f"davinci_anketAge3_{i}_{next_page}"
        ))

        if len(buttons) >= 6:
            builder.row(*buttons)
            buttons = []

    if buttons:
        builder.row(*buttons)

    return builder.as_markup()


async def create_anket_message(user_data):
    """Anketani ko'rsatish uchun xabar yaratish"""
    text = ""
    media_group = []

    # Gallery'ni parse qilish
    gallery = user_data.get('davinci_anket_gallary', '[]')
    if isinstance(gallery, str):
        try:
            gallery = json.loads(gallery)
        except:
            gallery = []

    # Matnni yaratish
    sex_text = await davinci_sex_my(user_data.get('davinci_anket_sex', 0), only_smile=True)
    name = user_data.get('davinci_anket_name', '')
    age = user_data.get('davinci_anket_age', '')
    city = user_data.get('davinci_anket_city', '')
    about_me = user_data.get('davinci_anket_aboutme', '')

    text += f"{sex_text} <b>{name}</b>"
    if age:
        text += f", {age}"
    if city:
        text += f", {city.title()}"
    if about_me:
        text += f" - {about_me.strip()}"

    return {
        'text': text,
        'media': gallery
    }


# Commands
@client_bot_router.message(Command('view'))
async def cmd_view(message: types.Message, state: FSMContext):
    """Anketalarni ko'rish"""
    await davinci_rate_start(message, state)


@client_bot_router.message(Command('anket'))
async def cmd_anket(message: types.Message, state: FSMContext):
    """Mening anketam"""
    await davinci_account(message, state)


@client_bot_router.message(Command('boost'))
async def cmd_boost(message: types.Message, state: FSMContext):
    """Boost funksiyasi"""
    await davinci_boost(message, state)


# Main handlers
@client_bot_router.message(F.text == "🚀 Смотреть анкеты")
async def davinci_rate_handler(message: types.Message, state: FSMContext):
    await davinci_rate_start(message, state)


@client_bot_router.message(F.text == "👤 Моя анкета")
async def davinci_account_handler(message: types.Message, state: FSMContext):
    await davinci_account(message, state)


@client_bot_router.message(F.text == "👑 Boost")
async def davinci_boost_handler(message: types.Message, state: FSMContext):
    await davinci_boost(message, state)


# Callback handlers
@client_bot_router.callback_query(F.data.startswith('davinci_'))
async def davinci_callback(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()

    # Callback data'ni parse qilish
    parts = callback.data.split('_')
    if len(parts) < 2:
        return

    action = parts[1]

    if action == 'anketSex':
        sex = parts[2]
        next_page = parts[3] if len(parts) > 3 else 'anketAge'
        await update_user_davinci(callback.from_user.id, {'davinci_anket_sex': int(sex)})

        if next_page == 'anketAge':
            await davinci_anket_age(callback.message, state)
        elif next_page == 'account':
            await davinci_account(callback.message, state)

    elif action == 'anketAge2':
        age_range = parts[2]
        next_page = parts[3]

        keyboard = await create_age_keyboard(age_range, next_page)
        await callback.message.edit_text(
            "Сколько тебе лет?",
            reply_markup=keyboard
        )

    elif action == 'anketAge3':
        age = parts[2]
        next_page = parts[3]
        await update_user_davinci(callback.from_user.id, {'davinci_anket_age': int(age)})

        if next_page == 'anketSearch':
            await davinci_anket_search(callback.message, state)
        elif next_page == 'account':
            await davinci_account(callback.message, state)

    elif action == 'anketSearch':
        search = parts[2]
        next_page = parts[3] if len(parts) > 3 else 'anketName'
        await update_user_davinci(callback.from_user.id, {'davinci_anket_search': int(search)})

        if next_page == 'anketName':
            await davinci_anket_name(callback.message, state)
        elif next_page == 'account':
            await davinci_account(callback.message, state)

    elif action == 'go':
        await davinci_main_menu(callback.message, state)


# Main functions
async def davinci_main_menu(message: types.Message, state: FSMContext):
    """Asosiy menyu"""
    user_data = await get_user_davinci(message.from_user.id)

    if not user_data:
        # Yangi foydalanuvchi uchun ma'lumot yaratish
        await message.answer("Добро пожаловать в Дайвинчик! Давайте создадим вашу анкету.")
        await davinci_anket_sex(message, state)
        return

    # Anketa to'liqligini tekshirish
    if not user_data['davinci_anket_active']:
        if not user_data['davinci_anket_sex']:
            await davinci_anket_sex(message, state)
            return
        elif not user_data['davinci_anket_age']:
            await davinci_anket_age(message, state)
            return
        # Va hokazo...

    # Asosiy menyu
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text="🚀 Смотреть анкеты"),
        KeyboardButton(text="👑 Boost")
    )
    builder.row(
        KeyboardButton(text="👤 Моя анкета"),
        KeyboardButton(text="💎 VIP")
    )

    await message.answer(
        "Выберите действие:",
        reply_markup=builder.as_markup(resize_keyboard=True)
    )


async def davinci_anket_sex(message: types.Message, state: FSMContext):
    """Jins tanlash"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text=await davinci_sex_my(1),
            callback_data="davinci_anketSex_1_anketAge"
        ),
        InlineKeyboardButton(
            text=await davinci_sex_my(2),
            callback_data="davinci_anketSex_2_anketAge"
        )
    )

    await message.answer(
        "Выбери свой пол",
        reply_markup=builder.as_markup()
    )
    await state.set_state(DavinciStates.ANKET_SEX)


async def davinci_anket_age(message: types.Message, state: FSMContext):
    """Yosh tanlash"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text='16-20', callback_data="davinci_anketAge2_16-20_anketSearch"),
        InlineKeyboardButton(text='21-30', callback_data="davinci_anketAge2_21-30_anketSearch"),
    )
    builder.row(
        InlineKeyboardButton(text='31-50', callback_data="davinci_anketAge2_31-50_anketSearch"),
        InlineKeyboardButton(text='51-80', callback_data="davinci_anketAge2_51-80_anketSearch"),
    )
    builder.row(
        InlineKeyboardButton(text='81-99', callback_data="davinci_anketAge2_81-99_anketSearch")
    )

    await message.answer(
        "Сколько тебе лет?",
        reply_markup=builder.as_markup()
    )
    await state.set_state(DavinciStates.ANKET_AGE)


async def davinci_anket_search(message: types.Message, state: FSMContext):
    """Qidirish parametrlari"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text=await davinci_search(1),
            callback_data="davinci_anketSearch_1_anketName"
        ),
        InlineKeyboardButton(
            text=await davinci_search(3),
            callback_data="davinci_anketSearch_3_anketName"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=await davinci_search(2),
            callback_data="davinci_anketSearch_2_anketName"
        )
    )

    await message.answer(
        "Кто тебе интересен?",
        reply_markup=builder.as_markup()
    )
    await state.set_state(DavinciStates.ANKET_SEARCH)


async def davinci_anket_name(message: types.Message, state: FSMContext):
    """Ism kiritish"""
    user_data = await get_user_davinci(message.from_user.id)

    builder = InlineKeyboardBuilder()
    if user_data and user_data.get('first_name'):
        builder.row(
            InlineKeyboardButton(
                text=user_data['first_name'],
                callback_data="davinci_anketNameFirstname_anketCity"
            )
        )

    await message.answer(
        "Как мне тебя называть?",
        reply_markup=builder.as_markup() if builder else None
    )
    await state.set_state(DavinciStates.ANKET_NAME)


async def davinci_rate_start(message: types.Message, state: FSMContext):
    """Anketalarni baholashni boshlash"""
    await message.answer("🔍 Ищем анкеты для вас...")
    # Bu yerda anketalarni qidirish logikasi bo'ladi
    await state.set_state(DavinciStates.RATE_VIEW)


async def davinci_account(message: types.Message, state: FSMContext):
    """Foydalanuvchi anketasini ko'rsatish"""
    user_data = await get_user_davinci(message.from_user.id)

    if not user_data or not user_data['davinci_anket_active']:
        await message.answer("У вас пока нет анкеты. Давайте создадим!")
        await davinci_anket_sex(message, state)
        return

    # Anketani ko'rsatish
    anket_data = await create_anket_message(user_data)

    # Media yuborish
    if anket_data['media']:
        # Bu yerda media group yuborish logikasi
        pass

    # Tugmalar
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="Изменить имя", callback_data="davinci_editName"),
        InlineKeyboardButton(text="Изменить пол", callback_data="davinci_editSex")
    )
    builder.row(
        InlineKeyboardButton(text="Изменить возраст", callback_data="davinci_editAge"),
        InlineKeyboardButton(text='Изменить "о себе"', callback_data="davinci_editAboutMe")
    )
    builder.row(
        InlineKeyboardButton(text="Изменить фото", callback_data="davinci_editGallary"),
        InlineKeyboardButton(text="Изменить город", callback_data="davinci_editCity")
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Назад", callback_data="davinci_go")
    )

    await message.answer(
        f"⬆️ Ваша анкета ⬆️\n\n{anket_data['text']}",
        reply_markup=builder.as_markup()
    )


async def davinci_boost(message: types.Message, state: FSMContext):
    """Boost funksiyasi"""
    user_id = message.from_user.id

    # 14 kunlik statistika (bu yerda ma'lumotlar bazasidan olish kerak)
    count_ref = 0  # Referallar soni
    count_bon = count_ref * 20 if count_ref <= 5 else 100

    text = "Пригласи друзей и получи больше лайков!"
    text += "\n\nТвоя статистика"
    text += f"\nПришло за 14 дней: {count_ref}"
    text += f"\nБонус к силе анкеты: {count_bon}%"
    text += "\n\nПерешли друзьям или размести в своих соцсетях."
    text += "\nВот твоя личная ссылка 👇"

    await message.answer(text)

    # Referral havolasi
    bot_username = "your_bot_username"  # Bu yerda bot username'ini olish kerak
    link_text = "Бот знакомств Дайвинчик🍷 в Telegram! Найдет друзей или даже половинку 👫"
    link_text += f"\n👉 https://t.me/{bot_username}?start=u{user_id}"

    await message.answer(link_text)


# Text handlers
@client_bot_router.message(DavinciStates.ANKET_NAME)
async def handle_anket_name(message: types.Message, state: FSMContext):
    """Ism kiritishni qayta ishlash"""
    text = message.text

    # Validatsiya
    if re.search(r"[@|\/][a-z|A-Z|0-9|_]{3,}", text) or re.search(r"[a-z|A-Z|0-9|_]{2,}bot", text):
        await message.answer("❌ Ссылки запрещены")
        return

    if not re.search(r"^[a-z|A-Z|а-я|А-Я|ё|Ё|\s]{1,}$", text):
        await message.answer("❌ Разрешены только буквы и пробел")
        return

    # Ismni saqlash
    if len(text) > 100:
        text = f'{text[:100]}...'

    text = text.replace('>', '»').replace('<', '«')
    await update_user_davinci(message.from_user.id, {'davinci_anket_name': text})

    # Keyingi bosqichga o'tish
    await message.answer("Отлично! Теперь введите ваш город.")
    await state.set_state(DavinciStates.ANKET_CITY)


@client_bot_router.message(DavinciStates.ANKET_CITY)
async def handle_anket_city(message: types.Message, state: FSMContext):
    """Shahar kiritishni qayta ishlash"""
    text = message.text.lower().strip()

    # Validatsiya va normalizatsiya
    if text in ['укр', 'украины']:
        text = 'украина'
    elif text in ['казакстан', 'казахстана']:
        text = 'казахстан'
    elif text in ['росия', 'россии']:
        text = 'россия'
    elif text in ['сбп', 'питер']:
        text = 'санкт-петербург'
    elif text in ['мск', 'масква']:
        text = 'москва'

    if text in ['россия', 'белорусь', 'украина', 'казахстан']:
        await message.answer("❌ Должен быть город, а не страна")
        return

    await update_user_davinci(message.from_user.id, {'davinci_anket_city': text})

    # Keyingi bosqichga o'tish
    await message.answer("Теперь расскажите о себе (минимум 7 символов)")
    await state.set_state(DavinciStates.ANKET_ABOUT_ME)


@client_bot_router.message(DavinciStates.ANKET_ABOUT_ME)
async def handle_anket_about_me(message: types.Message, state: FSMContext):
    """O'zi haqida ma'lumot kiritishni qayta ishlash"""
    text = message.text

    # Validatsiya
    if re.search(r"[@|\/][a-z|A-Z|0-9|_]{3,}", text) or re.search(r"[a-z|A-Z|0-9|_]{2,}bot", text):
        await message.answer("❌ Ссылки запрещены")
        return

    if len(text) < 7:
        await message.answer("❌ Напиши о себе что-нибудь поинтереснее (минимум 7 символов)")
        return

    if len(text) > 300:
        text = f'{text[:300]}...'

    text = text.replace('>', '»').replace('<', '«')
    await update_user_davinci(message.from_user.id, {'davinci_anket_aboutme': text})

    # Gallery bosqichiga o'tish
    await message.answer("Отлично! Теперь пришлите фото или видео (до 15 сек)")
    await state.set_state(DavinciStates.ANKET_GALLERY)


@client_bot_router.message(DavinciStates.ANKET_GALLERY)
async def handle_anket_gallery(message: types.Message, state: FSMContext):
    """Galereya fayllarini qayta ishlash"""
    if not message.photo and not message.video:
        await message.answer("❌ Бот ждет фото или видео от вас")
        return

    # State'dan gallery ma'lumotlarini olish
    data = await state.get_data()
    gallery = data.get('gallery', [])

    # Fayl qo'shish
    if message.photo:
        gallery.append({
            'type': 'photo',
            'media': message.photo[-1].file_id
        })
    elif message.video:
        gallery.append({
            'type': 'video',
            'media': message.video.file_id
        })

    await state.update_data(gallery=gallery)

    if len(gallery) >= 3:
        # Galleyani saqlash
        gallery_json = json.dumps(gallery)
        await update_user_davinci(message.from_user.id, {
            'davinci_anket_gallary': gallery_json,
            'davinci_anket_active': 1
        })

        await message.answer("✅ Анкета создана! Теперь вы можете начать знакомиться.")
        await state.clear()
        await davinci_main_menu(message, state)
    else:
        await message.answer(f"Фото добавлено - {len(gallery)} из 3. Еще одно фото или видео?")


@client_bot_router.message(F.text == "🫰 Знакомства")
async def handle_dating(message: types.Message):
    """Обработка функции знакомств"""
    await message.answer("Добро пожаловать в раздел знакомств! 💕")
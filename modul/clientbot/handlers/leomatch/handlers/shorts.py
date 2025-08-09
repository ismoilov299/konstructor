from aiogram import types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from modul.clientbot.handlers.leomatch.keyboards import reply_kb
from modul.clientbot.handlers.leomatch.data.state import LeomatchRegistration, LeomatchMain
from aiogram.fsm.context import FSMContext
from modul.clientbot.handlers.leomatch.shortcuts import get_leo


async def manage(message: types.Message, state: FSMContext):
    """Asosiy boshqaruv menyusi"""
    data = await state.get_data()
    me = data.get("me")

    # Agar state'da me yo'q bo'lsa, message'dan olish (lekin callback'da bu bot ID bo'lishi mumkin)
    if not me:
        me = message.from_user.id
        print(f"DEBUG: No 'me' in state, using message.from_user.id: {me}")
    else:
        print(f"DEBUG: Using 'me' from state: {me}")

    print(f"DEBUG: manage() called for user {me}")

    leo = await get_leo(me)
    print(f"DEBUG: get_leo({me}) returned: {leo}")

    # Agar get_leo None qaytarsa, to'g'ridan-to'g'ri database'dan tekshirish
    if not leo:
        print(f"DEBUG: get_leo failed, checking database directly")

        # To'g'ridan-to'g'ri database check
        from modul.models import UserTG, LeoMatchModel
        from asgiref.sync import sync_to_async

        @sync_to_async
        def check_leo_direct():
            try:
                # Avval UserTG ni topamiz
                user = UserTG.objects.filter(uid=str(me)).first()
                print(f"DEBUG: Found user: {user}")

                if user:
                    # MUHIM: user_id ishlatish user o'rniga
                    leo = LeoMatchModel.objects.filter(user_id=user.id).first()
                    print(f"DEBUG: Found leo: {leo}")

                    if leo:
                        print(
                            f"DEBUG: Leo details - id: {leo.id}, active: {getattr(leo, 'active', 'N/A')}, search: {getattr(leo, 'search', 'N/A')}")

                    return leo
                else:
                    print(f"DEBUG: User not found in database for uid: {me}")
                    return None
            except Exception as e:
                print(f"DEBUG: Direct database check error: {e}")
                import traceback
                print(f"DEBUG: Traceback: {traceback.format_exc()}")
                return None

        leo = await check_leo_direct()
        print(f"DEBUG: Direct database check result: {leo}")

    # Agar hali ham yo'q bo'lsa
    if not leo:
        print(f"DEBUG: Leo still not found for user {me}, redirecting to registration")
        await message.answer(
            "❌ Профиль не найден. Необходимо пройти регистрацию.",
            reply_markup=reply_kb.begin_registration()
        )
        await state.set_state(LeomatchRegistration.BEGIN)
        return

    print(f"DEBUG: Leo found, continuing with manage logic")

    # Agar foydalanuvchi profili mavjud bo'lmasa
    if not leo:
        await message.answer(
            "❌ Профиль не найден. Необходимо пройти регистрацию.",
            reply_markup=reply_kb.begin_registration()
        )
        await state.set_state(LeomatchRegistration.BEGIN)
        return

    # Tugmalarni yaratamiz
    buttons = []

    # 1. Profil ko'rish tugmasi
    buttons.append([InlineKeyboardButton(text="👀 Просмотр профилей", callback_data="view_profiles")])

    # 2. Mening profilim tugmasi
    buttons.append([InlineKeyboardButton(text="👤 Мой профиль", callback_data="my_profile")])

    # 3. Qidiruv holati bo'yicha tugma
    if not leo.active or not leo.search:
        text = (
            "\nСейчас аккаунт выключен от поиска, если Вы начнете просматривать аккаунты, то Ваш аккаунт вновь включится для поиска другим пользователем")
        # Agar qidiruv o'chirilgan bo'lsa
    else:
        # Agar qidiruv yoqilgan bo'lsa - "Больше не ищу" tugmasini qo'shamiz
        buttons.append([InlineKeyboardButton(text="❌ Больше не ищу", callback_data="stop_search")])
        text = ("\n3. Больше не ищу")

    # Chiqish tugmasi
    buttons.append([InlineKeyboardButton(text="🚪 Выйти", callback_data="exit_leomatch")])

    # Keyboard yaratamiz
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    menu_text = "Выберите действие:"
    if not leo.active or not leo.search:
        menu_text += "\n\n⚠️ Сейчас аккаунт выключен от поиска, если Вы начнете просматривать аккаунты, то Ваш аккаунт вновь включится для поиска другим пользователем"

    await message.answer(menu_text, reply_markup=keyboard)
    await state.set_state(LeomatchMain.WAIT)


async def set_sex(sex: str, message: types.Message, state: FSMContext):
    """Jinsni belgilash funksiyasi"""
    await state.update_data(sex=sex)
    await message.answer(("Кого Вы ищите?"), reply_markup=reply_kb.which_search())
    await state.set_state(LeomatchRegistration.WHICH_SEARCH)


async def set_which_search(which_search: str, message: types.Message, state: FSMContext):
    """Qidiruv parametrini belgilash funksiyasi"""
    await state.update_data(which_search=which_search)

    # Inline keyboard o'rniga oddiy xabar yuboryapmiz chunki shahar nomi yozilishi kerak
    await message.answer(("Из какого ты города?"))
    await state.set_state(LeomatchRegistration.CITY)


async def begin_registration(message: types.Message, state: FSMContext):
    """Registratsiyani boshlash funksiyasi"""
    await state.clear()

    # Cancel tugmasi bilan inline keyboard
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_registration")]
    ])

    await message.answer(("Сколько тебе лет?"), reply_markup=keyboard)
    await state.set_state(LeomatchRegistration.AGE)


# Qo'shimcha funksiyalar main menu uchun
async def show_main_menu_with_status(message: types.Message, state: FSMContext, leo):
    """Status bilan asosiy menyuni ko'rsatish"""
    # Leo mavjudligini tekshirish
    if not leo:
        await message.answer(
            "❌ Профиль не найден. Необходимо пройти регистрацию.",
            reply_markup=reply_kb.begin_registration()
        )
        await state.set_state(LeomatchRegistration.BEGIN)
        return

    buttons = []

    # Profil ko'rish
    buttons.append([InlineKeyboardButton(text="👀 Просмотр профилей", callback_data="view_profiles")])

    # Mening profilim
    buttons.append([InlineKeyboardButton(text="👤 Мой профиль", callback_data="my_profile")])

    # Qidiruv holati
    if leo.active and leo.search:
        buttons.append([InlineKeyboardButton(text="❌ Больше не ищу", callback_data="stop_search")])
        status_text = "🟢 Поиск активен"
    else:
        buttons.append([InlineKeyboardButton(text="✅ Начать поиск", callback_data="start_search")])
        status_text = "🔴 Поиск приостановлен"

    # Настройки
    buttons.append([InlineKeyboardButton(text="⚙️ Настройки", callback_data="settings")])

    # Выйти
    buttons.append([InlineKeyboardButton(text="🚪 Выйти", callback_data="exit_leomatch")])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    text = f"📍 Главное меню\n\n{status_text}"
    if not leo.active or not leo.search:
        text += "\n\n⚠️ При просмотре профилей поиск автоматически активируется"

    await message.answer(text, reply_markup=keyboard)
    await state.set_state(LeomatchMain.WAIT)


async def create_age_input_keyboard():
    """Yosh kiritish uchun keyboard yaratish"""
    buttons = []

    # Mashhur yoshlar
    ages = [18, 19, 20, 21, 22, 23, 25, 30]
    for i in range(0, len(ages), 4):
        row = []
        for j in range(4):
            if i + j < len(ages):
                age = ages[i + j]
                row.append(InlineKeyboardButton(text=str(age), callback_data=f"age_{age}"))
        if row:
            buttons.append(row)

    # Boshqa yosh
    buttons.append([InlineKeyboardButton(text="✏️ Другой возраст", callback_data="custom_age")])

    # Bekor qilish
    buttons.append([InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_registration")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


async def create_city_suggestions_keyboard(user_location=None):
    """Shahar tanlash uchun keyboard yaratish"""
    buttons = []

    # Mashhur shaharlar
    popular_cities = ["Москва", "Санкт-Петербург", "Новосибирск", "Екатеринбург", "Казань", "Нижний Новгород"]

    for i in range(0, len(popular_cities), 2):
        row = []
        for j in range(2):
            if i + j < len(popular_cities):
                city = popular_cities[i + j]
                row.append(InlineKeyboardButton(text=city, callback_data=f"city_{city}"))
        if row:
            buttons.append(row)

    # Agar geolokatsiya bor bo'lsa
    if user_location:
        buttons.insert(0, [InlineKeyboardButton(text=f"📍 {user_location}", callback_data=f"city_{user_location}")])

    # Boshqa shahar
    buttons.append([InlineKeyboardButton(text="✏️ Другой город", callback_data="custom_city")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


# Utility funksiya
async def send_numbered_menu(message: types.Message, options: list, callback_prefix: str, add_exit: bool = True):
    """Raqamlangan menyu yuborish uchun utility funksiya"""
    buttons = []

    for i, option in enumerate(options, 1):
        buttons.append([InlineKeyboardButton(text=f"{i}. {option}", callback_data=f"{callback_prefix}_{i}")])

    if add_exit:
        buttons.append([InlineKeyboardButton(text="🚪 Выйти", callback_data="exit")])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    menu_text = "Выберите вариант:\n\n"
    for i, option in enumerate(options, 1):
        menu_text += f"{i}. {option}\n"

    await message.answer(menu_text, reply_markup=keyboard)
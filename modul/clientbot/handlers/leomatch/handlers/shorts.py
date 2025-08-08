from aiogram import types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from modul.clientbot.handlers.leomatch.keyboards import reply_kb
from modul.clientbot.handlers.leomatch.data.state import LeomatchRegistration, LeomatchMain
from aiogram.fsm.context import FSMContext
from modul.clientbot.handlers.leomatch.shortcuts import get_leo


async def manage(message: types.Message, state: FSMContext):
    data = await state.get_data()
    me = data.get("me") if data.get("me") else message.from_user.id
    leo = await get_leo(me)

    if not leo:
        await message.answer(
            "❌ Профиль не найден. Необходимо пройти регистрацию.",
            reply_markup=reply_kb.begin_registration()
        )
        await state.set_state(LeomatchRegistration.BEGIN)
        return

    if not leo:
        await message.answer(
            "❌ Профиль не найден. Необходимо пройти регистрацию.",
            reply_markup=reply_kb.begin_registration()
        )
        await state.set_state(LeomatchRegistration.BEGIN)
        return

    buttons = []

    buttons.append([InlineKeyboardButton(text="👀 Просмотр профилей", callback_data="view_profiles")])

    buttons.append([InlineKeyboardButton(text="👤 Мой профиль", callback_data="my_profile")])

    if not leo.active or not leo.search:
        text = (
            "\nСейчас аккаунт выключен от поиска, если Вы начнете просматривать аккаунты, то Ваш аккаунт вновь включится для поиска другим пользователем")
    else:
        buttons.append([InlineKeyboardButton(text="❌ Больше не ищу", callback_data="stop_search")])
        text = ("\n3. Больше не ищу")

    buttons.append([InlineKeyboardButton(text="🚪 Выйти", callback_data="exit_leomatch")])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    menu_text = "Выберите действие:"
    if not leo.active or not leo.search:
        menu_text += "\n\n⚠️ Сейчас аккаунт выключен от поиска, если Вы начнете просматривать аккаунты, то Ваш аккаунт вновь включится для поиска другим пользователем"

    await message.answer(menu_text, reply_markup=keyboard)
    await state.set_state(LeomatchMain.WAIT)


async def set_sex(sex: str, message: types.Message, state: FSMContext):
    await state.update_data(sex=sex)
    await message.answer(("Кого Вы ищите?"), reply_markup=reply_kb.which_search())
    await state.set_state(LeomatchRegistration.WHICH_SEARCH)


async def set_which_search(which_search: str, message: types.Message, state: FSMContext):
    await state.update_data(which_search=which_search)

    await message.answer(("Из какого ты города?"))
    await state.set_state(LeomatchRegistration.CITY)


async def begin_registration(message: types.Message, state: FSMContext):
    await state.clear()

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_registration")]
    ])

    await message.answer(("Сколько тебе лет?"), reply_markup=keyboard)
    await state.set_state(LeomatchRegistration.AGE)


async def show_main_menu_with_status(message: types.Message, state: FSMContext, leo):
    if not leo:
        await message.answer(
            "❌ Профиль не найден. Необходимо пройти регистрацию.",
            reply_markup=reply_kb.begin_registration()
        )
        await state.set_state(LeomatchRegistration.BEGIN)
        return

    buttons = []

    buttons.append([InlineKeyboardButton(text="👀 Просмотр профилей", callback_data="view_profiles")])

    buttons.append([InlineKeyboardButton(text="👤 Мой профиль", callback_data="my_profile")])

    if leo.active and leo.search:
        buttons.append([InlineKeyboardButton(text="❌ Больше не ищу", callback_data="stop_search")])
        status_text = "🟢 Поиск активен"
    else:
        buttons.append([InlineKeyboardButton(text="✅ Начать поиск", callback_data="start_search")])
        status_text = "🔴 Поиск приостановлен"

    buttons.append([InlineKeyboardButton(text="⚙️ Настройки", callback_data="settings")])

    buttons.append([InlineKeyboardButton(text="🚪 Выйти", callback_data="exit_leomatch")])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    text = f"📍 Главное меню\n\n{status_text}"
    if not leo.active or not leo.search:
        text += "\n\n⚠️ При просмотре профилей поиск автоматически активируется"

    await message.answer(text, reply_markup=keyboard)
    await state.set_state(LeomatchMain.WAIT)


async def create_age_input_keyboard():
    buttons = []

    ages = [18, 19, 20, 21, 22, 23, 25, 30]
    for i in range(0, len(ages), 4):
        row = []
        for j in range(4):
            if i + j < len(ages):
                age = ages[i + j]
                row.append(InlineKeyboardButton(text=str(age), callback_data=f"age_{age}"))
        if row:
            buttons.append(row)

    buttons.append([InlineKeyboardButton(text="✏️ Другой возраст", callback_data="custom_age")])

    buttons.append([InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_registration")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


async def create_city_suggestions_keyboard(user_location=None):
    buttons = []

    popular_cities = ["Москва", "Санкт-Петербург", "Новосибирск", "Екатеринбург", "Казань", "Нижний Новгород"]

    for i in range(0, len(popular_cities), 2):
        row = []
        for j in range(2):
            if i + j < len(popular_cities):
                city = popular_cities[i + j]
                row.append(InlineKeyboardButton(text=city, callback_data=f"city_{city}"))
        if row:
            buttons.append(row)

    if user_location:
        buttons.insert(0, [InlineKeyboardButton(text=f"📍 {user_location}", callback_data=f"city_{user_location}")])

    buttons.append([InlineKeyboardButton(text="✏️ Другой город", callback_data="custom_city")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


async def send_numbered_menu(message: types.Message, options: list, callback_prefix: str, add_exit: bool = True):
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
import logging

from aiogram import types
from modul.clientbot.handlers.leomatch.keyboards import reply_kb
from modul.clientbot.handlers.leomatch.data.state import LeomatchRegistration, LeomatchMain
from aiogram.fsm.context import FSMContext
from modul.clientbot.handlers.leomatch.shortcuts import get_leo

logger = logging.getLogger(__name__)


async def manage(message: types.Message
                 , state: FSMContext):
    try:
        logger.info(f"Starting manage function for user {message.from_user.id}")
        data = await state.get_data()
        me = data.get("me", message.from_user.id)

        leo = await get_leo(me)
        if not leo:
            logger.error(f"User {me} not found in database")
            await message.answer("Ошибка при получении данных пользователя")
            return

        logger.info(f"User {me} status - active: {leo.active}, search: {leo.search}")

        # Xabar va tugmalarni tayyorlaymiz
        menu_items = ["1. Просмотр профилей", "2. Мой профиль"]
        if not leo.active or not leo.search:
            menu_items.append("\nСейчас аккаунт выключен от поиска...")
            button_count = 2
        else:
            menu_items.append("3. Больше не ищу")
            button_count = 3

        menu_text = "\n".join(menu_items)

        # Klaviaturani yaratamiz
        keyboard = reply_kb.get_numbers(button_count, add_exit=True, one_time_keyboard=True)

        # Xabarni yuboramiz
        await message.answer(menu_text, reply_markup=keyboard)

        # Yangi state o'rnatamiz
        await state.set_state(LeomatchMain.WAIT)

        logger.info(f"Manage menu sent to user {me}")
    except Exception as e:
        logger.error(f"Error in manage function for user {message.from_user.id}: {e}", exc_info=True)
        await message.answer("Произошла ошибка при обработке запроса")

async def set_sex(sex: str, message: types.Message, state: FSMContext):
    """Jins ma'lumotlarini saqlash"""
    try:
        # State ni tekshirish
        current_state = await state.get_state()
        if current_state != LeomatchRegistration.SEX:
            logger.warning(f"Wrong state for setting sex. Expected SEX, got {current_state}")
            return

        # Xozirgi state data ni ko'rish
        data = await state.get_data()
        logger.info(f"Current state data before setting sex: {data}")

        # Sex ni saqlash
        if sex in ["MALE", "FEMALE"]:
            await state.update_data(sex=sex)
            data = await state.get_data()
            logger.info(f"Updated state data after setting sex: {data}")

            await message.answer(
                "Кого Вы ищите?",
                reply_markup=reply_kb.which_search()
            )
            await state.set_state(LeomatchRegistration.WHICH_SEARCH)
            logger.info(f"State changed to WHICH_SEARCH for user {message.from_user.id}")
        else:
            logger.warning(f"Invalid sex value: {sex}")
            await message.answer("Пожалуйста, выберите пол используя кнопки")

    except Exception as e:
        logger.error(f"Error in set_sex function: {e}", exc_info=True)
        await message.answer("Произошла ошибка при выборе пола. Попробуйте еще раз.")

async def set_which_search(which_search: str, message: types.Message, state: FSMContext):
    await state.update_data(which_search=which_search)
    await message.answer(("Из какого ты города?"), reply_markup=reply_kb.remove())
    await state.set_state(LeomatchRegistration.CITY)


async def begin_registration(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(("Сколько тебе лет?"), reply_markup=reply_kb.cancel())
    await state.set_state(LeomatchRegistration.AGE)

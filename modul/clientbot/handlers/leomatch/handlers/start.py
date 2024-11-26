import logging

from aiogram import types, F, Bot
from asgiref.sync import sync_to_async

from modul.clientbot.handlers.leomatch.keyboards import reply_kb
from modul.clientbot.utils.functs import return_main
from modul.clientbot.handlers.leomatch.shortcuts import exists_leo, get_leo
from modul.clientbot.handlers.leomatch.handlers.shorts import manage
from modul.models import LeoMatchModel
from modul.loader import client_bot_router
from aiogram.fsm.context import FSMContext
from modul.clientbot.handlers.leomatch.data.state import LeomatchRegistration
from aiogram.utils.i18n import gettext as _
from aiogram.utils.i18n import lazy_gettext as __
logger = logging.getLogger(__name__)

from modul.models import UserTG


@client_bot_router.message(F.text == "🫰 Знакомства")
async def bot_start(message: types.Message, state: FSMContext):
    try:
        logger.info(f"Starting dating bot for user {message.from_user.id}")
        await state.clear()  # Clear any existing state

        has_user = await exists_leo(message.from_user.id)
        if not has_user:
            await message.answer(
                "Добро пожаловать! Я - бот для знакомств. Я помогу тебе найти свою вторую половинку.",
                reply_markup=reply_kb.begin_registration()
            )
            await state.set_state(LeomatchRegistration.BEGIN)
            logger.info(f"Set BEGIN state for new user {message.from_user.id}")
        else:
            account = await get_leo(message.from_user.id)
            if account and account.blocked:
                await message.answer("Ваш аккаунт заблокирован")
                return
            await manage(message, state)

    except Exception as e:
        logger.error(f"Error in bot_start: {e}", exc_info=True)
        await message.answer("Произошла ошибка при запуске")


@client_bot_router.message(F.text == "Я не хочу никого искать", LeomatchRegistration.BEGIN)
async def bot_start_cancel(message: types.Message, state: FSMContext, bot: Bot):
    try:
        current_state = await state.get_state()
        if current_state != LeomatchRegistration.BEGIN:
            return

        await state.clear()
        await return_main(message, state, bot)

    except Exception as e:
        logger.error(f"Error in bot_start_cancel: {e}", exc_info=True)
        await message.answer("Произошла ошибка при отмене")

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

from modul.models import UserTG


@client_bot_router.callback_query(F.data == "start_registration", LeomatchRegistration.BEGIN)
async def handle_start_registration_callback(callback: types.CallbackQuery, state: FSMContext):

    await callback.answer()

@client_bot_router.callback_query(F.data == "dont_want_search", LeomatchRegistration.BEGIN)
async def handle_dont_want_search_callback(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    await return_main(callback.message, state, bot)
    await callback.answer("Вы отказались от поиска")

@client_bot_router.callback_query(F.data == "refuse_registration")
async def handle_refuse_registration_callback(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    await return_main(callback.message, state, bot)
    await callback.answer("Регистрация отменена")



@client_bot_router.message(F.text == "🫰 Знакомства")
async def bot_start(message: types.Message, state: FSMContext):
    has_user = await exists_leo(message.from_user.id)
    if not has_user:
        await message.answer(
            ("Добро пожаловать! Я - бот для знакомств. Я помогу тебе найти свою вторую половинку. "),
            reply_markup=reply_kb.begin_registration())
        await state.set_state(LeomatchRegistration.BEGIN)
    else:
        account = await get_leo(message.from_user.id)
        if account.blocked:
            await message.answer(("Ваш аккаунт заблокирован"))
            return
        await manage(message, state)

@client_bot_router.message(F.text == ("Я не хочу никого искать"), LeomatchRegistration.BEGIN)
async def bot_start_cancel(message: types.Message, state: FSMContext, bot: Bot):
    await return_main(message, state, bot)

@client_bot_router.message(F.text == ("Давай, начнем!"), LeomatchRegistration.BEGIN)
async def handle_start_registration_text(message: types.Message, state: FSMContext):
    pass

@client_bot_router.message(LeomatchRegistration.BEGIN)
async def handle_begin_state_fallback(message: types.Message, state: FSMContext):

    await message.answer(
        "Пожалуйста, выберите один из вариантов ниже:",
        reply_markup=reply_kb.begin_registration()
    )

@client_bot_router.message(F.text.contains("Знакомства"))
async def handle_dating_variations(message: types.Message, state: FSMContext):

    await bot_start(message, state)
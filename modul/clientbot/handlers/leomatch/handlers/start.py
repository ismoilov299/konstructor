from aiogram import types, F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext

from modul.clientbot.handlers.leomatch.keyboards import reply_kb
from modul.clientbot.utils.functs import return_main
from modul.clientbot.handlers.leomatch.shortcuts import exists_leo, get_leo
from modul.clientbot.handlers.leomatch.handlers.shorts import manage
# from db.models import LeoMatchModel
# from loader import client_bot_router
# from aiogram.dispatcher.fsm.context import FSMContext
from modul.clientbot.handlers.leomatch.data.state import LeomatchRegistration
from aiogram.utils.keyboard import InlineKeyboardBuilder


from modul.loader import client_bot_router
from modul.models import LeoMatchModel


@client_bot_router.message(F.text == ("🫰 Знакомства"))
async def bot_start(message: types.Message, state: FSMContext):
    has_user = await exists_leo(message.from_user.id)
    if not has_user:
        await message.answer(("Добро пожаловать! Я - бот для знакомств. Я помогу тебе найти свою вторую половинку. "),
                             reply_markup=reply_kb.begin_registration())
        await state.set_state(LeomatchRegistration.BEGIN)
    else:
        account: LeoMatchModel = await get_leo(message.from_user.id)
        if account.blocked:
            await message.answer(("Ваш аккаунт заблокирован"))
            return
        await manage(message, state)
        kbrds = InlineKeyboardBuilder()
        kbrds.add(
            types.InlineKeyboardButton(text=("Запустите WebApp"),
                                       web_app=types.WebAppInfo(url='https://simplerulet.online/waleo/'))
        )
        await message.answer(("Попробуйте наш WebAPP знакомства"), reply_markup=kbrds.as_markup())


@client_bot_router.message(F.text == ("Я не хочу никого искать"), StateFilter(LeomatchRegistration.BEGIN))
async def bot_start(message: types.Message, state: FSMContext):
    await return_main(message, state)

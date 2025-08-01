import os
from aiogram import types, F, Bot
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext

from modul.clientbot.handlers.leomatch.keyboards import reply_kb
from modul.clientbot.handlers.leomatch.data.state import LeomatchMain
from modul.clientbot.handlers.leomatch.shortcuts import get_leo, show_profile_db, update_profile
from modul.clientbot.handlers.leomatch.handlers.shorts import begin_registration
from modul.clientbot.handlers.leomatch.handlers import profiles
from modul.clientbot.utils.functs import return_main
from modul.clientbot.shortcuts import get_current_bot
# from loader import client_bot_router, bot_session
# from aiogram.dispatcher.fsm.context import FSMContext


from modul.loader import client_bot_router, bot_session


async def start(message: types.Message, state: FSMContext):
    await show_profile_db(message, message.from_user.id, reply_kb.get_numbers(4, True))
    await message.answer(
         ("1. Отредактировать мой профиль.\n2. Изменить фото/видео.\n3. Изменить текст профиля.\n4. Просмотреть профили"),
        reply_markup=reply_kb.get_numbers(4, True))
    await state.set_state(LeomatchMain.PROFILE_MANAGE)


@client_bot_router.message(F.text =="1", StateFilter(LeomatchMain.WAIT))
async def bot_start(message: types.Message, state: FSMContext):
    leo = await get_leo(message.from_user.id)
    if not leo.active or not leo.search:
        await update_profile(message.from_user.id, {"active": True, "search": True})
    await profiles.start(message, state)


@client_bot_router.message(F.text =="2", StateFilter(LeomatchMain.WAIT))
async def bot_start(message: types.Message, state: FSMContext):
    await start(message, state)


@client_bot_router.message(F.text ==  ("Выйти"), StateFilter(LeomatchMain.WAIT))
@client_bot_router.message(F.text ==  ("Выйти"), StateFilter(LeomatchMain.PROFILE_MANAGE))
async def bot_start(message: types.Message, state: FSMContext, bot: Bot):
    await return_main(message, state,bot)


@client_bot_router.message(F.text =="3", StateFilter(LeomatchMain.WAIT))
async def bot_start(message: types.Message, state: FSMContext):
    await message.answer(
         ("Тогда ты не будешь знать, кому ты нравишься... Уверены насчет деактивации?\n\n1. Да, деактивируйте мой профиль, пожалуйста.\n2. Нет, я хочу посмотреть свои матчи."),
        reply_markup=reply_kb.get_numbers(2)
    )
    await state.set_state(LeomatchMain.SLEEP)


@client_bot_router.message(F.text =="1", StateFilter(LeomatchMain.SLEEP))
async def bot_start(message: types.Message, state: FSMContext):
    await message.answer(
         ("Надеюсь, вы встретили кого-нибудь с моей помощью! \nВсегда рад пообщаться. Если скучно, напиши мне - я найду для тебя кого-то особенного.\n\n1. Просмотр профилей"),
        reply_markup=reply_kb.get_numbers(1)
    )
    await update_profile(message.from_user.id, {"active": False, "search": False})
    await state.set_state(LeomatchMain.WAIT)


@client_bot_router.message(F.text =="2", StateFilter(LeomatchMain.SLEEP))
async def bot_start(message: types.Message, state: FSMContext):
    await start(message, state)


@client_bot_router.message(F.text =="1", StateFilter(LeomatchMain.PROFILE_MANAGE))
async def bot_start(message: types.Message, state: FSMContext):
    await begin_registration(message, state)


@client_bot_router.message(F.text =="2", StateFilter(LeomatchMain.PROFILE_MANAGE))
async def bot_start(message: types.Message, state: FSMContext):
    await message.answer( ("Отправьте фото или видео (до 15 сек)"), reply_markup=reply_kb.cancel())
    await state.set_state(LeomatchMain.SET_PHOTO)


@client_bot_router.message(F.text =="3", StateFilter(LeomatchMain.PROFILE_MANAGE))
async def bot_start(message: types.Message, state: FSMContext):
    await message.answer( ("Введите новый текст профиля"), reply_markup=reply_kb.cancel())
    await state.set_state(LeomatchMain.SET_DESCRIPTION)


@client_bot_router.message(F.text == "4", StateFilter(LeomatchMain.PROFILE_MANAGE))
async def bot_start(message: types.Message, state: FSMContext):
    await profiles.start(message, state)


@client_bot_router.message(F.text ==  ("Отменить"), StateFilter(LeomatchMain.SET_DESCRIPTION))
async def bot_start(message: types.Message, state: FSMContext):
    await start(message, state)


@client_bot_router.message(StateFilter(LeomatchMain.SET_DESCRIPTION))
async def bot_start(message: types.Message, state: FSMContext):
    await update_profile(message.from_user.id, {"about_me": message.text})
    await start(message, state)


@client_bot_router.message(F.text ==  ("Отменить"), StateFilter(LeomatchMain.SET_PHOTO))
async def bot_start(message: types.Message, state: FSMContext):
    await start(message, state)


@client_bot_router.message(StateFilter(LeomatchMain.SET_PHOTO))
async def bot_start(message: types.Message, state: FSMContext,bot: Bot):
    photo = ""
    media_type = ""
    if message.photo:
        photo = message.photo[-1].file_id
        media_type = "PHOTO"
    elif message.video:
        if message.video.duration > 15:
            await message.answer( ("Пожалуйста, пришли видео не более 15 секунд"))
            return
        photo = message.video.file_id
        media_type = "VIDEO"
    elif message.video_note:
        if message.video_note.duration > 15:
            await message.answer( ("Пожалуйста, пришли видео не более 15 секунд"))
            return
        photo = message.video_note.file_id
        media_type = "VIDEO_NOTE"
    await update_profile(message.from_user.id, {"photo": photo, "media_type": media_type})
    bot = await get_current_bot(bot)
    async with Bot(token=bot.token, session=bot_session).context(auto_close=False) as bot_:
        media_format = "jpg" if media_type == "PHOTO" else "mp4"
        os.makedirs("clientbot/data/leo", exist_ok=True)
        await bot_.download(photo, f"clientbot/data/leo/{message.from_user.id}.{media_format}")
    await start(message, state)

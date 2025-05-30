import os
import traceback

from aiogram import types, F
from modul.clientbot.handlers.leomatch.keyboards import reply_kb
from modul.clientbot.handlers.leomatch.data.state import LeomatchMain
from modul.clientbot.handlers.leomatch.shortcuts import get_leo, show_profile_db, update_profile
from modul.clientbot.handlers.leomatch.handlers.shorts import begin_registration
from modul.clientbot.handlers.leomatch.handlers import profiles
from modul.clientbot.utils.functs import return_main
from modul.loader import client_bot_router
from aiogram.fsm.context import FSMContext
from aiogram import Bot

async def start(message: types.Message, state: FSMContext):
    await show_profile_db(message, message.from_user.id, reply_kb.get_numbers(4, True))
    await message.answer(
        "1. Отредактировать мой профиль.\n2. Изменить фото/видео.\n3. Изменить текст профиля.\n4. Просмотреть профили",
        reply_markup=reply_kb.get_numbers(4, True))
    await state.set_state(LeomatchMain.PROFILE_MANAGE)


@client_bot_router.message(F.text == "1", LeomatchMain.WAIT)
async def bot_start(message: types.Message, state: FSMContext):
    leo = await get_leo(message.from_user.id)
    if not leo.active or not leo.search:
        await update_profile(message.from_user.id, {"active": True, "search": True})
    await profiles.start(message, state)


@client_bot_router.message(F.text == "2", LeomatchMain.WAIT)
async def bot_start(message: types.Message, state: FSMContext):
    await start(message, state)


@client_bot_router.message(F.text == ("Выйти"), LeomatchMain.WAIT)
@client_bot_router.message(F.text == ("Выйти"), LeomatchMain.PROFILE_MANAGE)
async def bot_start(message: types.Message, state: FSMContext):
    bot = message.bot
    await return_main(message, state,bot)


@client_bot_router.message(F.text == "3", LeomatchMain.WAIT)
async def bot_start(message: types.Message, state: FSMContext):
    await message.answer(
        (
            "Тогда ты не будешь знать, кому ты нравишься... Уверены насчет деактивации?\n\n1. Да, деактивируйте мой профиль, пожалуйста.\n2. Нет, я хочу посмотреть свои матчи."),
        reply_markup=reply_kb.get_numbers(2)
    )
    await state.set_state(LeomatchMain.SLEEP)


@client_bot_router.message(F.text == "1", LeomatchMain.SLEEP)
async def bot_start(message: types.Message, state: FSMContext):
    await message.answer(
        (
            "Надеюсь, вы встретили кого-нибудь с моей помощью! \nВсегда рад пообщаться. Если скучно, напиши мне - я найду для тебя кого-то особенного.\n\n1. Просмотр профилей"),
        reply_markup=reply_kb.get_numbers(1)
    )
    await update_profile(message.from_user.id, {"active": False, "search": False})
    await state.set_state(LeomatchMain.WAIT)


@client_bot_router.message(F.text == "2", LeomatchMain.SLEEP)
async def bot_start(message: types.Message, state: FSMContext):
    await start(message, state)


@client_bot_router.message(F.text == "1", LeomatchMain.PROFILE_MANAGE)
async def bot_start(message: types.Message, state: FSMContext):
    await begin_registration(message, state)


@client_bot_router.message(F.text == "2", LeomatchMain.PROFILE_MANAGE)
async def bot_start(message: types.Message, state: FSMContext):
    await message.answer(("Отправьте фото или видео (до 15 сек)"), reply_markup=reply_kb.cancel())
    await state.set_state(LeomatchMain.SET_PHOTO)


@client_bot_router.message(F.text == "3", LeomatchMain.PROFILE_MANAGE)
async def bot_start(message: types.Message, state: FSMContext):
    await message.answer(("Введите новый текст профиля"), reply_markup=reply_kb.cancel())
    await state.set_state(LeomatchMain.SET_DESCRIPTION)


@client_bot_router.message(F.text == "4", LeomatchMain.PROFILE_MANAGE)
async def bot_start(message: types.Message, state: FSMContext):
    await profiles.start(message, state)


@client_bot_router.message(F.text == ("Отменить"), LeomatchMain.SET_DESCRIPTION)
async def bot_start(message: types.Message, state: FSMContext):
    await start(message, state)


@client_bot_router.message(LeomatchMain.SET_DESCRIPTION)
async def bot_start(message: types.Message, state: FSMContext):
    await update_profile(message.from_user.id, {"about_me": message.text})
    await start(message, state)


@client_bot_router.message(F.text == ("Отменить"), LeomatchMain.SET_PHOTO)
async def bot_start(message: types.Message, state: FSMContext):
    await start(message, state)


@client_bot_router.message(LeomatchMain.SET_PHOTO)
async def bot_start(message: types.Message, state: FSMContext, bot: Bot):
    try:
        photo = None
        media_type = None
        file_extension = None

        if message.photo:
            photo = message.photo[-1]
            media_type = "PHOTO"
            file_extension = ".jpg"
        elif message.video:
            if message.video.duration > 15:
                await message.answer("Пожалуйста, пришли видео не более 15 секунд")
                return
            photo = message.video
            media_type = "VIDEO"
            file_extension = ".mp4"
        elif message.video_note:
            if message.video_note.duration > 15:
                await message.answer("Пожалуйста, пришли видео не более 15 секунд")
                return
            photo = message.video_note
            media_type = "VIDEO_NOTE"
            file_extension = ".mp4"
        else:
            await message.answer("Пожалуйста, отправьте фото или видео")
            return

        if photo:
            # Получаем информацию о файле
            file = await bot.get_file(photo.file_id)

            # Используем абсолютные пути
            abs_base_dir = "/var/www/konstructor/modul/clientbot/data"
            abs_file_path = os.path.join(abs_base_dir, f"leo{message.from_user.id}{file_extension}")

            # Создаем директорию если нужно
            if not os.path.exists(abs_base_dir):
                os.makedirs(abs_base_dir, exist_ok=True)
                print(f"Created directory: {abs_base_dir}")

            # Загружаем файл
            print(f"Downloading file to: {abs_file_path}")
            try:
                # Загружаем файл с Telegram
                await bot.download_file(file.file_path, abs_file_path)

                # Проверяем, был ли файл сохранен
                if os.path.exists(abs_file_path):
                    print(f"File was successfully saved: {abs_file_path}")
                    file_size = os.path.getsize(abs_file_path)
                    print(f"File size: {file_size} bytes")

                    # Сохраняем относительный путь в БД (для совместимости)
                    rel_path = f"modul/clientbot/data/leo{message.from_user.id}{file_extension}"

                    success = await update_profile(message.from_user.id, {
                        "photo": rel_path,  # Сохраняем относительный путь
                        "media_type": media_type
                    })

                    if success:
                        await message.answer("✅ Фото/видео успешно обновлено")

                        # Проверяем, действительно ли файл существует
                        print(f"After update, checking if file exists: {os.path.exists(abs_file_path)}")

                        await start(message, state)
                    else:
                        await message.answer("❌ Произошла ошибка при обновлении базы данных")
                else:
                    print(f"WARNING: File was not saved: {abs_file_path}")
                    await message.answer("❌ Произошла ошибка при сохранении файла")
            except Exception as download_error:
                print(f"Error downloading file: {download_error}")
                print(f"Error traceback: {traceback.format_exc()}")
                await message.answer("❌ Ошибка при загрузке файла")
        else:
            await message.answer("❌ Не удалось получить файл")

    except Exception as e:
        print(f"Error in SET_PHOTO handler: {e}")
        print(f"Error traceback: {traceback.format_exc()}")
        await message.answer("❌ Произошла ошибка при обновлении фото/видео")
from datetime import datetime

from aiogram import types, F
from aiogram.fsm.context import FSMContext
import logging

from modul.clientbot.handlers.leomatch.keyboards import reply_kb
from modul.clientbot.handlers.leomatch.data.state import LeomatchMain, LeomatchRegistration, LeomatchProfiles
from modul.clientbot.handlers.leomatch.shortcuts import get_leo, show_profile_db, update_profile
from modul.clientbot.handlers.leomatch.handlers.shorts import begin_registration
from modul.clientbot.handlers.leomatch.handlers import profiles
from modul.clientbot.utils.functs import return_main
from modul.loader import client_bot_router
from modul.models import Bot

logger = logging.getLogger(__name__)


async def start(message: types.Message, state: FSMContext):
    try:
        await show_profile_db(message, message.from_user.id, reply_kb.get_numbers(4, add_exit=True))
        await message.answer(
            "1. Отредактировать мой профиль.\n"
            "2. Изменить фото/видео.\n"
            "3. Изменить текст профиля.\n"
            "4. Просмотреть профили",
            reply_markup=reply_kb.get_numbers(4, add_exit=True)
        )
        await state.set_state(LeomatchMain.PROFILE_MANAGE)
        logger.info(f"Profile menu sent to user {message.from_user.id}")

    except Exception as e:
        logger.error(f"Error in start: {e}", exc_info=True)
        await message.answer("Произошла ошибка")


@client_bot_router.message(F.text.in_({"1", "2", "3", "4"}), LeomatchMain.PROFILE_MANAGE)
async def handle_profile_actions(message: types.Message, state: FSMContext):
    try:
        user_id = message.from_user.id
        button = message.text

        # Button bosishlarni kuzatish
        if user_id not in button_clicks:
            button_clicks[user_id] = {}
        if button not in button_clicks[user_id]:
            button_clicks[user_id][button] = 0
        button_clicks[user_id][button] += 1

        logger.info(f"Button {button} clicked {button_clicks[user_id][button]} times by user {user_id}")
        print(f"User {user_id} button clicks: {button_clicks[user_id]}")

        current_state = await state.get_state()
        if current_state != LeomatchMain.PROFILE_MANAGE:
            logger.info(f"Ignoring due to wrong state: {current_state}")
            return

        if message.text == "1":
            await state.set_state(LeomatchRegistration.BEGIN)
            await begin_registration(message, state)

        elif message.text == "2":
            await state.set_state(LeomatchMain.SET_PHOTO)
            await message.answer(
                "Отправьте фото или видео (до 15 сек)",
                reply_markup=reply_kb.cancel()
            )

        elif message.text == "3":
            await state.set_state(LeomatchMain.SET_DESCRIPTION)
            await message.answer(
                "Введите новый текст профиля",
                reply_markup=reply_kb.cancel()
            )

        elif message.text == "4":
            await state.set_state(LeomatchProfiles.LOOCK)
            await profiles.start(message, state)

    except Exception as e:
        logger.error(f"Error handling profile action: {e}", exc_info=True)
        await message.answer("Произошла ошибка")


@client_bot_router.message(F.text == "1", LeomatchMain.WAIT)
async def view_profiles(message: types.Message, state: FSMContext):
    """Просмотр профилей"""
    try:
        if await state.get_state() != LeomatchMain.WAIT:
            return

        leo = await get_leo(message.from_user.id)
        if not leo.active or not leo.search:
            await update_profile(message.from_user.id, {"active": True, "search": True})
            logger.info(f"Activated profile for user {message.from_user.id}")

        await profiles.start(message, state)

    except Exception as e:
        logger.error(f"Error viewing profiles: {e}", exc_info=True)
        await message.answer("Произошла ошибка при просмотре профилей")


button_clicks = {}


@client_bot_router.message(F.text == "2", LeomatchMain.WAIT)
async def manage_profile(message: types.Message, state: FSMContext):
    """Profilni boshqarish"""
    try:
        user_id = message.from_user.id

        # Button bosishlarni kuzatish
        if user_id not in button_clicks:
            button_clicks[user_id] = {"2": 0}
        button_clicks[user_id]["2"] += 1

        logger.info(f"Button 2 clicked {button_clicks[user_id]['2']} times by user {user_id}")

        current_state = await state.get_state()
        if current_state != LeomatchMain.WAIT:
            logger.info(f"Ignoring message due to wrong state: {current_state}")
            return

        await state.set_state(LeomatchMain.PROFILE_MANAGE)
        await start(message, state)

    except Exception as e:
        logger.error(f"Error managing profile: {e}", exc_info=True)
        await message.answer("Произошла ошибка")


@client_bot_router.message(F.text == "Выйти", LeomatchMain.WAIT)
@client_bot_router.message(F.text == "Выйти", LeomatchMain.PROFILE_MANAGE)
async def exit_profile(message: types.Message, state: FSMContext, bot: Bot):
    """Profildan chiqish"""
    try:
        user_id = message.from_user.id

        # Chiqish tugmasi bosishlarini kuzatish
        if user_id not in button_clicks:
            button_clicks[user_id] = {"exit": 0}
        button_clicks[user_id]["exit"] += 1

        logger.info(f"Exit button clicked {button_clicks[user_id]['exit']} times by user {user_id}")
        print(f"User {user_id} exit clicks: {button_clicks[user_id]['exit']}")

        current_state = await state.get_state()
        if current_state not in [LeomatchMain.WAIT, LeomatchMain.PROFILE_MANAGE]:
            return

        await return_main(message, state, bot)  # bot qo'shildi

    except Exception as e:
        logger.error(f"Error exiting profile: {e}", exc_info=True)
        await message.answer("Произошла ошибка")


def print_button_stats():
    print("\nButton click statistics:")
    for user_id, clicks in button_clicks.items():
        print(f"\nUser {user_id}:")
        for button, count in clicks.items():
            print(f"Button {button}: clicked {count} times")


# Har bir handler ichida button_clicks ni tekshirish
async def check_button_clicks(user_id: int, button: str) -> bool:
    """Tugma birinchi marta bosilganini tekshirish"""
    if user_id not in button_clicks:
        button_clicks[user_id] = {}
    if button not in button_clicks[user_id]:
        button_clicks[user_id][button] = 0
    button_clicks[user_id][button] += 1

    logger.info(f"Button {button} clicked {button_clicks[user_id][button]} times by user {user_id}")
    print(f"User {user_id} button {button} clicked {button_clicks[user_id][button]} times")

    return button_clicks[user_id][button] == 1


@client_bot_router.message(F.text == "3", LeomatchMain.WAIT)
async def deactivate_profile(message: types.Message, state: FSMContext):
    """Удалить профиль"""
    try:
        if await state.get_state() != LeomatchMain.WAIT:
            return

        await message.answer(
            "Тогда ты не будешь знать, кому ты нравишься... Уверены насчет деактивации?\n\n"
            "1. Да, деактивируйте мой профиль, пожалуйста.\n"
            "2. Нет, я хочу посмотреть свои матчи.",
            reply_markup=reply_kb.get_numbers(2)
        )
        await state.set_state(LeomatchMain.SLEEP)

    except Exception as e:
        logger.error(f"Error deactivating profile: {e}", exc_info=True)
        await message.answer("Произошла ошибка")


@client_bot_router.message(F.text == "1", LeomatchMain.SLEEP)
async def confirm_deactivation(message: types.Message, state: FSMContext):
    """Подтвердить удаление профиля"""
    try:
        if await state.get_state() != LeomatchMain.SLEEP:
            return

        await message.answer(
            "Надеюсь, вы встретили кого-нибудь с моей помощью!\n"
            "Всегда рад пообщаться. Если скучно, напиши мне - я найду для тебя кого-то особенного.\n\n"
            "1. Просмотр профилей",
            reply_markup=reply_kb.get_numbers(1)
        )
        await update_profile(message.from_user.id, {"active": False, "search": False})
        await state.set_state(LeomatchMain.WAIT)
        logger.info(f"Profile deactivated for user {message.from_user.id}")

    except Exception as e:
        logger.error(f"Error confirming deactivation: {e}", exc_info=True)
        await message.answer("Произошла ошибка")


@client_bot_router.message(F.text == "2", LeomatchMain.SLEEP)
async def cancel_deactivation(message: types.Message, state: FSMContext):
    """Удалить профиль Отмена"""
    try:
        if await state.get_state() != LeomatchMain.SLEEP:
            return

        await start(message, state)

    except Exception as e:
        logger.error(f"Error canceling deactivation: {e}", exc_info=True)
        await message.answer("Произошла ошибка")


@client_bot_router.message(F.text == "1", LeomatchMain.PROFILE_MANAGE)
async def edit_profile(message: types.Message, state: FSMContext):
    """Редактировать профиль"""
    try:
        if await state.get_state() != LeomatchMain.PROFILE_MANAGE:
            return

        await begin_registration(message, state)

    except Exception as e:
        logger.error(f"Error editing profile: {e}", exc_info=True)
        await message.answer("Произошла ошибка при редактировании профиля")


@client_bot_router.message(F.text == "2", LeomatchMain.PROFILE_MANAGE)
async def change_photo(message: types.Message, state: FSMContext):
    """Преобразование изображения/видео"""
    try:
        if await state.get_state() != LeomatchMain.PROFILE_MANAGE:
            return

        await message.answer("Отправьте фото или видео (до 15 сек)", reply_markup=reply_kb.cancel())
        await state.set_state(LeomatchMain.SET_PHOTO)

    except Exception as e:
        logger.error(f"Error changing photo: {e}", exc_info=True)
        await message.answer("Произошла ошибка")


@client_bot_router.message(F.text == "3", LeomatchMain.PROFILE_MANAGE)
async def change_description(message: types.Message, state: FSMContext):
    """Изменить текст профиля"""
    try:
        if await state.get_state() != LeomatchMain.PROFILE_MANAGE:
            return

        await message.answer("Введите новый текст профиля", reply_markup=reply_kb.cancel())
        await state.set_state(LeomatchMain.SET_DESCRIPTION)

    except Exception as e:
        logger.error(f"Error changing description: {e}", exc_info=True)
        await message.answer("Произошла ошибка")


@client_bot_router.message(F.text == "4", LeomatchMain.PROFILE_MANAGE)
async def view_profiles_from_manage(message: types.Message, state: FSMContext):
    """Просмотр профилей"""
    try:
        if await state.get_state() != LeomatchMain.PROFILE_MANAGE:
            return

        await profiles.start(message, state)

    except Exception as e:
        logger.error(f"Error viewing profiles: {e}", exc_info=True)
        await message.answer("Произошла ошибка при просмотре профилей")


@client_bot_router.message(F.text == "Отменить", LeomatchMain.SET_DESCRIPTION)
@client_bot_router.message(F.text == "Отменить", LeomatchMain.SET_PHOTO)
async def cancel_changes(message: types.Message, state: FSMContext):
    """Отменить изменения"""
    try:
        current_state = await state.get_state()
        if current_state not in [LeomatchMain.SET_DESCRIPTION, LeomatchMain.SET_PHOTO]:
            return

        await start(message, state)

    except Exception as e:
        logger.error(f"Error canceling changes: {e}", exc_info=True)
        await message.answer("Произошла ошибка")


@client_bot_router.message(LeomatchMain.SET_DESCRIPTION)
async def save_description(message: types.Message, state: FSMContext):
    """Сохранить текст профиля"""
    try:
        if await state.get_state() != LeomatchMain.SET_DESCRIPTION:
            return

        await update_profile(message.from_user.id, {"about_me": message.text})
        logger.info(f"Updated profile description for user {message.from_user.id}")
        await start(message, state)

    except Exception as e:
        logger.error(f"Error saving description: {e}", exc_info=True)
        await message.answer("Произошла ошибка при сохранении текста")


@client_bot_router.message(LeomatchMain.SET_PHOTO)
async def save_media(message: types.Message, state: FSMContext):
    """Хранение изображений/видео"""
    try:
        if await state.get_state() != LeomatchMain.SET_PHOTO:
            return

        photo = ""
        media_type = ""

        if message.photo:
            photo = message.photo[-1].file_id
            media_type = "PHOTO"
        elif message.video:
            if message.video.duration > 15:
                await message.answer("Пожалуйста, пришли видео не более 15 секунд")
                return
            photo = message.video.file_id
            media_type = "VIDEO"
        elif message.video_note:
            if message.video_note.duration > 15:
                await message.answer("Пожалуйста, пришли видео не более 15 секунд")
                return
            photo = message.video_note.file_id
            media_type = "VIDEO_NOTE"
        else:
            await message.answer("Пожалуйста, отправьте фото или видео")
            return

        await update_profile(message.from_user.id, {"photo": photo, "media_type": media_type})
        logger.info(f"Updated profile media for user {message.from_user.id}")
        await start(message, state)

    except Exception as e:
        logger.error(f"Error saving media: {e}", exc_info=True)
        await message.answer("Произошла ошибка при сохранении медиафайла")
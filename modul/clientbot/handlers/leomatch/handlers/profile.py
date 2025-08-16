import os
import traceback

from aiogram import types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from asgiref.sync import sync_to_async

from modul.clientbot.handlers.leomatch.keyboards import reply_kb
from modul.clientbot.handlers.leomatch.data.state import LeomatchMain, LeomatchRegistration, LeomatchProfiles
from modul.clientbot.handlers.leomatch.shortcuts import get_leo, show_profile_db, update_profile
from modul.clientbot.handlers.leomatch.handlers.shorts import begin_registration
from modul.clientbot.handlers.leomatch.handlers import profiles
from modul.clientbot.utils.functs import return_main
from modul.loader import client_bot_router
from aiogram.fsm.context import FSMContext
from aiogram import Bot

__all__ = ['start', 'bot_start', 'profile_start']

from modul.models import LeoMatchModel


async def start(message: types.Message, state: FSMContext):
    data = await state.get_data()
    user_id = data.get("me") if data.get("me") else message.from_user.id

    print(f"DEBUG: profile start() called for user {user_id}")

    leo = await get_leo(user_id)
    if not leo:
        await message.answer(
            "❌ Профиль не найден. Необходимо пройти регистрацию.",
            reply_markup=reply_kb.begin_registration()
        )
        await state.set_state(LeomatchRegistration.BEGIN)
        return

    await show_profile_db(message, user_id)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Отредактировать профиль", callback_data="edit_full_profile")],
        [InlineKeyboardButton(text="📸 Изменить фото/видео", callback_data="change_media")],
        [InlineKeyboardButton(text="📝 Изменить описание", callback_data="change_description")],
        [InlineKeyboardButton(text="👀 Просмотреть профили", callback_data="view_profiles")],
        [InlineKeyboardButton(text="🚪 Выйти", callback_data="exit_profile_menu")]
    ])

    await message.answer(
        "⚙️ Управление профилем\n\nВыберите действие:",
        reply_markup=keyboard
    )
    await state.set_state(LeomatchMain.PROFILE_MANAGE)


@client_bot_router.callback_query(F.data == "view_profiles", LeomatchMain.WAIT)
async def handle_view_profiles_from_wait(callback: types.CallbackQuery, state: FSMContext):
    """Profil ko'rishni boshlash (WAIT state'dan)"""
    print(f"\n🔥 === CALLBACK DEBUG START ===")
    print(f"callback.from_user.id: {callback.from_user.id}")
    print(f"callback.from_user.username: {callback.from_user.username}")

    # REAL USER ID
    real_user_id = callback.from_user.id
    print(f"✅ Using real_user_id: {real_user_id}")

    # State'ga saqlash
    await state.update_data(me=real_user_id)

    # Leo profilini tekshirish
    leo = await get_leo(real_user_id)
    if not leo:
        print(f"❌ Leo not found for user: {real_user_id}")
        await callback.message.edit_text(
            "❌ Профиль не найден. Необходимо пройти регистрацию.",
            reply_markup=reply_kb.begin_registration()
        )
        await state.set_state(LeomatchRegistration.BEGIN)
        await callback.answer()
        return

    print(f"✅ Leo found: {leo.full_name}")

    # Active qilish
    if not leo.active or not leo.search:
        await update_profile(real_user_id, {"active": True, "search": True})

    await callback.message.edit_reply_markup()

    # profiles modulini import qilish (ichkarida, circular import'ni oldini olish uchun)
    from modul.clientbot.handlers.leomatch.handlers import profiles

    await profiles.start(callback.message, state)
    print(f"=== CALLBACK DEBUG END ===\n")

    await callback.answer("🔍 Начинаем поиск профилей")




@client_bot_router.callback_query(F.data == "my_profile", LeomatchMain.WAIT)
async def handle_my_profile_from_wait(callback: types.CallbackQuery, state: FSMContext):
    """Mening profilim (WAIT state'dan)"""
    # Leo profili mavjudligini tekshirish
    leo = await get_leo(callback.from_user.id)  # callback.from_user.id ishlatish
    if not leo:
        await callback.message.edit_text(
            "❌ Профиль не найден. Необходимо пройти регистрацию.",
            reply_markup=reply_kb.begin_registration()
        )
        await state.set_state(LeomatchRegistration.BEGIN)
        await callback.answer()
        return

    # User ID ni state'ga saqlash
    await state.update_data(me=callback.from_user.id)

    await callback.message.edit_reply_markup()
    await start(callback.message, state)
    await callback.answer()


@client_bot_router.callback_query(F.data == "stop_search", LeomatchMain.WAIT)
async def handle_stop_search(callback: types.CallbackQuery, state: FSMContext):
    """Qidiruvni to'xtatish"""
    # User ID ni state'ga saqlash
    await state.update_data(me=callback.from_user.id)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да, деактивировать", callback_data="confirm_deactivate")],
        [InlineKeyboardButton(text="❌ Нет, показать матчи", callback_data="show_matches")]
    ])

    await callback.message.edit_text(
        "🤔 Тогда ты не будешь знать, кому ты нравишься...\n\n"
        "Уверены насчет деактивации?",
        reply_markup=keyboard
    )
    await state.set_state(LeomatchMain.SLEEP)
    await callback.answer()


@client_bot_router.callback_query(F.data == "confirm_deactivate", LeomatchMain.SLEEP)
async def handle_confirm_deactivate(callback: types.CallbackQuery, state: FSMContext):
    """Deaktivatsiyani tasdiqlash"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👀 Просмотр профилей", callback_data="view_profiles")]
    ])

    await callback.message.edit_text(
        "😊 Надеюсь, вы встретили кого-нибудь с моей помощью!\n\n"
        "Всегда рад пообщаться. Если скучно, напиши мне - я найду для тебя кого-то особенного.",
        reply_markup=keyboard
    )

    await update_profile(callback.from_user.id, {"active": False, "search": False})
    await state.set_state(LeomatchMain.WAIT)
    await callback.answer("😴 Профиль деактивирован")


@client_bot_router.callback_query(F.data == "show_matches", LeomatchMain.SLEEP)
async def handle_show_matches(callback: types.CallbackQuery, state: FSMContext):
    """Matchlarni ko'rsatish"""
    await callback.message.edit_reply_markup()
    await start(callback.message, state)
    await callback.answer()


@client_bot_router.callback_query(F.data == "edit_full_profile", LeomatchMain.PROFILE_MANAGE)
async def handle_edit_full_profile(callback: types.CallbackQuery, state: FSMContext):
    """To'liq profilni tahrirlash"""
    await callback.message.edit_reply_markup()
    await begin_registration(callback.message, state)
    await callback.answer("✏️ Начинаем редактирование профиля")


@client_bot_router.callback_query(F.data == "change_media", LeomatchMain.PROFILE_MANAGE)
async def handle_change_media(callback: types.CallbackQuery, state: FSMContext):
    """Media o'zgartirish"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_media_change")]
    ])

    await callback.message.edit_text(
        "📸 Отправьте новое фото или видео (до 15 сек)",
        reply_markup=keyboard
    )
    await state.set_state(LeomatchMain.SET_PHOTO)
    await callback.answer()


@client_bot_router.callback_query(F.data == "change_description", LeomatchMain.PROFILE_MANAGE)
async def handle_change_description(callback: types.CallbackQuery, state: FSMContext):
    """Tavsifni o'zgartirish"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_description_change")]
    ])

    await callback.message.edit_text(
        "📝 Введите новое описание профиля",
        reply_markup=keyboard
    )
    await state.set_state(LeomatchMain.SET_DESCRIPTION)
    await callback.answer()


@client_bot_router.callback_query(F.data == "view_profiles", LeomatchMain.PROFILE_MANAGE)
async def handle_view_profiles_from_profile(callback: types.CallbackQuery, state: FSMContext):
    """Profillarni ko'rish (PROFILE_MANAGE state'dan)"""
    await callback.message.edit_reply_markup()
    await profiles.start(callback.message, state)
    await callback.answer()


@client_bot_router.callback_query(F.data == "exit_profile_menu")
async def handle_exit_profile_menu(callback: types.CallbackQuery, state: FSMContext):
    """Profil menyusidan chiqish"""
    bot = callback.message.bot
    await callback.message.edit_reply_markup()
    await return_main(callback.message, state, bot)
    await callback.answer("🏠 Возвращаемся в главное меню")


@client_bot_router.callback_query(F.data == "cancel_media_change", LeomatchMain.SET_PHOTO)
async def handle_cancel_media_change(callback: types.CallbackQuery, state: FSMContext):
    """Media o'zgartirishni bekor qilish"""
    await callback.message.edit_reply_markup()
    await start(callback.message, state)
    await callback.answer("❌ Отменено")


@client_bot_router.callback_query(F.data == "cancel_description_change", LeomatchMain.SET_DESCRIPTION)
async def handle_cancel_description_change(callback: types.CallbackQuery, state: FSMContext):
    """Tavsif o'zgartirishni bekor qilish"""
    await callback.message.edit_reply_markup()
    await start(callback.message, state)
    await callback.answer("❌ Отменено")


# =============== MESSAGE HANDLERS (BACKWARD COMPATIBILITY) ===============

@client_bot_router.message(F.text == "1", LeomatchMain.WAIT)
async def handle_view_profiles_text(message: types.Message, state: FSMContext):
    """Profillarni ko'rish (matn orqali)"""
    leo = await get_leo(message.from_user.id)
    if not leo:
        await message.answer("❌ Профиль не найден. Необходимо пройти регистрацию.")
        return

    if not leo.active or not leo.search:
        await update_profile(message.from_user.id, {"active": True, "search": True})
    await profiles.start(message, state)


@client_bot_router.message(F.text == "2", LeomatchMain.WAIT)
async def handle_my_profile_text(message: types.Message, state: FSMContext):
    """Mening profilim (matn orqali)"""
    leo = await get_leo(message.from_user.id)
    if not leo:
        await message.answer(
            "❌ Профиль не найден. Необходимо пройти регистрацию.",
            reply_markup=reply_kb.begin_registration()
        )
        await state.set_state(LeomatchRegistration.BEGIN)
        return
    await start(message, state)


@client_bot_router.message(F.text == ("Выйти"), LeomatchMain.WAIT)
@client_bot_router.message(F.text == ("Выйти"), LeomatchMain.PROFILE_MANAGE)
async def handle_exit_text(message: types.Message, state: FSMContext):
    """Chiqish (matn orqali)"""
    bot = message.bot
    await return_main(message, state, bot)


@client_bot_router.message(F.text == "3", LeomatchMain.WAIT)
async def handle_stop_search_text(message: types.Message, state: FSMContext):
    """Qidiruvni to'xtatish (matn orqali)"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да, деактивировать", callback_data="confirm_deactivate")],
        [InlineKeyboardButton(text="❌ Нет, показать матчи", callback_data="show_matches")]
    ])

    await message.answer(
        "🤔 Тогда ты не будешь знать, кому ты нравишься...\n\n"
        "Уверены насчет деактивации?",
        reply_markup=keyboard
    )
    await state.set_state(LeomatchMain.SLEEP)


@client_bot_router.message(F.text == "1", LeomatchMain.SLEEP)
async def handle_confirm_deactivate_text(message: types.Message, state: FSMContext):
    """Deaktivatsiyani tasdiqlash (matn orqali)"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👀 Просмотр профилей", callback_data="view_profiles")]
    ])

    await message.answer(
        "😊 Надеюсь, вы встретили кого-нибудь с моей помощью!\n\n"
        "Всегда рад пообщаться. Если скучно, напиши мне - я найду для тебя кого-то особенного.",
        reply_markup=keyboard
    )

    await update_profile(message.from_user.id, {"active": False, "search": False})
    await state.set_state(LeomatchMain.WAIT)


@client_bot_router.message(F.text == "2", LeomatchMain.SLEEP)
async def handle_show_matches_text(message: types.Message, state: FSMContext):
    """Matchlarni ko'rsatish (matn orqali)"""
    await start(message, state)


@client_bot_router.message(F.text == "1", LeomatchMain.PROFILE_MANAGE)
async def handle_edit_full_profile_text(message: types.Message, state: FSMContext):
    """To'liq profilni tahrirlash (matn orqali)"""
    await begin_registration(message, state)


@client_bot_router.message(F.text == "2", LeomatchMain.PROFILE_MANAGE)
async def handle_change_media_text(message: types.Message, state: FSMContext):
    """Media o'zgartirish (matn orqali)"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_media_change")]
    ])
    await message.answer("📸 Отправьте новое фото или видео (до 15 сек)", reply_markup=keyboard)
    await state.set_state(LeomatchMain.SET_PHOTO)


@client_bot_router.message(F.text == "3", LeomatchMain.PROFILE_MANAGE)
async def handle_change_description_text(message: types.Message, state: FSMContext):
    """Tavsifni o'zgartirish (matn orqali)"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_description_change")]
    ])
    await message.answer("📝 Введите новое описание профиля", reply_markup=keyboard)
    await state.set_state(LeomatchMain.SET_DESCRIPTION)


@client_bot_router.message(F.text == "4", LeomatchMain.PROFILE_MANAGE)
async def handle_view_profiles_from_profile_text(message: types.Message, state: FSMContext):
    """Profillarni ko'rish (PROFILE_MANAGE state'dan, matn orqali)"""
    await profiles.start(message, state)


@client_bot_router.message(F.text == ("Отменить"), LeomatchMain.SET_DESCRIPTION)
async def handle_cancel_description_text(message: types.Message, state: FSMContext):
    """Tavsif o'zgartirishni bekor qilish (matn orqali)"""
    await start(message, state)


@client_bot_router.message(LeomatchMain.SET_DESCRIPTION)
async def handle_description_input(message: types.Message, state: FSMContext):
    """Yangi tavsifni qabul qilish"""
    if len(message.text) > 300:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_description_change")]
        ])
        await message.answer("📝 Описание слишком длинное. Максимум 300 символов.", reply_markup=keyboard)
        return

    await update_profile(message.from_user.id, {"about_me": message.text})
    await message.answer("✅ Описание успешно обновлено!")
    await start(message, state)


@client_bot_router.message(F.text == ("Отменить"), LeomatchMain.SET_PHOTO)
async def handle_cancel_media_text(message: types.Message, state: FSMContext):
    """Media o'zgartirishni bekor qilish (matn orqali)"""
    await start(message, state)


@client_bot_router.message(LeomatchMain.SET_PHOTO)
async def handle_media_upload(message: types.Message, state: FSMContext, bot: Bot):
    """Yangi media faylni qabul qilish"""
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
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_media_change")]
                ])
                await message.answer("⚠️ Пожалуйста, пришлите видео не более 15 секунд", reply_markup=keyboard)
                return
            photo = message.video
            media_type = "VIDEO"
            file_extension = ".mp4"
        elif message.video_note:
            if message.video_note.duration > 15:
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_media_change")]
                ])
                await message.answer("⚠️ Пожалуйста, пришлите видео не более 15 секунд", reply_markup=keyboard)
                return
            photo = message.video_note
            media_type = "VIDEO_NOTE"
            file_extension = ".mp4"
        else:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_media_change")]
            ])
            await message.answer("📸 Пожалуйста, отправьте фото или видео", reply_markup=keyboard)
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
                # Показываем процесс загрузки
                loading_msg = await message.answer("⏳ Загружаю файл...")

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

                    await loading_msg.delete()

                    if success:
                        await message.answer("✅ Фото/видео успешно обновлено!")
                        await start(message, state)
                    else:
                        await message.answer("❌ Произошла ошибка при обновлении базы данных")
                else:
                    print(f"WARNING: File was not saved: {abs_file_path}")
                    await loading_msg.delete()
                    await message.answer("❌ Произошла ошибка при сохранении файла")
            except Exception as download_error:
                print(f"Error downloading file: {download_error}")
                print(f"Error traceback: {traceback.format_exc()}")
                try:
                    await loading_msg.delete()
                except:
                    pass
                await message.answer("❌ Ошибка при загрузке файла")
        else:
            await message.answer("❌ Не удалось получить файл")

    except Exception as e:
        print(f"Error in SET_PHOTO handler: {e}")
        print(f"Error traceback: {traceback.format_exc()}")
        await message.answer("❌ Произошла ошибка при обновлении фото/видео")


# =============== LEGACY COMPATIBILITY ===============

# Legacy function for backward compatibility
async def bot_start(message: types.Message, state: FSMContext):
    """Legacy funksiya - backward compatibility uchun"""
    await start(message, state)


# Legacy alias
profile_start = start  # Yangi nom uchun alias


# =============== UTILITY FUNCTIONS ===============

def create_profile_menu_keyboard():
    """Profil boshqaruv menyusi klaviaturasini yaratish"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Отредактировать профиль", callback_data="edit_full_profile")],
        [InlineKeyboardButton(text="📸 Изменить фото/видео", callback_data="change_media")],
        [InlineKeyboardButton(text="📝 Изменить описание", callback_data="change_description")],
        [InlineKeyboardButton(text="👀 Просмотреть профили", callback_data="view_profiles")],
        [InlineKeyboardButton(text="🚪 Выйти", callback_data="exit_profile_menu")]
    ])


def create_deactivation_keyboard():
    """Deaktivatsiya tasdiqlash klaviaturasi"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да, деактивировать", callback_data="confirm_deactivate")],
        [InlineKeyboardButton(text="❌ Нет, показать матчи", callback_data="show_matches")]
    ])


def create_cancel_keyboard(cancel_action: str):
    """Bekor qilish klaviaturasi"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отменить", callback_data=cancel_action)]
    ])
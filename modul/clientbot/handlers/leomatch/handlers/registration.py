import os

import aiohttp
from aiogram import types, Bot, F
from aiogram.exceptions import TelegramNetworkError
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from asgiref.sync import sync_to_async

from modul.clientbot.handlers.leomatch.keyboards import reply_kb
from modul.clientbot.handlers.leomatch.data.state import LeomatchRegistration
from modul.clientbot.handlers.leomatch.handlers.shorts import manage, begin_registration, set_which_search, set_sex
from modul.clientbot.handlers.leomatch.shortcuts import add_leo, get_leo, show_profile, update_leo
from modul.clientbot.utils.functs import return_main
from modul.clientbot.shortcuts import get_current_bot
from modul.loader import client_bot_router, bot_session
from aiogram.fsm.context import FSMContext

from modul.models import User


async def now_send_photo(message: types.Message, state: FSMContext):
    leo = await get_leo(message.from_user.id)
    kwargs = {}
    print(kwargs)
    if leo:
        # Inline keyboard yaratamiz
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Оставить текущее", callback_data="save_current_photo")]
        ])
        kwargs['reply_markup'] = keyboard
    await message.answer(("Теперь пришли фото или запиши видео 👍 (до 15 сек), его будут видеть другие пользователи"),
                         **kwargs)
    await state.set_state(LeomatchRegistration.SEND_PHOTO)


def get_file_extension(media_type):
    if media_type in ["VIDEO", "VIDEO_NOTE"]:
        return "mp4"
    else:
        return "jpg"


async def save_media(message: types.Message, state: FSMContext, file_path: str, media_type: str):
    try:
        # Oldingi state ma'lumotlarini olish
        data = await state.get_data()
        print(f"Data in save_media BEFORE: {data}")

        # Qolgan ma'lumotlarni olish
        age = data.get('age')
        full_name = data.get('full_name')
        about_me = data.get('about_me')
        city = data.get('city')

        # Profilni ko'rsatish
        await show_profile(message, message.from_user.id, full_name, age, city, about_me, file_path, media_type)

        # Yangi statega o'tish
        await state.set_state(LeomatchRegistration.FINAL)

        # MUHIM: barcha ma'lumotlarni qayta saqlash va file_path, media_type ni ham qo'shish
        await state.update_data(
            photo=file_path,  # file_path ni photo sifatida saqlash
            media_type=media_type,  # Parametr orqali kelgan media_type ni saqlash
            age=age,
            full_name=full_name,
            about_me=about_me,
            city=city
        )

        # Tekshirish uchun
        updated_data = await state.get_data()
        print(f"Data in save_media AFTER: {updated_data}")

        await message.answer("Всё верно?", reply_markup=reply_kb.final_registration())

    except Exception as e:
        print(f"Error in save_media: {e}")
        await message.answer("Произошла ошибка при сохранении медиа")


async def download_file(url: str, file_path: str):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                with open(file_path, 'wb') as f:
                    while True:
                        chunk = await response.content.read(1024)
                        if not chunk:
                            break
                        f.write(chunk)
            else:
                raise Exception(f"Failed to download file: HTTP {response.status}")


async def show_about_step(callback, state: FSMContext, is_text_message=False):
    """About me bosqichi"""
    leo = await get_leo(callback.message.chat.id)
    has_existing = leo and leo.about_me

    keyboard = reply_kb.about_me_options(has_existing=has_existing)

    data = await state.get_data()
    sex_text = "Парень" if data.get('sex') == "MALE" else "Девушка"
    search_text = {"MALE": "Парня", "FEMALE": "Девушку", "ANY": "Всех"}[data.get('which_search')]

    text = f"✅ Возраст: {data.get('age')}\n✅ Пол: {sex_text}\n✅ Ищешь: {search_text}\n✅ Город: {data.get('city')}\n✅ Имя: {data.get('full_name')}\n\n📝 Расскажи о себе:"

    # Agar text message'dan kelgan bo'lsa, yangi xabar yuborish
    if is_text_message or not hasattr(callback.message, 'edit_text'):
        await callback.message.answer(text, reply_markup=keyboard)
    else:
        # Callback message'dan kelgan bo'lsa, edit qilish
        await callback.message.edit_text(text, reply_markup=keyboard)

    await state.set_state(LeomatchRegistration.ABOUT_ME)


async def show_photo_step(callback, state: FSMContext, is_text_message=False):
    leo = await get_leo(callback.message.chat.id)
    has_existing = leo and leo.photo

    keyboard = reply_kb.photo_options(has_existing=has_existing)

    data = await state.get_data()
    sex_text = "Парень" if data.get('sex') == "MALE" else "Девушка"
    search_text = {"MALE": "Парня", "FEMALE": "Девушку", "ANY": "Всех"}[data.get('which_search')]

    text = f"✅ Возраст: {data.get('age')}\n✅ Пол: {sex_text}\n✅ Ищешь: {search_text}\n✅ Город: {data.get('city')}\n✅ Имя: {data.get('full_name')}\n✅ Описание: есть\n\n📷 Загрузи фото или видео:"

    if is_text_message or not hasattr(callback.message, 'edit_text'):
        await callback.message.answer(text, reply_markup=keyboard)
    else:
        await callback.message.edit_text(text, reply_markup=keyboard)

    await state.set_state(LeomatchRegistration.SEND_PHOTO)


async def show_final_step(callback, state: FSMContext, is_text_message=False):
    """Yakuniy bosqich"""
    data = await state.get_data()

    keyboard = reply_kb.final_registration()

    sex_text = "Парень" if data.get('sex') == "MALE" else "Девушка"
    search_text = {"MALE": "Парня", "FEMALE": "Девушку", "ANY": "Всех"}[data.get('which_search')]

    text = f"🎯 Проверьте данные:\n\n✅ Возраст: {data.get('age')}\n✅ Пол: {sex_text}\n✅ Ищешь: {search_text}\n✅ Город: {data.get('city')}\n✅ Имя: {data.get('full_name')}\n✅ Описание: есть\n✅ Фото/видео: есть\n\nВсё верно?"

    if is_text_message or not hasattr(callback.message, 'edit_text'):
        await callback.message.answer(text, reply_markup=keyboard)
    else:
        await callback.message.edit_text(text, reply_markup=keyboard)

    await state.set_state(LeomatchRegistration.FINAL)


# =============== CALLBACK QUERY HANDLERS ===============

@client_bot_router.callback_query(F.data == "start_registration", LeomatchRegistration.BEGIN)
async def handle_start_registration(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.username == None:
        await callback.message.answer(
            "Настоятельно рекомендуем указать username или в настройках разрешение на пересылку сообщения иначе Вам не смогут написать те, кого вы лайкните")

    await begin_registration(callback.message, state)
    await callback.answer()


@client_bot_router.callback_query(F.data == "sex_male", LeomatchRegistration.SEX)
async def handle_sex_male(callback: types.CallbackQuery, state: FSMContext):
    """Erkak tanlash"""
    data = await state.get_data()
    await state.update_data(sex="MALE")

    keyboard = reply_kb.which_search()

    await callback.message.edit_text(
        f"✅ Возраст: {data.get('age')}\n✅ Пол: Парень\n\n💕 Кого ищешь?",
        reply_markup=keyboard
    )
    await state.set_state(LeomatchRegistration.WHICH_SEARCH)
    await callback.answer()


@client_bot_router.callback_query(F.data == "sex_female", LeomatchRegistration.SEX)
async def handle_sex_female(callback: types.CallbackQuery, state: FSMContext):
    """Ayol tanlash"""
    data = await state.get_data()
    await state.update_data(sex="FEMALE")

    keyboard = reply_kb.which_search()

    await callback.message.edit_text(
        f"✅ Возраст: {data.get('age')}\n✅ Пол: Девушка\n\n💕 Кого ищешь?",
        reply_markup=keyboard
    )
    await state.set_state(LeomatchRegistration.WHICH_SEARCH)
    await callback.answer()

@client_bot_router.callback_query(F.data == "search_male", LeomatchRegistration.WHICH_SEARCH)
async def handle_search_male(callback: types.CallbackQuery, state: FSMContext):
    """Erkak qidirish"""
    data = await state.get_data()
    await state.update_data(which_search="MALE")

    keyboard = reply_kb.city_input()

    sex_text = "Парень" if data.get('sex') == "MALE" else "Девушка"

    await callback.message.edit_text(
        f"✅ Возраст: {data.get('age')}\n✅ Пол: {sex_text}\n✅ Ищешь: Парня\n\n🏙️ Введи свой город:",
        reply_markup=keyboard
    )
    await state.set_state(LeomatchRegistration.CITY)
    await callback.answer()

@client_bot_router.callback_query(F.data == "search_female", LeomatchRegistration.WHICH_SEARCH)
async def handle_search_female(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await state.update_data(which_search="FEMALE")

    keyboard = reply_kb.city_input()

    sex_text = "Парень" if data.get('sex') == "MALE" else "Девушка"

    await callback.message.edit_text(
        f"✅ Возраст: {data.get('age')}\n✅ Пол: {sex_text}\n✅ Ищешь: Девушку\n\n🏙️ Введи свой город:",
        reply_markup=keyboard
    )
    await state.set_state(LeomatchRegistration.CITY)
    await callback.answer()


@client_bot_router.callback_query(F.data == "search_any", LeomatchRegistration.WHICH_SEARCH)
async def handle_search_any(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await state.update_data(which_search="ANY")

    keyboard = reply_kb.city_input()

    sex_text = "Парень" if data.get('sex') == "MALE" else "Девушка"

    await callback.message.edit_text(
        f"✅ Возраст: {data.get('age')}\n✅ Пол: {sex_text}\n✅ Ищешь: Всех\n\n🏙️ Введи свой город:",
        reply_markup=keyboard
    )
    await state.set_state(LeomatchRegistration.CITY)
    await callback.answer()


@client_bot_router.callback_query(F.data == "input_city", LeomatchRegistration.CITY)
async def handle_input_city(callback: types.CallbackQuery, state: FSMContext):
    keyboard = reply_kb.text_input_with_cancel()
    # await callback.message.delete()
    await callback.message.edit_text(
        "🏙️ Напишите название вашего города:",
        reply_markup=keyboard
    )
    await callback.answer()

@client_bot_router.callback_query(F.data.startswith("name_"), LeomatchRegistration.FULL_NAME)
async def handle_name_selection(callback: types.CallbackQuery, state: FSMContext):
    name = callback.data.replace("name_", "")
    if len(name) > 15:
        await callback.answer("Имя слишком длинное (макс 15 символов)")
        return

    await state.update_data(full_name=name)
    await show_about_step(callback, state)
    await callback.answer()

@client_bot_router.callback_query(F.data == "input_custom_name", LeomatchRegistration.FULL_NAME)
async def handle_input_custom_name(callback: types.CallbackQuery, state: FSMContext):
    keyboard = reply_kb.text_input_with_cancel()

    await callback.message.edit_text(
        "📝 Напишите ваше имя (до 15 символов):",
        reply_markup=keyboard
    )
    await callback.answer()

@client_bot_router.callback_query(F.data == "save_current_about", LeomatchRegistration.ABOUT_ME)
async def handle_save_current_about(callback: types.CallbackQuery, state: FSMContext):
    leo = await get_leo(callback.from_user.id)
    if not leo or not leo.about_me:
        await callback.answer("Нет сохраненного описания")
        return

    await state.update_data(about_me=leo.about_me)
    await show_photo_step(callback, state)
    await callback.answer()



@client_bot_router.callback_query(F.data == "input_new_about", LeomatchRegistration.ABOUT_ME)
async def handle_input_new_about(callback: types.CallbackQuery, state: FSMContext):
    keyboard = reply_kb.text_input_with_cancel()
    # await callback.message.delete()
    await callback.message.edit_text(
        "📝 Напишите описание о себе (до 300 символов):",
        reply_markup=keyboard
    )
    await callback.answer()

@client_bot_router.callback_query(F.data == "save_current_photo", LeomatchRegistration.SEND_PHOTO)
async def handle_save_current_photo(callback: types.CallbackQuery, state: FSMContext):
    leo = await get_leo(callback.from_user.id)
    if not leo or not leo.photo:
        await callback.answer("Нет сохраненного фото")
        return

    await state.update_data(photo=leo.photo, media_type=leo.media_type)
    await show_final_step(callback, state)
    await callback.answer()


@client_bot_router.callback_query(F.data == "upload_new_photo", LeomatchRegistration.SEND_PHOTO)
async def handle_upload_new_photo(callback: types.CallbackQuery, state: FSMContext):
    keyboard = reply_kb.text_input_with_cancel()
    # await callback.message.delete()
    await state.set_state(LeomatchRegistration.SEND_PHOTO)
    await callback.message.edit_text(
        "📷 Пришлите фото или видео (до 15 сек):",
        reply_markup=keyboard
    )
    await callback.answer()


@client_bot_router.callback_query(F.data == "final_yes", LeomatchRegistration.FINAL)
async def handle_final_yes(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    try:
        data = await state.get_data()
        print(f"Final data: {data}")

        photo = data['photo']
        media_type = data['media_type']
        sex = data['sex']
        age = data['age']
        full_name = data['full_name']
        about_me = data['about_me']
        city = data['city']
        which_search = data['which_search']

        # Get bot username
        bot_info = await bot.get_me()
        bot_username = bot_info.username

        try:
            from modul.models import UserTG, LeoMatchModel

            @sync_to_async
            def get_or_create_leo():
                # User topish yoki yaratish
                user, created = UserTG.objects.get_or_create(
                    uid=str(callback.from_user.id),
                    defaults={
                        'username': f"user_{callback.from_user.id}",
                        'first_name': full_name if full_name else f"User {callback.from_user.id}"
                    }
                )
                print(f"User {'created' if created else 'found'}: {user}")

                # Django User yaratish agar yo'q bo'lsa
                if user.user is None:
                    django_user = User.objects.create(
                        username=f"tg_user_{user.uid}",
                        first_name=user.first_name or full_name,
                        last_name=user.last_name or "",
                    )
                    user.user = django_user
                    user.save()
                    print(f"Created Django User with ID {django_user.id}")
                else:
                    django_user = user.user

                # LeoMatchModel yaratish yoki yangilash
                leo, leo_created = LeoMatchModel.objects.get_or_create(
                    user_id=django_user.id,
                    bot_username=bot_username,
                    defaults={
                        'photo': photo,
                        'media_type': media_type,
                        'sex': sex,
                        'age': age,
                        'full_name': full_name,
                        'about_me': about_me,
                        'city': city,
                        'which_search': which_search,
                        'active': True,
                        'search': True,
                        'blocked': False,
                        'count_likes': 0
                    }
                )

                if not leo_created:
                    # Update existing record
                    leo.photo = photo
                    leo.media_type = media_type
                    leo.sex = sex
                    leo.age = age
                    leo.full_name = full_name
                    leo.about_me = about_me
                    leo.city = city
                    leo.which_search = which_search
                    leo.active = True
                    leo.search = True
                    leo.save()

                return True

            success = await get_or_create_leo()

            if success:
                await state.clear()
                await callback.message.edit_text("✅ Регистрация завершена успешно!")

                await state.update_data(me=callback.from_user.id)

                import asyncio
                await asyncio.sleep(0.5)

                await manage(callback.message, state)
                await callback.answer("Добро пожаловать!")
            else:
                await callback.message.edit_text("❌ Произошла ошибка при сохранении. Попробуйте еще раз.")
                await callback.answer("Ошибка сохранения")

        except Exception as db_error:
            print(f"Database error: {db_error}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")

            await callback.message.edit_text("❌ Произошла ошибка при сохранении данных. Попробуйте еще раз.")
            await callback.answer("Ошибка сохранения")

    except Exception as e:
        print(f"Error in final_yes handler: {e}")
        await callback.answer("Произошла ошибка")


@client_bot_router.callback_query(F.data.startswith("age_"), LeomatchRegistration.AGE)
async def handle_age_selection(callback: types.CallbackQuery, state: FSMContext):
    """Yosh tanlash"""
    try:
        age_str = callback.data.replace("age_", "")
        age = int(age_str)

        await state.update_data(age=age)

        # Jins tanlash keyboard
        keyboard = reply_kb.chooice_sex()

        await callback.message.edit_text(
            f"✅ Возраст: {age}\n\n👤 Теперь определимся с полом!",
            reply_markup=keyboard
        )
        await state.set_state(LeomatchRegistration.SEX)
        await callback.answer()

    except Exception as e:
        print(f"Error in age selection: {e}")
        await callback.answer("Ошибка")


@client_bot_router.callback_query(F.data == "custom_age", LeomatchRegistration.AGE)
async def handle_custom_age(callback: types.CallbackQuery, state: FSMContext):
    """Boshqa yosh kiritish"""
    keyboard = reply_kb.text_input_with_cancel()

    await callback.message.edit_text(
        "✏️ Введите ваш возраст цифрами (например: 25):",
        reply_markup=keyboard
    )
    await callback.answer()

@client_bot_router.callback_query(F.data == "cancel_registration")
async def handle_cancel_registration(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    """Registratsiyani bekor qilish"""
    await callback.message.edit_text("❌ Регистрация отменена")
    await return_main(callback.message, state, bot)
    await callback.answer("Регистрация отменена")



@client_bot_router.callback_query(F.data == "final_edit", LeomatchRegistration.FINAL)
async def handle_final_edit(callback: types.CallbackQuery, state: FSMContext):
    await begin_registration(callback.message, state)
    await callback.answer()


# =============== MESSAGE HANDLERS (BACKWARD COMPATIBILITY) ===============

@client_bot_router.message(F.text == "Давай, начнем!", LeomatchRegistration.BEGIN)
async def bot_start_lets_leo(message: types.Message, state: FSMContext):
    if message.from_user.username == None:
        await message.answer(
            "Настоятельно рекомендуем указать username или в настройках разрешение на пересылку сообщения иначе Вам не смогут написать те, кого вы лайкните")
    await begin_registration(message, state)


@client_bot_router.message(LeomatchRegistration.AGE)
async def handle_age_input(message: Message, state: FSMContext, bot: Bot):
    try:
        age = int(message.text)
        await state.update_data(age=age)

        keyboard = reply_kb.chooice_sex()
        await message.answer(f"✅ Возраст: {age}\n\n👤 Теперь определимся с полом!", reply_markup=keyboard)
        await state.set_state(LeomatchRegistration.SEX)
    except ValueError:
        if message.text == "Отменить":
            await return_main(message, state, bot)
            return
        await message.answer("Пожалуйста, введите возраст цифрами")


# Message handlers for backward compatibility
@client_bot_router.message(F.text == ("Я парень"), LeomatchRegistration.SEX)
async def handle_male_text(message: types.Message, state: FSMContext):
    await set_sex("MALE", message, state)


@client_bot_router.message(F.text == ("Я девушка"), LeomatchRegistration.SEX)
async def handle_female_text(message: types.Message, state: FSMContext):
    await set_sex("FEMALE", message, state)


@client_bot_router.message(LeomatchRegistration.SEX)
async def handle_sex_fallback(message: types.Message):
    await message.answer(("Пожалуйста, укажите Ваш пол, нажав на кнопку"), reply_markup=reply_kb.chooice_sex())


@client_bot_router.message(F.text == ("Парня"), LeomatchRegistration.WHICH_SEARCH)
async def handle_search_male_text(message: types.Message, state: FSMContext):
    await set_which_search("MALE", message, state)


@client_bot_router.message(F.text == ("Девушку"), LeomatchRegistration.WHICH_SEARCH)
async def handle_search_female_text(message: types.Message, state: FSMContext):
    await set_which_search("FEMALE", message, state)


@client_bot_router.message(F.text == ("Мне всё равно"), LeomatchRegistration.WHICH_SEARCH)
async def handle_search_any_text(message: types.Message, state: FSMContext):
    await set_which_search("ANY", message, state)


@client_bot_router.message(LeomatchRegistration.WHICH_SEARCH)
async def handle_search_fallback(message: types.Message):
    await message.answer(("Пожалуйста, укажите кого Вы ищите, нажав на кнопку"), reply_markup=reply_kb.which_search())


@client_bot_router.message(LeomatchRegistration.CITY)
async def handle_city_input(message: types.Message, state: FSMContext):
    city = message.text.strip()
    await state.update_data(city=city)

    data = await state.get_data()
    suggested_name = message.from_user.full_name or message.from_user.first_name or "Пользователь"

    keyboard = reply_kb.name_suggestion(suggested_name)

    sex_text = "Парень" if data.get('sex') == "MALE" else "Девушка"
    search_text = {"MALE": "Парня", "FEMALE": "Девушку", "ANY": "Всех"}[data.get('which_search')]

    await message.answer(
        f"✅ Возраст: {data.get('age')}\n✅ Пол: {sex_text}\n✅ Ищешь: {search_text}\n✅ Город: {city}\n\n📝 Как тебя зовут?",
        reply_markup=keyboard
    )
    await state.set_state(LeomatchRegistration.FULL_NAME)


@client_bot_router.message(LeomatchRegistration.FULL_NAME)
async def handle_name_input(message: types.Message, state: FSMContext):
    name = message.text.strip()
    if len(name) > 15:
        await message.answer("Пожалуйста, введите имя не более 15 символов")
        return

    await state.update_data(full_name=name)

    class MessageWrapper:
        def __init__(self, msg):
            self.message = msg

    await show_about_step(MessageWrapper(message), state, is_text_message=True)


@client_bot_router.message(F.text == ("Оставить текущее"), LeomatchRegistration.ABOUT_ME)
async def handle_save_current_about_text(message: types.Message, state: FSMContext):
    leo = await get_leo(message.from_user.id)
    if not leo:
        await message.answer("❌ Предыдущий текст не сохранен. Пожалуйста, введите новый текст.")
        return
    await state.update_data(about_me=leo.about_me)
    await now_send_photo(message, state)


@client_bot_router.message(LeomatchRegistration.ABOUT_ME)
async def handle_about_me_input(message: types.Message, state: FSMContext):
    if len(message.text) > 300:
        await message.answer("Описание слишком длинное (макс 300 символов)")
        return

    await state.update_data(about_me=message.text)

    # FakeCallback o'rniga to'g'ridan-to'g'ri funksiyani chaqirish
    class MessageWrapper:
        def __init__(self, msg):
            self.message = msg

    await show_photo_step(MessageWrapper(message), state, is_text_message=True)


@client_bot_router.message(F.text == ("Оставить текущее"), LeomatchRegistration.SEND_PHOTO)
async def handle_save_current_photo_text(message: types.Message, state: FSMContext):
    leo = await get_leo(message.from_user.id)
    if not leo:
        await message.answer("❌ Предыдущее медиа не сохранено. Пожалуйста, загрузите новое фото или видео.")
        return
    await save_media(message, state, leo.photo, leo.media_type)


# Import kerak bo'lgan funksiya
from modul.clientbot.handlers.leomatch.data.state import LeomatchRegistration

@client_bot_router.message(LeomatchRegistration.SEND_PHOTO)
async def handle_media_upload(message: types.Message, state: FSMContext, bot: Bot):
    if not message.photo and not message.video and not message.video_note:
        await message.answer("Пожалуйста, пришлите фото, видео или видеосообщение")
        return

    # Media processing
    url = ""
    media_type = ""
    if message.photo:
        url = message.photo[-1].file_id
        media_type = "PHOTO"
    elif message.video:
        if message.video.duration > 15:
            await message.answer("Пожалуйста, пришлите видео не более 15 секунд")
            return
        url = message.video.file_id
        media_type = "VIDEO"
    elif message.video_note:
        if message.video_note.duration > 15:
            await message.answer("Пожалуйста, пришлите видеосообщение не более 15 секунд")
            return
        url = message.video_note.file_id
        media_type = "VIDEO_NOTE"

    base_dir = "modul/clientbot/data"
    os.makedirs(base_dir, exist_ok=True)
    format_ext = "jpg" if media_type == "PHOTO" else "mp4"
    file_path = f"{base_dir}/leo{message.from_user.id}.{format_ext}"

    try:
        file = await bot.get_file(url)
        await bot.download_file(file.file_path, file_path)

        await state.update_data(photo=file_path, media_type=media_type)

        # FakeCallback o'rniga to'g'ridan-to'g'ri funksiyani chaqirish
        class MessageWrapper:
            def __init__(self, msg):
                self.message = msg

        await show_final_step(MessageWrapper(message), state, is_text_message=True)

    except Exception as e:
        print(f"Error saving media: {e}")
        await message.answer("Произошла ошибка. Попробуйте еще раз.")


@client_bot_router.message(F.text == ("Да"), LeomatchRegistration.FINAL)
async def handle_final_yes_text(message: types.Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    print(data)
    photo = data['photo']
    media_type = data['media_type']
    sex = data['sex']
    age = data['age']
    full_name = data['full_name']
    about_me = data['about_me']
    city = data['city']
    which_search = data['which_search']

    # Get bot username
    bot_info = await bot.get_me()
    bot_username = bot_info.username

    leo = await get_leo(message.from_user.id)
    if not leo:
        await add_leo(message.from_user.id, photo, media_type, sex, age, full_name, about_me, city, which_search,
                      bot_username)
    else:
        await update_leo(uid=message.from_user.id, photo=photo, media_type=media_type, sex=sex, age=age,
                         full_name=full_name, about_me=about_me, city=city, which_search=which_search)

    await state.clear()
    await manage(message, state)


@client_bot_router.message(F.text == ("Изменить анкету"), LeomatchRegistration.FINAL)
async def handle_final_edit_text(message: types.Message, state: FSMContext):
    await begin_registration(message, state)


@client_bot_router.message(LeomatchRegistration.FINAL)
async def handle_final_fallback(message: types.Message, state: FSMContext):
    await message.answer("Пожалуйста, нажмите на кнопку", reply_markup=reply_kb.final_registration())
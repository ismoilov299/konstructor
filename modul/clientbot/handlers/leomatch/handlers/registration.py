import asyncio
import logging
import os

from aiogram import types, Bot, F
from aiogram.exceptions import TelegramNetworkError
from aiogram.types import Message
from pathlib import Path
from collections import defaultdict
from datetime import datetime
from modul.clientbot.handlers.leomatch.keyboards import reply_kb
from modul.clientbot.handlers.leomatch.data.state import LeomatchRegistration
from modul.clientbot.handlers.leomatch.handlers.shorts import manage, begin_registration
from modul.clientbot.handlers.leomatch.shortcuts import add_leo, get_leo, show_profile, update_leo
from modul.clientbot.storage import message_store
from modul.clientbot.utils.functs import return_main
from modul.clientbot.shortcuts import get_current_bot
from modul.loader import client_bot_router, bot_session
from aiogram.fsm.context import FSMContext

logger = logging.getLogger(__name__)

last_message_time = defaultdict(float)
MIN_MESSAGE_INTERVAL = 1.0

async def now_send_photo(message: types.Message, state: FSMContext):
    """
    Photo/video yuborish bosqichi
    """
    try:
        leo = await get_leo(message.from_user.id)
        kwargs = {}
        if leo:
            kwargs['reply_markup'] = reply_kb.save_current()

        await message.answer(
            "Теперь пришли фото или запиши видео 👍 (до 15 сек), его будут видеть другие пользователи",
            **kwargs
        )
        await state.set_state(LeomatchRegistration.SEND_PHOTO)
        logger.info(f"✅ Переход к отправке фото для user_id={message.from_user.id}")

    except Exception as e:
        logger.error(f"🔴 Ошибка при переходе к фото для user_id={message.from_user.id}: {str(e)}", exc_info=True)
        await message.answer("Произошла ошибка. Попробуйте позже.")


async def save_media(message: types.Message, state: FSMContext, url: str, type: str):
    """
    Media ma'lumotlarini saqlash
    """
    try:
        logger.info(f"📝 Сохранение медиа для user_id={message.from_user.id}")

        data = await state.get_data()
        age = data.get('age')
        full_name = data.get('full_name')
        about_me = data.get('about_me')
        city = data.get('city')

        logger.info(f"📄 Данные профиля: age={age}, name={full_name}, city={city}")

        await show_profile(message, message.from_user.id, full_name, age, city, about_me, url, type)
        await message.answer("Всё верно?", reply_markup=reply_kb.final_registration())
        await state.set_state(LeomatchRegistration.FINAL)

        logger.info(f"✅ Медиа успешно сохранено для user_id={message.from_user.id}")
        return True

    except Exception as e:
        logger.error(f"🔴 Ошибка при сохранении медиа для user_id={message.from_user.id}: {str(e)}", exc_info=True)
        raise e


last_message_time = defaultdict(float)
processed_messages = defaultdict(set)


@client_bot_router.message(F.text == "Давай, начнем!", LeomatchRegistration.BEGIN)
async def bot_start_lets_leo(message: Message, state: FSMContext):
    """
    Ro'yxatdan o'tishni boshlash
    """
    try:
        user_id = message.from_user.id
        message_id = message.message_id

        if message_store.is_processed(user_id, message_id):
            logger.info(f"🔄 Пропуск дубликата сообщения {message_id} от user_id={user_id}")
            return

        if not message_store.can_process(user_id):
            logger.info(f"⏳ Слишком частые запросы от user_id={user_id}")
            return

        current_state = await state.get_state()
        if current_state != LeomatchRegistration.BEGIN:
            logger.warning(f"❌ Неверное состояние: {current_state}")
            return

        state_data = await state.get_data()
        if state_data.get('registration_started'):
            logger.info(f"🔄 Регистрация уже начата для user_id={user_id}")
            return

        message_store.mark_processed(user_id, message_id)

        await state.update_data(registration_started=True)
        await state.clear()

        await message.answer(
            "Настоятельно рекомендуем указать username или в настройках разрешение на пересылку сообщения"
        )
        await message.answer(
            "Сколько тебе лет?",
            reply_markup=reply_kb.cancel()
        )
        await state.set_state(LeomatchRegistration.AGE)
        logger.info(f"✅ Переход к вводу возраста для user_id={user_id}")

    except Exception as e:
        logger.error(f"🔴 Ошибка при старте регистрации для user_id={user_id}: {str(e)}", exc_info=True)
        await message.answer("Произошла ошибка")


async def clear_processed_messages():
    while True:
        await asyncio.sleep(3600)  # har soatda
        processed_messages.clear()
        logger.info("🧹 Очистка списка обработанных сообщений")


@client_bot_router.message(LeomatchRegistration.AGE)
async def process_age(message: Message, state: FSMContext):
    """
    Yosh kiritishni qayta ishlash
    """
    try:
        user_id = message.from_user.id
        current_time = datetime.now().timestamp()

        if current_time - last_message_time[user_id] < MIN_MESSAGE_INTERVAL:
            logger.info(f"⏳ Игнорирование частого сообщения от user_id={user_id}")
            return

        last_message_time[user_id] = current_time
        logger.info(f"🔵 Обработка возраста от user_id={user_id}: {message.text}")

        current_state = await state.get_state()
        if current_state != LeomatchRegistration.AGE:
            logger.warning(f"❌ Неверное состояние: {current_state}")
            return

        state_data = await state.get_data()
        if state_data.get('age_set'):
            logger.info(f"🔄 Возраст уже установлен для user_id={user_id}")
            return

        try:
            age = int(message.text)
            if 18 <= age <= 100:
                logger.info(f"✅ Возраст {age} принят для user_id={user_id}")
                await state.update_data(age=age, age_set=True)  # age_set qo'shildi
                await message.answer(
                    "Теперь определимся с полом!",
                    reply_markup=reply_kb.chooice_sex()
                )
                await state.set_state(LeomatchRegistration.SEX)
            else:
                logger.warning(f"❌ Некорректный возраст {age} от user_id={user_id}")
                await message.answer("Пожалуйста, введите корректный возраст (18-100)")
        except ValueError:
            logger.warning(f"❌ Неверный формат возраста от user_id={user_id}")
            await message.answer("Пожалуйста, введите возраст цифрами")

    except Exception as e:
        logger.error(f"🔴 Ошибка при обработке возраста для user_id={user_id}: {str(e)}", exc_info=True)
        await message.answer("Произошла ошибка")


@client_bot_router.message(LeomatchRegistration.SEX)
async def process_gender(message: Message, state: FSMContext):
    """
    Jins tanlashni qayta ishlash
    """
    try:
        user_id = message.from_user.id
        current_time = datetime.now().timestamp()

        if current_time - last_message_time[user_id] < MIN_MESSAGE_INTERVAL:
            logger.info(f"⏳ Игнорирование частого сообщения от user_id={user_id}")
            return

        last_message_time[user_id] = current_time
        logger.info(f"🔵 Обработка выбора пола от user_id={user_id}: {message.text}")

        current_state = await state.get_state()
        if current_state != LeomatchRegistration.SEX:
            logger.warning(f"❌ Неверное состояние: {current_state}")
            return

        state_data = await state.get_data()
        if state_data.get('sex_set'):
            logger.info(f"🔄 Пол уже установлен для user_id={user_id}")
            return

        gender_mapping = {
            "Мужской": "MALE",
            "Женский": "FEMALE"
        }

        selected_gender = gender_mapping.get(message.text)

        if not selected_gender:
            logger.warning(f"❌ Неверный выбор пола: {message.text}")
            await message.answer(
                "Пожалуйста, укажите Ваш пол, используя кнопки ниже",
                reply_markup=reply_kb.chooice_sex()
            )
            return

        logger.info(f"✅ Пол {selected_gender} принят для user_id={user_id}")

        # Saqlash va keyingi bosqichga o'tish
        await state.update_data(sex=selected_gender, sex_set=True)  # sex_set qo'shildi
        await message.answer(
            "Кого Вы ищите?",
            reply_markup=reply_kb.which_search()
        )
        await state.set_state(LeomatchRegistration.WHICH_SEARCH)
        logger.info(f"✅ Переход к выбору поиска для user_id={user_id}")

    except Exception as e:
        logger.error(f"🔴 Ошибка при обработке пола для user_id={user_id}: {str(e)}", exc_info=True)
        await message.answer(
            "Произошла ошибка. Попробуйте еще раз.",
            reply_markup=reply_kb.chooice_sex()
        )


@client_bot_router.message(LeomatchRegistration.WHICH_SEARCH)
async def process_search_preference(message: Message, state: FSMContext):
    """
    Qidirish turini qayta ishlash
    """
    try:
        user_id = message.from_user.id
        logger.info(f"🔵 Обработка выбора поиска от user_id={user_id}: {message.text}")

        current_state = await state.get_state()
        if current_state != LeomatchRegistration.WHICH_SEARCH:
            logger.warning(f"❌ Неверное состояние: {current_state}")
            return

        search_mapping = {
            "Мужской": "MALE",
            "Женский": "FEMALE",
            "Все равно": "ANY"
        }

        search_type = search_mapping.get(message.text)

        if not search_type:
            logger.warning(f"❌ Неверный выбор поиска: {message.text}")
            await message.answer(
                "Пожалуйста, укажите кого Вы ищите, используя кнопки",
                reply_markup=reply_kb.which_search()
            )
            return

        logger.info(f"✅ Тип поиска {search_type} принят для user_id={user_id}")

        # Ma'lumotni saqlash va keyingi bosqichga o'tish
        await state.update_data(which_search=search_type)
        await message.answer("Из какого ты города?", reply_markup=reply_kb.remove())
        await state.set_state(LeomatchRegistration.CITY)
        logger.info(f"✅ Переход к вводу города для user_id={user_id}")

    except Exception as e:
        logger.error(f"🔴 Ошибка при обработке выбора поиска для user_id={user_id}: {str(e)}", exc_info=True)
        await message.answer(
            "Произошла ошибка. Попробуйте еще раз.",
            reply_markup=reply_kb.which_search()
        )


@client_bot_router.message(LeomatchRegistration.CITY)
async def process_city(message: Message, state: FSMContext):
    """
    Shahar kiritishni qayta ishlash
    """
    try:
        user_id = message.from_user.id
        logger.info(f"🔵 Обработка города от user_id={user_id}: {message.text}")

        current_state = await state.get_state()
        if current_state != LeomatchRegistration.CITY:
            logger.warning(f"❌ Неверное состояние: {current_state}")
            return

        city = message.text.strip()

        # Shahar nomini tekshirish
        if len(city) > 50:
            logger.warning(f"❌ Слишком длинное название города от user_id={user_id}")
            await message.answer("Пожалуйста, введите более короткое название города")
            return

        logger.info(f"✅ Город {city} принят для user_id={user_id}")

        await state.update_data(city=city)
        button = types.ReplyKeyboardMarkup(
            keyboard=[[types.KeyboardButton(text=message.from_user.full_name)]],
            resize_keyboard=True
        )
        await message.answer("Как мне тебя называть?", reply_markup=button)
        await state.set_state(LeomatchRegistration.FULL_NAME)
        logger.info(f"✅ Переход к вводу имени для user_id={user_id}")

    except Exception as e:
        logger.error(f"🔴 Ошибка при обработке города для user_id={user_id}: {str(e)}", exc_info=True)
        await message.answer("Произошла ошибка")


@client_bot_router.message(LeomatchRegistration.FULL_NAME)
async def process_name(message: Message, state: FSMContext):
    """
    Ism kiritishni qayta ishlash
    """
    try:
        user_id = message.from_user.id
        logger.info(f"🔵 Обработка имени от user_id={user_id}: {message.text}")

        name = message.text.strip()
        if len(name) > 15:
            logger.warning(f"❌ Слишком длинное имя от user_id={user_id}")
            await message.answer("Пожалуйста, введите имя не более 15 символов")
            return

        logger.info(f"✅ Имя {name} принято для user_id={user_id}")

        await state.update_data(full_name=name)
        leo = await get_leo(message.from_user.id)

        kwargs = {}
        if leo:
            kwargs['reply_markup'] = reply_kb.save_current()

        await message.answer(
            "Расскажи о себе и кого хочешь найти, чем предлагаешь заняться. Это поможет лучше подобрать тебе компанию.",
            **kwargs
        )
        await state.set_state(LeomatchRegistration.ABOUT_ME)
        logger.info(f"✅ Переход к описанию для user_id={user_id}")

    except Exception as e:
        logger.error(f"🔴 Ошибка при обработке имени для user_id={user_id}: {str(e)}", exc_info=True)
        await message.answer("Произошла ошибка")


@client_bot_router.message(LeomatchRegistration.ABOUT_ME)
async def process_about(message: Message, state: FSMContext):
    """
    O'zingiz haqingizda ma'lumot kiritishni qayta ishlash
    """
    try:
        user_id = message.from_user.id
        logger.info(f"🔵 Обработка описания от user_id={user_id}")

        if len(message.text) > 300:
            logger.warning(f"❌ Слишком длинное описание от user_id={user_id}")
            await message.answer("Пожалуйста, введите описание не более 300 символов")
            return

        await state.update_data(about_me=message.text)
        await now_send_photo(message, state)
        logger.info(f"✅ Переход к фото для user_id={user_id}")

    except Exception as e:
        logger.error(f"🔴 Ошибка при обработке описания для user_id={user_id}: {str(e)}", exc_info=True)
        await message.answer("Произошла ошибка")


@client_bot_router.message(F.text == "Оставить текущее", LeomatchRegistration.ABOUT_ME)
async def keep_current_about(message: Message, state: FSMContext):
    """
    Joriy malumotni saqlash
    """
    try:
        user_id = message.from_user.id
        logger.info(f"🔵 Сохранение текущего описания для user_id={user_id}")

        leo = await get_leo(message.from_user.id)
        if not leo:
            logger.warning(f"❌ Нет сохраненного описания для user_id={user_id}")
            await message.answer("К сожалению, прошлый текст не сохранен")
            return

        await state.update_data(about_me=leo.about_me)
        await now_send_photo(message, state)
        logger.info(f"✅ Текущее описание сохранено для user_id={user_id}")

    except Exception as e:
        logger.error(f"🔴 Ошибка при сохранении описания для user_id={user_id}: {str(e)}", exc_info=True)
        await message.answer("Произошла ошибка")


@client_bot_router.message(F.text == "Оставить текущее", LeomatchRegistration.SEND_PHOTO)
async def keep_current_photo(message: Message, state: FSMContext):
    """
    Joriy rasmni saqlash
    """
    try:
        user_id = message.from_user.id
        logger.info(f"🔵 Сохранение текущего фото для user_id={user_id}")

        leo = await get_leo(message.from_user.id)
        if not leo:
            logger.warning(f"❌ Нет сохраненного фото для user_id={user_id}")
            await message.answer("К сожалению, прошлое медиа не сохранено")
            return

        await save_media(message, state, leo.photo, leo.media_type)
        logger.info(f"✅ Текущее фото сохранено для user_id={user_id}")

    except Exception as e:
        logger.error(f"🔴 Ошибка при сохранении фото для user_id={user_id}: {str(e)}", exc_info=True)
        await message.answer("Произошла ошибка")


@client_bot_router.message(LeomatchRegistration.SEND_PHOTO)
async def process_photo(message: Message, state: FSMContext, bot: Bot):
    """
    Rasmni qayta ishlash
    """
    try:
        user_id = message.from_user.id
        logger.info(f"🔵 Обработка медиа от user_id={user_id}")

        if not message.photo and not message.video:
            logger.warning(f"❌ Нет медиафайла от user_id={user_id}")
            await message.answer("Пожалуйста, пришли фото или видео")
            return

        url = ""
        type = ""

        if message.photo:
            url = message.photo[-1].file_id
            type = "PHOTO"
            format = "jpg"
            logger.info(f"📸 Получено фото от user_id={user_id}")
        elif message.video:
            if message.video.duration > 15:
                logger.warning(f"❌ Слишком длинное видео от user_id={user_id}")
                await message.answer("Пожалуйста, пришли видео не более 15 секунд")
                return
            url = message.video.file_id
            type = "VIDEO"
            format = "mp4"
            logger.info(f"🎥 Получено видео от user_id={user_id}")

        # Create directory if doesn't exist
        data_dir = Path("modul/clientbot/data")
        data_dir.mkdir(parents=True, exist_ok=True)

        file_path = data_dir / f"leo{message.from_user.id}.{format}"

        try:
            async with Bot(token=bot.token, session=bot_session).context() as bot_:
                await bot_.download(url, destination=str(file_path))
                logger.info(f"✅ Файл сохранен: {file_path}")
        except Exception as download_error:
            logger.error(f"❌ Ошибка при сохранении файла: {str(download_error)}")
            await message.answer("Ошибка при загрузке файла. Пожалуйста, попробуйте снова.")
            return

        await state.update_data(photo=url, media_type=type)
        data = await state.get_data()

        try:
            await show_profile(
                message=message,
                uid=message.from_user.id,
                full_name=data.get('full_name'),
                age=data.get('age'),
                city=data.get('city'),
                about_me=data.get('about_me'),
                url=str(file_path),
                type=type
            )

            await message.answer("Всё верно?", reply_markup=reply_kb.final_registration())
            await state.set_state(LeomatchRegistration.FINAL)
            logger.info(f"✅ Профиль показан user_id={user_id}")

        except Exception as profile_error:
            logger.error(f"❌ Ошибка при показе профиля: {str(profile_error)}")
            await message.answer("Всё верно?", reply_markup=reply_kb.final_registration())
            await state.set_state(LeomatchRegistration.FINAL)

    except Exception as e:
        logger.error(f"🔴 Ошибка при обработке медиа для user_id={user_id}: {str(e)}", exc_info=True)
        await message.answer("Произошла ошибка при сохранении медиафайла. Пожалуйста, попробуйте снова.")


@client_bot_router.message(F.text == "Да", LeomatchRegistration.FINAL)
async def finalize_registration(message: Message, state: FSMContext, bot: Bot):
    """
    Ro'yxatdan o'tishni yakunlash
    """
    try:
        user_id = message.from_user.id
        logger.info(f"🔵 Финализация регистрации для user_id={user_id}")

        data = await state.get_data()

        # Collect all required data
        registration_data = {
            'photo': data['photo'],
            'media_type': data['media_type'],
            'sex': data['sex'],
            'age': data['age'],
            'full_name': data['full_name'],
            'about_me': data['about_me'],
            'city': data['city'],
            'which_search': data['which_search']
        }

        leo = await get_leo(user_id)
        if not leo:
            bot = await get_current_bot(bot)
            await add_leo(
                user_id,
                **registration_data,
                bot_username=bot.username
            )
            logger.info(f"✅ Создан новый профиль для user_id={user_id}")
        else:
            await update_leo(
                user_id,
                **registration_data
            )
            logger.info(f"✅ Обновлен профиль для user_id={user_id}")

        await state.clear()
        await manage(message, state)

    except Exception as e:
        logger.error(f"🔴 Ошибка при финализации регистрации для user_id={user_id}: {str(e)}", exc_info=True)
        await message.answer("Произошла ошибка при сохранении профиля")


@client_bot_router.message(F.text == "Изменить анкету", LeomatchRegistration.FINAL)
async def edit_profile(message: Message, state: FSMContext):
    """
    Profilni tahrirlash
    """
    try:
        user_id = message.from_user.id
        logger.info(f"🔄 Начало редактирования профиля для user_id={user_id}")

        await begin_registration(message, state)
        logger.info(f"✅ Переход к редактированию для user_id={user_id}")

    except Exception as e:
        logger.error(f"🔴 Ошибка при редактировании профиля для user_id={user_id}: {str(e)}", exc_info=True)
        await message.answer("Произошла ошибка")
import os

import aiohttp
from aiogram import types, Bot, F
from aiogram.exceptions import TelegramNetworkError
from aiogram.types import Message

from modul.clientbot.handlers.leomatch.keyboards import reply_kb
from modul.clientbot.handlers.leomatch.data.state import LeomatchRegistration
from modul.clientbot.handlers.leomatch.handlers.shorts import manage, begin_registration, set_which_search, set_sex
from modul.clientbot.handlers.leomatch.shortcuts import add_leo, get_leo, show_profile, update_leo
from modul.clientbot.utils.functs import return_main
from modul.clientbot.shortcuts import get_current_bot
from modul.loader import client_bot_router, bot_session
from aiogram.fsm.context import FSMContext


async def now_send_photo(message: types.Message, state: FSMContext):
    leo = await get_leo(message.from_user.id)
    kwargs = {}
    print(kwargs)
    if leo:
        kwargs['reply_markup'] = reply_kb.save_current()
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


@client_bot_router.message(F.text == "Давай, начнем!", LeomatchRegistration.BEGIN)
async def bot_start_lets_leo(message: types.Message, state: FSMContext):
    if message.from_user.username == None:
        await message.answer(
            (
                "Настоятельно рекомендуем указать username или в настройках разрешение на пересылку сообщения иначе Вам не смогут написать те, кого вы лайкните"))

        await begin_registration(message, state)


    else:
        # await message.answer(
        #     (
        #         "Настоятельно рекомендуем указать username или в настройках разрешение на пересылку сообщения иначе Вам не смогут написать те, кого вы лайкните"))
        await begin_registration(message, state)


@client_bot_router.message(LeomatchRegistration.AGE)
async def bot_start(message: Message, state: FSMContext, bot: Bot):
    try:
        age = int(message.text)
        await state.set_data({"age": age})
        await message.answer(("Теперь определимся с полом!"), reply_markup=reply_kb.chooice_sex())
        await state.set_state(LeomatchRegistration.SEX)
    except:
        if message.text == "Отменить":
            await message.answer(("Отменена регистрация!"), )
            await return_main(message, state, bot)
            return
        await message.answer(("Пожалуйста, введите возрост цифрами"), )



@client_bot_router.message(F.text == ("Я парень"), LeomatchRegistration.SEX)
async def bot_start(message: types.Message, state: FSMContext):
    await set_sex("MALE", message, state)


@client_bot_router.message(F.text == ("Я девушка"), LeomatchRegistration.SEX)
async def bot_start(message: types.Message, state: FSMContext):
    await set_sex("FEMALE", message, state)


@client_bot_router.message(LeomatchRegistration.SEX)
async def bot_start(message: types.Message):
    await message.answer(("Пожалуйста, укажите Ваш пол, нажав на кнопку"), )


@client_bot_router.message(F.text == ("Парня"), LeomatchRegistration.WHICH_SEARCH)
async def bot_start(message: types.Message, state: FSMContext):
    await set_which_search("MALE", message, state)


@client_bot_router.message(F.text == ("Девушку"), LeomatchRegistration.WHICH_SEARCH)
async def bot_start(message: types.Message, state: FSMContext):
    await set_which_search("FEMALE", message, state)


@client_bot_router.message(F.text == ("Мне всё равно"), LeomatchRegistration.WHICH_SEARCH)
async def bot_start(message: types.Message, state: FSMContext):
    await set_which_search("ANY", message, state)


@client_bot_router.message(LeomatchRegistration.WHICH_SEARCH)
async def bot_start(message: types.Message):
    await message.answer(("Пожалуйста, укажите кого Вы ищите, нажав на кнопку"), )


@client_bot_router.message(LeomatchRegistration.CITY)
async def bot_start(message: types.Message, state: FSMContext):
    city = message.text
    await state.update_data(city=city)
    button = types.ReplyKeyboardMarkup(keyboard=[[types.KeyboardButton(text=message.from_user.full_name)]],
                                       resize_keyboard=True, one_time_keyboard=True)
    await message.answer(("Как мне тебя называть?"), reply_markup=button)
    await state.set_state(LeomatchRegistration.FULL_NAME)


@client_bot_router.message(LeomatchRegistration.FULL_NAME)
async def bot_start(message: types.Message, state: FSMContext):
    name = message.text.strip()
    if len(name) > 15:
        await message.answer(("Пожалуйста, введите имя не более 15 символов"))
        return
    await state.update_data(full_name=name)
    leo = await get_leo(message.from_user.id)
    kwargs = {}
    if leo:
        kwargs['reply_markup'] = reply_kb.save_current()
    await message.answer(
        ("Расскажи о себе и кого хочешь найти, чем предлагаешь заняться. Это поможет лучше подобрать тебе компанию."),
        **kwargs)
    await state.set_state(LeomatchRegistration.ABOUT_ME)


@client_bot_router.message(F.text == ("Оставить текущее"), LeomatchRegistration.ABOUT_ME)
async def bot_start(message: types.Message, state: FSMContext):
    leo = await get_leo(message.from_user.id)
    if not leo:
        await message.answer(("К сожалению, прошлый текст не сохранен"))
        return
    await state.update_data(about_me=leo.about_me)
    await now_send_photo(message, state)


@client_bot_router.message(LeomatchRegistration.ABOUT_ME)
async def bot_start(message: types.Message, state: FSMContext):
    if len(message.text) > 300:
        await message.answer(("Пожалуйста, введите описание не более 300 символов"))
        return
    await state.update_data(about_me=message.text)
    await now_send_photo(message, state)


@client_bot_router.message(F.text == ("Оставить текущее"), LeomatchRegistration.SEND_PHOTO)
async def bot_start(message: types.Message, state: FSMContext):
    leo = await get_leo(message.from_user.id)
    if not leo:
        await message.answer(("К сожалению, прошлое медия не сохранено"))
        return
    await save_media(message, state, leo.photo, leo.media_type)


@client_bot_router.message(LeomatchRegistration.SEND_PHOTO)
async def bot_start(message: types.Message, state: FSMContext, bot: Bot):
    if not message.photo and not message.video and not message.video_note:
        await message.answer("Пожалуйста, пришли фото, видео или видеосообщение")
        return

    url = ""
    type = ""
    if message.photo:
        url = message.photo[-1].file_id
        type = "PHOTO"
    elif message.video:
        if message.video.duration > 15:
            await message.answer("Пожалуйста, пришли видео не более 15 секунд")
            return
        url = message.video.file_id
        type = "VIDEO"
    elif message.video_note:
        if message.video_note.duration > 15:
            await message.answer("Пожалуйста, пришли видеосообщение не более 15 секунд")
            return
        url = message.video_note.file_id
        type = "VIDEO_NOTE"

    print(f"Received media - type: {type}, file_id: {url}")

    base_dir = "modul/clientbot/data"
    os.makedirs(base_dir, exist_ok=True)

    format = "jpg" if type == "PHOTO" else "mp4"
    file_path = f"{base_dir}/leo{message.from_user.id}.{format}"

    try:
        file = await bot.get_file(url)
        await bot.download_file(file.file_path, file_path)

        print(f"File saved to: {file_path}")

        await state.update_data(photo=url, media_type=type)

        updated_data = await state.get_data()
        print(f"State after saving photo: {updated_data}")

        await save_media(message, state, file_path, type)

    except Exception as e:
        print(f"Error saving media: {e}")
        await message.answer("Произошла ошибка. Пожалуйста, попробуйте еще раз.")


@client_bot_router.message(F.text == ("Да"), LeomatchRegistration.FINAL)
async def bot_start(message: types.Message, state: FSMContext, bot: Bot):
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
        await add_leo(message.from_user.id, photo, media_type, sex, age, full_name, about_me, city, which_search, bot_username)
    else:
        await update_leo(uid=message.from_user.id, photo=photo, media_type=media_type, sex=sex, age=age,
                         full_name=full_name, about_me=about_me, city=city, which_search=which_search)

    await state.clear()
    await manage(message, state)

@client_bot_router.message(F.text == ("Изменить анкету"), LeomatchRegistration.FINAL)
async def bot_start(message: types.Message, state: FSMContext):
    await begin_registration(message, state)


@client_bot_router.message(LeomatchRegistration.ABOUT_ME)
async def bot_start(message: types.Message, state: FSMContext):
    await message.answer(("Пожалуйста, нажмите на кнопку"), reply_markup=reply_kb.final_registration())

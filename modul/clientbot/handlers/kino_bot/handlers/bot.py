import asyncio
from contextlib import suppress

from aiogram import Bot, F, html
from aiogram.exceptions import TelegramForbiddenError
from aiogram.filters import Command, CommandStart, CommandObject, Filter, BaseFilter
from aiogram.fsm.context import FSMContext
from aiogram.filters.state import State, StatesGroup, StateFilter

from aiogram.types import CallbackQuery, Message, InlineKeyboardButton, InlineKeyboardMarkup, InlineQueryResultArticle, \
    InputTextMessageContent, InlineQuery, BotCommand, ReplyKeyboardRemove, URLInputFile
from aiogram.utils.deep_linking import create_start_link
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from django.db import transaction
from django.utils import timezone


from modul import models
from modul.clientbot import shortcuts
from modul.clientbot.data.states import Download
from modul.clientbot.handlers.chat_gpt_bot.shortcuts import get_info_db
from modul.clientbot.handlers.kino_bot.shortcuts import *
from modul.clientbot.handlers.kino_bot.keyboards.kb import *
from modul.clientbot.handlers.kino_bot.api import *
from modul.clientbot.handlers.leomatch.data.state import LeomatchRegistration
from modul.clientbot.handlers.leomatch.handlers.registration import bot_start_lets_leo
from modul.clientbot.handlers.leomatch.handlers.start import bot_start, bot_start_cancel
from modul.clientbot.handlers.refs.handlers.bot import start_ref
from modul.clientbot.keyboards import reply_kb
from modul.clientbot.shortcuts import get_all_users
from modul.loader import client_bot_router


class SearchFilmForm(StatesGroup):
    query = State()


class AddChannelSponsorForm(StatesGroup):
    channel = State()


class SendMessagesForm(StatesGroup):
    message = State()


async def check_subs(user_id: int, bot: Bot) -> bool:
    channels = await get_all_channels_sponsors()

    if not channels:
        return True

    check_results = []

    for channel in channels:

        try:

            m = await bot.get_chat_member(chat_id=channel, user_id=user_id)

            if m.status != 'left':
                check_results.append(True)
            else:
                check_results.append(False)

        except Exception as e:

            print(e)
            check_results.append(False)

    print(check_results)

    return all(check_results)


async def get_subs_kb(bot: Bot) -> types.InlineKeyboardMarkup:
    channels = await get_all_channels_sponsors()

    kb = InlineKeyboardBuilder()

    for index, channel in enumerate(channels, 1):
        try:
            link = await bot.create_chat_invite_link(channel)
            kb.button(text=f'Ссылка {index}', url=link.invite_link)
        except Exception as e:
            print(e)

    me = await bot.get_me()
    kb.button(
        text='✅ Проверить подписку',
        url=f'https://t.me/{me.username}?start'
    )

    return kb.as_markup()


async def get_films_kb(data: dict) -> types.InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()

    for film in data['results']:
        kb.button(
            text=f'{film["name"]} - {film["year"]}',
            callback_data=f'watch_film|{film["id"]}'
        )

    return kb.adjust(1).as_markup()


async def get_remove_channel_sponsor_kb(channels: list, bot: Bot) -> types.InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()

    for channel in channels:
        channel_data = await bot.get_chat(channel)
        kb.button(
            text=channel_data.full_name,
            callback_data=f'remove_channel|{channel}'

        )

    kb.button(text='Отменить', callback_data='cancel')

    return kb.as_markup()


async def send_message(message: types.Message, users: list):
    good = []
    bad = []

    for user in users:

        try:

            await message.copy_to(user, reply_markup=message.reply_markup)
            good.append(user)

            await asyncio.sleep(0.1)

        except:

            bad.append(user)

    await message.answer(f'Рассылка завершена!\n\nУспешно: {len(good)}\nНеуспешно: {len(bad)}')


class AdminFilter(BaseFilter):
    async def __call__(self, message: Message, bot: Bot) -> bool:
        bot_db = await shortcuts.get_bot(bot)
        admin_id = bot_db.owner.uid
        return message.from_user.id == admin_id


@client_bot_router.message(Command('admin'), AdminFilter())
async def admin(message: types.Message):
    await message.answer('Админ панель', reply_markup=admin_kb)


@client_bot_router.callback_query(F.data == 'admin_send_message', AdminFilter(), StateFilter('*'))
async def admin_send_message(call: CallbackQuery, state: FSMContext):
    await state.set_state(SendMessagesForm.message)
    await call.message.edit_text('Отправьте сообщение для рассылки', reply_markup=cancel_kb)


@client_bot_router.message(SendMessagesForm.message, F.content_type.in_({'any'}))
async def admin_send_message_msg(message: Message, state: FSMContext):
    await state.clear()

    users = await get_all_users()

    await asyncio.create_task(send_message(message, users))

    await message.answer('Рассылка началась!\n\nПо ее окончанию вы получите отчет')


@client_bot_router.callback_query(F.data == 'admin_get_stats', AdminFilter(), StateFilter('*'))
async def admin_get_stats(call: CallbackQuery):
    users = await get_all_users()
    await call.message.edit_text(f'<b>Количество пользователей в боте:</b> {len(users)}', reply_markup=admin_kb)


@client_bot_router.callback_query(F.data == 'cancel', StateFilter('*'))
async def cancel(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_text('Отменено')


@client_bot_router.callback_query(F.data == 'admin_delete_channel', AdminFilter(), StateFilter('*'))
async def admin_delete_channel(call: CallbackQuery):
    channels = get_all_channels_sponsors()
    kb = await get_remove_channel_sponsor_kb(channels)
    await call.message.edit_text('Выберите канал для удаления', reply_markup=kb)


@client_bot_router.callback_query(F.data.contains('remove_channel'),AdminFilter(), StateFilter('*'))
async def remove_channel(call: CallbackQuery):
    channel_id = int(call.data.split('|')[-1])
    remove_channel_sponsor(channel_id)
    await call.message.edit_text('Канал был удален!', reply_markup=admin_kb)


@client_bot_router.callback_query(F.data == 'admin_add_channel', AdminFilter(), StateFilter('*'))
async def admin_add_channel(call: CallbackQuery, state: FSMContext):
    await state.set_state(AddChannelSponsorForm.channel)
    await call.message.edit_text('Отправьте id канала\n\nУбедитесь в том, что бот является администратором в канале',
                                 reply_markup=cancel_kb)

@client_bot_router.message(AddChannelSponsorForm.channel)
async def admin_add_channel_msg(message: Message, state: FSMContext, bot: Bot):
    channel_id = int(message.text)
    try:
        await bot.get_chat(channel_id)
        create_channel_sponsor(channel_id)
        await state.clear()
        await message.answer('Канал успешно добавлен!')
    except Exception as e:
        print(e)
        await message.answer(
            'Ошибка при добавлении канала!\n\nСкорее всего, дело в том, что бот не является администратором в канале',
            reply_markup=cancel_kb)


async def start_kino_bot(message: Message, state: FSMContext, bot: Bot):
    sub_status = await check_subs(message.from_user.id, bot)
    if not sub_status:
        kb = await get_subs_kb()
        await message.answer('<b>Чтобы воспользоваться ботом, необходимо подписаться на каналы</b>', reply_markup=kb)
        return
    await state.set_state(SearchFilmForm.query)
    await message.answer(
        '<b>Отправьте название фильма / сериала / аниме</b>\n\nНе указывайте года, озвучки и т.д.\n\nПравильный пример: Ведьмак\nНеправильный пример: Ведьмак 2022',
        parse_mode="HTML", reply_markup=ReplyKeyboardRemove())


@sync_to_async
def get_user(uid: int, username: str, first_name: str = None, last_name: str = None):
    user = models.UserTG.objects.get_or_create(uid=uid, username=username, first_name=first_name, last_name=last_name)
    return user


@sync_to_async
@transaction.atomic
def save_user(u, bot: Bot, link=None, inviter=None):
    bot = models.Bot.objects.select_related("owner").filter(token=bot.token).first()
    user = models.UserTG.objects.filter(uid=u.id).first()
    current_ai_limit = 12
    if not user:
        user = models.UserTG.objects.create(
            uid=u.id,
            username=u.username,
            first_name=u.first_name,
            last_name=u.last_name,
            user_link=link
        )
    else:
        current_ai_limit = 0

    client_user = models.ClientBotUser.objects.filter(uid=u.id, bot=bot).first()
    if client_user:
        return client_user

    client_user = models.ClientBotUser.objects.create(
        uid=u.id,
        user=user,
        bot=bot,
        inviter=inviter,
        current_ai_limit=current_ai_limit
    )
    return client_user


class NonChatGptFilter(Filter):
    async def __call__(self, message: Message, bot: Bot) -> bool:
        bot_db = await shortcuts.get_bot(bot)
        return not shortcuts.have_one_module(bot_db, "chatgpt")


async def start(message: Message, state: FSMContext, bot: Bot):
    bot_db = await shortcuts.get_bot(bot)
    uid = message.from_user.id
    text = "Добро пожаловать, {hello}".format(hello=html.quote(message.from_user.full_name))
    kwargs = {}
    if shortcuts.have_one_module(bot_db, "download"):
        builder = ReplyKeyboardBuilder()
        builder.button(text='💸Заработать')
        text = ("🤖 Привет, {full_name}! Я бот-загрузчик.\r\n\r\n"
                "Я могу скачать фото/видео/аудио/файлы/архивы с *Youtube, Instagram, TikTok, Facebook, SoundCloud, Vimeo, Вконтакте, Twitter и 1000+ аудио/видео/файловых хостингов*. Просто пришли мне URL на публикацию с медиа или прямую ссылку на файл.").format(
            full_name=message.from_user.full_name)
        await state.set_state(Download.download)
        kwargs['parse_mode'] = "Markdown"
        kwargs['reply_markup'] = builder.as_markup(resize_keyboard=True)
    elif shortcuts.have_one_module(bot_db, "refs"):
        await start_ref(message)
    elif shortcuts.have_one_module(bot_db, "kino"):
        await start_kino_bot(message, state)
        kwargs['parse_mode'] = "HTML"
    elif shortcuts.have_one_module(bot_db, "chatgpt"):
        builder = InlineKeyboardBuilder()
        builder.button(text='☁ Чат с GPT-4', callback_data='chat_4')
        builder.button(text='☁ Чат с GPT-3.5', callback_data='chat_3')
        builder.button(text='🆘 Помощь', callback_data='helper')
        builder.button(text='⚙️ Настройки', callback_data='settings')
        builder.button(text='💸Заработать', callback_data='ref')
        builder.adjust(2, 1, 1, 1, 1, 1, 2)
        result = await get_info_db(uid)
        print(result)
        text = f'Привет {message.from_user.username}\nВаш баланс - {result[0][2]}'
        kwargs['reply_markup'] = builder.as_markup()
    else:
        kwargs['reply_markup'] = await reply_kb.main_menu(uid, bot)
    await message.answer(text, **kwargs)

# print(client_bot_router.message.handlers)
# client_bot_router.message.register(bot_start, F.text == "🫰 Знакомства")

@client_bot_router.message(CommandStart(), NonChatGptFilter())
async def start_on(message: Message, state: FSMContext, bot: Bot, command: CommandObject):
    bot_db = await shortcuts.get_bot(bot)

    info = await get_user(uid=message.from_user.id, username=message.from_user.username,
                          first_name=message.from_user.first_name if message.from_user.first_name else None,
                          last_name=message.from_user.last_name if message.from_user.last_name else None)
    await state.clear()
    commands = await bot.get_my_commands()
    bot_commands = [
        BotCommand(command="/start", description="Меню"),
    ]
    print('command start')
    if commands != bot_commands:
        await bot.set_my_commands(bot_commands)
    referral = command.args
    uid = message.from_user.id
    user = await shortcuts.get_user(uid, bot)

    if not user:
        if referral and referral.isdigit():
            inviter = await shortcuts.get_user(int(referral))
            if inviter:
                await shortcuts.increase_referral(inviter)
                with suppress(TelegramForbiddenError):
                    user_link = html.link('реферал', f'tg://user?id={uid}')
                    await bot.send_message(
                        chat_id=referral,
                        text=('new_referral').format(
                            user_link=user_link,
                        )
                    )
        else:
            inviter = None
        new_link = await create_start_link(message.bot, str(message.from_user.id), encode=True)
        link_for_db = new_link[new_link.index("=") + 1:]
        await save_user(u=message.from_user, inviter=inviter, bot=bot, link=link_for_db)
    await start(message, state, bot)
    return


@client_bot_router.callback_query(F.data == 'start_search')
async def start_search(call: types.CallbackQuery, state: FSMContext):
    await state.set_state(SearchFilmForm.query)
    await call.message.answer(
        '<b>Отправьте название фильма / сериала / аниме</b>\n\nНе указывайте года, озвучки и т.д.\n\nПравильный пример: Ведьмак\nНеправильный пример: Ведьмак 2022')


@client_bot_router.callback_query(F.data.contains('watch_film'), StateFilter('*'))
async def watch_film(call: CallbackQuery, state: FSMContext):
    film_id = int(call.data.split('|')[-1])

    film_data = await get_film_for_view(film_id)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='Смотреть', url=film_data['view_link'])],
        [InlineKeyboardButton(text='🔥 Лучшие фильмы 🔥', url='https://t.me/KinoPlay_HD')],
        [InlineKeyboardButton(text='🔍 Поиск фильмов 🔍', url=f'https://t.me/{BOT_UNAME}')]
    ])

    caption = f'<b>{film_data["name"]} {film_data["year"]}</b>\n\n{film_data["description"]}\n\n{film_data["country"]}\n{film_data["genres"]}'

    try:
        await call.message.answer_photo(photo=film_data['poster'],
                                        caption=caption,
                                        reply_markup=kb, parse_mode="HTML")
    except Exception:
        await call.message.answer(caption, reply_markup=kb)


@client_bot_router.message(F.text == '🔍 Поиск')
async def reply_start_search(message: Message, state: FSMContext, bot: Bot):
    sub_status = await check_subs(message.from_user.id, bot)

    if not sub_status:
        kb = await get_subs_kb()
        await message.answer('<b>Чтобы воспользоваться ботом, необходимо подписаться на каналы</b>', reply_markup=kb)
        return

    await state.set_state(SearchFilmForm.query)
    await message.answer(
        '<b>Отправьте название фильма / сериала / аниме</b>\n\nНе указывайте года, озвучки и т.д.\n\nПравильный пример: Ведьмак\nНеправильный пример: Ведьмак 2022')


@client_bot_router.message(SearchFilmForm.query)
async def get_results(message: types.Message, state: FSMContext, bot: Bot):
    await state.clear()

    sub_status = await check_subs(message.from_user.id, bot)

    if not sub_status:
        kb = await get_subs_kb()
        await message.answer('<b>Чтобы воспользоваться ботом, необходимо подписаться на каналы</b>', reply_markup=kb)
        return

    results = await film_search(message.text)

    if results['results_count'] == 0:
        await message.answer(
            '<b>По вашему запросу не найдено результатов!</b>\n\nПроверьте корректность введенных данных')
        return

    kb = await get_films_kb(results)

    await message.answer(f'<b>Результаты поиска по ключевому слову</b>: {message.text}', reply_markup=kb)


class KinoBotFilter(Filter):
    async def __call__(self, message: types.Message, bot: Bot) -> bool:
        bot_db = await shortcuts.get_bot(bot)
        return shortcuts.have_one_module(bot_db, "kino")


@client_bot_router.message(KinoBotFilter())
async def simple_text_film_handler(message: Message, bot: Bot):
    sub_status = await check_subs(message.from_user.id, bot)

    if not sub_status:
        kb = await get_subs_kb()
        await message.answer('<b>Чтобы воспользоваться ботом, необходимо подписаться на каналы</b>',
                             reply_markup=kb)
        return

    results = await film_search(message.text)

    if results['results_count'] == 0:
        await message.answer(
            '<b>По вашему запросу не найдено результатов!</b>\n\nПроверьте корректность введенных данных',
            parse_mode="HTML")
        return

    kb = await get_films_kb(results)

    await message.answer(f'<b>Результаты поиска по ключевому слову</b>: {message.text}', reply_markup=kb,
                         parse_mode="HTML")
    return


@client_bot_router.inline_query(F.query)
async def inline_film_requests(query: InlineQuery):
    results = await film_search(query.query)

    inline_answer = []

    for film in results['results']:
        film_data = await get_film_for_view(film['id'])

        text = f'<a href="{film_data["poster"]}">🔥🎥</a> {film_data["name"]} ({film_data["year"]})\n\n{film_data["description"]}\n\n{film_data["country"]}\n{film_data["genres"]}'

        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text='Смотреть', url=film_data['view_link'])],
            [InlineKeyboardButton(text='🔥 Лучшие фильмы 🔥', url='https://t.me/KinoPlay_HD')],
            [InlineKeyboardButton(text='🔍 Поиск фильмов 🔍', url=f'https://t.me/{BOT_UNAME}')]
        ])

        answer = InlineQueryResultArticle(
            id=str(film["id"]),
            title=f'{film_data["name"]} {film_data["year"]}',
            input_message_content=InputTextMessageContent(message_text=text, parse_mode='html'),
            reply_markup=kb,
            thumb_url=film_data["poster"]
        )

        inline_answer.append(answer)

    await query.answer(inline_answer, cache_time=240, is_personal=True)


client_bot_router.message.register(bot_start, F.text == "🫰 Знакомства")
client_bot_router.message.register(bot_start_cancel, F.text == ("Я не хочу никого искать"), LeomatchRegistration.BEGIN)
client_bot_router.message.register(bot_start_lets_leo, F.text == "Давай, начнем!", LeomatchRegistration.BEGIN)


@sync_to_async
def create_task_model(client, url):
    info = models.TaskModel.objects.create(client=client, task_type=models.TaskTypeEnum.DOWNLOAD_MEDIA,
                                           data={'url': url})
    return True


@sync_to_async
def get_user_tg(uid):
    info = models.UserTG.objects.get(uid=uid)
    return info


@sync_to_async
def update_download_analytics(bot_username, domain):
    from modul.models import DownloadAnalyticsModel  # Импорт здесь во избежание циклических импортов
    analytics, created = DownloadAnalyticsModel.objects.get_or_create(
        bot_username=bot_username,
        domain=domain,
        date__date=timezone.now().date()
    )
    DownloadAnalyticsModel.objects.filter(id=analytics.id).update(count=F('count') + 1)


from aiogram.types import URLInputFile, FSInputFile
import yt_dlp
import os

import yt_dlp
import logging

logger = logging.getLogger(__name__)


async def youtube_download_handler(message: Message, bot: Bot):
    try:
        await message.answer('📥 Скачиваю видео...')

        if not message.text:
            await message.answer('Пришлите ссылку на видео')
            return

        if 'streaming' in message.text:
            await message.answer('❌ Я не могу скачать стримы')
            return

        me = await bot.get_me()

        if 'instagram' in message.text:
            new_url = message.text.replace('www.', 'dd')
            await message.answer(f'{new_url}\r\nВидео скачано через бота @{me.username}')
            return

        url = message.text
        await bot.send_chat_action(message.chat.id, "upload_video")

        ydl_opts = {
            'format': 'best[height<=720][ext=mp4]/best[ext=mp4]/best',  # Limit to 720p MP4
            'noplaylist': True,
            'quiet': True,
            'no_warnings': True,
        }

        try:
            async with bot.send_chat_action(message.chat.id, "upload_video"):
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    try:
                        # Get video info
                        info = ydl.extract_info(url, download=False)

                        if 'url' in info:
                            try:
                                await bot.send_video(
                                    chat_id=message.chat.id,
                                    video=info['url'],
                                    caption=f"📹 {info.get('title', 'Video')}\n\nСкачано через @{me.username}",
                                    supports_streaming=True
                                )

                                # Update analytics
                                try:
                                    await shortcuts.add_to_analitic_data(me.username, url)
                                except Exception as analytics_error:
                                    logger.error(f"Analytics error: {analytics_error}")

                            except Exception as send_error:
                                logger.error(f"Error sending video: {send_error}")
                                await message.answer("❌ Не удалось отправить видео. Возможно оно слишком большое.")
                        else:
                            await message.answer("❌ Не удалось получить ссылку на видео")

                    except Exception as extract_error:
                        logger.error(f"Error extracting info: {extract_error}")
                        await message.answer(
                            "❌ Не удалось получить информацию о видео. Возможно видео недоступно или защищено.")

        except Exception as ydl_error:
            logger.error(f"yt-dlp error: {ydl_error}")
            await message.answer("❌ Ошибка при скачивании. Попробуйте другое видео или позже.")

    except Exception as e:
        logger.error(f"General error: {e}")
        await message.answer("❌ Произошла ошибка. Попробуйте позже.")


client_bot_router.message.register(youtube_download_handler, Download.download)


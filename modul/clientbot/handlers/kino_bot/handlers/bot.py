import asyncio
import time
from contextlib import suppress

from aiogram import Bot, F, html
from aiogram.exceptions import TelegramForbiddenError
from aiogram.filters import Command, CommandStart, CommandObject, Filter, BaseFilter, command
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
from modul.clientbot.handlers.refs.shortcuts import plus_ref, plus_money
from modul.clientbot.keyboards import reply_kb
from modul.clientbot.shortcuts import get_all_users
from modul.loader import client_bot_router
from modul.models import UserTG, AdminInfo


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
    """
    Kino bot boshlanish funksiyasi
    """
    try:
        sub_status = await check_subs(message.from_user.id, bot)
        if not sub_status:
            kb = await get_subs_kb(bot)  # bot ni parametr sifatida uzatamiz
            await message.answer(
                '<b>Чтобы воспользоваться ботом, необходимо подписаться на каналы</b>',
                reply_markup=kb
            )
            return

        await state.set_state(SearchFilmForm.query)
        await message.answer(
            '<b>Отправьте название фильма / сериала / аниме</b>\n\n'
            'Не указывайте года, озвучки и т.д.\n\n'
            'Правильный пример: Ведьмак\n'
            'Неправильный пример: Ведьмак 2022',
            parse_mode="HTML",
            reply_markup=ReplyKeyboardRemove()
        )
    except Exception as e:
        logger.error(f"Error in start_kino_bot: {e}")
        await message.answer(
            "Произошла ошибка при запуске бота. Пожалуйста, попробуйте позже или обратитесь к администратору."
        )

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


# /var/www/Konstructor/modul/clientbot/handlers/kino_bot/handlers/bot.py
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
        # Get referral ID from message text after /start command
        referral = message.text[7:] if message.text and len(message.text) > 7 else None
        logger.info(f"Processing start command with referral: {referral}")

        if referral:
            # Pass referral ID directly
            await start_ref(message, bot=bot, referral=referral)
        else:
            await start_ref(message, bot=bot)

    elif shortcuts.have_one_module(bot_db, "kino"):
        await start_kino_bot(message, state, bot)
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
    """
    /start komandasi uchun handler
    """
    try:
        logger.info(f"Start command received from user {message.from_user.id}")
        bot_db = await shortcuts.get_bot(bot)

        if command.args:
            logger.info(f"Referral args received: {command.args}")
            await state.update_data(referral=command.args)

        uid = message.from_user.id
        user = await shortcuts.get_user(uid, bot)

        if not user:
            if command.args and command.args.isdigit():
                inviter_id = int(command.args)
                inviter = await shortcuts.get_user(inviter_id, bot)
                if inviter:
                    # Referral xabarini yuborish
                    with suppress(TelegramForbiddenError):
                        user_link = html.link('реферал', f'tg://user?id={uid}')
                        await bot.send_message(
                            chat_id=command.args,
                            text=f"У вас новый {user_link}!"
                        )

                    try:
                        # Process referral in transaction
                        @sync_to_async
                        @transaction.atomic
                        def update_referral():
                            user_tg = UserTG.objects.select_for_update().get(uid=inviter_id)
                            user_tg.refs += 1
                            user_tg.balance += float(AdminInfo.objects.first().price or 10.0)
                            user_tg.save()
                            return True

                        await update_referral()
                        logger.info(f"Successfully updated referral stats for user {inviter_id}")
                    except Exception as e:
                        logger.error(f"Error updating referral stats: {e}")
            else:
                inviter = None

            me = await bot.get_me()
            new_link = f"https://t.me/{me.username}?start={message.from_user.id}"
            await save_user(u=message.from_user, inviter=inviter, bot=bot, link=new_link)

        await start(message, state, bot)

    except Exception as e:
        logger.error(f"Error in start_on handler: {e}")
        await message.answer(
            "Произошла ошибка при запуске. Пожалуйста, попробуйте позже."
        )


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




import yt_dlp
import logging
from aiogram.types import Message, FSInputFile
from aiogram.enums import ChatAction
from aiogram import Bot
import os

logger = logging.getLogger(__name__)


@client_bot_router.message(Download.download)
async def youtube_download_handler(message: Message, state: FSMContext, bot: Bot):

    if not message.text:
        await message.answer('Пришлите ссылку на видео')
        return

    url = message.text
    me = await bot.get_me()

    if 'tiktok.com' in url:
        await handle_tiktok(message, url, me, bot)
    elif 'instagram' in url or 'inst.ae' in url:
        await handle_instagram(message, url, me, bot)
    else:

        await handle_youtube(message, url, me, bot, state)



async def handle_tiktok(message: Message, url: str, me, bot: Bot):
    try:
        ydl_opts = {
            'format': 'mp4',
            'quiet': True,
            'no_warnings': True,
            'max_filesize': 40000000,
        }

        if '?' in url:
            url = url.split('?')[0]

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(url, download=False)
                if info and 'url' in info:
                    try:
                        await bot.send_video(
                            chat_id=message.chat.id,
                            video=info['url'],
                            caption=f"📹 TikTok video\nСкачано через @{me.username}",
                        )
                        await shortcuts.add_to_analitic_data(me.username, url)
                        return
                    except Exception:
                        # Если не удалось отправить по URL, пробуем скачать
                        await download_and_send_video(message, url, ydl_opts, me, bot, "TikTok")
                else:
                    await message.answer("❌ Не удалось получить ссылку на видео")

            except Exception as e:
                logger.error(f"TikTok processing error: {e}")
                await message.answer("❌ Ошибка при скачивании из TikTok")

    except Exception as e:
        logger.error(f"TikTok handler error: {e}")
        await message.answer("❌ Ошибка при обработке TikTok видео")


async def handle_instagram(message: Message, url: str, me, bot: Bot):
    try:
        await bot.send_chat_action(message.chat.id, ChatAction.UPLOAD_PHOTO)


        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
            'max_filesize': 45000000,

            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'DNT': '1',
                'Connection': 'keep-alive',
            }
        }

        try:
            media_id = url.split('/')[-1].split('?')[0]

            api_url = f'https://www.instagram.com/p/{media_id}/?__a=1'

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                try:
                    info = ydl.extract_info(url, download=False)

                    if 'entries' in info:
                        entries = info['entries']
                        for entry in entries:
                            if 'url' in entry:
                                if entry.get('ext') in ['mp4', 'mov']:
                                    await bot.send_video(
                                        chat_id=message.chat.id,
                                        video=entry['url'],
                                        caption=f"📹 Instagram video\nСкачано через @{me.username}"
                                    )
                                else:
                                    await bot.send_photo(
                                        chat_id=message.chat.id,
                                        photo=entry['url'],
                                        caption=f"🖼 Instagram фото\nСкачано через @{me.username}"
                                    )
                    else:
                        if info.get('ext') in ['mp4', 'mov']:
                            await bot.send_video(
                                chat_id=message.chat.id,
                                video=info['url'],
                                caption=f"📹 Instagram video\nСкачано через @{me.username}"
                            )
                        else:
                            await bot.send_photo(
                                chat_id=message.chat.id,
                                photo=info['url'],
                                caption=f"🖼 Instagram фото\nСкачано через @{me.username}"
                            )

                    await shortcuts.add_to_analitic_data(me.username, url)

                except Exception as e:
                    logger.error(f"Instagram extraction error: {str(e)}")
                    try:
                        ydl_opts['format'] = 'worst'
                        with yt_dlp.YoutubeDL(ydl_opts) as ydl_low:
                            info = ydl_low.extract_info(url, download=True)
                            media_path = ydl_low.prepare_filename(info)

                            if os.path.exists(media_path):
                                try:
                                    if info.get('ext') in ['mp4', 'mov']:
                                        await bot.send_video(
                                            chat_id=message.chat.id,
                                            video=FSInputFile(media_path),
                                            caption=f"📹 Instagram video (Низкое качество)\nСкачано через @{me.username}"
                                        )
                                    else:
                                        await bot.send_photo(
                                            chat_id=message.chat.id,
                                            photo=FSInputFile(media_path),
                                            caption=f"🖼 Instagram фото\nСкачано через @{me.username}"
                                        )
                                finally:
                                    if os.path.exists(media_path):
                                        os.remove(media_path)

                    except Exception as low_quality_error:
                        logger.error(f"Low quality download error: {str(low_quality_error)}")
                        await message.answer("❌ Не удалось скачать медиа")

        except Exception as e:
            logger.error(f"Instagram download error: {str(e)}")
            await message.answer("❌ Ошибка при скачивании. Возможно пост недоступен или защищен.")

    except Exception as e:
        logger.error(f"Instagram handler error: {str(e)}")
        await message.answer("❌ Произошла ошибка")


from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters.callback_data import CallbackData
import base64


class FormatCallback(CallbackData, prefix="format"):
    format_id: str
    type: str
    quality: str
    index: int


async def handle_youtube(message: Message, url: str, me, bot: Bot, state: FSMContext):
    try:
        status_message = await message.answer("🔍 Проверяю доступные форматы...")

        base_opts = {
            'quiet': True,
            'no_warnings': True,
            'noplaylist': True,
            'format': 'best[height<=480]', # Default format restriction
            'http_headers': {  # Add custom headers
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            }
        }

        with yt_dlp.YoutubeDL(base_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            formats = info.get('formats', [])
            title = info.get('title', 'Video')

            builder = InlineKeyboardBuilder()
            valid_formats = []
            seen_heights = set()

            # Filter and deduplicate video formats
            video_formats = []
            for f in formats:
                if f.get('ext') == 'mp4' and f.get('height', 0) <= 480 and f.get('vcodec') != 'none':
                    video_formats.append(f)

            # Sort by height and preference
            video_formats.sort(key=lambda x: (x.get('height', 0), x.get('tbr', 0)), reverse=True)

            # Add best formats for each unique height
            for f in video_formats:
                height = f.get('height', 0)
                if height > 0 and height not in seen_heights:
                    seen_heights.add(height)
                    format_info = {
                        'format_id': f'{f["format_id"]}+bestaudio/best',  # Combine with best audio
                        'type': 'video',
                        'height': height
                    }
                    valid_formats.append(format_info)
                    builder.button(
                        text=f"🎥 {height}p",
                        callback_data=FormatCallback(
                            format_id=format_info['format_id'],
                            type='video',
                            quality=str(height),
                            index=len(valid_formats) - 1
                        ).pack()
                    )

            # Add audio format
            audio_format = next((f for f in formats if f.get('acodec', 'none') != 'none' and f.get('vcodec') == 'none'), None)
            if audio_format:
                format_info = {
                    'format_id': 'bestaudio/best',
                    'type': 'audio',
                    'height': 0
                }
                valid_formats.append(format_info)
                builder.button(
                    text="🎵 Аудио",
                    callback_data=FormatCallback(
                        format_id=format_info['format_id'],
                        type='audio',
                        quality='audio',
                        index=len(valid_formats) - 1
                    ).pack()
                )

            builder.adjust(2)
            await status_message.delete()

            if valid_formats:
                await state.update_data(url=url, formats=valid_formats)
                await message.answer(
                    f"📹 {title}\n\nВыберите формат:",
                    reply_markup=builder.as_markup()
                )
            else:
                await message.answer("❌ Не найдены подходящие форматы")
                await state.set_state(Download.download)

    except Exception as e:
        logger.error(f"YouTube handler error: {str(e)}")
        await message.answer("❌ Ошибка при получении форматов")
        await state.set_state(Download.download)


class DownloadProgress:
    def __init__(self, message: Message):
        self.message = message
        self.last_update_time = 0
        self.last_percentage = 0
        self.last_text = None
        self.message_to_edit = None

    async def init_progress_message(self):
        """Initialize the progress message"""
        self.message_to_edit = await self.message.answer("⏳ Начинаю загрузку...")
        return self.message_to_edit

    def get_progress_bar(self, percentage):
        filled = int(percentage / 5)  # 20 segments
        empty = 20 - filled
        return f"[{'█' * filled}{'▒' * empty}]"

    def create_text(self, percentage, speed):
        progress_bar = self.get_progress_bar(percentage)
        speed_text = f"{speed / 1024 / 1024:.1f} МБ/с" if speed > 0 else "⌛️"
        return f"⏳ Загрузка...\n{progress_bar}\n{percentage:.1f}% | {speed_text}"

    def progress_hook(self, d):
        if d['status'] == 'downloading':
            try:
                current_time = time.time()

                # Update only if more than 2 seconds passed or percentage changed significantly
                total = d.get('total_bytes', 0) or d.get('total_bytes_estimate', 0)
                downloaded = d.get('downloaded_bytes', 0)

                if total > 0:
                    percentage = (downloaded / total) * 100
                    speed = d.get('speed', 0)

                    # Only update if enough time passed or significant change
                    if (current_time - self.last_update_time >= 2 and
                            abs(percentage - self.last_percentage) >= 1):

                        text = self.create_text(percentage, speed)

                        # Only update if text actually changed
                        if text != self.last_text:
                            asyncio.run_coroutine_threadsafe(
                                self.message_to_edit.edit_text(text),
                                asyncio.get_event_loop()
                            )
                            self.last_text = text
                            self.last_percentage = percentage
                            self.last_update_time = current_time

            except Exception as e:
                if "message is not modified" not in str(e):  # Ignore same content errors
                    logger.error(f"Progress update error: {str(e)}")


@client_bot_router.callback_query(FormatCallback.filter())
async def process_format_selection(callback: CallbackQuery, callback_data: FormatCallback, state: FSMContext):
    message = callback.message
    if not message:
        return

    try:
        try:
            await callback.answer()
        except Exception as e:
            logger.error(f"Callback answer error: {e}")
            pass

        # Create progress handler
        progress_handler = DownloadProgress(message)
        await progress_handler.init_progress_message()

        data = await state.get_data()
        url = data.get('url')
        formats = data.get('formats', [])

        download_opts = {
            'format': callback_data.format_id,
            'quiet': True,
            'no_warnings': True,
            'noplaylist': True,
            'progress_hooks': [progress_handler.progress_hook],
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            },
            'merge_output_format': 'mp4'
        }

        with yt_dlp.YoutubeDL(download_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info)

            if os.path.exists(file_path):
                try:
                    if callback_data.type == 'video':
                        video = FSInputFile(file_path)
                        await message.answer_video(
                            video=video,
                            caption=f"📹 {info.get('title', 'Video')} ({callback_data.quality}p)"
                        )
                    else:
                        audio = FSInputFile(file_path)
                        await message.answer_audio(
                            audio=audio,
                            title=info.get('title', 'Audio'),
                            caption="🎵 Аудио версия"
                        )
                finally:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                    if progress_handler.message_to_edit:
                        try:
                            await progress_handler.message_to_edit.delete()
                        except Exception:
                            pass
                    try:
                        await message.delete()
                    except Exception:
                        pass

        await state.set_state(Download.download)
        await message.answer("✅ Отправьте новую ссылку на видео:")

    except Exception as e:
        error_msg = str(e)
        if "Connection lost" in error_msg:
            await message.answer("❌ Соединение прервано. Попробуйте еще раз.")
        else:
            logger.error(f"Download error: {error_msg}")
            await message.answer("❌ Ошибка при скачивании. Попробуйте еще раз.")
        await state.set_state(Download.download)

async def download_and_send_video(message: Message, url: str, ydl_opts: dict, me, bot: Bot, platform: str):
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            video_path = ydl.prepare_filename(info)

            if os.path.exists(video_path):
                try:
                    video = FSInputFile(video_path)
                    await bot.send_video(
                        chat_id=message.chat.id,
                        video=video,
                        caption=f"📹 {info.get('title', 'Video')} (Низкое качество)\nСкачано через @{me.username}",
                        supports_streaming=True
                    )
                finally:
                    # Всегда удаляем файл после отправки
                    if os.path.exists(video_path):
                        os.remove(video_path)
            else:
                raise FileNotFoundError("Downloaded video file not found")

    except Exception as e:
        logger.error(f"Error downloading and sending video from {platform}: {e}")
        await message.answer(f"❌ Не удалось скачать видео из {platform}")


async def is_short_video(url: str) -> bool:
    return any(x in url.lower() for x in ['shorts', 'reels', 'tiktok.com'])


# Регистрация хендлера
client_bot_router.message.register(youtube_download_handler, Download.download)
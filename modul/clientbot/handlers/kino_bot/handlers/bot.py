import asyncio
import time
from contextlib import suppress

from aiogram import Bot, F, html
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest
from aiogram.filters import Command, CommandStart, CommandObject, Filter, BaseFilter, command
from aiogram.fsm.context import FSMContext
from aiogram.filters.state import State, StatesGroup, StateFilter

from aiogram.types import CallbackQuery, Message, InlineKeyboardButton, InlineKeyboardMarkup, InlineQueryResultArticle, \
    InputTextMessageContent, InlineQuery, BotCommand, ReplyKeyboardRemove, URLInputFile
from aiogram.utils.deep_linking import create_start_link
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from django.db import transaction
from django.utils import timezone
import re

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

import yt_dlp
import logging
from aiogram.types import Message, FSInputFile
from aiogram.enums import ChatAction
from aiogram import Bot
import os
from aiogram.filters.callback_data import CallbackData
from concurrent.futures import ThreadPoolExecutor
logger = logging.getLogger(__name__)


class SearchFilmForm(StatesGroup):
    query = State()


class AddChannelSponsorForm(StatesGroup):
    channel = State()


class SendMessagesForm(StatesGroup):
    message = State()

class Download(StatesGroup):
    download = State()


# Callback data
class FormatCallback(CallbackData, prefix="format"):
    format_id: str
    type: str
    quality: str
    index: int
executor = ThreadPoolExecutor(max_workers=4)


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
    bot = call.bot
    users_count = await get_all_users(bot)
    await call.message.edit_text(
        f'<b>Количество пользователей в боте:</b> {users_count}',
        reply_markup=admin_kb
    )



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
    """
    Обработчик для добавления спонсорского канала.
    """
    try:
        channel_id = int(message.text)

        # Telegram API orqali kanal haqida ma'lumot olish
        chat_info = await bot.get_chat(channel_id)

        # `available_reactions` ni filtrlash
        if hasattr(chat_info, "available_reactions") and chat_info.available_reactions:
            chat_info.available_reactions = [
                reaction for reaction in chat_info.available_reactions
                if reaction.type in {"emoji", "custom_emoji"}
            ]

        # Kanal ekanligini tekshirish
        if chat_info.type != "channel":
            await message.answer(
                "Указанный ID не является каналом. Пожалуйста, введите ID канала.",
                reply_markup=cancel_kb
            )
            return

        # Bot adminligini tekshirish
        bot_member = await bot.get_chat_member(channel_id, bot.id)
        if bot_member.status not in ["administrator", "creator"]:
            await message.answer(
                "Бот не является администратором канала. Пожалуйста, добавьте бота в администраторы канала.",
                reply_markup=cancel_kb
            )
            return

        # Kanalga a'zo bo‘lish uchun taklif linkini olish
        invite_link = chat_info.invite_link
        if not invite_link:
            invite_link = (await bot.create_chat_invite_link(channel_id)).invite_link

        # Kanalni bazaga qo‘shish
        create_channel_sponsor(channel_id)
        await state.clear()

        await message.answer(
            f"✅ Канал успешно добавлен!\n\n"
            f"📣 Название: {chat_info.title}\n"
            f"🆔 ID: {channel_id}\n"
            f"🔗 Ссылка: {invite_link}",
            disable_web_page_preview=True
        )

    except ValueError:
        await message.answer(
            "Неверный формат. Пожалуйста, введите числовой ID канала.",
            reply_markup=cancel_kb
        )
    except TelegramBadRequest as e:
        logger.error(f"Telegram API xatosi: {e}")
        await message.answer(
            "Бот не смог найти канал. Пожалуйста, проверьте ID канала.",
            reply_markup=cancel_kb
        )
    except Exception as e:
        logger.error(f"Channel add error: channel_id={channel_id}, error={str(e)}")
        await message.answer(
            "Произошла ошибка. Пожалуйста, попробуйте еще раз.",
            reply_markup=cancel_kb
        )









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


def get_best_formats(formats):
    """Get the best video and audio formats"""
    video_formats = {}
    audio_format = None

    # Filter and find best formats
    for f in formats:
        if f.get('ext') == 'mp4' and f.get('height', 0) <= 720:
            height = f.get('height', 0)
            if height <= 0:  # Skip invalid heights
                continue

            filesize = f.get('filesize', float('inf'))

            # Only keep formats with better quality or smaller size
            if height not in video_formats or filesize < video_formats[height]['filesize']:
                video_formats[height] = {
                    'format_id': f['format_id'],
                    'filesize': filesize,
                    'type': 'video',
                    'quality': f'{height}p'
                }
        elif f.get('ext') == 'm4a' and (not audio_format or f.get('filesize', float('inf')) < audio_format['filesize']):
            audio_format = {
                'format_id': f['format_id'],
                'filesize': f.get('filesize', float('inf')),
                'type': 'audio',
                'quality': 'audio'
            }

    return list(video_formats.values()), audio_format


def download_video(url, format_id):
    """Download video in a separate thread"""
    ydl_opts = {
        'format': format_id,
        'quiet': True,
        'no_warnings': True,
        'noplaylist': True,
        'encoding': 'utf-8',
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return ydl.prepare_filename(info), info


@client_bot_router.message(Download.download)
async def youtube_download_handler(message: Message, state: FSMContext, bot: Bot):

    if not message.text:
        await message.answer("❗ Отправьте ссылку на видео")
        return

    url = message.text.strip()
    me = await bot.get_me()

    if 'tiktok.com' in url:
        await handle_tiktok(message, url, me, bot)
    elif 'instagram.com' in url or 'instagr.am' in url or 'inst.ae' in url:
        await handle_instagram(message, url, me, bot)
    elif 'youtube.com' in url or 'youtu.be' in url:
        await handle_youtube(message, url, me, bot, state)
    else:
        await message.answer("❗ Отправьте ссылку на видео с YouTube, Instagram или TikTok")

async def handle_youtube(message: Message, url: str, me, bot: Bot, state: FSMContext):
    status_message = await message.answer("⏳ Получаю информацию о видео...")

    try:
        base_opts = {
            'quiet': True,
            'no_warnings': True,
            'noplaylist': True,
            'encoding': 'utf-8',
            'extract_flat': True,
        }

        with yt_dlp.YoutubeDL(base_opts) as ydl:
            info = await asyncio.get_event_loop().run_in_executor(
                executor,
                lambda: ydl.extract_info(url, download=False)
            )

            formats = info.get('formats', [])
            title = info.get('title', 'Video').encode('utf-8', 'replace').decode('utf-8')

            video_formats, audio_format = get_best_formats(formats)
            builder = InlineKeyboardBuilder()
            valid_formats = []

            # Add video formats (sorted by quality)
            for fmt in sorted(video_formats, key=lambda x: int(x['quality'].rstrip('p')), reverse=True):
                valid_formats.append(fmt)
                builder.button(
                    text=f"🎥 {fmt['quality']}" + (
                        f" ({fmt['filesize'] // 1024 // 1024}MB)" if fmt.get('filesize') else ""),
                    callback_data=FormatCallback(
                        format_id=fmt['format_id'],
                        type='video',
                        quality=fmt['quality'],
                        index=len(valid_formats) - 1
                    ).pack()
                )

            # Add audio format
            if audio_format:
                valid_formats.append(audio_format)
                builder.button(
                    text=f"🎵 Аудио" + (
                        f" ({audio_format['filesize'] // 1024 // 1024}MB)" if audio_format.get('filesize') else ""),
                    callback_data=FormatCallback(
                        format_id=audio_format['format_id'],
                        type='audio',
                        quality='audio',
                        index=len(valid_formats) - 1
                    ).pack()
                )

            builder.adjust(2)

            if valid_formats:
                await state.update_data(url=url, formats=valid_formats, title=title)
                await status_message.edit_text(
                    f"🎥 {title}\n\n"
                    f"Выберите формат:",
                    reply_markup=builder.as_markup()
                )
            else:
                await status_message.edit_text("❗ Не найдены подходящие форматы")

    except Exception as e:
        logger.error(f"YouTube handler error: {str(e)}")
        await status_message.edit_text("❗ Ошибка при получении форматов")


@client_bot_router.callback_query(FormatCallback.filter())
async def process_format_selection(callback: CallbackQuery, callback_data: FormatCallback, state: FSMContext, bot):
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.answer("⏳ Начинаю загрузку...")

        data = await state.get_data()
        url = data.get('url')
        formats = data.get('formats', [])
        title = data.get('title', 'Video')

        if not url or not formats:
            await callback.message.answer("❌ Ошибка: данные не найдены")
            return

        selected_format = formats[callback_data.index]
        progress_msg = await callback.message.answer(
            f"⏳ Загружаю {title}\n"
            f"Формат: {callback_data.quality}"
        )

        try:
            # Download in separate thread
            file_path, info = await asyncio.get_event_loop().run_in_executor(
                executor,
                lambda: download_video(url, selected_format['format_id'])
            )

            if not os.path.exists(file_path):
                raise FileNotFoundError("Файл не найден после загрузки")

            await progress_msg.edit_text("📤 Отправляю файл...")

            try:
                me = await bot.get_me()
                caption = f"🎥 {title}"
                if callback_data.type == 'video':
                    caption += f" ({callback_data.quality})"
                caption += f"\nСкачано через @{me.username}"

                if callback_data.type == 'video':
                    await bot.send_video(
                        chat_id=callback.message.chat.id,
                        video=FSInputFile(file_path),
                        caption=caption,
                        supports_streaming=True
                    )
                else:
                    await bot.send_audio(
                        chat_id=callback.message.chat.id,
                        audio=FSInputFile(file_path),
                        caption=caption,
                        title=title
                    )
            finally:
                if os.path.exists(file_path):
                    os.remove(file_path)

            await progress_msg.delete()
            await state.clear()

        except Exception as e:
            logger.error(f"Download error: {str(e)}")
            await progress_msg.edit_text(f"❌ Ошибка при загрузке")

    except Exception as e:
        logger.error(f"Format selection error: {str(e)}")
        await callback.message.answer("❌ Ошибка при обработке запроса")


class InstagramDownloader:
    def __init__(self):
        self.ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'max_filesize': 50000000,
            'format': 'best',
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': '*/*',
                'Accept-Encoding': 'gzip, deflate, br',
                'Accept-Language': 'en-US,en;q=0.9',
                'Origin': 'https://www.instagram.com',
                'Referer': 'https://www.instagram.com/',
                'Sec-Fetch-Dest': 'empty',
                'Sec-Fetch-Mode': 'cors',
                'Sec-Fetch-Site': 'same-origin',
                'Connection': 'keep-alive',
            }
        }

    async def download_with_yt_dlp(self, url):
        with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
            return ydl.extract_info(url, download=False)

    async def download_with_api(self, url):
        # API endpoints for different Instagram content types
        api_endpoints = [
            "https://api.instagram.com/oembed/?url={}",
            "https://www.instagram.com/api/v1/media/{}/info/",
            "https://www.instagram.com/p/{}/?__a=1&__d=1"
        ]

        # Extract media ID from URL
        media_id = re.search(r'/p/([^/]+)', url)
        if not media_id:
            media_id = re.search(r'/reel/([^/]+)', url)
        if not media_id:
            return None

        media_id = media_id.group(1)

        async with aiohttp.ClientSession() as session:
            for endpoint in api_endpoints:
                try:
                    formatted_url = endpoint.format(url if '{}' in endpoint else media_id)
                    async with session.get(formatted_url) as response:
                        if response.status == 200:
                            data = await response.json()
                            if 'video_url' in data:
                                return {'url': data['video_url'], 'ext': 'mp4'}
                            elif 'thumbnail_url' in data:
                                return {'url': data['thumbnail_url'], 'ext': 'jpg'}
                except Exception as e:
                    logger.error(f"API endpoint error: {e}")
                    continue
        return None


async def handle_instagram(message: Message, url: str, me, bot: Bot):
    try:
        await bot.send_chat_action(message.chat.id, ChatAction.UPLOAD_PHOTO)
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
            'max_filesize': 45000000,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': '*/*',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Referer': 'https://www.instagram.com/',
                'Origin': 'https://www.instagram.com',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Sec-Fetch-Dest': 'empty',
                'Sec-Fetch-Mode': 'cors',
                'Sec-Fetch-Site': 'same-origin',
            }
        }

        progress_msg = await message.answer("⏳ Получаю информацию...")

        try:
            if '?' in url:
                url = url.split('?')[0]

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                try:
                    info = ydl.extract_info(url, download=False)

                    if 'entries' in info:
                        await progress_msg.edit_text("🔄 Загружаю карусель...")
                        entries = info['entries']
                        sent_count = 0

                        for entry in entries:
                            if 'url' in entry:
                                try:
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
                                    sent_count += 1
                                except Exception as item_error:
                                    logger.error(f"Error sending carousel item: {item_error}")
                                    continue

                        if sent_count > 0:
                            await shortcuts.add_to_analitic_data(me.username, url)
                            await progress_msg.delete()
                        else:
                            raise Exception("Не удалось загрузить элементы карусели")

                    else:
                        await progress_msg.edit_text("🔄 Загружаю медиа...")

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
                        await progress_msg.delete()

                except Exception as extract_error:
                    logger.error(f"Instagram extraction error: {str(extract_error)}")
                    await progress_msg.edit_text("🔄 Пробую альтернативный способ загрузки...")

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
                                    await shortcuts.add_to_analitic_data(me.username, url)
                                    await progress_msg.delete()
                                finally:
                                    if os.path.exists(media_path):
                                        os.remove(media_path)
                            else:
                                raise FileNotFoundError("Файл не найден после загрузки")

                    except Exception as low_quality_error:
                        logger.error(f"Low quality download error: {str(low_quality_error)}")
                        await progress_msg.edit_text("❌ Не удалось загрузить медиа")

        except Exception as e:
            logger.error(f"Instagram download error: {str(e)}")
            await progress_msg.edit_text("❌ Ошибка при скачивании. Возможно пост недоступен или защищен.")

    except Exception as e:
        logger.error(f"Instagram handler error: {str(e)}")
        if 'progress_msg' in locals():
            await progress_msg.edit_text("❌ Произошла ошибка")
        else:
            await message.answer("❌ Произошла ошибка")


# @client_bot_router.message()
# async def instagram_handler(message: Message, bot):
#     url = message.text
#     if 'instagram.com' in url or 'instagr.am' in url:
#         me = await bot.get_me()
#         await handle_instagram(message, url, me, bot)

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
                # Получаем информацию о видео без скачивания
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

# @client_bot_router.message()
# async def tiktok_handler(message: Message, bot):
#     """TikTok linklar uchun handler"""
#     url = message.text
#     if 'tiktok.com' in url:
#         me = await bot.get_me()
#         await handle_tiktok(message, url, me, bot)

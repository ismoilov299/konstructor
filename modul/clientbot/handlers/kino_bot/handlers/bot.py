import asyncio
import logging
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
from modul.clientbot.handlers.refs.handlers.bot import start_ref, banned, check_channels
from modul.clientbot.handlers.refs.shortcuts import get_actual_price
from modul.clientbot.keyboards import reply_kb
from modul.clientbot.shortcuts import get_all_users, get_users_count, get_all_users_list, increase_referral, \
    get_user_info_db
from modul.loader import client_bot_router
logger = logging.getLogger(__name__)


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
async def admin_send_message_msg(message: Message, state: FSMContext, bot: Bot):
    try:
        await state.clear()
        # Foydalanuvchilar listini olamiz
        users = await get_all_users_list(bot)

        if users:
            await asyncio.create_task(send_message(message, users))
            await message.answer('Рассылка началась!\n\nПо ее окончанию вы получите отчет')
        else:
            await message.answer("Пользователи не найдены")

    except Exception as e:
        logger.error(f"Error in admin_send_message_msg: {e}", exc_info=True)
        await message.answer("Произошла ошибка при начале рассылки")


@client_bot_router.callback_query(F.data == 'admin_get_stats', AdminFilter(), StateFilter('*'))
async def admin_get_stats(call: CallbackQuery, bot: Bot):
    try:
        # Foydalanuvchilar sonini olamiz
        users_count = await get_users_count(bot)
        logger.info(f"Got users count: {users_count}")

        await call.message.edit_text(
            f'<b>Количество пользователей в боте:</b> {users_count}',
            reply_markup=admin_kb
        )
    except Exception as e:
        logger.error(f"Error in admin_get_stats: {e}", exc_info=True)
        await call.message.edit_text("Произошла ошибка при получении статистики")


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
        kb = await get_subs_kb(bot)  # bot parametrini qo'shdik
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
    logger.info(f"Saving user {u.id} with inviter {inviter}")

    try:
        # Get or create Bot instance
        bot_instance = models.Bot.objects.select_related("owner").filter(token=bot.token).first()

        # Get or create UserTG
        user, created = models.UserTG.objects.get_or_create(
            uid=u.id,
            defaults={
                'username': u.username,
                'first_name': u.first_name,
                'last_name': u.last_name,
                'user_link': link
            }
        )

        # Check if ClientBotUser exists
        client_user = models.ClientBotUser.objects.filter(uid=u.id, bot=bot_instance).first()

        if not client_user:
            # Create new ClientBotUser with inviter if provided
            client_user = models.ClientBotUser.objects.create(
                uid=u.id,
                user=user,
                bot=bot_instance,
                inviter=inviter,
                current_ai_limit=12 if not user else 0,
                balance=0,
                referral_balance=0
            )

            # If there's an inviter and they haven't gotten the bonus yet
            if inviter and not inviter.inviter_got_bonus:
                inviter.referral_count += 1
                inviter.inviter_got_bonus = True
                inviter.save()
                logger.info(f"Updated inviter {inviter.uid} referral count to {inviter.referral_count}")

        return client_user

    except Exception as e:
        logger.error(f"Error in save_user: {e}", exc_info=True)
        raise


class NonChatGptFilter(Filter):
    async def __call__(self, message: Message, bot: Bot) -> bool:
        bot_db = await shortcuts.get_bot(bot)
        return not shortcuts.have_one_module(bot_db, "chatgpt")


async def start(message: Message, state: FSMContext, bot: Bot):
    try:
        logger.info(f"Starting start function for user {message.from_user.id}")
        bot_db = await shortcuts.get_bot(bot)
        uid = message.from_user.id
        text = "Добро пожаловать, {hello}".format(hello=html.quote(message.from_user.full_name))
        kwargs = {}

        # Modullarni tekshiramiz
        modules = []
        for module in ["download", "refs", "kino", "chatgpt"]:
            if shortcuts.have_one_module(bot_db, module):
                modules.append(module)
                logger.info(f"Module {module} is enabled for bot {bot_db.token}")

        logger.info(f"Active modules for user {uid}: {modules}")

        if "kino" in modules:
            logger.info(f"Starting kino module for user {uid}")
            await start_kino_bot(message, state, bot)

        if "refs" in modules:
            logger.info(f"Starting refs module for user {uid}")
            link = await create_start_link(message.bot, str(message.from_user.id), encode=False)
            price = await get_actual_price()
            await message.answer(
                f"👥  Приглашай друзей и зарабатывай, за \nкаждого друга ты получишь {price}₽\n\n"
                f"🔗 Ваша ссылка для приглашений:\n {link}"
            )

        elif "download" in modules:
            builder = ReplyKeyboardBuilder()
            builder.button(text='💸Заработать')
            text = ("🤖 Привет, {full_name}! Я бот-загрузчик...").format(
                full_name=message.from_user.full_name)
            await state.set_state(Download.download)
            kwargs.update({
                'parse_mode': "Markdown",
                'reply_markup': builder.as_markup(resize_keyboard=True)
            })
            await message.answer(text, **kwargs)

        elif "chatgpt" in modules:
            builder = InlineKeyboardBuilder()
            builder.button(text='☁ Чат с GPT-4', callback_data='chat_4')
            builder.button(text='☁ Чат с GPT-3.5', callback_data='chat_3')
            builder.button(text='🆘 Помощь', callback_data='helper')
            builder.button(text='⚙️ Настройки', callback_data='settings')
            builder.button(text='💸Заработать', callback_data='ref')
            builder.adjust(2, 1, 1, 1, 1, 1, 2)

            user_info = await get_user_info_db(uid, bot)
            logger.info(f"Got user info for {uid}: {user_info}")

            if user_info:
                text = f'Привет {message.from_user.username}\nВаш баланс - {user_info[2]}'
            kwargs['reply_markup'] = builder.as_markup()
            await message.answer(text, **kwargs)

        else:
            kwargs['reply_markup'] = await reply_kb.main_menu(uid, bot)
            await message.answer(text, **kwargs)

    except Exception as e:
        logger.error(f"Error in start: {e}", exc_info=True)
        await message.answer("Произошла ошибка. Попробуйте позже.")


@client_bot_router.message(CommandStart(), NonChatGptFilter())
async def start_on(message: Message, state: FSMContext, bot: Bot, command: CommandObject):
    try:
        logger.info(f"Starting bot for user {message.from_user.id}")
        bot_db = await shortcuts.get_bot(bot)

        referral = command.args
        uid = message.from_user.id
        user = await shortcuts.get_user(uid=uid, bot=bot)
        logger.info(f"Current user data: {user}")

        if not user:
            inviter = None
            if referral and referral.isdigit():
                inviter = await shortcuts.get_user(uid=int(referral), bot=bot)
                logger.info(f"Found inviter: {inviter} for referral {referral}")

                if inviter:
                    logger.info(
                        f"Inviter before update - balance: {inviter.referral_balance}, count: {inviter.referral_count}")

                    # Создаём нового пользователя
                    new_user = await save_user(
                        u=message.from_user,
                        inviter=inviter,
                        bot=bot,
                        link=None
                    )
                    logger.info(f"Created new user: {new_user}")

                    # Добавляем бонус инвайтеру
                    success = await increase_referral(inviter)
                    logger.info(f"Increase referral result: {success}")

                    # Проверяем обновлённые данные
                    updated_inviter = await shortcuts.get_user(uid=int(referral), bot=bot)
                    logger.info(
                        f"Inviter after update - balance: {updated_inviter.referral_balance}, count: {updated_inviter.referral_count}")

                    if success:
                        with suppress(TelegramForbiddenError):
                            user_link = html.link('реферал', f'tg://user?id={uid}')
                            await bot.send_message(
                                chat_id=referral,
                                text=f"🎉 Вы пригласили нового друга! {user_link}\nВы получили бонус 4.0₽!",
                                parse_mode='HTML'
                            )
                    else:
                        logger.error(f"Failed to add referral bonus for inviter {inviter.uid}")

            if not inviter:
                logger.info(f"Creating new user without inviter: {uid}")
                await save_user(u=message.from_user, bot=bot)

        await start(message, state, bot)

    except Exception as e:
        logger.error(f"Error in start_on: {e}", exc_info=True)
        await message.answer("Произошла ошибка. Попробуйте позже.")


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


async def youtube_download_handler(message: Message, bot: Bot):
    await message.answer('📥 Скачиваю...')

    if not message.text:
        await message.answer('Пришлите ссылку на видео')
        return

    if 'streaming' in message.text:
        await message.answer('Извините, но я не могу скачать стримы')
        return

    me = await bot.get_me()
    await shortcuts.add_to_analitic_data(me.username, message.text)

    if 'instagram' in message.text:
        new_url = message.text.replace('www.', 'dd')
        await message.answer(
            f'{new_url}\r\nВидео скачано через бота @{me.username}'
        )
        return

    url = message.text
    await bot.send_chat_action(message.chat.id, "upload_video")

    ydl_opts = {
        'cachedir': False,
        'noplaylist': True,
        'outtmpl': 'clientbot/downloads/%(title)s.%(ext)s',
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=mp3]/best[ext=mp4]/best',
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            await bot.send_video(message.chat.id, URLInputFile(info['url']), supports_streaming=True)

            # Обновляем аналитику
            domain = info.get('webpage_url_domain', 'unknown')
            await update_download_analytics(me.username, domain)
    except Exception as e:
        await bot.send_message(message.chat.id, f"Не удалось скачать это видео: {e}")


client_bot_router.message.register(youtube_download_handler, Download.download)


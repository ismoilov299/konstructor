import logging
from contextlib import suppress
from datetime import datetime, timedelta
import math
from aiogram import Bot, html, types, flags, F
from aiogram.filters import CommandObject, CommandStart, Filter
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest, TelegramNotFound
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.types import BotCommand
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

from modul.clientbot import shortcuts, strings
from modul.clientbot.data.callback_datas import MainMenuCallbackData
from modul.clientbot.handlers.chat_gpt_bot.shortcuts import get_info_db
from modul.clientbot.handlers.kino_bot.handlers.bot import start_kino_bot
from modul.clientbot.handlers.refs.handlers.bot import start_ref
from modul.clientbot.keyboards import inline_kb, reply_kb
from modul.clientbot.shortcuts import increase_referral
from modul.clientbot.utils.exceptions import UserNotFound
# from modul.clientbot.utils.order import paginate_orders
from modul import models
from modul.clientbot.data.states import Download
# from modul.clientbot.handlers.anon.handlers.main import cabinet_text

from modul.loader import client_bot_router, bot_session
from aiogram.fsm.context import FSMContext
import sys
import traceback
logger = logging.getLogger(__name__)

from django.db import transaction
from asgiref.sync import sync_to_async
from aiogram import Bot

from modul.models import UserTG


@sync_to_async
@transaction.atomic
def save_user(u, bot: Bot, link=None, inviter=None):
    logger.info(f"Saving user {u.id} with inviter {inviter}")
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
        logger.info(f"User {u.id} already exists in ClientBotUser")
        return client_user

    logger.info(f"Creating new ClientBotUser for {u.id} with inviter {inviter}")
    client_user = models.ClientBotUser.objects.create(
        uid=u.id,
        user=user,
        bot=bot,
        inviter=inviter,  # Bu yerda inviter obyekti saqlanayapti
        current_ai_limit=current_ai_limit
    )

    # Inviter mavjud bo'lsa referral countni oshiramiz
    if inviter:
        inviter.referral_count = models.F('referral_count') + 1
        inviter.save()
        logger.info(f"Increased referral count for inviter {inviter.uid}")

    return client_user


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

@sync_to_async
def get_user(uid: int, bot: Bot = None):
    """Get UserTG instance by uid"""
    try:
        user = UserTG.objects.filter(uid=uid).first()
        if bot and user:
            # Also get ClientBotUser if bot is provided
            client_user = models.ClientBotUser.objects.filter(
                uid=uid,
                bot__token=bot.token
            ).first()
            return client_user
        return user
    except Exception as e:
        print(f"Error in get_user: {str(e)}")
        return None


def start_bot_client():
    @client_bot_router.message(CommandStart())
    async def on_start(message: Message, command: CommandObject, state: FSMContext, bot: Bot):
        logger.info(f"Client bot start command from user: {message.from_user.id}")
        try:
            # Get or create user
            info = await get_user(
                uid=message.from_user.id,
                username=message.from_user.username,
                first_name=message.from_user.first_name if message.from_user.first_name else None,
                last_name=message.from_user.last_name if message.from_user.last_name else None
            )

            # Clear state
            await state.clear()

            # Set bot commands
            commands = await bot.get_my_commands()
            bot_commands = [
                BotCommand(command="/start", description="Меню"),
            ]

            if commands != bot_commands:
                await bot.set_my_commands(bot_commands)

            # Handle referral
            referral = command.args
            uid = message.from_user.id
            user = await get_user(uid, bot)

            if not user:
                if referral and referral.isdigit():
                    inviter = await get_user(int(referral))
                    if inviter:
                        await increase_referral(inviter)
                        with suppress(TelegramForbiddenError):
                            user_link = html.link('реферал', f'tg://user?id={uid}')
                            await bot.send_message(
                                chat_id=referral,
                                text=('new_referral').format(user_link=user_link)
                            )
                else:
                    inviter = None
                await save_user(u=message.from_user, inviter=inviter, bot=bot)

            # Start main menu
            await start(message, state, bot)

        except Exception as e:
            logger.error(f"Error in client bot start: {e}")
            await message.answer("Произошла ошибка. Пожалуйста, попробуйте позже.")


@client_bot_router.message(CommandStart())
# @flags.rate_limit(key="on_start")
async def on_start(message: Message, command: CommandObject, state: FSMContext, bot: Bot):
    print(message.from_user.id)
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
        await save_user(u=message.from_user, inviter=inviter, bot=bot)
    await start(message, state, bot)


@client_bot_router.callback_query(MainMenuCallbackData.filter())
@flags.rate_limit(key="back-to-main-menu", rate=2)
async def main_menu(query: types.CallbackQuery, callback_data: MainMenuCallbackData):
    if callback_data.action is None:
        try:
            await query.message.delete()
        except (TelegramBadRequest, TelegramNotFound):
            await query.message.edit_reply_markup()
        finally:
            await query.message.answer(strings.MAIN_MENU.format(query.from_user.first_name),
                                       reply_markup=await reply_kb.main_menu(query.message.from_user.id))

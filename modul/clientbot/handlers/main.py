from contextlib import suppress
from datetime import datetime, timedelta
import math
from aiogram import Bot, html, types, flags, F
from aiogram.filters import CommandObject, CommandStart, Filter
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest, TelegramNotFound
from aiogram.types import Message, BotCommand
from aiogram.utils.keyboard import InlineKeyboardBuilder

from modul import models
from modul.clientbot import shortcuts, strings
from modul.clientbot.data.callback_datas import MainMenuCallbackData
from modul.clientbot.handlers.chat_gpt_bot.shortcuts import get_info_db
from modul.clientbot.handlers.kino_bot.handlers.bot import start_kino_bot
from modul.clientbot.handlers.refs.handlers.bot import start_ref
from modul.clientbot.handlers.refs.shortcuts import plus_money, plus_ref
from modul.clientbot.keyboards import reply_kb
from modul.clientbot.data.states import Download
from modul.loader import client_bot_router
from aiogram.fsm.context import FSMContext
import logging

from django.db import transaction
from asgiref.sync import sync_to_async
from modul.models import UserTG, AdminInfo

logger = logging.getLogger(__name__)


@sync_to_async
@transaction.atomic
def save_user(u, bot: Bot, link=None, inviter=None):
    try:
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
    except Exception as e:
        logger.error(f"Error in save_user: {e}")
        raise


async def start(message: Message, state: FSMContext, bot: Bot):
    try:
        bot_db = await shortcuts.get_bot(bot)
        uid = message.from_user.id
        text = "Добро пожаловать, {hello}".format(hello=html.quote(message.from_user.full_name))
        kwargs = {}

        if shortcuts.have_one_module(bot_db, "download"):
            text = ("🤖 Привет, {full_name}! Я бот-загрузчик.\r\n\r\n"
                    "Я могу скачать фото/видео/аудио/файлы/архивы с *Youtube, Instagram, TikTok, Facebook, SoundCloud, Vimeo, Вконтакте, Twitter и 1000+ аудио/видео/файловых хостингов*. Просто пришли мне URL на публикацию с медиа или прямую ссылку на файл.").format(
                full_name=message.from_user.full_name)
            await state.set_state(Download.download)
            kwargs['parse_mode'] = "Markdown"
        elif shortcuts.have_one_module(bot_db, "refs"):
            await start_ref(message, bot)
            return
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
            builder.adjust(2, 1, 1, 1, 1)
            result = await get_info_db(uid)
            text = f'Привет {message.from_user.username}\nВаш баланс - {result[0][2]}'
            kwargs['reply_markup'] = builder.as_markup()
        else:
            kwargs['reply_markup'] = await reply_kb.main_menu(uid, bot)

        await message.answer(text, **kwargs)
    except Exception as e:
        logger.error(f"Error in start function: {e}")
        raise


@client_bot_router.message(CommandStart())
async def on_start(message: Message, command: CommandObject, state: FSMContext, bot: Bot):
    try:
        logger.info(f"Start command received from user {message.from_user.id}")
        bot_db = await shortcuts.get_bot(bot)

        if command.args:
            logger.info(f"Referral args received: {command.args}")
            await state.update_data(referral=command.args)

        uid = message.from_user.id
        user = await shortcuts.get_user(uid, bot)

        if not user:
            inviter = None
            if command.args and command.args.isdigit():
                inviter_id = int(command.args)
                inviter = await shortcuts.get_user(inviter_id, bot)
                if inviter:
                    with suppress(TelegramForbiddenError):
                        user_link = html.link('реферал', f'tg://user?id={uid}')
                        await bot.send_message(
                            chat_id=inviter_id,
                            text=f"У вас новый {user_link}!"
                        )
                        print("main start")

                    ref_success = await plus_ref(inviter_id)
                    if ref_success:
                        logger.info(f"Referral count updated for user {inviter_id}")
                    else:
                        logger.error(f"Failed to update referral count for user {inviter_id}")

                    balance_success = await plus_money(inviter_id)
                    if balance_success:
                        logger.info(f"Balance updated for user {inviter_id}")
                    else:
                        logger.error(f"Failed to update balance for user {inviter_id}")

            await save_user(u=message.from_user, inviter=inviter, bot=bot)

        await start(message, state, bot)

    except Exception as e:
        logger.error(f"Error in start handler: {e}")
        await message.answer("Произошла ошибка. Пожалуйста, попробуйте позже.")



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

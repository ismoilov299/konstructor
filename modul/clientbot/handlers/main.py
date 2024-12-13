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
from modul.models import UserTG

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
    """Handler for /start command"""
    try:
        logger.info(f"Start command received from user {message.from_user.id}")

        await state.clear()
        commands = [BotCommand(command="/start", description="Меню")]
        await bot.set_my_commands(commands)

        # Handle referral
        referral = command.args
        uid = message.from_user.id
        user = await shortcuts.get_user(uid, bot)

        if not user:
            if referral and referral.isdigit():
                inviter_id = int(referral)
                inviter = await shortcuts.get_user(inviter_id, bot)

                if inviter and inviter_id != uid:  # Prevent self-referral
                    # Add referral bonus
                    await plus_ref(inviter_id)
                    await plus_money(inviter_id)

                    # Send notification
                    with suppress(TelegramForbiddenError):
                        user_link = html.link('реферал', f'tg://user?id={uid}')
                        await bot.send_message(
                            chat_id=referral,
                            text=f"У вас новый {user_link}!"
                        )
                    logger.info(f"Processed referral: user {uid} invited by {inviter_id}")
            else:
                inviter = None

            await save_user(u=message.from_user, inviter=inviter, bot=bot)

        await start(message, state, bot)

    except Exception as e:
        logger.error(f"Error in start handler: {e}")
        await message.answer("Произошла ошибка. Пожалуйста, попробуйте позже.")


# from contextlib import suppress
# from datetime import datetime, timedelta
# import math
# from aiogram import Bot, html, types, flags, F
# from aiogram.filters import CommandObject, CommandStart, Filter
# from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest, TelegramNotFound
# from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
# from aiogram.types import BotCommand
# from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
#
# from modul.clientbot import shortcuts, strings
# from modul.clientbot.data.callback_datas import MainMenuCallbackData
# from modul.clientbot.handlers.chat_gpt_bot.shortcuts import get_info_db
# from modul.clientbot.handlers.kino_bot.handlers.bot import start_kino_bot
# from modul.clientbot.handlers.refs.handlers.bot import start_ref
# from modul.clientbot.keyboards import inline_kb, reply_kb
# from modul.clientbot.utils.exceptions import UserNotFound
# # from modul.clientbot.utils.order import paginate_orders
# from modul import models
# from modul.clientbot.data.states import Download
# # from modul.clientbot.handlers.anon.handlers.main import cabinet_text
#
# from modul.loader import client_bot_router, bot_session
# from aiogram.fsm.context import FSMContext
# import sys
# import traceback
#
# from django.db import transaction
# from asgiref.sync import sync_to_async
# from aiogram import Bot
#
# from modul.models import UserTG
#
#
# @sync_to_async
# @transaction.atomic
# def save_user(u, bot: Bot, link=None, inviter=None):
#     bot = models.Bot.objects.select_related("owner").filter(token=bot.token).first()
#     user = models.UserTG.objects.filter(uid=u.id).first()
#     current_ai_limit = 12
#     if not user:
#         user = models.UserTG.objects.create(
#             uid=u.id,
#             username=u.username,
#             first_name=u.first_name,
#             last_name=u.last_name,
#             user_link=link
#         )
#     else:
#         current_ai_limit = 0
#
#     client_user = models.ClientBotUser.objects.filter(uid=u.id, bot=bot).first()
#     if client_user:
#         return client_user
#
#     client_user = models.ClientBotUser.objects.create(
#         uid=u.id,
#         user=user,
#         bot=bot,
#         inviter=inviter,
#         current_ai_limit=current_ai_limit
#     )
#     return client_user
#
#
# async def start(message: Message, state: FSMContext, bot: Bot):
#     bot_db = await shortcuts.get_bot(bot)
#     uid = message.from_user.id
#     text = "Добро пожаловать, {hello}".format(hello=html.quote(message.from_user.full_name))
#     kwargs = {}
#
#     if shortcuts.have_one_module(bot_db, "download"):
#         text = ("🤖 Привет, {full_name}! Я бот-загрузчик.\r\n\r\n"
#                 "Я могу скачать фото/видео/аудио/файлы/архивы с *Youtube, Instagram, TikTok, Facebook, SoundCloud, Vimeo, Вконтакте, Twitter и 1000+ аудио/видео/файловых хостингов*. Просто пришли мне URL на публикацию с медиа или прямую ссылку на файл.").format(
#             full_name=message.from_user.full_name)
#         await state.set_state(Download.download)
#         kwargs['parse_mode'] = "Markdown"
#
#     elif shortcuts.have_one_module(bot_db, "refs"):
#         await start_ref(message)
#     elif shortcuts.have_one_module(bot_db, "kino"):
#         await start_kino_bot(message, state)
#         kwargs['parse_mode'] = "HTML"
#     elif shortcuts.have_one_module(bot_db, "chatgpt"):
#         builder = InlineKeyboardBuilder()
#         builder.button(text='☁ Чат с GPT-4', callback_data='chat_4')
#         builder.button(text='☁ Чат с GPT-3.5', callback_data='chat_3')
#         builder.button(text='🆘 Помощь', callback_data='helper')
#         builder.button(text='⚙️ Настройки', callback_data='settings')
#         builder.button(text='💸Заработать', callback_data='ref')
#         builder.adjust(2, 1, 1, 1, 1, 1, 2)
#         result = await get_info_db(uid)
#         print(result)
#         text = f'Привет {message.from_user.username}\nВаш баланс - {result[0][2]}'
#         kwargs['reply_markup'] = builder.as_markup()
#     else:
#         kwargs['reply_markup'] = await reply_kb.main_menu(uid, bot)
#
#     await message.answer(text, **kwargs)
#
# @sync_to_async
# def get_user(uid: int, username: str, first_name: str = None, last_name: str = None):
#     user = UserTG.objects.get_or_create(uid=uid, username=username, first_name=first_name, last_name=last_name)
#     return user
#
#
# def start_bot_client():
#     @client_bot_router.message(CommandStart())
#     async def on_start(message: Message, command: CommandObject, state: FSMContext, bot: Bot):
#         print("Start command received from", message.from_user.id)
#         try:
#             info = await get_user(uid=message.from_user.id,
#                                   username=message.from_user.username,
#                                   first_name=message.from_user.first_name if message.from_user.first_name else None,
#                                   last_name=message.from_user.last_name if message.from_user.last_name else None)
#
#             await state.clear()
#             commands = await bot.get_my_commands()
#             bot_commands = [
#                 BotCommand(command="/start", description="Меню"),
#             ]
#             print('command start')
#
#             if commands != bot_commands:
#                 await bot.set_my_commands(bot_commands)
#
#             referral = command.args
#             uid = message.from_user.id
#             user = await shortcuts.get_user(uid, bot)
#
#             if not user:
#                 if referral and referral.isdigit():
#                     inviter = await shortcuts.get_user(int(referral))
#                     if inviter:
#                         await shortcuts.increase_referral(inviter)
#                         with suppress(TelegramForbiddenError):
#                             user_link = html.link('реферал', f'tg://user?id={uid}')
#                             await bot.send_message(
#                                 chat_id=referral,
#                                 text=f"У вас новый {user_link}!"  # formatni to'g'ridan to'g'ri beramiz
#                             )
#                 else:
#                     inviter = None
#                 await save_user(u=message.from_user, inviter=inviter, bot=bot)
#
#             await start(message, state, bot)
#         except Exception as e:
#             print(f"Error in start handler: {e}")
#             raise
#
#
# @client_bot_router.message(CommandStart())
# # @flags.rate_limit(key="on_start")
# async def on_start(message: Message, command: CommandObject, state: FSMContext, bot: Bot):
#     print(message.from_user.id)
#     info = await get_user(uid=message.from_user.id, username=message.from_user.username,
#                           first_name=message.from_user.first_name if message.from_user.first_name else None,
#                           last_name=message.from_user.last_name if message.from_user.last_name else None)
#     await state.clear()
#     commands = await bot.get_my_commands()
#     bot_commands = [
#         BotCommand(command="/start", description="Меню"),
#     ]
#     print('command start')
#     if commands != bot_commands:
#         await bot.set_my_commands(bot_commands)
#     referral = command.args
#     uid = message.from_user.id
#     user = await shortcuts.get_user(uid, bot)
#
#     if not user:
#         if referral and referral.isdigit():
#             inviter = await shortcuts.get_user(int(referral))
#             if inviter:
#                 await shortcuts.increase_referral(inviter)
#                 with suppress(TelegramForbiddenError):
#                     user_link = html.link('реферал', f'tg://user?id={uid}')
#                     await bot.send_message(
#                         chat_id=referral,
#                         text=('new_referral').format(
#                             user_link=user_link,
#                         )
#                     )
#         else:
#             inviter = None
#         await save_user(u=message.from_user, inviter=inviter, bot=bot)
#     await start(message, state, bot)


# @client_bot_router.message(text=__("🌍 Поменять язык"))
# async def change_language(message: types.Message):
#     user = await shortcuts.get_base_user(message.from_user.id)
#     user.language_code = 'ru' if user.language_code == 'en' else 'en'
#     await user.save()
#     await message.answer(
#         _("Вы поменяли язык на {lang}").format(lang=("Русский" if user.language_code == 'ru' else "English")))


# @client_bot_router.message(text=__("💰 Баланс"))
# @flags.rate_limit(key="balance")
# async def balance_menu(message: Message):
#     user = await shortcuts.get_user(message.from_user.id)
#     await message.answer(_("💲 Ваш баланс: {balance}₽\n🏷 Ваш id: <code>{user_id}</code>").format(balance=user.balance,
#                                                                                                 user_id=message.from_user.id),
#                          reply_markup=inline_kb.balance_menu())


# @client_bot_router.message(text=__("✨ Список наших ботов"))
# @flags.rate_limit(key="our-bots")
# async def balance_menu(message: Message):
#     bot_db = await shortcuts.get_bot()
#     owner = await bot_db.owner
#     bots = await models.Bot.filter(owner=owner, unauthorized=False)
#     text = _("✨ Список наших ботов:\n")
#     for bot in bots:
#         try:
#             b = Bot(bot.token, bot_session)
#             info = await b.get_me()
#             text += f"🤖 @{bot.username} - {info.full_name}\n"
#         except Exception as e:
#             pass
#     await message.answer(text)


# @client_bot_router.message(text=__("📋 Мои заказы"))
# @flags.rate_limit(key="user_orders")
# async def user_orders(message: Message):
#     await Bot.get_current().send_chat_action(message.from_user.id, "typing")
#     try:
#         text, reply_markup = await paginate_orders(message.from_user.id)
#     except UserNotFound:
#         await save_user(message.from_user)
#         text, reply_markup = await paginate_orders(message.from_user.id)
#     if text:
#         await message.answer(text, reply_markup=reply_markup, disable_web_page_preview=True)
#     else:
#         await message.answer(_("⛔️ У вас еще нет заказов"))

#
# @client_bot_router.message(text=__("👤 Реферальная система"))
# @flags.rate_limit(key="partners")
# async def partners(message: Message):
#     username = (await Bot.get_current().get_me()).username
#     uid = message.from_user.id
#     await message.answer(
#         text=strings.PARTNERS_INFO.format(
#             await shortcuts.referral_count(uid),
#             await shortcuts.referral_balance(uid),
#             username,
#             uid
#         ),
#         reply_markup=inline_kb.transfer_keyboard()
#     )


# @client_bot_router.message(text=__("⭐️ Социальные сети"))
# @flags.rate_limit(key='social_networks')
# async def social_networks(message: Message):
#     await message.answer(
#         text=strings.CHOOSE_SOCIAL,
#         reply_markup=await inline_kb.social_networks()
#     )


# @client_bot_router.message(text=__("👮‍♂️ Связаться с администратором"))
# @client_bot_router.message(text=__("ℹ️ Информация"))
# @flags.rate_limit(key="information")
# async def information_menu(message: types.Message, bot: Bot):
#     bot_obj = await shortcuts.get_bot()
#     owner: models.MainBotUser = bot_obj.owner
#     try:
#         await message.answer(strings.INFO.format(username=f"@{bot_obj.username}"), reply_markup=inline_kb.info_menu(
#             support=bot_obj.support or owner.uid,
#             channel_link=bot_obj.news_channel
#         ))
#     except TelegramBadRequest as e:
#         if "BUTTON_USER_INVALID" in e.message:
#             await bot.send_message(owner.uid, _("⚠️ Измените ид поддержки бота. Текущий недействителен."))
#         try:
#             await message.answer(strings.INFO.format(username=f"@{bot_obj.username}"), reply_markup=inline_kb.info_menu(
#                 support=owner.uid,
#                 channel_link=bot_obj.news_channel
#             ))
#         except TelegramBadRequest:
#             await bot.send_message(owner.uid, _("Неправильный хост URL. Пожалуйста, измените ссылку на канал"))
#             await message.answer(strings.INFO.format(username=f"@{bot_obj.username}"), reply_markup=inline_kb.info_menu(
#                 support=owner.uid,
#             ))


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

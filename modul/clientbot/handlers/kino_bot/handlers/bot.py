import glob
import asyncio
import json
import subprocess
import tempfile
import time
import traceback
from contextlib import suppress
import shutil
from datetime import timedelta, datetime

import requests
from aiogram import Bot, F, html
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest
from aiogram.filters import Command, CommandStart, CommandObject, Filter, BaseFilter, command
from aiogram.fsm.context import FSMContext
from aiogram.filters.state import State, StatesGroup, StateFilter
from aiogram.methods import GetChat, CreateChatInviteLink, GetChatMember

from aiogram.types import CallbackQuery, Message, InlineKeyboardButton, InlineKeyboardMarkup, InlineQueryResultArticle, \
    InputTextMessageContent, InlineQuery, BotCommand, ReplyKeyboardRemove, URLInputFile, BufferedInputFile
from aiogram.utils.deep_linking import create_start_link
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from asgiref.sync import async_to_sync
from django.db import transaction
from django.utils import timezone
import re
# from modul.clientbot.handlers.davinci_bot import *
from yt_dlp import YoutubeDL

from modul import models
from modul.clientbot import shortcuts
from modul.clientbot.data.states import Download
from modul.clientbot.handlers.annon_bot.handlers.bot import check_channels, process_referral, check_if_already_referred
from modul.clientbot.handlers.annon_bot.keyboards.buttons import channels_in
from modul.clientbot.handlers.annon_bot.userservice import get_channels_for_check, check_user, add_user, get_user_by_id
from modul.clientbot.handlers.chat_gpt_bot.shortcuts import get_info_db
from modul.clientbot.handlers.kino_bot.shortcuts import *
from modul.clientbot.handlers.kino_bot.keyboards.kb import *
from modul.clientbot.handlers.kino_bot.api import *
from modul.clientbot.handlers.leomatch.data.state import LeomatchRegistration
from modul.clientbot.handlers.leomatch.handlers.start import bot_start, bot_start_cancel, bot_start_lets_leo

from modul.clientbot.handlers.leomatch.handlers.registration import bot_start_lets_leo
from modul.clientbot.handlers.leomatch.handlers.start import bot_start_cancel
# from modul.clientbot.handlers.leomatch.data.state import LeomatchRegistration
# from modul.clientbot.handlers.leomatch.handlers.registration import bot_start_lets_leo
# from modul.clientbot.handlers.leomatch.handlers.start import bot_start, bot_start_cancel


from modul.clientbot.handlers.refs.data.excel_converter import convert_to_excel
from modul.clientbot.handlers.refs.data.states import ChangeAdminInfo
from modul.clientbot.handlers.refs.handlers.bot import start_ref, check_user_in_specific_bot, add_user_safely, \
    process_referral_bonus
from modul.clientbot.handlers.refs.keyboards.buttons import main_menu_bt, main_menu_bt2, payments_action_in, \
    declined_in, accepted_in, imp_menu_in
from modul.clientbot.handlers.refs.shortcuts import plus_ref, plus_money, get_actual_price, get_all_wait_payment, \
    change_price, change_min_amount, get_actual_min_amount, status_declined, status_accepted, check_ban, \
    get_user_info_db, changebalance_db, addbalance_db, ban_unban_db, get_bot_user_info
from modul.clientbot.keyboards import reply_kb
from modul.clientbot.shortcuts import get_all_users, get_bot_by_username, get_bot_by_token, get_users, users_count, \
    executor
from modul.loader import client_bot_router, main_bot
from modul.models import UserTG, AdminInfo, User, ClientBotUser
from typing import Union, List, Dict
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

# class Download(StatesGroup):
#     download = State()


# Callback data
class FormatCallback(CallbackData, prefix="format"):
    index: int
    quality: str
    type: str

class KinoBotFilter(Filter):
    async def __call__(self, message: types.Message, bot: Bot) -> bool:
        bot_db = await shortcuts.get_bot(bot)
        return shortcuts.have_one_module(bot_db, "kino")

@sync_to_async
def get_channels_with_type_for_check():
    try:
        sponsor_channels = ChannelSponsor.objects.all()
        sponsor_list = [(str(c.chanel_id), '', 'sponsor') for c in sponsor_channels]
        system_channels = SystemChannel.objects.filter(is_active=True)
        system_list = [(str(c.channel_id), c.channel_url, 'system') for c in system_channels]

        all_channels = sponsor_list + system_list

        logger.info(f"Found sponsor channels: {len(sponsor_list)}, system channels: {len(system_list)}")
        return all_channels
    except Exception as e:
        logger.error(f"Error getting channels with type: {e}")
        return []


@sync_to_async
def remove_invalid_sponsor_channel(channel_id):
    try:
        ChannelSponsor.objects.filter(chanel_id=channel_id).delete()
        logger.info(f"Removed invalid sponsor channel {channel_id} from database")
    except Exception as e:
        logger.error(f"Error removing invalid sponsor channel {channel_id}: {e}")


@sync_to_async
def remove_sponsor_channel(channel_id):
    try:
        ChannelSponsor.objects.filter(chanel_id=channel_id).delete()
    except Exception as e:
        logger.error(f"Error removing sponsor channel {channel_id}: {e}")


async def check_subs(user_id: int, bot: Bot) -> bool:
    try:
        bot_db = await shortcuts.get_bot(bot)
        admin_id = bot_db.owner.uid
        if user_id == admin_id:
            return True

        channels_with_type = await get_channels_with_type_for_check()
        if not channels_with_type:
            return True

        for channel_id, channel_url, channel_type in channels_with_type:
            try:
                # System kanallarni FAQAT main bot orqali tekshirish
                if channel_type == 'system':
                    member = await main_bot.get_chat_member(chat_id=int(channel_id), user_id=user_id)
                    logger.info(f"System channel {channel_id} checked via main_bot: {member.status}")
                else:
                    # Sponsor kanallarni joriy bot orqali tekshirish
                    member = await bot.get_chat_member(chat_id=int(channel_id), user_id=user_id)

                if member.status in ['left', 'kicked']:
                    kb = await get_subs_kb(bot)
                    await bot.send_message(
                        chat_id=user_id,
                        text="<b>Чтобы воспользоваться ботом, необходимо подписаться на каналы:</b>",
                        reply_markup=kb,
                        parse_mode="HTML"
                    )
                    return False

            except Exception as e:
                logger.error(f"Error checking channel {channel_id} (type: {channel_type}): {e}")

                # Faqat sponsor kanallarni o'chirish
                if channel_type == 'sponsor':
                    await remove_sponsor_channel(channel_id)
                    logger.info(f"Removed invalid sponsor channel {channel_id}")
                else:
                    # System kanallar uchun HECH NARSA QILMASLIK - faqat log
                    logger.warning(f"System channel {channel_id} access error (ignoring): {e}")
                    # Continue - bu kanalni e'tiborsiz qoldirib davom etamiz

                continue

        return True

    except Exception as e:
        logger.error(f"General error in check_subs: {e}")
        return True  # Xato bo'lsa ham davom etishga ruxsat berish


@sync_to_async
def remove_sponsor_channel(channel_id):
    """Faqat sponsor kanallarni o'chirish"""
    try:
        ChannelSponsor.objects.filter(chanel_id=channel_id).delete()
    except Exception as e:
        logger.error(f"Error removing sponsor channel {channel_id}: {e}")


# @sync_to_async
# def remove_invalid_channel(channel_id):
#     try:
#         sponsor_deleted = ChannelSponsor.objects.filter(chanel_id=channel_id).delete()
#         if sponsor_deleted[0] > 0:
#             logger.info(f"Removed invalid sponsor channel {channel_id} from database")
#             return
#         system_updated = SystemChannel.objects.filter(channel_id=channel_id).update(is_active=False)
#         if system_updated > 0:
#             logger.warning(f"Deactivated invalid system channel {channel_id}")
#         else:
#             logger.warning(f"Channel {channel_id} not found in database")
#
#     except Exception as e:
#         logger.error(f"Error handling invalid channel {channel_id}: {e}")

async def get_subs_kb(bot: Bot) -> types.InlineKeyboardMarkup:
    channels = await get_all_channels_sponsors()
    kb = InlineKeyboardBuilder()

    for channel_id in channels:
        try:
            chat_info = await bot.get_chat(channel_id)
            invite_link = chat_info.invite_link
            if not invite_link:
                invite_link = (await bot.create_chat_invite_link(channel_id)).invite_link

            kb.button(text=f'{chat_info.title}', url=invite_link)
        except Exception as e:
            print(f"Error with channel {channel_id}: {e}")
            continue

    kb.button(
        text='✅ Проверить подписку',
        callback_data='check_subs'
    )

    kb.adjust(1)
    return kb.as_markup()


@sync_to_async
def remove_invalid_sponsor_channels(channel_ids):
    try:
        ChannelSponsor.objects.filter(chanel_id__in=channel_ids).delete()
    except Exception as e:
        logger.error(f"Error removing invalid sponsor channels: {e}")


async def notify_system_channel_errors(bot, user_id: int, errors: list):
    try:
        error_message = "⚠️ <b>Errors:</b>\n\n"
        for channel_id, channel_title, error in errors:
            channel_name = channel_title or f"channel {channel_id}"
            error_message += f"• <b>{channel_name}</b>\n"
            error_message += f"  <i>error: {error}</i>\n\n"
        error_message += "📞 <b>Произошла ошибка, обратитесь к администратору.</b>"
        # await bot.send_message(
        #     chat_id=user_id,
        #     text=error_message,
        #     parse_mode="HTML"
        # )
        logger.info(f"Notified user {user_id} about system channel errors")
    except Exception as e:
        logger.error(f"Error notifying user about system channel errors: {e}")


async def check_user_subscription(user_id: int, bot) -> tuple[bool, list]:
    channels = await get_channels_for_check()
    if not channels:
        return True, []
    not_subscribed = []
    invalid_channels_to_remove = []
    system_channel_errors = []
    for channel_id, channel_title, channel_type in channels:
        try:
            member = await bot.get_chat_member(chat_id=int(channel_id), user_id=user_id)
            if member.status in ['left', 'kicked']:
                not_subscribed.append((channel_id, channel_title))
        except Exception as e:
            logger.error(f"Error checking channel {channel_id}: {e}")

            if channel_type == 'sponsor':
                # Sponsor kanallarni o'chirish
                invalid_channels_to_remove.append(channel_id)
                logger.info(f"Removed invalid sponsor channel {channel_id} from database")
            elif channel_type == 'system':
                # System kanallar uchun foydalanuvchiga ko'rsatish
                system_channel_errors.append((channel_id, channel_title, str(e)))
                logger.error(f"System channel {channel_id} error: {e}")

    if invalid_channels_to_remove:
        await remove_invalid_sponsor_channels(invalid_channels_to_remove)

    if system_channel_errors:
        await notify_system_channel_errors(bot, user_id, system_channel_errors)

    return len(not_subscribed) == 0, not_subscribed

@client_bot_router.callback_query(lambda c: c.data == 'check_subs',KinoBotFilter())
async def check_subs_callback(callback: types.CallbackQuery, state: FSMContext):
    try:
        is_subscribed = await check_subs(callback.from_user.id, callback.bot)

        if is_subscribed:
            await callback.message.delete()
            await state.set_state(SearchFilmForm.query)
            await callback.message.answer(
                '<b>Отправьте название фильма / сериала / аниме</b>\n\n'
                'Не указывайте года, озвучки и т.д.\n\n'
                'Правильный пример: Ведьмак\n'
                'Неправильный пример: Ведьмак 2022',
                parse_mode="HTML",
                reply_markup=ReplyKeyboardRemove()
            )
        else:
            await callback.answer(
                "❌ Вы не подписаны на все каналы. Пожалуйста, подпишитесь!",
                show_alert=True
            )
    except Exception as e:
        logger.error(f"Error in check_subs_callback: {e}")
        await callback.answer(
            "Произошла ошибка при проверке подписки. Попробуйте позже.",
            show_alert=True
        )


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
        try:
            channel_data = await bot.get_chat(channel)
            kb.button(
                text=channel_data.title,
                callback_data=f'remove_channel|{channel}'
            )
        except TelegramBadRequest as e:
            logger.error(f"Channel not found or bot was removed: {channel}, Error: {e}")
            continue
        except Exception as e:
            logger.error(f"Error accessing channel {channel}: {e}")
            continue

    kb.button(text='Отменить', callback_data='cancel')
    kb.adjust(1)

    return kb.as_markup()

from aiogram.types import Message
from aiogram.exceptions import TelegramAPIError

async def send_message_to_users(bot, users, text):
    for user_id in users:
        try:
            await bot.send_message(chat_id=user_id, text=text)
        except TelegramAPIError as e:
            logger.warning(f"Не удалось отправить сообщение пользователю {user_id}: {e}")



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
    print('admin_send_message called')
    await state.set_state(SendMessagesForm.message)
    await call.message.edit_text('Отправьте сообщение для рассылки (текст, фото, видео и т.д.)', reply_markup=cancel_kb)


def extract_keyboard_from_message(message: types.Message) -> InlineKeyboardMarkup | None:
    """Habardan keyboard ni ajratib olish - CLIENT BOT VERSION"""
    try:
        if not hasattr(message, 'reply_markup') or message.reply_markup is None:
            logger.info("No reply_markup found in message")
            return None

        # reply_markup mavjud
        reply_markup = message.reply_markup
        logger.info(f"Found reply_markup: {type(reply_markup)}")

        # Inline keyboard ekanligini tekshiramiz
        if hasattr(reply_markup, 'inline_keyboard'):
            inline_keyboard = reply_markup.inline_keyboard
            logger.info(f"Found inline_keyboard with {len(inline_keyboard)} rows")

            # Yangi keyboard builder yaratamiz
            builder = InlineKeyboardBuilder()

            for row_idx, row in enumerate(inline_keyboard):
                row_buttons = []
                for btn_idx, btn in enumerate(row):
                    logger.info(f"Processing button [{row_idx}][{btn_idx}]: text='{btn.text}'")

                    # Button type ni aniqlash
                    if hasattr(btn, 'url') and btn.url:
                        logger.info(f"  - URL button: {btn.url}")
                        new_btn = InlineKeyboardButton(text=btn.text, url=btn.url)
                    elif hasattr(btn, 'callback_data') and btn.callback_data:
                        logger.info(f"  - Callback button: {btn.callback_data}")
                        new_btn = InlineKeyboardButton(text=btn.text, callback_data=btn.callback_data)
                    elif hasattr(btn, 'switch_inline_query') and btn.switch_inline_query is not None:
                        new_btn = InlineKeyboardButton(text=btn.text, switch_inline_query=btn.switch_inline_query)
                        logger.info(f"  - Switch inline query button")
                    elif hasattr(btn,
                                 'switch_inline_query_current_chat') and btn.switch_inline_query_current_chat is not None:
                        new_btn = InlineKeyboardButton(text=btn.text,
                                                       switch_inline_query_current_chat=btn.switch_inline_query_current_chat)
                        logger.info(f"  - Switch inline query current chat button")
                    elif hasattr(btn, 'web_app') and btn.web_app:
                        new_btn = InlineKeyboardButton(text=btn.text, web_app=btn.web_app)
                        logger.info(f"  - Web app button")
                    elif hasattr(btn, 'login_url') and btn.login_url:
                        new_btn = InlineKeyboardButton(text=btn.text, login_url=btn.login_url)
                        logger.info(f"  - Login URL button")
                    else:
                        # Default - callback button
                        callback_data = f"broadcast_btn_{row_idx}_{btn_idx}"
                        new_btn = InlineKeyboardButton(text=btn.text, callback_data=callback_data)
                        logger.info(f"  - Default callback button: {callback_data}")

                    row_buttons.append(new_btn)

                # Row qo'shish
                if row_buttons:
                    builder.row(*row_buttons)

            result_keyboard = builder.as_markup()
            logger.info(f"Successfully created keyboard with {len(result_keyboard.inline_keyboard)} rows")
            return result_keyboard

        else:
            logger.info("reply_markup does not have inline_keyboard")
            return None

    except Exception as e:
        logger.error(f"Error extracting keyboard: {e}")
        return None


def log_message_structure(message: types.Message):
    """Habar strukturasini JSON formatda log qilish - CLIENT BOT VERSION"""
    try:
        debug_data = {
            "message_id": message.message_id,
            "content_type": message.content_type,
            "text": getattr(message, 'text', None),
            "caption": getattr(message, 'caption', None),
            "has_reply_markup": hasattr(message, 'reply_markup') and message.reply_markup is not None
        }

        if hasattr(message, 'reply_markup') and message.reply_markup:
            debug_data["reply_markup"] = {
                "type": type(message.reply_markup).__name__,
                "has_inline_keyboard": hasattr(message.reply_markup, 'inline_keyboard')
            }

            if hasattr(message.reply_markup, 'inline_keyboard'):
                keyboard_structure = []
                for row in message.reply_markup.inline_keyboard:
                    row_structure = []
                    for btn in row:
                        btn_info = {"text": btn.text}
                        if hasattr(btn, 'url') and btn.url:
                            btn_info["url"] = btn.url
                        if hasattr(btn, 'callback_data') and btn.callback_data:
                            btn_info["callback_data"] = btn.callback_data
                        row_structure.append(btn_info)
                    keyboard_structure.append(row_structure)
                debug_data["reply_markup"]["keyboard_structure"] = keyboard_structure

        logger.info(f"CLIENT BOT MESSAGE STRUCTURE: {json.dumps(debug_data, indent=2, ensure_ascii=False)}")

    except Exception as e:
        logger.error(f"Error logging message structure: {e}")


async def send_message_with_keyboard(bot, user_id: int, message: types.Message, keyboard: InlineKeyboardMarkup = None):
    """Universal message sender with keyboard support"""
    try:
        if message.content_type == "text":
            # Текстовое сообщение
            return await bot.send_message(
                chat_id=user_id,
                text=message.text,
                entities=getattr(message, 'entities', None),
                reply_markup=keyboard,
                parse_mode=None
            )

        elif message.content_type == "photo":
            # Фото
            return await bot.send_photo(
                chat_id=user_id,
                photo=message.photo[-1].file_id,
                caption=getattr(message, 'caption', None),
                caption_entities=getattr(message, 'caption_entities', None),
                reply_markup=keyboard
            )

        elif message.content_type == "video":
            # Видео
            return await bot.send_video(
                chat_id=user_id,
                video=message.video.file_id,
                caption=getattr(message, 'caption', None),
                caption_entities=getattr(message, 'caption_entities', None),
                reply_markup=keyboard
            )

        elif message.content_type == "document":
            # Документ
            return await bot.send_document(
                chat_id=user_id,
                document=message.document.file_id,
                caption=getattr(message, 'caption', None),
                caption_entities=getattr(message, 'caption_entities', None),
                reply_markup=keyboard
            )

        elif message.content_type == "audio":
            # Аудио
            return await bot.send_audio(
                chat_id=user_id,
                audio=message.audio.file_id,
                caption=getattr(message, 'caption', None),
                caption_entities=getattr(message, 'caption_entities', None),
                reply_markup=keyboard
            )

        elif message.content_type == "voice":
            # Голосовое сообщение
            return await bot.send_voice(
                chat_id=user_id,
                voice=message.voice.file_id,
                caption=getattr(message, 'caption', None),
                caption_entities=getattr(message, 'caption_entities', None),
                reply_markup=keyboard
            )

        elif message.content_type == "video_note":
            # Кружок (video note)
            return await bot.send_video_note(
                chat_id=user_id,
                video_note=message.video_note.file_id,
                reply_markup=keyboard
            )

        elif message.content_type == "animation":
            # GIF/анимация
            return await bot.send_animation(
                chat_id=user_id,
                animation=message.animation.file_id,
                caption=getattr(message, 'caption', None),
                caption_entities=getattr(message, 'caption_entities', None),
                reply_markup=keyboard
            )

        elif message.content_type == "sticker":
            # Стикер
            return await bot.send_sticker(
                chat_id=user_id,
                sticker=message.sticker.file_id,
                reply_markup=keyboard
            )

        elif message.content_type == "location":
            # Местоположение
            return await bot.send_location(
                chat_id=user_id,
                latitude=message.location.latitude,
                longitude=message.location.longitude,
                reply_markup=keyboard
            )

        elif message.content_type == "contact":
            # Контакт
            return await bot.send_contact(
                chat_id=user_id,
                phone_number=message.contact.phone_number,
                first_name=message.contact.first_name,
                last_name=getattr(message.contact, 'last_name', None),
                reply_markup=keyboard
            )

        elif message.content_type == "poll":
            # Опрос
            return await bot.send_poll(
                chat_id=user_id,
                question=message.poll.question,
                options=[option.text for option in message.poll.options],
                is_anonymous=message.poll.is_anonymous,
                type=message.poll.type,
                allows_multiple_answers=getattr(message.poll, 'allows_multiple_answers', False),
                reply_markup=keyboard
            )
        else:
            # Неподдерживаемый тип - fallback
            return await bot.send_message(
                chat_id=user_id,
                text=f"📎 Медиа сообщение\n\nТип: {message.content_type.upper()}",
                reply_markup=keyboard
            )

    except Exception as e:
        logger.error(f"Error sending message to {user_id}: {e}")
        raise e


@client_bot_router.message(SendMessagesForm.message)
async def admin_send_message_msg(message: types.Message, state: FSMContext):
    await state.clear()

    try:
        print(f"📤 [CLIENT-BROADCAST] Broadcast started by user: {message.from_user.id}")

        # Debug: habar strukturasini log qilish
        log_message_structure(message)

        bot_db = await shortcuts.get_bot(message.bot)
        print(f"🤖 [CLIENT-BROADCAST] Bot found: {bot_db}")

        if not bot_db:
            await message.answer("❌ Bot ma'lumotlari topilmadi!")
            return

        users = await get_all_users(bot_db)
        print(f"👥 [CLIENT-BROADCAST] Users found: {len(users)} - {users}")

        if not users:
            await message.answer("❌ Нет пользователей для рассылки.")
            return

        # ✅ Professional keyboard extraction (COPY_MESSAGE ISHLATMAYMIZ!)
        extracted_keyboard = extract_keyboard_from_message(message)
        has_buttons = extracted_keyboard is not None
        button_count = 0

        if has_buttons:
            button_count = sum(len(row) for row in extracted_keyboard.inline_keyboard)
            print(f"🔘 [CLIENT-BROADCAST] Extracted {button_count} buttons from message")
        else:
            print(f"📝 [CLIENT-BROADCAST] No buttons found in message")

        success_count = 0
        fail_count = 0
        total_users = len(users)

        # Progress xabari
        keyboard_status = f"с кнопками ({button_count} шт.)" if has_buttons else "без кнопок"
        progress_msg = await message.answer(
            f"🚀 Рассылка началась...\n\n"
            f"📊 Статистика:\n"
            f"👥 Всего пользователей: {total_users}\n"
            f"📝 Тип сообщения: {message.content_type} ({keyboard_status})\n"
            f"✅ Отправлено: 0\n"
            f"❌ Ошибок: 0\n"
            f"📈 Прогресс: 0%"
        )

        # Рассылка по пользователям
        update_interval = 25  # Каждые 25 пользователей обновляем прогресс
        last_update = 0

        for idx, user_id in enumerate(users, 1):
            try:
                print(f"📨 [CLIENT-BROADCAST] Sending to user: {user_id} ({idx}/{total_users})")

                # ✅ НЕ ИСПОЛЬЗУЕМ copy_message - ИСПОЛЬЗУЕМ НАШИ ФУНКЦИИ!
                result = await send_message_with_keyboard(
                    bot=message.bot,
                    user_id=user_id,
                    message=message,
                    keyboard=extracted_keyboard
                )

                if result and hasattr(result, 'message_id'):
                    success_count += 1
                    if idx <= 5:  # Первые 5 пользователей
                        print(
                            f"✅ [CLIENT-BROADCAST] SUCCESS: User {user_id} received message {result.message_id} ({keyboard_status})")
                else:
                    fail_count += 1
                    print(f"❌ [CLIENT-BROADCAST] FAILED: No valid result for user {user_id}")

                # Progress update
                if idx - last_update >= update_interval or idx == total_users:
                    try:
                        progress_percent = (idx / total_users * 100)
                        await progress_msg.edit_text(
                            f"🚀 Рассылка в процессе...\n\n"
                            f"📊 Статистика:\n"
                            f"👥 Всего пользователей: {total_users}\n"
                            f"📝 Тип сообщения: {message.content_type} ({keyboard_status})\n"
                            f"✅ Отправлено: {success_count}\n"
                            f"❌ Ошибок: {fail_count}\n"
                            f"📈 Прогресс: {idx}/{total_users} ({progress_percent:.1f}%)"
                        )
                        last_update = idx
                    except:
                        pass

                # Flood control
                await asyncio.sleep(0.05)  # 50ms задержка между сообщениями

            except Exception as e:
                fail_count += 1
                error_msg = str(e).lower()

                print(f"❌ [CLIENT-BROADCAST] Error sending to {user_id}: {e}")
                logger.error(f"Ошибка при отправке сообщения пользователю {user_id}: {e}")

                # Обработка flood control
                if "flood" in error_msg or "too many" in error_msg:
                    print(f"⏸️ [CLIENT-BROADCAST] Flood control triggered, sleeping...")
                    await asyncio.sleep(1)

        # Удаляем progress сообщение
        try:
            await progress_msg.delete()
        except:
            pass

        # ✅ Финальная статистика
        success_rate = (success_count / total_users * 100) if total_users > 0 else 0

        result_text = f"""
📊 <b>Рассылка завершена!</b>

📈 <b>Результат:</b>
👥 Всего пользователей: {total_users}
✅ Успешно отправлено: {success_count}
❌ Ошибок: {fail_count}
📊 Успешность: {success_rate:.1f}%

🤖 <b>Детали:</b>
📝 Тип сообщения: {message.content_type}
{f'🔘 Кнопки: {button_count} шт.' if has_buttons else '📝 Без кнопок'}
🏷️ Бот: @{bot_db.username if bot_db.username else 'Unknown'}

💡 <i>Возможности рассылки:</i>
• ✅ Извлечение кнопок из любых сообщений
• ✅ Поддержка всех типов медиа
• ✅ Сохранение форматирования
• ✅ Flood control защита
• ✅ Резервные механизмы отправки
"""

        await message.answer(result_text, parse_mode="HTML")

        print(f"📊 [CLIENT-BROADCAST] Broadcast completed: {success_count}/{total_users} " +
              f"({'with ' + str(button_count) + ' buttons' if has_buttons else 'without buttons'})")

    except Exception as e:
        print(f"❌ [CLIENT-BROADCAST] Global broadcast error: {e}")
        logger.error(f"[CLIENT-BROADCAST] Global broadcast error: {e}")
        await message.answer(
            f"❌ Критическая ошибка во время рассылки!\n\n"
            f"Ошибка: {str(e)}\n\n"
            f"Обратитесь к администратору."
        )


# Qo'shimcha: Maxsus formatli xabar yuborish uchun helper funksiya
async def send_formatted_message(bot, chat_id: int, message: types.Message):
    """
    Xabarni barcha format va buttonlar bilan yuborish
    """
    try:
        # copy_message eng to'g'ri variant
        return await bot.copy_message(
            chat_id=chat_id,
            from_chat_id=message.chat.id,
            message_id=message.message_id
        )
    except Exception as e:
        # Fallback: manual formatting bilan
        try:
            if message.text:
                return await bot.send_message(
                    chat_id=chat_id,
                    text=message.text,
                    entities=message.entities,
                    reply_markup=message.reply_markup
                )
            elif message.photo:
                return await bot.send_photo(
                    chat_id=chat_id,
                    photo=message.photo[-1].file_id,
                    caption=message.caption,
                    caption_entities=message.caption_entities,
                    reply_markup=message.reply_markup
                )
            elif message.video:
                return await bot.send_video(
                    chat_id=chat_id,
                    video=message.video.file_id,
                    caption=message.caption,
                    caption_entities=message.caption_entities,
                    reply_markup=message.reply_markup
                )
            elif message.document:
                return await bot.send_document(
                    chat_id=chat_id,
                    document=message.document.file_id,
                    caption=message.caption,
                    caption_entities=message.caption_entities,
                    reply_markup=message.reply_markup
                )
            else:
                # Oxirgi imkoniyat sifatida copy_message
                return await bot.copy_message(
                    chat_id=chat_id,
                    from_chat_id=message.chat.id,
                    message_id=message.message_id
                )
        except Exception as fallback_error:
            print(f"❌ Fallback error: {fallback_error}")
            raise fallback_error

@client_bot_router.callback_query(F.data == "imp", AdminFilter(), StateFilter('*'))
async def manage_user_handler(call: CallbackQuery, state: FSMContext):
    await call.message.edit_text(
        "Введите ID пользователя",
        reply_markup=cancel_kb
    )
    await state.set_state(ChangeAdminInfo.imp)


@client_bot_router.callback_query(lambda call: "accept_" in call.data, AdminFilter(), StateFilter('*'))
async def acception(query: CallbackQuery):
    id_of_wa = int(query.data.replace("accept_", ""))
    user_info = await status_accepted(id_of_wa)

    if user_info:
        await query.message.edit_reply_markup(reply_markup=await accepted_in())
        await query.bot.send_message(
            user_info[0],
            f"Ваша завявка на выплату {user_info[1]} была подтверждена ✅"
        )
    else:
        await query.answer("Ошибка: Не удалось подтвердить заявку", show_alert=True)


@client_bot_router.callback_query(lambda call: "decline_" in call.data, AdminFilter(), StateFilter('*'))
async def declined(query: CallbackQuery):
    id_of_wa = int(query.data.replace("decline_", ""))
    user_info = await status_declined(id_of_wa)

    if user_info:
        await query.message.edit_reply_markup(reply_markup=await declined_in())
        await query.bot.send_message(
            user_info[0],
            f"Ваша завявка на выплату {user_info[1]} была отклонена❌"
        )
    else:
        await query.answer("Ошибка: Не удалось отклонить заявку", show_alert=True)


@client_bot_router.message(ChangeAdminInfo.imp)
async def get_user_info_handler(message: Message, state: FSMContext):
    if message.text == "❌Отменить":
        await message.answer("🚫 Действие отменено", reply_markup=await main_menu_bt())
        await state.clear()
        return

    if message.text.isdigit():
        user_id = int(message.text)
        try:
            status = await check_ban(user_id)
            user_info = await get_user_info_db(user_id)
            bot_user_info = await get_bot_user_info(message.from_user.id, message.bot.token)
            bot_balance = bot_user_info[0] if bot_user_info else 0
            bot_referrals = bot_user_info[1] if bot_user_info else 0
            if user_info:
                user_name = "@"
                try:
                    chat = await message.bot.get_chat(user_info[1])
                    user_name += f"{chat.username}"
                except:
                    pass
                await message.answer(
                    f"📝Имя юзера: {user_info[0]} {user_name}\n"
                    f"🆔ID юзера: <code>{user_info[1]}</code>\n"
                    f"👥 Пригласил: {user_info[3]}\n"
                    f"💳 Баланс юзера: {bot_balance}₽ \n"
                    f"📤 Вывел: {user_info[5]} руб.",
                    parse_mode="html",
                    reply_markup=await imp_menu_in(user_info[1], status)
                )
                await state.clear()
            else:
                await message.answer("Юзер не найден", reply_markup=await main_menu_bt())
                await state.clear()
        except Exception as e:
            await message.answer(f"🚫 Не удалось найти юзера. Ошибка: {e}", reply_markup=await main_menu_bt())
            await state.clear()
    else:
        await message.answer("️️❗Ошибка! Введите числовой ID пользователя.", reply_markup=await main_menu_bt())
        await state.clear()
@client_bot_router.callback_query(F.data.startswith("changerefs_"), AdminFilter(), StateFilter('*'))
async def change_refs_handler(call: CallbackQuery, state: FSMContext):
    user_id = int(call.data.replace("changerefs_", ""))
    await call.message.edit_text(
        "Введите новое количество рефералов:",
        reply_markup=cancel_kb
    )
    await state.set_state(ChangeAdminInfo.change_refs)
    await state.update_data(user_id=user_id)
@client_bot_router.message(ChangeAdminInfo.change_refs)
async def set_new_refs_count(message: Message, state: FSMContext):
    data = await state.get_data()
    user_id = data.get("user_id")
    if message.text == "❌Отменить":
        await message.answer("🚫 Действие отменено", reply_markup=await main_menu_bt())
        await state.clear()
        return

    if message.text.isdigit():
        new_refs_count = int(message.text)

        try:
            @sync_to_async
            @transaction.atomic
            def update_refs():
                user = UserTG.objects.select_for_update().filter(uid=user_id).first()
                if user:
                    user.refs = new_refs_count
                    user.save()
                    return True
                return False

            updated = await update_refs()

            if updated:
                await message.answer(f"Количество рефералов для пользователя {user_id} успешно обновлено на {new_refs_count}.", reply_markup=await main_menu_bt())
            else:
                await message.answer(f"🚫 Пользователь с ID {user_id} не найден.", reply_markup=await main_menu_bt())

        except Exception as e:
            logger.error(f"Error updating refs count for user {user_id}: {e}")
            await message.answer("🚫 Не удалось обновить количество рефералов.", reply_markup=await main_menu_bt())
    else:
        await message.answer("❗ Введите корректное числовое значение.")

    await state.clear()


@client_bot_router.callback_query(F.data == 'all_payments', AdminFilter(), StateFilter('*'))
async def all_payments_handler(call: CallbackQuery):
    active_payments = await get_all_wait_payment()

    if active_payments:
        for payment in active_payments:
            print(payment)
            await call.message.answer(
                text=f"<b>Заявка на выплату № {payment[0]}</b>\n"  # payment[0] - id
                     f"ID пользователя: <code>{payment[1]}</code>\n"  # payment[1] - user_id
                     f"Сумма: {payment[2]} руб.\n"  # payment[2] - amount
                     f"Карта: <code>{payment[3]}</code>\n"  # payment[3] - card
                     f"Банк: {payment[4]}",  # payment[4] - bank
                parse_mode="HTML",
                reply_markup=await payments_action_in(payment[0])  # payment[0] - id
            )
    else:
        await call.message.edit_text('Нет заявок на выплату.', reply_markup=admin_kb)


@client_bot_router.message(ChangeAdminInfo.get_amount)
async def get_new_amount_handler(message: Message, state: FSMContext):
    if message.text == "❌Отменить":
        await message.answer("🚫 Действие отменено", reply_markup=await main_menu_bt())
        await state.clear()
        return

    try:
        new_reward = float(message.text)
        # Передаем токен текущего бота
        success = await change_price(new_reward, message.bot.token)

        if success:
            await message.answer(
                f"Награда за реферала успешно изменена на {new_reward:.2f} руб.",
                reply_markup=await main_menu_bt()
            )
        else:
            await message.answer(
                "🚫 Не удалось изменить награду за реферала.",
                reply_markup=await main_menu_bt()
            )
        await state.clear()

    except ValueError:
        await message.answer("❗ Введите корректное числовое значение.")
    except Exception as e:
        logger.error(f"Ошибка при обновлении награды за реферала: {e}")
        await message.answer("🚫 Не удалось изменить награду за реферала.", reply_markup=await main_menu_bt())
        await state.clear()




@client_bot_router.callback_query(F.data.startswith("changebalance_"), AdminFilter(), StateFilter('*'))
async def change_balance_handler(call: CallbackQuery, state: FSMContext):
    id_of_user = int(call.data.replace("changebalance_", ""))
    await call.message.edit_text(
        "Введите новую сумму баланса. Для нецелых чисел используйте точку, а не запятую.",
        reply_markup=cancel_kb
    )
    await state.set_state(ChangeAdminInfo.change_balance)
    await state.update_data(user_id=id_of_user)

@client_bot_router.callback_query(F.data == 'change_money', AdminFilter(), StateFilter('*'))
async def change_money_handler(call: CallbackQuery, state: FSMContext):
    await state.set_state(ChangeAdminInfo.get_amount)
    await call.message.edit_text(
        'Введите новую награду за рефералов:',
        reply_markup=cancel_kb
    )
    await state.set_state(ChangeAdminInfo.get_amount)


@client_bot_router.callback_query(F.data == "change_min", AdminFilter(), StateFilter('*'))
async def change_min_handler(call: CallbackQuery, state: FSMContext):
    edited_message = await call.message.edit_text(
        "Введите новую минимальную выплату:",
        reply_markup=cancel_kb
    )
    await state.set_state(ChangeAdminInfo.get_min)
    await state.update_data(edit_msg=edited_message)


@client_bot_router.message(ChangeAdminInfo.get_min)
async def get_new_min_handler(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    edit_msg = data.get('edit_msg')

    if message.text == "❌Отменить":
        await message.delete()
        if edit_msg:
            await edit_msg.delete()
        await state.clear()
        await start(message, state, bot)
        return

    try:
        new_min_payout = float(message.text)

        # Hech qanday cheklov yo'q - 0 va barcha musbat qiymatlar qabul qilinadi

        logger.info(f"Yangi min_amount: {new_min_payout}")

        success = await change_min_amount(new_min_payout, bot_token=bot.token)



        await message.delete()
        if edit_msg:
            await edit_msg.delete()

        if success:
            # Natijani ko'rsatish uchun yangilangan qiymatni olish
            @sync_to_async
            def get_updated_amount():
                try:
                    admin_info = AdminInfo.objects.filter(bot_token=bot.token).first()
                    if not admin_info:
                        admin_info = AdminInfo.objects.first()
                    return admin_info.min_amount if admin_info else new_min_payout
                except:
                    return new_min_payout

            current_amount = await get_updated_amount()

            # 0 bo'lganda maxsus xabar
            if current_amount == 0:
                await message.answer(
                    f"✅ Минимальная сумма вывода установлена на {current_amount:.1f} руб.\n"
                    f"💡 Теперь пользователи могут выводить любую сумму."
                )
            else:
                await message.answer(
                    f"✅ Минимальная сумма вывода успешно изменена на {current_amount:.1f} руб."
                )
        else:
            await message.answer(
                "🚫 Не удалось изменить минимальную сумму вывода.\n"
                "Проверьте логи или обратитесь к разработчику."
            )

        await state.clear()
        await start(message, state, bot)

    except ValueError:
        await message.answer("❗ Введите корректное числовое значение.")
    except Exception as e:
        logger.error(f"Handler error: {e}")
        await message.answer("🚫 Произошла ошибка.")
        await state.clear()
        await start(message, state, bot)




@client_bot_router.callback_query(F.data.startswith("ban_"), AdminFilter(), StateFilter('*'))
async def ban_user_handler(call: CallbackQuery):
    user_id = int(call.data.replace("ban_", ""))
    ban_unban_db(id=user_id, bool=True)
    await call.message.edit_reply_markup(reply_markup=await imp_menu_in(user_id, True))


@client_bot_router.callback_query(F.data.startswith("razb_"), AdminFilter(), StateFilter('*'))
async def unban_user_handler(call: CallbackQuery):
    user_id = int(call.data.replace("razb_", ""))
    ban_unban_db(id=user_id, bool=False)
    await call.message.edit_reply_markup(reply_markup=await imp_menu_in(user_id, False))


@client_bot_router.callback_query(F.data.startswith("addbalance_"), AdminFilter(), StateFilter('*'))
async def add_balance_handler(call: CallbackQuery, state: FSMContext):
    user_id = int(call.data.replace("addbalance_", ""))
    await call.message.edit_text(
        "Введите сумму для добавления к балансу. Для дробных чисел используйте точку.",
        reply_markup=cancel_kb
    )
    await state.set_state(ChangeAdminInfo.add_balance)
    await state.update_data(user_id=user_id)


@client_bot_router.message(ChangeAdminInfo.add_balance)
async def process_add_balance(message: Message, state: FSMContext):
    if message.text == "❌Отменить":
        await message.answer("🚫 Действие отменено", reply_markup=await main_menu_bt())
        await state.clear()
        return

    try:
        amount = float(message.text)
        data = await state.get_data()
        await addbalance_db(data["user_id"], amount)
        await message.answer(f"Баланс успешно пополнен на {amount} руб.", reply_markup=await main_menu_bt())
        await state.clear()
    except ValueError:
        await message.answer("❗ Введите корректное числовое значение.")
    except Exception as e:
        await message.answer(f"🚫 Не удалось изменить баланс. Ошибка: {e}", reply_markup=await main_menu_bt())
        await state.clear()


@client_bot_router.callback_query(F.data.startswith("changebalance_"), AdminFilter(), StateFilter('*'))
async def change_balance_handler(call: CallbackQuery, state: FSMContext):
    user_id = int(call.data.replace("changebalance_", ""))
    await call.message.edit_text(
        "Введите новую сумму баланса. Для дробных чисел используйте точку.",
        reply_markup=cancel_kb
    )
    await state.set_state(ChangeAdminInfo.change_balance)
    await state.update_data(user_id=user_id)


@client_bot_router.message(ChangeAdminInfo.change_balance)
async def process_change_balance(message: Message, state: FSMContext):
    if message.text == "❌Отменить":
        await message.answer("🚫 Действие отменено", reply_markup=await main_menu_bt())
        await state.clear()
        return

    try:
        new_balance = float(message.text)
        data = await state.get_data()
        await changebalance_db(data["user_id"], new_balance)
        await message.answer(f"Баланс успешно изменен на {new_balance} руб.", reply_markup=await main_menu_bt())
        await state.clear()
    except ValueError:
        await message.answer("❗ Введите корректное числовое значение.")
    except Exception as e:
        await message.answer(f"🚫 Не удалось изменить баланс. Ошибка: {e}", reply_markup=await main_menu_bt())
        await state.clear()


@client_bot_router.callback_query(F.data.startswith("showrefs_"), AdminFilter(), StateFilter('*'))
async def show_refs_handler(call: CallbackQuery):
    user_id = int(call.data.replace("showrefs_", ""))
    try:
        file_data, filename = await convert_to_excel(user_id, call.bot.token)
        document = BufferedInputFile(file_data, filename=filename)
        await call.message.answer_document(document)
    except Exception as e:
        await call.message.answer(f"🚫 Произошла ошибка при создании файла: {e}")


@client_bot_router.callback_query(F.data == 'admin_get_stats', AdminFilter(), StateFilter('*'))
async def admin_get_stats(call: CallbackQuery):
    print('stats called')
    try:
        bot_token = call.bot.token
        print(f"Bot token: {bot_token}")

        bot_db = await get_bot_by_token(bot_token)
        print(f"Bot DB object: {bot_db}")

        if bot_db:
            @sync_to_async
            def count_bot_users(bot_id):
                try:
                    return models.ClientBotUser.objects.filter(bot_id=bot_id).count()
                except Exception as e:
                    logger.error(f"Error counting bot users: {e}")
                    return 0

            total_users = await count_bot_users(bot_db.id)
            print(f"Users count for this bot: {total_users}")

            new_text = f'<b>Количество пользователей в боте:</b> {total_users}'

            try:
                await call.message.edit_text(
                    text=new_text,
                    reply_markup=admin_kb,
                    parse_mode='HTML'
                )
            except TelegramBadRequest as e:
                if "message is not modified" in str(e):
                    await call.answer("Статистика актуальна")
                else:
                    raise

        else:
            logger.error(f"Bot not found in database for token: {bot_token}")
            await call.answer("Бот не найден в базе данных")

    except Exception as e:
        logger.error(f"Ошибка получения статистики: {e}")
        logger.error(f"Full error traceback: {traceback.format_exc()}")
        await call.answer("Ошибка при получении статистики")



@client_bot_router.callback_query(F.data == 'cancel', StateFilter('*'))
async def cancel(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_text('Отменено')


@client_bot_router.callback_query(F.data == 'admin_delete_channel', AdminFilter(), StateFilter('*'))
async def admin_delete_channel(call: CallbackQuery, bot: Bot):
    channels = await get_all_channels_sponsors()
    kb = await get_remove_channel_sponsor_kb(channels, bot)
    await call.message.edit_text('Выберите канал для удаления', reply_markup=kb)


@client_bot_router.callback_query(F.data.contains('remove_channel'), AdminFilter(), StateFilter('*'))
async def remove_channel(call: CallbackQuery, bot: Bot):
    channel_id = int(call.data.split('|')[-1])
    try:
        await remove_channel_sponsor(channel_id)
        await call.message.edit_text('Канал был удален!', reply_markup=admin_kb)

        logger.info(f"Kanal muvaffaqiyatli o‘chirildi: {channel_id}")
    except Exception as e:
        logger.error(f"Kanalni o‘chirishda xatolik: {e}")
        await call.message.answer("Произошла ошибка при удалении канала.")



@client_bot_router.callback_query(F.data == 'admin_add_channel', AdminFilter(), StateFilter('*'))
async def admin_add_channel(call: CallbackQuery, state: FSMContext):
    await state.set_state(AddChannelSponsorForm.channel)
    await call.message.edit_text(
        '📢 Для добавления канала:\n\n'
        '1️⃣ Перейдите в канал\n'
        '2️⃣ Найдите любое сообщение в канале\n'
        '3️⃣ Переслать это сообщение мне\n\n'
        '⚠️ Важно: Бот должен быть администратором канала!',
        reply_markup=cancel_kb
    )


from enum import Enum
from typing import Optional, List, Union
from pydantic import BaseModel


# Define ReactionType enum to include all possible types
class ReactionTypeType(str, Enum):
    EMOJI = "emoji"
    CUSTOM_EMOJI = "custom_emoji"
    PAID = "paid"


# Base class for all reaction types
class ReactionTypeBase(BaseModel):
    type: ReactionTypeType


# Specific reaction type models
class ReactionTypeEmoji(ReactionTypeBase):
    type: ReactionTypeType = ReactionTypeType.EMOJI
    emoji: str


class ReactionTypeCustomEmoji(ReactionTypeBase):
    type: ReactionTypeType = ReactionTypeType.CUSTOM_EMOJI
    custom_emoji_id: str


class ReactionTypePaid(ReactionTypeBase):
    type: ReactionTypeType = ReactionTypeType.PAID


# Union type for all possible reactions
ReactionType = Union[ReactionTypeEmoji, ReactionTypeCustomEmoji, ReactionTypePaid]


class ChatInfo(BaseModel):
    id: int
    title: str
    type: str
    description: Optional[str] = None
    invite_link: Optional[str] = None
    has_visible_history: Optional[bool] = None
    can_send_paid_media: Optional[bool] = None
    available_reactions: Optional[List[ReactionType]] = None
    max_reaction_count: Optional[int] = None
    accent_color_id: Optional[int] = None

from aiogram import F

@client_bot_router.message(F.text == "🔙Назад в меню")
async def back_to_main_menu(message: Message, state: FSMContext, bot: Bot):
    await start(message, state, bot)


@client_bot_router.message(AddChannelSponsorForm.channel)
async def admin_add_channel_msg(message: Message, state: FSMContext):
    print(f"DEBUG: admin_add_channel_msg called")
    print(f"DEBUG: Forward from: {message.forward_from_chat}")

    try:
        # Forward message tekshirish
        if not message.forward_from_chat:
            await message.answer(
                "❌ Пожалуйста, перешлите сообщение из канала",
                reply_markup=cancel_kb
            )
            return

        channel_id = message.forward_from_chat.id

        # Kanal type tekshirish
        if message.forward_from_chat.type != 'channel':
            await message.answer(
                "❌ Это не канал! Перешлите сообщение из канала.",
                reply_markup=cancel_kb
            )
            return

        print(f"DEBUG: Channel ID: {channel_id}")

        # Bot obyekti
        bot = message.bot

        # ✅ TO'G'RI aiogram metodi
        chat_info = await bot.get_chat(channel_id)
        print(f"DEBUG: Chat info: {chat_info.title}")

        # ✅ TO'G'RI aiogram metodi
        bot_member = await bot.get_chat_member(channel_id, bot.id)
        print(f"DEBUG: Bot status: {bot_member.status}")

        if bot_member.status not in ["administrator", "creator"]:
            await message.answer(
                f"❌ Бот не администратор в '{chat_info.title}'",
                reply_markup=cancel_kb
            )
            return

        # Invite link olish
        invite_link = chat_info.invite_link
        if not invite_link:
            try:
                # ✅ TO'G'RI aiogram metodi
                link_data = await bot.create_chat_invite_link(channel_id)
                invite_link = link_data.invite_link
            except Exception as e:
                print(f"DEBUG: Invite link error: {e}")
                invite_link = f"Channel ID: {channel_id}"

        # Bazaga saqlash
        await create_channel_sponsor(channel_id)
        await state.clear()

        await message.answer(
            f"✅ Канал добавлен!\n\n"
            f"📣 {chat_info.title}\n"
            f"🆔 {channel_id}\n"
            f"🔗 {invite_link}"
        )

        print("DEBUG: Channel added successfully")

    except Exception as e:
        print(f"DEBUG: Error in admin_add_channel_msg: {e}")
        import traceback
        print(f"DEBUG: Traceback: {traceback.format_exc()}")

        await message.answer(
            f"❌ Ошибка: {str(e)}",
            reply_markup=cancel_kb
        )

@sync_to_async
def check_channel_exists(channel_id):
    """Проверка существования канала в базе"""
    try:
        # Замените на вашу модель каналов
        from modul.models import Channels  # или ваша модель
        return Channels.objects.filter(channel_id=channel_id).exists()
    except Exception as e:
        logger.error(f"Error checking channel exists: {e}")
        return False



class DavinchiBotFilter(Filter):
    async def __call__(self, message: types.Message, bot: Bot) -> bool:
        bot_db = await shortcuts.get_bot(bot)
        return shortcuts.have_one_module(bot_db, "leo")


@client_bot_router.message(F.text == "💸Заработать")
async def kinogain(message: Message, bot: Bot, state: FSMContext):
    bot_db = await shortcuts.get_bot(bot)

    me = await bot.get_me()
    link = f"https://t.me/{me.username}?start={message.from_user.id}"

    price = await get_actual_price(bot.token)
    min_withdraw = (await get_actual_min_amount()) or 0


    await message.bot.send_message(
        message.from_user.id,
        f"👥 Приглашай друзей и зарабатывай! За \nкаждого друга ты получишь {price}₽.\n\n"
        f"🔗 Ваша ссылка для приглашений:\n{link}\n\n",
        # f"💰 Минимальная сумма для вывода: {min_withdraw}₽",
        reply_markup=await main_menu_bt2()
    )

async def start_kino_bot(message: Message, state: FSMContext, bot: Bot):
    try:
        bot_db = await shortcuts.get_bot(bot)
        if not shortcuts.have_one_module(bot_db, "kino"):
            return

        await state.set_state(SearchFilmForm.query)
        earn_kb = ReplyKeyboardBuilder()
        earn_kb.button(text='💸Заработать')
        earn_kb = earn_kb.as_markup(resize_keyboard=True)

        await message.answer(
            '<b>Отправьте название фильма / сериала / аниме</b>\n\n'
            'Не указывайте года, озвучки и т.д.\n\n'
            'Правильный пример: Ведьмак\n'
            'Неправильный пример: Ведьмак 2022',
            parse_mode="HTML",
            reply_markup=earn_kb
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
    try:
        bot_instance = models.Bot.objects.select_related("owner").filter(token=bot.token).first()
        if not bot_instance:
            raise ValueError(f"Bot with token {bot.token} not found")

        user, user_created = models.UserTG.objects.update_or_create(
            uid=u.id,
            defaults={
                "username": u.username,
                "first_name": u.first_name,
                "last_name": u.last_name,
                "user_link": link,
            }
        )

        client_user, client_user_created = models.ClientBotUser.objects.update_or_create(
            uid=u.id,
            bot=bot_instance,
            defaults={
                "user": user,
                "inviter": inviter,
                "current_ai_limit": 12 if user_created else 0,
            }
        )

        return client_user

    except Exception as e:
        logger.error(f"Error saving user {u.id}: {e}")
        raise


class NonChatGptFilter(Filter):
    async def __call__(self, message: Message, bot: Bot) -> bool:
        bot_db = await shortcuts.get_bot(bot)
        return not shortcuts.have_one_module(bot_db, "chatgpt")


@client_bot_router.callback_query(lambda c: c.data == 'check_chan', NonChatGptFilter())
async def check_subscriptions(callback: CallbackQuery, state: FSMContext, bot: Bot):
    user_id = callback.from_user.id
    bot_db = await shortcuts.get_bot(bot)
    print("kino 978")
    subscribed = True
    not_subscribed_channels = []
    channels = await get_channels_for_check()

    if channels:
        for channel_id, channel_url in channels:
            try:
                member = await bot.get_chat_member(chat_id=channel_id, user_id=user_id)
                print(f"Channel {channel_id} status: {member.status}")

                if member.status == "left":
                    subscribed = False
                    try:
                        chat_info = await bot.get_chat(chat_id=channel_id)
                        not_subscribed_channels.append({
                            'id': channel_id,
                            'title': chat_info.title,
                            'invite_link': channel_url or chat_info.invite_link or f"https://t.me/{channel_id.strip('-')}"
                        })
                    except Exception as e:
                        print(f"⚠️ Error getting chat info for channel {channel_id}: {e}")
                        not_subscribed_channels.append({
                            'id': channel_id,
                            'title': f"Канал {channel_id}",
                            'invite_link': channel_url or f"https://t.me/{channel_id.strip('-')}"
                        })
            except Exception as e:
                logger.error(f"Error checking channel {channel_id}: {e}")
                continue

    if not subscribed:

        await callback.answer("⚠️ Вы не подписались на все каналы! Пожалуйста, подпишитесь на все указанные каналы.",
                              show_alert=True)


        channels_text = f"📢 **Для использования бота необходимо подписаться на каналы:**\n\n"

        markup = InlineKeyboardBuilder()

        for index, channel in enumerate(not_subscribed_channels):
            title = channel['title']
            invite_link = channel['invite_link']

            channels_text += f"{index + 1}. {title}\n"
            markup.button(text=f"📢 {title}", url=invite_link)

        markup.button(text="✅ Проверить подписку", callback_data="check_chan")
        markup.adjust(1)  # Har bir qatorda 1 ta tugma

        try:

            await callback.message.edit_text(
                channels_text + f"\n\nПосле подписки на все каналы нажмите кнопку «Проверить подписку».",
                reply_markup=markup.as_markup(),
                parse_mode="HTML"
            )
        except Exception as e:

            try:
                await callback.message.delete()
            except:
                pass  # Agar o'chirishda xatolik bo'lsa, e'tiborsiz qoldiramiz


            await callback.message.answer(
                channels_text + f"\n\nПосле подписки на все каналы нажмите кнопку «Проверить подписку».",
                reply_markup=markup.as_markup(),
                parse_mode="HTML"
            )

        return

    await callback.answer("Вы успешно подписались на все каналы!")


    user_exists = await check_user(user_id)


    referral_id = None


    data = await state.get_data()
    referral = data.get('referral')
    if referral and str(referral).isdigit():
        referral_id = int(referral)
        logger.info(f"Got referral ID from state: {referral_id}")


    if not user_exists:
        try:

            new_link = await create_start_link(bot, str(callback.from_user.id))
            link_for_db = new_link[new_link.index("=") + 1:]

            # Referral ID bor bo'lsa va o'zini o'zi refer qilmayotgan bo'lsa
            if referral_id and str(referral_id) != str(user_id):
                # Referral bilan qo'shish
                await add_user(
                    tg_id=callback.from_user.id,
                    user_name=callback.from_user.first_name,
                    invited="Referral",
                    invited_id=referral_id,
                    bot_token=callback.bot.token
                )
                logger.info(f"New user {callback.from_user.id} added to database with referrer {referral_id}")

                # Referral jarayonini ishga tushirish
                success = await process_referral(callback.message, referral_id)
                logger.info(f"Referral process result: {success}")
            else:
                # Referralsiz qo'shish
                await add_user(
                    tg_id=callback.from_user.id,
                    user_name=callback.from_user.first_name,
                    bot_token=callback.bot.token
                )
                logger.info(f"New user {callback.from_user.id} added to database without referrer")
        except Exception as e:
            logger.error(f"Error processing user or referral: {e}")
    else:
        # Mavjud foydalanuvchi uchun ham referral operatsiyasini tekshirish
        if referral_id and str(referral_id) != str(user_id):
            try:
                # Foydalanuvchi oldin shu referral ID ni ishlatganmi?
                user_tg = await get_user_by_id(user_id)
                if user_tg and user_tg.invited_id != referral_id:
                    # Referral jarayonini ishga tushirish
                    success = await process_referral(callback.message, referral_id)
                    logger.info(f"Existing user, new referral process result: {success}")
            except Exception as e:
                logger.error(f"Error processing referral for existing user: {e}")
        else:
            logger.info(f"User {user_id} already exists, skipping referral")

    # Bot moduliga qarab o'tish
    if shortcuts.have_one_module(bot_db, "leo"):
        # await callback.message.delete()
        builder = ReplyKeyboardBuilder()
        builder.button(text="🫰 Знакомства")
        builder.button(text="💸Заработать")
        builder.adjust(2)
        await callback.message.answer(
            "Добро пожаловать в бот знакомств!",
            reply_markup=builder.as_markup(resize_keyboard=True)
        )

    elif shortcuts.have_one_module(bot_db, "download"):
        builder = ReplyKeyboardBuilder()
        builder.button(text='💸Заработать')
        text = ("🤖 Привет, {full_name}! Я бот-загрузчик.\r\n\r\n"
                "Я могу скачать фото/видео/аудио/файлы/архивы с *Youtube, Instagram, TikTok, Facebook, SoundCloud, Vimeo, Вконтакте, Twitter и 1000+ аудио/видео/файловых хостингов*. Просто пришли мне URL на публикацию с медиа или прямую ссылку на файл.").format(
            full_name=callback.from_user.full_name)
        await state.set_state(Download.download)
        await callback.message.answer(text, parse_mode="Markdown",
                                      reply_markup=builder.as_markup(resize_keyboard=True))

    elif shortcuts.have_one_module(bot_db, "kino"):
        await callback.message.delete()
        await start_kino_bot(callback.message, state, bot)

    elif shortcuts.have_one_module(bot_db, "chatgpt"):
        builder = InlineKeyboardBuilder()
        builder.button(text='☁ Чат с GPT-4', callback_data='chat_4')
        builder.button(text='☁ Чат с GPT-3.5', callback_data='chat_3')
        builder.button(text='💸Заработать', callback_data='ref')
        builder.adjust(2, 1, 1, 1, 1, 1, 2)
        result = await get_info_db(user_id)
        text = f'Привет {callback.from_user.username}\nВаш баланс - {result[0][2]}'
        await callback.message.edit_text(text, reply_markup=builder.as_markup())

    else:
        await callback.message.delete()

        # Qo'shimcha referral operatsiyalari - Dobro pojalovatdan oldin
        data = await state.get_data()
        referral = data.get('referral')
        if referral and referral.isdigit():
            try:
                referral_id = int(referral)
                if str(referral_id) != str(user_id):
                    await process_referral(callback.message, referral_id)
            except ValueError:
                logger.error(f"Invalid referral ID at final check: {referral}")
            except Exception as e:
                logger.error(f"Error processing referral at final check: {e}")

        text = "Добро пожаловать, {hello}".format(
            hello=html.quote(callback.from_user.full_name))
        await callback.message.answer(text,
                                      reply_markup=await reply_kb.main_menu(user_id, bot))
import html
async def start(message: Message, state: FSMContext, bot: Bot):
    print(f"Start function called for user {message.from_user.id}")
    bot_db = await shortcuts.get_bot(bot)
    uid = message.from_user.id
    print(uid, 'kino start')

    # Bot modullarini tekshirish
    print(f"DEBUG: Bot modules:")
    print(f"  - enable_leo: {getattr(bot_db, 'enable_leo', 'NOT_FOUND')}")
    print(f"  - enable_download: {getattr(bot_db, 'enable_download', 'NOT_FOUND')}")
    print(f"  - enable_kino: {getattr(bot_db, 'enable_kino', 'NOT_FOUND')}")
    print(f"  - enable_refs: {getattr(bot_db, 'enable_refs', 'NOT_FOUND')}")
    print(f"  - enable_chatgpt: {getattr(bot_db, 'enable_chatgpt', 'NOT_FOUND')}")

    # have_one_module funksiyasini tekshirish
    print(f"DEBUG: have_one_module checks:")
    print(f"  - have_one_module(bot_db, 'leo'): {shortcuts.have_one_module(bot_db, 'leo')}")
    print(f"  - have_one_module(bot_db, 'refs'): {shortcuts.have_one_module(bot_db, 'refs')}")
    print(f"  - have_one_module(bot_db, 'download'): {shortcuts.have_one_module(bot_db, 'download')}")
    print(f"  - have_one_module(bot_db, 'kino'): {shortcuts.have_one_module(bot_db, 'kino')}")
    print(f"  - have_one_module(bot_db, 'chatgpt'): {shortcuts.have_one_module(bot_db, 'chatgpt')}")
    print(f"DEBUG: User {uid} started the bot with message: {message.text}")


    referral = message.text[7:] if message.text and len(message.text) > 7 else None
    print(f"Referral from command for user {uid}: {referral}")

    state_data = await state.get_data()
    state_referral = state_data.get('referrer_id') or state_data.get('referral')
    if not referral and state_referral:
        referral = state_referral
        print(f"Using referral from state for user {uid}: {referral}")

    if referral and isinstance(referral, str) and referral.isdigit():
        referrer_id = int(referral)
        await state.update_data(referrer_id=referrer_id, referral=referral)
        print(f"SAVED referrer_id {referrer_id} to state for user {uid}")
        logger.info(f"Processing start command with referral: {referral}")

        state_data = await state.get_data()
        print(f"State after saving for user {uid}: {state_data}")

    text = "Добро пожаловать, {hello}".format(hello=html.escape(message.from_user.full_name))
    kwargs = {}

    if shortcuts.have_one_module(bot_db, "leo"):
        builder = ReplyKeyboardBuilder()
        builder.button(text="🫰 Знакомства")
        builder.button(text="💸Заработать")
        builder.adjust(2)
        kwargs['reply_markup'] = builder.as_markup(resize_keyboard=True)

    if shortcuts.have_one_module(bot_db, "download"):
        builder = ReplyKeyboardBuilder()
        builder.button(text='💸Заработать')
        text = ("🤖 Привет, {full_name}! Я бот-загрузчик.\r\n\r\n"
                "Я могу скачать фото/видео/аудио/файлы/архивы с *Youtube, Instagram, TikTok, Facebook, SoundCloud, Vimeo, Вконтакте, Twitter и 1000+ аудио/видео/файловых хостингов*. Просто пришли мне URL на публикацию с медиа или прямую ссылку на файл.").format(
            full_name=message.from_user.full_name)
        await state.set_state(Download.download)
        kwargs['parse_mode'] = "Markdown"
        kwargs['reply_markup'] = builder.as_markup(resize_keyboard=True)

    if shortcuts.have_one_module(bot_db, "refs"):
        is_registered = await check_user(uid)
        is_banned = await check_ban(uid)

        if is_banned:
            logger.info(f"User {uid} is banned, exiting")
            await message.answer("Вы были заблокированы")
            return

        if not is_registered and referral and isinstance(referral, str) and referral.isdigit():
            ref_id = int(referral)

            if ref_id == uid:
                print(f"Self-referral blocked: user {uid} tried to refer themselves")
                logger.warning(f"SELF-REFERRAL BLOCKED: User {uid}")
            else:
                print(f"Processing referral for new user {uid} from {ref_id}")
                try:
                    already_referred = await check_if_already_referred(uid, ref_id, message.bot.token)
                    if already_referred:
                        print(f"User {uid} is already referred by {ref_id}, skipping referral process")
                        logger.warning(f"ALREADY REFERRED: User {uid} is already referred by {ref_id}")
                    else:
                        @sync_to_async
                        def get_referrer_direct():
                            try:
                                referrer = UserTG.objects.filter(uid=ref_id).first()
                                return referrer
                            except Exception as e:
                                print(f"Error getting referrer from database: {e}")
                                logger.error(f"Error getting referrer from database: {e}")
                                return None

                        referrer = await get_referrer_direct()

                        if not referrer:
                            print(f"Referrer {ref_id} not found in database directly")
                            logger.warning(f"Referrer {ref_id} not found in database")
                        else:
                            print(f"Found referrer {ref_id} in database")
                            new_user = await add_user(
                                tg_id=uid,
                                user_name=message.from_user.first_name,
                                invited=referrer.first_name or "Unknown",
                                invited_id=ref_id,
                                bot_token=message.bot.token
                            )
                            print(f"Added new user {uid} with referrer {ref_id}")

                            @sync_to_async
                            @transaction.atomic
                            def update_referrer_balance(ref_id, bot_token):
                                try:
                                    # Получаем бота по токену
                                    bot = Bot.objects.get(token=bot_token)

                                    # Получаем пользователя
                                    user_tg = UserTG.objects.select_for_update().get(uid=ref_id)

                                    # Получаем или создаем запись ClientBotUser для этого бота
                                    client_bot_user, created = ClientBotUser.objects.get_or_create(
                                        uid=ref_id,
                                        bot=bot,
                                        defaults={
                                            'user': user_tg,
                                            'balance': 0,
                                            'referral_count': 0,
                                            'referral_balance': 0
                                        }
                                    )

                                    # Получаем цену из настроек для этого бота
                                    admin_info = AdminInfo.objects.filter(bot_token=bot_token).first()

                                    if not admin_info:
                                        admin_info = AdminInfo.objects.first()

                                    # Определяем награду
                                    if admin_info and hasattr(admin_info, 'price') and admin_info.price:
                                        price = float(admin_info.price)
                                    else:
                                        price = 3.0  # По умолчанию 3 рубля

                                    # Обновляем поля для конкретного бота
                                    client_bot_user.referral_count += 1
                                    client_bot_user.referral_balance += price
                                    client_bot_user.save()

                                    # Также обновляем общие поля в UserTG
                                    user_tg.refs += 1
                                    user_tg.balance += price
                                    user_tg.save()

                                    print(
                                        f"Updated referrer {ref_id} for bot: refs={client_bot_user.referral_count}, balance={client_bot_user.referral_balance}")
                                    return True
                                except Exception as e:
                                    print(f"Error updating referrer balance: {e}")
                                    traceback.print_exc()
                                    return False

                            success = await update_referrer_balance(ref_id, message.bot.token)
                            print(f"Referrer balance update success: {success}")

                            # HTML formatlash uchun to'g'irlang
                            if success:
                                try:
                                    print(f"Preparing to send referral notification to {ref_id}")
                                    user_name = message.from_user.first_name
                                    user_profile_link = f'tg://user?id={uid}'

                                    await asyncio.sleep(1)

                                    await bot.send_message(
                                        chat_id=ref_id,
                                        text=f"У вас новый реферал! <a href='{user_profile_link}'>{user_name}</a>",
                                        parse_mode="HTML"
                                    )
                                    print(f"Sent referral notification to {ref_id} about user {uid}")
                                    logger.info(f"Sent referral notification to {ref_id} about user {uid}")
                                except Exception as e:
                                    print(f"Error sending notification to referrer: {e}")
                                    logger.error(f"Error sending notification to referrer: {e}")
                                    traceback.print_exc()
                except Exception as e:
                    print(f"Error in referral process: {e}")
                    logger.error(f"Error in referral process: {e}")
                    traceback.print_exc()

        channels = await get_channels_for_check()

        if not channels:
            print(f"No channels found for user {uid}, considering as subscribed")
            channels_checker = True
        else:
            try:
                channels_checker = await check_channels(uid, bot)

            except Exception as e:
                print(f"Error checking channels: {e}")
                logger.error(f"Error checking channels: {e}")
                channels_checker = False

            if not channels_checker:
                print(f"Channel check failed for user {uid}, but referrer_id saved in state")
                return

        print(f"Channels check result for user {uid}: {channels_checker}")

        await message.answer(
            f"🎉 Привет, {message.from_user.first_name}",
            reply_markup=await main_menu_bt()
        )
        return

    elif shortcuts.have_one_module(bot_db, "kino"):
        print("kino")
        await start_kino_bot(message, state, bot)
        return
    elif shortcuts.have_one_module(bot_db, "chatgpt"):
        builder = InlineKeyboardBuilder()
        builder.button(text='☁ Чат с GPT-4', callback_data='chat_4')
        builder.button(text='☁ Чат с GPT-3.5', callback_data='chat_3')

        builder.button(text='💸Заработать', callback_data='ref')
        builder.adjust(2, 1, 1, 1, 1, 1, 2)
        result = await get_info_db(uid)
        print(result)
        text = f'Привет {message.from_user.username}\nВаш баланс - {result[0][2]}'
        kwargs['reply_markup'] = builder.as_markup()

    # elif shortcuts.have_one_module(bot_db,"anon"):
    #     await message.answer('anon')
    else:
        print("DEBUG: No specific module, using default")
        kwargs['reply_markup'] = await reply_kb.main_menu(uid, bot)

    await message.answer(text, **kwargs)

import html
@client_bot_router.message(CommandStart(), NonChatGptFilter())
async def start_on(message: Message, state: FSMContext, bot: Bot, command: CommandObject):
    try:
        print(f"Full start message: {message.text}")
        logger.info(f"Start command received from user {message.from_user.id}")

        referral = command.args if command and command.args else None
        print(f"Extracted referral from command.args: {referral}")

        if not referral and message.text and len(message.text) > 7:
            text_referral = message.text[7:]
            if text_referral.isdigit():
                referral = text_referral
                print(f"Extracted referral from text: {referral}")

        if referral:
            await state.update_data(referral=referral, referrer_id=referral)
            print(f"Saved referral to state with both keys: {referral}")

        # O'ZGARISH: get_channels_with_type_for_check() ishlatish
        channels = await get_channels_with_type_for_check()
        print(f"📡 Found channels: {channels}")

        if channels:
            print(f"🔒 Channels exist, checking user subscription for {message.from_user.id}")
            not_subscribed_channels = []

            # O'ZGARISH: channel_type ham olish
            for channel_id, channel_url, channel_type in channels:
                try:
                    # O'ZGARISH: channel type ga qarab bot tanlash
                    if channel_type == 'system':
                        from modul.loader import main_bot
                        member = await main_bot.get_chat_member(
                            chat_id=int(channel_id),
                            user_id=message.from_user.id
                        )
                        print(f"System channel {channel_id} checked via main_bot: {member.status}")
                    else:
                        member = await message.bot.get_chat_member(
                            chat_id=int(channel_id),
                            user_id=message.from_user.id
                        )
                        print(f"Sponsor channel {channel_id} checked via current_bot: {member.status}")

                    if member.status == "left":
                        try:
                            # Chat info ni ham to'g'ri bot orqali olish
                            if channel_type == 'system':
                                chat_info = await main_bot.get_chat(chat_id=int(channel_id))
                            else:
                                chat_info = await message.bot.get_chat(chat_id=int(channel_id))

                            not_subscribed_channels.append({
                                'id': channel_id,
                                'title': chat_info.title,
                                'invite_link': channel_url or chat_info.invite_link or f"https://t.me/{channel_id.strip('-')}"
                            })
                        except Exception as e:
                            print(f"⚠️ Error getting chat info for channel {channel_id}: {e}")
                            not_subscribed_channels.append({
                                'id': channel_id,
                                'title': f"Канал {channel_id}",
                                'invite_link': channel_url or f"https://t.me/{channel_id.strip('-')}"
                            })
                except Exception as e:
                    logger.error(f"Error checking channel {channel_id} (type: {channel_type}): {e}")

                    # O'ZGARISH: faqat sponsor kanallarni o'chirish
                    if channel_type == 'sponsor':
                        await remove_sponsor_channel(channel_id)
                        logger.info(f"Removed invalid sponsor channel {channel_id}")
                    else:
                        # System kanallar uchun faqat log
                        logger.warning(f"System channel {channel_id} error (ignoring): {e}")
                    continue

            if not not_subscribed_channels:
                print(f"✅ User {message.from_user.id} subscribed to all channels - proceeding with registration")
                current_user_id = message.from_user.id
                is_registered = await check_user_in_specific_bot(current_user_id, bot.token)

                if not is_registered:
                    new_user = await add_user_safely(
                        tg_id=current_user_id,
                        user_name=message.from_user.first_name,
                        invited_type="Direct" if not referral else "Referral",
                        invited_id=int(referral) if referral else None,
                        bot_token=bot.token
                    )
                    print(f"➕ Added user {current_user_id} to database (all channels subscribed), result: {new_user}")

                    # REFERRAL JARAYONI
                    if new_user and referral and referral.isdigit():
                        ref_id = int(referral)
                        if ref_id != current_user_id:
                            success, reward = await process_referral_bonus(current_user_id, ref_id, bot.token)

                            if success:
                                try:
                                    user_name = html.escape(message.from_user.first_name)
                                    user_profile_link = f'tg://user?id={current_user_id}'

                                    await asyncio.sleep(1)

                                    await bot.send_message(
                                        chat_id=ref_id,
                                        text=f"У вас новый реферал! <a href='{user_profile_link}'>{user_name}</a>\n"
                                             f"💰 Получено: {reward}₽",
                                        parse_mode="HTML"
                                    )
                                    print(f"📨 Sent referral notification to {ref_id} about user {current_user_id}")
                                except Exception as e:
                                    print(f"⚠️ Error sending notification to referrer {ref_id}: {e}")
                else:
                    print(f"ℹ️ User {current_user_id} already registered in this bot")

                await start(message, state, bot)
                return

            print(f"🚫 User {message.from_user.id} not subscribed to all channels")

            channels_text = "📢 <b>Для использования бота необходимо подписаться на каналы:</b>\n\n"
            kb = InlineKeyboardBuilder()

            for index, channel in enumerate(not_subscribed_channels):
                title = channel['title']
                invite_link = channel['invite_link']

                channels_text += f"{index + 1}. {title}\n"
                kb.button(text=f"📢 {title}", url=invite_link)

            kb.button(text="✅ Проверить подписку", callback_data="check_chan")
            kb.adjust(1)

            await message.answer(
                channels_text + "\n\nПосле подписки на все каналы нажмите кнопку «Проверить подписку».",
                reply_markup=kb.as_markup(),
                parse_mode="HTML"
            )

            print(f"📝 State saved for user {message.from_user.id}: referral data will be processed after channel check")
            print(f"🚫 NOT adding user to database - waiting for check_chan callback")
            return  # FAQAT OBUNA BO'LMAGAN KANALLARNI KO'RSATISH

        # Qolgan kod o'zgarmaydi...
        print(f"ℹ️ No channels found, proceeding with normal registration for {message.from_user.id}")

        current_user_id = message.from_user.id
        is_registered = await check_user_in_specific_bot(current_user_id, bot.token)

        if not is_registered:
            new_user = await add_user_safely(
                tg_id=current_user_id,
                user_name=message.from_user.first_name,
                invited_type="Direct" if not referral else "Referral",
                invited_id=int(referral) if referral else None,
                bot_token=bot.token
            )
            print(f"➕ Added user {current_user_id} to database (no channels), result: {new_user}")

            if new_user and referral and referral.isdigit():
                ref_id = int(referral)
                if ref_id != current_user_id:
                    success, reward = await process_referral_bonus(current_user_id, ref_id, bot.token)

                    if success:
                        try:
                            user_name = html.escape(message.from_user.first_name)
                            user_profile_link = f'tg://user?id={current_user_id}'

                            await asyncio.sleep(1)

                            await bot.send_message(
                                chat_id=ref_id,
                                text=f"У вас новый реферал! <a href='{user_profile_link}'>{user_name}</a>\n"
                                     f"💰 Получено: {reward}₽",
                                parse_mode="HTML"
                            )
                            print(f"📨 Sent referral notification to {ref_id} about user {current_user_id}")
                        except Exception as e:
                            print(f"⚠️ Error sending notification to referrer {ref_id}: {e}")
        else:
            print(f"ℹ️ User {current_user_id} already registered in this bot")

        await start(message, state, bot)

    except Exception as e:
        logger.error(f"Error in start handler: {e}")
        traceback.print_exc()
        await message.answer("Произошла ошибка при запуске. Пожалуйста, попробуйте позже.")


@client_bot_router.callback_query(F.data == 'start_search')
async def start_search(call: types.CallbackQuery, state: FSMContext):
    await state.set_state(SearchFilmForm.query)
    await call.message.answer(
        '<b>Отправьте название фильма / сериала / аниме</b>\n\n'
        'Не указывайте года, озвучки и т.д.\n\n'
        'Правильный пример: Ведьмак\n'
        'Неправильный пример: Ведьмак 2022')


@client_bot_router.callback_query(F.data.contains('watch_film'), StateFilter('*'))
async def watch_film(call: CallbackQuery, state: FSMContext):
    film_id = int(call.data.split('|')[-1])
    bot_info = await call.bot.me()
    bot_username = bot_info.username

    film_data = await get_film_for_view(film_id)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='Смотреть', url=film_data['view_link'])],
        [InlineKeyboardButton(text='🔥 Лучшие фильмы 🔥', url='https://t.me/KinoPlay_HD')],
        [InlineKeyboardButton(text='🔍 Поиск фильмов 🔍', url=f'https://t.me/{bot_username}?start=start_search')]

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
    # await state.clear()  # Bu qatorni olib tashlang yoki kommentariyaga aylantiring

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

    await state.set_state(SearchFilmForm.query)
    await message.answer(
        '<b>Можете искать другие фильмы. Отправьте название фильма / сериала / аниме</b>',
        parse_mode="HTML"
    )


@client_bot_router.message(StateFilter(SearchFilmForm.query), KinoBotFilter())
async def simple_text_film_handler(message: Message, bot: Bot):
    sub_status = await check_subs(message.from_user.id, bot)

    if not sub_status:
        kb = await get_subs_kb(bot)
        await message.answer(
            '<b>Чтобы воспользоваться ботом, необходимо подписаться на каналы</b>',
            reply_markup=kb,
            parse_mode="HTML"
        )
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

@client_bot_router.inline_query(F.query)
async def inline_film_requests(query: InlineQuery):
    results = await film_search(query.query)

    inline_answer = []
    bot = query.bot.me()
    for film in results['results']:
        film_data = await get_film_for_view(film['id'])

        text = f'<a href="{film_data["poster"]}">🔥🎥</a> {film_data["name"]} ({film_data["year"]})\n\n{film_data["description"]}\n\n{film_data["country"]}\n{film_data["genres"]}'

        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text='Смотреть', url=film_data['view_link'])],
            # [InlineKeyboardButton(text='🔥 Лучшие фильмы 🔥', url='https://t.me/KinoPlay_HD')],
            [InlineKeyboardButton(text='🔍 Поиск фильмов 🔍', url=f'https://t.me/{bot}')]
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


client_bot_router.message.register(bot_start, F.text == "🫰 Знакомства", DavinchiBotFilter())
client_bot_router.message.register(bot_start_cancel, F.text == ("Я не хочу никого искать"), LeomatchRegistration.BEGIN)
client_bot_router.callback_query(F.data == "start_registration")
client_bot_router.message.register(bot_start_lets_leo, F.text == "Давай, начнем!", LeomatchRegistration.BEGIN)

from modul.clientbot.handlers.leomatch.handlers.start import handle_start_registration_callback, handle_dont_want_search_callback
# Debug: Registering callback for start_registration
print("Registering callback: handle_start_registration_callback for start_registration")
client_bot_router.callback_query.register(handle_start_registration_callback, F.data == "start_registration", LeomatchRegistration.BEGIN)
#write me debug info
client_bot_router.callback_query.register(handle_dont_want_search_callback, F.data == "dont_want_search", LeomatchRegistration.BEGIN)


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



@client_bot_router.callback_query(F.data == "too_large")
async def handle_too_large_file(callback: CallbackQuery):
    """Katta fayl tanlanganda"""
    await callback.answer(
        "⚠️ Bu fayl Telegram uchun juda katta (50MB+). "
        "Kichikroq sifatli formatni tanlang.",
        show_alert=True
    )




class DownloaderBotFilter(Filter):
    async def __call__(self, message: types.Message, bot: Bot) -> bool:
        bot_db = await shortcuts.get_bot(bot)
        return shortcuts.have_one_module(bot_db, "download")


@client_bot_router.message(DownloaderBotFilter())
@client_bot_router.message(Download.download)
async def youtube_download_handler(message: Message, state: FSMContext, bot: Bot):
    if not message.text:
        await message.answer("❗ Отправьте ссылку на видео")
        return

    url = message.text.strip()
    me = await bot.get_me()

    if 'tiktok.com' in url:
        await handle_tiktok(message, url, me, bot, state)
    elif 'instagram.com' in url or 'instagr.am' in url or 'inst.ae' in url:
        await handle_instagram(message, url, me, bot)
    elif 'youtube.com' in url or 'youtu.be' in url:
        await handle_youtube(message, url, me, bot, state)  # Yangilangan funksiya
    else:
        await message.answer("❗ Поддерживаются только YouTube, Instagram и TikTok ссылки")


@client_bot_router.callback_query(F.data.startswith("yt_dl_"))
async def process_youtube_download(callback: CallbackQuery, state: FSMContext):
    """YouTube download callback"""
    try:
        await callback.answer()

        format_index = int(callback.data.split('_')[2])

        data = await state.get_data()
        video_data = data.get('youtube_data')
        formats = data.get('youtube_formats', [])

        if not video_data or not formats or format_index >= len(formats):
            await callback.message.edit_text("❌ Yuklab olish ma'lumotlari topilmadi")
            return

        selected_format = formats[format_index]
        title = video_data.get('title', 'Video')

        await callback.message.edit_text(
            f"⏳ <b>Yuklab olmoqda...</b>\n\n"
            f"🎥 <b>{title[:50]}...</b>\n"
            f"📋 <b>Format:</b> {selected_format['quality']} {selected_format['ext'].upper()}",
            parse_mode="HTML"
        )

        # Download URL ni topish
        download_url = None
        itag = selected_format['itag']

        # Progressive formatlardan qidirish
        if 'formats' in video_data:
            for fmt in video_data['formats']:
                if fmt.get('itag') == itag:
                    download_url = fmt.get('url')
                    break

        # Adaptive formatlardan qidirish
        if not download_url and 'adaptiveFormats' in video_data:
            for fmt in video_data['adaptiveFormats']:
                if fmt.get('itag') == itag:
                    download_url = fmt.get('url')
                    break

        if not download_url:
            await callback.message.edit_text("❌ Yuklab olish URL topilmadi")
            return

        # Faylni yuklab olish va yuborish
        await download_and_send_youtube(callback, download_url, selected_format, video_data, title)

    except Exception as e:
        logger.error(f"YouTube download callback error: {e}")
        await callback.message.edit_text("❌ Yuklab olish xatoligi")


async def download_and_send_youtube(callback, download_url, format_data, video_data, title):
    """YouTube faylni yuklab olib Telegram ga yuborish"""
    temp_dir = None
    try:
        # Temp directory yaratish
        temp_dir = tempfile.mkdtemp(prefix='yt_api_')
        file_ext = format_data['ext']
        filename = f"{title[:50]}.{file_ext}".replace('/', '_').replace('\\', '_')
        filepath = os.path.join(temp_dir, filename)

        # Progress yangilash
        await callback.message.edit_text(
            f"⏬ <b>Yuklab olmoqda...</b>\n\n"
            f"🎥 <b>{title[:50]}...</b>\n"
            f"📋 <b>Format:</b> {format_data['quality']} {format_data['ext'].upper()}\n"
            f"📦 <b>Hajmi:</b> {format_data['size']:.1f} MB",
            parse_mode="HTML"
        )

        # Faylni yuklab olish
        async with aiohttp.ClientSession() as session:
            async with session.get(download_url) as response:
                if response.status == 200:
                    total_size = int(response.headers.get('content-length', 0))
                    downloaded = 0

                    with open(filepath, 'wb') as file:
                        async for chunk in response.content.iter_chunked(8192):
                            file.write(chunk)
                            downloaded += len(chunk)

                            # Har 1MB da progress yangilash
                            if downloaded % (1024 * 1024) == 0:
                                progress = (downloaded / total_size) * 100 if total_size else 0
                                await callback.message.edit_text(
                                    f"⏬ <b>Yuklab olmoqda: {progress:.0f}%</b>\n\n"
                                    f"🎥 <b>{title[:50]}...</b>\n"
                                    f"📋 <b>Format:</b> {format_data['quality']} {format_data['ext'].upper()}\n"
                                    f"📦 <b>Hajmi:</b> {format_data['size']:.1f} MB",
                                    parse_mode="HTML"
                                )
                else:
                    raise Exception(f"Download failed: HTTP {response.status}")

        # Fayl hajmini tekshirish
        file_size = os.path.getsize(filepath)
        file_size_mb = file_size / (1024 * 1024)

        if file_size_mb > 50:
            await callback.message.edit_text(
                f"❌ <b>Fayl juda katta</b>\n\n"
                f"📦 <b>Hajmi:</b> {file_size_mb:.1f} MB\n"
                f"📏 <b>Telegram limiti:</b> 50 MB\n\n"
                f"💡 Kichikroq sifat tanlang",
                parse_mode="HTML"
            )
            return

        # Telegram ga yuborish
        await callback.message.edit_text(
            f"📤 <b>Telegram ga yubormoqda...</b>\n\n"
            f"🎥 <b>{title[:50]}...</b>",
            parse_mode="HTML"
        )

        caption = (
            f"🎥 {title}\n"
            f"👤 {video_data.get('channelTitle', 'Unknown')}\n"
            f"📋 {format_data['quality']} {format_data['ext'].upper()}\n"
            f"📦 {file_size_mb:.1f} MB\n"
            f"🎯 YouTube API orqali yuklab olindi"
        )

        try:
            if format_data['type'] == 'audio':
                await callback.bot.send_audio(
                    chat_id=callback.message.chat.id,
                    audio=FSInputFile(filepath),
                    caption=caption,
                    title=title,
                    performer=video_data.get('channelTitle', 'Unknown'),
                    duration=int(video_data.get('lengthSeconds', 0))
                )
            else:
                await callback.bot.send_video(
                    chat_id=callback.message.chat.id,
                    video=FSInputFile(filepath),
                    caption=caption,
                    supports_streaming=True,
                    duration=int(video_data.get('lengthSeconds', 0))
                )

            await callback.message.delete()

            # Analytics
            try:
                await shortcuts.add_to_analitic_data(
                    (await callback.bot.get_me()).username,
                    callback.message.chat.id
                )
            except:
                pass

        except Exception as send_error:
            logger.error(f"Error sending file: {send_error}")
            await callback.message.edit_text(
                f"❌ <b>Faylni yuborishda xatolik</b>\n\n"
                f"📋 <b>Xatolik:</b> {str(send_error)[:150]}...",
                parse_mode="HTML"
            )

    except Exception as e:
        logger.error(f"Download and send error: {e}")
        await callback.message.edit_text(
            f"❌ <b>Yuklab olishda xatolik</b>\n\n"
            f"📋 <b>Xatolik:</b> {str(e)[:150]}...",
            parse_mode="HTML"
        )
    finally:
        # Temp fayllarni tozalash
        if temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
            except:
                pass


async def handle_youtube(message: Message, url: str, me, bot, state: FSMContext):
    logger.info(f"🎬 YouTube handler started")
    logger.info(f"🔗 URL: {url}")

    try:
        progress_msg = await message.answer("🔍 Анализирую YouTube видео...")
        logger.info("✅ Progress message sent")

        # Video ID ni olish
        video_id = extract_youtube_id(url)
        if not video_id:
            logger.error("❌ Could not extract video ID")
            await progress_msg.edit_text("❌ Неверная ссылка YouTube")
            return

        # API dan ma'lumot olish
        logger.info(f"🔍 Getting video info for ID: {video_id}")
        video_data = await get_youtube_info_via_fast_api(video_id, "247")

        if not video_data:
            logger.error("❌ No video data received from API")
            await progress_msg.edit_text(
                "❌ <b>Не удалось получить данные видео</b>\n\n"
                "💡 Проверьте ссылку или попробуйте позже",
                parse_mode="HTML"
            )
            return

        # Video ma'lumotlarini formatlash
        size_mb = int(video_data.get('size', 0)) / (1024 * 1024) if video_data.get('size') else 0
        logger.info(f"📦 Video size: {size_mb:.1f} MB")

        info_text = (
            f"✅ <b>YouTube видео найдено!</b>\n\n"
            f"🆔 <b>ID видео:</b> {video_id}\n"
            f"📋 <b>Качество:</b> {video_data.get('quality', 'Неизвестно')}\n"
            f"📦 <b>Размер:</b> {size_mb:.1f} МБ\n"
            f"🎞 <b>Формат:</b> {video_data.get('mime', 'Неизвестно')}\n"
            f"⚡ <b>Битрейт:</b> {video_data.get('bitrate', 'Неизвестно')}\n\n"
            f"📥 <b>Выберите формат:</b>"
        )

        keyboard = create_youtube_format_keyboard()

        # State ga saqlash
        await state.update_data(
            youtube_url=url,
            youtube_video_id=video_id,
            youtube_api_type="fast_api"
        )
        logger.info("💾 Data saved to state")

        await progress_msg.edit_text(
            info_text,
            reply_markup=keyboard.as_markup(),
            parse_mode="HTML"
        )
        logger.info("✅ YouTube handler completed successfully")

    except Exception as e:
        logger.error(f"❌ YouTube handler error: {type(e).__name__}: {e}")
        import traceback
        logger.error(f"📍 Traceback: {traceback.format_exc()}")
        await message.answer("❌ Ошибка при обработке YouTube видео")

download_tasks = {}


@client_bot_router.callback_query(F.data.startswith("yt_fast_dl_"))
async def process_youtube_fast_download(callback: CallbackQuery, state: FSMContext):
    logger.info(f"📱 Fast download callback triggered")
    logger.info(f"📋 Callback data: {callback.data}")

    try:
        # Callback answer
        try:
            await callback.answer("⏳ Загрузка начата...")
        except:
            pass

        # Ma'lumotlarni olish
        parts = callback.data.split('_')
        if len(parts) < 4:
            await callback.message.edit_text("❌ Неверный формат данных")
            return

        requested_quality = parts[3]  # Foydalanuvchi tanlagan sifat
        data = await state.get_data()
        video_id = data.get('youtube_video_id')

        if not video_id:
            await callback.message.edit_text("❌ Данные видео не найдены")
            return

        qualities = get_available_youtube_qualities()
        if requested_quality not in qualities:
            await callback.message.edit_text("❌ Неверный формат выбран")
            return

        selected_format = qualities[requested_quality]

        await callback.message.edit_text(
            f"⏳ <b>Отправляю запрос на загрузку...</b>\n\n"
            f"🆔 <b>ID видео:</b> {video_id}\n"
            f"📋 <b>Запрошенное качество:</b> {requested_quality}p\n"
            f"⚙️ <b>Формат:</b> {selected_format['desc']}",
            parse_mode="HTML"
        )

        # API dan download URL olish
        logger.info(f"🔍 Getting download URL for quality: {requested_quality}")
        download_data = await get_youtube_info_via_fast_api(video_id, requested_quality)

        if not download_data:
            await callback.message.edit_text("❌ Данные для загрузки не получены")
            return

        if 'file' not in download_data:
            await callback.message.edit_text("❌ URL для загрузки не найден")
            return

        # 🎯 QUALITY TEKSHIRISH - YANGI QO'SHILGAN
        actual_quality = download_data.get('quality', '').replace('p', '')  # "144p" -> "144"
        api_comment = download_data.get('comment', '')

        logger.info(f"🎯 Requested quality: {requested_quality}p")
        logger.info(f"📥 API returned quality: {download_data.get('quality')}")
        logger.info(f"💬 API comment: {api_comment}")

        # Agar quality mos kelmasa
        if actual_quality != requested_quality:
            logger.warning(f"⚠️ Quality mismatch: requested {requested_quality}, got {actual_quality}")

            # Avtomatik pastroq sifat tanlanganini tekshirish
            if "not found" in api_comment.lower() or "automatically selected" in api_comment.lower():

                # Mavjud quality'larni topish
                available_qualities = await find_available_qualities(video_id)
                quality_text = ", ".join(
                    [f"{q}p" for q in available_qualities]) if available_qualities else "неизвестно"

                await callback.message.edit_text(
                    f"⚠️ <b>Запрошенное качество недоступно!</b>\n\n"
                    f"🎯 <b>Вы выбрали:</b> {requested_quality}p\n"
                    f"📥 <b>API вернул:</b> {download_data.get('quality', 'неизвестно')}\n"
                    f"✅ <b>Доступные качества:</b> {quality_text}\n\n"
                    f"❓ <b>Скачать доступное качество ({download_data.get('quality', 'неизвестно')})?</b>",
                    parse_mode="HTML",
                    reply_markup=create_quality_choice_keyboard(video_id, actual_quality, requested_quality)
                )
                return
            else:
                # Boshqa sabab bo'lsa
                await callback.message.edit_text(
                    f"⚠️ <b>Качество не совпадает</b>\n\n"
                    f"🎯 <b>Запрошено:</b> {requested_quality}p\n"
                    f"📥 <b>Получено:</b> {download_data.get('quality', 'неизвестно')}\n\n"
                    f"💡 Попробуйте выбрать другое качество",
                    parse_mode="HTML"
                )
                return

        # Quality mos kelsa, davom etish
        download_url = download_data['file']
        size_mb = int(download_data.get('size', 0)) / (1024 * 1024)

        logger.info(f"✅ Quality confirmed: {requested_quality}p")
        logger.info(f"✅ Download URL obtained: {download_url[:50]}...")
        logger.info(f"📦 File size: {size_mb:.1f} MB")

        # Telegram limit tekshirish
        if size_mb > 50:
            await callback.message.edit_text(
                f"❌ <b>Файл слишком большой!</b>\n\n"
                f"📦 <b>Размер:</b> {size_mb:.1f} МБ\n"
                f"📏 <b>Лимит Telegram:</b> 50 МБ\n\n"
                f"💡 Выберите формат меньшего размера",
                parse_mode="HTML"
            )
            return

        await callback.message.edit_text(
            f"⏳ <b>Жду готовности файла...</b>\n\n"
            f"🆔 <b>ID видео:</b> {video_id}\n"
            f"📋 <b>Качество:</b> {download_data.get('quality', requested_quality + 'p')} ✅\n"
            f"📦 <b>Размер:</b> {size_mb:.1f} МБ\n\n"
            f"⏱ <b>Максимальное ожидание:</b> 2 минуты",
            parse_mode="HTML"
        )

        # Fayl tayyor bo'lishini kutish
        logger.info("⏳ Starting file ready check...")
        is_ready = await wait_for_youtube_file_ready(download_url, max_wait_minutes=2)

        if not is_ready:
            logger.error("⏰ File not ready after waiting")
            await callback.message.edit_text(
                f"⏰ <b>Файл не готов через 2 минуты</b>\n\n"
                f"💡 Попробуйте позже или выберите другой формат",
                parse_mode="HTML"
            )
            return

        # Faylni yuklab olib yuborish
        logger.info("📥 Starting file download and send...")
        await download_and_send_youtube_fast(callback, download_url, selected_format, video_id, size_mb)

    except Exception as e:
        logger.error(f"❌ Fast download callback error: {type(e).__name__}: {e}")
        import traceback
        logger.error(f"📍 Traceback: {traceback.format_exc()}")
        await callback.message.edit_text("❌ Ошибка при загрузке")


def create_quality_choice_keyboard(video_id, available_quality, requested_quality):
    """Quality tanlash uchun keyboard"""
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text=f"✅ Скачать {available_quality}p",
                callback_data=f"yt_accept_quality_{available_quality}_{video_id}"
            )
        ],
        [
            InlineKeyboardButton(
                text="🔄 Показать все доступные",
                callback_data=f"yt_show_available_{video_id}"
            )
        ],
        [
            InlineKeyboardButton(
                text="❌ Отмена",
                callback_data="yt_cancel_download"
            )
        ]
    ])
    return keyboard


@client_bot_router.callback_query(F.data.startswith("yt_accept_quality_"))
async def accept_available_quality(callback: CallbackQuery, state: FSMContext):
    """Mavjud quality'ni qabul qilish"""
    try:
        await callback.answer()

        parts = callback.data.replace("yt_accept_quality_", "").split('_', 1)
        if len(parts) < 2:
            await callback.message.edit_text("❌ Неверные данные")
            return

        quality = parts[0]
        video_id = parts[1]

        logger.info(f"✅ User accepted quality: {quality}p for video: {video_id}")

        # State yangilash
        await state.update_data(youtube_video_id=video_id)

        # Fake callback yaratish
        callback.data = f"yt_fast_dl_{quality}"

        # Qayta ishga tushirish
        await process_youtube_fast_download(callback, state)

    except Exception as e:
        logger.error(f"❌ Accept quality error: {e}")
        await callback.message.edit_text("❌ Ошибка")


@client_bot_router.callback_query(F.data.startswith("yt_show_available_"))
async def show_available_qualities(callback: CallbackQuery, state: FSMContext):
    """Barcha mavjud quality'larni ko'rsatish"""
    try:
        await callback.answer()
        video_id = callback.data.replace("yt_show_available_", "")

        await callback.message.edit_text(
            f"🔍 <b>Проверяю доступные качества...</b>\n\n"
            f"🆔 <b>Видео:</b> {video_id}\n"
            f"⏳ <b>Это займет несколько секунд</b>",
            parse_mode="HTML"
        )

        # Available quality'larni topish
        available = await find_available_qualities(video_id)

        if not available:
            await callback.message.edit_text(
                f"❌ <b>Не удалось найти доступные качества</b>\n\n"
                f"💡 Попробуйте позже",
                parse_mode="HTML"
            )
            return

        # Quality tanlash keyboard'i
        keyboard_buttons = []
        for quality in available:
            keyboard_buttons.append([
                InlineKeyboardButton(
                    text=f"📺 {quality}p",
                    callback_data=f"yt_fast_dl_{quality}"
                )
            ])

        keyboard_buttons.append([
            InlineKeyboardButton(text="❌ Отмена", callback_data="yt_cancel_download")
        ])

        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

        # State yangilash
        await state.update_data(youtube_video_id=video_id)

        await callback.message.edit_text(
            f"📋 <b>Доступные качества для скачивания:</b>\n\n"
            f"🆔 <b>Видео:</b> {video_id}\n"
            f"✅ <b>Найдено качеств:</b> {len(available)}\n"
            f"📺 <b>Доступны:</b> {', '.join([f'{q}p' for q in available])}\n\n"
            f"👆 <b>Выберите нужное качество:</b>",
            parse_mode="HTML",
            reply_markup=keyboard
        )

    except Exception as e:
        logger.error(f"❌ Show available error: {e}")
        await callback.message.edit_text("❌ Ошибка при проверке качества")


async def find_available_qualities(video_id, max_check=5):
    """
    Video uchun mavjud quality'larni tezkor topish
    """
    available = []
    # Eng keng tarqalgan quality'lar
    test_qualities = ['144', '240', '360', '480', '720']

    logger.info(f"🔍 Quick check for available qualities: {video_id}")

    for i, quality in enumerate(test_qualities):
        if i >= max_check:  # Maximum 5ta tekshirish
            break

        try:
            data = await asyncio.wait_for(
                get_youtube_info_via_fast_api(video_id, quality),
                timeout=10  # 10 sekund timeout
            )

            if data and 'quality' in data:
                actual_quality = data.get('quality', '').replace('p', '')
                if actual_quality == quality:
                    available.append(quality)
                    logger.info(f"✅ {quality}p available")
                elif actual_quality and actual_quality not in available:
                    # Boshqa quality qaytgan bo'lsa, uni ham qo'shish
                    available.append(actual_quality)
                    logger.info(f"✅ {actual_quality}p available (alternate)")

        except asyncio.TimeoutError:
            logger.warning(f"⏰ Timeout checking {quality}p")
        except Exception as e:
            logger.warning(f"❌ Error checking {quality}p: {e}")

        # Har tekshirishdan keyin biroz kutish
        await asyncio.sleep(0.3)

    # Takrorlarni olib tashlash va tartiblash
    available = sorted(list(set(available)), key=lambda x: int(x))
    logger.info(f"📋 Found available qualities: {available}")
    return available

async def background_youtube_download(task_id, callback, video_id, quality_id, state):
    """Background'da YouTube yuklab olish"""
    try:
        # Progress update qilish uchun
        async def update_progress(status, progress=0, extra_info=""):
            if task_id in download_tasks:
                download_tasks[task_id]['status'] = status
                download_tasks[task_id]['progress'] = progress

                try:
                    await download_tasks[task_id]['message'].edit_text(
                        f"⏳ <b>Загрузка в процессе</b>\n\n"
                        f"🎬 <b>Видео ID:</b> {video_id}\n"
                        f"📋 <b>Качество:</b> {quality_id}\n"
                        f"⏱ <b>Статус:</b> {status}\n"
                        f"📊 <b>Прогресс:</b> {progress}%\n"
                        f"{extra_info}",
                        parse_mode="HTML"
                    )
                except:
                    pass

        # 1. Quality ma'lumotini olish
        await update_progress("Получение информации о видео", 10)
        qualities = get_available_youtube_qualities()

        if quality_id not in qualities:
            await update_progress("Ошибка: неверное качество", 0)
            return

        selected_format = qualities[quality_id]

        # 2. API dan ma'lumot olish
        await update_progress("Запрос к API", 20)
        download_data = await get_youtube_info_via_fast_api(video_id, quality_id)

        if not download_data or 'file' not in download_data:
            await update_progress("Ошибка: данные не получены", 0)
            return

        download_url = download_data['file']
        size_mb = int(download_data.get('size', 0)) / (1024 * 1024)

        # 3. Size check
        if size_mb > 50:
            await callback.message.edit_text(
                f"❌ <b>Файл слишком большой!</b>\n\n"
                f"📦 <b>Размер:</b> {size_mb:.1f} МБ\n"
                f"📏 <b>Лимит:</b> 50 МБ",
                parse_mode="HTML"
            )
            return

        # 4. Fayl tayyor bo'lishini kutish
        await update_progress("Ожидание готовности файла", 40,
                              f"\n📦 <b>Размер:</b> {size_mb:.1f} МБ")

        # 2 minut kutish
        for i in range(24):  # 24 * 5 = 120 sekund
            try:
                # Faylni tekshirish
                async with aiohttp.ClientSession() as session:
                    async with session.head(download_url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                        if resp.status == 200:
                            break
            except:
                pass

            progress = 40 + (i * 2)  # 40% dan 88% gacha
            await update_progress(f"Ожидание готовности файла ({i * 5}s)", progress,
                                  f"\n📦 <b>Размер:</b> {size_mb:.1f} МБ")
            await asyncio.sleep(5)
        else:
            await update_progress("Файл не готов", 0)
            return

        await update_progress("Загрузка и отправка файла", 90)

        try:
            await download_and_send_youtube_fast(
                callback, download_url, selected_format, video_id, size_mb
            )

            # Muvaffaqiyat xabari
            elapsed = datetime.now() - download_tasks[task_id]['start_time']
            await callback.message.edit_text(
                f"✅ <b>Файл успешно отправлен!</b>\n\n"
                f"📦 <b>Размер:</b> {size_mb:.1f} МБ\n"
                f"⏱ <b>Время:</b> {elapsed.total_seconds():.1f}s\n"
                f"📋 <b>Качество:</b> {selected_format['desc']}",
                parse_mode="HTML"
            )

        except Exception as send_error:
            logger.error(f"❌ Send error: {send_error}")
            await callback.message.edit_text(
                f"❌ <b>Ошибка при отправке</b>\n\n"
                f"💡 Попробуйте выбрать другое качество",
                parse_mode="HTML"
            )

    except Exception as e:
        logger.error(f"❌ Background task error: {e}")
        try:
            await callback.message.edit_text("❌ Ошибка при загрузке")
        except:
            pass

    finally:
        # Task'ni tozalash
        if task_id in download_tasks:
            del download_tasks[task_id]
        logger.info(f"🗑️ Task cleaned up: {task_id}")


# Task'larni tozalash uchun background service
async def cleanup_old_tasks():
    """Eski task'larni tozalash"""
    while True:
        try:
            current_time = datetime.now()
            tasks_to_remove = []

            for task_id, task_info in download_tasks.items():
                # 10 daqiqadan eski task'larni o'chirish
                if current_time - task_info['start_time'] > timedelta(minutes=10):
                    tasks_to_remove.append(task_id)
                    try:
                        task_info['task'].cancel()
                    except:
                        pass

            for task_id in tasks_to_remove:
                del download_tasks[task_id]
                logger.info(f"🗑️ Cleaned up old task: {task_id}")

            await asyncio.sleep(300)  # Har 5 daqiqada tekshirish

        except Exception as e:
            logger.error(f"❌ Cleanup error: {e}")
            await asyncio.sleep(60)


# Bot ishga tushganda cleanup service ni boshlash
async def start_cleanup_service():
    """Cleanup service ni boshlash"""
    asyncio.create_task(cleanup_old_tasks())
    logger.info("🧹 Cleanup service started")


@client_bot_router.callback_query(F.data == "yt_more_formats")
async def show_more_formats(callback: CallbackQuery):
    logger.info("🔧 More formats requested")
    await callback.answer()
    keyboard = create_more_formats_keyboard()
    await callback.message.edit_text(
        "🔧 <b>Дополнительные форматы:</b>\n\n"
        "🎬 Только видео - без звука\n"
        "📹 Видео+Аудио - полный формат",
        reply_markup=keyboard.as_markup(),
        parse_mode="HTML"
    )


@client_bot_router.callback_query(F.data == "yt_main_formats")
async def show_main_formats(callback: CallbackQuery):
    logger.info("📹 Main formats requested")
    await callback.answer()
    keyboard = create_youtube_format_keyboard()
    await callback.message.edit_text(
        "📥 <b>Основные форматы:</b>\n\n"
        "📹 = Видео + Аудио вместе",
        reply_markup=keyboard.as_markup(),
        parse_mode="HTML"
    )


async def download_and_send_youtube_fast(callback, download_url, selected_format, video_id, size_mb):
    """
    YouTube fayl yuklash va yuborish - optimallashtirilgan
    """
    temp_file = None
    try:
        # 1. Temp file yaratish
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tf:
            temp_file = tf.name

        logger.info(f"📥 Downloading to: {temp_file}")

        # 2. Progress bilan yuklab olish
        await callback.message.edit_text(
            f"📥 <b>Загрузка файла...</b>\n\n"
            f"📦 <b>Размер:</b> {size_mb:.1f} МБ\n"
            f"📊 <b>Прогресс:</b> 0%",
            parse_mode="HTML"
        )

        # 3. Faylni yuklab olish
        success = await download_file_with_progress(download_url, temp_file, callback.message)

        if not success:
            await callback.message.edit_text("❌ Ошибка при загрузке файла")
            return

        # 4. Telegram'ga yuborish - optimallashtirilgan
        logger.info("📤 Starting optimized Telegram upload...")

        # Fayl o'lchamiga qarab strategiya tanlash
        if size_mb < 10:
            # Kichik fayllar uchun oddiy yuborish
            success = await send_file_to_telegram_simple(
                callback.bot, callback.message.chat.id, temp_file,
                caption=f"🎬 {selected_format['desc']}\n📦 {size_mb:.1f} МБ"
            )
        else:
            success = await send_file_to_telegram_optimized(
                callback.bot, callback.message.chat.id, temp_file,
                callback.message, f"🎬 {selected_format['desc']}\n📦 {size_mb:.1f} МБ"
            )

        if success:
            logger.info("✅ File sent successfully")
        else:
            await callback.message.edit_text("❌ Ошибка при отправке файла")

    except Exception as e:
        logger.error(f"❌ Download and send error: {e}")
        await callback.message.edit_text("❌ Ошибка при загрузке")

    finally:
        # 5. Temp file'ni o'chirish
        if temp_file and os.path.exists(temp_file):
            try:
                os.unlink(temp_file)
                logger.info("🗑️ Temp file cleaned up")
            except:
                pass


async def send_file_to_telegram_simple(bot, chat_id, file_path, caption=""):
    try:
        logger.info("📤 Using simple upload for small file")
        with open(file_path, 'rb') as f:
            document = BufferedInputFile(f.read(), filename=os.path.basename(file_path))
            await bot.send_document(
                chat_id=chat_id,
                document=document,
                caption=caption,
                request_timeout=120
            )
        return True

    except Exception as e:
        logger.error(f"❌ Simple upload error: {e}")
        return False


async def send_file_to_telegram_optimized(bot, chat_id, file_path, message_to_edit, caption=""):
    """
    Katta fayllar uchun optimallashtirilgan yuborish
    """
    try:
        file_size = os.path.getsize(file_path)
        filename = os.path.basename(file_path)

        logger.info("📤 Using optimized upload for large file")

        # Connection optimization
        connector = aiohttp.TCPConnector(
            limit=1,  # Bitta connection
            limit_per_host=1,  # Host uchun 1ta
            keepalive_timeout=300,  # 5 minut keepalive
            enable_cleanup_closed=True,
            force_close=False,  # Connection'ni berkitmaslik
            ssl=False  # SSL muammosini hal qilish
        )

        # Timeout optimization
        timeout = aiohttp.ClientTimeout(
            total=None,  # Jami timeout yo'q
            connect=30,  # Connect 30s
            sock_read=300,  # Read 5 minut
            sock_connect=30  # Socket connect 30s
        )

        # Custom session yaratish
        session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout
        )

        # Bot object'ini yangi session bilan yangilash
        old_session = bot.session
        bot.session = session

        try:
            # Progress callback
            uploaded_size = 0
            last_progress = 0

            async def update_progress(chunk_size):
                nonlocal uploaded_size, last_progress
                uploaded_size += chunk_size
                progress = (uploaded_size / file_size) * 100

                # Har 15% da update
                if progress - last_progress >= 15:
                    try:
                        await message_to_edit.edit_text(
                            f"📤 <b>Отправка файла...</b>\n\n"
                            f"📁 <b>Файл:</b> {filename}\n"
                            f"📦 <b>Размер:</b> {file_size / 1024 / 1024:.1f} МБ\n"
                            f"📊 <b>Прогресс:</b> {progress:.1f}%\n"
                            f"⚡ <b>Загружено:</b> {uploaded_size / 1024 / 1024:.1f} МБ",
                            parse_mode="HTML"
                        )
                        last_progress = progress
                    except:
                        pass

            # Upload progress boshida
            await update_progress(0)

            # Faylni o'qish va yuborish
            with open(file_path, 'rb') as f:
                document = BufferedInputFile(f.read(), filename=filename)

                # Yuborish
                await bot.send_document(
                    chat_id=chat_id,
                    document=document,
                    caption=caption,
                    request_timeout=300  # 5 minut timeout
                )

                # 100% progress
                await update_progress(file_size - uploaded_size)

            logger.info("✅ File sent successfully with optimized upload")
            return True

        finally:
            # Session'ni qaytarish
            await session.close()
            bot.session = old_session

    except Exception as e:
        logger.error(f"❌ Optimized upload error: {e}")
        return False


async def download_file_with_progress(url, file_path, message):
    """
    Progress bilan fayl yuklab olish - eski nom
    """
    try:
        # Connection settings
        connector = aiohttp.TCPConnector(
            keepalive_timeout=300,
            enable_cleanup_closed=True,
            ssl=False  # SSL muammolarini hal qilish
        )

        timeout = aiohttp.ClientTimeout(
            total=300,  # 5 minut total
            connect=30,  # Connect 30s
            sock_read=60  # Read 1 minut
        )

        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            async with session.get(url) as response:
                if response.status != 200:
                    logger.error(f"❌ HTTP {response.status} error")
                    return False

                total_size = int(response.headers.get('content-length', 0))
                downloaded = 0
                last_progress = 0

                logger.info(f"📥 Starting download: {total_size / 1024 / 1024:.1f} MB")

                with open(file_path, 'wb') as f:
                    async for chunk in response.content.iter_chunked(1024 * 1024):  # 1MB chunks
                        f.write(chunk)
                        downloaded += len(chunk)

                        if total_size > 0:
                            progress = (downloaded / total_size) * 100

                            # Har 20% da update
                            if progress - last_progress >= 20:
                                try:
                                    await message.edit_text(
                                        f"📥 <b>Загрузка файла...</b>\n\n"
                                        f"📦 <b>Размер:</b> {total_size / 1024 / 1024:.1f} МБ\n"
                                        f"📊 <b>Прогресс:</b> {progress:.1f}%\n"
                                        f"⚡ <b>Скорость:</b> Загружается...",
                                        parse_mode="HTML"
                                    )
                                    last_progress = progress
                                except:
                                    pass

                logger.info(f"✅ Download completed: {downloaded / 1024 / 1024:.1f} MB")
                return True

    except asyncio.TimeoutError:
        logger.error("❌ Download timeout")
        return False
    except Exception as e:
        logger.error(f"❌ Download error: {e}")
        return False


from modul.loader import client_bot_router
from aiogram import F
import json
RAPIDAPI_KEY = "532d0e9edemsh5566c31aceb7163p1343e7jsn11577b0723dd"
RAPIDAPI_HOST = "youtube-video-fast-downloader-24-7.p.rapidapi.com"


def extract_youtube_id(url):
    """YouTube URL dan video ID ni olish"""
    logger.info(f"Extracting video ID from URL: {url}")

    patterns = [
        r'(?:youtube\.be/)([a-zA-Z0-9_-]+)',
        r'(?:youtube\.com/watch\?v=)([a-zA-Z0-9_-]+)',
        r'(?:youtube\.com/embed/)([a-zA-Z0-9_-]+)',
        r'(?:youtube\.com/v/)([a-zA-Z0-9_-]+)',
        r'(?:youtube\.com/shorts/)([a-zA-Z0-9_-]+)',
        r'(?:youtu\.be/)([a-zA-Z0-9_-]+)'
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            video_id = match.group(1)
            logger.info(f"✅ Video ID extracted: {video_id}")
            return video_id

    logger.error(f"❌ Could not extract video ID from: {url}")
    return None

def get_available_youtube_qualities():
    """Mavjud YouTube sifatlari"""
    return {
        "18": {"quality": "360p", "type": "progressive", "format": "MP4", "desc": "360p MP4 (Video+Audio)"},
        "22": {"quality": "720p", "type": "progressive", "format": "MP4", "desc": "720p MP4 (Video+Audio)"},
        "247": {"quality": "720p", "type": "video", "format": "WebM", "desc": "720p WebM (Video only)"},
        "248": {"quality": "1080p", "type": "video", "format": "WebM", "desc": "1080p WebM (Video only)"},
        "360": {"quality": "360p", "type": "progressive", "format": "MP4", "desc": "360p (Video+Audio)"},
        "720": {"quality": "720p", "type": "progressive", "format": "MP4", "desc": "720p (Video+Audio)"},
        "1080": {"quality": "1080p", "type": "progressive", "format": "MP4", "desc": "1080p (Video+Audio)"}
    }


async def get_youtube_info_via_fast_api(video_id, quality="247"):
    """Fast API orqali YouTube video ma'lumotlarini olish - DEBUGGING BILAN"""
    logger.info(f"🔍 API request starting...")
    logger.info(f"   Video ID: {video_id}")
    logger.info(f"   Quality: {quality}")
    logger.info(f"   API Host: {RAPIDAPI_HOST}")

    try:
        url = f"https://{RAPIDAPI_HOST}/download_short/{video_id}"
        params = {"quality": quality}
        headers = {
            "x-rapidapi-key": RAPIDAPI_KEY,
            "x-rapidapi-host": RAPIDAPI_HOST
        }

        logger.info(f"📡 Request URL: {url}")
        logger.info(f"📋 Request params: {params}")
        logger.info(f"🔑 Request headers: {headers}")

        async with aiohttp.ClientSession() as session:
            logger.info("🌐 Making HTTP request...")
            async with session.get(url, headers=headers, params=params, timeout=30) as response:
                status = response.status
                logger.info(f"📡 Response status: {status}")

                if status == 200:
                    try:
                        data = await response.json()
                        logger.info(f"✅ API Success! Response keys: {list(data.keys())}")
                        logger.info(f"📄 Full response: {json.dumps(data, indent=2)}")
                        return data
                    except Exception as json_error:
                        logger.error(f"❌ JSON parsing error: {json_error}")
                        text_response = await response.text()
                        logger.error(f"📄 Raw response: {text_response}")
                        return None
                else:
                    error_text = await response.text()
                    logger.error(f"❌ API error {status}: {error_text}")
                    return None

    except asyncio.TimeoutError:
        logger.error("⏰ API request timeout (30s)")
        return None
    except Exception as e:
        logger.error(f"❌ API request error: {type(e).__name__}: {e}")
        import traceback
        logger.error(f"📍 Traceback: {traceback.format_exc()}")
        return None


async def wait_for_youtube_file_ready(download_url, max_wait_minutes=2):
    """
    YouTube fayl tayyor bo'lishini kutish - optimallashtirilgan
    """
    try:
        max_attempts = max_wait_minutes * 12  # Har 5 sekundda tekshirish

        connector = aiohttp.TCPConnector(
            keepalive_timeout=60,
            ssl=False
        )

        timeout = aiohttp.ClientTimeout(total=10, connect=5)

        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            for attempt in range(max_attempts):
                try:
                    async with session.head(download_url) as response:
                        if response.status == 200:
                            content_length = response.headers.get('content-length')
                            if content_length and int(content_length) > 1000:  # 1KB dan katta
                                logger.info(f"✅ File ready after {attempt * 5}s")
                                return True

                except Exception as check_error:
                    logger.debug(f"🔍 Check attempt {attempt + 1} failed: {check_error}")

                if attempt < max_attempts - 1:
                    await asyncio.sleep(5)

        logger.warning(f"⏰ File not ready after {max_wait_minutes} minutes")
        return False

    except Exception as e:
        logger.error(f"❌ File ready check error: {e}")
        return False


def create_youtube_format_keyboard():
    keyboard = InlineKeyboardBuilder()
    qualities = get_available_youtube_qualities()

    # Asosiy formatlar
    popular_formats = ["22", "18", "720", "360"]

    for quality_id in popular_formats:
        if quality_id in qualities:
            fmt = qualities[quality_id]
            icon = "📹" if fmt["type"] == "progressive" else "🎬"
            button_text = f"{icon} {fmt['desc']}"
            keyboard.row(InlineKeyboardButton(
                text=button_text,
                callback_data=f"yt_fast_dl_{quality_id}"
            ))

    keyboard.row(InlineKeyboardButton(text="🔧 Другие форматы", callback_data="yt_more_formats"))
    keyboard.row(InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_download"))
    return keyboard


def create_more_formats_keyboard():
    keyboard = InlineKeyboardBuilder()
    qualities = get_available_youtube_qualities()
    additional_formats = ["1080", "247", "248"]

    for quality_id in additional_formats:
        if quality_id in qualities:
            fmt = qualities[quality_id]
            icon = "📹" if fmt["type"] == "progressive" else "🎬"
            button_text = f"{icon} {fmt['desc']}"
            keyboard.row(InlineKeyboardButton(
                text=button_text,
                callback_data=f"yt_fast_dl_{quality_id}"
            ))

    keyboard.row(InlineKeyboardButton(text="⬅️ Основные форматы", callback_data="yt_main_formats"))
    keyboard.row(InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_download"))
    return keyboard



def format_video_info(video_data):
    """Video ma'lumotlarini formatlash"""
    title = video_data.get('title', 'Video')
    channel = video_data.get('channelTitle', 'Unknown')
    duration = video_data.get('lengthSeconds', 0)
    views = video_data.get('viewCount', 0)

    # Duration formatlash
    duration_str = ""
    if duration:
        duration = int(duration)
        hours, remainder = divmod(duration, 3600)
        minutes, seconds = divmod(remainder, 60)
        if hours:
            duration_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        else:
            duration_str = f"{minutes:02d}:{seconds:02d}"

    # Views formatlash
    views_str = ""
    if views:
        views = int(views)
        if views >= 1_000_000:
            views_str = f"{views / 1_000_000:.1f}M"
        elif views >= 1_000:
            views_str = f"{views / 1_000:.1f}K"
        else:
            views_str = f"{views:,}"

    info_text = (
        f"✅ <b>Video topildi!</b>\n\n"
        f"🎥 <b>{title}</b>\n"
        f"👤 <b>Kanal:</b> {channel}\n"
        f"⏱ <b>Davomiyligi:</b> {duration_str}\n"
        f"👀 <b>Ko'rishlar:</b> {views_str}\n\n"
        f"📥 <b>Formatni tanlang:</b>\n"
        f"✅ = Video + Audio birga"
    )

    return info_text

@client_bot_router.callback_query(F.data == "cancel_download")
async def cancel_download_callback(callback: CallbackQuery, state: FSMContext):
    """Handle download cancellation"""
    await callback.message.edit_text("❌ Загрузка отменена.")
    await callback.answer("Отменено")
    await state.clear()



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
    progress_msg = await message.answer("⏳ Загружаю медиа из Instagram...")
    message_deleted = False

    try:
        # Clean up URL - remove tracking parameters
        if '?' in url:
            url = url.split('?')[0]

        # Check if URL is valid Instagram URL
        if not any(domain in url for domain in ['instagram.com', 'instagr.am', 'instagram']):
            try:
                await progress_msg.edit_text("❌ Это не похоже на ссылку Instagram")
            except Exception as e:
                logger.error(f"Error editing message: {e}")
                await message.answer("❌ Это не похоже на ссылку Instagram")
            return

        logger.info(f"Processing Instagram URL: {url}")

        # Определяем, является ли это reel или обычным постом
        is_reel = "/reel/" in url
        logger.info(f"Is this a reel? {is_reel}")

        # Create temp directory for files if it doesn't exist
        temp_dir = "/var/www/downloads"
        os.makedirs(temp_dir, exist_ok=True)

        # Generate unique ID for this request
        import hashlib
        import time
        request_id = hashlib.md5(f"{url}_{time.time()}".encode()).hexdigest()[:10]

        # Helper function to send Instagram files
        async def send_instagram_files(message, directory, files, me, bot):
            """Helper function to send downloaded Instagram files"""
            sent_count = 0
            media_files = []

            # Логируем все найденные файлы для отладки
            logger.info(f"Files in directory {directory}: {files}")

            # Проверяем, содержит ли имя директории или файлы слово "reel" - это поможет определить видео
            is_file_reel = "reel" in directory.lower() or any("reel" in f.lower() for f in files)
            logger.info(f"Files indicate reel: {is_file_reel}")

            # First sort files to ensure correct order and filter unwanted files
            for f in sorted(files):
                filepath = os.path.join(directory, f)
                if not os.path.isfile(filepath):
                    continue

                # Skip small files and metadata files
                filesize = os.path.getsize(filepath)
                if filesize < 1000 or '.json' in f or '.txt' in f:
                    continue

                # Determine file type by extension
                ext = os.path.splitext(f)[1].lower()

                # Determine if this is a video by file extension
                if ext in ['.mp4', '.mov', '.webm']:
                    media_type = 'video'
                elif ext in ['.jpg', '.jpeg', '.png', '.webp']:
                    # If we know this is a reel but file is an image, it's a thumbnail
                    media_type = 'thumbnail' if (is_reel or is_file_reel) else 'photo'
                else:
                    # Log unusual extensions for analysis
                    logger.info(f"Unusual file extension found: {ext} in file {f}")
                    continue

                media_files.append((filepath, media_type))

            # Then send files
            total_files = len(media_files)
            logger.info(f"Found {total_files} media files in directory {directory}")

            for i, (filepath, media_type) in enumerate(media_files):
                try:
                    logger.info(f"Sending file {i + 1}/{total_files}: {filepath} as {media_type}")

                    if media_type == 'video':
                        try:
                            await bot.send_video(
                                chat_id=message.chat.id,
                                video=FSInputFile(filepath),
                                caption=f"📹 Instagram видео {i + 1}/{total_files}\nСкачано через @{me.username}"
                            )
                            sent_count += 1
                        except Exception as video_error:
                            logger.error(f"Error sending as video, trying as document: {video_error}")
                            await bot.send_document(
                                chat_id=message.chat.id,
                                document=FSInputFile(filepath),
                                caption=f"📹 Instagram видео {i + 1}/{total_files}\nСкачано через @{me.username}"
                            )
                            sent_count += 1
                    elif media_type == 'thumbnail':
                        await bot.send_photo(
                            chat_id=message.chat.id,
                            photo=FSInputFile(filepath),
                            caption=f"🎞 Instagram превью видео {i + 1}/{total_files}\nСкачано через @{me.username}"
                        )
                        sent_count += 1
                    else:  # photo
                        await bot.send_photo(
                            chat_id=message.chat.id,
                            photo=FSInputFile(filepath),
                            caption=f"🖼 Instagram фото {i + 1}/{total_files}\nСкачано через @{me.username}"
                        )
                        sent_count += 1

                    # Add small delay between posts
                    await asyncio.sleep(0.5)
                except Exception as e:
                    logger.error(f"Error sending file {filepath}: {e}")

                    # Try alternate method if primary fails
                    try:
                        await bot.send_document(
                            chat_id=message.chat.id,
                            document=FSInputFile(filepath),
                            caption=f"📄 Instagram медиа {i + 1}/{total_files}\nСкачано через @{me.username}"
                        )
                        sent_count += 1
                    except Exception as fallback_error:
                        logger.error(f"Fallback error for file {filepath}: {fallback_error}")

            return sent_count > 0

        # Безопасное редактирование сообщения
        async def safe_edit_message(msg, text):
            nonlocal message_deleted
            if not message_deleted:
                try:
                    await msg.edit_text(text)
                except Exception as e:
                    logger.error(f"Error editing message: {e}")
                    message_deleted = True
                    await message.answer(text)

        # First, try direct API method if this is a reel (fastest method)
        if is_reel:
            await safe_edit_message(progress_msg, "🔍 Использую прямой API метод для reel...")

            try:
                import re
                import aiohttp

                # Extract shortcode
                match = re.search(r'/reel/([^/]+)', url)
                if match:
                    shortcode = match.group(1)

                    # Try specialized API endpoint for reels
                    api_url = f"https://www.instagram.com/graphql/query/?query_hash=b3055c01b4b222b8a47dc12b090e4e64&variables={{\"shortcode\":\"{shortcode}\"}}"

                    headers = {
                        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 12_3_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 Instagram 105.0.0.11.118 (iPhone11,8; iOS 12_3_1; en_US; en-US; scale=2.00; 828x1792; 165586599)",
                        "Accept": "*/*",
                        "Accept-Language": "en-US,en;q=0.5",
                        "Origin": "https://www.instagram.com",
                        "Referer": url,
                        "x-ig-app-id": "936619743392459",
                    }

                    async with aiohttp.ClientSession() as session:
                        async with session.get(api_url, headers=headers, timeout=10) as response:
                            if response.status == 200:
                                data = await response.json()

                                if 'data' in data and 'shortcode_media' in data['data']:
                                    media = data['data']['shortcode_media']

                                    if media.get('is_video') and 'video_url' in media:
                                        video_url = media['video_url']
                                        logger.info(f"Found video URL via API: {video_url}")

                                        try:
                                            await bot.send_video(
                                                chat_id=message.chat.id,
                                                video=video_url,
                                                caption=f"📹 Instagram видео\nСкачано через @{me.username}"
                                            )
                                            await shortcuts.add_to_analitic_data(me.username, url)
                                            try:
                                                await progress_msg.delete()
                                                message_deleted = True
                                            except:
                                                pass
                                            return
                                        except Exception as video_err:
                                            logger.error(f"Error sending video: {video_err}")

                                    # If video not found but we have image
                                    if 'display_url' in media:
                                        display_url = media['display_url']
                                        logger.info(f"Found image URL via API: {display_url}")

                                        try:
                                            await bot.send_photo(
                                                chat_id=message.chat.id,
                                                photo=display_url,
                                                caption=f"🎞 Instagram превью видео\nСкачано через @{me.username}"
                                            )
                                            await shortcuts.add_to_analitic_data(me.username, url)
                                            try:
                                                await progress_msg.delete()
                                                message_deleted = True
                                            except:
                                                pass
                                            return
                                        except Exception as photo_err:
                                            logger.error(f"Error sending image: {photo_err}")
            except Exception as e:
                logger.error(f"Direct API method error: {e}")

        # Approach 1: Direct instaloader method (using Python subprocess)
        await safe_edit_message(progress_msg, "🔍 Загружаю через instaloader (метод 1/3)...")

        try:
            # Check if instaloader is installed
            instaloader_present = False
            try:
                subprocess.run(["instaloader", "--version"], capture_output=True, text=True, check=True)
                instaloader_present = True
            except (subprocess.SubprocessError, FileNotFoundError):
                logger.info("Instaloader not found, skipping method 1")

            if instaloader_present:
                # Extract shortcode from URL
                import re
                match = re.search(r'/(p|reel)/([^/]+)', url)
                if not match:
                    logger.warning(f"Could not extract shortcode from URL: {url}")
                else:
                    shortcode = match.group(2)
                    output_dir = os.path.join(temp_dir, f"insta_{request_id}")
                    os.makedirs(output_dir, exist_ok=True)

                    # Try to download using instaloader
                    cmd = [
                        "instaloader",
                        "--no-metadata-json",
                        "--no-captions",
                        "--no-video-thumbnails",
                        "--login", "anonymous",
                        f"--dirname-pattern={output_dir}",
                        f"--filename-pattern={shortcode}",
                        f"-- -{shortcode}"  # Format for downloading by shortcode
                    ]

                    try:
                        process = await asyncio.create_subprocess_exec(
                            *cmd,
                            stdout=asyncio.subprocess.PIPE,
                            stderr=asyncio.subprocess.PIPE
                        )
                        stdout, stderr = await process.communicate()

                        if process.returncode == 0:
                            # Find downloaded files
                            files = os.listdir(output_dir)

                            if files:
                                success = await send_instagram_files(message, output_dir, files, me, bot)
                                if success:
                                    await shortcuts.add_to_analitic_data(me.username, url)
                                    try:
                                        await progress_msg.delete()
                                        message_deleted = True
                                    except:
                                        pass
                                    # Clean up
                                    shutil.rmtree(output_dir, ignore_errors=True)
                                    return
                    except Exception as e:
                        logger.error(f"Instaloader error: {e}")
        except Exception as e:
            logger.error(f"Approach 1 error: {e}")

        # Approach 2: Gallery-dl method (external tool)
        await safe_edit_message(progress_msg, "🔍 Загружаю через gallery-dl (метод 2/3)...")

        try:
            # Check if gallery-dl is installed
            gallery_dl_present = False
            try:
                subprocess.run(["gallery-dl", "--version"], capture_output=True, text=True, check=True)
                gallery_dl_present = True
            except (subprocess.SubprocessError, FileNotFoundError):
                logger.info("Gallery-dl not found, skipping method 2")

            if gallery_dl_present:
                output_dir = os.path.join(temp_dir, f"insta_{request_id}")
                os.makedirs(output_dir, exist_ok=True)

                # Try to download using gallery-dl
                cmd = [
                    "gallery-dl",
                    "--cookies", "none",
                    "--dest", output_dir,
                    url
                ]

                try:
                    process = await asyncio.create_subprocess_exec(
                        *cmd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    stdout, stderr = await process.communicate()

                    # Check if files were downloaded
                    files = os.listdir(output_dir)

                    if files:
                        success = await send_instagram_files(message, output_dir, files, me, bot)
                        if success:
                            await shortcuts.add_to_analitic_data(me.username, url)
                            try:
                                await progress_msg.delete()
                                message_deleted = True
                            except:
                                pass
                            # Clean up
                            shutil.rmtree(output_dir, ignore_errors=True)
                            return
                except Exception as e:
                    logger.error(f"Gallery-dl error: {e}")
        except Exception as e:
            logger.error(f"Approach 2 error: {e}")

        # Approach 3: youtube-dl / yt-dlp method (fallback)
        await safe_edit_message(progress_msg, "🔍 Загружаю через yt-dlp (метод 3/3)...")

        try:
            output_file = os.path.join(temp_dir, f"insta_{request_id}")

            # Advanced yt-dlp options with writethumbnail
            ydl_opts = {
                'format': 'best',
                'outtmpl': f"{output_file}.%(ext)s",
                'writethumbnail': True,  # Save thumbnails too
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False,
                'http_headers': {
                    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Mobile/15E148 Safari/604.1',
                    'Accept': '*/*',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Referer': 'https://www.instagram.com/',
                    'Origin': 'https://www.instagram.com',
                    'x-ig-app-id': '936619743392459',
                }
            }

            # Попробуем сначала без cookie
            try:
                no_cookie_opts = ydl_opts.copy()

                with YoutubeDL(no_cookie_opts) as ydl:
                    await asyncio.get_event_loop().run_in_executor(
                        executor,
                        lambda: ydl.extract_info(url, download=True)
                    )
            except Exception as no_cookie_error:
                logger.error(f"Failed without cookies: {no_cookie_error}")

                # Try with cookies
                cookies_file = os.path.join(temp_dir, f"cookies_{request_id}.txt")
                with open(cookies_file, "w") as f:
                    f.write("""# Netscape HTTP Cookie File
.instagram.com\tTRUE\t/\tFALSE\t1999999999\tcsrftoken\tsomerandomcsrftoken
.instagram.com\tTRUE\t/\tFALSE\t1999999999\tmid\tYf8XQgABAAHaJf3kDKq0ZiVw4YHl
.instagram.com\tTRUE\t/\tFALSE\t1999999999\tds_user_id\t1234567890
.instagram.com\tTRUE\t/\tFALSE\t1999999999\tsessionid\t1234567890%3A12345abcdef%3A1
""")
                ydl_opts['cookiefile'] = cookies_file

                try:
                    with YoutubeDL(ydl_opts) as ydl:
                        await asyncio.get_event_loop().run_in_executor(
                            executor,
                            lambda: ydl.extract_info(url, download=True)
                        )
                except Exception as e:
                    logger.error(f"Failed with cookies too: {e}")

            # Check for downloaded files - first check for videos
            media_found = False

            # First check for video files
            for ext in ['mp4', 'webm', 'mov']:
                filepath = f"{output_file}.{ext}"
                if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
                    logger.info(f"Found video file: {filepath} size: {os.path.getsize(filepath)}")
                    try:
                        await bot.send_video(
                            chat_id=message.chat.id,
                            video=FSInputFile(filepath),
                            caption=f"📹 Instagram видео\nСкачано через @{me.username}"
                        )
                        media_found = True
                        await shortcuts.add_to_analitic_data(me.username, url)
                        try:
                            await progress_msg.delete()
                            message_deleted = True
                        except:
                            pass
                        break
                    except Exception as send_error:
                        logger.error(f"Error sending video: {send_error}")
                        # Try as document if video fails
                        try:
                            await bot.send_document(
                                chat_id=message.chat.id,
                                document=FSInputFile(filepath),
                                caption=f"📹 Instagram видео\nСкачано через @{me.username}"
                            )
                            media_found = True
                            await shortcuts.add_to_analitic_data(me.username, url)
                            try:
                                await progress_msg.delete()
                                message_deleted = True
                            except:
                                pass
                            break
                        except Exception as doc_error:
                            logger.error(f"Error sending as document: {doc_error}")
                    finally:
                        try:
                            if os.path.exists(filepath):
                                os.remove(filepath)
                        except:
                            pass

            # If no video found, check for images
            if not media_found:
                image_files = []
                for ext in ['jpg', 'jpeg', 'png', 'webp']:
                    # Check direct filename matches
                    filepath = f"{output_file}.{ext}"
                    if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
                        image_files.append(filepath)

                    # Also check for alternate filenames (like thumbnails)
                    for alt_file in glob.glob(f"{output_file}*.{ext}"):
                        if os.path.exists(alt_file) and os.path.getsize(alt_file) > 0:
                            image_files.append(alt_file)

                # Sort by size - larger files first (usually better quality)
                image_files.sort(key=lambda f: os.path.getsize(f), reverse=True)

                for filepath in image_files:
                    try:
                        logger.info(f"Found image file: {filepath} size: {os.path.getsize(filepath)}")

                        # Determine if this is a reel thumbnail or regular photo
                        caption = "🎞 Instagram превью видео" if is_reel else "🖼 Instagram фото"

                        await bot.send_photo(
                            chat_id=message.chat.id,
                            photo=FSInputFile(filepath),
                            caption=f"{caption}\nСкачано через @{me.username}"
                        )
                        media_found = True
                        await shortcuts.add_to_analitic_data(me.username, url)
                        try:
                            await progress_msg.delete()
                            message_deleted = True
                        except:
                            pass
                        break
                    except Exception as send_error:
                        logger.error(f"Error sending image: {send_error}")
                        # Try as document if photo fails
                        try:
                            await bot.send_document(
                                chat_id=message.chat.id,
                                document=FSInputFile(filepath),
                                caption=f"{caption}\nСкачано через @{me.username}"
                            )
                            media_found = True
                            await shortcuts.add_to_analitic_data(me.username, url)
                            try:
                                await progress_msg.delete()
                                message_deleted = True
                            except:
                                pass
                            break
                        except Exception as doc_error:
                            logger.error(f"Error sending as document: {doc_error}")
                    finally:
                        try:
                            if os.path.exists(filepath):
                                os.remove(filepath)
                        except:
                            pass

            # Clean up all related files
            for f in glob.glob(f"{output_file}*"):
                try:
                    if os.path.exists(f):
                        os.remove(f)
                except:
                    pass

            # Clean up cookies file if it exists
            cookies_file = os.path.join(temp_dir, f"cookies_{request_id}.txt")
            try:
                if os.path.exists(cookies_file):
                    os.remove(cookies_file)
            except:
                pass

            if media_found:
                return

        except Exception as e:
            logger.error(f"Approach 3 error: {e}")

        # If all approaches failed, try one final direct API request for thumbnails
        try:
            await safe_edit_message(progress_msg, "🔍 Использую запасной метод...")

            import re
            import aiohttp

            # Extract shortcode
            match = re.search(r'/(p|reel)/([^/]+)', url)
            if match:
                shortcode = match.group(2)
                post_type = match.group(1)

                # Try OEmbed API - works well for thumbnails
                oembed_url = f"https://api.instagram.com/oembed/?url=https://www.instagram.com/{post_type}/{shortcode}/"

                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                    "Accept": "application/json",
                }

                async with aiohttp.ClientSession() as session:
                    async with session.get(oembed_url, headers=headers, timeout=10) as response:
                        if response.status == 200:
                            try:
                                data = await response.json()

                                if 'thumbnail_url' in data:
                                    thumbnail_url = data['thumbnail_url']
                                    logger.info(f"Found thumbnail URL via OEmbed: {thumbnail_url}")

                                    caption = "🎞 Instagram превью видео" if is_reel else "🖼 Instagram фото"

                                    try:
                                        await bot.send_photo(
                                            chat_id=message.chat.id,
                                            photo=thumbnail_url,
                                            caption=f"{caption}\nСкачано через @{me.username}"
                                        )
                                        await shortcuts.add_to_analitic_data(me.username, url)
                                        try:
                                            await progress_msg.delete()
                                            message_deleted = True
                                        except:
                                            pass
                                        return
                                    except Exception as photo_err:
                                        logger.error(f"Error sending image: {photo_err}")
                            except Exception as json_error:
                                logger.error(f"JSON parsing error: {json_error}")
        except Exception as e:
            logger.error(f"Final fallback method error: {e}")

        # If all approaches failed, send error message
        if not message_deleted:
            try:
                await progress_msg.delete()
                message_deleted = True
            except:
                pass

        await message.answer(
            "❌ Не удалось загрузить медиа из Instagram. Instagram часто блокирует подобные загрузки. Попробуйте другой пост или позже.")

    except Exception as e:
        logger.error(f"Instagram handler error: {e}")
        if not message_deleted:
            try:
                await progress_msg.delete()
            except:
                pass

        await message.answer("❌ Ошибка при скачивании из Instagram. Возможно, пост приватный или удалён.")


async def send_instagram_files(message, directory, files, me, bot):
    """Helper function to send downloaded Instagram files"""
    sent_count = 0
    media_files = []

    # Логируем все найденные файлы для отладки
    logger.info(f"Files in directory {directory}: {files}")

    # Проверяем, содержит ли имя директории "reel" - это поможет нам определить, что это видео
    is_reel = "reel" in directory.lower() or any("reel" in f.lower() for f in files)
    logger.info(f"Is this a reel? {is_reel}")

    # First sort files to ensure correct order and filter unwanted files
    for f in sorted(files):
        filepath = os.path.join(directory, f)
        if not os.path.isfile(filepath):
            continue

        # Skip small files and metadata files
        filesize = os.path.getsize(filepath)
        if filesize < 1000 or '.json' in f or '.txt' in f:
            continue

        # Determine file type by extension
        ext = os.path.splitext(f)[1].lower()

        # Determine if this is a video by file extension
        if ext in ['.mp4', '.mov', '.webm']:
            media_type = 'video'
        elif ext in ['.jpg', '.jpeg', '.png', '.webp']:
            # If we know this is a reel but file is an image, it's a thumbnail
            media_type = 'thumbnail' if is_reel else 'photo'
        else:
            # Log unusual extensions for analysis
            logger.info(f"Unusual file extension found: {ext} in file {f}")
            continue

        media_files.append((filepath, media_type))

    # Then send files
    total_files = len(media_files)
    logger.info(f"Found {total_files} media files in directory {directory}")

    for i, (filepath, media_type) in enumerate(media_files):
        try:
            logger.info(f"Sending file {i + 1}/{total_files}: {filepath} as {media_type}")

            if media_type == 'video':
                try:
                    await bot.send_video(
                        chat_id=message.chat.id,
                        video=FSInputFile(filepath),
                        caption=f"📹 Instagram видео {i + 1}/{total_files}\nСкачано через @{me.username}"
                    )
                    sent_count += 1
                except Exception as video_error:
                    logger.error(f"Error sending as video, trying as document: {video_error}")
                    await bot.send_document(
                        chat_id=message.chat.id,
                        document=FSInputFile(filepath),
                        caption=f"📹 Instagram видео {i + 1}/{total_files}\nСкачано через @{me.username}"
                    )
                    sent_count += 1
            elif media_type == 'thumbnail':
                await bot.send_photo(
                    chat_id=message.chat.id,
                    photo=FSInputFile(filepath),
                    caption=f"🎞 Instagram превью видео {i + 1}/{total_files}\nСкачано через @{me.username}"
                )
                sent_count += 1
            else:  # photo
                await bot.send_photo(
                    chat_id=message.chat.id,
                    photo=FSInputFile(filepath),
                    caption=f"🖼 Instagram фото {i + 1}/{total_files}\nСкачано через @{me.username}"
                )
                sent_count += 1

            # Add small delay between posts
            await asyncio.sleep(0.5)
        except Exception as e:
            logger.error(f"Error sending file {filepath}: {e}")

            # Try alternate method if primary fails
            try:
                await bot.send_document(
                    chat_id=message.chat.id,
                    document=FSInputFile(filepath),
                    caption=f"📄 Instagram медиа {i + 1}/{total_files}\nСкачано через @{me.username}"
                )
                sent_count += 1
            except Exception as fallback_error:
                logger.error(f"Fallback error for file {filepath}: {fallback_error}")

    return sent_count > 0


async def download_and_send_video(message: Message, url: str, ydl_opts: dict, me, bot: Bot, platform: str,state: FSMContext):
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
                    await state.set_state(Download.download)
                finally:
                    # Всегда удаляем файл после отправки
                    if os.path.exists(video_path):
                        os.remove(video_path)
            else:
                raise FileNotFoundError("Downloaded video file not found")

    except Exception as e:
        logger.error(f"Error downloading and sending video from {platform}: {e}")
        await message.answer(f"❌ Не удалось скачать видео из {platform}")


async def handle_tiktok(message: Message, url: str, me, bot: Bot,state: FSMContext):
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
                        await state.set_state(Download.download)
                        await shortcuts.add_to_analitic_data(me.username, url)
                        return
                    except Exception:

                        await download_and_send_video(message, url, ydl_opts, me, bot, "TikTok",state)
                else:
                    await message.answer("❌ Не удалось получить ссылку на видео")

            except Exception as e:
                logger.error(f"TikTok processing error: {e}")
                await message.answer("❌ Ошибка при скачивании из TikTok")

    except Exception as e:
        logger.error(f"TikTok handler error: {e}")
        await message.answer("❌ Ошибка при обработке TikTok видео")

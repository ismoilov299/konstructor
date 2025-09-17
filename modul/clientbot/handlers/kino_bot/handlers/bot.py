import glob 
import asyncio
import json
import subprocess
import tempfile
import time
import traceback
from contextlib import suppress
import shutil

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


class UnifiedSocialDownloader:
    def __init__(self):
        self.api_key = "532d0e9edemsh5566c31aceb7163p1343e7jsn11577b0723dd"
        self.api_host = "social-download-all-in-one.p.rapidapi.com"
        self.base_url = f"https://{self.api_host}/v1/social"

        self.headers = {
            "x-rapidapi-key": self.api_key,
            "x-rapidapi-host": self.api_host,
            "Content-Type": "application/json"
        }

    def get_platform_from_url(self, url: str):
        """Определение платформы по URL"""
        url_lower = url.lower()
        if 'youtube.com' in url_lower or 'youtu.be' in url_lower:
            return 'youtube'
        elif 'instagram.com' in url_lower or 'instagr.am' in url_lower or 'inst.ae' in url_lower:
            return 'instagram'
        elif 'tiktok.com' in url_lower:
            return 'tiktok'
        elif 'twitter.com' in url_lower or 'x.com' in url_lower:
            return 'twitter'
        elif 'facebook.com' in url_lower or 'fb.watch' in url_lower:
            return 'facebook'
        elif 'reddit.com' in url_lower:
            return 'reddit'
        elif 'vimeo.com' in url_lower:
            return 'vimeo'
        else:
            return 'unknown'

    async def download_media(self, url: str):
        """DEBUG: API запрос с подробным логированием"""
        logger.info(f"🔍 API REQUEST START")
        logger.info(f"📍 URL: {url}")
        logger.info(f"🌐 API Host: {self.api_host}")

        try:
            payload = {"url": url}
            logger.info(f"📋 Payload: {payload}")

            async with aiohttp.ClientSession() as session:
                logger.info(f"📡 Making POST request...")

                async with session.post(f"{self.base_url}/autolink", json=payload, headers=self.headers,
                                        timeout=30) as response:
                    status = response.status
                    logger.info(f"📊 Response status: {status}")

                    if response.status == 200:
                        data = await response.json()
                        logger.info(f"✅ API SUCCESS")
                        logger.info(f"🔍 Response keys: {list(data.keys())}")
                        logger.info(f"📝 Title: {data.get('title', 'N/A')}")
                        logger.info(f"📱 Source: {data.get('source', 'N/A')}")
                        logger.info(f"🎥 Medias count: {len(data.get('medias', []))}")
                        logger.info(f"❌ Error flag: {data.get('error', 'N/A')}")

                        # Log first few medias
                        medias = data.get('medias', [])
                        for i, media in enumerate(medias[:3]):
                            logger.info(
                                f"🎬 Media {i + 1}: {media.get('label', 'N/A')} - {media.get('type', 'N/A')} - FormatID: {media.get('formatId', 'N/A')}")

                        if not data.get('error', True):
                            return {'success': True, 'data': data}
                        else:
                            error_msg = data.get('message', 'API error')
                            logger.error(f"❌ API returned error: {error_msg}")
                            return {'success': False, 'error': error_msg}
                    else:
                        error_text = await response.text()
                        logger.error(f"❌ HTTP Error {status}: {error_text}")
                        return {'success': False, 'error': f'HTTP {status}: {error_text}'}

        except Exception as e:
            logger.error(f"❌ Exception in API request: {type(e).__name__}: {e}")
            import traceback
            logger.error(f"📍 Traceback: {traceback.format_exc()}")
            return {'success': False, 'error': str(e)}

    async def download_file(self, file_url: str, max_size_mb: int = 50):
        """DEBUG: Скачивание файла с подробным логированием"""
        logger.info(f"⬇️ FILE DOWNLOAD START")
        logger.info(f"🔗 URL: {file_url[:100]}...")
        logger.info(f"📏 Max size: {max_size_mb} MB")

        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': '*/*',
                'Connection': 'keep-alive'
            }

            logger.info(f"🌐 Creating session...")
            async with aiohttp.ClientSession() as session:
                logger.info(f"📡 Making GET request...")

                async with session.get(file_url, headers=headers, timeout=60) as response:
                    status = response.status
                    logger.info(f"📊 Response status: {status}")

                    # Headers info
                    content_length = response.headers.get('content-length')
                    content_type = response.headers.get('content-type')
                    logger.info(f"📦 Content-Length: {content_length}")
                    logger.info(f"📄 Content-Type: {content_type}")

                    if response.status == 200:
                        if content_length:
                            size_mb = int(content_length) / (1024 * 1024)
                            logger.info(f"📏 File size: {size_mb:.2f} MB")

                            if size_mb > max_size_mb:
                                logger.error(f"❌ File too large: {size_mb:.2f} MB > {max_size_mb} MB")
                                return None

                            logger.info(f"✅ File size OK, downloading...")
                        else:
                            logger.warning(f"⚠️ No content-length header, downloading anyway...")

                        data = await response.read()
                        actual_size = len(data) / (1024 * 1024)
                        logger.info(f"✅ Downloaded successfully: {actual_size:.2f} MB")
                        return data

                    else:
                        logger.error(f"❌ Download failed with status: {status}")
                        response_text = await response.text()
                        logger.error(f"📄 Response: {response_text[:200]}...")
                        return None

        except Exception as e:
            logger.error(f"❌ Exception in file download: {type(e).__name__}: {e}")
            import traceback
            logger.error(f"📍 Traceback: {traceback.format_exc()}")
            return None


# Global instance
unified_downloader = UnifiedSocialDownloader()

@client_bot_router.message(DownloaderBotFilter())
@client_bot_router.message(Download.download)
async def unified_download_handler(message: Message, state: FSMContext, bot: Bot):
    """Единый handler для всех платформ"""
    if not message.text:
        await message.answer("❗ Отправьте ссылку на видео")
        return

    url = message.text.strip()
    me = await bot.get_me()

    # Определяем платформу
    platform = unified_downloader.get_platform_from_url(url)

    if platform == 'unknown':
        await message.answer(
            "❗ Поддерживаются только YouTube, Instagram, TikTok, Twitter, Facebook, Reddit и Vimeo ссылки")
        return

    # YOUTUBE - показываем форматы для выбора
    if platform == 'youtube':
        await handle_youtube_unified(message, url, me, bot, state)

    # ВСЕ ОСТАЛЬНЫЕ - автоматически лучший формат
    else:
        await handle_other_platforms_unified(message, url, me, bot, state, platform)


async def handle_youtube_unified(message: Message, url: str, me, bot: Bot, state: FSMContext):
    """YouTube handler с логированием"""
    logger.info(f"🎯 YOUTUBE HANDLER START")
    logger.info(f"🔗 URL: {url}")
    logger.info(f"👤 User: {message.from_user.id}")

    progress_msg = await message.answer("📡 Анализирую YouTube видео...")

    try:
        # Получаем данные через unified API
        logger.info(f"📡 Getting data from API...")
        result = await unified_downloader.download_media(url)

        logger.info(f"🔍 API result success: {result.get('success')}")

        if not result['success']:
            error_msg = result['error']
            logger.error(f"❌ API failed: {error_msg}")
            await progress_msg.edit_text(f"❌ Не удалось получить данные: {error_msg}")
            return

        data = result['data']
        title = data.get('title', 'YouTube видео')
        duration = data.get('duration', 0)
        medias = data.get('medias', [])

        logger.info(f"📝 Title: {title}")
        logger.info(f"⏱ Duration: {duration}")
        logger.info(f"🎥 Medias count: {len(medias)}")

        if not medias:
            logger.error(f"❌ No medias found")
            await progress_msg.edit_text("❌ Форматы не найдены")
            return

        await progress_msg.edit_text("🔍 Обрабатываю доступные форматы...")

        # Анализ форматов
        logger.info(f"🔍 ANALYZING FORMATS:")
        video_with_audio = []
        video_only = []
        audio_only = []

        for i, media in enumerate(medias):
            media_type = media.get('type', '')
            has_audio = media.get('is_audio', False)
            format_id = media.get('formatId')
            label = media.get('label', 'N/A')

            logger.info(f"🎬 Format {i}: ID={format_id}, Type={media_type}, Audio={has_audio}, Label={label}")

            if media_type == 'video' and has_audio:
                video_with_audio.append(media)
                logger.info(f"  ✅ Added to video_with_audio")
            elif media_type == 'video' and not has_audio:
                video_only.append(media)
                logger.info(f"  ✅ Added to video_only")
            elif media_type == 'audio':
                audio_only.append(media)
                logger.info(f"  ✅ Added to audio_only")
            else:
                logger.info(f"  ⚠️ Uncategorized format")

        logger.info(f"📊 CATEGORIZATION RESULTS:")
        logger.info(f"📹 Video with audio: {len(video_with_audio)}")
        logger.info(f"🎬 Video only: {len(video_only)}")
        logger.info(f"🎵 Audio only: {len(audio_only)}")

        # Создание кнопок
        keyboard = InlineKeyboardBuilder()

        # 1. Видео с аудио (приоритет)
        if video_with_audio:
            keyboard.row(InlineKeyboardButton(
                text="📹 Готовые форматы (Видео + Аудио)",
                callback_data="yt_section_ready"
            ))

            for media in video_with_audio[:5]:
                label = media.get('label', 'Unknown')
                format_id = media.get('formatId', 0)

                logger.info(f"🔘 Adding button: {label} (ID: {format_id})")

                keyboard.row(InlineKeyboardButton(
                    text=f"📹 {label}",
                    callback_data=f"yt_dl_{format_id}"
                ))

        # 2. Только аудио
        if audio_only:
            keyboard.row(InlineKeyboardButton(
                text="🎵 Только аудио",
                callback_data="yt_section_audio"
            ))

            for media in audio_only[:3]:
                label = media.get('label', 'Unknown')
                format_id = media.get('formatId', 0)

                logger.info(f"🔘 Adding audio button: {label} (ID: {format_id})")

                keyboard.row(InlineKeyboardButton(
                    text=f"🎵 {label}",
                    callback_data=f"yt_dl_{format_id}"
                ))

        keyboard.row(InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_download"))

        # Информация для пользователя
        info_text = f"""✅ YouTube видео найдено!

📝 {title}
⏱ Длительность: {duration // 60}:{duration % 60:02d}

📋 Доступно форматов:
• Готовых (видео+аудио): {len(video_with_audio)}
• Только видео: {len(video_only)}  
• Только аудио: {len(audio_only)}

Выберите формат для скачивания:"""

        # Сохраняем в state
        logger.info(f"💾 Saving to state...")
        await state.update_data(
            youtube_data=data,
            youtube_url=url,
            youtube_medias=medias
        )

        logger.info(f"✅ Showing format selection to user")
        await progress_msg.edit_text(info_text, reply_markup=keyboard.as_markup())

    except Exception as e:
        logger.error(f"❌ CRITICAL ERROR in YouTube handler: {type(e).__name__}: {e}")
        import traceback
        logger.error(f"📍 Full traceback: {traceback.format_exc()}")
        await progress_msg.edit_text(f"❌ Критическая ошибка: {str(e)[:100]}...")


# Включить DEBUG логирование
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


@client_bot_router.callback_query(F.data.startswith("yt_dl_"))
async def process_youtube_download_unified(callback: CallbackQuery, state: FSMContext):
    """YouTube download callback с логированием"""
    logger.info(f"🎯 YOUTUBE CALLBACK START")
    logger.info(f"📋 Callback data: {callback.data}")
    logger.info(f"👤 User: {callback.from_user.id}")

    try:
        await callback.answer()

        # Получаем format_id
        format_id_str = callback.data.replace("yt_dl_", "")
        logger.info(f"🔢 Format ID string: '{format_id_str}'")

        try:
            format_id = int(format_id_str)
            logger.info(f"🔢 Format ID integer: {format_id}")
        except ValueError as e:
            logger.error(f"❌ Cannot convert format_id to int: {e}")
            await callback.message.edit_text("❌ Ошибка формата ID")
            return

        # Получаем данные из state
        logger.info(f"📊 Getting data from state...")
        data = await state.get_data()
        logger.info(f"🗂 State keys: {list(data.keys())}")

        youtube_data = data.get('youtube_data', {})
        medias = data.get('youtube_medias', [])

        logger.info(f"📝 YouTube title: {youtube_data.get('title', 'N/A')}")
        logger.info(f"🎥 Total medias: {len(medias)}")

        # Находим выбранный формат
        logger.info(f"🔍 Searching for format_id: {format_id}")
        selected_media = None

        for i, media in enumerate(medias):
            media_format_id = media.get('formatId')
            logger.info(f"🎬 Media {i}: formatId={media_format_id}, label={media.get('label', 'N/A')}")

            if media_format_id == format_id:
                selected_media = media
                logger.info(f"✅ FOUND matching media!")
                break

        if not selected_media:
            logger.error(f"❌ Selected media not found for format_id: {format_id}")
            await callback.message.edit_text("❌ Выбранный формат не найден")
            return

        # Детали выбранного медиа
        logger.info(f"📋 SELECTED MEDIA DETAILS:")
        logger.info(f"🏷 Label: {selected_media.get('label', 'N/A')}")
        logger.info(f"🎭 Type: {selected_media.get('type', 'N/A')}")
        logger.info(f"📦 Extension: {selected_media.get('ext', 'N/A')}")
        logger.info(f"🔗 URL length: {len(selected_media.get('url', ''))}")
        logger.info(f"🔗 URL preview: {selected_media.get('url', '')}")

        title = youtube_data.get('title', 'YouTube видео')
        download_url = selected_media.get('url')
        label = selected_media.get('label', 'Unknown')

        if not download_url:
            logger.error(f"❌ No download URL in selected media!")
            await callback.message.edit_text("❌ URL для скачивания не найден")
            return

        await callback.message.edit_text(f"⏬ Скачиваю: {label}\n📝 {title}")

        # Скачиваем файл
        logger.info(f"⬇️ Starting file download...")
        file_data = await unified_downloader.download_file(download_url)

        if not file_data:
            logger.error(f"❌ File download failed!")
            await callback.message.edit_text("❌ Не удалось скачать файл (см. логи для деталей)")
            return

        logger.info(f"✅ File downloaded successfully!")
        await callback.message.edit_text("📤 Отправляю в Telegram...")

        # Определяем тип и расширение
        media_type = selected_media.get('type', 'video')
        ext = selected_media.get('ext', 'mp4')

        logger.info(f"📄 Media type: {media_type}")
        logger.info(f"📎 Extension: {ext}")

        # Создаем временный файл
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=f'.{ext}', delete=False) as temp_file:
            temp_file.write(file_data)
            temp_filepath = temp_file.name

        logger.info(f"💾 Temporary file created: {temp_filepath}")

        try:
            caption = f"🎥 YouTube\n📝 {title}\n📊 {label}\n🚀 @{(await callback.bot.get_me()).username}"
            logger.info(f"📝 Caption: {caption}")

            if media_type == 'video':
                logger.info(f"📹 Sending as video...")
                await callback.bot.send_video(
                    chat_id=callback.message.chat.id,
                    video=FSInputFile(temp_filepath),
                    caption=caption,
                    supports_streaming=True
                )
            elif media_type == 'audio':
                logger.info(f"🎵 Sending as audio...")
                await callback.bot.send_audio(
                    chat_id=callback.message.chat.id,
                    audio=FSInputFile(temp_filepath),
                    caption=caption
                )
            else:
                logger.info(f"📄 Sending as document...")
                await callback.bot.send_document(
                    chat_id=callback.message.chat.id,
                    document=FSInputFile(temp_filepath),
                    caption=caption
                )

            logger.info(f"✅ File sent successfully!")
            await callback.message.delete()

            # Analytics
            try:
                await shortcuts.add_to_analitic_data((await callback.bot.get_me()).username, youtube_data.get('url'))
                logger.info(f"📊 Analytics updated")
            except Exception as analytics_error:
                logger.error(f"⚠️ Analytics error: {analytics_error}")

        finally:
            # Cleanup
            try:
                os.unlink(temp_filepath)
                logger.info(f"🗑 Temporary file cleaned up")
            except Exception as cleanup_error:
                logger.error(f"⚠️ Cleanup error: {cleanup_error}")

    except Exception as e:
        logger.error(f"❌ CRITICAL ERROR in YouTube callback: {type(e).__name__}: {e}")
        import traceback
        logger.error(f"📍 Full traceback: {traceback.format_exc()}")

        try:
            await callback.message.edit_text(f"❌ Критическая ошибка: {str(e)[:100]}...")
        except:
            pass


async def handle_other_platforms_unified(message: Message, url: str, me, bot: Bot, state: FSMContext, platform: str):
    """Handler для остальных платформ - автоматический выбор лучшего формата"""
    platform_names = {
        'instagram': 'Instagram',
        'tiktok': 'TikTok',
        'twitter': 'Twitter',
        'facebook': 'Facebook',
        'reddit': 'Reddit',
        'vimeo': 'Vimeo'
    }

    platform_name = platform_names.get(platform, platform.title())
    progress_msg = await message.answer(f"⏳ Загружаю медиа из {platform_name}...")

    try:
        # Получаем данные
        await progress_msg.edit_text(f"📡 Получаю информацию из {platform_name}...")
        result = await unified_downloader.download_media(url)

        if not result['success']:
            await progress_msg.edit_text(f"❌ Не удалось получить данные: {result['error']}")
            return

        data = result['data']
        title = data.get('title', f'{platform_name} медиа')
        author = data.get('author', 'Неизвестно')
        medias = data.get('medias', [])

        if not medias:
            await progress_msg.edit_text(f"❌ Медиа из {platform_name} не найдено")
            return

        # Автоматический выбор лучшего формата
        selected_media = None

        # Приоритет: видео с аудио > видео без аудио > аудио
        for media in medias:
            if media.get('type') == 'video' and media.get('is_audio', False):
                selected_media = media
                break

        if not selected_media:
            for media in medias:
                if media.get('type') == 'video':
                    selected_media = media
                    break

        if not selected_media:
            selected_media = medias[0]  # Берем первый доступный

        # Показываем информацию
        info_text = f"✅ {platform_name} медиа найдено!\n\n📝 {title}"
        if author and author != 'Неизвестно':
            info_text += f"\n👤 {author}"
        info_text += "\n\n📥 Скачиваю..."

        await progress_msg.edit_text(info_text)

        # Скачиваем
        file_data = await unified_downloader.download_file(selected_media['url'])

        if not file_data:
            await progress_msg.edit_text(f"❌ Не удалось скачать файл из {platform_name}")
            return

        await progress_msg.edit_text("📤 Отправляю в Telegram...")

        # Отправляем
        caption = f"🎥 {platform_name}\n📝 {title}"
        if author and author != 'Неизвестно':
            caption += f"\n👤 {author}"
        caption += f"\n🚀 @{me.username}"

        media_type = selected_media.get('type', 'video')
        ext = selected_media.get('ext', 'mp4')

        with tempfile.NamedTemporaryFile(suffix=f'.{ext}', delete=False) as temp_file:
            temp_file.write(file_data)
            temp_filepath = temp_file.name

        try:
            if media_type == 'video':
                await bot.send_video(
                    chat_id=message.chat.id,
                    video=FSInputFile(temp_filepath),
                    caption=caption,
                    supports_streaming=True
                )
            elif media_type == 'audio':
                await bot.send_audio(
                    chat_id=message.chat.id,
                    audio=FSInputFile(temp_filepath),
                    caption=caption
                )
            else:
                await bot.send_document(
                    chat_id=message.chat.id,
                    document=FSInputFile(temp_filepath),
                    caption=caption
                )

            await progress_msg.delete()
            await shortcuts.add_to_analitic_data(me.username, url)
            await state.set_state(Download.download)

        finally:
            try:
                os.unlink(temp_filepath)
            except:
                pass

    except Exception as e:
        logger.error(f"{platform_name} handler error: {e}")
        try:
            await progress_msg.edit_text(f"❌ Ошибка при скачивании из {platform_name}")
        except:
            await message.answer(f"❌ Ошибка при скачивании из {platform_name}")

@client_bot_router.callback_query(F.data == "cancel_download")
async def cancel_download_unified(callback: CallbackQuery, state: FSMContext):
    """Отмена скачивания"""
    await callback.message.edit_text("❌ Скачивание отменено")
    await callback.answer("Отменено")
    await state.clear()

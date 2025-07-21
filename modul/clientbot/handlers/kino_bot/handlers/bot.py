import glob 
import asyncio
import subprocess
import time
import traceback
from contextlib import suppress
import shutil
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
from modul.clientbot.handlers.davinci_bot import *
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
from modul.loader import client_bot_router
from modul.models import UserTG, AdminInfo, User, ClientBotUser
from typing import Union, List
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
    """Callback data for format selection"""
    format_id: str
    type: str
    quality: str
    index: int


async def check_subs(user_id: int, bot: Bot) -> bool:
    try:
        bot_db = await shortcuts.get_bot(bot)
        admin_id = bot_db.owner.uid
        if user_id == admin_id:
            return True

        channels = await get_all_channels_sponsors()
        if not channels:
            return True

        for channel in channels:
            print(channel)
            try:
                member = await bot.get_chat_member(chat_id=channel, user_id=user_id)
                if member.status == 'left':
                    kb = await get_subs_kb(bot)
                    await bot.send_message(
                        chat_id=user_id,
                        text="<b>Чтобы воспользоваться ботом, необходимо подписаться на каналы:</b>",
                        reply_markup=kb,
                        parse_mode="HTML"
                    )
                    return False
            except TelegramBadRequest as e:
                logger.error(f"Error checking channel {channel}: {e}")
                await remove_invalid_channel(channel)
                continue

        return True

    except Exception as e:
        logger.error(f"General error in check_subs: {e}")
        return False


@sync_to_async
def remove_invalid_channel(channel_id: int):
    try:
        ChannelSponsor.objects.filter(chanel_id=channel_id).delete()
        logger.info(f"Removed invalid channel {channel_id} from database")
    except Exception as e:
        logger.error(f"Error removing channel {channel_id}: {e}")

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

async def check_user_subscriptions(bot: Bot, user_id: int) -> bool:
    channels = await get_all_channels_sponsors()
    for channel in channels:
        try:
            member = await bot.get_chat_member(channel.chanel_id, user_id)
            if member.status in ['left', 'kicked', 'banned']:
                return False
        except Exception as e:
            print(f"Error checking subscription for channel {channel.chanel_id}: {e}")
            return False

    return True
@client_bot_router.callback_query(lambda c: c.data == 'check_subs')
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


# @client_bot_router.message(Command('admin'), AdminFilter())
# async def admin(message: types.Message):
#     await message.answer('Админ панель', reply_markup=admin_kb)


# @client_bot_router.callback_query(F.data == 'admin_send_message', AdminFilter(), StateFilter('*'))
# async def admin_send_message(call: CallbackQuery, state: FSMContext):
#     print('admin_send_message called')
#     await state.set_state(SendMessagesForm.message)
#     await call.message.edit_text('Отправьте сообщение для рассылки (текст, фото, видео и т.д.)', reply_markup=cancel_kb)
#
#
#
# @client_bot_router.message(SendMessagesForm.message)
# async def admin_send_message_msg(message: types.Message, state: FSMContext):
#     await state.clear()
#     bot_db = await shortcuts.get_bot(message.bot)
#     users = await get_all_users(bot_db)
#
#     if not users:
#         await message.answer("Нет пользователей для рассылки.")
#         return
#
#     success_count = 0
#     fail_count = 0
#
#     for user_id in users:
#         try:
#             if message.text:
#                 await message.bot.send_message(chat_id=user_id, text=message.text)
#             elif message.photo:
#                 await message.bot.send_photo(chat_id=user_id, photo=message.photo[-1].file_id, caption=message.caption)
#             elif message.video:
#                 await message.bot.send_video(chat_id=user_id, video=message.video.file_id, caption=message.caption)
#             elif message.audio:
#                 await message.bot.send_audio(chat_id=user_id, audio=message.audio.file_id, caption=message.caption)
#             elif message.document:
#                 await message.bot.send_document(chat_id=user_id, document=message.document.file_id, caption=message.caption)
#             else:
#                 await message.bot.copy_message(chat_id=user_id, from_chat_id=message.chat.id, message_id=message.message_id)
#
#             success_count += 1
#         except Exception as e:
#             fail_count += 1
#             logger.error(f"Ошибка при отправке сообщения пользователю {user_id}: {e}")
#
#     await message.answer(
#         f'Рассылка завершена!\n'
#         f'Успешно отправлено: {success_count}\n'
#         f'Не удалось отправить: {fail_count}'
#     )
#
#
#
# @client_bot_router.callback_query(F.data == "imp", AdminFilter(), StateFilter('*'))
# async def manage_user_handler(call: CallbackQuery, state: FSMContext):
#     await call.message.edit_text(
#         "Введите ID пользователя",
#         reply_markup=cancel_kb
#     )
#     await state.set_state(ChangeAdminInfo.imp)
#
#
# @client_bot_router.callback_query(lambda call: "accept_" in call.data, AdminFilter(), StateFilter('*'))
# async def acception(query: CallbackQuery):
#     id_of_wa = int(query.data.replace("accept_", ""))
#     user_info = await status_accepted(id_of_wa)
#
#     if user_info:
#         await query.message.edit_reply_markup(reply_markup=await accepted_in())
#         await query.bot.send_message(
#             user_info[0],
#             f"Ваша завявка на выплату {user_info[1]} была подтверждена ✅"
#         )
#     else:
#         await query.answer("Ошибка: Не удалось подтвердить заявку", show_alert=True)
#
#
# @client_bot_router.callback_query(lambda call: "decline_" in call.data, AdminFilter(), StateFilter('*'))
# async def declined(query: CallbackQuery):
#     id_of_wa = int(query.data.replace("decline_", ""))
#     user_info = await status_declined(id_of_wa)
#
#     if user_info:
#         await query.message.edit_reply_markup(reply_markup=await declined_in())
#         await query.bot.send_message(
#             user_info[0],
#             f"Ваша завявка на выплату {user_info[1]} была отклонена❌"
#         )
#     else:
#         await query.answer("Ошибка: Не удалось отклонить заявку", show_alert=True)
#
#
# @client_bot_router.message(ChangeAdminInfo.imp)
# async def get_user_info_handler(message: Message, state: FSMContext):
#     if message.text == "❌Отменить":
#         await message.answer("🚫 Действие отменено", reply_markup=await main_menu_bt())
#         await state.clear()
#         return
#
#     if message.text.isdigit():
#         user_id = int(message.text)
#         try:
#             status = await check_ban(user_id)
#             user_info = await get_user_info_db(user_id)
#             bot_user_info = await get_bot_user_info(message.from_user.id, message.bot.token)
#             bot_balance = bot_user_info[0] if bot_user_info else 0
#             bot_referrals = bot_user_info[1] if bot_user_info else 0
#
#             if user_info:
#                 user_name = "@"
#                 try:
#                     chat = await message.bot.get_chat(user_info[1])
#                     user_name += f"{chat.username}"
#                 except:
#                     pass
#                 await message.answer(
#                     f"📝Имя юзера: {user_info[0]} {user_name}\n"
#                     f"🆔ID юзера: <code>{user_info[1]}</code>\n"
#                     f"👥 Пригласил: {user_info[3]}\n"
#                     f"💳 Баланс юзера: {bot_balance}₽ \n"
#                     f"📤 Вывел: {user_info[5]} руб.",
#                     parse_mode="html",
#                     reply_markup=await imp_menu_in(user_info[1], status)
#                 )
#                 await state.clear()
#             else:
#                 await message.answer("Юзер не найден", reply_markup=await main_menu_bt())
#                 await state.clear()
#         except Exception as e:
#             await message.answer(f"🚫 Не удалось найти юзера. Ошибка: {e}", reply_markup=await main_menu_bt())
#             await state.clear()
#     else:
#         await message.answer("️️❗Ошибка! Введите числовой ID пользователя.", reply_markup=await main_menu_bt())
#         await state.clear()
#
# @client_bot_router.callback_query(F.data.startswith("changerefs_"), AdminFilter(), StateFilter('*'))
# async def change_refs_handler(call: CallbackQuery, state: FSMContext):
#     user_id = int(call.data.replace("changerefs_", ""))
#     await call.message.edit_text(
#         "Введите новое количество рефералов:",
#         reply_markup=cancel_kb
#     )
#     await state.set_state(ChangeAdminInfo.change_refs)
#     await state.update_data(user_id=user_id)
#
# @client_bot_router.message(ChangeAdminInfo.change_refs)
# async def set_new_refs_count(message: Message, state: FSMContext):
#     data = await state.get_data()
#     user_id = data.get("user_id")
#
#     if message.text == "❌Отменить":
#         await message.answer("🚫 Действие отменено", reply_markup=await main_menu_bt())
#         await state.clear()
#         return
#
#     if message.text.isdigit():
#         new_refs_count = int(message.text)
#
#         try:
#             @sync_to_async
#             @transaction.atomic
#             def update_refs():
#                 user = UserTG.objects.select_for_update().filter(uid=user_id).first()
#                 if user:
#                     user.refs = new_refs_count
#                     user.save()
#                     return True
#                 return False
#
#             updated = await update_refs()
#
#             if updated:
#                 await message.answer(f"Количество рефералов для пользователя {user_id} успешно обновлено на {new_refs_count}.", reply_markup=await main_menu_bt())
#             else:
#                 await message.answer(f"🚫 Пользователь с ID {user_id} не найден.", reply_markup=await main_menu_bt())
#
#         except Exception as e:
#             logger.error(f"Error updating refs count for user {user_id}: {e}")
#             await message.answer("🚫 Не удалось обновить количество рефералов.", reply_markup=await main_menu_bt())
#     else:
#         await message.answer("❗ Введите корректное числовое значение.")
#
#     await state.clear()
#
#
# @client_bot_router.callback_query(F.data == 'all_payments', AdminFilter(), StateFilter('*'))
# async def all_payments_handler(call: CallbackQuery):
#     active_payments = await get_all_wait_payment()
#
#     if active_payments:
#         for payment in active_payments:
#             print(payment)
#             await call.message.answer(
#                 text=f"<b>Заявка на выплату № {payment[0]}</b>\n"  # payment[0] - id
#                      f"ID пользователя: <code>{payment[1]}</code>\n"  # payment[1] - user_id
#                      f"Сумма: {payment[2]} руб.\n"  # payment[2] - amount
#                      f"Карта: <code>{payment[3]}</code>\n"  # payment[3] - card
#                      f"Банк: {payment[4]}",  # payment[4] - bank
#                 parse_mode="HTML",
#                 reply_markup=await payments_action_in(payment[0])  # payment[0] - id
#             )
#     else:
#         await call.message.edit_text('Нет заявок на выплату.', reply_markup=admin_kb)
#
#
# @client_bot_router.message(ChangeAdminInfo.get_amount)
# async def get_new_amount_handler(message: Message, state: FSMContext):
#     if message.text == "❌Отменить":
#         await message.answer("🚫 Действие отменено", reply_markup=await main_menu_bt())
#         await state.clear()
#         return
#
#     try:
#         new_reward = float(message.text)
#         # Передаем токен текущего бота
#         success = await change_price(new_reward, message.bot.token)
#
#         if success:
#             await message.answer(
#                 f"Награда за реферала успешно изменена на {new_reward:.2f} руб.",
#                 reply_markup=await main_menu_bt()
#             )
#         else:
#             await message.answer(
#                 "🚫 Не удалось изменить награду за реферала.",
#                 reply_markup=await main_menu_bt()
#             )
#         await state.clear()
#
#     except ValueError:
#         await message.answer("❗ Введите корректное числовое значение.")
#     except Exception as e:
#         logger.error(f"Ошибка при обновлении награды за реферала: {e}")
#         await message.answer("🚫 Не удалось изменить награду за реферала.", reply_markup=await main_menu_bt())
#         await state.clear()
#
#
#
#
# @client_bot_router.callback_query(F.data.startswith("changebalance_"), AdminFilter(), StateFilter('*'))
# async def change_balance_handler(call: CallbackQuery, state: FSMContext):
#     id_of_user = int(call.data.replace("changebalance_", ""))
#     await call.message.edit_text(
#         "Введите новую сумму баланса. Для нецелых чисел используйте точку, а не запятую.",
#         reply_markup=cancel_kb
#     )
#     await state.set_state(ChangeAdminInfo.change_balance)
#     await state.update_data(user_id=id_of_user)
#
# @client_bot_router.callback_query(F.data == 'change_money', AdminFilter(), StateFilter('*'))
# async def change_money_handler(call: CallbackQuery, state: FSMContext):
#     await state.set_state(ChangeAdminInfo.get_amount)
#     await call.message.edit_text(
#         'Введите новую награду за рефералов:',
#         reply_markup=cancel_kb
#     )
#     await state.set_state(ChangeAdminInfo.get_amount)
#
#
# @client_bot_router.callback_query(F.data == "change_min", AdminFilter(), StateFilter('*'))
# async def change_min_handler(call: CallbackQuery, state: FSMContext):
#     edited_message = await call.message.edit_text(
#         "Введите новую минимальную выплату:",
#         reply_markup=cancel_kb
#     )
#     await state.set_state(ChangeAdminInfo.get_min)
#     await state.update_data(edit_msg=edited_message)
#
#
# @client_bot_router.message(ChangeAdminInfo.get_min)
# async def get_new_min_handler(message: Message, state: FSMContext, bot: Bot):
#     data = await state.get_data()
#     edit_msg = data.get('edit_msg')
#
#     if message.text == "❌Отменить":
#         await message.delete()
#         if edit_msg:
#             await edit_msg.delete()
#         await state.clear()
#         await start(message, state, bot)
#         return
#
#     try:
#         new_min_payout = float(message.text)
#         print(new_min_payout)
#
#         await change_min_amount(new_min_payout)
#
#         await message.delete()
#         if edit_msg:
#             await edit_msg.delete()
#
#         await message.answer(
#             f"Минимальная выплата успешно изменена на {new_min_payout:.1f} руб."
#         )
#         await state.clear()
#         await start(message, state, bot)
#
#     except ValueError:
#         await message.answer("❗ Введите корректное числовое значение.")
#     except Exception as e:
#         logger.error(f"Ошибка при обновлении минимальной выплаты: {e}")
#         await message.answer("🚫 Не удалось изменить минимальную выплату.")
#         await state.clear()
#         await start(message, state, bot)
#
#
#
#
# @client_bot_router.callback_query(F.data.startswith("ban_"), AdminFilter(), StateFilter('*'))
# async def ban_user_handler(call: CallbackQuery):
#     user_id = int(call.data.replace("ban_", ""))
#     ban_unban_db(id=user_id, bool=True)
#     await call.message.edit_reply_markup(reply_markup=await imp_menu_in(user_id, True))
#
#
# @client_bot_router.callback_query(F.data.startswith("razb_"), AdminFilter(), StateFilter('*'))
# async def unban_user_handler(call: CallbackQuery):
#     user_id = int(call.data.replace("razb_", ""))
#     ban_unban_db(id=user_id, bool=False)
#     await call.message.edit_reply_markup(reply_markup=await imp_menu_in(user_id, False))
#
#
# @client_bot_router.callback_query(F.data.startswith("addbalance_"), AdminFilter(), StateFilter('*'))
# async def add_balance_handler(call: CallbackQuery, state: FSMContext):
#     user_id = int(call.data.replace("addbalance_", ""))
#     await call.message.edit_text(
#         "Введите сумму для добавления к балансу. Для дробных чисел используйте точку.",
#         reply_markup=cancel_kb
#     )
#     await state.set_state(ChangeAdminInfo.add_balance)
#     await state.update_data(user_id=user_id)
#
#
# @client_bot_router.message(ChangeAdminInfo.add_balance)
# async def process_add_balance(message: Message, state: FSMContext):
#     if message.text == "❌Отменить":
#         await message.answer("🚫 Действие отменено", reply_markup=await main_menu_bt())
#         await state.clear()
#         return
#
#     try:
#         amount = float(message.text)
#         data = await state.get_data()
#         await addbalance_db(data["user_id"], amount)
#         await message.answer(f"Баланс успешно пополнен на {amount} руб.", reply_markup=await main_menu_bt())
#         await state.clear()
#     except ValueError:
#         await message.answer("❗ Введите корректное числовое значение.")
#     except Exception as e:
#         await message.answer(f"🚫 Не удалось изменить баланс. Ошибка: {e}", reply_markup=await main_menu_bt())
#         await state.clear()
#
#
# @client_bot_router.callback_query(F.data.startswith("changebalance_"), AdminFilter(), StateFilter('*'))
# async def change_balance_handler(call: CallbackQuery, state: FSMContext):
#     user_id = int(call.data.replace("changebalance_", ""))
#     await call.message.edit_text(
#         "Введите новую сумму баланса. Для дробных чисел используйте точку.",
#         reply_markup=cancel_kb
#     )
#     await state.set_state(ChangeAdminInfo.change_balance)
#     await state.update_data(user_id=user_id)
#
#
# @client_bot_router.message(ChangeAdminInfo.change_balance)
# async def process_change_balance(message: Message, state: FSMContext):
#     if message.text == "❌Отменить":
#         await message.answer("🚫 Действие отменено", reply_markup=await main_menu_bt())
#         await state.clear()
#         return
#
#     try:
#         new_balance = float(message.text)
#         data = await state.get_data()
#         await changebalance_db(data["user_id"], new_balance)
#         await message.answer(f"Баланс успешно изменен на {new_balance} руб.", reply_markup=await main_menu_bt())
#         await state.clear()
#     except ValueError:
#         await message.answer("❗ Введите корректное числовое значение.")
#     except Exception as e:
#         await message.answer(f"🚫 Не удалось изменить баланс. Ошибка: {e}", reply_markup=await main_menu_bt())
#         await state.clear()
#
#
# @client_bot_router.callback_query(F.data.startswith("showrefs_"), AdminFilter(), StateFilter('*'))
# async def show_refs_handler(call: CallbackQuery):
#     user_id = int(call.data.replace("showrefs_", ""))
#     try:
#         file_data, filename = await convert_to_excel(user_id, call.bot.token)
#         document = BufferedInputFile(file_data, filename=filename)
#         await call.message.answer_document(document)
#     except Exception as e:
#         await call.message.answer(f"🚫 Произошла ошибка при создании файла: {e}")
#
#
# @client_bot_router.callback_query(F.data == 'admin_get_stats', AdminFilter(), StateFilter('*'))
# async def admin_get_stats(call: CallbackQuery):
#     print('stats called')
#     try:
#         bot_token = call.bot.token
#         print(f"Bot token: {bot_token}")
#
#         bot_db = await get_bot_by_token(bot_token)
#         print(f"Bot DB object: {bot_db}")
#
#         if bot_db:
#             @sync_to_async
#             def count_bot_users(bot_id):
#                 try:
#                     return models.ClientBotUser.objects.filter(bot_id=bot_id).count()
#                 except Exception as e:
#                     logger.error(f"Error counting bot users: {e}")
#                     return 0
#
#             total_users = await count_bot_users(bot_db.id)
#             print(f"Users count for this bot: {total_users}")
#
#             new_text = f'<b>Количество пользователей в боте:</b> {total_users}'
#
#             try:
#                 await call.message.edit_text(
#                     text=new_text,
#                     reply_markup=admin_kb,
#                     parse_mode='HTML'
#                 )
#             except TelegramBadRequest as e:
#                 if "message is not modified" in str(e):
#                     await call.answer("Статистика актуальна")
#                 else:
#                     raise
#
#         else:
#             logger.error(f"Bot not found in database for token: {bot_token}")
#             await call.answer("Бот не найден в базе данных")
#
#     except Exception as e:
#         logger.error(f"Ошибка получения статистики: {e}")
#         logger.error(f"Full error traceback: {traceback.format_exc()}")
#         await call.answer("Ошибка при получении статистики")
#
#
#
# @client_bot_router.callback_query(F.data == 'cancel', StateFilter('*'))
# async def cancel(call: CallbackQuery, state: FSMContext):
#     await state.clear()
#     await call.message.edit_text('Отменено')
#
#
# @client_bot_router.callback_query(F.data == 'admin_delete_channel', AdminFilter(), StateFilter('*'))
# async def admin_delete_channel(call: CallbackQuery, bot: Bot):
#     channels = await get_all_channels_sponsors()
#     kb = await get_remove_channel_sponsor_kb(channels, bot)
#     await call.message.edit_text('Выберите канал для удаления', reply_markup=kb)
#
#
# @client_bot_router.callback_query(F.data.contains('remove_channel'), AdminFilter(), StateFilter('*'))
# async def remove_channel(call: CallbackQuery, bot: Bot):
#     channel_id = int(call.data.split('|')[-1])
#     try:
#         await remove_channel_sponsor(channel_id)
#         await call.message.edit_text('Канал был удален!', reply_markup=admin_kb)
#
#         logger.info(f"Kanal muvaffaqiyatli o‘chirildi: {channel_id}")
#     except Exception as e:
#         logger.error(f"Kanalni o‘chirishda xatolik: {e}")
#         await call.message.answer("Произошла ошибка при удалении канала.")
#
#
#
# @client_bot_router.callback_query(F.data == 'admin_add_channel', AdminFilter(), StateFilter('*'))
# async def admin_add_channel(call: CallbackQuery, state: FSMContext):
#     await state.set_state(AddChannelSponsorForm.channel)
#     await call.message.edit_text('Отправьте id канала\n\n'
#                                  'Убедитесь в том, что бот является администратором в канале\n\n'
#                                  '@username_to_id_bot id канала можно получить у этого бота',
#                                  reply_markup=cancel_kb)
#
#
# from enum import Enum
# from typing import Optional, List, Union
# from pydantic import BaseModel
#
#
# # Define ReactionType enum to include all possible types
# class ReactionTypeType(str, Enum):
#     EMOJI = "emoji"
#     CUSTOM_EMOJI = "custom_emoji"
#     PAID = "paid"
#
#
# # Base class for all reaction types
# class ReactionTypeBase(BaseModel):
#     type: ReactionTypeType
#
#
# # Specific reaction type models
# class ReactionTypeEmoji(ReactionTypeBase):
#     type: ReactionTypeType = ReactionTypeType.EMOJI
#     emoji: str
#
#
# class ReactionTypeCustomEmoji(ReactionTypeBase):
#     type: ReactionTypeType = ReactionTypeType.CUSTOM_EMOJI
#     custom_emoji_id: str
#
#
# class ReactionTypePaid(ReactionTypeBase):
#     type: ReactionTypeType = ReactionTypeType.PAID
#
#
# # Union type for all possible reactions
# ReactionType = Union[ReactionTypeEmoji, ReactionTypeCustomEmoji, ReactionTypePaid]
#
#
# class ChatInfo(BaseModel):
#     id: int
#     title: str
#     type: str
#     description: Optional[str] = None
#     invite_link: Optional[str] = None
#     has_visible_history: Optional[bool] = None
#     can_send_paid_media: Optional[bool] = None
#     available_reactions: Optional[List[ReactionType]] = None
#     max_reaction_count: Optional[int] = None
#     accent_color_id: Optional[int] = None
#
# from aiogram import F
#
# @client_bot_router.message(F.text == "🔙Назад в меню")
# async def back_to_main_menu(message: Message, state: FSMContext, bot: Bot):
#     await start(message, state, bot)
#
#
# @client_bot_router.message(AddChannelSponsorForm.channel)
# async def admin_add_channel_msg(message: Message, state: FSMContext):
#     try:
#         channel_id = int(message.text)
#         # 1) Получаем объект Bot напрямую из message:
#         bot = message.bot
#
#         # 2) Узнаём информацию о чате (метод GetChat)
#         chat_data = await bot(GetChat(chat_id=channel_id, flags={"raw": True}))
#         print(chat_data)
#         chat_info = await bot(GetChat(chat_id=channel_id))
#
#         # 3) Проверяем, что это именно канал
#         if chat_info.type != "channel":
#             await message.answer(
#                 "Указанный ID не является каналом. Пожалуйста, введите ID канала.",
#                 reply_markup=cancel_kb
#             )
#             return
#
#         # 4) Проверяем, что бот — администратор в этом канале (GetChatMember)
#         bot_member = await bot(GetChatMember(chat_id=channel_id, user_id=bot.id))
#         if bot_member.status not in ["administrator", "creator"]:
#             await message.answer(
#                 "Бот не является администратором канала. Пожалуйста, добавьте бота в администраторы канала.",
#                 reply_markup=cancel_kb
#             )
#             return
#
#         # 5) Проверяем / создаём invite link (CreateChatInviteLink)
#         invite_link = chat_info.invite_link
#         if not invite_link:
#             link_data = await bot(CreateChatInviteLink(chat_id=channel_id))
#             invite_link = link_data.invite_link
#
#         # 6) Добавляем в базу (ваша функция)
#         await create_channel_sponsor(channel_id)
#         await state.clear()
#
#         # 7) Формируем итоговый список строк для ответа
#         channel_info = [
#             "✅ Канал успешно добавлен!",
#             f"📣 Название: {chat_info.title}",
#             f"🆔 ID: {channel_id}",
#             f"🔗 Ссылка: {invite_link}"
#         ]
#
#         # 8) Если доступны реакции, добавляем информацию
#         if chat_info.available_reactions:
#             try:
#                 # chat_info.available_reactions может быть списком объектов-реакций
#                 # Тут зависит от вашей сериализации. Предположим, это список dict
#                 reactions = chat_info.available_reactions
#                 if reactions:
#                     reaction_types = [
#                         r.get("type", "unknown") for r in reactions
#                     ]
#                     channel_info.append(
#                         f"💫 Доступные реакции: {', '.join(reaction_types)}"
#                     )
#             except Exception as e:
#                 logger.warning(f"Failed to process reactions: {e}")
#
#         # 9) Отправляем готовый текст
#         await message.answer(
#             "\n\n".join(channel_info),
#             disable_web_page_preview=True
#         )
#
#     except ValueError:
#         # int(...) не смог преобразовать текст → сообщаем об ошибке формата
#         await message.answer(
#             "Неверный формат. Пожалуйста, введите числовой ID канала.",
#             reply_markup=cancel_kb
#         )
#     except TelegramBadRequest as e:
#         logger.error(f"Telegram API error: {e}")
#         await message.answer(
#             "Бот не смог найти канал. Пожалуйста, проверьте ID канала.",
#             reply_markup=cancel_kb
#         )
#     except Exception as e:
#         logger.error(f"Channel add error: channel_id={channel_id}, error={str(e)}")
#         logger.exception("Detailed error:")
#         await message.answer(
#             "Произошла ошибка. Пожалуйста, попробуйте еще раз.",
#             reply_markup=cancel_kb
#         )

class KinoBotFilter(Filter):
    async def __call__(self, message: types.Message, bot: Bot) -> bool:
        bot_db = await shortcuts.get_bot(bot)
        return shortcuts.have_one_module(bot_db, "kino")

class DavinchiBotFilter(Filter):
    async def __call__(self, message: types.Message, bot: Bot) -> bool:
        bot_db = await shortcuts.get_bot(bot)
        return shortcuts.have_one_module(bot_db, "leo")


@client_bot_router.message(F.text == "💸Заработать")
async def kinogain(message: Message, bot: Bot, state: FSMContext):
    bot_db = await shortcuts.get_bot(bot)

    sub_status = await check_subs(message.from_user.id, bot)
    if not sub_status:
        kb = await get_subs_kb(bot)
        await message.answer(
            '<b>Чтобы воспользоваться ботом, необходимо подписаться на каналы</b>',
            reply_markup=kb,
            parse_mode="HTML"
        )
        return

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

        # sub_status = await check_subs(message.from_user.id, bot)
        # if not sub_status:
        #     kb = await get_subs_kb(bot)
        #     await message.answer(
        #         '<b>Чтобы воспользоваться ботом, необходимо подписаться на каналы:</b>',
        #         reply_markup=kb,
        #         parse_mode="HTML"
        #     )
        #     return

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

    # 1. Kanallarni tekshirish va obuna bo'lmaganlarini aniqlash
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
                    # Obuna bo'lmagan kanal ma'lumotlarini olish
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
                await remove_invalid_channel(channel_id)
                continue

    if not subscribed:
        # Foydalanuvchiga aniq xabar berish
        await callback.answer("⚠️ Вы не подписались на все каналы! Пожалуйста, подпишитесь на все указанные каналы.",
                              show_alert=True)

        # Obuna bo'lmagan kanallarni ko'rsatish
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
            # Xabarni yangilashga urinish
            await callback.message.edit_text(
                channels_text + f"\n\nПосле подписки на все каналы нажмите кнопку «Проверить подписку».",
                reply_markup=markup.as_markup(),
                parse_mode="HTML"
            )
        except Exception as e:
            # Xatolik yuz bersa, eski xabarni o'chirib, yangi xabar yuborish
            try:
                await callback.message.delete()
            except:
                pass  # Agar o'chirishda xatolik bo'lsa, e'tiborsiz qoldiramiz

            # Yangi xabar yuborish
            await callback.message.answer(
                channels_text + f"\n\nПосле подписки на все каналы нажмите кнопку «Проверить подписку».",
                reply_markup=markup.as_markup(),
                parse_mode="HTML"
            )

        return

    await callback.answer("Вы успешно подписались на все каналы!")

    # Foydalanuvchi bazada mavjud yoki yo'qligini tekshirish
    user_exists = await check_user(user_id)

    # Referral ID olish
    referral_id = None

    # State dan olish
    data = await state.get_data()
    referral = data.get('referral')
    if referral and str(referral).isdigit():
        referral_id = int(referral)
        logger.info(f"Got referral ID from state: {referral_id}")

    # Yangi foydalanuvchi va referral ID bor bo'lsa, referral jarayonini bajarish
    if not user_exists:
        try:
            # Foydalanuvchini bazaga qo'shish
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
        builder.button(text='🆘 Помощь', callback_data='helper')
        builder.button(text='⚙️ Настройки', callback_data='settings')
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
# Kino_bot/bot.py faylidagi start funksiyasining referral jarayonini boshqaradigan qismi
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

            # O'zini o'zi referral qilishni tekshirish
            if ref_id == uid:
                print(f"Self-referral blocked: user {uid} tried to refer themselves")
                logger.warning(f"SELF-REFERRAL BLOCKED: User {uid}")
                # O'zini referral qilganda log chiqaradi, lekin ishlashni to'xtatmaydi
            else:
                print(f"Processing referral for new user {uid} from {ref_id}")
                try:
                    # Allaqachon referral qilinganligini tekshirish
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
        builder.button(text='🆘 Помощь', callback_data='helper')
        builder.button(text='⚙️ Настройки', callback_data='settings')
        builder.button(text='💸Заработать', callback_data='ref')
        builder.adjust(2, 1, 1, 1, 1, 1, 2)
        result = await get_info_db(uid)
        print(result)
        text = f'Привет {message.from_user.username}\nВаш баланс - {result[0][2]}'
        kwargs['reply_markup'] = builder.as_markup()
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

        channels = await get_channels_for_check()
        print(f"📡 Found channels: {channels}")

        if channels:
            print(f"🔒 Channels exist, checking user subscription for {message.from_user.id}")
            not_subscribed_channels = []

            for channel_id, channel_url in channels:
                try:
                    member = await message.bot.get_chat_member(
                        chat_id=channel_id,
                        user_id=message.from_user.id
                    )
                    print(f"Channel {channel_id} status: {member.status}")

                    if member.status == "left":
                        try:
                            chat_info = await message.bot.get_chat(chat_id=channel_id)
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
                    await remove_invalid_channel(channel_id)
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

            channels_text = "📢 **Для использования бота необходимо подписаться на каналы:**\n\n"
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


# client_bot_router.message.register(bot_start, F.text == "🫰 Знакомства",DavinchiBotFilter())
# client_bot_router.message.register(bot_start_cancel, F.text == ("Я не хочу никого искать"), LeomatchRegistration.BEGIN)
# client_bot_router.message.register(bot_start_lets_leo, F.text == "Давай, начнем!", LeomatchRegistration.BEGIN)


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
    """Get the best video and audio formats, prioritizing formats that don't need merging"""
    video_formats = []
    audio_format = None
    seen_qualities = set()

    # First, find formats that contain both video and audio (no merging needed)
    complete_formats = []
    for fmt in formats:
        if not isinstance(fmt, dict):
            continue

        vcodec = fmt.get('vcodec', 'none')
        acodec = fmt.get('acodec', 'none')

        # This is a complete format with both video and audio
        if vcodec != 'none' and acodec != 'none':
            height = fmt.get('height', 0)
            if height and height not in seen_qualities:
                seen_qualities.add(height)
                complete_formats.append(fmt)

    # If we have complete formats, use them
    if complete_formats:
        complete_formats.sort(key=lambda x: int(x.get('height', 0) or 0), reverse=True)
        return complete_formats, audio_format

    # Otherwise, fall back to separate video and audio formats
    seen_qualities = set()
    for fmt in formats:
        if not isinstance(fmt, dict):
            continue

        vcodec = fmt.get('vcodec', 'none')
        acodec = fmt.get('acodec', 'none')

        if vcodec != 'none' and acodec == 'none':
            height = fmt.get('height', 0)
            if height and height not in seen_qualities:
                seen_qualities.add(height)
                video_formats.append(fmt)

        elif acodec != 'none' and vcodec == 'none':
            if not audio_format or (fmt.get('abr', 0) > audio_format.get('abr', 0)):
                audio_format = fmt

    video_formats.sort(key=lambda x: int(x.get('height', 0) or 0), reverse=True)

    return video_formats, audio_format


async def download_video(url: str, format_id: str, state: FSMContext, progress_msg=None):
    try:
        # Make sure download directory exists
        download_dir = "/var/www/downloads"
        os.makedirs(download_dir, exist_ok=True)

        # Simple progress hook for basic updates
        last_percent = [0]

        def progress_hook(d):
            try:
                if d['status'] == 'downloading':
                    percent = d.get('_percent_str', '0%').strip()
                    percent_num = float(percent.replace('%', '')) if percent.replace('%', '').replace('.', '',
                                                                                                      1).isdigit() else 0
                    speed = d.get('_speed_str', 'N/A')
                    eta = d.get('_eta_str', 'N/A')

                    # Only update if significant progress
                    if abs(percent_num - last_percent[0]) >= 5 or percent_num >= 100:
                        last_percent[0] = percent_num
                        logger.info(f"Download progress: {percent} | Speed: {speed} | ETA: {eta}")

                        # Update message to user if provided
                        if progress_msg:
                            loop = asyncio.get_event_loop()
                            if loop.is_running():
                                asyncio.run_coroutine_threadsafe(
                                    progress_msg.edit_text(
                                        f"⏳ Загрузка: {percent}\n⚡ Скорость: {speed}\n⏱ Осталось: {eta}"),
                                    loop
                                )

                elif d['status'] == 'finished':
                    logger.info("Download finished, now post-processing...")
                    if progress_msg:
                        loop = asyncio.get_event_loop()
                        if loop.is_running():
                            asyncio.run_coroutine_threadsafe(
                                progress_msg.edit_text("📥 Загрузка завершена! Обрабатываю видео..."),
                                loop
                            )
            except Exception as e:
                logger.error(f"Progress hook error: {e}")

        # Check if ffmpeg is available, if not, use a format that doesn't require merging
        try:
            ffmpeg_path = "/usr/bin/ffmpeg"
            subprocess.run([ffmpeg_path, '-version'], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            logger.info("ffmpeg is installed and available")

            # If ffmpeg is available, use the specified format
            ydl_opts = {
                'format': f"{format_id}+bestaudio/best",
                'outtmpl': os.path.join(download_dir, '%(title)s-%(id)s.%(ext)s'),
                'retries': 3,
                'fragment_retries': 3,
                'merge_output_format': 'mp4',
                'progress_hooks': [progress_hook],
            }

        except (subprocess.CalledProcessError, FileNotFoundError):
            logger.warning("ffmpeg not found - downloading single format without merging")

            # No ffmpeg, use a simpler format that doesn't require merging
            ydl_opts = {
                'format': format_id,  # Just download the specific format without merging
                'outtmpl': os.path.join(download_dir, '%(title)s-%(id)s.%(ext)s'),
                'retries': 3,
                'fragment_retries': 3,
                'progress_hooks': [progress_hook],
            }

        # Initialize download message
        if progress_msg:
            await progress_msg.edit_text("⏳ Начинаю загрузку...")

        with YoutubeDL(ydl_opts) as ydl:
            # Download with progress
            info = await asyncio.get_event_loop().run_in_executor(
                executor,
                lambda: ydl.extract_info(url, download=True)
            )

            if not info:
                raise Exception("Could not get video info")

            output_file = ydl.prepare_filename(info)

            # Check if file exists or find it with different extension
            if not os.path.exists(output_file):
                base_name = os.path.splitext(output_file)[0]
                possible_files = [
                    os.path.join(download_dir, f)
                    for f in os.listdir(download_dir)
                    if f.startswith(os.path.basename(base_name))
                ]

                if possible_files:
                    output_file = possible_files[0]
                else:
                    raise FileNotFoundError(f"Downloaded file not found: {output_file}")

            # Update progress message
            if progress_msg:
                await progress_msg.edit_text("✅ Загрузка завершена! Отправляю файл...")

            logger.info(f"Download complete: {output_file}")
            return output_file, info

    except Exception as e:
        logger.error(f"Download error: {str(e)}")
        if progress_msg:
            await progress_msg.edit_text(f"❌ Ошибка загрузки: {str(e)}")
        raise

async def handle_format_selection(callback_query: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    url = data.get('url')
    formats = data.get('formats')
    # Parse callback data (e.g., "format:232:video:720p:3")
    callback_parts = callback_query.data.split(':')
    selected_index = int(callback_parts[-1])  # Last part is the index
    selected_format = formats[selected_index]

    status_message = await callback_query.message.edit_text("⏳ Скачиваю видео...")

    try:
        file_path, info = await download_video(url, selected_format['format_id'], state)
        await status_message.edit_text(f"✅ Видео скачано: {file_path}")
        with open(file_path, 'rb') as video:
            await callback_query.message.answer_document(video)
    except Exception as e:
        logger.error(f"Download error: {str(e)}")
        await status_message.edit_text("❗ Ошибка при скачивании")

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
        await handle_tiktok(message, url, me, bot,state)
    elif 'instagram.com' in url or 'instagr.am' in url or 'inst.ae' in url:
        await handle_instagram(message, url, me, bot)
    elif 'youtube.com' in url or 'youtu.be' in url:
        await handle_youtube(message, url, me, bot, state)
    else:
        await message.answe


COOKIES_FILE = "/tmp/youtube_cookies.txt"


def get_browser_user_agents():
    """Get realistic browser user agents"""
    return [
        # Latest Chrome
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',

        # Latest Firefox
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:120.0) Gecko/20100101 Firefox/120.0',

        # Latest Safari
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',

        # Mobile browsers
        'Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1',
        'Mozilla/5.0 (Android 14; Mobile; rv:120.0) Gecko/120.0 Firefox/120.0',
    ]

import random
import string

def generate_random_string(length=16):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def create_realistic_cookies():
    """Create cookies that mimic real browser behavior"""
    try:
        timestamp = int(time.time())
        session_id = random.randint(100000000000000, 999999999999999)

        cookies_content = f"""# Netscape HTTP Cookie File
# Generated by yt-dlp
.youtube.com\tTRUE\t/\tFALSE\t{timestamp + 31536000}\tCONSENT\tYES+cb.{time.strftime('%Y%m%d')}-{random.randint(10, 99)}-p0.en+FX+{random.randint(100, 999)}
.youtube.com\tTRUE\t/\tFALSE\t{timestamp + 31536000}\tVISITOR_INFO1_LIVE\t{random.choice(['Gt8aKOhOigw', 'K4N8DY4wRLU', 'y_GfyCBHGcU', 'Kj8dHB4s3Dk'])}
.youtube.com\tTRUE\t/\tFALSE\t{timestamp + 31536000}\tPREF\tf4=4000000&f6=40000000&tz=UTC&f7=100&hl=en&gl=US
.youtube.com\tTRUE\t/\tTRUE\t{timestamp + 31536000}\t__Secure-YEC\tCgtZZjhYUWdPaWd3NCIhEhgSFhML
.youtube.com\tTRUE\t/\tFALSE\t{timestamp + 31536000}\tGPS\t1
.youtube.com\tTRUE\t/\tFALSE\t{timestamp + 31536000}\tYSC\t{random.choice(['y_GfyCBHGcU', 'Kj8dHB4s3Dk', 'F5s8DJfhG2k', 'N3k8DJfhG7m'])}
.youtube.com\tTRUE\t/\tFALSE\t{timestamp + 31536000}\tSIDCC\tAJi4QfH{random.randint(1000000, 9999999)}
.youtube.com\tTRUE\t/\tTRUE\t{timestamp + 31536000}\t__Secure-1PSIDCC\tAJi4QfH{random.randint(1000000, 9999999)}
.youtube.com\tTRUE\t/\tFALSE\t{timestamp + 31536000}\tHSID\tA{session_id}
.youtube.com\tTRUE\t/\tTRUE\t{timestamp + 31536000}\tSSID\tA{session_id + 1}
.youtube.com\tTRUE\t/\tTRUE\t{timestamp + 31536000}\tAPISID\t{generate_random_string()}
.youtube.com\tTRUE\t/\tTRUE\t{timestamp + 31536000}\tSAPISID\t{generate_random_string()}
.youtube.com\tTRUE\t/\tFALSE\t{timestamp + 31536000}\tLOGIN_INFO\tAFmmF2swRgIhAK{random.randint(100000, 999999)}
"""

        with open(COOKIES_FILE, 'w', encoding='utf-8') as f:
            f.write(cookies_content)

        logger.info(f"Created realistic YouTube cookies: {COOKIES_FILE}")
        return True

    except Exception as e:
        logger.error(f"Failed to create cookies: {e}")
        return False


def get_optimal_ydl_options():
    """Get optimized yt-dlp options following GitHub FAQ recommendations"""
    user_agents = get_browser_user_agents()
    selected_ua = random.choice(user_agents)

    # Create fresh cookies
    create_realistic_cookies()

    return {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,

        # User agent (as recommended in FAQ)
        'http_headers': {
            'User-Agent': selected_ua,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'Cache-Control': 'max-age=0',
        },

        # Cookies (as recommended in FAQ)
        'cookiefile': COOKIES_FILE if os.path.exists(COOKIES_FILE) else None,

        # Network settings to avoid throttling
        'socket_timeout': 60,
        'retries': 3,
        'fragment_retries': 3,
        'extractor_retries': 3,

        # Rate limiting to avoid detection
        'sleep_interval': 1,
        'max_sleep_interval': 5,
        'sleep_interval_requests': 1,

        # Geo bypass
        'geo_bypass': True,
        'geo_bypass_country': 'US',

        # Additional anti-detection
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'web'],
                'player_skip': ['webpage'],
                'include_live_dash': False,
            }
        },

        # No metadata files to speed up
        'writeinfojson': False,
        'writesubtitles': False,
        'writeautomaticsub': False,
        'writethumbnail': False,
    }


async def try_youtube_extraction(url, max_attempts=3):
    """Try YouTube extraction with different strategies"""

    for attempt in range(max_attempts):
        strategy_name = f"attempt_{attempt + 1}"
        logger.info(f"YouTube extraction {strategy_name} for URL: {url}")

        try:
            # Wait between attempts to avoid rate limiting
            if attempt > 0:
                await asyncio.sleep(random.uniform(2.0, 5.0))

            # Get fresh options for each attempt
            ydl_opts = get_optimal_ydl_options()

            # Modify options based on attempt
            if attempt == 0:
                # First attempt: full quality
                pass
            elif attempt == 1:
                # Second attempt: lower quality preference
                ydl_opts['format'] = 'best[height<=720]/best'
                ydl_opts['extractor_args']['youtube']['player_client'] = ['android']
            else:
                # Third attempt: minimal quality
                ydl_opts['format'] = 'worst'
                ydl_opts['extractor_args']['youtube']['player_client'] = ['android']
                ydl_opts.pop('cookiefile', None)  # Try without cookies

            def extract_info():
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    return ydl.extract_info(url, download=False)

            info = await asyncio.get_event_loop().run_in_executor(executor, extract_info)

            if info:
                logger.info(f"Successfully extracted YouTube info on {strategy_name}")
                return info

        except Exception as e:
            error_msg = str(e).lower()
            logger.warning(f"YouTube extraction {strategy_name} failed: {e}")

            # Check for specific errors
            if 'sign in to confirm' in error_msg or 'not a bot' in error_msg:
                logger.warning("Bot detection encountered, trying next strategy")
                continue
            elif 'private' in error_msg or 'unavailable' in error_msg:
                logger.error("Video is private or unavailable")
                break
            elif 'age' in error_msg:
                logger.warning("Age restriction detected")
                continue

    logger.error("All YouTube extraction attempts failed")
    return None


@client_bot_router.callback_query(F.data.startswith("yt_download_"))
async def process_youtube_download_production(callback: CallbackQuery, state: FSMContext):
    """Process YouTube download with production error handling"""
    try:
        await callback.answer()

        # Parse format index
        format_index = int(callback.data.split('_')[2])

        # Get state data
        data = await state.get_data()
        url = data.get('youtube_url')
        formats = data.get('youtube_formats', [])
        info = data.get('youtube_info', {})

        if not url or not formats or format_index >= len(formats):
            await callback.message.edit_text("❌ Данные для загрузки не найдены")
            return

        selected_format = formats[format_index]
        title = info.get('title', 'Video')

        # Update message to show download progress
        await callback.message.edit_text(
            f"⏳ <b>Подготовка к загрузке...</b>\n\n"
            f"🎥 <b>{title}</b>\n"
            f"📋 <b>Формат:</b> {selected_format['quality']} {selected_format['ext'].upper()}\n"
            f"📦 <b>Тип:</b> {'Видео' if selected_format['type'] == 'video' else 'Аудио'}",
            parse_mode="HTML"
        )

        # Download the file
        await download_youtube_file_production(callback, url, selected_format, info)

    except Exception as e:
        logger.error(f"YouTube download callback error: {e}")
        await callback.message.edit_text("❌ Ошибка при обработке запроса на загрузку")


async def download_youtube_file_production(callback, url, format_data, video_info):
    """Download YouTube file with production error handling"""
    try:
        # Create temporary directory
        temp_dir = tempfile.mkdtemp(prefix='youtube_prod_')
        output_template = os.path.join(temp_dir, '%(title).50s.%(ext)s')

        # Configure download options
        ydl_opts = get_optimal_ydl_options()
        ydl_opts.update({
            'format': format_data['id'],
            'outtmpl': output_template,
        })

        # Add progress hook
        def progress_hook(d):
            if d['status'] == 'downloading':
                percent = d.get('_percent_str', '0%')
                speed = d.get('_speed_str', 'N/A')
                asyncio.create_task(update_download_progress(
                    callback.message,
                    f"⏬ Загрузка: {percent} ({speed})",
                    video_info,
                    format_data
                ))
            elif d['status'] == 'finished':
                asyncio.create_task(update_download_progress(
                    callback.message,
                    "✅ Подготовка файла к отправке...",
                    video_info,
                    format_data
                ))

        ydl_opts['progress_hooks'] = [progress_hook]

        # Download
        def download():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                return ydl.extract_info(url, download=True)

        download_info = await asyncio.get_event_loop().run_in_executor(executor, download)

        # Find downloaded file
        downloaded_file = None
        for file in os.listdir(temp_dir):
            if not file.endswith('.info.json') and os.path.isfile(os.path.join(temp_dir, file)):
                downloaded_file = os.path.join(temp_dir, file)
                break

        if not downloaded_file or not os.path.exists(downloaded_file):
            await callback.message.edit_text("❌ Загруженный файл не найден")
            return

        # Check file size
        file_size = os.path.getsize(downloaded_file)
        if file_size > 50 * 1024 * 1024:  # 50 MB Telegram limit
            await callback.message.edit_text(
                f"❌ <b>Файл слишком большой для Telegram</b>\n\n"
                f"📦 <b>Размер:</b> {file_size / (1024 * 1024):.1f} MB\n"
                f"📏 <b>Лимит Telegram:</b> 50 MB\n\n"
                f"Выберите формат с меньшим качеством.",
                parse_mode="HTML"
            )
            os.remove(downloaded_file)
            return

        # Send file
        title = video_info.get('title', 'Video')
        uploader = video_info.get('uploader', 'Unknown')

        caption = (
            f"🎥 {title}\n"
            f"👤 {uploader}\n"
            f"📋 {format_data['quality']} {format_data['ext'].upper()}\n"
            f"📦 {file_size / (1024 * 1024):.1f} MB\n\n"
            f"📥 Скачано через @{(await callback.bot.get_me()).username}"
        )

        with open(downloaded_file, 'rb') as file:
            if format_data['type'] == 'video':
                await callback.bot.send_video(
                    chat_id=callback.message.chat.id,
                    video=file,
                    caption=caption,
                    supports_streaming=True
                )
            else:
                await callback.bot.send_audio(
                    chat_id=callback.message.chat.id,
                    audio=file,
                    caption=caption,
                    title=title
                )

        # Cleanup
        os.remove(downloaded_file)
        os.rmdir(temp_dir)

        await callback.message.delete()
        # await state.clear()

        # Analytics
        from modul.clientbot import shortcuts
        await shortcuts.add_to_analitic_data((await callback.bot.get_me()).username, url)

    except Exception as e:
        logger.error(f"YouTube download error: {e}")
        await callback.message.edit_text(
            f"❌ <b>Ошибка при загрузке</b>\n\n"
            f"<code>{str(e)[:100]}...</code>\n\n"
            f"Попробуйте выбрать другой формат или повторите позже.",
            parse_mode="HTML"
        )

@client_bot_router.callback_query(F.data == "too_large")
async def handle_too_large_callback(callback: CallbackQuery):
    """Handle too large file selection"""
    await callback.answer(
        "Этот файл слишком большой для Telegram (более 50 MB). "
        "Выберите формат с меньшим качеством.",
        show_alert=True
    )

# Use this function instead of the old handle_youtube
async def handle_youtube(message: Message, url: str, me, bot, state: FSMContext):
    """Wrapper to use production YouTube handler"""
    await handle_youtube_production(message, url, me, bot, state)

async def update_download_progress(message, text, video_info, format_data):
    """Update download progress message"""
    try:
        title = video_info.get('title', 'Video')
        await message.edit_text(
            f"{text}\n\n"
            f"🎥 <b>{title}</b>\n"
            f"📋 <b>Формат:</b> {format_data['quality']} {format_data['ext'].upper()}",
            parse_mode="HTML"
        )
    except:
        pass


async def handle_youtube_production(message: Message, url: str, me, bot, state: FSMContext):
    """Production-ready YouTube handler"""
    try:
        # Initial message
        progress_msg = await message.answer("🔍 Получаю информацию о YouTube видео...")

        # Extract video information
        try:
            info = await try_youtube_extraction(url)

            if not info:
                await progress_msg.edit_text(
                    "❌ <b>Не удалось загрузить видео с YouTube</b>\n\n"
                    "🛡️ <b>Возможные причины:</b>\n"
                    "• YouTube обнаружил автоматическую загрузку\n"
                    "• Видео требует авторизации\n"
                    "• Географические ограничения\n"
                    "• Возрастные ограничения\n"
                    "• Видео приватное или удалено\n\n"
                    "💡 <b>Рекомендации:</b>\n"
                    "• Попробуйте публичное видео\n"
                    "• Используйте короткие видео (до 10 минут)\n"
                    "• Повторите попытку через 10-15 минут\n"
                    "• Попробуйте другие платформы (Instagram, TikTok)\n\n"
                    "🔧 <b>Для разработчиков:</b>\n"
                    "Рассмотрите использование browser cookies с опцией <code>--cookies-from-browser</code>",
                    parse_mode="HTML"
                )
                return

            # Extract video details
            title = info.get('title', 'Unknown Video')
            duration = info.get('duration', 0)
            uploader = info.get('uploader', 'Unknown')
            view_count = info.get('view_count', 0)
            formats = info.get('formats', [])

            # Filter usable formats
            video_formats = []
            audio_formats = []

            for fmt in formats:
                if not fmt.get('url'):
                    continue

                vcodec = fmt.get('vcodec', 'none')
                acodec = fmt.get('acodec', 'none')
                height = fmt.get('height', 0)
                abr = fmt.get('abr', 0)
                filesize = fmt.get('filesize') or fmt.get('filesize_approx') or 0

                # Filter video formats (reasonable quality for Telegram)
                if vcodec != 'none' and height > 0 and height <= 1080:
                    video_formats.append({
                        'format_id': fmt.get('format_id'),
                        'height': height,
                        'ext': fmt.get('ext', 'mp4'),
                        'filesize': filesize,
                        'fps': fmt.get('fps', 0)
                    })

                # Filter audio formats
                elif acodec != 'none' and vcodec == 'none' and abr > 0:
                    audio_formats.append({
                        'format_id': fmt.get('format_id'),
                        'abr': abr,
                        'ext': fmt.get('ext', 'm4a'),
                        'filesize': filesize
                    })

            # Sort and limit formats
            video_formats.sort(key=lambda x: x['height'], reverse=True)
            audio_formats.sort(key=lambda x: x['abr'], reverse=True)

            # Take best formats for each category
            best_formats = []

            # Add video formats (limit to 4 best)
            for vf in video_formats[:4]:
                quality = f"{vf['height']}p"
                if vf['fps'] > 30:
                    quality += f"{int(vf['fps'])}"

                size_text = ""
                if vf['filesize'] > 0:
                    size_mb = vf['filesize'] / (1024 * 1024)
                    if size_mb > 1024:
                        size_text = f" ({size_mb / 1024:.1f} GB)"
                    elif size_mb > 0:
                        size_text = f" ({size_mb:.0f} MB)"

                best_formats.append({
                    'id': vf['format_id'],
                    'type': 'video',
                    'quality': quality,
                    'ext': vf['ext'],
                    'label': f"📹 {quality} {vf['ext'].upper()}{size_text}",
                    'filesize': vf['filesize']
                })

            # Add best audio format
            if audio_formats:
                af = audio_formats[0]
                size_text = ""
                if af['filesize'] > 0:
                    size_mb = af['filesize'] / (1024 * 1024)
                    size_text = f" ({size_mb:.0f} MB)"

                best_formats.append({
                    'id': af['format_id'],
                    'type': 'audio',
                    'quality': f"{int(af['abr'])}kbps",
                    'ext': af['ext'],
                    'label': f"🎵 Аудио {int(af['abr'])}kbps {af['ext'].upper()}{size_text}",
                    'filesize': af['filesize']
                })

            if not best_formats:
                await progress_msg.edit_text(
                    f"❌ <b>Видео найдено, но нет доступных форматов</b>\n\n"
                    f"🎥 <b>{title}</b>\n"
                    f"👤 <b>Канал:</b> {uploader}\n\n"
                    f"Возможно, видео защищено от скачивания.",
                    parse_mode="HTML"
                )
                return

            # Create download keyboard
            keyboard = InlineKeyboardBuilder()

            for i, fmt in enumerate(best_formats):
                # Check if file is too large (45 MB limit to be safe)
                if fmt['filesize'] > 45 * 1024 * 1024:
                    label = f"⚠️ {fmt['label']} (слишком большой)"
                    callback_data = "too_large"
                else:
                    label = fmt['label']
                    callback_data = f"yt_download_{i}"

                keyboard.row(InlineKeyboardButton(
                    text=label,
                    callback_data=callback_data
                ))

            keyboard.row(InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_download"))

            # Format info message
            duration_str = ""
            if duration:
                minutes, seconds = divmod(duration, 60)
                hours, minutes = divmod(minutes, 60)
                if hours:
                    duration_str = f" • {hours:02d}:{minutes:02d}:{seconds:02d}"
                else:
                    duration_str = f" • {minutes:02d}:{seconds:02d}"

            view_count_str = ""
            if view_count:
                if view_count > 1_000_000:
                    view_count_str = f" • {view_count / 1_000_000:.1f}M просмотров"
                elif view_count > 1_000:
                    view_count_str = f" • {view_count / 1_000:.1f}K просмотров"
                else:
                    view_count_str = f" • {view_count} просмотров"

            info_text = (
                f"✅ <b>Видео успешно загружено!</b>\n\n"
                f"🎥 <b>{title}</b>\n"
                f"👤 <b>Канал:</b> {uploader}{duration_str}{view_count_str}\n\n"
                f"📥 <b>Выберите качество для скачивания:</b>"
            )

            # Store data in state
            await state.update_data(
                youtube_url=url,
                youtube_info=info,
                youtube_formats=best_formats
            )

            await progress_msg.edit_text(
                info_text,
                reply_markup=keyboard.as_markup(),
                parse_mode="HTML"
            )

        except Exception as e:
            logger.error(f"YouTube processing error: {e}")
            await progress_msg.edit_text(
                f"❌ <b>Ошибка при обработке видео</b>\n\n"
                f"🔧 <b>Техническая информация:</b>\n"
                f"<code>{str(e)[:100]}...</code>\n\n"
                f"Попробуйте повторить через несколько минут.",
                parse_mode="HTML"
            )

    except Exception as e:
        logger.error(f"YouTube handler error: {e}")
        await message.answer(
            "❌ Произошла неожиданная ошибка при обработке YouTube видео."
        )


def create_youtube_cookies_file():
    """Create an improved YouTube cookies file to avoid bot detection"""
    try:
        # Create cookies content with more realistic values
        cookies_content = """# Netscape HTTP Cookie File
.youtube.com	TRUE	/	FALSE	1999999999	CONSENT	YES+cb.20240101-00-p0.en+FX+000
.youtube.com	TRUE	/	FALSE	1999999999	VISITOR_INFO1_LIVE	y_GfyCBHGcU
.youtube.com	TRUE	/	FALSE	1999999999	PREF	f4=4000000&tz=UTC&f6=40000000
.youtube.com	TRUE	/	TRUE	1999999999	__Secure-YEC	Cgs4OTQ3NDcyNjMwNBIBTQ%3D%3D
.youtube.com	TRUE	/	FALSE	1999999999	GPS	1
.youtube.com	TRUE	/	FALSE	1999999999	YSC	y_GfyCBHGcU
.youtube.com	TRUE	/	FALSE	1999999999	SIDCC	AJi4QfF7VhEF0w
"""

        with open(COOKIES_FILE, 'w', encoding='utf-8') as f:
            f.write(cookies_content)

        logger.info(f"Created YouTube cookies file: {COOKIES_FILE}")
        return True

    except Exception as e:
        logger.error(f"Failed to create cookies file: {e}")
        return False


def get_youtube_ydl_options(format_id=None, audio_only=False):
    """Get optimized yt-dlp options for YouTube"""

    # Create cookies file if it doesn't exist
    if not os.path.exists(COOKIES_FILE):
        create_youtube_cookies_file()

    # User agents rotation
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    ]

    import random

    opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
        'writeinfojson': False,
        'writesubtitles': False,
        'writeautomaticsub': False,
        'writethumbnail': False,

        # Anti-bot measures
        'http_headers': {
            'User-Agent': random.choice(user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-us,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.7',
            'Keep-Alive': '300',
            'Connection': 'keep-alive',
        },

        # Use cookies
        'cookiefile': COOKIES_FILE if os.path.exists(COOKIES_FILE) else None,

        # Network and retry settings
        'socket_timeout': 30,
        'retries': 3,
        'fragment_retries': 3,
        'extractor_retries': 3,

        # Rate limiting to avoid detection
        'sleep_interval': 1,
        'max_sleep_interval': 3,
        'sleep_interval_requests': 1,
        'sleep_interval_subtitles': 1,

        # Geo bypass
        'geo_bypass': True,
        'geo_bypass_country': 'US',
    }

    # Format selection
    if audio_only:
        opts['format'] = 'bestaudio[ext=m4a]/bestaudio/best'
    elif format_id:
        opts['format'] = format_id
    else:
        # Default to reasonable quality
        opts['format'] = 'best[height<=720]/best[height<=480]/best'

    return opts


async def extract_youtube_info(url):
    """Extract YouTube video information without downloading"""
    try:
        def extract_info():
            ydl_opts = get_youtube_ydl_options()
            with YoutubeDL(ydl_opts) as ydl:
                return ydl.extract_info(url, download=False)

        info = await asyncio.get_event_loop().run_in_executor(executor, extract_info)
        return info

    except Exception as e:
        logger.error(f"YouTube info extraction failed: {e}")

        # Try with minimal options as fallback
        try:
            def extract_minimal():
                minimal_opts = {
                    'quiet': True,
                    'no_warnings': True,
                    'extract_flat': False,
                    'format': 'worst',
                    'http_headers': {
                        'User-Agent': 'yt-dlp/2023.12.30',
                    },
                    'geo_bypass': True,
                }
                with YoutubeDL(minimal_opts) as ydl:
                    return ydl.extract_info(url, download=False)

            info = await asyncio.get_event_loop().run_in_executor(executor, extract_minimal)
            logger.info("Fallback extraction succeeded")
            return info

        except Exception as e2:
            logger.error(f"Fallback extraction also failed: {e2}")
            return None


async def get_youtube_formats(url):
    """Get available YouTube formats"""
    try:
        info = await extract_youtube_info(url)
        if not info:
            return None, []

        title = info.get('title', 'Unknown Video')
        duration = info.get('duration', 0)
        uploader = info.get('uploader', 'Unknown')
        view_count = info.get('view_count', 0)

        # Process formats
        formats = info.get('formats', [])
        video_formats = []
        audio_formats = []

        # Filter video formats
        for fmt in formats:
            if not fmt.get('url'):
                continue

            format_id = fmt.get('format_id', '')
            ext = fmt.get('ext', 'mp4')
            filesize = fmt.get('filesize') or fmt.get('filesize_approx') or 0

            # Video formats
            if fmt.get('vcodec') and fmt.get('vcodec') != 'none':
                height = fmt.get('height', 0)
                fps = fmt.get('fps', 0)

                if height and height > 0:
                    quality_label = f"{height}p"
                    if fps and fps > 30:
                        quality_label += f"{int(fps)}"

                    video_formats.append({
                        'format_id': format_id,
                        'quality': quality_label,
                        'ext': ext,
                        'filesize': filesize,
                        'height': height,
                        'type': 'video'
                    })

            # Audio formats
            elif fmt.get('acodec') and fmt.get('acodec') != 'none':
                abr = fmt.get('abr', 0)
                if abr and abr > 0:
                    audio_formats.append({
                        'format_id': format_id,
                        'quality': f"{int(abr)}kbps",
                        'ext': ext,
                        'filesize': filesize,
                        'type': 'audio'
                    })

        # Sort and limit formats
        video_formats.sort(key=lambda x: x['height'], reverse=True)
        audio_formats.sort(key=lambda x: int(x['quality'].replace('kbps', '')), reverse=True)

        # Limit to prevent message size issues
        video_formats = video_formats[:6]
        audio_formats = audio_formats[:3]

        video_info = {
            'title': title,
            'duration': duration,
            'uploader': uploader,
            'view_count': view_count,
            'thumbnail': info.get('thumbnail')
        }

        return video_info, video_formats + audio_formats

    except Exception as e:
        logger.error(f"Error getting YouTube formats: {e}")
        return None, []


async def process_youtube_callback(callback: CallbackQuery, state: FSMContext, bot):
    """Process YouTube format selection callback"""
    try:
        # Parse callback data: yt_dl_<index>_<type>_<quality>
        parts = callback.data.split('_')
        if len(parts) < 4:
            await callback.answer("❌ Неверные данные")
            return

        format_index = int(parts[2])
        format_type = parts[3]
        quality = '_'.join(parts[4:]) if len(parts) > 4 else 'unknown'

        # Get data from state
        data = await state.get_data()
        url = data.get('youtube_url')
        formats = data.get('youtube_formats', [])
        video_info = data.get('youtube_info', {})

        if not url or not formats or format_index >= len(formats):
            await callback.answer("❌ Данные не найдены")
            return

        selected_format = formats[format_index]

        # Update message
        await callback.message.edit_text(
            f"⏳ Подготовка к загрузке...\n\n"
            f"🎥 <b>{video_info.get('title', 'Video')}</b>\n"
            f"📋 <b>Формат:</b> {quality} {selected_format['ext'].upper()}\n"
            f"📦 <b>Тип:</b> {'Видео' if format_type == 'video' else 'Аудио'}",
            parse_mode="HTML"
        )

        await callback.answer()

        # Progress callback
        async def progress_callback(text):
            try:
                await callback.message.edit_text(
                    f"{text}\n\n"
                    f"🎥 <b>{video_info.get('title', 'Video')}</b>\n"
                    f"📋 <b>Формат:</b> {quality} {selected_format['ext'].upper()}",
                    parse_mode="HTML"
                )
            except:
                pass

        # Download the video
        try:
            file_path, info = await download_youtube_video(
                url,
                selected_format['format_id'],
                progress_callback
            )

            # Check file size (50 MB Telegram limit)
            file_size = os.path.getsize(file_path)
            if file_size > 50 * 1024 * 1024:
                await callback.message.edit_text(
                    f"❌ Файл слишком большой для Telegram\n"
                    f"📦 Размер: {file_size / (1024 * 1024):.1f} MB (макс: 50 MB)\n\n"
                    f"Выберите формат с меньшим качеством."
                )
                os.remove(file_path)
                return

            # Send file
            caption = (
                f"🎥 {video_info.get('title', 'Video')}\n"
                f"👤 {video_info.get('uploader', 'Unknown')}\n"
                f"📋 {quality} {selected_format['ext'].upper()}\n"
                f"📦 {file_size / (1024 * 1024):.1f} MB\n\n"
                f"📥 Скачано через @{(await bot.get_me()).username}"
            )

            with open(file_path, 'rb') as video_file:
                if format_type == 'video':
                    await bot.send_video(
                        chat_id=callback.message.chat.id,
                        video=video_file,
                        caption=caption,
                        supports_streaming=True
                    )
                else:
                    await bot.send_audio(
                        chat_id=callback.message.chat.id,
                        audio=video_file,
                        caption=caption,
                        title=video_info.get('title', 'Audio')
                    )

            # Cleanup
            os.remove(file_path)
            os.rmdir(os.path.dirname(file_path))

            await callback.message.delete()
            await state.clear()

            # Analytics
            from modul.clientbot import shortcuts
            await shortcuts.add_to_analitic_data((await bot.get_me()).username, url)

        except Exception as e:
            logger.error(f"YouTube download error: {e}")
            await callback.message.edit_text(
                f"❌ Ошибка при загрузке:\n{str(e)[:200]}...\n\n"
                f"Попробуйте выбрать другой формат."
            )

    except Exception as e:
        logger.error(f"YouTube callback error: {e}")
        await callback.answer("❌ Произошла ошибка")

from modul.loader import client_bot_router
from aiogram import F

@client_bot_router.callback_query(F.data.startswith("yt_dl_"))
async def youtube_download_callback(callback: CallbackQuery, state: FSMContext):
    """Handle YouTube download callbacks"""
    await process_youtube_callback(callback, state, callback.bot)

@client_bot_router.callback_query(F.data == "cancel_download")
async def cancel_download_callback(callback: CallbackQuery, state: FSMContext):
    """Handle download cancellation"""
    await callback.message.edit_text("❌ Загрузка отменена.")
    await callback.answer("Отменено")
    await state.clear()

@client_bot_router.callback_query(F.data == "ignore")
async def ignore_callback(callback: CallbackQuery):
    """Ignore section header callbacks"""
    await callback.answer()

import tempfile
async def download_youtube_video(url, format_id, progress_callback=None):
    """Download YouTube video with specified format"""
    try:
        temp_dir = tempfile.mkdtemp(prefix='youtube_')
        output_template = os.path.join(temp_dir, '%(title)s.%(ext)s')

        ydl_opts = get_youtube_ydl_options(format_id)
        ydl_opts.update({
            'outtmpl': output_template,
            'writeinfojson': True,
        })

        # Add progress hook
        if progress_callback:
            def progress_hook(d):
                if d['status'] == 'downloading':
                    percent = d.get('_percent_str', '0%')
                    speed = d.get('_speed_str', 'N/A')
                    asyncio.create_task(progress_callback(f"⏬ Загрузка: {percent} ({speed})"))
                elif d['status'] == 'finished':
                    asyncio.create_task(progress_callback("✅ Обработка файла..."))

            ydl_opts['progress_hooks'] = [progress_hook]

        def download():
            with YoutubeDL(ydl_opts) as ydl:
                return ydl.extract_info(url, download=True)

        info = await asyncio.get_event_loop().run_in_executor(executor, download)

        if not info:
            raise Exception("Download failed - no info returned")

        # Find the downloaded file
        downloaded_file = None
        for file in os.listdir(temp_dir):
            if not file.endswith('.info.json'):
                downloaded_file = os.path.join(temp_dir, file)
                break

        if not downloaded_file or not os.path.exists(downloaded_file):
            raise Exception("Downloaded file not found")

        return downloaded_file, info

    except Exception as e:
        logger.error(f"YouTube download error: {e}")
        raise



@client_bot_router.callback_query(FormatCallback.filter())
async def process_format_selection(callback: CallbackQuery, callback_data: FormatCallback, state: FSMContext, bot):
    try:
        # Remove format buttons
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.answer("⏳ Начинаю загрузку...")

        # Get data from state
        data = await state.get_data()
        url = data.get('youtube_url')
        formats = data.get('formats', [])
        title = data.get('title', 'Video')

        if not url or not formats:
            await callback.message.answer("❌ Ошибка: данные не найдены")
            return

        selected_format = formats[callback_data.index]

        # Create progress message
        progress_msg = await callback.message.answer(
            f"⏳ Подготовка к загрузке {title}...\n"
            f"Формат: {callback_data.quality}"
        )

        try:
            # Download with progress updates
            file_path, info = await download_video(url, selected_format['format_id'], state, progress_msg)

            # Send file to user
            try:
                me = await bot.get_me()
                caption = f"🎥 {title}"
                if callback_data.type == 'video':
                    caption += f" ({callback_data.quality})"
                caption += f"\nСкачано через @{me.username}"

                file_size = os.path.getsize(file_path) / (1024 * 1024)  # Size in MB
                size_text = f"{file_size:.1f} MB"
                if file_size > 1024:
                    size_text = f"{file_size / 1024:.1f} GB"
                caption += f"\n📦 Размер: {size_text}"

                # Send video or audio
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

                # Delete progress message after success
                await progress_msg.delete()

            finally:
                # Clean up file
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logger.info(f"Cleaned up file: {file_path}")

            await state.clear()

        except Exception as e:
            logger.error(f"Download error: {str(e)}")
            await progress_msg.edit_text(f"❌ Ошибка при загрузке: {str(e)}")

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


# @client_bot_router.message()
# async def instagram_handler(message: Message, bot):
#     url = message.text
#     if 'instagram.com' in url or 'instagr.am' in url:
#         me = await bot.get_me()
#         await handle_instagram(message, url, me, bot)

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
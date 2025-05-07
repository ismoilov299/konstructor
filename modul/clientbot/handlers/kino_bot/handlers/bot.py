import asyncio
import subprocess
import time
import traceback
from contextlib import suppress

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
from modul.clientbot.handlers.leomatch.handlers.registration import bot_start_lets_leo
from modul.clientbot.handlers.leomatch.handlers.start import bot_start, bot_start_cancel
from modul.clientbot.handlers.refs.data.excel_converter import convert_to_excel
from modul.clientbot.handlers.refs.data.states import ChangeAdminInfo
from modul.clientbot.handlers.refs.handlers.bot import start_ref
from modul.clientbot.handlers.refs.keyboards.buttons import main_menu_bt, main_menu_bt2, payments_action_in, \
    declined_in, accepted_in, imp_menu_in
from modul.clientbot.handlers.refs.shortcuts import plus_ref, plus_money, get_actual_price, get_all_wait_payment, \
    change_price, change_min_amount, get_actual_min_amount, status_declined, status_accepted, check_ban, \
    get_user_info_db, changebalance_db, addbalance_db, ban_unban_db
from modul.clientbot.keyboards import reply_kb
from modul.clientbot.shortcuts import get_all_users, get_bot_by_username, get_bot_by_token, get_users, users_count
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

class Download(StatesGroup):
    download = State()


# Callback data
class FormatCallback(CallbackData, prefix="format"):
    format_id: str
    type: str
    quality: str
    index: int

# Thread pool for CPU-intensive tasks
executor = ThreadPoolExecutor(max_workers=4)


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


@client_bot_router.message(Command('admin'), AdminFilter())
async def admin(message: types.Message):
    await message.answer('Админ панель', reply_markup=admin_kb)


@client_bot_router.callback_query(F.data == 'admin_send_message', AdminFilter(), StateFilter('*'))
async def admin_send_message(call: CallbackQuery, state: FSMContext):
    await state.set_state(SendMessagesForm.message)
    await call.message.edit_text('Отправьте сообщение для рассылки (текст, фото, видео и т.д.)', reply_markup=cancel_kb)



@client_bot_router.message(SendMessagesForm.message)
async def admin_send_message_msg(message: types.Message, state: FSMContext):
    await state.clear()
    bot_db = await shortcuts.get_bot(message.bot)
    users = await get_all_users(bot_db)

    if not users:
        await message.answer("Нет пользователей для рассылки.")
        return

    success_count = 0
    fail_count = 0

    for user_id in users:
        try:
            if message.text:
                await message.bot.send_message(chat_id=user_id, text=message.text)
            elif message.photo:
                await message.bot.send_photo(chat_id=user_id, photo=message.photo[-1].file_id, caption=message.caption)
            elif message.video:
                await message.bot.send_video(chat_id=user_id, video=message.video.file_id, caption=message.caption)
            elif message.audio:
                await message.bot.send_audio(chat_id=user_id, audio=message.audio.file_id, caption=message.caption)
            elif message.document:
                await message.bot.send_document(chat_id=user_id, document=message.document.file_id, caption=message.caption)
            else:
                await message.bot.copy_message(chat_id=user_id, from_chat_id=message.chat.id, message_id=message.message_id)

            success_count += 1
        except Exception as e:
            fail_count += 1
            logger.error(f"Ошибка при отправке сообщения пользователю {user_id}: {e}")

    await message.answer(
        f'Рассылка завершена!\n'
        f'Успешно отправлено: {success_count}\n'
        f'Не удалось отправить: {fail_count}'
    )



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
                    f"💳 Баланс юзера: {user_info[2]} руб.\n"
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
        print(new_min_payout)

        await change_min_amount(new_min_payout)

        await message.delete()
        if edit_msg:
            await edit_msg.delete()

        await message.answer(
            f"Минимальная выплата успешно изменена на {new_min_payout:.1f} руб."
        )
        await state.clear()
        await start(message, state, bot)

    except ValueError:
        await message.answer("❗ Введите корректное числовое значение.")
    except Exception as e:
        logger.error(f"Ошибка при обновлении минимальной выплаты: {e}")
        await message.answer("🚫 Не удалось изменить минимальную выплату.")
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
    await call.message.edit_text('Отправьте id канала\n\n'
                                 'Убедитесь в том, что бот является администратором в канале\n\n'
                                 '@username_to_id_bot id канала можно получить у этого бота',
                                 reply_markup=cancel_kb)


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
    try:
        channel_id = int(message.text)
        # 1) Получаем объект Bot напрямую из message:
        bot = message.bot

        # 2) Узнаём информацию о чате (метод GetChat)
        chat_data = await bot(GetChat(chat_id=channel_id, flags={"raw": True}))
        print(chat_data)
        chat_info = await bot(GetChat(chat_id=channel_id))

        # 3) Проверяем, что это именно канал
        if chat_info.type != "channel":
            await message.answer(
                "Указанный ID не является каналом. Пожалуйста, введите ID канала.",
                reply_markup=cancel_kb
            )
            return

        # 4) Проверяем, что бот — администратор в этом канале (GetChatMember)
        bot_member = await bot(GetChatMember(chat_id=channel_id, user_id=bot.id))
        if bot_member.status not in ["administrator", "creator"]:
            await message.answer(
                "Бот не является администратором канала. Пожалуйста, добавьте бота в администраторы канала.",
                reply_markup=cancel_kb
            )
            return

        # 5) Проверяем / создаём invite link (CreateChatInviteLink)
        invite_link = chat_info.invite_link
        if not invite_link:
            link_data = await bot(CreateChatInviteLink(chat_id=channel_id))
            invite_link = link_data.invite_link

        # 6) Добавляем в базу (ваша функция)
        await create_channel_sponsor(channel_id)
        await state.clear()

        # 7) Формируем итоговый список строк для ответа
        channel_info = [
            "✅ Канал успешно добавлен!",
            f"📣 Название: {chat_info.title}",
            f"🆔 ID: {channel_id}",
            f"🔗 Ссылка: {invite_link}"
        ]

        # 8) Если доступны реакции, добавляем информацию
        if chat_info.available_reactions:
            try:
                # chat_info.available_reactions может быть списком объектов-реакций
                # Тут зависит от вашей сериализации. Предположим, это список dict
                reactions = chat_info.available_reactions
                if reactions:
                    reaction_types = [
                        r.get("type", "unknown") for r in reactions
                    ]
                    channel_info.append(
                        f"💫 Доступные реакции: {', '.join(reaction_types)}"
                    )
            except Exception as e:
                logger.warning(f"Failed to process reactions: {e}")

        # 9) Отправляем готовый текст
        await message.answer(
            "\n\n".join(channel_info),
            disable_web_page_preview=True
        )

    except ValueError:
        # int(...) не смог преобразовать текст → сообщаем об ошибке формата
        await message.answer(
            "Неверный формат. Пожалуйста, введите числовой ID канала.",
            reply_markup=cancel_kb
        )
    except TelegramBadRequest as e:
        logger.error(f"Telegram API error: {e}")
        await message.answer(
            "Бот не смог найти канал. Пожалуйста, проверьте ID канала.",
            reply_markup=cancel_kb
        )
    except Exception as e:
        logger.error(f"Channel add error: channel_id={channel_id}, error={str(e)}")
        logger.exception("Detailed error:")
        await message.answer(
            "Произошла ошибка. Пожалуйста, попробуйте еще раз.",
            reply_markup=cancel_kb
        )

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

        sub_status = await check_subs(message.from_user.id, bot)
        if not sub_status:
            kb = await get_subs_kb(bot)
            await message.answer(
                '<b>Чтобы воспользоваться ботом, необходимо подписаться на каналы:</b>',
                reply_markup=kb,
                parse_mode="HTML"
            )
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

            state_data = await state.get_data()
            print(f"State after saving referral: {state_data}")

        channels = await get_channels_for_check()
        if channels:
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

            if not_subscribed_channels:
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
                state_data = await state.get_data()
                print(f"State before channel check (user not subscribed): {state_data}")
                return False

        state_data = await state.get_data()
        print(f"State after channel check (user subscribed): {state_data}")

        bot_db = await shortcuts.get_bot(bot)
        current_user_id = message.from_user.id

        @sync_to_async
        def check_user_in_specific_bot(user_id, bot_token):
            try:
                bot_obj = models.Bot.objects.get(token=bot_token)

                client_user = models.ClientBotUser.objects.filter(
                    uid=user_id,
                    bot=bot_obj
                ).first()

                return client_user is not None
            except Exception as e:
                logger.error(f"Error checking user in specific bot: {e}")
                return False

        is_registered = await check_user_in_specific_bot(current_user_id, bot.token)

        if not is_registered:
            new_user = await add_user(
                tg_id=current_user_id,
                user_name=message.from_user.first_name,
                invited="Direct" if not referral else "Referral",
                invited_id=int(referral) if referral else None,
                bot_token=bot.token
            )
            print(f"➕ Added user {current_user_id} to database, result: {new_user}")

            if referral:
                try:
                    ref_id = int(referral)
                    print(f"🔄 Processing referral for user {current_user_id} from {ref_id}")

                    if ref_id != current_user_id:
                        print(f"👥 User {current_user_id} referred by {ref_id}")

                        referrer_exists = await check_user_in_specific_bot(ref_id, bot.token)

                        if not referrer_exists:
                            print(f"⚠️ Referrer {ref_id} not found in this bot's database, skipping referral")
                        else:
                            @sync_to_async
                            @transaction.atomic
                            def update_referrer(ref_id, bot_token):
                                try:
                                    from modul.models import Bot
                                    current_bot = Bot.objects.get(token=bot_token)

                                    user_tg = UserTG.objects.select_for_update().get(uid=ref_id)

                                    client_bot_user, created = ClientBotUser.objects.get_or_create(
                                        uid=ref_id,
                                        bot=current_bot,
                                        defaults={
                                            'user': user_tg,
                                            'balance': 0,
                                            'referral_count': 0,
                                            'referral_balance': 0
                                        }
                                    )

                                    admin_info = AdminInfo.objects.filter(bot_token=bot_token).first()
                                    price = float(admin_info.price) if admin_info and admin_info.price else 3.0

                                    client_bot_user.referral_count += 1
                                    client_bot_user.referral_balance += price
                                    client_bot_user.save()

                                    user_tg.refs += 1
                                    user_tg.balance += price
                                    user_tg.save()

                                    print(
                                        f"💰 Updated referrer {ref_id} for bot {current_bot.username}: referrals={client_bot_user.referral_count}, balance={client_bot_user.referral_balance}")
                                    return True, price
                                except UserTG.DoesNotExist:
                                    print(f"❓ Referrer {ref_id} not found in UserTG table")
                                    return False, 0
                                except Exception as e:
                                    print(f"⚠️ Error updating referrer: {e}")
                                    traceback.print_exc()
                                    return False, 0

                            if referrer_exists:
                                success, reward_amount = await update_referrer(ref_id, bot.token)
                                print(f"✅ Referrer update success for user {current_user_id}: {success}")

                                if success:
                                    try:
                                        user_name = html.escape(message.from_user.first_name)
                                        user_profile_link = f'tg://user?id={current_user_id}'

                                        await asyncio.sleep(1)

                                        await bot.send_message(
                                            chat_id=ref_id,
                                            text=f"У вас новый реферал! <a href='{user_profile_link}'>{user_name}</a>\nВам начислено {reward_amount}₽",
                                            parse_mode="html"
                                        )
                                        print(f"📨 Sent referral notification to {ref_id} about user {current_user_id}")
                                    except Exception as e:
                                        print(f"⚠️ Error sending notification to referrer {ref_id}: {e}")
                    else:
                        print(f"🚫 Self-referral detected: user {current_user_id} trying to refer themselves")
                except ValueError:
                    print(f"❌ Invalid referrer_id: {referral}")
        else:
            print(f"ℹ️ User {current_user_id} already registered with this bot, skipping registration")

        await start(message, state, bot)
    except Exception as e:
        logger.error(f"Error in start handler: {e}")
        traceback.print_exc()
        await message.answer(
            "Произошла ошибка при запуске. Пожалуйста, попробуйте позже."
        )


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


client_bot_router.message.register(bot_start, F.text == "🫰 Знакомства",DavinchiBotFilter())
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


class DownloaderBotFilter(Filter):
    async def __call__(self, message: types.Message, bot: Bot) -> bool:
        bot_db = await shortcuts.get_bot(bot)
        return shortcuts.have_one_module(bot_db, "download")


def get_best_formats(formats):
    video_formats = []
    audio_format = None
    seen_qualities = set()

    # Log the total number of formats found
    logger.debug(f"Total formats found: {len(formats)}")

    for fmt in formats:
        if not isinstance(fmt, dict):
            continue

        # Add more detailed logging
        logger.debug(
            f"Format: {fmt.get('format_id')} - vcodec: {fmt.get('vcodec')} - acodec: {fmt.get('acodec')} - ext: {fmt.get('ext')} - height: {fmt.get('height')}")

        vcodec = fmt.get('vcodec', 'none')
        acodec = fmt.get('acodec', 'none')

        # Only add video formats with real height values
        if vcodec != 'none' and vcodec != 'NA':
            height = fmt.get('height', 0)
            if height and height not in seen_qualities and height > 0:
                seen_qualities.add(height)
                video_formats.append(fmt)
                logger.debug(f"Added video format: {fmt.get('format_id')} - {height}p")

        # Only select audio formats with no video
        if acodec != 'none' and vcodec == 'none':
            if not audio_format or (fmt.get('abr', 0) or 0) > (audio_format.get('abr', 0) or 0):
                audio_format = fmt
                logger.debug(f"Found better audio format: {fmt.get('format_id')} - {fmt.get('abr')}kbps")

    # Sort video formats by height (resolution) in descending order
    video_formats.sort(key=lambda x: int(x.get('height', 0) or 0), reverse=True)
    logger.debug(f"Final video formats count: {len(video_formats)}")

    return video_formats, audio_format


async def download_video(url: str, format_id: str, state: FSMContext):
    try:
        # Use a secure temporary directory
        temp_dir = "/tmp/youtube_downloads"
        os.makedirs(temp_dir, exist_ok=True)

        # Try to ensure proper permissions
        try:
            os.chmod(temp_dir, 0o777)
        except Exception as e:
            logger.warning(f"Could not set permissions on temp dir: {e}")

        timestamp = int(time.time())
        output_filename = f"video_{timestamp}.mp4"
        output_file = os.path.join(temp_dir, output_filename)

        logger.info(f"Starting download for format {format_id} to {output_file}")

        # Check for ffmpeg
        ffmpeg_exists = False
        try:
            process = await asyncio.create_subprocess_exec(
                'which', 'ffmpeg',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            ffmpeg_exists = (process.returncode == 0)
            logger.info(f"FFMPEG {'is' if ffmpeg_exists else 'is not'} available: {stdout.decode().strip()}")
        except Exception as e:
            logger.error(f"Error checking ffmpeg: {e}")

        # Configure yt-dlp options
        ydl_opts = {
            'outtmpl': output_file,
            'verbose': True,
            'retries': 5,
            'fragment_retries': 5,
            'ignoreerrors': False,
            'continuedl': True,
            'nooverwrites': False,
        }

        # Set format based on ffmpeg availability
        if ffmpeg_exists:
            if format_id.lower() == 'audio':
                ydl_opts['format'] = 'bestaudio'
                ydl_opts['postprocessors'] = [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }]
                output_file = output_file.replace('.mp4', '.mp3')
            else:
                ydl_opts['format'] = format_id
        else:
            logger.warning("FFMPEG not found. Using single format mode.")
            if format_id.lower() == 'audio':
                ydl_opts['format'] = 'bestaudio'
            else:
                ydl_opts['format'] = 'best'

        logger.info(f"Download options: {ydl_opts}")

        # Use a semaphore to limit concurrent downloads
        async with asyncio.Semaphore(2):
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Run the download in a separate thread
                info = await asyncio.to_thread(
                    ydl.extract_info, url, download=True
                )

                if not info:
                    raise Exception("Failed to extract video info")

                logger.info(f"Download complete for {info.get('title')}")

                # Get the actual output path (yt-dlp might modify it)
                actual_output = ydl.prepare_filename(info)

                # Check if file exists with potential different extensions
                if not os.path.exists(actual_output):
                    base_name = os.path.splitext(actual_output)[0]
                    for ext in ['.mp4', '.webm', '.mkv', '.mp3', '.m4a']:
                        test_path = f"{base_name}{ext}"
                        if os.path.exists(test_path):
                            actual_output = test_path
                            logger.info(f"Found file with different extension: {actual_output}")
                            break
                    else:
                        # List all files in directory to help debug
                        logger.error(f"Files in directory: {os.listdir(os.path.dirname(actual_output))}")
                        raise FileNotFoundError(f"Downloaded file not found: {actual_output}")

                # Verify file size
                file_size = os.path.getsize(actual_output)
                logger.info(f"Downloaded file size: {file_size} bytes")

                if file_size == 0:
                    raise Exception("Downloaded file is empty")

                return actual_output, info

    except Exception as e:
        logger.error(f"Download error: {str(e)}")
        logger.exception("Detailed error:")
        raise


async def download_and_send_video(message: Message, url: str, ydl_opts: dict, me, bot: Bot, platform: str,
                                  state: FSMContext):
    """
    Downloads and sends a video from the specified URL using yt-dlp.
    For files larger than 50MB, automatically compresses them.

    Args:
        message: Telegram message object
        url: URL of the video to download
        ydl_opts: Options for yt-dlp
        me: Bot instance information
        bot: Bot instance
        platform: Platform name (YouTube, TikTok, etc.)
        state: FSM context for state management
    """
    progress_msg = await message.answer(f"⏳ Загружаю видео из {platform}...")
    temp_file = None
    compressed_file = None

    try:
        # Create a secure temporary directory
        temp_dir = "/tmp/youtube_downloads"
        os.makedirs(temp_dir, exist_ok=True)

        # Try to set permissions
        try:
            os.chmod(temp_dir, 0o777)
        except Exception as e:
            logger.warning(f"Could not set permissions on temp dir: {e}")

        # Add more robust options to ydl_opts
        final_opts = {
            'format': 'mp4',  # Ensure consistent format
            'merge_output_format': 'mp4',
            'outtmpl': os.path.join(temp_dir, f'temp_{int(time.time())}_{message.from_user.id}.%(ext)s'),
            'noplaylist': True,
            'geo_bypass': True,  # Try to bypass geo-restrictions
            'retries': 3,
            'fragment_retries': 3,
            'verbose': True,
            **ydl_opts  # Add user-provided options
        }

        # Log download attempt
        logger.info(f"Downloading {platform} video from {url} with options: {final_opts}")

        # Create a custom progress hook to update the message
        last_update_time = [time.time()]
        download_start = [time.time()]

        def progress_hook(d):
            if d['status'] == 'downloading':
                current_time = time.time()
                # Update message at most every 3 seconds to avoid flood limits
                if current_time - last_update_time[0] > 3:
                    last_update_time[0] = current_time
                    elapsed = current_time - download_start[0]

                    try:
                        percent = d.get('_percent_str', '0%').strip()
                        speed = d.get('_speed_str', 'N/A')
                        eta = d.get('_eta_str', 'N/A')

                        # Schedule message update asynchronously
                        asyncio.create_task(
                            progress_msg.edit_text(
                                f"⏳ Загружаю видео из {platform}...\n"
                                f"Прогресс: {percent}\n"
                                f"Скорость: {speed}\n"
                                f"Осталось: {eta}\n"
                                f"Прошло времени: {int(elapsed)}с"
                            )
                        )
                    except Exception as e:
                        logger.warning(f"Failed to update progress message: {e}")

            elif d['status'] == 'finished':
                logger.info(f"Download finished: {d['filename']}")

        final_opts['progress_hooks'] = [progress_hook]

        # Use youtube-dl in a separate thread to avoid blocking
        with yt_dlp.YoutubeDL(final_opts) as ydl:
            # Run in thread pool to avoid blocking the event loop
            info_dict = await asyncio.to_thread(
                ydl.extract_info, url, download=True
            )

            if not info_dict:
                await progress_msg.edit_text(f"❌ Не удалось получить информацию о видео из {platform}")
                return

            # Get correct filename
            video_path = ydl.prepare_filename(info_dict)
            logger.info(f"Download completed to path: {video_path}")

            # Handle potential filename format issues
            if not os.path.exists(video_path):
                base_path = video_path.rsplit('.', 1)[0]
                for ext in ['.mp4', '.webm', '.mkv', '.mov']:
                    if os.path.exists(base_path + ext):
                        video_path = base_path + ext
                        logger.info(f"Found file with different extension: {video_path}")
                        break

            # Verify file exists and has content
            if not os.path.exists(video_path):
                raise FileNotFoundError(f"Downloaded file not found at {video_path}")

            file_size = os.path.getsize(video_path)
            if file_size == 0:
                raise ValueError("Downloaded file is empty (0 bytes)")

            logger.info(f"File size: {file_size} bytes")

            # Store path for cleanup
            temp_file = video_path

            # Get title and other metadata
            title = info_dict.get('title', f"{platform} video")
            duration = info_dict.get('duration')
            duration_str = f" ({duration // 60}:{duration % 60:02d})" if duration else ""

            # Check if file is too large for Telegram
            MAX_SIZE = 50 * 1024 * 1024  # 50 MB
            if file_size <= MAX_SIZE:
                # File is small enough, send directly
                await progress_msg.edit_text("📤 Отправляю видео...")

                # Prepare video for sending
                video = FSInputFile(video_path)

                # Send the video
                await bot.send_chat_action(message.chat.id, "upload_video")
                await bot.send_video(
                    chat_id=message.chat.id,
                    video=video,
                    caption=f"📹 {title}{duration_str}\nСкачано через @{me.username}",
                    supports_streaming=True
                )

                # Update state
                await state.set_state(Download.download)

                # Delete progress message
                await progress_msg.delete()
            else:
                # File is too large, compress it
                await progress_msg.edit_text(
                    f"📦 Файл слишком большой ({file_size / (1024 * 1024):.1f} МБ), сжимаю видео...")

                # Create path for compressed file
                compressed_path = os.path.join(temp_dir, f"compressed_{os.path.basename(video_path)}")
                compressed_file = compressed_path

                try:
                    # Get video duration
                    duration_cmd = [
                        'ffprobe',
                        '-v', 'error',
                        '-show_entries', 'format=duration',
                        '-of', 'default=noprint_wrappers=1:nokey=1',
                        video_path
                    ]

                    process = await asyncio.create_subprocess_exec(
                        *duration_cmd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )

                    stdout, stderr = await process.communicate()

                    if process.returncode != 0:
                        logger.error(f"Error getting video duration: {stderr.decode()}")
                        raise Exception("Не удалось определить длительность видео")

                    try:
                        duration = float(stdout.decode().strip())
                    except (ValueError, TypeError):
                        logger.error("Invalid duration value received")
                        duration = 60  # Default to 60 seconds if duration can't be determined

                    # Calculate target bitrate for a ~45MB file (leaving margin)
                    target_size_bits = 45 * 8 * 1024 * 1024
                    target_bitrate = int(target_size_bits / duration) if duration > 0 else 500000

                    # Ensure reasonable bitrate range
                    target_bitrate = max(300000, min(target_bitrate, 2000000))

                    # Compress the video with FFmpeg
                    compress_cmd = [
                        'ffmpeg',
                        '-i', video_path,
                        '-c:v', 'libx264',
                        '-preset', 'fast',  # Use 'fast' preset for speed
                        '-crf', '30',  # Use higher CRF value for smaller file size
                        '-maxrate', f'{target_bitrate}',
                        '-bufsize', f'{target_bitrate * 2}',
                        '-movflags', '+faststart',  # Optimize for web streaming
                        '-c:a', 'aac',
                        '-b:a', '128k',
                        '-y',  # Overwrite output file
                        compressed_path
                    ]

                    await progress_msg.edit_text("📦 Сжимаю видео... Это может занять несколько минут")

                    process = await asyncio.create_subprocess_exec(
                        *compress_cmd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )

                    stdout, stderr = await process.communicate()

                    if process.returncode != 0:
                        error_output = stderr.decode()
                        logger.error(f"Error compressing video: {error_output}")
                        raise Exception("Ошибка сжатия видео. Попробуйте другой формат.")

                    # Check if compression was successful and file exists
                    if not os.path.exists(compressed_path):
                        raise FileNotFoundError("Сжатый файл не найден")

                    # Check final file size
                    compressed_size = os.path.getsize(compressed_path)

                    # If still too big, adjust quality and try again
                    if compressed_size > 50 * 1024 * 1024:
                        await progress_msg.edit_text("📦 Файл всё ещё слишком большой, оптимизирую...")

                        # Try more aggressive compression
                        retry_compress_cmd = [
                            'ffmpeg',
                            '-i', video_path,
                            '-c:v', 'libx264',
                            '-preset', 'medium',
                            '-crf', '35',  # Much higher CRF for smaller size
                            '-vf', 'scale=854:480',  # Reduce resolution to 480p
                            '-c:a', 'aac',
                            '-b:a', '96k',
                            '-y',
                            compressed_path
                        ]

                        process = await asyncio.create_subprocess_exec(
                            *retry_compress_cmd,
                            stdout=asyncio.subprocess.PIPE,
                            stderr=asyncio.subprocess.PIPE
                        )

                        stdout, stderr = await process.communicate()

                        if process.returncode != 0:
                            logger.error(f"Error during second compression attempt: {stderr.decode()}")
                            raise Exception("Не удалось сжать видео до требуемого размера")

                        # Check if second compression was successful
                        if not os.path.exists(compressed_path):
                            raise FileNotFoundError("Сжатый файл не найден после повторной попытки")

                        compressed_size = os.path.getsize(compressed_path)

                        # If still too big after second attempt
                        if compressed_size > 50 * 1024 * 1024:
                            await progress_msg.edit_text(
                                f"⚠️ Не удалось сжать видео до требуемого размера. "
                                f"Исходный размер: {file_size / (1024 * 1024):.1f} МБ, "
                                f"Сжатый размер: {compressed_size / (1024 * 1024):.1f} МБ"
                            )
                            return

                    # Send the compressed video
                    await progress_msg.edit_text("📤 Отправляю сжатое видео...")

                    await bot.send_video(
                        chat_id=message.chat.id,
                        video=FSInputFile(compressed_path),
                        caption=f"📹 {title}{duration_str} (Сжатое видео)\n"
                                f"Исходный размер: {file_size / (1024 * 1024):.1f} МБ\n"
                                f"Скачано через @{me.username}",
                        supports_streaming=True
                    )

                    # Update state
                    await state.set_state(Download.download)

                    # Delete progress message
                    await progress_msg.delete()

                except Exception as e:
                    logger.error(f"Video compression error: {str(e)}")
                    await progress_msg.edit_text(f"❌ Ошибка при обработке видео: {str(e)[:100]}...")

    except Exception as e:
        logger.error(f"Error downloading video from {platform}: {str(e)}")
        logger.exception("Full traceback:")
        error_msg = str(e)

        # Provide user-friendly error message
        if "HTTP Error 429" in error_msg:
            await progress_msg.edit_text(f"❌ Слишком много запросов к {platform}. Пожалуйста, попробуйте позже.")
        elif "HTTP Error 403" in error_msg:
            await progress_msg.edit_text(f"❌ Доступ запрещен. Возможно, видео имеет ограничения.")
        elif "Age verification" in error_msg:
            await progress_msg.edit_text(f"❌ Видео имеет возрастные ограничения.")
        elif "Private video" in error_msg or "not available" in error_msg.lower():
            await progress_msg.edit_text(f"❌ Видео недоступно (приватное или было удалено).")
        elif "ffmpeg" in error_msg.lower():
            await progress_msg.edit_text(f"❌ Ошибка обработки видео. Возможно, проблема с ffmpeg.")
        else:
            await progress_msg.edit_text(f"❌ Не удалось скачать видео из {platform}. Пожалуйста, попробуйте позже.")

    finally:
        # Clean up downloaded files
        if temp_file and os.path.exists(temp_file):
            try:
                os.remove(temp_file)
                logger.info(f"Removed temporary file: {temp_file}")
            except Exception as e:
                logger.error(f"Error removing temporary file: {e}")

        if compressed_file and os.path.exists(compressed_file):
            try:
                os.remove(compressed_file)
                logger.info(f"Removed compressed file: {compressed_file}")
            except Exception as e:
                logger.error(f"Error removing compressed file: {e}")


async def handle_large_video_download(bot, chat_id, video_path, title, username, progress_msg=None):
    """
    Handle video download and sending, with automatic compression for large files

    Args:
        bot: Bot instance
        chat_id: Chat ID to send the video to
        video_path: Path to the video file
        title: Video title for the caption
        username: Bot username for the caption
        progress_msg: Optional message object to update with progress

    Returns:
        bool: True if successful, False otherwise
    """
    file_size = os.path.getsize(video_path)

    # Send directly if under 50MB
    if file_size <= 50 * 1024 * 1024:
        if progress_msg:
            await progress_msg.edit_text("📤 Отправляю видео...")

        await bot.send_video(
            chat_id=chat_id,
            video=FSInputFile(video_path),
            caption=f"📹 {title}\nСкачано через @{username}",
            supports_streaming=True
        )
        return True

    # File is too large, compress it
    if progress_msg:
        await progress_msg.edit_text("📦 Файл слишком большой, сжимаю видео...")

    # Create temp directory if it doesn't exist
    temp_dir = os.path.dirname(video_path)
    compressed_path = os.path.join(temp_dir, f"compressed_{os.path.basename(video_path)}")

    try:
        # Get video duration
        duration_cmd = [
            'ffprobe',
            '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            video_path
        ]

        process = await asyncio.create_subprocess_exec(
            *duration_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            logger.error(f"Error getting video duration: {stderr.decode()}")
            raise Exception("Не удалось определить длительность видео")

        try:
            duration = float(stdout.decode().strip())
        except (ValueError, TypeError):
            logger.error("Invalid duration value received")
            duration = 60  # Default to 60 seconds if duration can't be determined

        # Calculate target bitrate for a ~45MB file (leaving margin)
        target_size_bits = 45 * 8 * 1024 * 1024
        target_bitrate = int(target_size_bits / duration) if duration > 0 else 500000

        # Ensure reasonable bitrate range
        target_bitrate = max(300000, min(target_bitrate, 2000000))

        # Compress the video with FFmpeg
        compress_cmd = [
            'ffmpeg',
            '-i', video_path,
            '-c:v', 'libx264',
            '-preset', 'fast',  # Use 'fast' preset for speed
            '-crf', '30',  # Use higher CRF value for smaller file size
            '-maxrate', f'{target_bitrate}',
            '-bufsize', f'{target_bitrate * 2}',
            '-movflags', '+faststart',  # Optimize for web streaming
            '-c:a', 'aac',
            '-b:a', '128k',
            '-y',  # Overwrite output file
            compressed_path
        ]

        if progress_msg:
            await progress_msg.edit_text("📦 Сжимаю видео... Это может занять несколько минут")

        process = await asyncio.create_subprocess_exec(
            *compress_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            error_output = stderr.decode()
            logger.error(f"Error compressing video: {error_output}")
            raise Exception("Ошибка сжатия видео. Попробуйте другой формат.")

        # Check if compression was successful and file exists
        if not os.path.exists(compressed_path):
            raise FileNotFoundError("Сжатый файл не найден")

        # Check final file size
        compressed_size = os.path.getsize(compressed_path)

        # If still too big, adjust quality and try again
        if compressed_size > 50 * 1024 * 1024:
            if progress_msg:
                await progress_msg.edit_text("📦 Файл всё ещё слишком большой, оптимизирую...")

            # Try more aggressive compression
            retry_compress_cmd = [
                'ffmpeg',
                '-i', video_path,
                '-c:v', 'libx264',
                '-preset', 'medium',
                '-crf', '35',  # Much higher CRF for smaller size
                '-vf', 'scale=854:480',  # Reduce resolution to 480p
                '-c:a', 'aac',
                '-b:a', '96k',
                '-y',
                compressed_path
            ]

            process = await asyncio.create_subprocess_exec(
                *retry_compress_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                logger.error(f"Error during second compression attempt: {stderr.decode()}")
                raise Exception("Не удалось сжать видео до требуемого размера")

            # Check if second compression was successful
            if not os.path.exists(compressed_path):
                raise FileNotFoundError("Сжатый файл не найден после повторной попытки")

            compressed_size = os.path.getsize(compressed_path)

            # If still too big after second attempt
            if compressed_size > 50 * 1024 * 1024:
                if progress_msg:
                    await progress_msg.edit_text("⚠️ Не удалось сжать видео до требуемого размера")
                return False

        # Send the compressed video
        if progress_msg:
            await progress_msg.edit_text("📤 Отправляю сжатое видео...")

        await bot.send_video(
            chat_id=chat_id,
            video=FSInputFile(compressed_path),
            caption=f"📹 {title} (Сжатое видео)\nРазмер исходного файла: {file_size / (1024 * 1024):.1f} МБ\nСкачано через @{username}",
            supports_streaming=True
        )

        return True

    except Exception as e:
        logger.error(f"Video compression error: {str(e)}")
        if progress_msg:
            await progress_msg.edit_text(f"❌ Ошибка при обработке видео: {str(e)[:100]}...")
        return False

    finally:
        # Clean up files
        try:
            if os.path.exists(video_path):
                os.remove(video_path)

            if os.path.exists(compressed_path):
                os.remove(compressed_path)
        except Exception as e:
            logger.error(f"Error cleaning up files: {e}")


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
        await handle_youtube(message, url, me, bot, state)
    else:
        await message.answer("❗ Отправьте ссылку на видео с YouTube, Instagram или TikTok")


async def handle_youtube(message: Message, url: str, me, bot: Bot, state: FSMContext):
    """
    Handle YouTube videos with proper temp directory management
    """
    status_message = await message.answer("⏳ Получаю информацию о видео...")

    try:
        # Clean the URL to improve compatibility
        clean_url = url.split('&')[0] if '&' in url else url
        logger.info(f"Processing YouTube URL: {clean_url}")

        # Create a custom temporary directory with appropriate permissions
        temp_dir = "/tmp/youtube_downloads"
        os.makedirs(temp_dir, exist_ok=True)

        # Make sure directory has proper permissions
        try:
            os.chmod(temp_dir, 0o777)
        except Exception as e:
            logger.warning(f"Could not set permissions on temp dir: {e}")

        # Configure options to extract available formats
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'skip_download': True,
            'youtube_include_dash_manifest': False,
            'noplaylist': True,
        }

        try:
            # Extract video info with all available formats
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info_dict = ydl.extract_info(clean_url, download=False)

                if not info_dict:
                    raise Exception("Failed to extract video info")

                # Extract basic video information
                title = info_dict.get('title', 'YouTube Video')
                uploader = info_dict.get('uploader', 'Unknown')
                duration = info_dict.get('duration', 0)
                minutes = duration // 60
                seconds = duration % 60

                # Get available formats
                formats = info_dict.get('formats', [])

                # Filter and organize video formats
                video_formats = []
                audio_format = None
                seen_resolutions = set()

                # Process all formats to find unique video resolutions and best audio
                for fmt in formats:
                    if not isinstance(fmt, dict):
                        continue

                    vcodec = fmt.get('vcodec', 'none')
                    acodec = fmt.get('acodec', 'none')
                    filesize = fmt.get('filesize', 0)

                    # Only consider video formats with height and valid video codec
                    if vcodec != 'none' and vcodec != 'NA':
                        height = fmt.get('height', 0)
                        if height and height > 0:
                            # Use resolution as key to avoid duplicates
                            resolution_key = f"{height}p"
                            if resolution_key not in seen_resolutions:
                                seen_resolutions.add(resolution_key)

                                # Create format info object
                                format_info = {
                                    'format_id': fmt.get('format_id'),
                                    'height': height,
                                    'extension': fmt.get('ext', 'mp4'),
                                    'filesize': filesize,
                                    'resolution': resolution_key
                                }
                                video_formats.append(format_info)

                    # Find the best audio format
                    if acodec != 'none' and vcodec == 'none':
                        if not audio_format or (fmt.get('abr', 0) or 0) > (audio_format.get('abr', 0) or 0):
                            audio_format = {
                                'format_id': fmt.get('format_id'),
                                'extension': fmt.get('ext', 'mp3'),
                                'abr': fmt.get('abr', 0),
                                'filesize': filesize
                            }

                # Sort video formats by resolution (highest first)
                video_formats.sort(key=lambda x: x['height'], reverse=True)

                # Limit to a reasonable number of choices (max 5 video formats)
                if len(video_formats) > 5:
                    # Keep highest, some middle options, and lowest quality
                    video_formats = [
                        video_formats[0],  # Highest
                        video_formats[len(video_formats) // 4],  # 75% quality
                        video_formats[len(video_formats) // 2],  # 50% quality
                        video_formats[-1]  # Lowest
                    ]

                # Build keyboard with format options
                markup = InlineKeyboardBuilder()

                # Add video format buttons
                for idx, fmt in enumerate(video_formats):
                    resolution = fmt['resolution']
                    size_text = ""
                    if fmt['filesize']:
                        size_mb = fmt['filesize'] / (1024 * 1024)
                        size_text = f" ({size_mb:.1f} MB)"

                    button_text = f"🎬 {resolution}{size_text}"
                    markup.button(
                        text=button_text,
                        callback_data=f"format:{fmt['format_id']}:video:{resolution}:{idx}"
                    )

                # Add audio button at the end
                if audio_format:
                    abr_text = f"{audio_format['abr']}kbps" if audio_format['abr'] else ""
                    size_text = ""
                    if audio_format['filesize']:
                        size_mb = audio_format['filesize'] / (1024 * 1024)
                        size_text = f" ({size_mb:.1f} MB)"

                    markup.button(
                        text=f"🎵 Аудио {abr_text}{size_text}",
                        callback_data=f"format:{audio_format['format_id']}:audio:audio:{len(video_formats)}"
                    )

                # Set single column layout
                markup.adjust(1)

                # Store video information in state
                await state.update_data(
                    url=clean_url,
                    title=title,
                    uploader=uploader,
                    duration=duration,
                    formats=video_formats + ([audio_format] if audio_format else []),
                    temp_dir=temp_dir
                )

                # Display video information and format options
                await status_message.edit_text(
                    f"🎥 <b>{html.escape(title)}</b>\n"
                    f"👤 {html.escape(uploader)}\n"
                    f"⏱ {minutes}:{seconds:02d}\n\n"
                    f"Выберите формат для скачивания:",
                    reply_markup=markup.as_markup(),
                    parse_mode="HTML"
                )

        except Exception as e:
            logger.error(f"Error extracting formats: {e}")

            # Fallback to simple options
            markup = InlineKeyboardBuilder()
            markup.button(text="🎬 Высокое качество", callback_data=f"yt_best:{clean_url}")
            markup.button(text="🎬 Среднее качество", callback_data=f"yt_medium:{clean_url}")
            markup.button(text="🎬 Низкое качество", callback_data=f"yt_low:{clean_url}")
            markup.button(text="🎵 Аудио", callback_data=f"yt_audio:{clean_url}")
            markup.adjust(1)

            # Store temp dir in state for fallback options too
            await state.update_data(temp_dir=temp_dir)

            await status_message.edit_text(
                f"🎥 YouTube видео\n\n"
                f"Не удалось получить список форматов. Выберите вариант загрузки:",
                reply_markup=markup.as_markup()
            )

    except Exception as e:
        logger.error(f"YouTube handler error: {str(e)}")
        await status_message.edit_text("❗ Ошибка при получении информации о видео")


@client_bot_router.callback_query(lambda c: c.data.startswith("dl_"))
async def download_youtube_content(callback: CallbackQuery, state: FSMContext, bot: Bot):
    await callback.answer("⏳ Начинаю загрузку...")

    try:
        # Parse callback data
        parts = callback.data.split(":")
        if len(parts) != 2:
            await callback.message.answer("❌ Некорректный формат запроса")
            return

        mode, url = parts
        is_audio = mode == "dl_audio"

        # Create secure temp directory
        temp_dir = "/tmp/youtube_downloads"
        os.makedirs(temp_dir, exist_exist=True)

        try:
            os.chmod(temp_dir, 0o777)
        except Exception as e:
            logger.warning(f"Could not set permissions on temp dir: {e}")

        # Show progress message
        progress_msg = await callback.message.answer(
            f"⏳ {'Загружаю аудио' if is_audio else 'Загружаю видео'}...\n"
            f"Это может занять несколько минут."
        )

        try:
            # Set format based on mode
            format_id = 'bestaudio' if is_audio else 'bestvideo+bestaudio/best'

            # Configure download options
            ydl_opts = {
                'format': format_id,
                'outtmpl': os.path.join(temp_dir, f'temp_{int(time.time())}_{callback.from_user.id}.%(ext)s'),
                'noplaylist': True,
                'quiet': True,
                'retries': 3,
                'fragment_retries': 3,
            }

            # Add audio post-processing if needed
            if is_audio:
                ydl_opts['postprocessors'] = [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }]

            # Store URL in state
            await state.update_data(url=url)

            # Download the file
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = await asyncio.to_thread(ydl.extract_info, url, download=True)

                if not info:
                    raise Exception("Could not get video info")

                # Get the output path
                video_path = ydl.prepare_filename(info)

                # Check for file extension changes
                if not os.path.exists(video_path):
                    base_path = os.path.splitext(video_path)[0]

                    if is_audio:
                        # Check if mp3 exists
                        if os.path.exists(f"{base_path}.mp3"):
                            video_path = f"{base_path}.mp3"
                    else:
                        # Check common video extensions
                        for ext in ['.mp4', '.webm', '.mkv']:
                            if os.path.exists(f"{base_path}{ext}"):
                                video_path = f"{base_path}{ext}"
                                break

                if not os.path.exists(video_path):
                    raise FileNotFoundError(f"Downloaded file not found: {video_path}")
                title = info.get('title', 'Видео')
                # Get file size
                file_size = os.path.getsize(video_path)
                me = await bot.get_me()

                # Check if file is too large for Telegram
                if file_size > 50 * 1024 * 1024:  # 50 MB limit
                    # Use our compression function for large files
                    success = await handle_large_video_download(
                        bot=bot,
                        chat_id=callback.message.chat.id,
                        video_path=video_path,
                        title=title,
                        username=me.username,
                        progress_msg=progress_msg
                    )

                    if success:
                        # If compression was successful, clean up and finish
                        await state.clear()
                        return
                    else:
                        # If compression failed, show error message
                        await progress_msg.edit_text(
                            "❌ Не удалось обработать видео из-за его большого размера.\n"
                            "Попробуйте выбрать вариант с более низким качеством."
                        )
                        return

                await progress_msg.edit_text("📤 Отправляю файл...")

                # Get bot username
                me = await bot.get_me()

                # Get video title
                title = info.get('title', 'Видео')

                try:
                    # Send file based on type
                    if is_audio:
                        await bot.send_audio(
                            chat_id=callback.message.chat.id,
                            audio=FSInputFile(video_path),
                            caption=f"🎵 {title}\nСкачано через @{me.username}",
                            title=title,
                            performer=info.get('uploader', '')
                        )
                    else:
                        await bot.send_video(
                            chat_id=callback.message.chat.id,
                            video=FSInputFile(video_path),
                            caption=f"🎥 {title}\nСкачано через @{me.username}",
                            supports_streaming=True
                        )
                finally:
                    # Always clean up
                    if os.path.exists(video_path):
                        os.remove(video_path)

                # Clean up and finish
                await progress_msg.delete()
                await state.clear()

        except Exception as e:
            logger.error(f"Download error: {str(e)}")
            await progress_msg.edit_text(f"❌ Ошибка при загрузке: {str(e)[:100]}...")

    except Exception as e:
        logger.error(f"Callback error: {str(e)}")
        await callback.message.answer("❌ Произошла ошибка при обработке запроса")




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
        await handle_youtube(message, url, me, bot, state)
    else:
        await message.answer("❗ Отправьте ссылку на видео с YouTube, Instagram или TikTok")



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



@client_bot_router.callback_query(lambda c: c.data.startswith("yt_"))
async def youtube_format_selected(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """
    Handle YouTube download format selection for fallback options
    """
    await callback.answer("⏳ Начинаю загрузку...")

    try:
        # Parse callback data
        parts = callback.data.split(":")
        if len(parts) != 2:
            await callback.message.answer("❌ Некорректный формат запроса")
            return

        format_type, url = parts

        # Set up temp directory
        temp_dir = "/tmp/youtube_downloads"
        try:
            os.makedirs(temp_dir, exist_ok=True)
            os.chmod(temp_dir, 0o777)
        except Exception as e:
            logger.error(f"Error creating temp directory: {e}")
            temp_dir = "/var/tmp"

        # Show progress message
        progress_msg = await callback.message.answer("⏳ Начинаю загрузку...")

        # Create a unique filename
        timestamp = int(time.time())
        file_id = f"{timestamp}_{callback.from_user.id}"
        output_template = os.path.join(temp_dir, f"{file_id}.%(ext)s")

        # Configure options based on format type
        ydl_opts = {
            'outtmpl': output_template,
            'noplaylist': True,
            'quiet': True,
            'no_warnings': True,
        }

        if format_type == "yt_best":
            ydl_opts['format'] = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
            format_name = "высоком качестве"
            is_audio = False
        elif format_type == "yt_medium":
            ydl_opts['format'] = 'bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]/best'
            format_name = "среднем качестве"
            is_audio = False
        elif format_type == "yt_low":
            ydl_opts['format'] = 'worstvideo[ext=mp4]+worstaudio[ext=m4a]/worst[ext=mp4]/worst'
            format_name = "низком качестве"
            is_audio = False
        elif format_type == "yt_audio":
            ydl_opts['format'] = 'bestaudio[ext=m4a]/bestaudio'
            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }]
            format_name = "аудио формате"
            is_audio = True
        else:
            await callback.message.answer("❌ Неизвестный формат")
            return

        await progress_msg.edit_text(f"⏳ Загружаю в {format_name}...")

        try:
            # Download the file
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = await asyncio.to_thread(ydl.extract_info, url, download=True)

                if not info:
                    raise Exception("Could not get video info")

                # Get the output path
                video_path = ydl.prepare_filename(info)
                title = info.get('title', 'Video')

                # Check for file extension changes
                if not os.path.exists(video_path):
                    base_path = os.path.splitext(video_path)[0]

                    if is_audio:
                        # Check if mp3 exists
                        if os.path.exists(f"{base_path}.mp3"):
                            video_path = f"{base_path}.mp3"
                    else:
                        # Check common video extensions
                        for ext in ['.mp4', '.webm', '.mkv']:
                            if os.path.exists(f"{base_path}{ext}"):
                                video_path = f"{base_path}{ext}"
                                break

                if not os.path.exists(video_path):
                    logger.error(f"Files in temp dir: {os.listdir(temp_dir)}")
                    raise FileNotFoundError(f"Downloaded file not found at {video_path}")

                # Get file size
                file_size = os.path.getsize(video_path)
                logger.info(f"Downloaded file: {video_path}, size: {file_size / 1024 / 1024:.2f} MB")
                me = await bot.get_me()
                # Check if file is too large
                if file_size > 50 * 1024 * 1024:  # 50 MB limit
                    # Use our compression function for large files
                    success = await handle_large_video_download(
                        bot=bot,
                        chat_id=callback.message.chat.id,
                        video_path=video_path,
                        title=title,
                        username=me.username,
                        progress_msg=progress_msg
                    )

                    if success:
                        # If compression was successful, clean up and finish
                        await state.clear()
                        return
                    else:
                        # If compression failed, show error message
                        await progress_msg.edit_text(
                            "❌ Не удалось обработать видео из-за его большого размера.\n"
                            "Попробуйте выбрать вариант с более низким качеством."
                        )
                        return

                await progress_msg.edit_text("📤 Отправляю файл...")

                # Get bot name
                me = await bot.get_me()

                try:
                    # Send file based on type
                    if is_audio:
                        await bot.send_audio(
                            chat_id=callback.message.chat.id,
                            audio=FSInputFile(video_path),
                            caption=f"🎵 {title}\nСкачано через @{me.username}",
                            title=title
                        )
                    else:
                        await bot.send_video(
                            chat_id=callback.message.chat.id,
                            video=FSInputFile(video_path),
                            caption=f"🎥 {title}\nСкачано через @{me.username}",
                            supports_streaming=True
                        )
                finally:
                    # Clean up
                    if os.path.exists(video_path):
                        try:
                            os.remove(video_path)
                        except Exception as e:
                            logger.error(f"Error removing file: {e}")

                # Delete progress message and clear state
                await progress_msg.delete()
                await state.clear()

        except Exception as e:
            logger.error(f"Download error: {str(e)}")
            await progress_msg.edit_text(f"❌ Ошибка при загрузке: {str(e)[:100]}...")

    except Exception as e:
        logger.error(f"Format selection error: {str(e)}")
        await callback.message.answer("❌ Ошибка при обработке запроса")


@client_bot_router.callback_query(FormatCallback.filter())
async def process_format_selection(callback: CallbackQuery, callback_data: FormatCallback, state: FSMContext, bot: Bot):
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.answer("⏳ Начинаю загрузку...")

        data = await state.get_data()
        url = data.get('url')

        if not url:
            # Try to get URL from previous state data or extract from callback
            try:
                format_parts = callback_data.data.split(':')
                if len(format_parts) > 1:
                    url = format_parts[1]
            except:
                pass

            if not url:
                await callback.message.answer("❌ Ошибка: данные о видео не найдены")
                return

        # Create a temporary directory with proper permissions
        temp_dir = "/tmp/youtube_downloads"
        try:
            os.makedirs(temp_dir, exist_ok=True)
            # Try to ensure proper permissions
            os.chmod(temp_dir, 0o777)
        except Exception as e:
            logger.error(f"Error creating temp directory: {e}")
            # Fallback to another location
            temp_dir = "/var/tmp"

        format_id = callback_data.format_id
        is_audio = callback_data.type == 'audio'
        quality = callback_data.quality

        progress_msg = await callback.message.answer(
            f"⏳ Загружаю {'аудио' if is_audio else 'видео'}\n"
            f"{'🎵 Аудио формат' if is_audio else f'🎬 Качество: {quality}'}"
        )

        try:
            # Create a unique filename in the temp directory
            timestamp = int(time.time())
            file_id = f"{timestamp}_{callback.from_user.id}"
            output_template = os.path.join(temp_dir, f"{file_id}.%(ext)s")

            # Configure download options
            ydl_opts = {
                'format': format_id,
                'outtmpl': output_template,
                'noplaylist': True,
                'quiet': True,
                'no_warnings': True,
            }

            # Add audio post-processing if needed
            if is_audio:
                ydl_opts['postprocessors'] = [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }]

            # Download the file
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = await asyncio.to_thread(ydl.extract_info, url, download=True)

                if not info:
                    raise Exception("Could not get video info")

                # Get the output path
                video_path = ydl.prepare_filename(info)

                # Check for file extension changes
                if not os.path.exists(video_path):
                    base_path = os.path.splitext(video_path)[0]

                    if is_audio:
                        # Check if mp3 exists
                        if os.path.exists(f"{base_path}.mp3"):
                            video_path = f"{base_path}.mp3"
                    else:
                        # Check common video extensions
                        for ext in ['.mp4', '.webm', '.mkv']:
                            if os.path.exists(f"{base_path}{ext}"):
                                video_path = f"{base_path}{ext}"
                                break

                if not os.path.exists(video_path):
                    # List directory contents for debugging
                    logger.error(f"Files in temp dir: {os.listdir(temp_dir)}")
                    raise FileNotFoundError(f"Downloaded file not found: {video_path}")
                me = await bot.get_me()
                # Get file size for logging
                file_size = os.path.getsize(video_path)
                logger.info(f"Downloaded file: {video_path}, size: {file_size / 1024 / 1024:.2f} MB")
                title = info.get('title', 'YouTube Video')
                # Check if file is too large
                if file_size > 50 * 1024 * 1024:  # 50 MB limit
                    # Use our compression function for large files
                    success = await handle_large_video_download(
                        bot=bot,
                        chat_id=callback.message.chat.id,
                        video_path=video_path,
                        title=title,
                        username=me.username,
                        progress_msg=progress_msg
                    )

                    if success:
                        # If compression was successful, clean up and finish
                        await state.clear()
                        return
                    else:
                        # If compression failed, show error message
                        await progress_msg.edit_text(
                            "❌ Не удалось обработать видео из-за его большого размера.\n"
                            "Попробуйте выбрать вариант с более низким качеством."
                        )
                        return

                await progress_msg.edit_text("📤 Отправляю файл...")

                me = await bot.get_me()

                try:
                    title = info.get('title', 'YouTube Video')

                    # Send based on type
                    if is_audio:
                        # Send as audio
                        await bot.send_audio(
                            chat_id=callback.message.chat.id,
                            audio=FSInputFile(video_path),
                            caption=f"🎵 {title}\nСкачано через @{me.username}",
                            title=title
                        )
                    else:
                        # Send as video
                        await bot.send_video(
                            chat_id=callback.message.chat.id,
                            video=FSInputFile(video_path),
                            caption=f"🎥 {title} ({quality})\nСкачано через @{me.username}",
                            supports_streaming=True
                        )
                finally:
                    # Always clean up
                    if os.path.exists(video_path):
                        try:
                            os.remove(video_path)
                        except Exception as e:
                            logger.error(f"Error removing temp file: {e}")

                # Clean up and finish
                await progress_msg.delete()
                await state.clear()

        except Exception as e:
            logger.error(f"Download error: {str(e)}")
            await progress_msg.edit_text(f"❌ Ошибка при загрузке: {str(e)[:100]}...")

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
                            # await state.set_state(Download.download)
                        else:
                            await bot.send_photo(
                                chat_id=message.chat.id,
                                photo=info['url'],
                                caption=f"🖼 Instagram фото\nСкачано через @{me.username}"
                            )
                            # await state.set_state(Download.download)

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
                                        # await state.set_state(Download.download)
                                    else:
                                        await bot.send_photo(
                                            chat_id=message.chat.id,
                                            photo=FSInputFile(media_path),
                                            caption=f"🖼 Instagram фото\nСкачано через @{me.username}"
                                        )
                                        # await state.set_state(Download.download)
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







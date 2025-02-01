import asyncio
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
from modul.models import UserTG, AdminInfo
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
    """Mavjud bo'lmagan kanalni bazadan o'chirish"""
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

# Callback handler
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
        await change_price(new_reward)
        await message.answer(
            f"Награда за реферала успешно изменена на {new_reward:.2f} руб.",
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
        file_path = await convert_to_excel(user_id)
        document = FSInputFile(file_path, filename=os.path.basename(file_path))
        await call.message.answer_document(document)
        os.remove(file_path)
    except Exception as e:
        await call.message.answer(f"🚫 Произошла ошибка при создании файла: {e}")


@client_bot_router.callback_query(F.data == 'admin_get_stats', AdminFilter(), StateFilter('*'))
async def admin_get_stats(call: CallbackQuery):
    try:
        bot_token = call.bot.token
        print(f"Bot token: {bot_token}")

        # Bot modelini olish
        bot_db = await get_bot_by_token(bot_token)
        print(f"Bot DB object: {bot_db}")

        if bot_db:
            total = await users_count(bot_db)
            print(f"Users count: {total}")

            new_text = f'<b>Количество пользователей в боте:</b> {total}'

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
    await call.message.edit_text('Отправьте id канала\n\nУбедитесь в том, что бот является администратором в канале',
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

    price = await get_actual_price()
    min_withdraw = await get_actual_min_amount()

    await message.bot.send_message(
        message.from_user.id,
        f"👥 Приглашай друзей и зарабатывай! За \nкаждого друга ты получишь {price}₽.\n\n"
        f"🔗 Ваша ссылка для приглашений:\n{link}\n\n"
        f"💰 Минимальная сумма для вывода: {min_withdraw}₽",
        reply_markup=await main_menu_bt2()
    )


async def start_kino_bot(message: Message, state: FSMContext, bot: Bot):
    try:
        bot_db = await shortcuts.get_bot(bot)
        if shortcuts.have_one_module(bot_db, "kino"):
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



async def start(message: Message, state: FSMContext, bot: Bot):
    bot_db = await shortcuts.get_bot(bot)
    uid = message.from_user.id
    text = "Добро пожаловать, {hello}".format(hello=html.quote(message.from_user.full_name))
    kwargs = {}

    sub_status = await check_subs(message.from_user.id, bot)

    if not sub_status:
        kb = await get_subs_kb(bot)
        await message.answer(
            '<b>Чтобы воспользоваться ботом, необходимо подписаться на каналы:</b>',
            reply_markup=kb,
            parse_mode="HTML"
        )
        return

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
        referral = message.text[7:] if message.text and len(message.text) > 7 else None
        logger.info(f"Processing start command with referral: {referral}")

        if referral:
            await start_ref(message, bot=bot, referral=referral)
        else:
            await start_ref(message, bot=bot)
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

@client_bot_router.message(CommandStart(), NonChatGptFilter())
async def start_on(message: Message, state: FSMContext, bot: Bot, command: CommandObject):
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

                    try:
                        @sync_to_async
                        @transaction.atomic
                        def update_referral():
                            try:
                                user_tg = UserTG.objects.select_for_update().get(uid=inviter_id)
                                admin_info = AdminInfo.objects.first()

                                if not admin_info:
                                    raise ValueError("AdminInfo is not configured in the database.")

                                user_tg.refs += 1
                                user_tg.balance += float(admin_info.price or 10.0)
                                user_tg.save()
                                logger.info(f"Referral updated successfully for user {inviter_id}")
                                return True
                            except UserTG.DoesNotExist:
                                logger.error(f"Inviter with ID {inviter_id} does not exist.")
                                return False
                            except Exception as ex:
                                logger.error(f"Unexpected error during referral update: {ex}")
                                raise

                        referral_updated = await update_referral()
                        if referral_updated:
                            logger.info(f"Referral updated successfully for {inviter_id}")
                        else:
                            logger.warning(f"Failed to update referral for {inviter_id}")

                    except Exception as e:
                        logger.error(f"Error updating referral stats: {e}")
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

                        await download_and_send_video(message, url, ydl_opts, me, bot, "TikTok")
                else:
                    await message.answer("❌ Не удалось получить ссылку на видео")

            except Exception as e:
                logger.error(f"TikTok processing error: {e}")
                await message.answer("❌ Ошибка при скачивании из TikTok")

    except Exception as e:
        logger.error(f"TikTok handler error: {e}")
        await message.answer("❌ Ошибка при обработке TikTok видео")
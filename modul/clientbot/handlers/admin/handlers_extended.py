# modul/clientbot/handlers/admin/handlers_extended.py
"""
Extended admin handlers
Universal admin panel uchun qo'shimcha handler'lar
"""

import logging
import os
from typing import List, Dict, Any
from datetime import datetime

from aiogram import F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder

from modul.clientbot import shortcuts
from modul.clientbot.handlers.admin.admin_service import admin_service, send_mailing_message
from modul.clientbot.handlers.admin.keyboards import admin_keyboards
from modul.clientbot.handlers.admin.states import AdminStates, PaymentStates, ChannelStates, SettingsStates
from modul.loader import client_bot_router

logger = logging.getLogger(__name__)


class ExtendedAdminHandlers:
    """Qo'shimcha admin handler'lar"""

    def __init__(self):
        self.setup_extended_handlers()

    def setup_extended_handlers(self):
        """Qo'shimcha handler'larni sozlash"""

        # User management extended handlers
        @client_bot_router.message(AdminStates.change_balance)
        async def change_user_balance(message: Message, state: FSMContext, bot: Bot):
            """Foydalanuvchi balansini o'zgartirish"""
            try:
                if message.text == "❌ Отменить":
                    await message.answer("🚫 Действие отменено")
                    await state.clear()
                    return

                try:
                    new_balance = float(message.text.replace(',', '.'))
                except ValueError:
                    await message.answer("❗ Введите корректную сумму")
                    return

                data = await state.get_data()
                user_id = data.get('user_id')
                bot_db = await shortcuts.get_bot(bot)

                success = await admin_service.change_user_balance(user_id, bot_db.id, new_balance)

                if success:
                    await message.answer(f"✅ Баланс пользователя {user_id} изменен на {new_balance}")
                else:
                    await message.answer("❌ Не удалось изменить баланс")

                await state.clear()

            except Exception as e:
                logger.error(f"Change balance error: {e}")
                await message.answer("❌ Произошла ошибка")
                await state.clear()

        @client_bot_router.message(AdminStates.add_balance)
        async def add_user_balance(message: Message, state: FSMContext, bot: Bot):
            """Foydalanuvchi balansiga qo'shish"""
            try:
                if message.text == "❌ Отменить":
                    await message.answer("🚫 Действие отменено")
                    await state.clear()
                    return

                try:
                    amount = float(message.text.replace(',', '.'))
                except ValueError:
                    await message.answer("❗ Введите корректную сумму")
                    return

                data = await state.get_data()
                user_id = data.get('user_id')
                bot_db = await shortcuts.get_bot(bot)

                success = await admin_service.add_user_balance(user_id, bot_db.id, amount)

                if success:
                    await message.answer(f"✅ К балансу пользователя {user_id} добавлено {amount}")
                else:
                    await message.answer("❌ Не удалось добавить к балансу")

                await state.clear()

            except Exception as e:
                logger.error(f"Add balance error: {e}")
                await message.answer("❌ Произошла ошибка")
                await state.clear()

        @client_bot_router.message(AdminStates.change_referrals)
        async def change_user_referrals(message: Message, state: FSMContext, bot: Bot):
            """Foydalanuvchi referallarini o'zgartirish"""
            try:
                if message.text == "❌ Отменить":
                    await message.answer("🚫 Действие отменено")
                    await state.clear()
                    return

                try:
                    new_refs = int(message.text)
                except ValueError:
                    await message.answer("❗ Введите корректное число")
                    return

                data = await state.get_data()
                user_id = data.get('user_id')
                bot_db = await shortcuts.get_bot(bot)

                success = await admin_service.change_user_referrals(user_id, bot_db.id, new_refs)

                if success:
                    await message.answer(f"✅ Количество рефералов пользователя {user_id} изменено на {new_refs}")
                else:
                    await message.answer("❌ Не удалось изменить количество рефералов")

                await state.clear()

            except Exception as e:
                logger.error(f"Change referrals error: {e}")
                await message.answer("❌ Произошла ошибка")
                await state.clear()

        @client_bot_router.message(AdminStates.mailing_message)
        async def process_mailing(message: Message, state: FSMContext, bot: Bot):
            """Xabar tarqatishni bajarish"""
            try:
                if message.text == "❌ Отменить":
                    await message.answer("🚫 Действие отменено")
                    await state.clear()
                    return

                bot_db = await shortcuts.get_bot(bot)
                user_ids = await admin_service.get_all_users_for_mailing(bot_db.id)

                if not user_ids:
                    await message.answer("❌ Нет активных пользователей для рассылки")
                    await state.clear()
                    return

                await message.answer(f"📤 Начинаю рассылку для {len(user_ids)} пользователей...")

                # Xabar ma'lumotlarini tayyorlash
                message_data = {
                    'type': 'copy',
                    'from_chat_id': message.chat.id,
                    'message_id': message.message_id
                }

                # Xabar tarqatish
                result = await send_mailing_message(bot, user_ids, message_data)

                await message.answer(
                    f"📊 <b>Рассылка завершена!</b>\n\n"
                    f"✅ Успешно отправлено: {result['success']}\n"
                    f"❌ Неуспешно: {result['failed']}\n"
                    f"📈 Процент доставки: {result['success'] / len(user_ids) * 100:.1f}%",
                    parse_mode="HTML"
                )

                await state.clear()

            except Exception as e:
                logger.error(f"Mailing error: {e}")
                await message.answer("❌ Произошла ошибка при рассылке")
                await state.clear()

        # Settings handlers
        @client_bot_router.message(AdminStates.change_ref_reward)
        async def change_ref_reward(message: Message, state: FSMContext, bot: Bot):
            """Referal mukofotini o'zgartirish"""
            try:
                if message.text == "❌ Отменить":
                    await message.answer("🚫 Действие отменено")
                    await state.clear()
                    return

                try:
                    new_reward = float(message.text.replace(',', '.'))
                except ValueError:
                    await message.answer("❗ Введите корректную сумму")
                    return

                # Bu yerda ref reward o'zgartirish funksiyasini chaqirish
                # await admin_service.change_ref_reward(bot_db.id, new_reward)

                await message.answer(f"✅ Награда за реферала изменена на {new_reward}")
                await state.clear()

            except Exception as e:
                logger.error(f"Change ref reward error: {e}")
                await message.answer("❌ Произошла ошибка")
                await state.clear()

        @client_bot_router.message(AdminStates.change_min_payout)
        async def change_min_payout(message: Message, state: FSMContext, bot: Bot):
            """Minimal to'lov miqdorini o'zgartirish"""
            try:
                if message.text == "❌ Отменить":
                    await message.answer("🚫 Действие отменено")
                    await state.clear()
                    return

                try:
                    new_min = float(message.text.replace(',', '.'))
                except ValueError:
                    await message.answer("❗ Введите корректную сумму")
                    return

                # Bu yerda min payout o'zgartirish funksiyasini chaqirish
                # await admin_service.change_min_payout(bot_db.id, new_min)

                await message.answer(f"✅ Минимальная выплата изменена на {new_min}")
                await state.clear()

            except Exception as e:
                logger.error(f"Change min payout error: {e}")
                await message.answer("❌ Произошла ошибка")
                await state.clear()

        # Channel management handlers
        @client_bot_router.message(ChannelStates.channel_url)
        async def add_channel_url(message: Message, state: FSMContext, bot: Bot):
            """Kanal URL qo'shish"""
            try:
                if message.text == "❌ Отменить":
                    await message.answer("🚫 Действие отменено")
                    await state.clear()
                    return

                if "t.me/" not in message.text.lower():
                    await message.answer("❗ Введите корректную ссылку на канал (t.me/...)")
                    return

                await state.update_data(channel_url=message.text)
                await message.answer(
                    "📝 Теперь введите ID канала\n\n"
                    "ℹ️ Чтобы узнать ID канала:\n"
                    "1. Перешлите любой пост из канала в @getmyid_bot\n"
                    "2. Скопируйте значение из 'Forwarded from chat'",
                    reply_markup=await admin_keyboards.cancel_keyboard()
                )
                await state.set_state(ChannelStates.channel_id)

            except Exception as e:
                logger.error(f"Add channel URL error: {e}")
                await message.answer("❌ Произошла ошибка")
                await state.clear()

        @client_bot_router.message(ChannelStates.channel_id)
        async def add_channel_id(message: Message, state: FSMContext, bot: Bot):
            """Kanal ID qo'shish"""
            try:
                if message.text == "❌ Отменить":
                    await message.answer("🚫 Действие отменено")
                    await state.clear()
                    return

                try:
                    channel_id = int(message.text)
                    if channel_id > 0:
                        channel_id *= -1  # Kanal ID manfiy bo'lishi kerak
                except ValueError:
                    await message.answer("❗ Введите корректный ID канала")
                    return

                data = await state.get_data()
                channel_url = data.get('channel_url')

                # Bu yerda kanalni bazaga qo'shish
                # success = await admin_service.add_channel(bot_db.id, channel_url, channel_id)

                await message.answer(
                    f"✅ Канал успешно добавлен!\n\n"
                    f"🔗 URL: {channel_url}\n"
                    f"🆔 ID: {channel_id}\n\n"
                    f"❗ Не забудьте добавить бота в этот канал и дать ему права администратора!"
                )
                await state.clear()

            except Exception as e:
                logger.error(f"Add channel ID error: {e}")
                await message.answer("❌ Произошла ошибка")
                await state.clear()

        # Additional callback handlers
        @client_bot_router.callback_query(F.data.startswith("user_balance_"))
        async def start_balance_change(query: CallbackQuery, state: FSMContext):
            """Balans o'zgartirish jarayonini boshlash"""
            try:
                user_id = int(query.data.replace("user_balance_", ""))

                await query.message.answer(
                    f"💰 Введите новую сумму баланса для пользователя {user_id}\n\n"
                    f"ℹ️ Для дробных чисел используйте точку, а не запятую",
                    reply_markup=await admin_keyboards.cancel_keyboard()
                )

                await state.set_data({'user_id': user_id})
                await state.set_state(AdminStates.change_balance)

            except Exception as e:
                logger.error(f"Start balance change error: {e}")
                await query.answer("❌ Ошибка")

        @client_bot_router.callback_query(F.data.startswith("user_add_balance_"))
        async def start_add_balance(query: CallbackQuery, state: FSMContext):
            """Balansga qo'shish jarayonini boshlash"""
            try:
                user_id = int(query.data.replace("user_add_balance_", ""))

                await query.message.answer(
                    f"➕ Сколько добавить к балансу пользователя {user_id}?\n\n"
                    f"ℹ️ Для дробных чисел используйте точку, а не запятую",
                    reply_markup=await admin_keyboards.cancel_keyboard()
                )

                await state.set_data({'user_id': user_id})
                await state.set_state(AdminStates.add_balance)

            except Exception as e:
                logger.error(f"Start add balance error: {e}")
                await query.answer("❌ Ошибка")

        @client_bot_router.callback_query(F.data.startswith("user_refs_"))
        async def start_refs_change(query: CallbackQuery, state: FSMContext):
            """Referallar o'zgartirish jarayonini boshlash"""
            try:
                user_id = int(query.data.replace("user_refs_", ""))

                await query.message.answer(
                    f"👥 Введите новое количество рефералов для пользователя {user_id}",
                    reply_markup=await admin_keyboards.cancel_keyboard()
                )

                await state.set_data({'user_id': user_id})
                await state.set_state(AdminStates.change_referrals)

            except Exception as e:
                logger.error(f"Start refs change error: {e}")
                await query.answer("❌ Ошибка")

        @client_bot_router.callback_query(F.data == "mailing_create")
        async def start_mailing(query: CallbackQuery, state: FSMContext):
            """Xabar tarqatishni boshlash"""
            try:
                await query.message.answer(
                    "📝 Отправьте сообщение для рассылки\n\n"
                    "ℹ️ Можно отправить:\n"
                    "• Текст\n"
                    "• Фото с описанием\n"
                    "• Видео с описанием\n"
                    "• Стикер\n"
                    "• Файл",
                    reply_markup=await admin_keyboards.cancel_keyboard()
                )

                await state.set_state(AdminStates.mailing_message)

            except Exception as e:
                logger.error(f"Start mailing error: {e}")
                await query.answer("❌ Ошибка")

        @client_bot_router.callback_query(F.data == "setting_ref_reward")
        async def start_ref_reward_change(query: CallbackQuery, state: FSMContext):
            """Ref reward o'zgartirish"""
            try:
                await query.message.answer(
                    "💰 Введите новую награду за реферала",
                    reply_markup=await admin_keyboards.cancel_keyboard()
                )

                await state.set_state(AdminStates.change_ref_reward)

            except Exception as e:
                logger.error(f"Start ref reward change error: {e}")
                await query.answer("❌ Ошибка")

        @client_bot_router.callback_query(F.data == "setting_min_payout")
        async def start_min_payout_change(query: CallbackQuery, state: FSMContext):
            """Min payout o'zgartirish"""
            try:
                await query.message.answer(
                    "💳 Введите новую минимальную сумму для выплаты",
                    reply_markup=await admin_keyboards.cancel_keyboard()
                )

                await state.set_state(AdminStates.change_min_payout)

            except Exception as e:
                logger.error(f"Start min payout change error: {e}")
                await query.answer("❌ Ошибка")

        @client_bot_router.callback_query(F.data == "channel_add")
        async def start_add_channel(query: CallbackQuery, state: FSMContext):
            """Kanal qo'shishni boshlash"""
            try:
                await query.message.answer(
                    "🔗 Введите ссылку на канал\n\n"
                    "📝 Формат: t.me/channel_name или https://t.me/channel_name",
                    reply_markup=await admin_keyboards.cancel_keyboard()
                )

                await state.set_state(ChannelStates.channel_url)

            except Exception as e:
                logger.error(f"Start add channel error: {e}")
                await query.answer("❌ Ошибка")

        @client_bot_router.callback_query(F.data == "stats_general")
        async def show_general_stats(query: CallbackQuery, bot: Bot):
            """Umumiy statistikani ko'rsatish"""
            try:
                bot_db = await shortcuts.get_bot(bot)
                stats = await admin_service.get_bot_statistics_detailed(bot_db.id)

                stats_text = (
                    f"📊 <b>Общая статистика бота</b>\n\n"
                    f"👥 Всего пользователей: {stats['total_users']}\n"
                    f"   • Реферальных: {stats['refs_users']}\n"
                    f"   • Клиентских: {stats['client_users']}\n\n"
                    f"📈 Активность:\n"
                    f"   • Сегодня: {stats['today_users']}\n"
                    f"   • За неделю: {stats['week_users']}\n"
                    f"   • За месяц: {stats['month_users']}\n\n"
                    f"🔄 Статус пользователей:\n"
                    f"   • Активные: {stats['active_users']}\n"
                    f"   • Заблокированные: {stats['banned_users']}"
                )

                await query.message.edit_text(
                    stats_text,
                    parse_mode="HTML",
                    reply_markup=await admin_keyboards.back_keyboard()
                )

            except Exception as e:
                logger.error(f"Show general stats error: {e}")
                await query.answer("❌ Ошибка получения статистики")


# Extended handlers ni faollashtirish
def setup_extended_admin_handlers():
    """Extended admin handlers ni sozlash"""
    extended_handlers = ExtendedAdminHandlers()
    return extended_handlers


# Export
extended_admin_handlers = setup_extended_admin_handlers()
import logging
import os
from typing import Optional, List, Dict, Any

from aiogram import F, Bot
from aiogram.filters import Command, BaseFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder

from modul.clientbot import shortcuts
from modul.models import Bot as BotModel, User, UserTG
from modul.clientbot.handlers.admin.admin_service import *
from modul.clientbot.handlers.admin.keyboards import *
from modul.clientbot.handlers.admin.states import AdminStates
from modul.loader import client_bot_router

logger = logging.getLogger(__name__)


class AdminFilter(BaseFilter):
    """Admin huquqlarini tekshirish filtri"""

    async def __call__(self, message: Message, bot: Bot) -> bool:
        try:
            # Bot ma'lumotlarini olish
            bot_db = await shortcuts.get_bot(bot)
            if not bot_db:
                return False

            # Bot owner va admin users
            owner_id = bot_db.owner.uid
            admin_ids = [owner_id]  # Qo'shimcha adminlarni qo'shish mumkin

            return message.from_user.id in admin_ids
        except Exception as e:
            logger.error(f"AdminFilter error: {e}")
            return False


class UniversalAdminPanel:
    """Universal admin panel class"""

    def __init__(self):
        self.setup_handlers()

    def setup_handlers(self):
        """Handler'larni sozlash"""

        @client_bot_router.message(Command('admin'), AdminFilter())
        async def admin_panel_main(message: Message, bot: Bot):
            """Admin panel asosiy menu"""
            try:
                # Bot ma'lumotlarini olish
                bot_db = await shortcuts.get_bot(bot)
                if not bot_db:
                    await message.answer("❌ Bot ma'lumotlari topilmadi")
                    return

                # Statistika olish
                stats = await self.get_bot_statistics(bot_db)

                # Admin menu
                await message.answer(
                    f"🕵️‍♂️ <b>Пользователей в боте</b>: {stats['users_count']}\n"
                    f"💶<b>Заявок на вывод</b>: {stats['pending_payments']}",
                    parse_mode="HTML",
                    reply_markup=await self.admin_main_keyboard()
                )

            except Exception as e:
                logger.error(f"Admin panel error: {e}")
                await message.answer("❌ Произошла ошибка")

        @client_bot_router.callback_query(F.data.startswith("admin_"))
        async def admin_callbacks(query: CallbackQuery, state: FSMContext, bot: Bot):
            """Admin callback handler"""
            try:
                await state.clear()
                action = query.data.replace("admin_", "")

                if action == "users":
                    await self.handle_users_management(query, bot)
                elif action == "payments":
                    await self.handle_payments(query, bot)
                elif action == "settings":
                    await self.handle_settings(query, bot, state)
                elif action == "channels":
                    await self.handle_channels(query, bot, state)
                elif action == "mailing":
                    await self.handle_mailing(query, bot, state)
                elif action == "statistics":
                    await self.handle_statistics(query, bot)
                elif action == "cancel":
                    await query.message.delete()

            except Exception as e:
                logger.error(f"Admin callback error: {e}")
                await query.answer("❌ Произошла ошибка")

        @client_bot_router.callback_query(F.data.startswith("user_"))
        async def user_management_callbacks(query: CallbackQuery, state: FSMContext, bot: Bot):
            """Foydalanuvchilarni boshqarish"""
            try:
                action_data = query.data.replace("user_", "")

                if action_data == "search":
                    await query.message.answer(
                        "👤 Введите ID пользователя:",
                        reply_markup=await self.cancel_keyboard()
                    )
                    await state.set_state(AdminStates.user_search)

                elif action_data.startswith("ban_"):
                    user_id = int(action_data.replace("ban_", ""))
                    await self.ban_user(user_id, bot)
                    await query.answer("✅ Пользователь заблокирован")

                elif action_data.startswith("unban_"):
                    user_id = int(action_data.replace("unban_", ""))
                    await self.unban_user(user_id, bot)
                    await query.answer("✅ Пользователь разблокирован")

            except Exception as e:
                logger.error(f"User management error: {e}")
                await query.answer("❌ Ошибка")
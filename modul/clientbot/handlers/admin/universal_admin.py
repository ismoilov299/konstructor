# modul/clientbot/handlers/admin/universal_admin.py
"""
Universal admin panel for all bot types
Har qanday bot turi uchun universal admin panel
"""

import logging
import os
from typing import Optional, List, Dict, Any

from aiogram import F, Bot
from aiogram.filters import Command, BaseFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.state import State, StatesGroup

from modul.clientbot import shortcuts
from modul.models import Bot as BotModel, User, UserTG
from modul.loader import client_bot_router
from asgiref.sync import sync_to_async

logger = logging.getLogger(__name__)


class AdminFilter(BaseFilter):
    """Admin huquqlarini tekshirish filtri"""

    async def __call__(self, message: Message, bot: Bot) -> bool:
        try:
            bot_db = await shortcuts.get_bot(bot)
            if not bot_db:
                return False

            owner_id = bot_db.owner.uid
            return message.from_user.id == owner_id
        except Exception as e:
            logger.error(f"AdminFilter error: {e}")
            return False


class AdminStates(StatesGroup):
    """Admin panel states"""
    user_search = State()
    change_balance = State()
    add_balance = State()
    change_referrals = State()
    mailing_message = State()


# MAIN ADMIN COMMAND
def admin_panel():
    """Admin panel handler"""

    @client_bot_router.message(Command('admin'), AdminFilter())
    async def admin_panel_main(message: Message, bot: Bot):
        try:
            bot_db = await shortcuts.get_bot(bot)
            if not bot_db:
                await message.answer("❌ Bot ma'lumotlari topilmadi")
                return

            # Statistika olish
            users_count = await get_bot_users_count(bot_db.id)
            pending_payments = 0  # Placeholder

            # Keyboard
            builder = InlineKeyboardBuilder()
            builder.button(text="👥 Управление пользователями", callback_data="admin_users")
            builder.button(text="💰 Заявки на вывод", callback_data="admin_payments")
            builder.button(text="⚙️ Настройки бота", callback_data="admin_settings")
            builder.button(text="📢 Обязательные подписки", callback_data="admin_channels")
            builder.button(text="📤 Рассылка", callback_data="admin_mailing")
            builder.button(text="📊 Статистика", callback_data="admin_statistics")
            builder.button(text="❌ Закрыть", callback_data="admin_cancel")
            builder.adjust(2, 2, 2, 1)

            await message.answer(
                f"🕵️‍♂️ <b>Пользователей в боте</b>: {users_count}\n"
                f"💶<b>Заявок на вывод</b>: {pending_payments}",
                parse_mode="HTML",
                reply_markup=builder.as_markup()
            )

        except Exception as e:
            logger.error(f"Admin panel error: {e}")
            await message.answer("❌ Произошла ошибка")


# ADMIN CALLBACKS
@client_bot_router.callback_query(F.data.startswith("admin_"))
async def admin_callbacks(query: CallbackQuery, state: FSMContext, bot: Bot):
    """Admin callback handler"""
    try:
        await state.clear()
        action = query.data.replace("admin_", "")

        if action == "users":
            # Users management menu
            builder = InlineKeyboardBuilder()
            builder.button(text="🔍 Найти пользователя", callback_data="user_search")
            builder.button(text="📊 Статистика пользователей", callback_data="user_stats")
            builder.button(text="⬅️ Назад", callback_data="admin_back")
            builder.adjust(1)

            await query.message.edit_text(
                "👥 <b>Управление пользователями</b>\n\nВыберите действие:",
                parse_mode="HTML",
                reply_markup=builder.as_markup()
            )

        elif action == "payments":
            await query.answer("💰 Функция в разработке")

        elif action == "settings":
            await query.answer("⚙️ Функция в разработке")

        elif action == "channels":
            await query.answer("📢 Функция в разработке")

        elif action == "mailing":
            await query.answer("📤 Функция в разработке")

        elif action == "statistics":
            await query.answer("📊 Функция в разработке")

        elif action == "cancel":
            await query.message.delete()

        elif action == "back":
            # Admin panelga qaytish
            bot_db = await shortcuts.get_bot(bot)
            users_count = await get_bot_users_count(bot_db.id)
            pending_payments = 0

            builder = InlineKeyboardBuilder()
            builder.button(text="👥 Управление пользователями", callback_data="admin_users")
            builder.button(text="💰 Заявки на вывод", callback_data="admin_payments")
            builder.button(text="⚙️ Настройки бота", callback_data="admin_settings")
            builder.button(text="📢 Обязательные подписки", callback_data="admin_channels")
            builder.button(text="📤 Рассылка", callback_data="admin_mailing")
            builder.button(text="📊 Статистика", callback_data="admin_statistics")
            builder.button(text="❌ Закрыть", callback_data="admin_cancel")
            builder.adjust(2, 2, 2, 1)

            await query.message.edit_text(
                f"🕵️‍♂️ <b>Пользователей в боте</b>: {users_count}\n"
                f"💶<b>Заявок на вывод</b>: {pending_payments}",
                parse_mode="HTML",
                reply_markup=builder.as_markup()
            )

    except Exception as e:
        logger.error(f"Admin callback error: {e}")
        await query.answer("❌ Произошла ошибка")


# USER MANAGEMENT CALLBACKS
@client_bot_router.callback_query(F.data.startswith("user_"))
async def user_management_callbacks(query: CallbackQuery, state: FSMContext, bot: Bot):
    """Foydalanuvchilarni boshqarish"""
    try:
        action_data = query.data.replace("user_", "")

        if action_data == "search":
            # Cancel keyboard
            builder = InlineKeyboardBuilder()
            builder.button(text="❌ Отменить", callback_data="admin_cancel")

            await query.message.answer(
                "👤 Введите ID пользователя:",
                reply_markup=builder.as_markup()
            )
            await state.set_state(AdminStates.user_search)

        elif action_data.startswith("ban_"):
            user_id = int(action_data.replace("ban_", ""))
            success = await ban_user_by_id(user_id, bot)
            if success:
                await query.answer("✅ Пользователь заблокирован")
            else:
                await query.answer("❌ Ошибка блокировки")

        elif action_data.startswith("unban_"):
            user_id = int(action_data.replace("unban_", ""))
            success = await unban_user_by_id(user_id, bot)
            if success:
                await query.answer("✅ Пользователь разблокирован")
            else:
                await query.answer("❌ Ошибка разблокировки")

    except Exception as e:
        logger.error(f"User management error: {e}")
        await query.answer("❌ Ошибка")


# USER SEARCH MESSAGE HANDLER
@client_bot_router.message(AdminStates.user_search)
async def search_user(message: Message, state: FSMContext, bot: Bot):
    """Foydalanuvchi qidirish"""
    try:
        if message.text == "❌ Отменить":
            await message.answer("🚫 Действие отменено")
            await state.clear()
            return

        if not message.text.isdigit():
            await message.answer("❗ Введите корректный ID")
            return

        user_id = int(message.text)
        bot_db = await shortcuts.get_bot(bot)
        user_info = await get_user_info_by_id(user_id, bot_db.id)

        if user_info:
            is_banned = user_info.get('status') == "Заблокирован"

            # User actions keyboard
            builder = InlineKeyboardBuilder()
            if is_banned:
                builder.button(text="✅ Разблокировать", callback_data=f"user_unban_{user_id}")
            else:
                builder.button(text="🚫 Заблокировать", callback_data=f"user_ban_{user_id}")

            builder.button(text="💰 Изменить баланс", callback_data=f"user_balance_{user_id}")
            builder.button(text="👥 Изменить рефералов", callback_data=f"user_refs_{user_id}")
            builder.button(text="⬅️ Назад", callback_data="admin_users")
            builder.adjust(1, 2, 1)

            await message.answer(
                f"👤 <b>Информация о пользователе</b>\n\n"
                f"🆔 ID: <code>{user_info['id']}</code>\n"
                f"👤 Имя: {user_info['name']}\n"
                f"💰 Баланс: {user_info['balance']}\n"
                f"👥 Рефералов: {user_info['referrals']}\n"
                f"📅 Регистрация: {user_info['registration_date']}\n"
                f"🔄 Статус: {user_info['status']}",
                parse_mode="HTML",
                reply_markup=builder.as_markup()
            )
        else:
            await message.answer("❌ Пользователь не найден")

        await state.clear()

    except Exception as e:
        logger.error(f"User search error: {e}")
        await message.answer("❌ Ошибка при поиске")
        await state.clear()


# SERVICE FUNCTIONS
@sync_to_async
def get_bot_users_count(bot_id: int) -> int:
    """Bot foydalanuvchilar sonini olish"""
    try:
        refs_users = UserTG.objects.filter(bot_id=bot_id).count()
        try:
            from modul.models import ClientBotUser
            client_users = ClientBotUser.objects.filter(bot_id=bot_id).count()
        except:
            client_users = 0
        return refs_users + client_users
    except Exception as e:
        logger.error(f"Get users count error: {e}")
        return 0


@sync_to_async
def get_user_info_by_id(user_id: int, bot_id: int) -> Optional[Dict]:
    """Foydalanuvchi ma'lumotlarini olish"""
    try:
        # UserTG modelidan qidirish
        try:
            user = UserTG.objects.get(tg_id=user_id, bot_id=bot_id)
            return {
                'id': user.tg_id,
                'name': user.name or "Не указано",
                'balance': getattr(user, 'balance', 0),
                'referrals': getattr(user, 'referrals_count', 0),
                'registration_date': user.created_at.strftime("%d.%m.%Y"),
                'status': "Активен" if not getattr(user, 'is_banned', False) else "Заблокирован",
                'type': 'refs'
            }
        except UserTG.DoesNotExist:
            pass

        # ClientBotUser modelidan qidirish
        try:
            from modul.models import ClientBotUser
            user = ClientBotUser.objects.get(tg_id=user_id, bot_id=bot_id)
            return {
                'id': user.tg_id,
                'name': user.name or "Не указано",
                'balance': getattr(user, 'balance', 0),
                'referrals': 0,
                'registration_date': user.created_at.strftime("%d.%m.%Y"),
                'status': "Активен" if not getattr(user, 'is_banned', False) else "Заблокирован",
                'type': 'client'
            }
        except:
            pass

        return None

    except Exception as e:
        logger.error(f"Get user info error: {e}")
        return None


@sync_to_async
def ban_user_by_id(user_id: int, bot: Bot) -> bool:
    """Foydalanuvchini bloklash"""
    try:
        from modul.clientbot.shortcuts import get_bot

        bot_db = get_bot(bot)
        bot_id = bot_db.id if bot_db else 0

        users_updated = UserTG.objects.filter(
            tg_id=user_id, bot_id=bot_id
        ).update(is_banned=True)

        try:
            from modul.models import ClientBotUser
            client_users_updated = ClientBotUser.objects.filter(
                tg_id=user_id, bot_id=bot_id
            ).update(is_banned=True)
        except:
            client_users_updated = 0

        return users_updated > 0 or client_users_updated > 0

    except Exception as e:
        logger.error(f"Ban user error: {e}")
        return False


@sync_to_async
def unban_user_by_id(user_id: int, bot: Bot) -> bool:
    """Foydalanuvchini blokdan chiqarish"""
    try:
        from modul.clientbot.shortcuts import get_bot

        bot_db = get_bot(bot)
        bot_id = bot_db.id if bot_db else 0

        users_updated = UserTG.objects.filter(
            tg_id=user_id, bot_id=bot_id
        ).update(is_banned=False)

        try:
            from modul.models import ClientBotUser
            client_users_updated = ClientBotUser.objects.filter(
                tg_id=user_id, bot_id=bot_id
            ).update(is_banned=False)
        except:
            client_users_updated = 0

        return users_updated > 0 or client_users_updated > 0

    except Exception as e:
        logger.error(f"Unban user error: {e}")
        return False


logger.info("✅ Universal admin panel handlers loaded")
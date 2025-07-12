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
from modul.clientbot.handlers.admin.admin_service import get_users_count, get_channels_for_admin

from modul.models import Bot as BotModel, User, UserTG, ClientBotUser
from modul.loader import client_bot_router
from asgiref.sync import sync_to_async

logger = logging.getLogger(__name__)


class AdminFilter(BaseFilter):
    async def __call__(self, message: Message, bot: Bot) -> bool:
        bot_db = await shortcuts.get_bot(bot)
        admin_id = bot_db.owner.uid
        return message.from_user.id == admin_id

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
            builder.adjust(1, 2, 1, 2, 1)

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
        # Har xil bot turlari uchun foydalanuvchilar
        refs_users = UserTG.objects.filter(bot_id=bot_id).count()
        client_users = ClientBotUser.objects.filter(bot_id=bot_id).count()
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


# Admin panel callback handler'larini qo'shing

@client_bot_router.callback_query(F.data == "admin_users")
async def admin_users_handler(callback: CallbackQuery):
    """Пользователи управления"""
    try:
        # Foydalanuvchilar ro'yxatini olish
        users_count = await get_users_count()  # Bu funktsiya mavjud bo'lishi kerak

        text = f"👥 Управление пользователями\n\n"
        text += f"📊 Общее количество пользователей: {users_count}\n\n"
        text += "Выберите действие:"

        builder = InlineKeyboardBuilder()
        builder.button(text="📊 Статистика пользователей", callback_data="users_stats")
        builder.button(text="🔍 Найти пользователя", callback_data="find_user")
        builder.button(text="📋 Список пользователей", callback_data="users_list")
        builder.button(text="🚫 Заблокировать пользователя", callback_data="ban_user")
        builder.button(text="🔄 Назад", callback_data="admin_panel")
        builder.adjust(1)

        await callback.message.edit_text(text, reply_markup=builder.as_markup())
    except Exception as e:
        await callback.answer(f"Ошибка: {e}", show_alert=True)


@client_bot_router.callback_query(F.data == "admin_payments")
async def admin_payments_handler(callback: CallbackQuery):
    """Заявки на вывод средств"""
    try:
        # Pending payments ni olish
        pending_payments = await get_pending_payments()  # Bu funktsiya yaratilishi kerak

        text = f"💰 Заявки на вывод средств\n\n"
        if pending_payments:
            text += f"📋 Активных заявок: {len(pending_payments)}\n\n"
            for payment in pending_payments[:5]:  # Faqat 5 ta ko'rsatish
                text += f"• ID: {payment['id']} - {payment['amount']} руб.\n"
        else:
            text += "📭 Нет активных заявок на вывод\n\n"

        builder = InlineKeyboardBuilder()
        builder.button(text="📋 Все заявки", callback_data="all_payments")
        builder.button(text="✅ Одобрить заявку", callback_data="approve_payment")
        builder.button(text="❌ Отклонить заявку", callback_data="reject_payment")
        builder.button(text="🔄 Назад", callback_data="admin_panel")
        builder.adjust(1)

        await callback.message.edit_text(text, reply_markup=builder.as_markup())
    except Exception as e:
        await callback.answer(f"Ошибка: {e}", show_alert=True)


@client_bot_router.callback_query(F.data == "admin_settings")
async def admin_settings_handler(callback: CallbackQuery):
    """Настройки бота"""
    try:
        # Bot sozlamalarini olish
        bot_settings = await get_bot_settings()  # Bu funktsiya yaratilishi kerak

        text = f"⚙️ Настройки бота\n\n"
        text += f"🤖 Название бота: {bot_settings.get('name', 'Не установлено')}\n"
        text += f"💸 Минимальная выплата: {bot_settings.get('min_payout', 'Не установлено')} руб.\n"
        text += f"💰 Реферальная награда: {bot_settings.get('ref_reward', 'Не установлено')} руб.\n\n"
        text += "Выберите параметр для изменения:"

        builder = InlineKeyboardBuilder()
        builder.button(text="📝 Изменить название", callback_data="change_bot_name")
        builder.button(text="💸 Изменить мин. выплату", callback_data="change_min_payout")
        builder.button(text="💰 Изменить реф. награду", callback_data="change_ref_reward")
        builder.button(text="🔄 Назад", callback_data="admin_panel")
        builder.adjust(1)

        await callback.message.edit_text(text, reply_markup=builder.as_markup())
    except Exception as e:
        await callback.answer(f"Ошибка: {e}", show_alert=True)


@client_bot_router.callback_query(F.data == "admin_channels")
async def admin_channels_handler(callback: CallbackQuery):
    """Обязательные подписки"""
    try:
        # Majburiy obunalar ro'yxatini olish
        channels = await get_channels_for_admin()  # Bu funktsiya mavjud

        text = f"📢 Обязательные подписки\n\n"
        if channels:
            text += f"📋 Активных каналов: {len(channels)}\n\n"
            for i, channel in enumerate(channels, 1):
                text += f"{i}. {channel[1]} (ID: {channel[0]})\n"
        else:
            text += "📭 Обязательных подписок нет\n\n"

        builder = InlineKeyboardBuilder()
        builder.button(text="➕ Добавить канал", callback_data="add_channel")
        builder.button(text="🗑 Удалить канал", callback_data="delete_channel")
        builder.button(text="📋 Список каналов", callback_data="channels_list")
        builder.button(text="🔄 Назад", callback_data="admin_panel")
        builder.adjust(1)

        await callback.message.edit_text(text, reply_markup=builder.as_markup())
    except Exception as e:
        await callback.answer(f"Ошибка: {e}", show_alert=True)


@client_bot_router.callback_query(F.data == "admin_mailing")
async def admin_mailing_handler(callback: CallbackQuery):
    """Рассылка сообщений"""
    try:
        text = f"📤 Рассылка сообщений\n\n"
        text += "Выберите тип рассылки:"

        builder = InlineKeyboardBuilder()
        builder.button(text="📝 Текстовая рассылка", callback_data="text_mailing")
        builder.button(text="🖼 Рассылка с фото", callback_data="photo_mailing")
        builder.button(text="📊 Статистика рассылок", callback_data="mailing_stats")
        builder.button(text="🔄 Назад", callback_data="admin_panel")
        builder.adjust(1)

        await callback.message.edit_text(text, reply_markup=builder.as_markup())
    except Exception as e:
        await callback.answer(f"Ошибка: {e}", show_alert=True)


@client_bot_router.callback_query(F.data == "admin_statistics")
async def admin_statistics_handler(callback: CallbackQuery):
    """Статистика бота"""
    try:
        # Statistika ma'lumotlarini olish
        stats = await get_bot_statistics()  # Bu funktsiya yaratilishi kerak

        text = f"📊 Статистика бота\n\n"
        text += f"👥 Общее количество пользователей: {stats.get('total_users', 0)}\n"
        text += f"📈 Новых пользователей сегодня: {stats.get('new_users_today', 0)}\n"
        text += f"💰 Общая сумма выплат: {stats.get('total_payouts', 0)} руб.\n"
        text += f"🔄 Активных пользователей: {stats.get('active_users', 0)}\n"
        text += f"📢 Каналов в подписках: {stats.get('channels_count', 0)}\n"

        builder = InlineKeyboardBuilder()
        builder.button(text="📈 Подробная статистика", callback_data="detailed_stats")
        builder.button(text="📊 Экспорт данных", callback_data="export_stats")
        builder.button(text="🔄 Назад", callback_data="admin_panel")
        builder.adjust(1)

        await callback.message.edit_text(text, reply_markup=builder.as_markup())
    except Exception as e:
        await callback.answer(f"Ошибка: {e}", show_alert=True)


@client_bot_router.callback_query(F.data == "admin_cancel")
async def admin_cancel_handler(callback: CallbackQuery):
    """Admin panelni yopish"""
    try:
        await callback.message.delete()
        await callback.answer("Панель админа закрыта")
    except Exception as e:
        await callback.answer(f"Ошибка: {e}", show_alert=True)


@client_bot_router.callback_query(F.data == "admin_panel")
async def back_to_admin_panel(callback: CallbackQuery):
    """Admin panelga qaytish"""
    try:
        count = await get_users_count()

        builder = InlineKeyboardBuilder()
        builder.button(text="👥 Управление пользователями", callback_data="admin_users")
        builder.button(text="💰 Заявки на вывод", callback_data="admin_payments")
        builder.button(text="⚙️ Настройки бота", callback_data="admin_settings")
        builder.button(text="📢 Обязательные подписки", callback_data="admin_channels")
        builder.button(text="📤 Рассылка", callback_data="admin_mailing")
        builder.button(text="📊 Статистика", callback_data="admin_statistics")
        builder.button(text="❌ Закрыть", callback_data="admin_cancel")
        builder.adjust(1)

        await callback.message.edit_text(
            f"🕵 Панель админа\nКоличество юзеров в боте: {count}",
            reply_markup=builder.as_markup()
        )
    except Exception as e:
        await callback.answer(f"Ошибка: {e}", show_alert=True)


# Yordamchi funktsiyalar (agar mavjud bo'lmasa yaratish kerak)
async def get_pending_payments():
    """Pending payments ni olish"""
    # Bu yerda database'dan pending payments ni olish kerak
    return []


async def get_bot_settings():
    """Bot sozlamalarini olish"""
    # Bu yerda bot sozlamalarini olish kerak
    return {
        'name': 'My Bot',
        'min_payout': 100,
        'ref_reward': 10
    }


async def get_bot_statistics():
    """Bot statistikasini olish"""
    # Bu yerda bot statistikasini olish kerak
    return {
        'total_users': 0,
        'new_users_today': 0,
        'total_payouts': 0,
        'active_users': 0,
        'channels_count': 0
    }

logger.info("✅ Universal admin panel handlers loaded")
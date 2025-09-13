# modul/bot/main_bot/handlers/admin_panel.py
import json

from aiogram import F, Router, types, Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from asgiref.sync import sync_to_async
from django.db.models import Count, Q
from modul.loader import main_bot_router
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class AdminChannelStates(StatesGroup):
    waiting_for_channel_message = State()
    waiting_for_broadcast_message = State()

# Админ ID список
ADMIN_IDS = [
    1161180912,  # Основной админ
    558618720,  # Дополнительный админ
]


def is_admin_user(user_id: int) -> bool:
    """Проверка админских прав"""
    return user_id in ADMIN_IDS

# main_menu()
def get_admin_main_menu():
    """Главное меню админ панели"""
    keyboard = InlineKeyboardBuilder()

    keyboard.row(
        InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats"),
        InlineKeyboardButton(text="🤖 Боты", callback_data="admin_bots")
    )
    keyboard.row(
        InlineKeyboardButton(text="👥 Пользователи", callback_data="admin_users"),
        InlineKeyboardButton(text="📢 Каналы", callback_data="admin_channels")
    )
    keyboard.row(
        InlineKeyboardButton(text="📣 Рассылка", callback_data="admin_broadcast"),  # Yangi tugma
        InlineKeyboardButton(text="🔄 Обновить", callback_data="admin_refresh")
    )
    keyboard.row(
        InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main")
    )

    return keyboard.as_markup()

@sync_to_async
def get_all_active_bots():
    """Получить все активные боты"""
    try:
        from modul.models import Bot
        bots = Bot.objects.filter(bot_enable=True).values('token', 'username')
        return list(bots)
    except Exception as e:
        logger.error(f"Error getting active bots: {e}")
        return []

@sync_to_async
def get_all_bot_users():
    """Получить всех пользователей всех ботов"""
    try:
        from modul.models import ClientBotUser
        users = ClientBotUser.objects.select_related('user', 'bot').filter(
            bot__bot_enable=True
        ).values('uid', 'bot__token')
        return list(users)
    except Exception as e:
        logger.error(f"Error getting bot users: {e}")
        return []

def get_channels_menu():
    """Меню управления каналами"""
    keyboard = InlineKeyboardBuilder()

    keyboard.row(
        InlineKeyboardButton(text="📋 Список каналов", callback_data="channels_list"),
        InlineKeyboardButton(text="➕ Добавить канал", callback_data="channels_add")
    )
    keyboard.row(
        InlineKeyboardButton(text="🗑 Удалить канал", callback_data="channels_delete"),
        InlineKeyboardButton(text="🔄 Статус каналов", callback_data="channels_status")
    )
    keyboard.row(
        InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_main")
    )

    return keyboard.as_markup()


def get_back_menu():
    """Кнопка назад"""
    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_main"))
    return keyboard.as_markup()


# ==================== ФУНКЦИИ ДЛЯ РАБОТЫ С БАЗОЙ ДАННЫХ ====================

@sync_to_async
def get_system_stats():
    """Получить основную статистику системы"""
    try:
        from modul.models import Bot, UserTG, SystemChannel

        total_bots = Bot.objects.count()
        total_users = UserTG.objects.count()
        system_channels = SystemChannel.objects.filter(is_active=True).count()

        return {
            'total_bots': total_bots,
            'total_users': total_users,
            'system_channels': system_channels
        }
    except Exception as e:
        logger.error(f"Error getting system stats: {e}")
        return {'total_bots': 0, 'total_users': 0, 'system_channels': 0}


@sync_to_async
def get_detailed_stats():
    """Получить детальную статистику"""
    try:
        from modul.models import Bot, UserTG, ClientBotUser, SystemChannel
        from django.utils import timezone
        from datetime import timedelta

        total_bots = Bot.objects.count()
        active_bots = Bot.objects.filter(bot_enable=True).count()
        disabled_bots = total_bots - active_bots

        total_users = UserTG.objects.count()

        # Активные пользователи за последние 24 часа и 7 дней
        now = timezone.now()
        day_ago = now - timedelta(days=1)
        week_ago = now - timedelta(days=7)

        try:
            active_24h = UserTG.objects.filter(last_interaction__gte=day_ago).count()
            active_7d = UserTG.objects.filter(last_interaction__gte=week_ago).count()
        except:
            active_24h = UserTG.objects.filter(created_at__gte=day_ago).count()
            active_7d = UserTG.objects.filter(created_at__gte=week_ago).count()

        # Каналы
        system_channels = SystemChannel.objects.count()
        active_channels = SystemChannel.objects.filter(is_active=True).count()

        return {
            'total_bots': total_bots,
            'active_bots': active_bots,
            'disabled_bots': disabled_bots,
            'total_users': total_users,
            'active_24h': active_24h,
            'active_7d': active_7d,
            'system_channels': system_channels,
            'active_channels': active_channels
        }
    except Exception as e:
        logger.error(f"Error getting detailed stats: {e}")
        return {
            'total_bots': 0,
            'active_bots': 0,
            'disabled_bots': 0,
            'total_users': 0,
            'active_24h': 0,
            'active_7d': 0,
            'system_channels': 0,
            'active_channels': 0
        }


@sync_to_async
def get_bots_info():
    """Получить информацию о ботах"""
    try:
        from modul.models import Bot, ClientBotUser
        from django.db.models import Count

        bots = Bot.objects.select_related('owner').annotate(
            users_count=Count('clients')
        ).order_by('-users_count')[:20]

        result = []
        for bot in bots:
            owner_name = "Unknown"
            if bot.owner:
                if hasattr(bot.owner, 'first_name') and bot.owner.first_name:
                    owner_name = bot.owner.first_name
                elif hasattr(bot.owner, 'username') and bot.owner.username:
                    owner_name = bot.owner.username
                else:
                    owner_name = f"ID{bot.owner.uid}"

            result.append({
                'username': bot.username,
                'bot_enable': bot.bot_enable,
                'users_count': bot.users_count,
                'owner_name': owner_name,
                'owner_id': bot.owner.uid if bot.owner else 0
            })

        return result
    except Exception as e:
        logger.error(f"Error getting bots info: {e}")
        return []


@sync_to_async
def get_users_info():
    """Получить информацию о пользователях"""
    try:
        from modul.models import Bot, UserTG, ClientBotUser
        from django.utils import timezone
        from django.db.models import Avg, Max, Count
        from datetime import timedelta

        total_users = UserTG.objects.count()

        now = timezone.now()
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_ago = now - timedelta(days=7)
        day_ago = now - timedelta(days=1)

        today_users = UserTG.objects.filter(created_at__gte=today).count()
        week_users = UserTG.objects.filter(created_at__gte=week_ago).count()

        try:
            active_24h = UserTG.objects.filter(last_interaction__gte=day_ago).count()
        except:
            active_24h = UserTG.objects.filter(created_at__gte=day_ago).count()

        # Статистика по ботам
        try:
            bot_stats = Bot.objects.annotate(users_count=Count('clients')).aggregate(
                avg_users=Avg('users_count'),
                max_users=Max('users_count')
            )
        except:
            bot_stats = {'avg_users': 0, 'max_users': 0}

        return {
            'total_users': total_users,
            'today_users': today_users,
            'week_users': week_users,
            'active_24h': active_24h,
            'avg_per_bot': bot_stats['avg_users'] or 0,
            'max_in_bot': bot_stats['max_users'] or 0
        }
    except Exception as e:
        logger.error(f"Error getting users info: {e}")
        return {
            'total_users': 0,
            'today_users': 0,
            'week_users': 0,
            'active_24h': 0,
            'avg_per_bot': 0,
            'max_in_bot': 0
        }


@sync_to_async
def get_channels_info():
    """Получить информацию о каналах"""
    try:
        from modul.models import SystemChannel

        total = SystemChannel.objects.count()
        active = SystemChannel.objects.filter(is_active=True).count()
        disabled = total - active

        return {
            'total_channels': total,
            'active_channels': active,
            'disabled_channels': disabled
        }
    except Exception as e:
        logger.error(f"Error getting channels info: {e}")
        return {
            'total_channels': 0,
            'active_channels': 0,
            'disabled_channels': 0
        }


@sync_to_async
def get_all_system_channels_detailed():
    """Получить все системные каналы с деталями"""
    try:
        from modul.models import SystemChannel
        channels = SystemChannel.objects.all().order_by('-created_at')
        result = []

        for channel in channels:
            result.append({
                'channel_id': channel.channel_id,
                'title': channel.title or 'Без названия',
                'channel_url': channel.channel_url,
                'is_active': channel.is_active,
                'created_at': channel.created_at.strftime('%Y-%m-%d %H:%M') if channel.created_at else 'N/A'
            })

        return result
    except Exception as e:
        logger.error(f"Error getting system channels detailed: {e}")
        return []


@sync_to_async
def check_system_channel_exists(channel_id):
    """Проверить существование системного канала"""
    try:
        from modul.models import SystemChannel
        return SystemChannel.objects.filter(channel_id=channel_id).exists()
    except Exception as e:
        logger.error(f"Error checking system channel exists: {e}")
        return False


@sync_to_async
def save_system_channel(channel_id, channel_url, title, added_by):
    """Сохранить системный канал"""
    try:
        from modul.models import SystemChannel
        channel, created = SystemChannel.objects.get_or_create(
            channel_id=channel_id,
            defaults={
                'channel_url': channel_url,
                'title': title,
                'is_active': True,
                'added_by_user_id': added_by
            }
        )
        return created
    except Exception as e:
        logger.error(f"Error saving system channel: {e}")
        return False


@sync_to_async
def get_channel_info(channel_id):
    """Получить информацию о канале"""
    try:
        from modul.models import SystemChannel
        channel = SystemChannel.objects.filter(channel_id=channel_id).first()
        if channel:
            return {
                'title': channel.title or 'Канал',
                'channel_url': channel.channel_url,
                'is_active': channel.is_active
            }
        return None
    except Exception as e:
        logger.error(f"Error getting channel info: {e}")
        return None


@sync_to_async
def delete_system_channel(channel_id):
    """Удалить системный канал"""
    try:
        from modul.models import SystemChannel
        deleted_count, _ = SystemChannel.objects.filter(channel_id=channel_id).delete()
        return deleted_count > 0
    except Exception as e:
        logger.error(f"Error deleting system channel: {e}")
        return False


@sync_to_async
def update_channel_status(channel_id, is_active):
    """Обновить статус канала"""
    try:
        from modul.models import SystemChannel
        SystemChannel.objects.filter(channel_id=channel_id).update(is_active=is_active)
        return True
    except Exception as e:
        logger.error(f"Error updating channel status: {e}")
        return False


async def notify_other_admins(bot, channel_title, admin_id, admin_name):
    """Уведомить других админов о добавлении канала"""
    try:
        text = (
            f"🚨 СИСТЕМНЫЙ КАНАЛ ДОБАВЛЕН\n\n"
            f"📢 {channel_title}\n"
            f"👤 Администратор: {admin_name} ({admin_id})\n"
            f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            f"Теперь все боты требуют подписку на этот канал!"
        )

        for aid in ADMIN_IDS:
            if aid != admin_id:
                try:
                    await bot.send_message(aid, text)
                except:
                    pass
    except Exception as e:
        logger.error(f"Error notifying admins: {e}")


# ==================== ХЕНДЛЕРЫ ====================

@main_bot_router.message(F.text == "/admin")
async def show_admin_panel(message: Message):
    """Показать админ панель"""
    if not is_admin_user(message.from_user.id):
        await message.answer("У вас нет доступа к админ панели")
        return

    stats = await get_system_stats()

    text = (
        f"🔧 АДМИН ПАНЕЛЬ\n\n"
        f"📊 Общая статистика:\n"
        f"🤖 Ботов в системе: {stats['total_bots']}\n"
        f"👥 Всего пользователей: {stats['total_users']}\n"
        f"📢 Системных каналов: {stats['system_channels']}\n"
        f"⏰ Обновлено: {datetime.now().strftime('%H:%M:%S')}"
    )

    await message.answer(text, reply_markup=get_admin_main_menu())


@main_bot_router.callback_query(F.data == "admin_main")
async def admin_main_callback(callback: CallbackQuery):
    """Главное меню админ панели"""
    if not is_admin_user(callback.from_user.id):
        await callback.answer("Доступ запрещен")
        return

    stats = await get_system_stats()

    text = (
        f"🔧 АДМИН ПАНЕЛЬ\n\n"
        f"📊 Общая статистика:\n"
        f"🤖 Ботов в системе: {stats['total_bots']}\n"
        f"👥 Всего пользователей: {stats['total_users']}\n"
        f"📢 Системных каналов: {stats['system_channels']}\n"
        f"⏰ Обновлено: {datetime.now().strftime('%H:%M:%S')}"
    )

    await callback.message.edit_text(text, reply_markup=get_admin_main_menu())
    await callback.answer()


@main_bot_router.callback_query(F.data == "admin_stats")
async def admin_stats_callback(callback: CallbackQuery):
    """Детальная статистика"""
    if not is_admin_user(callback.from_user.id):
        await callback.answer("Доступ запрещен")
        return

    stats = await get_detailed_stats()

    text = (
        f"📊 ДЕТАЛЬНАЯ СТАТИСТИКА\n\n"
        f"🤖 БОТЫ:\n"
        f"• Всего ботов: {stats['total_bots']}\n"
        f"• Активных ботов: {stats['active_bots']}\n"
        f"• Отключенных ботов: {stats['disabled_bots']}\n\n"
        f"👥 ПОЛЬЗОВАТЕЛИ:\n"
        f"• Всего пользователей: {stats['total_users']}\n"
        f"• Активных за 24ч: {stats['active_24h']}\n"
        f"• Активных за 7 дней: {stats['active_7d']}\n\n"
        f"📢 КАНАЛЫ:\n"
        f"• Системных каналов: {stats['system_channels']}\n"
        f"• Активных каналов: {stats['active_channels']}\n"
        f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )

    await callback.message.edit_text(text, reply_markup=get_back_menu())
    await callback.answer()


@main_bot_router.callback_query(F.data == "admin_bots")
async def admin_bots_callback(callback: CallbackQuery):
    """Информация о ботах"""
    if not is_admin_user(callback.from_user.id):
        await callback.answer("Доступ запрещен")
        return

    bots_info = await get_bots_info()

    text = f"🤖 ИНФОРМАЦИЯ О БОТАХ\n\n"

    for bot_info in bots_info[:10]:  # Показываем первые 10
        status = "🟢" if bot_info['bot_enable'] else "🔴"
        text += (
            f"{status} @{bot_info['username']}\n"
            f"   👥 Пользователей: {bot_info['users_count']}\n"
            f"   👤 Владелец: {bot_info['owner_name']} (ID: {bot_info['owner_id']})\n\n"
        )

    if len(bots_info) > 10:
        text += f"... и еще {len(bots_info) - 10} ботов"

    await callback.message.edit_text(text, reply_markup=get_back_menu())
    await callback.answer()


@main_bot_router.callback_query(F.data == "admin_users")
async def admin_users_callback(callback: CallbackQuery):
    """Информация о пользователях"""
    if not is_admin_user(callback.from_user.id):
        await callback.answer("Доступ запрещен")
        return

    users_info = await get_users_info()

    text = (
        f"👥 ИНФОРМАЦИЯ О ПОЛЬЗОВАТЕЛЯХ\n\n"
        f"📊 Общая статистика:\n"
        f"• Всего пользователей: {users_info['total_users']}\n"
        f"• Новых за сегодня: {users_info['today_users']}\n"
        f"• Новых за неделю: {users_info['week_users']}\n"
        f"• Активных за 24ч: {users_info['active_24h']}\n\n"
        f"🤖 По ботам:\n"
        f"• В среднем на бота: {users_info['avg_per_bot']:.1f}\n"
        f"• Максимум в одном боте: {users_info['max_in_bot']}\n"
        f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )

    await callback.message.edit_text(text, reply_markup=get_back_menu())
    await callback.answer()


@main_bot_router.callback_query(F.data == "admin_channels")
async def admin_channels_callback(callback: CallbackQuery):
    """Управление каналами"""
    if not is_admin_user(callback.from_user.id):
        await callback.answer("Доступ запрещен")
        return

    channels_info = await get_channels_info()

    text = (
        f"📢 УПРАВЛЕНИЕ КАНАЛАМИ\n\n"
        f"📊 Статистика:\n"
        f"• Всего системных каналов: {channels_info['total_channels']}\n"
        f"• Активных каналов: {channels_info['active_channels']}\n"
        f"• Отключенных каналов: {channels_info['disabled_channels']}\n\n"
        f"ℹ️ Системные каналы обязательны для всех ботов"
    )

    await callback.message.edit_text(text, reply_markup=get_channels_menu())
    await callback.answer()


@main_bot_router.callback_query(F.data == "channels_list")
async def channels_list_callback(callback: CallbackQuery):
    """Список всех каналов"""
    if not is_admin_user(callback.from_user.id):
        await callback.answer("Доступ запрещен")
        return

    channels = await get_all_system_channels_detailed()

    if not channels:
        text = "📋 Системных каналов нет"
    else:
        text = f"📋 СИСТЕМНЫЕ КАНАЛЫ ({len(channels)}):\n\n"

        for i, channel in enumerate(channels, 1):
            status = "🟢 Активен" if channel['is_active'] else "🔴 Отключен"
            text += (
                f"{i}. {channel['title'] or 'Без названия'}\n"
                f"   🆔 ID: {channel['channel_id']}\n"
                f"   📊 {status}\n"
                f"   📅 Добавлен: {channel['created_at']}\n\n"
            )

    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_channels"))

    await callback.message.edit_text(text, reply_markup=keyboard.as_markup())
    await callback.answer()


@main_bot_router.callback_query(F.data == "channels_add")
async def channels_add_callback(callback: CallbackQuery, state: FSMContext):
    """Начать добавление канала"""
    if not is_admin_user(callback.from_user.id):
        await callback.answer("Доступ запрещен")
        return

    text = (
        f"➕ ДОБАВЛЕНИЕ СИСТЕМНОГО КАНАЛА\n\n"
        f"1️⃣ Перейдите в канал\n"
        f"2️⃣ Найдите любое сообщение\n"
        f"3️⃣ Переслать его сюда\n\n"
        f"⚠️ Бот должен быть администратором канала!\n"
        f"🚨 Канал станет обязательным для ВСЕХ ботов!"
    )

    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(text="❌ Отменить", callback_data="admin_channels"))

    await callback.message.edit_text(text, reply_markup=keyboard.as_markup())
    await state.set_state(AdminChannelStates.waiting_for_channel_message)
    await callback.answer()


@main_bot_router.callback_query(F.data == "channels_delete")
async def channels_delete_callback(callback: CallbackQuery):
    """Удаление канала - показать список"""
    if not is_admin_user(callback.from_user.id):
        await callback.answer("Доступ запрещен")
        return

    channels = await get_all_system_channels_detailed()

    if not channels:
        text = "📋 Нет каналов для удаления"
        keyboard = InlineKeyboardBuilder()
        keyboard.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_channels"))
    else:
        text = f"🗑 ВЫБЕРИТЕ КАНАЛ ДЛЯ УДАЛЕНИЯ:\n\n"
        keyboard = InlineKeyboardBuilder()

        for channel in channels:
            status = "🟢" if channel['is_active'] else "🔴"
            channel_name = channel['title'] or f"ID: {channel['channel_id']}"
            keyboard.row(InlineKeyboardButton(
                text=f"{status} {channel_name}",
                callback_data=f"delete_channel_{channel['channel_id']}"
            ))

        keyboard.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_channels"))

    await callback.message.edit_text(text, reply_markup=keyboard.as_markup())
    await callback.answer()


@main_bot_router.callback_query(F.data.startswith("delete_channel_"))
async def delete_channel_callback(callback: CallbackQuery):
    """Подтверждение удаления канала"""
    if not is_admin_user(callback.from_user.id):
        await callback.answer("Доступ запрещен")
        return

    channel_id = int(callback.data.replace("delete_channel_", ""))
    channel_info = await get_channel_info(channel_id)

    if not channel_info:
        await callback.answer("Канал не найден")
        return

    text = (
        f"⚠️ ПОДТВЕРДИТЕ УДАЛЕНИЕ\n\n"
        f"📢 Канал: {channel_info['title']}\n"
        f"🆔 ID: {channel_id}\n\n"
        f"🚨 После удаления боты НЕ будут требовать подписку на этот канал!\n\n"
        f"Вы уверены?"
    )

    keyboard = InlineKeyboardBuilder()
    keyboard.row(
        InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"confirm_delete_{channel_id}"),
        InlineKeyboardButton(text="❌ Отменить", callback_data="channels_delete")
    )

    await callback.message.edit_text(text, reply_markup=keyboard.as_markup())
    await callback.answer()


@main_bot_router.callback_query(F.data.startswith("confirm_delete_"))
async def confirm_delete_channel_callback(callback: CallbackQuery, bot: Bot):
    """Окончательное удаление канала"""
    if not is_admin_user(callback.from_user.id):
        await callback.answer("Доступ запрещен")
        return

    channel_id = int(callback.data.replace("confirm_delete_", ""))
    channel_info = await get_channel_info(channel_id)

    success = await delete_system_channel(channel_id)

    if success:
        channel_title = channel_info['title'] if channel_info else 'Неизвестный'
        text = (
            f"✅ КАНАЛ УДАЛЕН!\n\n"
            f"📢 {channel_title}\n"
            f"🆔 ID: {channel_id}\n"
            f"👤 Удалил: {callback.from_user.full_name}\n\n"
            f"ℹ️ Боты больше не требуют подписку на этот канал"
        )
    else:
        text = f"❌ Ошибка удаления канала"

    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(text="⬅️ К каналам", callback_data="admin_channels"))

    await callback.message.edit_text(text, reply_markup=keyboard.as_markup())
    await callback.answer()


@main_bot_router.callback_query(F.data == "channels_status")
async def channels_status_callback(callback: CallbackQuery, bot: Bot):
    """Проверить статус каналов"""
    if not is_admin_user(callback.from_user.id):
        await callback.answer("Доступ запрещен")
        return

    await callback.answer("🔄 Проверяю каналы...")

    channels = await get_all_system_channels_detailed()

    if not channels:
        text = "📋 Нет системных каналов для проверки"
    else:
        text = f"🔄 СТАТУС СИСТЕМНЫХ КАНАЛОВ:\n\n"

        for i, channel in enumerate(channels, 1):
            try:
                # Проверяем доступность канала
                chat = await bot.get_chat(channel['channel_id'])

                # Проверяем права бота
                bot_member = await bot.get_chat_member(channel['channel_id'], bot.id)

                if bot_member.status in ['creator', 'administrator']:
                    bot_status = "🤖 Админ"
                else:
                    bot_status = "⚠️ Не админ"

                status = f"✅ Доступен | {bot_status}"

            except Exception as e:
                error_message = str(e)[:30]
                status = f"❌ Недоступен: {error_message}"

            text += (
                f"{i}. {channel['title']}\n"
                f"   🆔 {channel['channel_id']}\n"
                f"   📊 {status}\n\n"
            )

    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(text="🔄 Обновить", callback_data="channels_status"))
    keyboard.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_channels"))

    await callback.message.edit_text(text, reply_markup=keyboard.as_markup())


@main_bot_router.callback_query(F.data == "admin_refresh")
async def admin_refresh_callback(callback: CallbackQuery):
    """Обновить админ панель"""
    if not is_admin_user(callback.from_user.id):
        await callback.answer("Доступ запрещен")
        return

    await callback.answer("🔄 Обновляю...")
    await admin_main_callback(callback)


@main_bot_router.message(AdminChannelStates.waiting_for_channel_message)
async def process_admin_channel_message(message: Message, state: FSMContext, bot: Bot):
    """Обработка сообщения для добавления канала"""
    if not is_admin_user(message.from_user.id):
        await message.answer("Доступ запрещен")
        await state.clear()
        return

    try:
        # Проверка forward сообщения
        if not message.forward_from_chat:
            await message.answer(
                "❌ Перешлите сообщение из канала\n\n"
                "Используйте /admin чтобы вернуться в панель"
            )
            return

        # Проверка типа канала
        if message.forward_from_chat.type != 'channel':
            await message.answer(
                "❌ Это не канал! Перешлите сообщение из канала\n\n"
                "Используйте /admin чтобы вернуться в панель"
            )
            return

        channel_id = message.forward_from_chat.id
        channel_title = message.forward_from_chat.title
        channel_username = getattr(message.forward_from_chat, 'username', None)

        # Проверка прав бота
        try:
            bot_member = await bot.get_chat_member(channel_id, bot.id)
            if bot_member.status not in ['creator', 'administrator']:
                await message.answer(
                    f"❌ Бот не администратор канала '{channel_title}'\n\n"
                    f"Добавьте бота в администраторы и попробуйте снова\n"
                    f"Используйте /admin чтобы вернуться в панель"
                )
                return
        except Exception as e:
            error_text = str(e)
            await message.answer(
                f"❌ Ошибка проверки канала '{channel_title}': {error_text}\n\n"
                f"Используйте /admin чтобы вернуться в панель"
            )
            return

        # Проверка существования
        exists = await check_system_channel_exists(channel_id)
        if exists:
            await message.answer(
                f"⚠️ Канал '{channel_title}' уже в системе\n\n"
                f"Используйте /admin чтобы вернуться в панель"
            )
            await state.clear()
            return

        # Получение ссылки
        invite_link = f"https://t.me/{channel_username}" if channel_username else None
        if not invite_link:
            try:
                link_data = await bot.create_chat_invite_link(channel_id)
                invite_link = link_data.invite_link
            except:
                invite_link = f"Channel ID: {channel_id}"

        # Сохранение в базу
        success = await save_system_channel(channel_id, invite_link, channel_title, message.from_user.id)

        if success:
            await message.answer(
                f"✅ СИСТЕМНЫЙ КАНАЛ ДОБАВЛЕН!\n\n"
                f"📢 {channel_title}\n"
                f"🆔 {channel_id}\n"
                f"🔗 {invite_link}\n"
                f"👤 Админ: {message.from_user.full_name}\n\n"
                f"🚨 Теперь ВСЕ боты требуют подписку на этот канал!\n\n"
                f"Используйте /admin чтобы вернуться в панель"
            )

            # Уведомление других админов
            await notify_other_admins(bot, channel_title, message.from_user.id, message.from_user.full_name)
        else:
            await message.answer(
                f"❌ Ошибка сохранения канала\n\n"
                f"Используйте /admin чтобы вернуться в панель"
            )

        await state.clear()

    except Exception as e:
        logger.error(f"Error in process_admin_channel_message: {e}")
        error_message = str(e)
        await message.answer(
            f"❌ Произошла ошибка: {error_message}\n\n"
            f"Используйте /admin чтобы вернуться в панель"
        )
        await state.clear()


@sync_to_async
def get_broadcast_stats():
    """Получить статистику для рассылки"""
    try:
        from modul.models import Bot, ClientBotUser

        active_bots = Bot.objects.filter(bot_enable=True).count()
        total_users = ClientBotUser.objects.filter(bot__bot_enable=True).count()

        return {
            'active_bots': active_bots,
            'total_users': total_users
        }
    except Exception as e:
        logger.error(f"Error getting broadcast stats: {e}")
        return {'active_bots': 0, 'total_users': 0}


# Yangi handlerlar
@main_bot_router.callback_query(F.data == "admin_broadcast")
async def admin_broadcast_callback(callback: CallbackQuery):
    """Меню рассылки"""
    if not is_admin_user(callback.from_user.id):
        await callback.answer("Доступ запрещен")
        return

    stats = await get_broadcast_stats()

    text = (
        f"📣 РАССЫЛКА ПО ВСЕМ БОТАМ\n\n"
        f"📊 Охват рассылки:\n"
        f"🤖 Активных ботов: {stats['active_bots']}\n"
        f"👥 Всего пользователей: {stats['total_users']}\n\n"
        f"⚠️ Сообщение будет отправлено ВСЕМ пользователям через ВСЕ активные боты!\n\n"
        f"Выберите действие:"
    )

    keyboard = InlineKeyboardBuilder()
    keyboard.row(
        InlineKeyboardButton(text="📝 Создать рассылку", callback_data="broadcast_create"),
        InlineKeyboardButton(text="📊 Статистика", callback_data="broadcast_stats")
    )
    keyboard.row(
        InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_main")
    )

    await callback.message.edit_text(text, reply_markup=keyboard.as_markup())
    await callback.answer()


@main_bot_router.callback_query(F.data == "broadcast_create")
async def broadcast_create_callback(callback: CallbackQuery, state: FSMContext):
    """Начать создание рассылки"""
    if not is_admin_user(callback.from_user.id):
        await callback.answer("Доступ запрещен")
        return

    text = (
        f"📝 СОЗДАНИЕ РАССЫЛКИ\n\n"
        f"Отправьте сообщение, которое хотите разослать:\n\n"
        f"📎 Поддерживается:\n"
        f"• Текст\n"
        f"• Фото с подписью\n"
        f"• Видео с подписью\n"
        f"• Документы\n\n"
        f"⚠️ После отправки сообщения начнется рассылка!"
    )

    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(text="❌ Отменить", callback_data="admin_broadcast"))

    await callback.message.edit_text(text, reply_markup=keyboard.as_markup())
    await state.set_state(AdminChannelStates.waiting_for_broadcast_message)
    await callback.answer()


@main_bot_router.callback_query(F.data == "broadcast_stats")
async def broadcast_stats_callback(callback: CallbackQuery):
    """Детальная статистика рассылки"""
    if not is_admin_user(callback.from_user.id):
        await callback.answer("Доступ запрещен")
        return

    bots = await get_all_active_bots()
    stats = await get_broadcast_stats()

    text = f"📊 ДЕТАЛЬНАЯ СТАТИСТИКА РАССЫЛКИ\n\n"
    text += f"🤖 Активных ботов: {stats['active_bots']}\n"
    text += f"👥 Всего пользователей: {stats['total_users']}\n\n"

    if bots:
        text += f"📋 Список активных ботов:\n"
        for i, bot in enumerate(bots[:10], 1):  # Показываем первые 10
            text += f"{i}. @{bot['username']}\n"

        if len(bots) > 10:
            text += f"... и еще {len(bots) - 10} ботов\n"

    text += f"\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_broadcast"))

    await callback.message.edit_text(text, reply_markup=keyboard.as_markup())
    await callback.answer()


def extract_keyboard_from_message(message: Message) -> InlineKeyboardMarkup | None:
    """Habardan keyboard ni ajratib olish"""
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

                    # Button properties
                    button_data = {"text": btn.text}

                    # Button type ni aniqlash
                    if hasattr(btn, 'url') and btn.url:
                        button_data["url"] = btn.url
                        logger.info(f"  - URL button: {btn.url}")
                        new_btn = InlineKeyboardButton(text=btn.text, url=btn.url)
                    elif hasattr(btn, 'callback_data') and btn.callback_data:
                        button_data["callback_data"] = btn.callback_data
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


# JSON debug function
def log_message_structure(message: Message):
    """Habar strukturasini JSON formatda log qilish"""
    try:
        # Message ni dict ga aylantirish
        msg_dict = message.model_dump() if hasattr(message, 'model_dump') else message.__dict__

        # Faqat kerakli qismlarni olish
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

        logger.info(f"MESSAGE STRUCTURE: {json.dumps(debug_data, indent=2, ensure_ascii=False)}")

    except Exception as e:
        logger.error(f"Error logging message structure: {e}")


@main_bot_router.message(AdminChannelStates.waiting_for_broadcast_message)
async def process_broadcast_message(message: Message, state: FSMContext, bot: Bot):
    """Обработка сообщения для рассылки с извлечением кнопок"""
    if not is_admin_user(message.from_user.id):
        await message.answer("Доступ запрещен")
        await state.clear()
        return

    try:
        # Debug: habar strukturasini log qilish
        log_message_structure(message)

        # Debug info
        logger.info(f"Starting broadcast from admin {message.from_user.id}")
        logger.info(f"Message ID: {message.message_id}, Chat ID: {message.chat.id}")
        logger.info(f"Message type: {message.content_type}")

        # Keyboard ni ajratib olish
        extracted_keyboard = extract_keyboard_from_message(message)
        has_keyboard = extracted_keyboard is not None

        logger.info(f"Keyboard extraction result: {has_keyboard}")
        if has_keyboard:
            logger.info(f"Extracted keyboard with {len(extracted_keyboard.inline_keyboard)} rows")

        # Получаем всех активных ботов
        active_bots = await get_all_active_bots()
        logger.info(f"Found {len(active_bots)} active bots")

        if not active_bots:
            await message.answer(
                "❌ Нет активных ботов для рассылки\n\n"
                "Используйте /admin чтобы вернуться в панель"
            )
            await state.clear()
            return

        # Получаем всех пользователей
        all_users = await get_all_bot_users()
        logger.info(f"Found {len(all_users)} total users")

        if not all_users:
            await message.answer(
                "❌ Нет пользователей для рассылки\n\n"
                "Используйте /admin чтобы вернуться в панель"
            )
            await state.clear()
            return

        # Показываем информацию о рассылке
        keyboard_status = f"с кнопками ✅ ({len(extracted_keyboard.inline_keyboard)} рядов)" if has_keyboard else "без кнопок ⚠️"
        stats_msg = await message.answer(
            f"🚀 НАЧИНАЮ РАССЫЛКУ...\n\n"
            f"📊 Статистика:\n"
            f"🤖 Ботов: {len(active_bots)}\n"
            f"👥 Пользователей: {len(all_users)}\n"
            f"📝 Тип сообщения: {message.content_type} ({keyboard_status})\n\n"
            f"⏳ Прогресс: 0/{len(all_users)} (0%)\n"
            f"✅ Успешно: 0\n"
            f"❌ Ошибок: 0"
        )

        # Счетчики
        sent_count = 0
        error_count = 0
        total_count = len(all_users)

        # Счетчики ошибок по типам
        chat_not_found_count = 0
        bot_blocked_count = 0
        other_errors_count = 0

        # Группируем пользователей по ботам
        users_by_bot = {}
        for user in all_users:
            bot_token = user['bot__token']
            if bot_token not in users_by_bot:
                users_by_bot[bot_token] = []
            users_by_bot[bot_token].append(user['uid'])

        logger.info(f"Users grouped by {len(users_by_bot)} bots")

        # Отправляем через каждого бота
        for bot_index, (bot_token, user_ids) in enumerate(users_by_bot.items(), 1):
            try:
                logger.info(f"Processing bot {bot_index}/{len(users_by_bot)}: token ending with ...{bot_token[-10:]}")
                logger.info(f"Bot has {len(user_ids)} users")

                # Создаем экземпляр бота
                from aiogram import Bot
                from modul.loader import bot_session

                async with Bot(token=bot_token, session=bot_session).context(auto_close=False) as broadcast_bot:

                    # Проверяем сам бот
                    try:
                        bot_info = await broadcast_bot.get_me()
                        logger.info(f"Broadcasting via bot @{bot_info.username}")
                    except Exception as e:
                        logger.error(f"Cannot access bot with token ...{bot_token[-10:]}: {e}")
                        error_count += len(user_ids)
                        continue

                    for user_index, user_id in enumerate(user_ids, 1):
                        try:
                            # Debug для первых 3 пользователей каждого бота
                            if user_index <= 3:
                                logger.info(f"Sending to user {user_id} via bot @{bot_info.username}")

                            result = None

                            # Отправляем сообщение в зависимости от типа
                            if message.content_type == "text":
                                # Текстовое сообщение с извлеченными кнопками
                                result = await broadcast_bot.send_message(
                                    chat_id=user_id,
                                    text=message.text,
                                    entities=getattr(message, 'entities', None),
                                    reply_markup=extracted_keyboard,  # ✅ Извлеченные кнопки
                                    parse_mode=None
                                )

                            elif message.content_type == "photo":
                                # Фото с подписью и извлеченными кнопками
                                try:
                                    file = await bot.get_file(message.photo[-1].file_id)
                                    file_data = await bot.download_file(file.file_path)

                                    from aiogram.types import BufferedInputFile
                                    input_file = BufferedInputFile(file_data.read(), filename="photo.jpg")

                                    result = await broadcast_bot.send_photo(
                                        chat_id=user_id,
                                        photo=input_file,
                                        caption=getattr(message, 'caption', None),
                                        caption_entities=getattr(message, 'caption_entities', None),
                                        reply_markup=extracted_keyboard  # ✅ Извлеченные кнопки
                                    )
                                except Exception as photo_error:
                                    logger.error(f"Error processing photo for user {user_id}: {photo_error}")
                                    raise photo_error

                            elif message.content_type == "video":
                                # Видео с подписью и извлеченными кнопками
                                try:
                                    file = await bot.get_file(message.video.file_id)
                                    file_data = await bot.download_file(file.file_path)

                                    from aiogram.types import BufferedInputFile
                                    input_file = BufferedInputFile(file_data.read(), filename="video.mp4")

                                    result = await broadcast_bot.send_video(
                                        chat_id=user_id,
                                        video=input_file,
                                        caption=getattr(message, 'caption', None),
                                        caption_entities=getattr(message, 'caption_entities', None),
                                        reply_markup=extracted_keyboard  # ✅ Извлеченные кнопки
                                    )
                                except Exception as video_error:
                                    logger.error(f"Error processing video for user {user_id}: {video_error}")
                                    raise video_error

                            elif message.content_type == "document":
                                # Документ с извлеченными кнопками
                                try:
                                    file = await bot.get_file(message.document.file_id)
                                    file_data = await bot.download_file(file.file_path)

                                    from aiogram.types import BufferedInputFile
                                    filename = getattr(message.document, 'file_name', 'document')
                                    input_file = BufferedInputFile(file_data.read(), filename=filename)

                                    result = await broadcast_bot.send_document(
                                        chat_id=user_id,
                                        document=input_file,
                                        caption=getattr(message, 'caption', None),
                                        caption_entities=getattr(message, 'caption_entities', None),
                                        reply_markup=extracted_keyboard  # ✅ Извлеченные кнопки
                                    )
                                except Exception as doc_error:
                                    logger.error(f"Error processing document for user {user_id}: {doc_error}")
                                    raise doc_error

                            elif message.content_type == "audio":
                                # Аудио с извлеченными кнопками
                                try:
                                    file = await bot.get_file(message.audio.file_id)
                                    file_data = await bot.download_file(file.file_path)

                                    from aiogram.types import BufferedInputFile
                                    filename = getattr(message.audio, 'file_name', 'audio.mp3')
                                    input_file = BufferedInputFile(file_data.read(), filename=filename)

                                    result = await broadcast_bot.send_audio(
                                        chat_id=user_id,
                                        audio=input_file,
                                        caption=getattr(message, 'caption', None),
                                        caption_entities=getattr(message, 'caption_entities', None),
                                        reply_markup=extracted_keyboard  # ✅ Извлеченные кнопки
                                    )
                                except Exception as audio_error:
                                    logger.error(f"Error processing audio for user {user_id}: {audio_error}")
                                    raise audio_error

                            elif message.content_type == "voice":
                                # Голосовое сообщение с извлеченными кнопками
                                try:
                                    file = await bot.get_file(message.voice.file_id)
                                    file_data = await bot.download_file(file.file_path)

                                    from aiogram.types import BufferedInputFile
                                    input_file = BufferedInputFile(file_data.read(), filename="voice.ogg")

                                    result = await broadcast_bot.send_voice(
                                        chat_id=user_id,
                                        voice=input_file,
                                        caption=getattr(message, 'caption', None),
                                        caption_entities=getattr(message, 'caption_entities', None),
                                        reply_markup=extracted_keyboard  # ✅ Извлеченные кнопки
                                    )
                                except Exception as voice_error:
                                    logger.error(f"Error processing voice for user {user_id}: {voice_error}")
                                    raise voice_error

                            elif message.content_type == "video_note":
                                # Кружок (video note) с извлеченными кнопками
                                try:
                                    file = await bot.get_file(message.video_note.file_id)
                                    file_data = await bot.download_file(file.file_path)

                                    from aiogram.types import BufferedInputFile
                                    input_file = BufferedInputFile(file_data.read(), filename="video_note.mp4")

                                    result = await broadcast_bot.send_video_note(
                                        chat_id=user_id,
                                        video_note=input_file,
                                        reply_markup=extracted_keyboard  # ✅ Извлеченные кнопки
                                    )
                                except Exception as vn_error:
                                    logger.error(f"Error processing video_note for user {user_id}: {vn_error}")
                                    raise vn_error

                            elif message.content_type == "animation":
                                # GIF/анимация с извлеченными кнопками
                                try:
                                    file = await bot.get_file(message.animation.file_id)
                                    file_data = await bot.download_file(file.file_path)

                                    from aiogram.types import BufferedInputFile
                                    filename = getattr(message.animation, 'file_name', 'animation.gif')
                                    input_file = BufferedInputFile(file_data.read(), filename=filename)

                                    result = await broadcast_bot.send_animation(
                                        chat_id=user_id,
                                        animation=input_file,
                                        caption=getattr(message, 'caption', None),
                                        caption_entities=getattr(message, 'caption_entities', None),
                                        reply_markup=extracted_keyboard  # ✅ Извлеченные кнопки
                                    )
                                except Exception as gif_error:
                                    logger.error(f"Error processing animation for user {user_id}: {gif_error}")
                                    raise gif_error

                            elif message.content_type == "sticker":
                                # Стикер с извлеченными кнопками
                                try:
                                    result = await broadcast_bot.send_sticker(
                                        chat_id=user_id,
                                        sticker=message.sticker.file_id,  # Стикеры можно отправлять по file_id
                                        reply_markup=extracted_keyboard  # ✅ Извлеченные кнопки
                                    )
                                except Exception as sticker_error:
                                    logger.error(f"Error processing sticker for user {user_id}: {sticker_error}")
                                    raise sticker_error

                            elif message.content_type == "location":
                                # Местоположение с извлеченными кнопками
                                try:
                                    result = await broadcast_bot.send_location(
                                        chat_id=user_id,
                                        latitude=message.location.latitude,
                                        longitude=message.location.longitude,
                                        reply_markup=extracted_keyboard  # ✅ Извлеченные кнопки
                                    )
                                except Exception as location_error:
                                    logger.error(f"Error processing location for user {user_id}: {location_error}")
                                    raise location_error

                            elif message.content_type == "contact":
                                # Контакт с извлеченными кнопками
                                try:
                                    result = await broadcast_bot.send_contact(
                                        chat_id=user_id,
                                        phone_number=message.contact.phone_number,
                                        first_name=message.contact.first_name,
                                        last_name=getattr(message.contact, 'last_name', None),
                                        reply_markup=extracted_keyboard  # ✅ Извлеченные кнопки
                                    )
                                except Exception as contact_error:
                                    logger.error(f"Error processing contact for user {user_id}: {contact_error}")
                                    raise contact_error

                            elif message.content_type == "poll":
                                # Опрос с извлеченными кнопками
                                try:
                                    result = await broadcast_bot.send_poll(
                                        chat_id=user_id,
                                        question=message.poll.question,
                                        options=[option.text for option in message.poll.options],
                                        is_anonymous=message.poll.is_anonymous,
                                        type=message.poll.type,
                                        allows_multiple_answers=getattr(message.poll, 'allows_multiple_answers', False),
                                        reply_markup=extracted_keyboard  # ✅ Извлеченные кнопки
                                    )
                                except Exception as poll_error:
                                    logger.error(f"Error processing poll for user {user_id}: {poll_error}")
                                    raise poll_error

                            else:
                                # Неподдерживаемые типы - текстовый fallback с кнопками
                                logger.warning(f"Unsupported content type: {message.content_type}")
                                result = await broadcast_bot.send_message(
                                    chat_id=user_id,
                                    text=f"📎 МЕДИА СООБЩЕНИЕ\n\nОригинальное сообщение содержало: {message.content_type.upper()}\n\n⚠️ Данный тип медиа не поддерживается для рассылки",
                                    reply_markup=extracted_keyboard  # ✅ Извлеченные кнопки
                                )

                            # Проверяем результат
                            if result and hasattr(result, 'message_id') and result.message_id:
                                sent_count += 1
                                if user_index <= 3:
                                    button_count = len(extracted_keyboard.inline_keyboard) if has_keyboard else 0
                                    total_buttons = sum(
                                        len(row) for row in extracted_keyboard.inline_keyboard) if has_keyboard else 0
                                    logger.info(
                                        f"✅ SUCCESS: User {user_id} received message {result.message_id} via @{bot_info.username} (keyboard: {button_count} rows, {total_buttons} buttons)")
                            else:
                                error_count += 1
                                other_errors_count += 1
                                logger.error(
                                    f"❌ FAILED: User {user_id} - no valid result returned via @{bot_info.username}")

                        except Exception as e:
                            error_count += 1
                            error_text = str(e).lower()

                            # Классифицируем ошибки
                            if "chat not found" in error_text:
                                chat_not_found_count += 1
                            elif "blocked" in error_text:
                                bot_blocked_count += 1
                            else:
                                other_errors_count += 1

                            if error_count <= 10:
                                logger.error(f"❌ EXCEPTION: User {user_id} via @{bot_info.username}: {e}")

                        # Задержка между сообщениями
                        if user_index % 20 == 0:
                            import asyncio
                            await asyncio.sleep(0.1)

                        # Обновляем прогресс
                        if (sent_count + error_count) % 100 == 0:
                            progress = ((sent_count + error_count) / total_count) * 100
                            try:
                                await stats_msg.edit_text(
                                    f"🚀 РАССЫЛКА В ПРОЦЕССЕ...\n\n"
                                    f"📊 Статистика:\n"
                                    f"🤖 Ботов: {len(active_bots)}\n"
                                    f"👥 Пользователей: {total_count}\n"
                                    f"📝 Тип: {message.content_type} ({keyboard_status})\n\n"
                                    f"⏳ Прогресс: {sent_count + error_count}/{total_count} ({progress:.1f}%)\n"
                                    f"✅ Успешно: {sent_count}\n"
                                    f"❌ Ошибок: {error_count}"
                                )
                            except:
                                pass

            except Exception as e:
                logger.error(f"Error with bot token ...{bot_token[-10:]}: {e}")
                error_count += len(user_ids)
                other_errors_count += len(user_ids)

        # Финальная статистика
        success_rate = (sent_count / total_count) * 100 if total_count > 0 else 0

        final_text = (
            f"✅ РАССЫЛКА ЗАВЕРШЕНА!\n\n"
            f"📊 Итоговая статистика:\n"
            f"🤖 Ботов использовано: {len(active_bots)}\n"
            f"👥 Всего пользователей: {total_count}\n"
            f"📝 Тип: {message.content_type} ({keyboard_status})\n"
            f"✅ Успешно доставлено: {sent_count}\n"
            f"❌ Ошибок доставки: {error_count}\n"
            f"📈 Успешность: {success_rate:.1f}%\n\n"
            f"🔍 Детали ошибок:\n"
            f"• Чат не найден: {chat_not_found_count}\n"
            f"• Бот заблокирован: {bot_blocked_count}\n"
            f"• Прочие ошибки: {other_errors_count}\n\n"
            f"👤 Администратор: {message.from_user.full_name}\n"
            f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )

        await stats_msg.edit_text(final_text)

        logger.info(f"Broadcast completed: {sent_count} sent, {error_count} errors, extracted keyboard: {has_keyboard}")

        await state.clear()

    except Exception as e:
        logger.error(f"Error in broadcast: {e}")
        await message.answer(
            f"❌ Ошибка при рассылке: {str(e)}\n\n"
            f"Используйте /admin чтобы вернуться в панель"
        )
        await state.clear()

async def notify_admins_about_broadcast(bot, admin_name, admin_id, sent_count, error_count, total_count):
    """Уведомить других админов о рассылке"""
    try:
        success_rate = (sent_count / total_count) * 100 if total_count > 0 else 0

        text = (
            f"📣 РАССЫЛКА ВЫПОЛНЕНА\n\n"
            f"👤 Администратор: {admin_name} ({admin_id})\n"
            f"📊 Результат:\n"
            f"✅ Доставлено: {sent_count}\n"
            f"❌ Ошибок: {error_count}\n"
            f"📈 Успешность: {success_rate:.1f}%\n"
            f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )

        for aid in ADMIN_IDS:
            if aid != admin_id:
                try:
                    await bot.send_message(aid, text)
                except:
                    pass
    except Exception as e:
        logger.error(f"Error notifying admins about broadcast: {e}")

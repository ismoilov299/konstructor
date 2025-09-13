
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from modul.bot.main_bot.handlers.admin_panel import is_admin_user
from modul.bot.main_bot.services.user_service import (
    get_user_bots, get_bot_statistics, toggle_bot_status,
    update_bot_modules, delete_bot
)
from modul.bot.main_bot.states import ManageBotStates
from modul.models import Bot

from datetime import datetime, timedelta
from django.db.models import Count, Q, Sum
from django.utils import timezone
from asgiref.sync import sync_to_async

logger = logging.getLogger(__name__)

manage_bots_router = Router()


# Keyboard funksiyalari
async def bot_list_keyboard(user_bots):
    """Клавиатура списка ботов"""
    buttons = []

    for bot in user_bots:
        status = "🟢" if bot.get('bot_enable', False) else "🔴"
        modules_count = sum([
            bot.get('enable_refs', False),
            bot.get('enable_leo', False),
            bot.get('enable_asker', False),
            bot.get('enable_kino', False),
            bot.get('enable_download', False),
            bot.get('enable_chatgpt', False)
        ])

        button_text = f"{status} @{bot['username']} "
        buttons.append([InlineKeyboardButton(
            text=button_text,
            callback_data=f"manage_bot:{bot['id']}"
        )])

    # Дополнительные кнопки
    buttons.append([InlineKeyboardButton(text="➕ Создать новый бот", callback_data="create_bot")])
    buttons.append([InlineKeyboardButton(text="📊 Общая статистика", callback_data="overall_stats")])
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


async def bot_management_keyboard(bot_id, is_active=True):
    """Клавиатура управления ботом"""
    buttons = [
        [InlineKeyboardButton(text="📊 Статистика", callback_data=f"bot_stats:{bot_id}")],
        # [InlineKeyboardButton(text="🔧 Модули", callback_data=f"edit_modules:{bot_id}")],
        # [InlineKeyboardButton(text="⚙️ Настройки", callback_data=f"bot_settings:{bot_id}")],
        [
            # InlineKeyboardButton(
            #     text="🔴 Выключить" if is_active else "🟢 Включить",
            #     callback_data=f"toggle_bot:{bot_id}"
            # ),
            InlineKeyboardButton(
                text="🗑️ Удалить",
                callback_data=f"delete_bot:{bot_id}"
            )
        ],
        [InlineKeyboardButton(text="◀️ Мои боты", callback_data="my_bots")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


async def bot_modules_edit_keyboard(bot_id, current_modules):
    """Клавиатура редактирования модулей бота"""
    modules = [
        ("refs", "Реферальный 👥"),
        ("leo", "Дайвинчик 💞"),
        ("asker", "Asker Бот 💬"),
        ("kino", "Кинотеатр 🎥"),
        ("download", "DownLoader 💾"),
        ("chatgpt", "ChatGPT 💡")
    ]

    buttons = []
    row = []
    for i, (module_key, module_name) in enumerate(modules):
        icon = "✅" if current_modules.get(f'enable_{module_key}', False) else "⬜"
        text = f"{icon} {module_name}"
        row.append(InlineKeyboardButton(
            text=text,
            callback_data=f"toggle_module:{bot_id}:{module_key}"
        ))

        # Добавляем по 2 кнопки в ряд
        if len(row) == 2 or i == len(modules) - 1:
            buttons.append(row)
            row = []

    buttons.append([InlineKeyboardButton(text="💾 Сохранить", callback_data=f"save_modules:{bot_id}")])
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data=f"manage_bot:{bot_id}")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


async def confirm_delete_keyboard(bot_id):
    """Клавиатура подтверждения удаления бота"""
    buttons = [
        [
            InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"confirm_delete:{bot_id}"),
            InlineKeyboardButton(text="❌ Нет, отменить", callback_data=f"manage_bot:{bot_id}")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# Handler'lar
@manage_bots_router.callback_query(F.data == "my_bots")
async def show_my_bots(callback: CallbackQuery):
    """Показать боты пользователя"""
    try:
        user_bots = await get_user_bots(callback.from_user.id)

        if not user_bots:
            await callback.message.edit_text(
                "🤖 <b>У вас пока нет ботов</b>\n\n"
                "🚀 <b>Создайте своего первого бота!</b>\n"
                "Создание бота очень простое:\n"
                "• Получите токен от @BotFather\n"
                "• Выберите нужные модули\n"
                "• Готово за 2-3 минуты!\n\n"
                "💡 <b>Доступно 6 профессиональных ботов:</b>\n"
                "👥 Реферальный, 💞 Дайвинчик, 💬 Asker Бот,\n"
                "🎥 Кинотеатр, 💾 DownLoader, 💡 ChatGPT",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="➕ Создать первый бот", callback_data="create_bot")],
                    [InlineKeyboardButton(text="❓ Помощь", callback_data="help")],
                    [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main")]
                ]),
                parse_mode="HTML"
            )
            await callback.answer()
            return

        # Статистика ботов
        total_bots = len(user_bots)
        active_bots = sum(1 for bot in user_bots if bot.get('bot_enable', False))
        total_modules = sum(
            sum([
                bot.get('enable_refs', False),
                bot.get('enable_leo', False),
                bot.get('enable_asker', False),
                bot.get('enable_kino', False),
                bot.get('enable_download', False),
                bot.get('enable_chatgpt', False)
            ]) for bot in user_bots
        )

        text = (
            f"🤖 <b>Ваши боты</b>\n\n"
            f"📊 <b>Общая информация:</b>\n"
            f"• Всего ботов: {total_bots}\n"
            f"• Активных ботов: {active_bots}\n"
            # f"• Всего модулей: {total_modules}\n\n"
            f"📋 <b>Список ботов:</b>\n"
            f"Нажмите на бот для управления ↓"
        )

        await callback.message.edit_text(
            text,
            reply_markup=await bot_list_keyboard(user_bots),
            parse_mode="HTML"
        )

    except Exception as e:
        logger.error(f"Error showing user bots for {callback.from_user.id}: {e}")
        await callback.message.edit_text(
            "❌ <b>Ошибка при загрузке ботов</b>\n\n"
            "Это может быть временная техническая проблема.\n"
            "Пожалуйста, попробуйте еще раз.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Попробовать снова", callback_data="my_bots")],
                [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main")]
            ]),
            parse_mode="HTML"
        )

    await callback.answer()


@manage_bots_router.callback_query(F.data.startswith("manage_bot:"))
async def manage_specific_bot(callback: CallbackQuery):
    """Управление конкретным ботом"""
    try:
        bot_id = int(callback.data.split(":")[1])
        bot_stats = await get_bot_statistics(bot_id)

        if not bot_stats:
            await callback.message.edit_text(
                "❌ <b>Бот не найден</b>\n\n"
                "Этот бот вам не принадлежит или был удален.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="◀️ Мои боты", callback_data="my_bots")]
                ]),
                parse_mode="HTML"
            )
            await callback.answer()
            return

        # Список включенных модулей
        enabled_modules = []
        module_names = {
            'enable_refs': '👥 Реферальный',
            'enable_leo': '💞 Дайвинчик',
            'enable_asker': '💬 Asker Бот',
            'enable_kino': '🎥 Кинотеатр',
            'enable_download': '💾 DownLoader',
            'enable_chatgpt': '💡 ChatGPT'
        }

        for key, name in module_names.items():
            if bot_stats.get(key, False):
                enabled_modules.append(name)

        modules_text = ", ".join(enabled_modules) if enabled_modules else "Ни один модуль не включен"

        # Статус активности
        activity_icon = "🟢" if bot_stats['is_active'] else "🔴"
        activity_text = "Активен" if bot_stats['is_active'] else "Выключен"

        # Рост пользователей
        growth_text = ""
        if bot_stats['new_users'] > 0:
            growth_text = f"📈 +{bot_stats['new_users']} (24 часа)"

        text = (
            f"⚙️ <b>Управление ботом</b>\n\n"
            f"🤖 <b>@{bot_stats['bot_username']}</b>\n"
            f"{activity_icon} <b>Статус:</b> {activity_text}\n\n"
            f"👥 <b>Пользователи:</b>\n"
            f"• Всего: {bot_stats['total_users']}\n"
            f"• Активных (7 дней): {bot_stats['active_users']}\n"
            f"• Новых (24 часа): {bot_stats['new_users']}\n\n"
            f"🔧 <b>Модули:</b>\n"
            f"{modules_text}\n\n"
            f"🔗 <b>Ссылка:</b> https://t.me/{bot_stats['bot_username']}\n\n"
            f"Выберите нужное действие:"
        )

        await callback.message.edit_text(
            text,
            reply_markup=await bot_management_keyboard(bot_id, bot_stats['is_active']),
            parse_mode="HTML"
        )

    except Exception as e:
        logger.error(f"Error managing bot for {callback.from_user.id}: {e}")
        await callback.message.edit_text(
            "❌ <b>Ошибка при загрузке данных бота</b>\n\n"
            "Пожалуйста, попробуйте еще раз.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Мои боты", callback_data="my_bots")]
            ]),
            parse_mode="HTML"
        )

    await callback.answer()


@manage_bots_router.callback_query(F.data.startswith("bot_stats:"))
async def show_bot_detailed_stats(callback: CallbackQuery):
    """Подробная статистика бота"""
    try:
        bot_id = int(callback.data.split(":")[1])
        bot_stats = await get_bot_statistics(bot_id)

        if not bot_stats:
            await callback.answer("❌ Бот не найден!", show_alert=True)
            return

        # Расчет роста
        total_users = bot_stats['total_users']
        new_users = bot_stats['new_users']
        active_users = bot_stats['active_users']

        # Процент активности
        activity_percentage = (active_users / total_users * 100) if total_users > 0 else 0

        # Статус
        status_icon = "🟢" if bot_stats['is_active'] else "🔴"
        status_text = "Активен" if bot_stats['is_active'] else "Неактивен"

        text = (
            f"📊 <b>Статистика @{bot_stats['bot_username']}</b>\n\n"
            f"{status_icon} <b>Статус:</b> {status_text}\n\n"
            f"👥 <b>Пользователи:</b>\n"
            f"• Всего: {total_users}\n"
            f"• Активных (7 дней): {active_users} ({activity_percentage:.1f}%)\n"
            f"• Новых (24 часа): {new_users}\n\n"
            f"📈 <b>Показатель активности:</b>\n"
            f"{'▓' * int(activity_percentage // 10)}{'░' * (10 - int(activity_percentage // 10))} {activity_percentage:.1f}%\n\n"
            f"🔧 <b>Включенные модули:</b>\n"
        )

        # Статистика модулей
        module_names = {
            'enable_refs': '👥 Реферальный',
            'enable_leo': '💞 Дайвинчик',
            'enable_asker': '💬 Asker Бот',
            'enable_kino': '🎥 Кинотеатр',
            'enable_download': '💾 DownLoader',
            'enable_chatgpt': '💡 ChatGPT'
        }

        enabled_count = 0
        for key, name in module_names.items():
            if bot_stats.get(key, False):
                text += f"• ✅ {name}\n"
                enabled_count += 1

        if enabled_count == 0:
            text += "• ❌ Ни один модуль не включен\n"

        text += f"\n📅 <b>Последнее обновление:</b> {datetime.now().strftime('%d.%m.%Y %H:%M')}"

        await callback.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Обновить", callback_data=f"bot_stats:{bot_id}")],
                [InlineKeyboardButton(text="📈 Посмотреть график", callback_data=f"bot_chart:{bot_id}")],
                [InlineKeyboardButton(text="◀️ Назад", callback_data=f"manage_bot:{bot_id}")]
            ]),
            parse_mode="HTML"
        )

    except Exception as e:
        logger.error(f"Error showing bot stats: {e}")
        await callback.answer("❌ Ошибка при загрузке статистики!", show_alert=True)


@manage_bots_router.callback_query(F.data.startswith("edit_modules:"))
async def edit_bot_modules(callback: CallbackQuery):
    """Редактирование модулей бота"""
    try:
        bot_id = int(callback.data.split(":")[1])
        bot_stats = await get_bot_statistics(bot_id)

        if not bot_stats:
            await callback.answer("❌ Бот не найден!", show_alert=True)
            return

        text = (
            f"🔧 <b>Редактирование ботов @{bot_stats['bot_username']}</b>\n\n"
            f"Следующие модули можно включить/выключить:\n"
            f"Каждый модуль добавляет отдельную функцию в ваш бот.\n\n"
            f"✅ Включенные модули\n"
            f"⬜ Выключенные модули\n\n"
            f"Нажмите на модуль для изменения:"
        )

        await callback.message.edit_text(
            text,
            reply_markup=await bot_modules_edit_keyboard(bot_id, bot_stats),
            parse_mode="HTML"
        )

    except Exception as e:
        logger.error(f"Error editing bot modules: {e}")
        await callback.answer("❌ Произошла ошибка!", show_alert=True)


@manage_bots_router.callback_query(F.data.startswith("toggle_module:"))
async def toggle_bot_module(callback: CallbackQuery):
    """Включение/выключение модуля бота"""
    try:
        _, bot_id, module_name = callback.data.split(":")
        bot_id = int(bot_id)

        # Получить текущие модули
        bot_stats = await get_bot_statistics(bot_id)
        if not bot_stats:
            await callback.answer("❌ Бот не найден!", show_alert=True)
            return

        # Переключить модуль
        current_value = bot_stats.get(f'enable_{module_name}', False)
        new_modules = {module_name: not current_value}

        success = await update_bot_modules(bot_id, callback.from_user.id, new_modules)

        if success:
            module_names = {
                'refs': 'Реферальный',
                'leo': 'Дайвинчик',
                'asker': 'Asker Бот',
                'kino': 'Кинотеатр',
                'download': 'DownLoader',
                'chatgpt': 'ChatGPT'
            }

            module_display = module_names.get(module_name, module_name)
            status = "включен" if not current_value else "выключен"

            await callback.answer(f"✅ {module_display} {status}")

            # Обновить страницу редактирования модулей
            await edit_bot_modules(callback)
        else:
            await callback.answer("❌ Ошибка при изменении состояния модуля!", show_alert=True)

    except Exception as e:
        logger.error(f"Error toggling bot module: {e}")
        await callback.answer("❌ Произошла ошибка!", show_alert=True)


@manage_bots_router.callback_query(F.data.startswith("toggle_bot:"))
async def toggle_bot_status_handler(callback: CallbackQuery):
    """Включение/выключение статуса бота"""
    try:
        bot_id = int(callback.data.split(":")[1])
        new_status = await toggle_bot_status(bot_id, callback.from_user.id)

        if new_status is None:
            await callback.answer("❌ Бот не найден или вам не принадлежит!", show_alert=True)
            return

        status_text = "включен" if new_status else "выключен"
        status_icon = "🟢" if new_status else "🔴"

        await callback.answer(f"{status_icon} Бот {status_text}!", show_alert=True)

        # Обновить страницу управления
        await manage_specific_bot(callback)

    except Exception as e:
        logger.error(f"Error toggling bot status: {e}")
        await callback.answer("❌ Произошла ошибка!", show_alert=True)


@manage_bots_router.callback_query(F.data.startswith("delete_bot:"))
async def request_bot_deletion(callback: CallbackQuery):
    """Запрос удаления бота"""
    try:
        bot_id = int(callback.data.split(":")[1])
        bot_stats = await get_bot_statistics(bot_id)

        if not bot_stats:
            await callback.answer("❌ Бот не найден!", show_alert=True)
            return

        text = (
            f"⚠️ <b>Подтвердите удаление бота</b>\n\n"
            f"🤖 <b>Бот:</b> @{bot_stats['bot_username']}\n"
            f"👥 <b>Пользователи:</b> {bot_stats['total_users']}\n\n"
            f"❗ <b>Предупреждение:</b>\n"
            f"• Бот будет полностью удален\n"
            f"• Все данные будут потеряны\n"
            f"• Это действие нельзя отменить\n\n"
            f"Вы действительно хотите удалить?"
        )

        await callback.message.edit_text(
            text,
            reply_markup=await confirm_delete_keyboard(bot_id),
            parse_mode="HTML"
        )

    except Exception as e:
        logger.error(f"Error requesting bot deletion: {e}")
        await callback.answer("❌ Произошла ошибка!", show_alert=True)


@manage_bots_router.callback_query(F.data.startswith("confirm_delete:"))
async def confirm_bot_deletion(callback: CallbackQuery):
    """Подтверждение удаления бота"""
    try:
        bot_id = int(callback.data.split(":")[1])

        deleted_username = await delete_bot(bot_id, callback.from_user.id)

        if deleted_username:
            await callback.message.edit_text(
                f"✅ <b>Бот успешно удален</b>\n\n"
                f"🤖 <b>Удаленный бот:</b> @{deleted_username}\n\n"
                f"Все данные очищены.\n"
                f"При необходимости вы можете создать новый бот.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="➕ Создать новый бот", callback_data="create_bot")],
                    [InlineKeyboardButton(text="🤖 Мои боты", callback_data="my_bots")],
                    [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_main")]
                ]),
                parse_mode="HTML"
            )

            logger.info(f"Bot deleted: @{deleted_username} by user {callback.from_user.id}")
        else:
            await callback.answer("❌ Ошибка при удалении бота!", show_alert=True)

    except Exception as e:
        logger.error(f"Error confirming bot deletion: {e}")
        await callback.answer("❌ Произошла ошибка!", show_alert=True)



# Database query functions for specific user
@sync_to_async
def get_user_bot_statistics(user_telegram_id):
    """Foydalanuvchining botlari uchun statistika"""
    try:
        from modul.models import Bot, ClientBotUser, UserTG, User

        # Foydalanuvchini topish
        try:
            user = User.objects.get(uid=user_telegram_id)
        except User.DoesNotExist:
            return None

        # Bugungi sana
        today = timezone.now().date()
        yesterday = today - timedelta(days=1)
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)

        # Foydalanuvchining botlari
        user_bots = Bot.objects.filter(owner=user)
        total_bots = user_bots.count()
        active_bots = user_bots.filter(bot_enable=True).count()
        inactive_bots = total_bots - active_bots

        if total_bots == 0:
            return {
                'user': user,
                'total_bots': 0,
                'no_bots': True
            }

        # Foydalanuvchining botlaridagi userlar
        user_bot_clients = ClientBotUser.objects.filter(bot__owner=user)
        total_users = user_bot_clients.count()
        total_unique_users = user_bot_clients.values('user').distinct().count()

        # Bugungi yangi foydalanuvchilar
        today_new_users = user_bot_clients.filter(
            user__created_at__date=today
        ).count()

        # Kechagi yangi foydalanuvchilar
        yesterday_new_users = user_bot_clients.filter(
            user__created_at__date=yesterday
        ).count()

        # Haftalik yangi foydalanuvchilar
        week_new_users = user_bot_clients.filter(
            user__created_at__date__gte=week_ago
        ).count()

        # Oylik yangi foydalanuvchilar
        month_new_users = user_bot_clients.filter(
            user__created_at__date__gte=month_ago
        ).count()

        # Foydalanuvchining eng mashhur botlari
        top_bots = user_bots.filter(bot_enable=True).annotate(
            user_count=Count('clients')
        ).order_by('-user_count')[:5]

        # Foydalanuvchining bot turlari statistikasi
        module_stats = {
            'ChatGPT': user_bots.filter(enable_chatgpt=True, bot_enable=True).count(),
            'Download': user_bots.filter(enable_download=True, bot_enable=True).count(),
            'Leo/Davinci': user_bots.filter(Q(enable_leo=True) | Q(enable_davinci=True), bot_enable=True).count(),
            'Anon Chat': user_bots.filter(enable_anon=True, bot_enable=True).count(),
            'Referral': user_bots.filter(enable_refs=True, bot_enable=True).count(),
            'Kino': user_bots.filter(enable_kino=True, bot_enable=True).count(),
        }

        # O'sish tendentsiyasi (bugun vs kecha)
        growth_rate = 0
        if yesterday_new_users > 0:
            growth_rate = ((today_new_users - yesterday_new_users) / yesterday_new_users) * 100
        elif today_new_users > 0 and yesterday_new_users == 0:
            growth_rate = 100  # 100% o'sish agar kecha 0 bo'lsa

        # O'rtacha bot per user
        avg_users_per_bot = total_users / active_bots if active_bots > 0 else 0

        # Eng faol bot
        most_popular_bot = top_bots.first() if top_bots else None

        return {
            'user': user,
            'total_bots': total_bots,
            'active_bots': active_bots,
            'inactive_bots': inactive_bots,
            'total_users': total_users,
            'total_unique_users': total_unique_users,
            'today_new_users': today_new_users,
            'yesterday_new_users': yesterday_new_users,
            'week_new_users': week_new_users,
            'month_new_users': month_new_users,
            'top_bots': list(top_bots),
            'module_stats': module_stats,
            'growth_rate': growth_rate,
            'avg_users_per_bot': avg_users_per_bot,
            'most_popular_bot': most_popular_bot,
            'today': today.strftime('%Y-%m-%d'),
            'no_bots': False
        }

    except Exception as e:
        logger.error(f"Error getting user bot statistics for {user_telegram_id}: {e}")
        return None


@sync_to_async
def get_user_detailed_bot_stats(user_telegram_id):
    """Foydalanuvchining botlari bo'yicha batafsil statistika"""
    try:
        from modul.models import Bot, ClientBotUser, User

        # Foydalanuvchini topish
        try:
            user = User.objects.get(uid=user_telegram_id)
        except User.DoesNotExist:
            return []

        # Foydalanuvchining botlari
        bot_stats = []
        bots = Bot.objects.filter(owner=user).annotate(
            user_count=Count('clients')
        ).order_by('-user_count')

        for bot in bots:
            # Enabled modules
            enabled_modules = []
            if bot.enable_chatgpt:
                enabled_modules.append('ChatGPT')
            if bot.enable_download:
                enabled_modules.append('Download')
            if bot.enable_leo:
                enabled_modules.append('Leo')
            if bot.enable_davinci:
                enabled_modules.append('Davinci')
            if bot.enable_anon:
                enabled_modules.append('Anon')
            if bot.enable_refs:
                enabled_modules.append('Refs')
            if bot.enable_kino:
                enabled_modules.append('Kino')

            # Bugungi yangi userlar shu bot uchun
            today = timezone.now().date()
            today_users = ClientBotUser.objects.filter(
                bot=bot,
                user__created_at__date=today
            ).count()

            bot_stats.append({
                'username': bot.username,
                'user_count': bot.user_count,
                'today_users': today_users,
                'is_active': bot.bot_enable,
                'modules': enabled_modules,
                'module_count': len(enabled_modules),
                'created_date': bot.id  # Bot creation order approximation
            })

        return bot_stats

    except Exception as e:
        logger.error(f"Error getting detailed bot stats for user {user_telegram_id}: {e}")
        return []


def format_number(num):
    """Sonlarni formatlash (1000 -> 1K)"""
    if num >= 1000000:
        return f"{num / 1000000:.1f}M"
    elif num >= 1000:
        return f"{num / 1000:.1f}K"
    else:
        return str(num)


def get_growth_emoji(rate):
    """O'sish ko'rsatkichi uchun emoji"""
    if rate > 10:
        return "🚀"
    elif rate > 5:
        return "📈"
    elif rate > 0:
        return "↗️"
    elif rate == 0:
        return "➡️"
    elif rate > -5:
        return "↘️"
    else:
        return "📉"


@manage_bots_router.callback_query(F.data == "overall_stats")
async def overall_stats_callback(callback: CallbackQuery):
    """Foydalanuvchining bot statistikasini ko'rsatish"""
    try:
        # Loading message
        await callback.message.edit_text("📊 Загрузка вашей статистики...")

        user_telegram_id = callback.from_user.id

        stats = await get_user_bot_statistics(user_telegram_id)

        if not stats:
            await callback.message.edit_text(
                "❌ Ошибка при загрузке статистики.\nВозможно, вы не зарегистрированы в системе.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="⬅️ Назад", callback_data="my_bots")]
                ])
            )
            return

        if stats.get('no_bots'):
            username = stats['user'].username or stats['user'].first_name or f"User{stats['user'].uid}"
            await callback.message.edit_text(
                f"🤖 <b>Ваши боты</b>\n\n"
                f"👤 Пользователь: {username}\n"
                f"📊 У вас пока нет ботов в системе.\n\n"
                f"💡 Создайте первого бота через главное меню!",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="➕ Создать бота", callback_data="create_bot")],
                    [InlineKeyboardButton(text="⬅️ Назад", callback_data="my_bots")]
                ]),
                parse_mode="HTML"
            )
            return

        # Username olish
        username = stats['user'].username or stats['user'].first_name or f"User{stats['user'].uid}"

        # Growth emoji
        growth_emoji = get_growth_emoji(stats['growth_rate'])

        # Asosiy statistika matni
        text = f"""
👤 <b>СТАТИСТИКА ВАШИХ БОТОВ</b>
<i>Владелец: {username}</i>

🤖 <b>Ваши боты:</b>
├ Всего: {stats['total_bots']}
├ Активных: {stats['active_bots']} ✅
└ Средний охват: {stats['avg_users_per_bot']:.1f} польз/бот

👥 <b>Пользователи ваших ботов:</b>
├ Всего подключений: {format_number(stats['total_users'])}
├ Уникальных: {format_number(stats['total_unique_users'])}
├ Сегодня: +{stats['today_new_users']} {growth_emoji}
├ Вчера: +{stats['yesterday_new_users']}
├ За неделю: +{stats['week_new_users']}
└ За месяц: +{stats['month_new_users']}

📈 <b>Рост аудитории:</b>
└ {growth_emoji} {stats['growth_rate']:+.1f}% (сегодня vs вчера)

"""



        if stats['most_popular_bot']:
            text += f"\n🥇 <b>Самый популярный бот:</b>\n"
            text += f"└ @{stats['most_popular_bot'].username}: {format_number(stats['most_popular_bot'].user_count)} польз.\n"

        # Top 3 botlar
        if len(stats['top_bots']) > 1:
            text += f"\n🏆 <b>Топ ваших ботов:</b>\n"
            for i, bot in enumerate(stats['top_bots'][:3], 1):
                emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉"
                status = "✅" if bot.bot_enable else "❌"
                text += f"{emoji} @{bot.username}: {format_number(bot.user_count)} польз. {status}\n"

        text += f"\n⏰ Обновлено: {datetime.now().strftime('%H:%M:%S')}"

        # Keyboard
        keyboard = InlineKeyboardBuilder()
        keyboard.row(
            InlineKeyboardButton(text="📋 Детали по ботам", callback_data="my_detailed_stats"),
            InlineKeyboardButton(text="🔄 Обновить", callback_data="overall_stats")
        )
        keyboard.row(
            # InlineKeyboardButton(text="📊 По модулям", callback_data="my_module_stats"),
            # InlineKeyboardButton(text="📈 Графики", callback_data="my_growth_stats")
        )
        keyboard.row(
            InlineKeyboardButton(text="⬅️ Назад", callback_data="my_bots")
        )

        await callback.message.edit_text(text, reply_markup=keyboard.as_markup(), parse_mode="HTML")
        await callback.answer()

    except Exception as e:
        logger.error(f"Error in overall_stats: {e}")
        await callback.message.edit_text(
            f"❌ Ошибка при загрузке статистики:\n{str(e)}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="my_bots")]
            ])
        )
        await callback.answer()


@manage_bots_router.callback_query(F.data == "my_detailed_stats")
async def my_detailed_stats_callback(callback: CallbackQuery):
    """Foydalanuvchining botlari bo'yicha batafsil statistika"""
    try:
        await callback.message.edit_text("📋 Загрузка детальной статистики ваших ботов...")

        user_telegram_id = callback.from_user.id
        bot_stats = await get_user_detailed_bot_stats(user_telegram_id)

        if not bot_stats:
            await callback.message.edit_text(
                "❌ У вас пока нет ботов для отображения статистики",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="➕ Создать бота", callback_data="create_bot")],
                    [InlineKeyboardButton(text="⬅️ Назад", callback_data="overall_stats")]
                ])
            )
            return

        text = "📋 <b>ДЕТАЛЬНАЯ СТАТИСТИКА ВАШИХ БОТОВ</b>\n\n"

        for i, bot in enumerate(bot_stats, 1):
            modules_text = ", ".join(bot['modules']) if bot['modules'] else "Нет модулей"
            status_emoji = "✅" if bot['is_active'] else "❌"

            text += f"<b>{i}. @{bot['username']} {status_emoji}</b>\n"
            text += f"├ 👥 Всего пользователей: {format_number(bot['user_count'])}\n"
            text += f"├ 🆕 Сегодня: +{bot['today_users']}\n"
            text += f"└ 📋 {modules_text}\n\n"

        text += f"⏰ Обновлено: {datetime.now().strftime('%H:%M:%S')}"

        keyboard = InlineKeyboardBuilder()
        keyboard.row(
            InlineKeyboardButton(text="🔄 Обновить", callback_data="my_detailed_stats"),
            InlineKeyboardButton(text="⬅️ Назад", callback_data="overall_stats")
        )

        await callback.message.edit_text(text, reply_markup=keyboard.as_markup(), parse_mode="HTML")
        await callback.answer()

    except Exception as e:
        logger.error(f"Error in my_detailed_stats: {e}")
        await callback.answer("❌ Ошибка загрузки", show_alert=True)


@manage_bots_router.callback_query(F.data == "my_module_stats")
async def my_module_stats_callback(callback: CallbackQuery):
    """Foydalanuvchining modullar bo'yicha statistika"""
    try:
        await callback.message.edit_text("🧩 Загрузка статистики ваших модулей...")

        user_telegram_id = callback.from_user.id
        stats = await get_user_bot_statistics(user_telegram_id)

        if not stats or stats.get('no_bots'):
            await callback.answer("❌ У вас нет ботов", show_alert=True)
            return

        text = "🧩 <b>ВАШИ МОДУЛИ</b>\n\n"

        # Modullarni popularity bo'yicha saralash
        sorted_modules = sorted(stats['module_stats'].items(), key=lambda x: x[1], reverse=True)

        total_active_bots = stats['active_bots']

        for module, count in sorted_modules:
            if count > 0:
                percentage = (count / total_active_bots * 100) if total_active_bots > 0 else 0
                bar_length = int(percentage / 10)  # 10% = 1 блок
                bar = "█" * bar_length + "░" * (10 - bar_length)

                text += f"<b>{module}:</b>\n"
                text += f"├ Ботов: {count}\n"
                text += f"├ Процент: {percentage:.1f}%\n"
                text += f"└ {bar}\n\n"

        if total_active_bots == 0:
            text += "❌ Нет активных ботов с модулями\n"
        else:
            text += f"📊 Ваших активных ботов: {total_active_bots}\n"

        text += f"⏰ Обновлено: {datetime.now().strftime('%H:%M:%S')}"

        keyboard = InlineKeyboardBuilder()
        keyboard.row(
            InlineKeyboardButton(text="🔄 Обновить", callback_data="my_module_stats"),
            InlineKeyboardButton(text="⬅️ Назад", callback_data="overall_stats")
        )

        await callback.message.edit_text(text, reply_markup=keyboard.as_markup(), parse_mode="HTML")
        await callback.answer()

    except Exception as e:
        logger.error(f"Error in my_module_stats: {e}")
        await callback.answer("❌ Ошибка загрузки", show_alert=True)


@manage_bots_router.callback_query(F.data == "my_growth_stats")
async def my_growth_stats_callback(callback: CallbackQuery):
    """Foydalanuvchining o'sish statistikasi"""
    try:
        await callback.message.edit_text("📈 Загрузка графиков роста...")

        user_telegram_id = callback.from_user.id
        stats = await get_user_bot_statistics(user_telegram_id)

        if not stats or stats.get('no_bots'):
            await callback.answer("❌ У вас нет ботов", show_alert=True)
            return

        growth_emoji = get_growth_emoji(stats['growth_rate'])

        text = f"""
📈 <b>АНАЛИЗ РОСТА ВАШИХ БОТОВ</b>

📊 <b>Динамика пользователей:</b>
├ Сегодня: +{stats['today_new_users']} {growth_emoji}
├ Вчера: +{stats['yesterday_new_users']}
├ За неделю: +{stats['week_new_users']}
└ За месяц: +{stats['month_new_users']}

📈 <b>Показатели роста:</b>
├ Дневной рост: {stats['growth_rate']:+.1f}% {growth_emoji}
├ Недельный средний: {stats['week_new_users'] / 7:.1f} польз/день
└ Месячный средний: {stats['month_new_users'] / 30:.1f} польз/день

🎯 <b>Эффективность:</b>
├ Всего ботов: {stats['active_bots']} активных
├ Средний охват: {stats['avg_users_per_bot']:.1f} польз/бот
└ Общая аудитория: {format_number(stats['total_users'])}

💡 <b>Рекомендации:</b>
"""

        # Рекомендации на основе данных
        if stats['growth_rate'] > 10:
            text += "🚀 Отличный рост! Продолжайте в том же духе!\n"
        elif stats['growth_rate'] > 0:
            text += "📈 Стабильный рост. Рассмотрите новые модули.\n"
        else:
            text += "📉 Стоит активизировать продвижение ботов.\n"

        if stats['avg_users_per_bot'] < 10:
            text += "💡 Сосредоточьтесь на продвижении существующих ботов.\n"
        elif stats['avg_users_per_bot'] > 100:
            text += "🎯 Рассмотрите создание специализированных ботов.\n"

        text += f"\n⏰ Обновлено: {datetime.now().strftime('%H:%M:%S')}"

        keyboard = InlineKeyboardBuilder()
        keyboard.row(
            InlineKeyboardButton(text="🔄 Обновить", callback_data="my_growth_stats"),
            InlineKeyboardButton(text="⬅️ Назад", callback_data="overall_stats")
        )

        await callback.message.edit_text(text, reply_markup=keyboard.as_markup(), parse_mode="HTML")
        await callback.answer()

    except Exception as e:
        logger.error(f"Error in my_growth_stats: {e}")
        await callback.answer("❌ Ошибка загрузки", show_alert=True)


@manage_bots_router.callback_query(F.data == "owner_stats")
async def owner_stats_callback(callback: CallbackQuery):
    """Egalar bo'yicha statistika"""
    if not is_admin_user(callback.from_user.id):
        await callback.answer("Доступ запрещен", show_alert=True)
        return

    try:
        await callback.message.edit_text("👥 Загрузка статистики владельцев...")

        # Top owners query
        top_owners = await sync_to_async(lambda: list(
            Bot.objects.values(
                'owner__username',
                'owner__first_name',
                'owner__uid'
            ).annotate(
                bot_count=Count('id'),
                active_bot_count=Count('id', filter=Q(bot_enable=True)),
                total_users=Count('clients', distinct=True)
            ).order_by('-bot_count')[:10]
        ))()

        if not top_owners:
            await callback.message.edit_text(
                "❌ Нет данных о владельцах",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="⬅️ Назад", callback_data="overall_stats")]
                ])
            )
            return

        text = "👑 <b>ТОП ВЛАДЕЛЬЦЕВ БОТОВ</b>\n\n"

        for i, owner in enumerate(top_owners, 1):
            name = owner['owner__username'] or owner['owner__first_name'] or f"User{owner['owner__uid']}"
            emoji = "👑" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."

            text += f"<b>{emoji} {name}</b>\n"
            text += f"├ 🤖 Всего ботов: {owner['bot_count']}\n"
            text += f"├ ✅ Активных: {owner['active_bot_count']}\n"
            text += f"└ 👥 Пользователей: {format_number(owner['total_users'])}\n\n"

        text += f"⏰ Обновлено: {datetime.now().strftime('%H:%M:%S')}"

        keyboard = InlineKeyboardBuilder()
        keyboard.row(
            InlineKeyboardButton(text="🔄 Обновить", callback_data="owner_stats"),
            InlineKeyboardButton(text="⬅️ Назад", callback_data="overall_stats")
        )

        await callback.message.edit_text(text, reply_markup=keyboard.as_markup(), parse_mode="HTML")
        await callback.answer()

    except Exception as e:
        logger.error(f"Error in owner_stats: {e}")
        await callback.answer("❌ Ошибка загрузки", show_alert=True)
# modul/bot/main_bot/handlers/manage_bots.py
"""
Botlarni boshqarish handlerlari
"""

import logging
from datetime import datetime, timedelta
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from asgiref.sync import sync_to_async

from modul.bot.main_bot.services.user_service import (
    get_user_bots, get_bot_statistics, toggle_bot_status,
    update_bot_modules, delete_bot
)
from modul.bot.main_bot.states import ManageBotStates

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


# Placeholder handlers
@manage_bots_router.callback_query(F.data.startswith("bot_settings:"))
async def bot_settings_redirect(callback: CallbackQuery):
    """Настройки бота - перенаправление в bot_settings.py"""
    pass  # handler существует в bot_settings.py


@manage_bots_router.callback_query(F.data.startswith("bot_chart:"))
async def bot_chart_placeholder(callback: CallbackQuery):
    """Просмотр графика бота (placeholder)"""
    await callback.answer("⚠️ Эта функция еще разрабатывается...", show_alert=True)


@manage_bots_router.callback_query(F.data == "overall_stats")
async def overall_stats_placeholder(callback: CallbackQuery):
    """Общая статистика (placeholder)"""
    await callback.answer("⚠️ Эта функция еще разрабатывается...", show_alert=True)
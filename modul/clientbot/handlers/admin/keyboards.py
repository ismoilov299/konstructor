# modul/clientbot/handlers/admin/keyboards.py
"""
Admin panel keyboards
Universal admin panel uchun klaviaturalar
"""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder


class AdminKeyboards:
    """Admin panel klaviaturas"""

    @staticmethod
    async def main_menu():
        """Asosiy admin menu"""
        builder = InlineKeyboardBuilder()

        builder.button(text="👥 Управление пользователями", callback_data="admin_users")
        builder.button(text="💰 Заявки на вывод", callback_data="admin_payments")
        builder.button(text="⚙️ Настройки бота", callback_data="admin_settings")
        builder.button(text="📢 Обязательные подписки", callback_data="admin_channels")
        builder.button(text="📤 Рассылка", callback_data="admin_mailing")
        builder.button(text="📊 Статистика", callback_data="admin_statistics")
        builder.button(text="❌ Закрыть", callback_data="admin_cancel")

        builder.adjust(2, 2, 2, 1)
        return builder.as_markup()

    @staticmethod
    async def users_menu():
        """Foydalanuvchilar boshqaruvi menu"""
        builder = InlineKeyboardBuilder()

        builder.button(text="🔍 Найти пользователя", callback_data="user_search")
        builder.button(text="📊 Статистика пользователей", callback_data="user_stats")
        builder.button(text="📋 Список всех пользователей", callback_data="user_list")
        builder.button(text="🚫 Заблокированные", callback_data="user_banned")
        builder.button(text="⬅️ Назад", callback_data="admin_back")

        builder.adjust(2, 2, 1)
        return builder.as_markup()

    @staticmethod
    async def user_actions(user_id: int, is_banned: bool = False):
        """Foydalanuvchi amallar klaviaturasi"""
        builder = InlineKeyboardBuilder()

        if is_banned:
            builder.button(text="✅ Разблокировать", callback_data=f"user_unban_{user_id}")
        else:
            builder.button(text="🚫 Заблокировать", callback_data=f"user_ban_{user_id}")

        builder.button(text="💰 Изменить баланс", callback_data=f"user_balance_{user_id}")
        builder.button(text="➕ Добавить к балансу", callback_data=f"user_add_balance_{user_id}")
        builder.button(text="👥 Изменить рефералов", callback_data=f"user_refs_{user_id}")
        builder.button(text="📋 Показать рефералов", callback_data=f"user_show_refs_{user_id}")
        builder.button(text="⬅️ Назад", callback_data="admin_users")

        builder.adjust(2, 2, 2, 1)
        return builder.as_markup()

    @staticmethod
    async def payments_menu():
        """To'lovlar menu"""
        builder = InlineKeyboardBuilder()

        builder.button(text="📋 Все заявки", callback_data="payment_all")
        builder.button(text="⏳ Ожидающие", callback_data="payment_pending")
        builder.button(text="✅ Одобренные", callback_data="payment_approved")
        builder.button(text="❌ Отклоненные", callback_data="payment_rejected")
        builder.button(text="⬅️ Назад", callback_data="admin_back")

        builder.adjust(2, 2, 1)
        return builder.as_markup()

    @staticmethod
    async def payment_actions(payment_id: int):
        """To'lov amallar klaviaturasi"""
        builder = InlineKeyboardBuilder()

        builder.button(text="✅ Одобрить", callback_data=f"payment_accept_{payment_id}")
        builder.button(text="❌ Отклонить", callback_data=f"payment_decline_{payment_id}")
        builder.button(text="📝 Информация", callback_data=f"payment_info_{payment_id}")
        builder.button(text="⬅️ Назад", callback_data="admin_payments")

        builder.adjust(2, 1, 1)
        return builder.as_markup()

    @staticmethod
    async def settings_menu():
        """Sozlamalar menu"""
        builder = InlineKeyboardBuilder()

        builder.button(text="💰 Награда за реферала", callback_data="setting_ref_reward")
        builder.button(text="💳 Минимальная выплата", callback_data="setting_min_payout")
        builder.button(text="🤖 Имя бота", callback_data="setting_bot_name")
        builder.button(text="👋 Приветствие", callback_data="setting_welcome")
        builder.button(text="⬅️ Назад", callback_data="admin_back")

        builder.adjust(2, 2, 1)
        return builder.as_markup()

    @staticmethod
    async def channels_menu():
        """Kanallar menu"""
        builder = InlineKeyboardBuilder()

        builder.button(text="📋 Список каналов", callback_data="channel_list")
        builder.button(text="➕ Добавить канал", callback_data="channel_add")
        builder.button(text="❌ Удалить канал", callback_data="channel_delete")
        builder.button(text="✏️ Редактировать", callback_data="channel_edit")
        builder.button(text="⬅️ Назад", callback_data="admin_back")

        builder.adjust(2, 2, 1)
        return builder.as_markup()

    @staticmethod
    async def mailing_menu():
        """Xabar tarqatish menu"""
        builder = InlineKeyboardBuilder()

        builder.button(text="📝 Создать рассылку", callback_data="mailing_create")
        builder.button(text="📊 История рассылок", callback_data="mailing_history")
        builder.button(text="⏰ Отложенная рассылка", callback_data="mailing_scheduled")
        builder.button(text="⬅️ Назад", callback_data="admin_back")

        builder.adjust(1, 1, 1, 1)
        return builder.as_markup()

    @staticmethod
    async def statistics_menu():
        """Statistika menu"""
        builder = InlineKeyboardBuilder()

        builder.button(text="📊 Общая статистика", callback_data="stats_general")
        builder.button(text="👥 По пользователям", callback_data="stats_users")
        builder.button(text="💰 По выплатам", callback_data="stats_payments")
        builder.button(text="📈 График активности", callback_data="stats_activity")
        builder.button(text="⬅️ Назад", callback_data="admin_back")

        builder.adjust(2, 2, 1)
        return builder.as_markup()

    @staticmethod
    async def cancel_keyboard():
        """Bekor qilish klaviaturasi"""
        builder = InlineKeyboardBuilder()
        builder.button(text="❌ Отменить", callback_data="admin_cancel")
        return builder.as_markup()

    @staticmethod
    async def confirm_keyboard(action: str, item_id: str = ""):
        """Tasdiqlash klaviaturasi"""
        builder = InlineKeyboardBuilder()

        builder.button(text="✅ Да", callback_data=f"confirm_{action}_{item_id}")
        builder.button(text="❌ Нет", callback_data="admin_cancel")

        builder.adjust(2)
        return builder.as_markup()

    @staticmethod
    async def back_keyboard():
        """Orqaga qaytish klaviaturasi"""
        builder = InlineKeyboardBuilder()
        builder.button(text="⬅️ Назад", callback_data="admin_back")
        return builder.as_markup()

    @staticmethod
    async def main_menu_reply():
        """Asosiy menu reply klaviatura"""
        builder = ReplyKeyboardBuilder()

        builder.button(text="👤 Профиль")
        builder.button(text="👥 Рефералы")
        builder.button(text="💰 Вывод")
        builder.button(text="📊 Статистика")
        builder.button(text="❌ Отменить")

        builder.adjust(2, 2, 1)
        return builder.as_markup(resize_keyboard=True)

    @staticmethod
    async def cancel_reply():
        """Bekor qilish reply klaviaturasi"""
        builder = ReplyKeyboardBuilder()
        builder.button(text="❌ Отменить")
        return builder.as_markup(resize_keyboard=True)


# Shortcut functions
async def admin_menu_in():
    """Admin asosiy menu"""
    return await AdminKeyboards.main_menu()


async def cancel_bt():
    """Bekor qilish tugmasi"""
    return await AdminKeyboards.cancel_keyboard()


async def main_menu_bt():
    """Asosiy menu tugmasi"""
    return await AdminKeyboards.main_menu_reply()


async def users_menu_in():
    """Foydalanuvchilar menu"""
    return await AdminKeyboards.users_menu()


async def payments_menu_in():
    """To'lovlar menu"""
    return await AdminKeyboards.payments_menu()


async def settings_menu_in():
    """Sozlamalar menu"""
    return await AdminKeyboards.settings_menu()


async def channels_menu_in():
    """Kanallar menu"""
    return await AdminKeyboards.channels_menu()


async def user_actions_in(user_id: int, is_banned: bool = False):
    """Foydalanuvchi amallar"""
    return await AdminKeyboards.user_actions(user_id, is_banned)


async def payment_actions_in(payment_id: int):
    """To'lov amallar"""
    return await AdminKeyboards.payment_actions(payment_id)


async def confirm_in(action: str, item_id: str = ""):
    """Tasdiqlash"""
    return await AdminKeyboards.confirm_keyboard(action, item_id)


# Keyboard utilities
class KeyboardUtils:
    """Klaviatura utility funksiyalari"""

    @staticmethod
    def paginate_keyboard(items: list, page: int = 0, per_page: int = 10, callback_prefix: str = "item"):
        """Sahifalash klaviaturasi"""
        builder = InlineKeyboardBuilder()

        start_idx = page * per_page
        end_idx = start_idx + per_page
        page_items = items[start_idx:end_idx]

        for item in page_items:
            builder.button(
                text=f"{item['name']}",
                callback_data=f"{callback_prefix}_{item['id']}"
            )

        # Navigation buttons
        nav_buttons = []
        if page > 0:
            nav_buttons.append(InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data=f"page_{callback_prefix}_{page - 1}"
            ))

        if end_idx < len(items):
            nav_buttons.append(InlineKeyboardButton(
                text="Вперед ➡️",
                callback_data=f"page_{callback_prefix}_{page + 1}"
            ))

        if nav_buttons:
            builder.row(*nav_buttons)

        builder.button(text="⬅️ Назад в меню", callback_data="admin_back")

        builder.adjust(1)
        return builder.as_markup()


# Export keyboard instance
admin_keyboards = AdminKeyboards()
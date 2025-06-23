# modul/bot/main_bot/filters/admin_filter.py
"""
Bot admin tekshirish filterlari
"""

import logging
from aiogram.filters import BaseFilter
from aiogram.types import Message, CallbackQuery
from asgiref.sync import sync_to_async

from modul.models import Bot, AdminInfo, User

logger = logging.getLogger(__name__)


class IsMainBotAdminFilter(BaseFilter):
    """
    Main bot (bot yaratuvchi) admin ekanligini tekshirish
    """

    async def __call__(self, message_or_query) -> bool:
        if isinstance(message_or_query, Message):
            user_id = message_or_query.from_user.id
            bot_token = message_or_query.bot.token
        elif isinstance(message_or_query, CallbackQuery):
            user_id = message_or_query.from_user.id
            bot_token = message_or_query.bot.token
        else:
            return False

        return await self.check_admin_status(user_id, bot_token)

    @sync_to_async
    def check_admin_status(self, user_id: int, bot_token: str) -> bool:
        """
        Foydalanuvchi admin ekanligini tekshirish
        """
        try:
            # Bot egasini tekshirish
            bot = Bot.objects.filter(token=bot_token).first()
            if bot and bot.owner.uid == user_id:
                return True

            # AdminInfo dan tekshirish
            admin_info = AdminInfo.objects.filter(bot_token=bot_token).first()
            if admin_info and admin_info.admin_channel:
                # Username bo'yicha tekshirish
                user = User.objects.filter(uid=user_id).first()
                if user and user.username:
                    admin_username = admin_info.admin_channel.strip('@')
                    if admin_username == user.username:
                        return True

                # User ID bo'yicha tekshirish
                if str(user_id) in admin_info.admin_channel:
                    return True

            return False

        except Exception as e:
            logger.error(f"Error checking admin status for user {user_id}: {e}")
            return False


class IsBotOwnerFilter(BaseFilter):
    """
    Bot egasi ekanligini tekshirish
    """

    def __init__(self, bot_id: int = None):
        self.bot_id = bot_id

    async def __call__(self, message_or_query) -> bool:
        if isinstance(message_or_query, Message):
            user_id = message_or_query.from_user.id
        elif isinstance(message_or_query, CallbackQuery):
            user_id = message_or_query.from_user.id
        else:
            return False

        return await self.check_owner_status(user_id, self.bot_id)

    @sync_to_async
    def check_owner_status(self, user_id: int, bot_id: int = None) -> bool:
        """
        Bot egasi ekanligini tekshirish
        """
        try:
            if bot_id:
                bot = Bot.objects.filter(id=bot_id).first()
            else:
                # Agar bot_id berilmagan bo'lsa, user ning birorta boti borligini tekshirish
                bot = Bot.objects.filter(owner__uid=user_id).first()

            return bot and bot.owner.uid == user_id

        except Exception as e:
            logger.error(f"Error checking owner status for user {user_id}: {e}")
            return False


# Utility functions
@sync_to_async
def get_user_admin_bots(user_id: int):
    """
    Foydalanuvchi admin bo'lgan botlar ro'yxati
    """
    try:
        bots = []

        # Foydalanuvchining o'zi egasi bo'lgan botlar
        owned_bots = Bot.objects.filter(owner__uid=user_id)
        for bot in owned_bots:
            bots.append({
                'id': bot.id,
                'username': bot.username,
                'token': bot.token,
                'role': 'owner'
            })

        # Foydalanuvchi admin bo'lgan botlar (AdminInfo orqali)
        user = User.objects.filter(uid=user_id).first()
        if user and user.username:
            admin_infos = AdminInfo.objects.filter(
                admin_channel__icontains=f"@{user.username}"
            )
            for admin_info in admin_infos:
                # Allaqachon owner sifatida qo'shilmagan botlarni qo'shish
                bot = Bot.objects.filter(token=admin_info.bot_token).first()
                if bot and bot.owner.uid != user_id:
                    bots.append({
                        'id': bot.id,
                        'username': bot.username,
                        'token': bot.token,
                        'role': 'admin'
                    })

        return bots

    except Exception as e:
        logger.error(f"Error getting admin bots for user {user_id}: {e}")
        return []


@sync_to_async
def check_bot_admin_permission(user_id: int, bot_id: int, permission: str = 'read') -> bool:
    """
    Bot uchun foydalanuvchi ruxsatini tekshirish

    permission types:
    - 'read': Bot ma'lumotlarini ko'rish
    - 'write': Bot sozlamalarini o'zgartirish
    - 'admin': Admin amallarini bajarish
    - 'owner': Egaga tegishli amallar (o'chirish, transfer)
    """
    try:
        bot = Bot.objects.filter(id=bot_id).first()
        if not bot:
            return False

        # Bot egasi barcha ruxsatlarga ega
        if bot.owner.uid == user_id:
            return True

        # Admin ruxsatlari (owner emas, lekin admin)
        if permission in ['read', 'write', 'admin']:
            admin_info = AdminInfo.objects.filter(bot_token=bot.token).first()
            if admin_info and admin_info.admin_channel:
                user = User.objects.filter(uid=user_id).first()
                if user and user.username:
                    admin_username = admin_info.admin_channel.strip('@')
                    if admin_username == user.username:
                        return True

                if str(user_id) in admin_info.admin_channel:
                    return True

        # Owner ruxsatlari faqat egaga
        if permission == 'owner':
            return bot.owner.uid == user_id

        return False

    except Exception as e:
        logger.error(f"Error checking bot admin permission: {e}")
        return False


# Decorator funksiyalar
def require_bot_admin(permission: str = 'read'):
    """
    Bot admin decorator
    """

    def decorator(func):
        async def wrapper(message_or_query, *args, **kwargs):
            # Bot ID ni extract qilish
            bot_id = None
            if hasattr(message_or_query, 'data') and ':' in message_or_query.data:
                try:
                    bot_id = int(message_or_query.data.split(':')[1])
                except (ValueError, IndexError):
                    pass

            if isinstance(message_or_query, Message):
                user_id = message_or_query.from_user.id
            elif isinstance(message_or_query, CallbackQuery):
                user_id = message_or_query.from_user.id
            else:
                return

            if bot_id:
                has_permission = await check_bot_admin_permission(user_id, bot_id, permission)
                if not has_permission:
                    if isinstance(message_or_query, CallbackQuery):
                        await message_or_query.answer("❌ Sizda bu amalni bajarish uchun ruxsat yo'q!", show_alert=True)
                    else:
                        await message_or_query.answer("❌ Sizda bu amalni bajarish uchun ruxsat yo'q!")
                    return

            return await func(message_or_query, *args, **kwargs)

        return wrapper

    return decorator
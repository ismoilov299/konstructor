# modul/bot/main_bot/services/auto_admin_service.py
"""
Bot yaratilganda avtomatik admin o'rnatish servisi
"""

import logging
from asgiref.sync import sync_to_async
from django.db import transaction

from modul.models import Bot, AdminInfo, User

logger = logging.getLogger(__name__)


@sync_to_async
@transaction.atomic
def setup_auto_admin(bot_token: str, owner_uid: int, bot_username: str):
    """
    Bot yaratilgandan keyin avtomatik admin sozlamalarini o'rnatish
    """
    try:
        # Bot yaratuvchisini admin qilib o'rnatish
        owner = User.objects.get(uid=owner_uid)

        # AdminInfo yaratish yoki yangilash
        admin_info, created = AdminInfo.objects.get_or_create(
            bot_token=bot_token,
            defaults={
                'admin_channel': f"@{owner.username}" if owner.username else str(owner_uid),
                'price': 3.0,  # Default referral bonus
                'min_amount': 30.0  # Default minimal yechish miqdori
            }
        )

        if not created:
            # Agar mavjud bo'lsa, admin kanalini yangilash
            admin_info.admin_channel = f"@{owner.username}" if owner.username else str(owner_uid)
            admin_info.save()

        logger.info(f"Auto admin setup completed for bot @{bot_username}, owner: {owner_uid}")

        return {
            'admin_user': f"@{owner.username}" if owner.username else str(owner_uid),
            'referral_price': admin_info.price,
            'min_withdrawal': admin_info.min_amount
        }

    except Exception as e:
        logger.error(f"Error in auto admin setup for bot {bot_token}: {e}")
        return None


@sync_to_async
def check_user_admin_status(user_id: int, bot_token: str) -> bool:
    """
    Foydalanuvchi admin ekanligini tekshirish
    """
    try:
        # Bot egasini tekshirish
        bot = Bot.objects.get(token=bot_token)
        if bot.owner.uid == user_id:
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


@sync_to_async
def get_bot_admins_list(bot_token: str):
    """
    Bot adminlari ro'yxatini olish
    """
    try:
        admins = []

        # Bot egasini qo'shish
        bot = Bot.objects.get(token=bot_token)
        owner = bot.owner
        admins.append({
            'uid': owner.uid,
            'username': owner.username,
            'first_name': owner.first_name,
            'role': 'owner',
            'is_owner': True
        })

        # AdminInfo dan qo'shimcha adminlarni olish
        admin_info = AdminInfo.objects.filter(bot_token=bot_token).first()
        if admin_info and admin_info.admin_channel:
            # Admin channel dan boshqa adminlarni parse qilish
            admin_channel = admin_info.admin_channel
            if admin_channel != f"@{owner.username}" and admin_channel != str(owner.uid):
                admins.append({
                    'uid': None,
                    'username': admin_channel,
                    'first_name': 'Admin',
                    'role': 'admin',
                    'is_owner': False
                })

        return admins

    except Exception as e:
        logger.error(f"Error getting admins list for bot {bot_token}: {e}")
        return []


# modul/bot/main_bot/services/user_service.py ga qo'shish kerak bo'lgan o'zgarish:

@sync_to_async
@transaction.atomic
def create_bot_with_auto_admin(owner_uid: int, token: str, username: str, modules: dict):
    """
    Yangi bot yaratish va avtomatik admin o'rnatish
    """
    try:
        from modul.bot.main_bot.services.auto_admin_service import setup_auto_admin

        owner = User.objects.get(uid=owner_uid)

        # Bot yaratish
        bot = Bot.objects.create(
            token=token,
            username=username,
            owner=owner,
            bot_enable=True,
            # Modullar
            enable_refs=modules.get('refs', False),
            enable_kino=modules.get('kino', False),
            enable_music=modules.get('music', False),
            enable_download=modules.get('download', False),
            enable_chatgpt=modules.get('chatgpt', False),
            enable_leo=modules.get('leo', False),
            enable_horoscope=modules.get('horoscope', False),
            enable_anon=modules.get('anon', False),
            enable_sms=modules.get('sms', False),
        )

        logger.info(f"Bot created successfully: {username} for user {owner_uid}")

        # AVTOMATIK ADMIN O'RNATISH
        # Bu sync funksiya, lekin biz sync context ichidamiz
        from django.db import connection
        try:
            admin_info, created = AdminInfo.objects.get_or_create(
                bot_token=token,
                defaults={
                    'admin_channel': f"@{owner.username}" if owner.username else str(owner_uid),
                    'price': 3.0,
                    'min_amount': 30.0
                }
            )

            logger.info(f"Auto admin setup completed for bot @{username}, admin: {admin_info.admin_channel}")
        except Exception as admin_error:
            logger.error(f"Error setting up auto admin: {admin_error}")

        return bot

    except Exception as e:
        logger.error(f"Error creating bot with auto admin for owner {owner_uid}: {e}")
        return None
# modul/clientbot/handlers/admin/admin_service.py
"""
Admin panel service functions
Universal admin panel uchun service funksiyalar
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from asgiref.sync import sync_to_async
from django.db.models import Count, Q
from django.utils import timezone

from modul.models import Bot, UserTG, ClientBotUser
from modul.clientbot import shortcuts

logger = logging.getLogger(__name__)


class AdminService:
    """Admin panel service class"""

    @staticmethod
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

    @staticmethod
    @sync_to_async
    def get_pending_payments_count(bot_id: int) -> int:
        """Kutilayotgan to'lovlar sonini olish"""
        try:
            # Bu yerda to'lov modeli bo'yicha kutilayotgan to'lovlarni sanash
            # Misol: Payment.objects.filter(bot_id=bot_id, status='pending').count()
            return 0  # Placeholder
        except Exception as e:
            logger.error(f"Get pending payments error: {e}")
            return 0

    @staticmethod
    @sync_to_async
    def get_today_activity(bot_id: int) -> int:
        """Bugungi faollikni olish"""
        try:
            today = timezone.now().date()
            activity_count = UserTG.objects.filter(
                bot_id=bot_id,
                created_at__date=today
            ).count()
            return activity_count
        except Exception as e:
            logger.error(f"Get today activity error: {e}")
            return 0

    @staticmethod
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
            except ClientBotUser.DoesNotExist:
                pass

            return None

        except Exception as e:
            logger.error(f"Get user info error: {e}")
            return None

    @staticmethod
    @sync_to_async
    def ban_user_by_id(user_id: int, bot_id: int) -> bool:
        """Foydalanuvchini bloklash"""
        try:
            # UserTG modelida bloklash
            users_updated = UserTG.objects.filter(
                tg_id=user_id, bot_id=bot_id
            ).update(is_banned=True)

            # ClientBotUser modelida bloklash
            client_users_updated = ClientBotUser.objects.filter(
                tg_id=user_id, bot_id=bot_id
            ).update(is_banned=True)

            return users_updated > 0 or client_users_updated > 0

        except Exception as e:
            logger.error(f"Ban user error: {e}")
            return False

    @staticmethod
    @sync_to_async
    def unban_user_by_id(user_id: int, bot_id: int) -> bool:
        """Foydalanuvchini blokdan chiqarish"""
        try:
            # UserTG modelida blokdan chiqarish
            users_updated = UserTG.objects.filter(
                tg_id=user_id, bot_id=bot_id
            ).update(is_banned=False)

            # ClientBotUser modelida blokdan chiqarish
            client_users_updated = ClientBotUser.objects.filter(
                tg_id=user_id, bot_id=bot_id
            ).update(is_banned=False)

            return users_updated > 0 or client_users_updated > 0

        except Exception as e:
            logger.error(f"Unban user error: {e}")
            return False

    @staticmethod
    @sync_to_async
    def change_user_balance(user_id: int, bot_id: int, new_balance: float) -> bool:
        """Foydalanuvchi balansini o'zgartirish"""
        try:
            # UserTG modelida balansni o'zgartirish
            users_updated = UserTG.objects.filter(
                tg_id=user_id, bot_id=bot_id
            ).update(balance=new_balance)

            return users_updated > 0

        except Exception as e:
            logger.error(f"Change balance error: {e}")
            return False

    @staticmethod
    @sync_to_async
    def add_user_balance(user_id: int, bot_id: int, amount: float) -> bool:
        """Foydalanuvchi balansiga qo'shish"""
        try:
            from django.db.models import F

            # UserTG modelida balansga qo'shish
            users_updated = UserTG.objects.filter(
                tg_id=user_id, bot_id=bot_id
            ).update(balance=F('balance') + amount)

            return users_updated > 0

        except Exception as e:
            logger.error(f"Add balance error: {e}")
            return False

    @staticmethod
    @sync_to_async
    def change_user_referrals(user_id: int, bot_id: int, new_refs: int) -> bool:
        """Foydalanuvchi referal sonini o'zgartirish"""
        try:
            # UserTG modelida referallarni o'zgartirish
            users_updated = UserTG.objects.filter(
                tg_id=user_id, bot_id=bot_id
            ).update(referrals_count=new_refs)

            return users_updated > 0

        except Exception as e:
            logger.error(f"Change referrals error: {e}")
            return False

    @staticmethod
    @sync_to_async
    def get_all_users_for_mailing(bot_id: int) -> List[int]:
        """Xabar tarqatish uchun barcha foydalanuvchilar ID sini olish"""
        try:
            # UserTG foydalanuvchilar
            refs_users = list(UserTG.objects.filter(
                bot_id=bot_id,
                is_banned=False
            ).values_list('tg_id', flat=True))

            # ClientBotUser foydalanuvchilar
            client_users = list(ClientBotUser.objects.filter(
                bot_id=bot_id,
                is_banned=False
            ).values_list('tg_id', flat=True))

            return refs_users + client_users

        except Exception as e:
            logger.error(f"Get users for mailing error: {e}")
            return []

    @staticmethod
    @sync_to_async
    def get_bot_statistics_detailed(bot_id: int) -> Dict[str, Any]:
        """Bot uchun batafsil statistika"""
        try:
            today = timezone.now().date()
            week_ago = today - timedelta(days=7)
            month_ago = today - timedelta(days=30)

            # Umumiy foydalanuvchilar
            total_users = UserTG.objects.filter(bot_id=bot_id).count()
            total_client_users = ClientBotUser.objects.filter(bot_id=bot_id).count()

            # Bugungi yangi foydalanuvchilar
            today_users = UserTG.objects.filter(
                bot_id=bot_id, created_at__date=today
            ).count()

            # Haftalik foydalanuvchilar
            week_users = UserTG.objects.filter(
                bot_id=bot_id, created_at__date__gte=week_ago
            ).count()

            # Oylik foydalanuvchilar
            month_users = UserTG.objects.filter(
                bot_id=bot_id, created_at__date__gte=month_ago
            ).count()

            # Bloklangan foydalanuvchilar
            banned_users = UserTG.objects.filter(
                bot_id=bot_id, is_banned=True
            ).count()

            return {
                'total_users': total_users + total_client_users,
                'refs_users': total_users,
                'client_users': total_client_users,
                'today_users': today_users,
                'week_users': week_users,
                'month_users': month_users,
                'banned_users': banned_users,
                'active_users': (total_users + total_client_users) - banned_users
            }

        except Exception as e:
            logger.error(f"Get detailed statistics error: {e}")
            return {
                'total_users': 0,
                'refs_users': 0,
                'client_users': 0,
                'today_users': 0,
                'week_users': 0,
                'month_users': 0,
                'banned_users': 0,
                'active_users': 0
            }


# Service functions
async def get_admin_id(bot) -> int:
    """Bot admin ID sini olish"""
    try:
        bot_db = await shortcuts.get_bot(bot)
        return bot_db.owner.uid if bot_db else 0
    except Exception as e:
        logger.error(f"Get admin ID error: {e}")
        return 0


async def check_admin_permission(user_id: int, bot) -> bool:
    """Admin huquqlarini tekshirish"""
    try:
        admin_id = await get_admin_id(bot)
        # Qo'shimcha adminlar ro'yxatini qo'shish mumkin
        admin_ids = [admin_id]
        return user_id in admin_ids
    except Exception as e:
        logger.error(f"Check admin permission error: {e}")
        return False


async def send_mailing_message(bot, user_ids: List[int], message_data: Dict) -> Dict[str, int]:
    """Xabar tarqatish"""
    success_count = 0
    failed_count = 0

    for user_id in user_ids:
        try:
            if message_data.get('type') == 'text':
                await bot.send_message(
                    chat_id=user_id,
                    text=message_data['text'],
                    parse_mode=message_data.get('parse_mode', 'HTML')
                )
            elif message_data.get('type') == 'copy':
                await bot.copy_message(
                    chat_id=user_id,
                    from_chat_id=message_data['from_chat_id'],
                    message_id=message_data['message_id']
                )
            success_count += 1
        except Exception as e:
            logger.error(f"Send message to {user_id} error: {e}")
            failed_count += 1

    return {
        'success': success_count,
        'failed': failed_count
    }


# modul/clientbot/handlers/annon_bot/adminservice.py

from asgiref.sync import sync_to_async
from modul.models import UserTG, Channels, ClientBotUser, Bot
import logging



@sync_to_async
def get_channels_for_admin():
    all_channels = Channels.objects.all()
    if all_channels:
        return [[i.id, i.channel_url, i.channel_id] for i in all_channels]
    return []


@sync_to_async
def add_new_channel_db(url, id):
    new_channel = Channels(channel_url=url, channel_id=id)
    new_channel.save()
    return True


@sync_to_async
def delete_channel_db(id):
    try:
        channel = Channels.objects.get(id=id)
        channel.delete()
        return True
    except Channels.DoesNotExist:
        return False


@sync_to_async
def get_all_users_tg_id():
    users = UserTG.objects.all()
    return [i.uid for i in users]


@sync_to_async
def get_users_count(bot_token=None):
    """
    Bot foydalanuvchilar sonini olish
    """
    try:
        if bot_token:
            # Bot tokeniga asosan botni topish
            bot = Bot.objects.get(token=bot_token)
            # Shu bot uchun foydalanuvchilar sonini hisoblash
            count = ClientBotUser.objects.filter(bot=bot).count()
            logger.info(f"Users count for bot {bot.username}: {count}")
        else:
            # Umumiy foydalanuvchilar soni (barcha botlar)
            count = ClientBotUser.objects.all().count()
            logger.info(f"Total users count across all bots: {count}")

        return count
    except Bot.DoesNotExist:
        logger.error(f"Bot with token {bot_token} not found")
        return 0
    except Exception as e:
        logger.error(f"Get users count error: {e}")
        return 0


# Qo'shimcha funktsiyalar
@sync_to_async
def get_bot_users_count_by_token(bot_token):
    """
    Muayyan bot uchun foydalanuvchilar soni
    """
    try:
        bot = Bot.objects.get(token=bot_token)
        return ClientBotUser.objects.filter(bot=bot).count()
    except Bot.DoesNotExist:
        logger.error(f"Bot with token {bot_token} not found")
        return 0
    except Exception as e:
        logger.error(f"Error getting bot users count: {e}")
        return 0


@sync_to_async
def get_total_users_count_all_bots():
    """
    Barcha botlardagi umumiy foydalanuvchilar soni
    """
    try:
        return ClientBotUser.objects.all().count()
    except Exception as e:
        logger.error(f"Error getting total users count: {e}")
        return 0

# Export service class
admin_service = AdminService()
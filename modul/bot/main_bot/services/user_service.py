# modul/bot/main_bot/services/user_service.py
"""
Main bot uchun foydalanuvchi xizmatlari
Barcha Django ORM operatsiyalari sync_to_async bilan amalga oshiriladi
"""

from asgiref.sync import sync_to_async
from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta
import logging

from modul.models import User, Bot, UserTG, ClientBotUser

logger = logging.getLogger(__name__)


@sync_to_async
def get_user_by_uid(uid: int):
    """
    Foydalanuvchini UID bo'yicha olish
    """
    try:
        return User.objects.get(uid=uid)
    except User.DoesNotExist:
        return None
    except Exception as e:
        logger.error(f"Error getting user {uid}: {e}")
        return None


@sync_to_async
def check_user_exists(uid: int) -> bool:
    """
    Foydalanuvchi mavjudligini tekshirish
    """
    try:
        return User.objects.filter(uid=uid).exists()
    except Exception as e:
        logger.error(f"Error checking user existence {uid}: {e}")
        return False


@sync_to_async
@transaction.atomic
def create_or_get_user(uid: int, first_name: str, last_name: str = None, username: str = None):
    """
    Foydalanuvchini yaratish yoki mavjudini olish
    """
    try:
        user, created = User.objects.get_or_create(
            uid=uid,
            defaults={
                'first_name': first_name,
                'last_name': last_name or "Не указано",
                'username': username or "Не указано"
            }
        )
        return user, created
    except Exception as e:
        logger.error(f"Error creating/getting user {uid}: {e}")
        return None, False


@sync_to_async
def get_user_bots(uid: int):
    """
    Foydalanuvchining barcha botlarini olish
    """
    try:
        return list(Bot.objects.filter(owner__uid=uid).values(
            'id', 'username', 'name', 'is_active', 'created_at',
            'enable_refs', 'enable_kino', 'enable_music', 'enable_download',
            'enable_chatgpt', 'enable_leo', 'enable_horoscope', 'enable_anon', 'enable_sms'
        ))
    except Exception as e:
        logger.error(f"Error getting user bots for {uid}: {e}")
        return []


@sync_to_async
def get_bot_by_id(bot_id: int, owner_uid: int):
    """
    Bot ID va owner UID bo'yicha botni olish
    """
    try:
        return Bot.objects.get(id=bot_id, owner__uid=owner_uid)
    except Bot.DoesNotExist:
        return None
    except Exception as e:
        logger.error(f"Error getting bot {bot_id} for owner {owner_uid}: {e}")
        return None


@sync_to_async
def get_bot_statistics(bot_id: int):
    """
    Bot statistikasini olish
    """
    try:
        bot = Bot.objects.get(id=bot_id)

        # Jami foydalanuvchilar
        total_users = ClientBotUser.objects.filter(bot=bot).count()

        # Faol foydalanuvchilar (oxirgi 7 kun)
        week_ago = timezone.now() - timedelta(days=7)
        active_users = ClientBotUser.objects.filter(
            bot=bot,
            user__last_interaction__gte=week_ago
        ).count()

        # Yangi foydalanuvchilar (oxirgi 24 soat)
        day_ago = timezone.now() - timedelta(days=1)
        new_users = ClientBotUser.objects.filter(
            bot=bot,
            created_at__gte=day_ago
        ).count()

        # Jami to'lovlar (agar refs modul yoqilgan bo'lsa)
        total_payments = 0
        if bot.enable_refs:
            # RefPayment modelidan olish mumkin
            pass

        return {
            'total_users': total_users,
            'active_users': active_users,
            'new_users': new_users,
            'total_payments': total_payments,
            'bot_username': bot.username,
            'bot_name': bot.name,
            'is_active': bot.is_active
        }
    except Exception as e:
        logger.error(f"Error getting bot statistics for {bot_id}: {e}")
        return None


@sync_to_async
@transaction.atomic
def toggle_bot_status(bot_id: int, owner_uid: int):
    """
    Bot holatini o'zgartirish (faol/nofaol)
    """
    try:
        bot = Bot.objects.get(id=bot_id, owner__uid=owner_uid)
        bot.is_active = not bot.is_active
        bot.save()
        return bot.is_active
    except Bot.DoesNotExist:
        return None
    except Exception as e:
        logger.error(f"Error toggling bot status {bot_id}: {e}")
        return None


@sync_to_async
@transaction.atomic
def update_bot_modules(bot_id: int, owner_uid: int, modules: dict):
    """
    Bot modullarini yangilash
    """
    try:
        bot = Bot.objects.get(id=bot_id, owner__uid=owner_uid)

        # Modullarni yangilash
        for module_name, enabled in modules.items():
            if hasattr(bot, f'enable_{module_name}'):
                setattr(bot, f'enable_{module_name}', enabled)

        bot.save()
        return True
    except Bot.DoesNotExist:
        logger.error(f"Bot {bot_id} not found for owner {owner_uid}")
        return False
    except Exception as e:
        logger.error(f"Error updating bot modules {bot_id}: {e}")
        return False


@sync_to_async
@transaction.atomic
def delete_bot(bot_id: int, owner_uid: int):
    """
    Botni o'chirish
    """
    try:
        bot = Bot.objects.get(id=bot_id, owner__uid=owner_uid)
        bot_username = bot.username
        bot.delete()
        return bot_username
    except Bot.DoesNotExist:
        return None
    except Exception as e:
        logger.error(f"Error deleting bot {bot_id}: {e}")
        return None


@sync_to_async
def validate_bot_token(token: str):
    """
    Bot tokenini tekshirish
    """
    import re
    import aiohttp

    # Token formatini tekshirish
    if not re.match(r'^\d+:[A-Za-z0-9_-]+$', token):
        return False, "Noto'g'ri token formati"

    # Token allaqachon ishlatilganmi tekshirish
    if Bot.objects.filter(token=token).exists():
        return False, "Bu token allaqachon ishlatilmoqda"

    return True, "Token to'g'ri"


@sync_to_async
@transaction.atomic
def create_bot(owner_uid: int, token: str, username: str, name: str, modules: dict):
    """
    Yangi bot yaratish
    """
    try:
        owner = User.objects.get(uid=owner_uid)

        bot = Bot.objects.create(
            token=token,
            username=username,
            name=name,
            owner=owner,
            enable_refs=modules.get('refs', False),
            enable_kino=modules.get('kino', False),
            enable_music=modules.get('music', False),
            enable_download=modules.get('download', False),
            enable_chatgpt=modules.get('chatgpt', False),
            enable_leo=modules.get('leo', False),
            enable_horoscope=modules.get('horoscope', False),
            enable_anon=modules.get('anon', False),
            enable_sms=modules.get('sms', False),
            is_active=True
        )

        return bot
    except Exception as e:
        logger.error(f"Error creating bot for owner {owner_uid}: {e}")
        return None


@sync_to_async
def get_user_statistics(uid: int):
    """
    Foydalanuvchi umumiy statistikasini olish
    """
    try:
        user = User.objects.get(uid=uid)

        # Foydalanuvchi botlari soni
        total_bots = Bot.objects.filter(owner=user).count()
        active_bots = Bot.objects.filter(owner=user, is_active=True).count()

        # Barcha botlardagi foydalanuvchilar
        total_bot_users = ClientBotUser.objects.filter(bot__owner=user).count()

        # UserTG dan balans va referrallar
        user_tg = UserTG.objects.filter(uid=uid).first()
        balance = user_tg.balance if user_tg else 0
        refs_count = user_tg.refs if user_tg else 0

        return {
            'total_bots': total_bots,
            'active_bots': active_bots,
            'total_bot_users': total_bot_users,
            'balance': balance,
            'refs_count': refs_count,
            'user_name': user.first_name,
            'user_username': user.username
        }
    except Exception as e:
        logger.error(f"Error getting user statistics for {uid}: {e}")
        return None


# Telegram API bilan ishlash uchun async funksiyalar
async def get_bot_info_from_telegram(token: str):
    """
    Telegram API orqali bot ma'lumotlarini olish
    """
    import aiohttp

    try:
        url = f"https://api.telegram.org/bot{token}/getMe"

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    if data['ok']:
                        bot_info = data['result']
                        return {
                            'id': bot_info['id'],
                            'username': bot_info['username'],
                            'first_name': bot_info['first_name'],
                            'is_bot': bot_info['is_bot']
                        }
                return None
    except Exception as e:
        logger.error(f"Error getting bot info for token {token}: {e}")
        return None


async def set_bot_webhook(token: str, webhook_url: str):
    """
    Bot uchun webhook o'rnatish
    """
    import aiohttp

    try:
        url = f"https://api.telegram.org/bot{token}/setWebhook"
        data = {'url': webhook_url}

        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=data) as response:
                if response.status == 200:
                    result = await response.json()
                    return result.get('ok', False)
                return False
    except Exception as e:
        logger.error(f"Error setting webhook for token {token}: {e}")
        return False
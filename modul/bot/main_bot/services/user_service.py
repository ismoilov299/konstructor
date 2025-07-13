# modul/bot/main_bot/services/user_service.py (tuzatilgan versiya)

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
    Получение пользователя по UID
    """
    try:
        return User.objects.get(uid=uid)
    except User.DoesNotExist:
        return None
    except Exception as e:
        logger.error(f"Ошибка при получении пользователя {uid}: {e}")
        return None


@sync_to_async
def check_user_exists(uid: int) -> bool:
    """
    Проверка существования пользователя
    """
    try:
        return User.objects.filter(uid=uid).exists()
    except Exception as e:
        logger.error(f"Ошибка при проверке существования пользователя {uid}: {e}")
        return False


@sync_to_async
@transaction.atomic
def create_or_get_user(uid: int, first_name: str, last_name: str = None, username: str = None):
    """
    Создание или получение пользователя
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
        logger.error(f"Ошибка при создании/получении пользователя {uid}: {e}")
        return None, False


@sync_to_async
def get_user_bots(uid: int):
    """
    Получение всех ботов пользователя
    Используются существующие поля из модели Bot
    """
    try:
        return list(Bot.objects.filter(owner__uid=uid).values(
            'id', 'username', 'token', 'bot_enable',
            'enable_refs', 'enable_leo', 'enable_kino',
            'enable_download', 'enable_chatgpt', 'enable_davinci'
        ).order_by('-id'))
    except Exception as e:
        logger.error(f"Ошибка при получении ботов пользователя {uid}: {e}")
        return []


@sync_to_async
def create_user_directly(uid, username, first_name, last_name="", profile_image_url=None):
    """
    Foydalanuvchini to'g'ridan-to'g'ri bazaga qo'shish
    """
    try:
        # User modelida yaratish
        user = User.objects.create(
            uid=uid,
            username=username if username else None,
            first_name=first_name,
            last_name=last_name if last_name else None,
        )

        # UserTG modelida ham yaratish (agar kerak bo'lsa)
        user_tg, created = UserTG.objects.get_or_create(
            uid=uid,
            defaults={
                'username': username if username else None,
                'first_name': first_name,
                'last_name': last_name if last_name else None,
                'balance': 0,
                'paid': 0,
                'refs': 0,
                'invited': "Никто",
                'invited_id': None,
                'banned': False
            }
        )

        logger.info(f"User {uid} created successfully: {user.username or user.first_name}")
        return user

    except Exception as e:
        logger.error(f"Error creating user {uid}: {e}")
        return None


@sync_to_async
def get_bot_by_id(bot_id: int, owner_uid: int):
    """
    Получение бота по ID и UID владельца
    """
    try:
        return Bot.objects.get(id=bot_id, owner__uid=owner_uid)
    except Bot.DoesNotExist:
        return None
    except Exception as e:
        logger.error(f"Ошибка при получении бота {bot_id} для владельца {owner_uid}: {e}")
        return None


@sync_to_async
def get_bot_statistics(bot_id: int):
    """
    Получение статистики бота
    """
    try:
        bot = Bot.objects.select_related('owner').get(id=bot_id)

        # Общее количество пользователей
        total_users = ClientBotUser.objects.filter(bot=bot).count()

        # Активные пользователи (последние 7 дней)
        week_ago = timezone.now() - timedelta(days=7)
        active_users = ClientBotUser.objects.filter(
            bot=bot,
            user__last_interaction__gte=week_ago
        ).count()

        # Новые пользователи (последние 24 часа)
        day_ago = timezone.now() - timedelta(days=1)
        try:
            # Проверка наличия поля created_at в ClientBotUser
            new_users = ClientBotUser.objects.filter(
                bot=bot,
                user__created_at__gte=day_ago  # Использование поля created_at из UserTG
            ).count()
        except Exception:
            # Если поле created_at отсутствует, возвращаем 0
            new_users = 0

        # Общие платежи (если включен модуль refs)
        total_payments = 0
        if bot.enable_refs:
            # Можно получить из модели RefPayment
            pass

        return {
            'total_users': total_users,
            'active_users': active_users,
            'new_users': new_users,
            'total_payments': total_payments,
            'bot_username': bot.username,
            'bot_token': bot.token,
            'is_active': bot.bot_enable,
            # Используем существующие поля из модели
            'enable_refs': bot.enable_refs,
            'enable_leo': bot.enable_leo,
            'enable_kino': bot.enable_kino,
            'enable_download': bot.enable_download,
            'enable_chatgpt': bot.enable_chatgpt,
            'enable_davinci': bot.enable_davinci
        }
    except Exception as e:
        logger.error(f"Ошибка при получении статистики бота {bot_id}: {e}")
        return None


@sync_to_async
@transaction.atomic
def toggle_bot_status(bot_id: int, owner_uid: int):
    """
    Изменение статуса бота (активный/неактивный)
    """
    try:
        bot = Bot.objects.get(id=bot_id, owner__uid=owner_uid)
        bot.bot_enable = not bot.bot_enable
        bot.save()
        return bot.bot_enable
    except Bot.DoesNotExist:
        return None
    except Exception as e:
        logger.error(f"Ошибка при изменении статуса бота {bot_id}: {e}")
        return None


@sync_to_async
@transaction.atomic
def update_bot_modules(bot_id: int, owner_uid: int, modules: dict):
    """
    Обновление модулей бота
    """
    try:
        bot = Bot.objects.get(id=bot_id, owner__uid=owner_uid)

        # Обновление модулей
        for module_name, enabled in modules.items():
            if hasattr(bot, f'enable_{module_name}'):
                setattr(bot, f'enable_{module_name}', enabled)

        bot.save()
        return True
    except Bot.DoesNotExist:
        logger.error(f"Бот {bot_id} не найден для владельца {owner_uid}")
        return False
    except Exception as e:
        logger.error(f"Ошибка при обновлении модулей бота {bot_id}: {e}")
        return False


@sync_to_async
@transaction.atomic
def delete_bot(bot_id: int, owner_uid: int):
    """
    Удаление бота
    """
    try:
        bot = Bot.objects.get(id=bot_id, owner__uid=owner_uid)
        bot_username = bot.username
        bot.delete()
        return bot_username
    except Bot.DoesNotExist:
        return None
    except Exception as e:
        logger.error(f"Ошибка при удалении бота {bot_id}: {e}")
        return None


@sync_to_async
def validate_bot_token(token: str):
    """
    Проверка токена бота
    ВАЖНО: Проверяет, что токен не используется дважды
    """
    import re

    # Проверка формата токена
    if not re.match(r'^\d{8,10}:[A-Za-z0-9_-]{35}$', token):
        return False, "Неправильный формат токена"

    # КРИТИЧЕСКАЯ ПРОВЕРКА: Токен уже используется?
    if Bot.objects.filter(token=token).exists():
        return False, "Этот токен уже используется другим ботом"

    return True, "Токен корректный"


@sync_to_async
@transaction.atomic
def create_bot(owner_uid: int, token: str, username: str, modules: dict):
    """
    Создание нового бота и автоматическая настройка админа
    ВАЖНО: Двойная проверка токена для предотвращения дублирования
    """
    try:
        # ДВОЙНАЯ ПРОВЕРКА ТОКЕНА ПЕРЕД СОЗДАНИЕМ
        if Bot.objects.filter(token=token).exists():
            logger.error(f"Попытка создать бот с уже используемым токеном: {token}")
            return None

        owner = User.objects.get(uid=owner_uid)

        # Создание бота с использованием существующих полей модели
        bot = Bot.objects.create(
            token=token,
            username=username,
            owner=owner,
            bot_enable=True,
            # Используем существующие поля из модели Bot
            enable_refs=modules.get('refs', False),
            enable_leo=modules.get('leo', False),
            enable_kino=modules.get('kino', False),
            enable_download=modules.get('download', False),
            enable_chatgpt=modules.get('chatgpt', False),
            enable_anon=modules.get('anon', False),
            enable_davinci=modules.get('davinci', False)
        )

        # АВТОМАТИЧЕСКАЯ НАСТРОЙКА АДМИНА
        try:
            from modul.models import AdminInfo
            admin_info, created = AdminInfo.objects.get_or_create(
                bot_token=token,
                defaults={
                    'admin_channel': f"@{owner.username}" if owner.username and owner.username != "Не указано" else str(owner_uid),
                    'price': 3.0,  # Реферальный бонус по умолчанию
                    'min_amount': 30.0  # Минимальная сумма вывода по умолчанию
                }
            )

            if not created:
                # Если уже существует, обновляем админа
                admin_info.admin_channel = f"@{owner.username}" if owner.username and owner.username != "Не указано" else str(owner_uid)
                admin_info.save()

            logger.info(f"Автонастройка админа: @{username} -> админ: {admin_info.admin_channel}")

        except Exception as admin_error:
            logger.error(f"Ошибка при настройке автоадмина для {username}: {admin_error}")

        logger.info(f"Бот успешно создан: {username} для пользователя {owner_uid}")
        return bot

    except Exception as e:
        logger.error(f"Ошибка при создании бота для владельца {owner_uid}: {e}")
        return None


@sync_to_async
def get_user_statistics(uid: int):
    """
    Получение общей статистики пользователя
    """
    try:
        user = User.objects.get(uid=uid)

        # Количество ботов пользователя
        total_bots = Bot.objects.filter(owner=user).count()
        active_bots = Bot.objects.filter(owner=user, bot_enable=True).count()

        # Пользователи во всех ботах
        total_bot_users = ClientBotUser.objects.filter(bot__owner=user).count()

        # Баланс и рефералы из UserTG
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
        logger.error(f"Ошибка при получении статистики пользователя {uid}: {e}")
        return None


# Async функции для работы с Telegram API
async def get_bot_info_from_telegram(token: str):
    """
    Получение информации о боте через Telegram API
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
        logger.error(f"Ошибка при получении информации о боте для токена {token}: {e}")
        return None


async def set_bot_webhook(token: str, webhook_url: str):
    """
    Установка webhook для бота
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
        logger.error(f"Ошибка при установке webhook для токена {token}: {e}")
        return False
import asyncio
import logging
from datetime import datetime, timezone
import json
from email._header_value_parser import get_domain
from math import ceil
import re
from typing import Union
from aiogram import Bot, types
import aiohttp
from aiogram.fsm.storage.base import StorageKey
from aiogram.fsm.context import FSMContext
from asgiref.sync import sync_to_async
from django.db import transaction
from openpyxl import Workbook
from urllib.parse import urlparse
from modul.clientbot import strings
from modul.config import settings_conf
from modul import models

from aiogram.types import FSInputFile
import os
from modul.loader import bot_session, main_bot, dp
from aiogram import Bot
logger = logging.getLogger(__name__)

def get_fsm_context(bot: Bot, chat_id: int, user_id: int = None):
    if not user_id:
        user_id = chat_id
    return FSMContext(
        storage=dp.storage,
        key=StorageKey(
            chat_id=chat_id,
            user_id=user_id,
            bot_id=bot.id
        )
    )


def have_one_module(bot, module_name: str):
    """
    Bot modullarini tekshirish
    """
    try:
        logger.info(f"Checking module {module_name} for bot {bot.token}")

        # Barcha mavjud modullar
        modules = {
            "promotion": "enable_promotion",
            "music": "enable_music",
            "download": "enable_download",
            "leo": "enable_leo",
            "chatgpt": "enable_chatgpt",
            "horoscope": "enable_horoscope",
            "anon": "enable_anon",
            "sms": "enable_sms",
            "refs": "enable_refs",
            "kino": "enable_kino"
        }

        # Bot attributlarini tekshiramiz
        enabled_modules = [
            key for key, attr in modules.items()
            if hasattr(bot, attr) and getattr(bot, attr)
        ]

        logger.info(f"Enabled modules for bot: {enabled_modules}")

        # So'ralgan modul yoqilganmi tekshiramiz
        module_attr = modules.get(module_name)
        if not module_attr:
            logger.error(f"Unknown module requested: {module_name}")
            return False

        is_enabled = hasattr(bot, module_attr) and getattr(bot, module_attr)
        logger.info(f"Module {module_name} is {'enabled' if is_enabled else 'disabled'}")

        # Modul yoqilgan va yagona bo'lishi kerakmi
        if 'single_module' in dir(bot) and getattr(bot, 'single_module'):
            return is_enabled and len(enabled_modules) == 1

        return is_enabled

    except Exception as e:
        logger.error(f"Error checking module {module_name}: {e}", exc_info=True)
        return False


def turn_bot_data(attr: str, bot: Bot):
    bot = get_current_bot(bot)
    setattr(bot, attr, not getattr(bot, attr))
    bot.save()


@sync_to_async
def get_current_bot(bot: Bot):
    return models.Bot.objects.filter(token=bot.token).first()


@sync_to_async
def get_bot(bot: Bot):
    return models.Bot.objects.filter(token=bot.token).select_related("owner").first()


@sync_to_async
def get_bot_by_token(token: str):
    return models.Bot.objects.filter(token=token).first()


@sync_to_async
def get_bot_owner(bot: Bot):
    current_bot = get_current_bot(bot)
    return models.Bot.objects.filter(bots__token=current_bot.token).first()


@sync_to_async
def get_bot_by_username(username: str):
    return models.Bot.objects.filter(username=username).first()


@sync_to_async
def create_client_bot_user(uid, bot: Bot):
    return models.ClientBotUser.objects.filter(uid=uid, bot__token=bot.token).first()


async def get_user(uid: int, bot: Bot):
    bot = await get_current_bot(bot)
    info = await create_client_bot_user(uid, bot)
    return info


@sync_to_async
def get_users(**kwargs):
    queryset = models.ClientBotUser.objects.filter(**kwargs)
    return queryset, queryset.count()


#
#
@sync_to_async
@transaction.atomic
def increase_referral(user: models.ClientBotUser):
    try:
        logger.info(f"Starting increase_referral for user {user.uid}")

        # Referral bonus summasi
        REFERRAL_BONUS = 4.0

        # Ma'lumotlarni bazadan yangilaymiz
        user_obj = models.ClientBotUser.objects.select_for_update().get(id=user.id)

        # Joriy qiymatlarni log qilamiz
        logger.info(f"Before update - count: {user_obj.referral_count}, balance: {user_obj.referral_balance}")

        # Balansni float ga o'girib, keyin qo'shamiz
        current_balance = float(user_obj.referral_balance)
        new_balance = current_balance + REFERRAL_BONUS

        user_obj.referral_count += 1
        user_obj.referral_balance = new_balance
        user_obj.save()

        # Bazadan yangi qiymatni qayta o'qiymiz tekshirish uchun
        updated_user = models.ClientBotUser.objects.get(id=user.id)
        logger.info(f"After update - count: {updated_user.referral_count}, balance: {updated_user.referral_balance}")

        return True

    except Exception as e:
        logger.error(f"Error in increase_referral: {e}", exc_info=True)
        raise  # Xatoni ko'rish uchun raise qilamiz


@sync_to_async
def get_user_info_db(tg_id: int, bot: Bot):
    try:
        logger.info(f"Getting user info for user {tg_id} with bot token {bot.token}")
        user = models.ClientBotUser.objects.select_related(
            'user',
            'inviter',
            'inviter__user',
            'bot'
        ).get(
            uid=tg_id,
            bot__token=bot.token
        )

        inviter_name = "Никто"
        if user.inviter:
            inviter_name = user.inviter.user.username or user.inviter.user.first_name or str(user.inviter.uid)

        # Calculate total balance
        total_balance = float(user.balance) + float(user.referral_balance)
        logger.info(f"User balances - main: {user.balance}, referral: {user.referral_balance}, total: {total_balance}")

        result = [
            user.user.username or user.user.first_name,
            user.uid,
            total_balance,
            user.referral_count,
            inviter_name
        ]
        logger.info(f"Returning user info: {result}")
        return result

    except Exception as e:
        logger.error(f"Error getting user info for {tg_id}: {e}", exc_info=True)
        return None

#
#
# async def referral_count(uid: int):
#     user = await get_user(uid)
#     if user:
#         return user.referral_count
#
#
# async def user_balance(uid: int):
#     user = await get_user(uid)
#     if user:
#         return user.balance
#
#
# async def referral_balance(uid: int):
#     user = await get_user(uid)
#     if user:
#         return user.referral_balance
#
#
# async def transfer_money(uid: int, amount: float):
# user = await get_user(uid)
# if user:
#     user.referral_balance -= amount
#     user.balance += amount
#     await user.save()
#     return True


# async def save_order(uid: int, order_id: int, category: str, quantity: int, price: float, profit: float,
#                      bot_admin_profit: float, link: str, service: int, category_id: int, smm: int):
#     user = await get_user(uid)
#     await models.Order.objects.create(
#         user=user,
#         order_id=order_id,
#         category=category,
#         quantity=quantity,
#         link=link,
#         price=price,
#         profit=profit,
#         status=strings.PENDING,
#         bot_admin_profit=bot_admin_profit
#     )
#     await models.OrderRetry.objects.create(
#         order_id=order_id,
#         service=service,
#         category=category_id,
#         smm=smm,
#     )

#
# async def get_orders(uid: int):
#     user = await get_user(uid)
#     if user:
#         return await models.Order.objects.filter(user=user).order_by('-id')
#     else:
#         raise Exception("User not found")


# async def update_user_balance(user_or_uid: Union[models.ClientBotUser, int], amount):
#     if isinstance(user_or_uid, int):
#         user_or_uid = await get_user(user_or_uid)
#     user_or_uid.balance += amount
#     await user_or_uid.save()


async def users_count(bot: Bot):
    # bot = await get_bot(bot)
    return await models.ClientBotUser.objects.filter(bot=bot).count()


# async def earned():
#     bot = await get_bot(Bot.get_current())
#     orders = await models.Order.objects.filter(user__bot=bot, status=strings.COMPLETED)
#     total_earned = sum(order.bot_admin_profit for order in orders)
#     return f"{total_earned:.2f}"

@sync_to_async
def get_all_users_list(bot: Bot) -> list:
    """Return list of users for bot"""
    try:
        logger.info(f"Getting all users list for bot {bot.token}")
        return list(models.ClientBotUser.objects.filter(bot__token=bot.token))
    except Exception as e:
        logger.error(f"Error getting users list: {e}", exc_info=True)
        return []

@sync_to_async
def get_users_count(bot: Bot) -> int:
    """Get count of users"""
    try:
        logger.info(f"Getting users count for bot {bot.token}")
        return models.ClientBotUser.objects.filter(bot__token=bot.token).count()
    except Exception as e:
        logger.error(f"Error getting users count: {e}", exc_info=True)
        return 0

@sync_to_async
def get_all_users(bot: Bot):
    try:
        logger.info(f"Getting all users for bot {bot.token}")
        # bot token bo'yicha filter qo'shamiz
        return models.ClientBotUser.objects.filter(bot__token=bot.token)
    except Exception as e:
        logger.error(f"Error getting all users: {e}", exc_info=True)
        return []

async def send_message(message: types.Message, users: list):
    good = []
    bad = []

    for user in users:
        try:
            await message.copy_to(user.uid, reply_markup=message.reply_markup)  # uid ga o'zgartirildi
            good.append(user.uid)
            await asyncio.sleep(0.1)
        except Exception as e:
            logger.error(f"Error sending message to user {user.uid}: {e}")
            bad.append(user.uid)

    await message.answer(
        f'Рассылка завершена!\n\n'
        f'Успешно: {len(good)}\n'
        f'Неуспешно: {len(bad)}'
    )

async def get_main_bot_user(uid: int):
    return await models.Bot.objects.filter(uid=uid).first()


async def get_all_users_count(bot: Bot):
    return await models.ClientBotUser.objects.filter(bot__token=bot.token).count()


async def get_new_users_count(bot: Bot):
    today = datetime.now(tz=timezone.utc)
    return await models.ClientBotUser.objects.filter(
        bot__token=bot.token,
        created_at__year=today.year,
        created_at__month=today.month,
        created_at__day=today.day
    ).count()


# async def add_to_favourites(user_id: int, service: int, smm: int, category: int) -> bool:
#     """Добавить в избранное"""
#     user = await get_user(user_id)
#     bot = await user.bot
#     record = await get_favourite_by_id(user_id, service)
#     if not record:
#         await models.FavouritesModel.create(
#             user=user,
#             bot=bot,
#             service=service,
#             smm=smm,
#             category=category,
#         )
#         return True
#     return False


# async def task_admin_export_history(uid: int, bot_username):
#     user = await models.MainBotUser.filter(uid=uid).first()
#     bot = await models.Bot.filter(owner=user, username=bot_username).first()
#     wb = Workbook()
#     ws_client_orders = wb.create_sheet("История")
#     ws_referals = wb.create_sheet("Рефералы")
#     ws_payouts = wb.create_sheet("Выводы")
#     ws_client_orders.append(['Клиент', 'Дата', 'Сумма', 'Заработок', ])
#     ws_referals.append(['Клиент', 'Дата', 'Сумма', 'Заработок', ])
#     ws_payouts.append(['Дата', 'Сумма', ])
#     plus = 0
#     all_payouts = 0
#     reff = 0
#     clients = await models.ClientBotUser.filter(bot=bot)
#     for client in clients:
#         orders = await models.Order.filter(status__in=["Partial", 'Completed'], user=client, )
#         for order in orders:
#             plus += order.bot_admin_profit
#             ws_client_orders.append(
#                 [client.uid, order.created_at.strftime("%d.%m.%Y"), order.price, order.bot_admin_profit])
#     ws_client_orders.append(['Итого:', '', plus, ''])
#     mes = await models.ClientBotUser.filter(uid=uid)
#     for me in mes:
#         inviters = await models.ClientBotUser.filter(inviter=me)
#         for inviter in inviters:
#             ord_inviter = await models.Order.filter(status__in=["Partial", 'Completed'], user=inviter, )
#             for order in ord_inviter:
#                 reff += order.price * 0.05
#                 ws_referals.append(
#                     [inviter.uid, order.created_at.strftime("%d.%m.%Y"), order.price, order.price * 0.05])
#     ws_referals.append(['Итого:', '', reff, ''])
#     payouts = await models.Payout.filter(user=user, payout_status="success")
#     for payout in payouts:
#         ws_payouts.append([payout.created_at.strftime("%d.%m.%Y"), payout.payout_amount])
#         all_payouts += payout.payout_amount
#     ws_payouts.append(['Итого:', all_payouts])
#     user.balance = plus - all_payouts
#     file_name = f"export-{uid}.xlsx"
#     wb.save(file_name)
#     bot_text = "Не создан"
#     if bot:
#         bot_text = f"@{bot.username}\n"
#         async with Bot(token=bot.token, session=bot_session).context(auto_close=False) as _bot:
#             await _bot.send_message(
#                 uid,
#                 f"Бот: {bot_text}\nЗаработано: {plus}\nВывод: {all_payouts}\nКлиентов: {len(inviters)}\nРефка: {reff}\nБаланс: {plus + reff - all_payouts}")
#             await _bot.send_document(uid, document=FSInputFile(file_name, filename=file_name))
#     else:
#         await main_bot.send_message(
#             uid,
#             f"Бот: Не создан\nЗаработано: {plus}\nВывод: {all_payouts}\nКлиентов: {len(inviters)}\nРефка: {reff}\nБаланс: {plus + reff - all_payouts}")
#         await main_bot.send_document(uid, document=FSInputFile(file_name, filename=file_name))
#     os.remove(file_name)


# def get_domain(url):
#     pattern = r"https?://(?:www\.)?([a-zA-Z0-9-]+)\..*"
#     match = re.match(pattern, url)
#     return match.group(1) if match else "None"

@sync_to_async
def add_to_analitic_data(bot_username: str, link: str, ignore_domain: bool = False):
    now = datetime.now()
    domain = get_domain(link) if not ignore_domain else link
    instance = models.DownloadAnalyticsModel.objects.filter(bot_username=bot_username, domain=domain,
                                                                  date__gte=now).first()
    if not instance:
        models.DownloadAnalyticsModel.objects.create(
            bot_username=bot_username,
            domain=domain,
            count=1,
            date=now,
        )
    else:
        instance.count += 1
        instance.save()

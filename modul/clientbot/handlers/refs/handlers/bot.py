import time
import traceback
import asyncio  # Asyncio uchun import

import aiogram
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.filters import BaseFilter
from aiogram.fsm.context import FSMContext
from django.db import transaction
from django.utils import html

from modul import models
from modul.clientbot.handlers.refs.keyboards.buttons import *
from modul.clientbot.handlers.refs.shortcuts import *
from modul.clientbot.handlers.refs.data.states import PaymentState
import logging
from modul.clientbot import shortcuts
from modul.loader import client_bot_router
from aiogram.types import Message, BotCommand, CallbackQuery
from modul.clientbot.handlers.refs.keyboards.buttons import main_menu_bt
from modul.clientbot.handlers.refs.shortcuts import (
    add_user, add_ref, check_user, check_ban, get_user_name, plus_ref, plus_money
)
from aiogram import F, Bot

from modul.models import User, SystemChannel

logger = logging.getLogger(__name__)


# TODO изменить метод получения айди админа
async def admin_id_func(user_id, bot):
    bot_db = await shortcuts.get_bot(bot)

    if not bot_db:
        logger.error("Bot ma'lumotlari topilmadi.")
        return False

    if not bot_db.owner:
        logger.error(f"Botda egasi mavjud emas: Bot ID = {bot_db.id}")
        return False

    logger.info(f"Tekshirilayotgan foydalanuvchi: {user_id}, Bot egasi: {bot_db.owner.uid}")
    return user_id == bot_db.owner.uid


async def check_channels(message) -> bool:
    try:
        channels = await get_channels_for_check()
        print("Checking channels:", channels)  # Debug uchun

        if not channels:
            return True

        bot_db = await shortcuts.get_bot(message.bot)
        admin_id = bot_db.owner.uid
        if message.from_user.id == admin_id:
            return True

        is_subscribed = True
        for channel_id, channel_url in channels:
            try:
                member = await message.bot.get_chat_member(
                    chat_id=channel_id,
                    user_id=message.from_user.id
                )
                print(f"Channel {channel_id} status: {member.status}")

                if member.status == 'left':
                    is_subscribed = False
                    await message.bot.send_message(
                        chat_id=message.from_user.id,
                        text="Для использования бота подпишитесь на наших спонсоров",
                        reply_markup=await channels_in(channels, message.bot)
                    )
                    return False

            except TelegramBadRequest as e:
                logger.error(f"Error checking channel {channel_id}: {e}")
                continue
            except Exception as e:
                logger.error(f"Error checking subscription: {e}")
                continue

        return is_subscribed

    except Exception as e:
        logger.error(f"General error in check_channels: {e}")
        return False


@sync_to_async
@transaction.atomic
def save_user(u, bot: Bot, link=None, inviter=None):
    try:
        bot_instance = models.Bot.objects.select_related("owner").filter(token=bot.token).first()
        if not bot_instance:
            raise ValueError(f"Bot with token {bot.token} not found")

        user, user_created = models.UserTG.objects.update_or_create(
            uid=u.id,
            defaults={
                "username": u.username,
                "first_name": u.first_name,
                "last_name": u.last_name,
                "user_link": link,
            }
        )

        client_user, client_user_created = models.ClientBotUser.objects.update_or_create(
            uid=u.id,
            bot=bot_instance,
            defaults={
                "user": user,
                "inviter": inviter,
                "current_ai_limit": 12 if user_created else 0,
            }
        )

        return client_user

    except Exception as e:
        logger.error(f"Error saving user {u.id}: {e}")
        raise


@sync_to_async
@transaction.atomic
def process_referral_bonus(new_user_id: int, referrer_id: int, bot_token: str):
    """
    Har bot uchun alohida referral bonus berish
    """
    try:
        from modul.models import Bot, UserTG, ClientBotUser, AdminInfo

        print(f"🔧 DEBUG: process_referral_bonus called - new_user: {new_user_id}, referrer: {referrer_id}")

        # Botni topish
        current_bot = Bot.objects.get(token=bot_token)
        print(f"🔧 DEBUG: Found bot: {current_bot.username}")

        # Referrer ni shu bot uchun tekshirish
        referrer_client = ClientBotUser.objects.filter(
            uid=referrer_id,
            bot=current_bot
        ).first()
        if not referrer_client:
            print(f"❌ Referrer {referrer_id} not found for bot {current_bot.username}")
            return False, 0
        print(
            f"🔧 DEBUG: Found referrer ClientBotUser: {referrer_client.uid}, current balance: {referrer_client.balance}")

        # Yangi foydalanuvchini shu bot uchun tekshirish
        new_user_client = ClientBotUser.objects.filter(
            uid=new_user_id,
            bot=current_bot
        ).first()

        if not new_user_client:
            print(f"❌ New user {new_user_id} not found for bot {current_bot.username}")
            return False, 0
        print(
            f"🔧 DEBUG: Found new user ClientBotUser: {new_user_client.uid}, current inviter: {new_user_client.inviter}")

        # Allaqachon referral bonus olinganmi tekshirish
        if new_user_client.inviter is not None:
            print(f"⚠️ User {new_user_id} already has referrer: {new_user_client.inviter.uid}")
            return False, 0

        # Bonus miqdorini aniqlash
        admin_info = AdminInfo.objects.filter(bot_token=bot_token).first()
        bonus_amount = float(admin_info.price) if admin_info and admin_info.price else 3.0
        print(f"🔧 DEBUG: Bonus amount: {bonus_amount}")

        # FAQAT SHU BOT UCHUN BALANSNI YANGILASH
        print(
            f"🔧 DEBUG: BEFORE UPDATE - Referrer bot balance: {referrer_client.balance}, refs: {referrer_client.referral_count}")

        # Referrer balansini yangilash (faqat shu bot uchun)
        referrer_client.referral_count += 1
        referrer_client.referral_balance += bonus_amount
        referrer_client.balance += bonus_amount
        referrer_client.save()

        # UserTG ni ham yangilaymiz (umumiy statistika uchun)
        referrer_user = UserTG.objects.filter(uid=referrer_id).first()
        if referrer_user:
            referrer_user.refs += 1
            referrer_user.balance += bonus_amount
            referrer_user.save()

        print(
            f"🔧 DEBUG: AFTER UPDATE - Referrer bot balance: {referrer_client.balance}, refs: {referrer_client.referral_count}")

        # Inviter ni belgilash
        new_user_client.inviter = referrer_client
        new_user_client.save()

        print(
            f"✅ Referral bonus processed for bot {current_bot.username}: {referrer_id} got {bonus_amount} for referring {new_user_id}")
        print(f"🔗 Set inviter {referrer_id} for user {new_user_id} in bot {current_bot.username}")
        return True, bonus_amount

    except Exception as e:
        print(f"❌ Error in process_referral_bonus: {e}")
        traceback.print_exc()
        return False, 0

async def banned(message):
    check = await check_ban(message.from_user.id)
    if check:
        await message.bot.send_message(chat_id=message.from_user.id,
                                       text="Вы были заблокированы")
        return False
    return True


async def check_referral_status(user_id: int) -> dict:
    """
    Check user's referral status and rewards
    """
    user = await sync_to_async(UserTG.objects.filter(uid=user_id).first)()
    if not user:
        return {
            'status': False,
            'message': 'User not found'
        }

    referrals = await sync_to_async(
        lambda: UserTG.objects.filter(invited_id=user_id).count()
    )()

    return {
        'status': True,
        'refs_count': referrals,
        'balance': user.balance,
        'earned_from_refs': user.balance  # You might want to track this separately
    }


async def start_ref(message: Message, bot: Bot, state: FSMContext = None, referral: str = None):
    try:
        logger.info(f"Checking channels for user {message.from_user.id}")
        channels_checker = await check_channels(message)
        logger.info(f"Channels check result: {channels_checker}")

        # Foydalanuvchi ro'yxatdan o'tganligini tekshirish
        is_registered = await check_user(message.from_user.id)
        is_banned = await check_ban(message.from_user.id)

        if is_banned:
            logger.info(f"User {message.from_user.id} is banned, exiting")
            return

        # Kanal tekshiruvi o'tmaganda va referral bo'lsa, referralni state ga saqlaymiz
        if not channels_checker and referral:
            try:
                referrer_id = int(referral)
                # Faqat agar state FSMContext bo'lsa saqlaymiz
                if state and isinstance(state, FSMContext):
                    await state.update_data(referrer_id=referrer_id)
                    logger.info(f"Stored referrer_id {referrer_id} in state for user {message.from_user.id}")
            except (ValueError, TypeError) as e:
                logger.error(f"Invalid referral ID: {referral}, error: {e}")
            return  # Kanallar tekshiruvi o'tmadi, qaytamiz

        # MUHIM: Agar foydalanuvchi allaqachon ro'yxatdan o'tgan bo'lsa
        if is_registered:
            logger.info(f"User {message.from_user.id} is already registered, skipping referral processing")
            # Faqat xabar yuborish kerak
            await message.answer(
                f"🎉 Привет, {message.from_user.first_name}",
                reply_markup=await main_menu_bt()
            )
            logger.info(f"Welcome message sent to registered user {message.from_user.id}")
            # State'ni tozalash, faqat agar u FSMContext bo'lsa
            if state and isinstance(state, FSMContext):
                await state.clear()
            return

        # Referral jarayoni - faqat yangi foydalanuvchilar uchun
        if referral and not is_registered:
            try:
                referrer_id = int(referral)
                logger.info(f"Processing referral ID: {referrer_id} for user {message.from_user.id}")

                # O'zini o'zi refer qilishni tekshirish - qattiq tekshirish
                if str(referrer_id) == str(message.from_user.id):
                    logger.warning(f"SELF-REFERRAL DETECTED: User {message.from_user.id} tried to refer themselves!")
                    await add_user(
                        tg_id=message.from_user.id,
                        user_name=message.from_user.first_name,
                        bot_token=message.bot.token
                    )
                    await message.answer(
                        "❌ Siz o'zingizni taklif qila olmaysiz!",
                        reply_markup=await main_menu_bt()
                    )
                    logger.info(f"Self-referral blocked for user {message.from_user.id}")
                    # State'ni tozalash, faqat agar u FSMContext bo'lsa
                    if state and isinstance(state, FSMContext):
                        await state.clear()
                    return  # Referral jarayoni to'xtatiladi

                # Referrer haqiqatan ham mavjudligini tekshirish
                referrer_exists = await check_user(referrer_id)
                if not referrer_exists:
                    logger.warning(f"Referrer {referrer_id} does not exist in database")
                    await add_user(
                        tg_id=message.from_user.id,
                        user_name=message.from_user.first_name,
                        bot_token=message.bot.token
                    )
                    await message.answer(
                        f"🎉 Привет, {message.from_user.first_name}",
                        reply_markup=await main_menu_bt()
                    )
                    # State'ni tozalash, faqat agar u FSMContext bo'lsa
                    if state and isinstance(state, FSMContext):
                        await state.clear()
                    return

                # Foydalanuvchini qo'shamiz
                new_user = await add_user(
                    tg_id=message.from_user.id,
                    user_name=message.from_user.first_name,
                    invited="Referral",  # Referrerning statusi
                    invited_id=referrer_id,
                    bot_token=message.bot.token
                )

                if new_user:
                    # Referral statistikasini yangilash
                    @sync_to_async
                    @transaction.atomic
                    def update_referral():
                        try:
                            user_tg = UserTG.objects.select_for_update().get(uid=referrer_id)
                            admin_info = AdminInfo.objects.first()

                            if not admin_info:
                                logger.error("Admin info not found")
                                return False

                            price = float(admin_info.price or 10.0)
                            user_tg.refs += 1
                            user_tg.balance += price
                            user_tg.save()
                            logger.info(
                                f"Referral stats updated for {referrer_id}: refs={user_tg.refs}, balance={user_tg.balance}")
                            return True
                        except UserTG.DoesNotExist:
                            logger.error(f"User with ID {referrer_id} not found in database")
                            return False
                        except Exception as ex:
                            logger.error(f"Error in referral update: {ex}")
                            return False

                    referral_success = await update_referral()

                    if referral_success:
                        try:
                            user_name = html.escape(message.from_user.first_name)
                            user_profile_link = f'tg://user?id={message.from_user.id}'

                            # O'zgarishlar saqlanganligiga ishonch hosil qilish uchun 1 soniya kutamiz
                            # Bu bazaga o'zgarishlar yozilishi uchun imkon beradi
                            await asyncio.sleep(1)

                            await message.bot.send_message(
                                chat_id=referrer_id,
                                text=f"У вас новый реферал! <a href='{user_profile_link}'>{user_name}</a>",
                                parse_mode="HTML"
                            )
                            logger.info(f"Referral notification sent to {referrer_id}")
                        except TelegramForbiddenError:
                            logger.error(f"Cannot send message to user {referrer_id}")
                        except Exception as e:
                            logger.error(f"Error sending notification to referrer: {e}")
            except ValueError:
                logger.error(f"Invalid referral ID: {referral}")
                await add_user(
                    tg_id=message.from_user.id,
                    user_name=message.from_user.first_name,
                    bot_token=message.bot.token
                )
        elif not is_registered:
            logger.info(f"Adding new user {message.from_user.id} without referral")
            await add_user(
                tg_id=message.from_user.id,
                user_name=message.from_user.first_name,
                bot_token=message.bot.token
            )

        # Yangi foydalanuvchilarga xabar yuborish
        if not is_registered:
            logger.info(f"Sending welcome message to {message.from_user.id}")
            await message.answer(
                f"🎉 Привет, {message.from_user.first_name}",
                reply_markup=await main_menu_bt()
            )
            logger.info(f"Welcome message sent to {message.from_user.id}")

        # State'ni tozalash, faqat agar u FSMContext bo'lsa
        if state and isinstance(state, FSMContext):
            await state.clear()

    except Exception as e:
        logger.error(f"Error in start_ref: {e}")
        traceback.print_exc()  # Xato stack trace'ni ham chiqarish
        await message.answer(
            "Произошла ошибка. Попробуйте позже.",
            reply_markup=await main_menu_bt()
        )
        # Xatolik yuz berganda ham state'ni tozalash (faqat agar u FSMContext bo'lsa)
        if state and isinstance(state, FSMContext):
            await state.clear()


class RefsBotFilter(BaseFilter):
    async def __call__(self, message: Message, bot: Bot) -> bool:
        bot_db = await shortcuts.get_bot(bot)
        return shortcuts.have_one_module(bot_db, "refs")


@client_bot_router.message(F.text == "💸Заработать", RefsBotFilter())
async def gain(message: Message, bot: Bot, state: FSMContext):
    bot_db = await shortcuts.get_bot(bot)
    await state.clear()
    if shortcuts.have_one_module(bot_db, 'refs'):
        channels_checker = await check_channels(message)
        checker_banned = await banned(message)
        if channels_checker and checker_banned:
            me = await bot.get_me()
            link = f"https://t.me/{me.username}?start={message.from_user.id}"

            price = await get_actual_price(bot.token)

            await message.bot.send_message(message.from_user.id,
                                           f"👥 Приглашай друзей и зарабатывай, за \nкаждого друга ты получишь {price}₽\n\n"
                                           f"🔗 Ваша ссылка для приглашений:\n {link}",
                                           reply_markup=await main_menu_bt())
    else:
        channels_checker = await check_channels(message)
        checker_banned = await banned(message)
        if channels_checker and checker_banned:
            me = await bot.get_me()
            link = f"https://t.me/{me.username}?start={message.from_user.id}"

            price = await get_actual_price(bot.token)

            await message.bot.send_message(message.from_user.id,
                                           f"👥 Приглашай друзей и зарабатывай, за \nкаждого друга ты получишь {price}₽\n\n"
                                           f"🔗 Ваша ссылка для приглашений:\n {link}"
                                           "\n Что бы вернуть функционал основного бота напишите /start",
                                           reply_markup=await main_menu_bt())


@client_bot_router.message(F.text == "📱Профиль")
async def profile(message: Message):
    try:
        channels_checker = await check_channels(message)
        is_banned = await check_ban(message.from_user.id)

        if not channels_checker or is_banned:
            return

        user_info = await get_user_info_db(message.from_user.id)

        if not user_info:
            try:
                await add_user(
                    tg_id=message.from_user.id,
                    user_name=message.from_user.first_name,
                    bot_token=message.bot.token
                )
                print(f"Added new user {message.from_user.id} from profile")

                user_info = await get_user_info_db(message.from_user.id)
                print(f"User info after adding: {user_info}")

                if not user_info:
                    await message.answer(
                        "Ошибка получения данных профиля. Попробуйте позже.",
                        reply_markup=await main_menu_bt()
                    )
                    return
            except Exception as e:
                print(f"Error adding user from profile: {e}")
                await message.answer(
                    "Ошибка получения данных профиля",
                    reply_markup=await main_menu_bt()
                )
                return

        # Получаем информацию о пользователе в этом боте
        bot_user_info = await get_bot_user_info(message.from_user.id, message.bot.token)
        print(f"Bot user info for {message.from_user.id}: {bot_user_info}")

        # Используем данные по конкретному боту или нули, если информация не найдена
        bot_balance = bot_user_info[0] if bot_user_info else 0
        bot_referrals = bot_user_info[1] if bot_user_info else 0

        profile_text = (
            f"📱Профиль\n\n"
            f"📝 Ваше имя: {message.from_user.full_name}\n"
            f"🆔 Ваш ID: <code>{user_info[1]}</code>\n"
            f"==========================\n"
            f"💳 Баланс: {bot_balance}₽\n"
            f"👥 Всего друзей: {bot_referrals}\n"
            f"==========================\n"
        )

        await message.answer(
            profile_text,
            parse_mode="html",
            reply_markup=await payment_in()
        )

    except Exception as e:
        logger.error(f"Error in profile handler: {e}")
        await message.answer(
            "Произошла ошибка при загрузке профиля",
            reply_markup=await main_menu_bt()
        )


@client_bot_router.message(F.text == "ℹ️Инфо")
async def info(message: Message):
    channels_checker = await check_channels(message)
    checker_banned = await banned(message)

    user_info = await get_user_info_db(message.from_user.id)

    # Agar foydalanuvchi topilmasa, uni qo'shamiz
    if not user_info:
        try:
            # Yangi foydalanuvchini qo'shish
            await add_user(
                tg_id=message.from_user.id,
                user_name=message.from_user.first_name,
                bot_token=message.bot.token
            )
            print(f"Added new user {message.from_user.id} from info")

            # Ma'lumotlarni qayta olish
            user_info = await get_user_info_db(message.from_user.id)

            if not user_info:
                await message.answer(
                    "Ошибка получения данных профиля. Попробуйте позже.",
                    reply_markup=await main_menu_bt()
                )
                return
        except Exception as e:
            print(f"Error adding user from info: {e}")
            await message.answer(
                "Ошибка получения данных профиля",
                reply_markup=await main_menu_bt()
            )
            return

    if channels_checker and checker_banned:
        # Текущий бот
        bot_token = message.bot.token

        # Получаем количество пользователей текущего бота из базы данных
        total_users_count = await get_total_users_count(bot_token)
        refs_count = user_info[3]  # Количество рефералов пользователя

        admin_user = await get_admin_user(bot_token)
        print(admin_user, "admin_user")
        bot_user_info = await get_bot_user_info(message.from_user.id, message.bot.token)

        await message.bot.send_message(
            message.from_user.id,
            f"👥 Всего пользователей: {total_users_count}\n"
            f"👨‍👨‍👦 Друзья: {bot_user_info[1]}\n",
            reply_markup=await admin_in(admin_user)
        )


@sync_to_async
def remove_sponsor_channel(channel_id):
    """Faqat sponsor kanallarni o'chirish"""
    try:
        from modul.models import ChannelSponsor
        deleted_count = ChannelSponsor.objects.filter(chanel_id=channel_id).delete()
        print(f"Removed invalid sponsor channel {channel_id}, deleted: {deleted_count[0]}")
    except Exception as e:
        print(f"Error removing sponsor channel {channel_id}: {e}")


@sync_to_async
def get_channels_with_type_for_check():
    try:
        from modul.models import ChannelSponsor, SystemChannel
        sponsor_channels = ChannelSponsor.objects.all()
        sponsor_list = [(str(c.chanel_id), '', 'sponsor') for c in sponsor_channels]
        system_channels = SystemChannel.objects.filter(is_active=True)
        system_list = [(str(c.channel_id), c.channel_url, 'system') for c in system_channels]
        all_channels = sponsor_list + system_list
        print(f"Found sponsor channels: {len(sponsor_list)}, system channels: {len(system_list)}")
        return all_channels
    except Exception as e:
        print(f"Error getting channels with type: {e}")
        return []

@client_bot_router.callback_query(F.data == "check_chan",RefsBotFilter())
async def check_chan_callback(query: CallbackQuery, state: FSMContext):
    try:
        bot = query.bot
        user_id = query.from_user.id
        print(f"🔍 NEW check_chan callback triggered for user {user_id}")
        state_data = await state.get_data()
        print(f"📊 State data for user {user_id}: {state_data}")
        referrer_id = state_data.get('referrer_id') or state_data.get('referral')
        print(f"👤 Referrer_id from state for user {user_id}: {referrer_id}")

        channels = await get_channels_with_type_for_check()
        print(f"📡 Channels for user {user_id}: {channels}")
        not_subscribed_channels = []

        if not channels:
            print(f"✅ No channels to check for user {user_id}")
            is_subscribed = True
        else:
            is_subscribed = True
            invalid_channels_to_remove = []

            for channel_id, channel_url, channel_type in channels:
                try:
                    if channel_type == 'system':
                        from modul.loader import main_bot
                        member = await main_bot.get_chat_member(
                            chat_id=int(channel_id),
                            user_id=user_id
                        )
                        print(f"📢 System channel {channel_id} status for user {user_id}: {member.status}")
                    else:
                        member = await query.bot.get_chat_member(
                            chat_id=int(channel_id),
                            user_id=user_id
                        )
                        print(f"📢 Sponsor channel {channel_id} status for user {user_id}: {member.status}")

                    if member.status == 'left':
                        is_subscribed = False
                        print(f"❌ User {user_id} not subscribed to channel {channel_id}")

                        try:
                            if channel_type == 'system':
                                chat_info = await main_bot.get_chat(chat_id=int(channel_id))
                            else:
                                chat_info = await query.bot.get_chat(chat_id=int(channel_id))

                            not_subscribed_channels.append({
                                'id': channel_id,
                                'title': chat_info.title,
                                'invite_link': channel_url or chat_info.invite_link or f"https://t.me/{channel_id.strip('-')}"
                            })
                        except Exception as e:
                            print(f"⚠️ Error getting chat info for channel {channel_id}: {e}")
                            not_subscribed_channels.append({
                                'id': channel_id,
                                'title': f"Канал {channel_id}",
                                'invite_link': channel_url or f"https://t.me/{channel_id.strip('-')}"
                            })
                except Exception as e:
                    print(f"⚠️ Error checking channel {channel_id} (type: {channel_type}): {e}")

                    if channel_type == 'sponsor':
                        invalid_channels_to_remove.append(channel_id)
                        print(f"Added invalid sponsor channel {channel_id} to removal list")
                    else:
                        print(f"System channel {channel_id} error (ignoring): {e}")
                    continue

            if invalid_channels_to_remove:
                for channel_id in invalid_channels_to_remove:
                    await remove_sponsor_channel(channel_id)

        if not is_subscribed:
            print(f"🚫 User {user_id} not subscribed to all channels")

            await query.answer("⚠️ Вы не подписались на все каналы! Пожалуйста, подпишитесь и нажмите кнопку снова.",
                               show_alert=True)

            channels_text = "📢 <b>Для использования бота необходимо подписаться на каналы:</b>\n\n"

            kb = InlineKeyboardBuilder()

            for index, channel in enumerate(not_subscribed_channels):
                title = channel['title']
                invite_link = channel['invite_link']

                channels_text += f"{index + 1}. {title}\n"
                kb.button(text=f"📢 {title}", url=invite_link)

            kb.button(text="✅ Проверить подписку", callback_data="check_chan")
            kb.adjust(1)  # Har bir qatorda 1 ta tugma

            try:
                import time
                now = int(time.time())
                await query.message.edit_text(
                    channels_text + f"\n\nПосле подписки на все каналы нажмите кнопку «Проверить подписку».",
                    reply_markup=kb.as_markup(),
                    parse_mode="HTML"
                )
            except aiogram.exceptions.TelegramBadRequest as e:
                if "message is not modified" in str(e):
                    pass
                else:
                    try:
                        await query.message.delete()
                    except:
                        pass

                    await query.bot.send_message(
                        chat_id=user_id,
                        text=channels_text + "\n\nПосле подписки на все каналы нажмите кнопку «Проверить подписку».",
                        reply_markup=kb.as_markup(),
                        parse_mode="HTML"
                    )

            return

        print(f"✅ User {user_id} subscribed to all channels")

        # Foydalanuvchi ro'yxatdan o'tganmi tekshirish
        is_registered = await check_user(user_id)
        print(f"📝 User {user_id} registration status: {is_registered}")

        # FAQAT yangi foydalanuvchi uchun referral jarayonini bajarish
        if not is_registered:
            # Foydalanuvchini bazaga qo'shish
            new_user = await add_user(
                tg_id=user_id,
                user_name=query.from_user.first_name,
                invited="Direct" if not referrer_id else "Referral",
                invited_id=int(referrer_id) if referrer_id else None,
                bot_token=query.bot.token
            )
            print(f"➕ Added user {user_id} to database, result: {new_user}")

            # YAGONA REFERRAL JARAYONI
            if referrer_id and str(referrer_id).isdigit():
                ref_id = int(referrer_id)
                if ref_id != user_id:  # O'zini referral qilmaslik
                    print(f"🔄 Processing referral for NEW user {user_id} from {ref_id}")

                    success, reward = await process_referral_bonus(user_id, ref_id, bot.token)
                    print(f"✅ Referral bonus result: success={success}, reward={reward}")

                    if success:
                        try:
                            user_name = html.escape(query.from_user.first_name)
                            user_profile_link = f'tg://user?id={user_id}'

                            await asyncio.sleep(1)

                            await query.bot.send_message(
                                chat_id=ref_id,
                                text=f"У вас новый реферал! <a href='{user_profile_link}'>{user_name}</a>\n"
                                     f"💰 Получено: {reward}₽",
                                parse_mode="HTML"
                            )
                            print(f"📨 Sent referral notification to {ref_id} about user {user_id}")
                        except Exception as e:
                            print(f"⚠️ Error sending notification to referrer {ref_id}: {e}")
                else:
                    print(f"🚫 Self-referral detected: user {user_id} trying to refer themselves")
        else:
            print(f"ℹ️ User {user_id} already registered, skipping referral process")

        # Foydalanuvchiga asosiy menyuni ko'rsatish
        try:
            await query.bot.delete_message(
                chat_id=user_id,
                message_id=query.message.message_id
            )
            print(f"🗑️ Deleted channel check message for user {user_id}")
        except Exception as e:
            print(f"⚠️ Error deleting message for user {user_id}: {e}")

        await query.bot.send_message(
            user_id,
            f"🎉 Привет, {query.from_user.first_name}",
            reply_markup=await main_menu_bt()
        )
        print(f"💬 Sent welcome message to user {user_id}")

        # State'ni tozalash
        await state.clear()
        print(f"🧹 Cleared state for user {user_id}")

    except Exception as e:
        print(f"⚠️ Error in check_chan_callback for user {query.from_user.id}: {e}")
        traceback.print_exc()

        # Har qanday xatolik yuz berganda state'ni tozalash
        try:
            await state.clear()
        except:
            pass

@sync_to_async
def check_user_in_specific_bot(user_id, bot_token):
    """
    Foydalanuvchi konkret botda ro'yxatdan o'tganmi tekshirish
    """
    try:
        from modul.models import Bot, ClientBotUser
        bot_obj = Bot.objects.get(token=bot_token)
        client_user = ClientBotUser.objects.filter(
            uid=user_id,
            bot=bot_obj
        ).first()
        return client_user is not None
    except Exception as e:
        print(f"Error checking user in specific bot: {e}")
        return False


@sync_to_async
@transaction.atomic
def add_user_safely(tg_id, user_name, invited_type, invited_id, bot_token):
    """
    Foydalanuvchini konkret bot uchun qo'shish
    """
    try:
        from modul.models import Bot, UserTG, ClientBotUser

        print(f"🔧 DEBUG: add_user_safely called for user {tg_id} in bot with token {bot_token}")

        # Botni topish
        bot_obj = Bot.objects.get(token=bot_token)

        # Bu bot uchun allaqachon mavjudligini tekshirish
        existing_client = ClientBotUser.objects.filter(
            uid=tg_id,
            bot=bot_obj
        ).first()

        if existing_client:
            print(f"⚠️ User {tg_id} already exists for bot {bot_obj.username}")
            return False

        # UserTG ni yaratish yoki olish (umumiy)
        user_tg, created = UserTG.objects.get_or_create(
            uid=tg_id,
            defaults={
                'username': user_name,
                'first_name': user_name,
            }
        )

        if created:
            print(f"✅ DEBUG: Created new UserTG for {tg_id}")
        else:
            print(f"ℹ️ DEBUG: UserTG already exists for {tg_id}")

        # ClientBotUser yaratish - BU BOT UCHUN ALOHIDA
        client_user = ClientBotUser.objects.create(
            uid=tg_id,
            user=user_tg,
            bot=bot_obj,
            inviter=None,  # Bu yerda None
            balance=0,  # Bu botdagi balans
            referral_count=0,  # Bu botdagi referrallar
            referral_balance=0  # Bu botdagi referral bonuslari
        )

        print(f"✅ DEBUG: Created ClientBotUser for {tg_id} in bot {bot_obj.username} WITH INVITER=None")
        return True

    except Exception as e:
        print(f"❌ Error in add_user_safely: {e}")
        traceback.print_exc()
        return False


@client_bot_router.callback_query(F.data.in_(["payment"]))
async def call_backs(query: CallbackQuery, state: FSMContext):
    if query.data == "payment":
        balance_q = await get_user_info_db(query.from_user.id)
        balance = balance_q[2]
        min_amount = await get_actual_min_amount(query.bot.token)
        if min_amount is None:
            min_amount = 0
        check_wa = await check_for_wa(query.from_user.id)

        if min_amount > 0 and balance < min_amount:
            await query.message.bot.answer_callback_query(
                query.id,
                text=f"🚫Минимальная сумма вывода: {min_amount}",
                show_alert=True
            )
        elif check_wa:
            await query.message.bot.answer_callback_query(query.id, text="⏳Вы уже оставили заявку. Ожидайте",
                                                          show_alert=True)
        elif balance >= min_amount:
            await query.bot.send_message(query.from_user.id, "💳Введите номер вашей карты",
                                         reply_markup=await cancel_bt())
            await state.set_state(PaymentState.get_card)

    elif query.data == "check_chan":
        print('525 refs')
        # State'dan referrer_id ni olishga harakat qilamiz
        state_data = await state.get_data()
        referrer_id = state_data.get('referrer_id')

        # O'ZGARISH: check_channels o'rniga to'g'ri channel check
        checking = await check_channels_properly(query)

        if checking:
            is_registered = await check_user(query.from_user.id)

            try:
                await query.bot.delete_message(chat_id=query.from_user.id, message_id=query.message.message_id)
            except Exception as e:
                logger.error(f"Error deleting message: {e}")

            await query.bot.send_message(
                query.from_user.id,
                f"🎉Привет, {query.from_user.first_name}",
                reply_markup=await main_menu_bt()
            )

            # Yangi foydalanuvchi va referral mavjud bo'lsa, referral jarayonini bajaramiz
            if not is_registered and referrer_id:
                try:
                    ref_id = int(referrer_id)
                    # Referrer ID o'zimizniki emas ekanligini tekshiramiz
                    if ref_id != query.from_user.id:
                        logger.info(f"Processing referral for new user {query.from_user.id} from {ref_id}")

                        # Foydalanuvchi qo'shish
                        new_user = await add_user(
                            tg_id=query.from_user.id,
                            user_name=query.from_user.first_name,
                            invited="Referral",
                            invited_id=ref_id,
                            bot_token=query.bot.token
                        )

                        if new_user:
                            # Referralga bonus qo'shish
                            @sync_to_async
                            @transaction.atomic
                            def update_referrer_bonus():
                                try:
                                    # Referrer mavjudligini tekshirish
                                    user_tg = UserTG.objects.select_for_update().get(uid=ref_id)
                                    admin_info = AdminInfo.objects.first()

                                    price = float(admin_info.price) if admin_info and admin_info.price else 10.0

                                    # Balansni va referallar sonini yangilash
                                    user_tg.refs += 1
                                    user_tg.balance += price
                                    user_tg.save()

                                    logger.info(
                                        f"Updated referrer {ref_id} stats: refs={user_tg.refs}, balance={user_tg.balance}")
                                    return True
                                except UserTG.DoesNotExist:
                                    logger.error(f"Referrer {ref_id} does not exist")
                                    return False
                                except Exception as e:
                                    logger.error(f"Error updating referrer: {e}")
                                    return False

                            update_success = await update_referrer_bonus()

                            if update_success:
                                # Referral xabarini yuborish
                                try:
                                    user_name = html.escape(query.from_user.first_name)
                                    user_profile_link = f'tg://user?id={query.from_user.id}'
                                    await query.bot.send_message(
                                        chat_id=ref_id,
                                        text=f"У вас новый реферал! <a href='{user_profile_link}'>{user_name}</a>",
                                        parse_mode="HTML"
                                    )
                                    logger.info(f"Sent referral notification to {ref_id}")
                                except Exception as e:
                                    logger.error(f"Error sending referral notification: {e}")
                        else:
                            logger.error(f"Failed to add new user {query.from_user.id}")
                except ValueError:
                    logger.error(f"Invalid referrer_id in state: {referrer_id}")

            # State ni tozalash
            await state.clear()


# YANGI FUNKSIYA: To'g'ri channel check
async def check_channels_properly(query):
    """Kanallarni to'g'ri tekshirish - system kanallar main bot orqali"""
    try:
        user_id = query.from_user.id

        # Kanallarni olish
        channels = await get_channels_with_type_for_check()

        if not channels:
            return True  # Kanal yo'q bo'lsa, o'tkazib yuborish

        invalid_channels_to_remove = []

        for channel_id, channel_url, channel_type in channels:
            try:
                # Channel type ga qarab bot tanlash
                if channel_type == 'system':
                    from modul.loader import main_bot
                    member = await main_bot.get_chat_member(chat_id=int(channel_id), user_id=user_id)
                    print(f"System channel {channel_id} checked via main_bot: {member.status}")
                else:
                    member = await query.bot.get_chat_member(chat_id=int(channel_id), user_id=user_id)
                    print(f"Sponsor channel {channel_id} checked via current_bot: {member.status}")

                if member.status in ['left', 'kicked']:
                    # Obuna bo'lmagan
                    await query.answer("❌ Вы еще не подписались на все каналы!", show_alert=True)
                    return False

            except Exception as e:
                print(f"Error checking channel {channel_id} (type: {channel_type}): {e}")

                # Faqat sponsor kanallarni o'chirish
                if channel_type == 'sponsor':
                    invalid_channels_to_remove.append(channel_id)
                    print(f"Added invalid sponsor channel {channel_id} to removal list")
                else:
                    # System kanallar uchun faqat log
                    print(f"System channel {channel_id} error (ignoring): {e}")

                # Xatolik bo'lsa ham obuna bo'lmagan deb hisoblaymiz
                await query.answer("❌ Ошибка проверки каналов!", show_alert=True)
                return False

        # Invalid sponsor kanallarni o'chirish
        if invalid_channels_to_remove:
            for channel_id in invalid_channels_to_remove:
                await remove_sponsor_channel(channel_id)

        # Barcha kanallarni tekshirib bo'ldik, hamma joyga obuna bo'lgan
        return True

    except Exception as e:
        print(f"Error in check_channels_properly: {e}")
        await query.answer("❌ Ошибка проверки!", show_alert=True)
        return False


async def process_new_user_referral(query, referrer_id):
    """Process referral for a new user after channel check"""
    try:
        logger.info(f"Processing new user referral. User: {query.from_user.id}, Referrer: {referrer_id}")

        # Foydalanuvchini qo'shamiz
        user_added = await add_user(
            tg_id=query.from_user.id,
            user_name=query.from_user.first_name,
            invited="Referral",
            invited_id=referrer_id,
            bot_token=query.bot.token
        )

        if not user_added:
            logger.error(f"Failed to add user {query.from_user.id}")
            return False

        logger.info(f"User {query.from_user.id} added successfully")

        # Referrer balansini yangilaymiz
        @sync_to_async
        @transaction.atomic
        def update_referrer():
            try:
                user_tg = UserTG.objects.select_for_update().get(uid=referrer_id)
                admin_info = AdminInfo.objects.first()

                if not admin_info:
                    logger.error("Admin info not found")
                    return False

                price = admin_info.price or 10.0
                user_tg.refs += 1
                user_tg.balance += float(price)
                user_tg.save()

                logger.info(f"Updated referrer {referrer_id}: refs={user_tg.refs}, balance={user_tg.balance}")
                return True
            except UserTG.DoesNotExist:
                logger.error(f"Referrer {referrer_id} not found in database")
                return False
            except Exception as e:
                logger.error(f"Error updating referrer: {e}")
                return False

        success = await update_referrer()

        if success:
            # Referrerga xabar yuboramiz
            try:
                user_name = html.escape(query.from_user.first_name)
                user_profile_link = f'tg://user?id={query.from_user.id}'

                # O'zgarishlar saqlanishini kutish
                await asyncio.sleep(1)

                await query.bot.send_message(
                    chat_id=referrer_id,
                    text=f"У вас новый реферал! <a href='{user_profile_link}'>{user_name}</a>",
                    parse_mode="HTML"
                )
                logger.info(f"Notification sent to referrer {referrer_id}")
            except TelegramForbiddenError:
                logger.error(f"Cannot send message to referrer {referrer_id} - forbidden")
            except TelegramBadRequest as e:
                logger.error(f"Bad request when sending notification to referrer {referrer_id}: {e}")
            except Exception as e:
                logger.error(f"Error sending notification to referrer {referrer_id}: {e}")
        else:
            logger.error(f"Failed to update referrer {referrer_id}")

        return success
    except Exception as e:
        logger.error(f"Error in process_new_user_referral: {e}")
        return False


@client_bot_router.message(PaymentState.get_card)
async def get_card(message: Message, state: FSMContext):
    if message.text == "❌Отменить":
        await message.bot.send_message(message.from_user.id, "🚫Действие отменено", reply_markup=await main_menu_bt())
        await state.clear()
    elif message.text:
        card = message.text
        await message.bot.send_message(message.from_user.id, "🏦Введите название банка")
        await state.set_data({"card": card})
        await state.set_state(PaymentState.get_bank)
    else:
        await message.bot.send_message(message.from_user.id, "❗️Ошибка", reply_markup=await main_menu_bt())
        await state.clear()


@client_bot_router.message(PaymentState.get_bank)
async def get_bank(message: Message, state: FSMContext, bot: Bot):
    if message.text == "❌Отменить":
        await message.answer("🚫 Действие отменено", reply_markup=await main_menu_bt())
        await state.clear()
        return

    if not message.text:
        await message.answer("️️❗ Ошибка", reply_markup=await main_menu_bt())
        await state.clear()
        return

    bank = message.text
    card_data = await state.get_data()

    user_info = await get_user_info_db(message.from_user.id)
    if not user_info:
        await message.answer("❗ Пользователь не найден.", reply_markup=await main_menu_bt())
        await state.clear()
        return

    balance = user_info[2]

    withdrawal = await reg_withdrawals(
        tg_id=message.from_user.id,
        amount=balance,
        card=card_data.get('card'),
        bank=bank
    )

    if not withdrawal:
        await message.answer("❗ Ошибка при регистрации заявки.", reply_markup=await main_menu_bt())
        await state.clear()
        return

    bot_db = await shortcuts.get_bot(bot)
    admin_id = bot_db.owner.uid if bot_db and bot_db.owner else None

    if admin_id:
        try:
            await bot.send_message(
                admin_id,
                (
                    f"<b>Заявка на выплату № {withdrawal[0]}</b>\n"
                    f"ID: <code>{withdrawal[1]}</code>\n"
                    f"Сумма выплаты: <code>{withdrawal[2]}</code>\n"
                    f"Карта: <code>{withdrawal[3]}</code>\n"
                    f"Банк: <code>{withdrawal[4]}</code>"
                ),
                parse_mode="HTML",
                reply_markup=await payments_action_in(withdrawal[0])
            )
        except TelegramBadRequest as e:
            logger.error(f"Ошибка отправки сообщения админу: {e}")
    else:
        logger.error("Admin ID не найден.")

    await message.answer("✅ Заявка на выплату принята. Ожидайте ответ.", reply_markup=await main_menu_bt())
    await state.clear()
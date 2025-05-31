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

from modul.models import User

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


async def process_referral(message: Message, referrer_id: int):
    """Process referral rewards and updates"""
    try:
        # Check if user already exists
        user = await shortcuts.get_user(message.from_user.id, message.bot)
        if user:
            return False

        print(f"Processing referral: new user {message.from_user.id} from referrer {referrer_id}")

        # Prevent self-referral
        if referrer_id == message.from_user.id:
            logger.warning(f"User {referrer_id} tried to refer themselves")
            return False

        # Get referrer
        inviter = await shortcuts.get_user(referrer_id, message.bot)
        if not inviter:
            return False

        # Update referrer's stats
        @sync_to_async
        @transaction.atomic
        def update_referral():
            try:
                user_tg = UserTG.objects.select_for_update().get(uid=referrer_id)
                admin_info = AdminInfo.objects.first()

                if not admin_info:
                    return False

                user_tg.refs += 1
                user_tg.balance += float(admin_info.price or 3.0)
                user_tg.save()
                return True
            except Exception as ex:
                logger.error(f"Error in referral update: {ex}")
                return False

        referral_success = await update_referral()

        if referral_success:
            # First save the new user
            me = await message.bot.get_me()
            new_link = f"https://t.me/{me.username}?start={message.from_user.id}"
            await save_user(
                u=message.from_user,
                inviter=inviter,
                bot=message.bot,
                link=new_link
            )

            # Then send notification
            try:
                user_link = html.escape(message.from_user.first_name)
                user_profile_link = f'tg://user?id={message.from_user.id}'
                await message.bot.send_message(
                    chat_id=referrer_id,
                    text=f"У вас новый реферал! <a href='{user_profile_link}'>{user_link}</a>",
                    parse_mode="HTML"
                )
                print('progress ')
            except TelegramForbiddenError:
                logger.error(f"Cannot send message to user {referrer_id}")

        return referral_success

    except Exception as e:
        logger.error(f"Error in process_referral: {e}")
        return False


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
        bot_user_info = await get_bot_user_info(message.from_user.id, message.bot.token)

        await message.bot.send_message(
            message.from_user.id,
            f"👥 Всего пользователей: {total_users_count}\n"
            f"👨‍👨‍👦 Друзья: {bot_user_info[1]}\n",
            reply_markup=await admin_in(admin_user)
        )

# 1. Check_chan callback'ni to'g'irlash - STATE'DAN REFERRAL OLISH QISMINI
@client_bot_router.callback_query(F.data == "check_chan")
async def check_chan_callback(query: CallbackQuery, state: FSMContext):
    try:
        bot = query.bot
        user_id = query.from_user.id
        print(f"🔍 NEW check_chan callback triggered for user {user_id}")

        # State'dan ma'lumotlarni olish
        state_data = await state.get_data()
        print(f"📊 State data for user {user_id}: {state_data}")

        # Har ikkala kalit nomini tekshirish - 'referral' yoki 'referrer_id' bo'lishi mumkin
        referrer_id = state_data.get('referrer_id') or state_data.get('referral')
        print(f"👤 Referrer_id from state for user {user_id}: {referrer_id}")

        channels = await get_channels_for_check()
        print(f"📡 Channels for user {user_id}: {channels}")

        # Obuna bo'lmagan kanallar ro'yxatini yaratish
        not_subscribed_channels = []

        if not channels:
            print(f"✅ No channels to check for user {user_id}")
            is_subscribed = True
        else:
            is_subscribed = True
            for channel_id, channel_url in channels:
                try:
                    member = await query.bot.get_chat_member(
                        chat_id=channel_id,
                        user_id=user_id
                    )
                    print(f"📢 Channel {channel_id} status for user {user_id}: {member.status}")

                    if member.status == 'left':
                        is_subscribed = False
                        print(f"❌ User {user_id} not subscribed to channel {channel_id}")

                        # Obuna bo'lmagan kanal ma'lumotlarini olish
                        try:
                            chat_info = await query.bot.get_chat(chat_id=channel_id)
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
                    print(f"⚠️ Error checking channel {channel_id}: {e}")
                    continue

        if not is_subscribed:
            print(f"🚫 User {user_id} not subscribed to all channels")

            # Foydalanuvchiga aniq ogohlantirish berish
            await query.answer("⚠️ Вы не подписались на все каналы! Пожалуйста, подпишитесь и нажмите кнопку снова.",
                               show_alert=True)

            # Obuna bo'lmagan kanallarni ko'rsatish
            channels_text = "📢 **Для использования бота необходимо подписаться на каналы:**\n\n"

            kb = InlineKeyboardBuilder()

            for index, channel in enumerate(not_subscribed_channels):
                title = channel['title']
                invite_link = channel['invite_link']

                channels_text += f"{index + 1}. {title}\n"
                kb.button(text=f"📢 {title}", url=invite_link)

            kb.button(text="✅ Проверить подписку", callback_data="check_chan")
            kb.adjust(1)  # Har bir qatorda 1 ta tugma

            # "message is not modified" xatoligini oldini olish
            try:
                # Har safar vaqt qo'shib, xabarni o'zgacha qilish
                import time
                now = int(time.time())
                await query.message.edit_text(
                    channels_text + f"\n\nПосле подписки на все каналы нажмите кнопку «Проверить подписку». (ID: {now})",
                    reply_markup=kb.as_markup(),
                    parse_mode="HTML"
                )
            except aiogram.exceptions.TelegramBadRequest as e:
                if "message is not modified" in str(e):
                    # Xabar o'zgarmagan - bu holda yangi dialog oynasi ochilgan
                    pass
                else:
                    # Boshqa xatolik bo'lsa, yangi xabar yuborish
                    try:
                        await query.message.delete()
                    except:
                        pass  # O'chirishda xatolik bo'lsa, e'tiborsiz qoldiramiz

                    await query.bot.send_message(
                        chat_id=user_id,
                        text=channels_text + "\n\nПосле подписки на все каналы нажмите кнопку «Проверить подписку».",
                        reply_markup=kb.as_markup(),
                        parse_mode="HTML"
                    )

            return

        print(f"✅ User {user_id} subscribed to all channels")

        # MUHIM: Avval foydalanuvchi bo'sh-yo'qligini tekshirish
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

            # Referral mavjud va to'g'ri bo'lsa, bonus berish
            if referrer_id:
                try:
                    ref_id = int(referrer_id)
                    print(f"🔄 Processing referral for NEW user {user_id} from {ref_id}")

                    # O'ziga-o'zi refer qilmaslikni tekshirish
                    if ref_id != user_id:
                        print(f"👥 User {user_id} referred by {ref_id}")

                        # Referrer mavjudligini tekshirish
                        @sync_to_async
                        def check_referrer_exists(ref_id, bot_token):
                            try:
                                from modul.models import Bot
                                current_bot = Bot.objects.get(token=bot_token)
                                client_bot_user = ClientBotUser.objects.filter(
                                    uid=ref_id,
                                    bot=current_bot
                                ).first()
                                return client_bot_user is not None
                            except Exception as e:
                                print(f"Error checking referrer exists: {e}")
                                return False

                        referrer_exists = await check_referrer_exists(ref_id, bot.token)

                        if referrer_exists:
                            @sync_to_async
                            @transaction.atomic
                            def update_referrer_balance(ref_id, bot_token):
                                try:
                                    from modul.models import Bot
                                    current_bot = Bot.objects.get(token=bot_token)

                                    # UserTG ni olish
                                    user_tg = UserTG.objects.select_for_update().get(uid=ref_id)

                                    # ClientBotUser ni olish
                                    client_bot_user = ClientBotUser.objects.select_for_update().get(
                                        uid=ref_id,
                                        bot=current_bot
                                    )

                                    # AdminInfo dan price olish
                                    admin_info = AdminInfo.objects.filter(bot_token=bot_token).first()
                                    price = float(admin_info.price) if admin_info and admin_info.price else 3.0

                                    # Balanslarni yangilash
                                    client_bot_user.referral_count += 1
                                    client_bot_user.referral_balance += price
                                    client_bot_user.balance += price
                                    client_bot_user.save()

                                    # UserTG balanslarini yangilash
                                    user_tg.refs += 1
                                    user_tg.balance += price
                                    user_tg.save()

                                    print(
                                        f"💰 Updated referrer {ref_id} for bot {current_bot.username}: "
                                        f"referrals={client_bot_user.referral_count}, "
                                        f"referral_balance={client_bot_user.referral_balance}, "
                                        f"total_balance={client_bot_user.balance}"
                                    )
                                    return True, price
                                except Exception as e:
                                    print(f"⚠️ Error updating referrer balance: {e}")
                                    traceback.print_exc()
                                    return False, 0

                            success, reward_amount = await update_referrer_balance(ref_id, bot.token)
                            print(f"✅ Referrer balance update success: {success}, reward: {reward_amount}")

                            if success:
                                # Referrerga xabar yuborish
                                try:
                                    user_name = html.escape(query.from_user.first_name)
                                    user_profile_link = f'tg://user?id={user_id}'

                                    await asyncio.sleep(1)  # Balans o'zgarishini kutish

                                    await query.bot.send_message(
                                        chat_id=ref_id,
                                        text=f"У вас новый реферал! <a href='{user_profile_link}'>{user_name}</a>\n"
                                             f"💰 Получено: {reward_amount} сум",
                                        parse_mode="HTML"
                                    )
                                    print(f"📨 Sent referral notification to {ref_id} about user {user_id}")
                                except Exception as e:
                                    print(f"⚠️ Error sending notification to referrer {ref_id}: {e}")
                        else:
                            print(f"❓ Referrer {ref_id} not found in database for this bot")
                    else:
                        print(f"🚫 Self-referral detected: user {user_id} trying to refer themselves")
                except ValueError:
                    print(f"❌ Invalid referrer_id: {referrer_id}")
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

@client_bot_router.callback_query(F.data.in_(["payment"]))
async def call_backs(query: CallbackQuery, state: FSMContext):
    if query.data == "payment":
        balance_q = await get_user_info_db(query.from_user.id)
        balance = balance_q[2]
        min_amount_q = await get_actual_min_amount()
        min_amount = min_amount_q if min_amount_q else 60
        check_wa = await check_for_wa(query.from_user.id)
        if balance < min_amount:
            await query.message.bot.answer_callback_query(query.id, text=f"🚫Минимальная сумма вывода: {min_amount}",
                                                          show_alert=True)
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

        # Kanallarni tekshiramiz
        checking = await check_channels(query)

        if checking:
            # Foydalanuvchi mavjudligini tekshiramiz
            is_registered = await check_user(query.from_user.id)

            # Xabarni o'chiramiz (agar mavjud bo'lsa)
            try:
                await query.bot.delete_message(chat_id=query.from_user.id, message_id=query.message.message_id)
            except Exception as e:
                logger.error(f"Error deleting message: {e}")

            # Foydalanuvchiga salomlashamiz
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
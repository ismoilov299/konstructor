import traceback

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

        # Only process referral if all channels are subscribed
        if is_subscribed and hasattr(message, 'command') and message.command.args:
            try:
                referrer_id = int(message.command.args)
                await process_referral(message, referrer_id)
            except ValueError:
                logger.error(f"Invalid referral ID: {message.command.args}")

        return True

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
                user_tg.balance += float(admin_info.price or 10.0)
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
                user_link = html.link('реферал', f'tg://user?id={message.from_user.id}')
                await message.bot.send_message(
                    chat_id=referrer_id,
                    text=f"У вас новый {user_link}!"
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


async def start_ref(message: Message, bot: Bot, referral: str = None):
    try:
        print('ishladi')
        logger.info(f"Checking channels for user {message.from_user.id}")
        channels_checker = await check_channels(message)
        # print(f"Found channels in DB: {await get_channels_from_db()}")
        # print(f"Checking channels: {await get_channels_from_db()}")
        print(channels_checker)
        logger.info(f"Channels check result: {channels_checker}")

        if not channels_checker:
            logger.info("Channels check failed, exiting")
            return

        is_registered = await check_user(message.from_user.id)
        is_banned = await check_ban(message.from_user.id)

        if is_banned:
            logger.info(f"User {message.from_user.id} is banned, exiting")
            return

        # Referral jarayoni
        if referral and not is_registered and channels_checker:
            try:
                referrer_id = int(referral)
                logger.info(f"Processing referral ID: {referrer_id} for user {message.from_user.id}")

                # O'zini o'zi refer qilishni tekshirish - qattiq tekshirish
                if str(referrer_id) == str(message.from_user.id):
                    logger.warning(f"SELF-REFERRAL DETECTED: User {message.from_user.id} tried to refer themselves!")
                    await add_user(
                        tg_id=message.from_user.id,
                        user_name=message.from_user.first_name
                    )
                    await message.answer(
                        "❌ Siz o'zingizni taklif qila olmaysiz!",
                        reply_markup=await main_menu_bt()
                    )
                    logger.info(f"Self-referral blocked for user {message.from_user.id}")
                    return  # Referral jarayoni to'xtatiladi
                else:
                    # Referrerni tekshirish
                    referrer_name = await get_user_name(referrer_id)
                    if referrer_name:
                        logger.info(f"Referrer found: {referrer_name} (ID: {referrer_id})")
                        # Yangi foydalanuvchini qo'shamiz
                        await add_user(
                            tg_id=message.from_user.id,
                            user_name=message.from_user.first_name,
                            invited=referrer_name,
                            invited_id=referrer_id
                        )

                        # Referral statistikasini yangilash
                        @sync_to_async
                        @transaction.atomic
                        def update_referral():
                            try:
                                # Qo'shimcha himoya - o'zini o'zi referral qilishni oldini olish
                                if str(referrer_id) == str(message.from_user.id):
                                    logger.error(f"Prevented self-referral in update_referral for user {referrer_id}")
                                    return False

                                user_tg = UserTG.objects.select_for_update().get(uid=referrer_id)
                                admin_info = AdminInfo.objects.first()

                                if not admin_info:
                                    logger.error("Admin info not found")
                                    return False

                                user_tg.refs += 1
                                user_tg.balance += float(admin_info.price or 10.0)
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
                                user_link = html.link('реферал', f'tg://user?id={message.from_user.id}')
                                await message.bot.send_message(
                                    chat_id=referrer_id,
                                    text=f"У вас новый {user_link}!"
                                )
                                logger.info(f"Referral notification sent to {referrer_id}")
                            except TelegramForbiddenError:
                                logger.error(f"Cannot send message to user {referrer_id}")
                            except Exception as e:
                                logger.error(f"Error sending notification to referrer: {e}")

                        logger.info(f"Successfully processed referral for {referrer_id}")
                    else:
                        logger.error(f"Referrer {referrer_id} not found")
                        await add_user(
                            tg_id=message.from_user.id,
                            user_name=message.from_user.first_name
                        )

            except ValueError:
                logger.error(f"Invalid referral ID: {referral}")
                await add_user(
                    tg_id=message.from_user.id,
                    user_name=message.from_user.first_name
                )
        elif not is_registered:
            logger.info(f"Adding new user {message.from_user.id} without referral")
            await add_user(
                tg_id=message.from_user.id,
                user_name=message.from_user.first_name
            )

        logger.info(f"Sending welcome message to {message.from_user.id}")
        await message.answer(
            f"🎉 Привет, {message.from_user.first_name}",
            reply_markup=await main_menu_bt()
        )
        logger.info(f"Welcome message sent to {message.from_user.id}")

    except Exception as e:
        logger.error(f"Error in start_ref: {e}")
        traceback.print_exc()  # Xato stack trace'ni ham chiqarish
        await message.answer(
            "Произошла ошибка. Попробуйте позже.",
            reply_markup=await main_menu_bt()
        )

class RefsBotFilter(BaseFilter):
    async def __call__(self, message: Message, bot: Bot) -> bool:
        bot_db = await shortcuts.get_bot(bot)
        return shortcuts.have_one_module(bot_db, "refs")


@client_bot_router.message(F.text == "💸Заработать",RefsBotFilter())
async def gain(message: Message, bot: Bot, state: FSMContext):
    bot_db = await shortcuts.get_bot(bot)
    await state.clear()
    if shortcuts.have_one_module(bot_db, 'refs'):
        channels_checker = await check_channels(message)
        checker_banned = await banned(message)
        if channels_checker and checker_banned:
            me = await bot.get_me()
            link = f"https://t.me/{me.username}?start={message.from_user.id}"
            price = await get_actual_price()
            await message.bot.send_message(message.from_user.id,
                                        f"👥 Приглашай друзей и зарабатывай, за \nкаждого друга ты получишь {price}₽\n\n"
                                        f"🔗 Ваша ссылка для приглашений:\n {link}")
    else:
        channels_checker = await check_channels(message)
        checker_banned = await banned(message)
        if channels_checker and checker_banned:
            me = await bot.get_me()
            link = f"https://t.me/{me.username}?start={message.from_user.id}"
            price = await get_actual_price()
            await message.bot.send_message(message.from_user.id,
                                        f"👥 Приглашай друзей и зарабатывай, за \nкаждого друга ты получишь {price}₽\n\n"
                                        f"🔗 Ваша ссылка для приглашений:\n {link}"
                                        "\n Что бы вернуть функционал основного бота напишите /start",
                                        reply_markup=await main_menu_bt())


@client_bot_router.message(F.text == "📱Профиль")
async def profile(message: Message):
    """Show user profile with referral information"""
    try:
        channels_checker = await check_channels(message)
        is_banned = await check_ban(message.from_user.id)

        if not channels_checker or is_banned:
            return

        user_info = await get_user_info_db(message.from_user.id)
        print(user_info)
        if not user_info:
            await message.answer(
                "Ошибка получения данных профиля",
                reply_markup=await main_menu_bt()
            )
            return

        profile_text = (
            f"📱Профиль\n\n"
            f"📝 Ваше имя: {message.from_user.full_name}\n"
            f"🆔 Ваш ID: <code>{user_info[1]}</code>\n"
            f"==========================\n"
            f"💳 Баланс: {user_info[2]}₽\n"
            f"👥 Всего друзей: {user_info[3]}\n"

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
    if not user_info:
        await message.answer(
            "Ошибка получения данных профиля",
            reply_markup=await main_menu_bt()
        )
        return
    if channels_checker and checker_banned:
        all_info = await count_info()

        bot_token = message.bot.token
        admin_user = await get_admin_user(bot_token)

        await message.bot.send_message(
            message.from_user.id,
            f"👥 Всего пользователей: {user_info[3]}\n",
            # f"📤 Выплачено всего: {all_info[1]}",
            reply_markup=await admin_in(admin_user)
        )




@client_bot_router.callback_query(F.data.in_(["payment",]))
async def call_backs(query: CallbackQuery, state: FSMContext):
    await state.clear()
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
        checking = await check_channels(query)
        await query.bot.delete_message(chat_id=query.from_user.id, message_id=query.message.message_id)
        if checking:
            await query.bot.send_message(query.from_user.id, f"🎉Привет, {query.from_user.first_name}",
                                         reply_markup=await main_menu_bt())


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




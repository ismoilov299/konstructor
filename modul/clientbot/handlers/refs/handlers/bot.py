import logging

import aiogram
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import BaseFilter

from modul.clientbot import shortcuts
from modul.loader import client_bot_router
from aiogram.utils.deep_linking import create_start_link, decode_payload
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, BotCommand, CallbackQuery
from modul.clientbot.handlers.refs.keyboards.buttons import *
from modul.clientbot.handlers.refs.shortcuts import *
from aiogram import F, Bot
from modul.clientbot.handlers.refs.data.states import PaymentState
logger = logging.getLogger(__name__)

# TODO изменить метод получения айди админа
async def admin_id_func(user_id, bot):
    bot_db = await shortcuts.get_bot(bot)
    if user_id == bot_db.owner.uid:
        return True
    return False


async def check_channels(message):
    all_channels = await get_channels_for_check()
    print(all_channels)
    if all_channels != []:
        for i in all_channels:
            try:
                check = await message.bot.get_chat_member(i[0], user_id=message.from_user.id)
                if check.status in ["left"]:
                    await message.bot.send_message(chat_id=message.from_user.id,
                                                   text="Для использования бота подпишитесь на наших спонсоров",
                                                   reply_markup=await channels_in(all_channels))
                    return False

            except:
                pass
    await check_and_add(tg_id=message.from_user.id)
    return True


async def banned(message):
    check = await check_ban(message.from_user.id)
    if check:
        await message.bot.send_message(chat_id=message.from_user.id,
                                       text="Вы были заблокированы")
        return False
    return True


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

#/ var / www / Konstructor / modul / clientbot / handlers / refs / handlers / bot.py

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


async def process_referral(message: Message, referrer_id: int):
    """Process referral rewards and updates"""
    try:
        print(f"Processing referral: new user {message.from_user.id} from referrer {referrer_id}")

        # Get referrer's name
        referrer_name = await get_user_name(referrer_id)
        if not referrer_name:
            print(f"Referrer {referrer_id} not found")
            return False

        # Add referral record
        await add_ref(message.from_user.id, referrer_id)
        print(f"Added ref record: {message.from_user.id} -> {referrer_id}")

        # Add user with referral info
        await add_user(
            tg_id=message.from_user.id,
            user_name=message.from_user.first_name,
            invited=referrer_name,
            invited_id=referrer_id
        )
        print(f"Added new user with referral info")

        # Update referrer's stats and add money
        success_ref = await plus_ref(referrer_id)
        print(f"Updated ref count: {success_ref}")

        success_money = await plus_money(referrer_id)
        print(f"Added money: {success_money}")

        print(f"Successfully processed referral")
        return True

    except Exception as e:
        print(f"Error in process_referral: {e}")
        return False


async def start_ref(message: Message, bot: Bot, referral: str = None):
    """Handle /start command with referral"""
    try:
        # Check requirements
        channels_checker = await check_channels(message)
        is_registered = await check_user(message.from_user.id)
        is_banned = await check_ban(message.from_user.id)

        if not channels_checker or is_banned:
            return

        if referral and not is_registered:
            try:
                referrer_id = int(referral)

                # Log referral process
                logger.info(f"Processing referral: {message.from_user.id} invited by {referrer_id}")

                # Prevent self-referral
                if referrer_id == message.from_user.id:
                    logger.warning(f"User {referrer_id} tried to refer themselves")
                    await add_user(
                        tg_id=message.from_user.id,
                        user_name=message.from_user.first_name
                    )
                else:
                    # Get referrer's name
                    referrer_name = await get_user_name(referrer_id)
                    if referrer_name:
                        # Add new user with referral info
                        await add_user(
                            tg_id=message.from_user.id,
                            user_name=message.from_user.first_name,
                            invited=referrer_name,
                            invited_id=referrer_id
                        )

                        # Add referral record
                        await add_ref(message.from_user.id, referrer_id)

                        # Update referrer stats and add bonus
                        await plus_ref(referrer_id)
                        await plus_money(referrer_id)

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
            # Add new user without referral
            await add_user(
                tg_id=message.from_user.id,
                user_name=message.from_user.first_name
            )

        await message.answer(
            f"🎉 Привет, {message.from_user.first_name}",
            reply_markup=await main_menu_bt()
        )

    except Exception as e:
        logger.error(f"Error in start_ref: {e}")
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
        if not user_info:
            await message.answer(
                "Ошибка получения данных профиля",
                reply_markup=await main_menu_bt()
            )
            return

        profile_text = (
            f"📱Профиль\n\n"
            f"📝 Ваше имя: {user_info[0]}\n"
            f"🆔 Ваш ID: <code>{user_info[1]}</code>\n"
            f"==========================\n"
            f"💳 Баланс: {user_info[2]}\n"
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
    if channels_checker and checker_banned:
        all_info = await count_info()

        bot_token = message.bot.token
        admin_user = await get_admin_user(bot_token)

        await message.bot.send_message(
            message.from_user.id,
            f"👥 Всего пользователей: {all_info[0]}\n"
            f"📤 Выплачено всего: {all_info[1]}",
            reply_markup=await admin_in(admin_user)
        )




@client_bot_router.callback_query(F.data.in_(["payment", "check_chan"]))
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
        await message.bot.send_message(message.from_user.id, "🚫Действие отменено", reply_markup=await main_menu_bt())
        await state.clear()
        return

    elif message.text:
        bank = message.text
        card = await state.get_data()

        # Foydalanuvchi ma'lumotlarini olish
        user_info = await get_user_info_db(message.from_user.id)
        if not user_info:
            await message.bot.send_message(message.from_user.id, "❗ Пользователь не найден.", reply_markup=await main_menu_bt())
            await state.clear()
            return

        balance = user_info[2]

        # Zayavkani ro‘yxatdan o‘tkazish
        withdrawal = await reg_withdrawals(
            tg_id=message.from_user.id,
            amount=balance,
            card=card.get('card'),
            bank=bank
        )

        # Admin ID ni tekshirish va xabar yuborish
        admin_id = await admin_id_func(message.from_user.id, bot)
        if admin_id:
            try:
                await message.bot.send_message(
                    admin_id,
                    f"<b>Заявка на выплату № {withdrawal[0]}</b>\n"
                    f"ID: <code>{withdrawal[1]}</code>\n"
                    f"Сумма выплаты: {withdrawal[2]}\n"
                    f"Карта: <code>{withdrawal[3]}</code>\n"
                    f"Банк: {withdrawal[4]}",
                    parse_mode="html",
                    reply_markup=await payments_action_in(withdrawal[0])
                )
            except TelegramBadRequest as e:
                logger.error(f"Ошибка отправки сообщения админу: {e}")
        else:
            logger.error("Admin ID не найден.")

        await message.bot.send_message(message.from_user.id, "✅ Заявка на выплату принята. Ожидайте ответ.", reply_markup=await main_menu_bt())
        await state.clear()
    else:
        await message.bot.send_message(message.from_user.id, "️️❗ Ошибка", reply_markup=await main_menu_bt())
        await state.clear()



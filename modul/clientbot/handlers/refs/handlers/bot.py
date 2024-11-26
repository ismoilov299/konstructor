import logging

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
    try:
        logger.info(f"Checking channels for user {message.from_user.id}")
        all_channels = await get_channels_for_check()

        if all_channels:
            logger.debug(f"Found channels to check: {len(all_channels)}")
            for channel in all_channels:
                try:
                    check = await message.bot.get_chat_member(channel[0], user_id=message.from_user.id)
                    logger.debug(f"Channel {channel[0]} check result: {check.status}")

                    if check.status in ["left"]:
                        await message.bot.send_message(
                            chat_id=message.from_user.id,
                            text="Для использования бота подпишитесь на наших спонсоров",
                            reply_markup=await channels_in(all_channels)
                        )
                        logger.info(f"User {message.from_user.id} needs to subscribe to channels")
                        return False
                except Exception as e:
                    logger.error(f"Error checking channel {channel[0]}: {str(e)}")
                    pass

        await check_and_add(tg_id=message.from_user.id)
        logger.info(f"Channel check passed for user {message.from_user.id}")
        return True

    except Exception as e:
        logger.error(f"Error in check_channels for user {message.from_user.id}: {str(e)}", exc_info=True)
        return False


async def banned(message):
    try:
        logger.debug(f"Checking ban status for user {message.from_user.id}")
        check = await check_ban(message.from_user.id)

        if check:
            logger.info(f"User {message.from_user.id} is banned")
            await message.bot.send_message(
                chat_id=message.from_user.id,
                text="Вы были заблокированы"
            )
            return False

        logger.debug(f"User {message.from_user.id} is not banned")
        return True

    except Exception as e:
        logger.error(f"Error checking ban status for user {message.from_user.id}: {str(e)}", exc_info=True)
        return False




async def start_ref(message: Message, command: BotCommand = None):
    try:
        logger.info(f"Starting referral process for user {message.from_user.id}")
        channels_checker = await check_channels(message)
        checker = await check_user(message.from_user.id)
        checker_banned = await banned(message)

        logger.debug(
            f"Checks results for user {message.from_user.id}: channels={channels_checker}, user_exists={checker}, banned={checker_banned}")

        if command and not checker and checker_banned:
            inv_id = int(command.args) if command.args else None
            logger.info(f"Processing referral invite. Inviter ID: {inv_id}, New user ID: {message.from_user.id}")

            if inv_id:
                inv_name = await get_user_name(inv_id)
                logger.debug(f"Found inviter name: {inv_name} for ID: {inv_id}")

                if inv_name:
                    await add_user(user_name=message.from_user.first_name, tg_id=message.from_user.id,
                                   invited=inv_name, invited_id=inv_id)
                    await add_ref(tg_id=message.from_user.id, inv_id=inv_id)
                    logger.info(f"Successfully added new user {message.from_user.id} with inviter {inv_id}")
                else:
                    await add_user(user_name=message.from_user.first_name, tg_id=message.from_user.id)
                    logger.info(f"Added user {message.from_user.id} without inviter (inviter not found)")
            else:
                await add_user(user_name=message.from_user.first_name, tg_id=message.from_user.id)
                logger.info(f"Added user {message.from_user.id} without referral")

            await message.bot.send_message(message.from_user.id, f"🎉Привет, {message.from_user.first_name}",
                                           reply_markup=await main_menu_bt())

    except Exception as e:
        logger.error(f"Error in start_ref for user {message.from_user.id}: {str(e)}", exc_info=True)
        await message.bot.send_message(message.from_user.id, "Произошла ошибка. Попробуйте позже.")


@client_bot_router.message(F.text == "💸Заработать")
async def gain(message: Message, bot: Bot, state: FSMContext):
    try:
        logger.info(f"Processing gain request for user {message.from_user.id}")
        bot_db = await shortcuts.get_bot(bot)
        await state.clear()

        if shortcuts.have_one_module(bot_db, 'refs'):
            channels_checker = await check_channels(message)
            checker_banned = await banned(message)

            logger.debug(
                f"Checks for user {message.from_user.id}: channels={channels_checker}, banned={checker_banned}")

            if channels_checker and checker_banned:
                try:
                    link = await create_start_link(message.bot, str(message.from_user.id), encode=False)
                    price = await get_actual_price()
                    logger.info(f"Generated referral link for user {message.from_user.id}: {link}")

                    await message.bot.send_message(message.from_user.id,
                                                   f"👥 Приглашай друзей и зарабатывай, за \nкаждого друга ты получишь {price}₽\n\n"
                                                   f"🔗 Ваша ссылка для приглашений:\n {link}")
                except Exception as e:
                    logger.error(f"Error generating referral link: {str(e)}", exc_info=True)
                    raise
        else:
            logger.debug(f"Processing non-refs module gain for user {message.from_user.id}")
            channels_checker = await check_channels(message)
            checker_banned = await banned(message)

            if channels_checker and checker_banned:
                try:
                    link = await create_start_link(message.bot, str(message.from_user.id), encode=False)
                    price = await get_actual_price()
                    logger.info(f"Generated link for non-refs user {message.from_user.id}: {link}")

                    await message.bot.send_message(message.from_user.id,
                                                   f"👥 Приглашай друзей и зарабатывай, за \nкаждого друга ты получишь {price}₽\n\n"
                                                   f"🔗 Ваша ссылка для приглашений:\n {link}"
                                                   "\n Что бы вернуть функционал основного бота напишите /start",
                                                   reply_markup=await main_menu_bt())
                except Exception as e:
                    logger.error(f"Error in non-refs link generation: {str(e)}", exc_info=True)
                    raise

    except Exception as e:
        logger.error(f"Error in gain handler for user {message.from_user.id}: {str(e)}", exc_info=True)
        await message.bot.send_message(message.from_user.id, "Произошла ошибка. Попробуйте позже.")



@client_bot_router.message(F.text == "📱Профиль")
async def profile(message: Message, bot: Bot):  # bot parametrini qo'shamiz
    try:
        channels_checker = await check_channels(message)
        checker_banned = await banned(message)
        if channels_checker and checker_banned:
            info = await get_user_info_db(message.from_user.id, bot)  # bot ni uzatamiz
            if info:
                await message.bot.send_message(
                    message.from_user.id,
                    f"📝 Ваше имя: {info[0]}\n"
                    f"🆔 Ваш ID: <code>{info[1]}</code>\n"
                    f"==========================\n"
                    f"💳 Баланс: {info[2]}\n"
                    f"👥 Всего друзей: {info[3]}\n"
                    f"👤 Вас привел {info[4]}\n"
                    f"==========================\n",
                    parse_mode="html",
                    reply_markup=await payment_in()
                )
            else:
                logger.error(f"Could not get user info for {message.from_user.id}")
                await message.answer("Произошла ошибка при получении данных профиля")
    except Exception as e:
        logger.error(f"Error in profile handler: {e}", exc_info=True)
        await message.answer("Произошла ошибка")


@client_bot_router.message(F.text == "ℹ️Инфо")
async def info(message: Message):
    channels_checker = await check_channels(message)
    checker_banned = await banned(message)
    if channels_checker and checker_banned:
        all_info = await count_info()
        # TODO изменить на юзернейм админа
        admin_user = await get_admin_user()
        print(admin_user)
        await message.bot.send_message(message.from_user.id,
                                       f"👥 Всего пользователей: {all_info[0]}\n"
                                       f"📤 Выплачено всего: {all_info[1]}",
                                       reply_markup=await admin_in(admin_user))


@client_bot_router.callback_query(F.data.in_(["payment", "check_chan"]))
async def call_backs(query: CallbackQuery, state: FSMContext, bot: Bot):  # bot parametri qo'shildi
    await state.clear()
    if query.data == "payment":
        # bot parametrini qo'shamiz
        balance_q = await get_user_info_db(query.from_user.id, bot)
        if balance_q:
            balance = balance_q[2]  # balance_q[2] balansni bildiradi
            min_amount_q = await get_actual_min_amount()
            min_amount = min_amount_q if min_amount_q else 60
            check_wa = await check_for_wa(query.from_user.id)

            if balance < min_amount:
                await query.bot.answer_callback_query(
                    query.id,
                    text=f"🚫Минимальная сумма вывода: {min_amount}",
                    show_alert=True
                )
            elif check_wa:
                await query.bot.answer_callback_query(
                    query.id,
                    text="⏳Вы уже оставили заявку. Ожидайте",
                    show_alert=True
                )
            elif balance >= min_amount:
                await query.bot.send_message(
                    query.from_user.id,
                    "💳Введите номер вашей карты",
                    reply_markup=await cancel_bt()
                )
                await state.set_state(PaymentState.get_card)
        else:
            await query.bot.answer_callback_query(
                query.id,
                text="Произошла ошибка при получении баланса",
                show_alert=True
            )

    elif query.data == "check_chan":
        checking = await check_channels(query)
        await query.bot.delete_message(
            chat_id=query.from_user.id,
            message_id=query.message.message_id
        )
        if checking:
            await query.bot.send_message(
                query.from_user.id,
                f"🎉Привет, {query.from_user.first_name}",
                reply_markup=await main_menu_bt()
            )


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
        await message.bot.send_message(
            message.from_user.id,
            "🚫Действие отменено",
            reply_markup=await main_menu_bt()
        )
        await state.clear()
    elif message.text:
        bank = message.text
        card = await state.get_data()
        # bot parametrini qo'shamiz
        user_info = await get_user_info_db(message.from_user.id, bot)
        if user_info:
            balance = user_info[2]  # Balansni olamiz
            await message.bot.send_message(
                message.from_user.id,
                "✅Заявка на выплату принята. Ожидайте ответ",
                reply_markup=await main_menu_bt()
            )
            i = reg_withdrawals(
                tg_id=message.from_user.id,
                amount=balance,
                card=card.get('card'),
                bank=bank
            )
            admin_id = await admin_id_func(message.from_user.id, bot)
            await message.bot.send_message(
                admin_id,
                f"<b>Заявка на выплату № {i[0]}</b>\n"
                f"ID: <code>{i[1]}</code>\n"
                f"Сумма выплаты: {i[2]}\n"
                f"Карта: <code>{i[3]}</code>\n"
                f"Банк: {i[4]}",
                parse_mode="html",
                reply_markup=await payments_action_in(i[0])
            )
            await state.clear()
        else:
            await message.answer("Произошла ошибка при получении баланса")
            await state.clear()
    else:
        await message.bot.send_message(
            message.from_user.id,
            "️️❗Ошибка",
            reply_markup=await main_menu_bt()
        )
        await state.clear()

import logging
import re
import traceback
from contextlib import suppress

from aiogram import F, Bot, types,html
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest
from aiogram.filters import CommandStart, Filter, CommandObject
from aiogram.utils.deep_linking import create_start_link
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, BotCommand, CallbackQuery, LabeledPrice
from aiogram.utils.keyboard import InlineKeyboardBuilder
from asgiref.sync import sync_to_async
from django.db import transaction
from openpyxl.styles.builtins import percent

from modul import models
from modul.clientbot import shortcuts
from modul.clientbot.handlers.annon_bot.keyboards.buttons import channels_in, payment_keyboard, main_menu_bt, cancel_in, \
    again_in, payment_amount_keyboard, greeting_in, link_in
from modul.clientbot.handlers.annon_bot.states import Links, AnonBotFilter
from modul.clientbot.handlers.annon_bot.userservice import get_greeting, get_user_link, get_user_by_link, \
    get_all_statistic, get_channels_for_check, change_greeting_user, change_link_db, add_user, add_link_statistic, \
    add_answer_statistic, add_messages_info, check_user, check_link, check_reply, update_user_link, get_user_by_id
from modul.clientbot.handlers.kino_bot.shortcuts import get_all_channels_sponsors
from modul.clientbot.handlers.refs.keyboards.buttons import main_menu_bt2
from modul.clientbot.handlers.refs.shortcuts import get_actual_price, get_actual_min_amount
from modul.loader import client_bot_router
from modul.clientbot.shortcuts import get_bot_by_token, get_bot
from modul.models import UserTG, AdminInfo, ClientBotUser

logger = logging.getLogger(__name__)


async def check_channels(user_id: int, bot: Bot) -> bool:
    try:
        channels = await get_channels_for_check()
        if not channels:
            return True

        for channel_id, _ in channels:
            try:
                member = await bot.get_chat_member(chat_id=channel_id, user_id=user_id)
                if member.status not in ['member', 'creator', 'administrator']:
                    return False
            except Exception as e:
                return False
        return True
    except Exception as e:
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
def check_if_already_referred(uid, ref_id, bot_token):
    try:
        # Получаем бота по токену
        bot = Bot.objects.get(token=bot_token)

        # Проверяем, есть ли пользователь с этим ботом в ClientBotUser
        client_bot_user = ClientBotUser.objects.filter(
            uid=uid,
            bot=bot
        ).first()

        if client_bot_user:
            # Проверяем, указан ли реферал
            if client_bot_user.inviter and client_bot_user.inviter.uid == ref_id:
                print(f"User {uid} is already referred by {ref_id} in bot {bot.username}")
                return True

        return False
    except Exception as e:
        print(f"Error checking referral status: {e}")
        return False


# async def process_referral(message: Message, referral_id: int):
#     try:
#         logger.info(f"Processing referral: user {message.from_user.id}, referrer {referral_id}")
#
#         # O'zini o'zi referral qilishni tekshirish
#         if str(referral_id) == str(message.from_user.id):
#             logger.warning(f"SELF-REFERRAL BLOCKED in process_referral: User {message.from_user.id}")
#             return False
#
#         # Referral beruvchini tekshirish
#         inviter = await get_user_by_id(referral_id)
#         if not inviter:
#             logger.warning(f"Inviter {referral_id} not found")
#             return False
#
#         try:
#             # Referral statistikasini yangilash
#             stats_updated = await update_referral_stats(referral_id)
#
#             if stats_updated:
#                 # Referral beruvchiga xabar yuborish
#                 user_link = html.link('реферал', f'tg://user?id={message.from_user.id}')
#                 await message.bot.send_message(
#                     chat_id=referral_id,
#                     text=f"У вас новый {user_link}!"
#                 )
#                 print("115 annon")
#                 logger.info(f"Referral notification sent to user {referral_id}")
#                 logger.info(f"Referral processed for user {referral_id}")
#                 return True
#             else:
#                 logger.warning(f"Failed to update referral stats for {referral_id}")
#                 return False
#         except Exception as e:
#             logger.error(f"Error in referral process: {e}")
#             return False
#
#     except Exception as e:
#         logger.error(f"Error processing referral: {e}")
#         return False


@sync_to_async
def update_referral_stats(referral_id: int):
    try:
        with transaction.atomic():
            user_tg = UserTG.objects.select_for_update().get(uid=referral_id)

            # AdminInfo jadvalidan mukofat miqdorini olish
            admin_info = AdminInfo.objects.first()
            if admin_info and admin_info.price is not None:
                reward = float(admin_info.price)
            else:
                reward = 10.0  # Default qiymat

            user_tg.refs += 1
            user_tg.balance += reward
            user_tg.save()

            logger.info(f"Referral stats updated for user {referral_id}, reward amount: {reward}")
            return True
    except UserTG.DoesNotExist:
        logger.error(f"UserTG with uid {referral_id} does not exist")
        return False
    except Exception as e:
        logger.error(f"Error updating referral stats: {e}")
        return False


async def check_subs(user_id: int, bot: Bot) -> bool:
    bot_db = await shortcuts.get_bot(bot)
    admin_id = bot_db.owner.uid

    if user_id == admin_id:
        return True

    channels = await get_all_channels_sponsors()
    print(channels, " ch")

    if not channels:
        return True

    check_results = []
    for channel in channels:
        try:
            # Agar channel tuple bo'lsa, faqat birinchi elementi (ID) ni olish
            chat_id = channel[0] if isinstance(channel, tuple) else channel

            # Agar chat_id string bo'lsa va raqam bilan boshlansa, integer ga aylantirish mumkin
            if isinstance(chat_id, str) and chat_id.strip('-').isdigit():
                chat_id = int(chat_id)

            member = await bot.get_chat_member(chat_id=chat_id, user_id=user_id)
            if member.status != 'left':
                check_results.append(True)
            else:
                check_results.append(False)
        except Exception as e:
            print(f"Error checking subscription for channel {channel}: {e}")
            check_results.append(False)

    print(check_results)
    return all(check_results)



async def get_subs_kb(bot: Bot) -> types.InlineKeyboardMarkup:
    channels = await get_all_channels_sponsors()
    kb = InlineKeyboardBuilder()

    for channel_id in channels:
        try:
            chat_info = await bot.get_chat(channel_id)
            invite_link = chat_info.invite_link
            if not invite_link:
                invite_link = (await bot.create_chat_invite_link(channel_id)).invite_link

            kb.button(text=f'{chat_info.title}', url=invite_link)
        except Exception as e:
            print(f"Error with channel {channel_id}: {e}")
            continue

    kb.button(
        text='✅ Проверить подписку',
        callback_data='check_subs'
    )

    kb.adjust(1)
    return kb.as_markup()

async def check_user_subscriptions(bot: Bot, user_id: int) -> bool:
    channels = await get_all_channels_sponsors()
    for channel in channels:
        try:
            member = await bot.get_chat_member(channel.chanel_id, user_id)
            if member.status in ['left', 'kicked', 'banned']:
                return False
        except Exception as e:
            print(f"Error checking subscription for channel {channel.chanel_id}: {e}")
            return False

    return True


@client_bot_router.message(F.text == "💸Заработать", AnonBotFilter())
async def anon(message: Message, bot: Bot, state: FSMContext):
    bot_db = await shortcuts.get_bot(bot)

    sub_status = await check_subs(message.from_user.id, bot)
    if not sub_status:
        kb = await get_subs_kb(bot)
        await message.answer(
            '**Чтобы воспользоваться ботом, необходимо подписаться на каналы**',
            reply_markup=kb,
            parse_mode="HTML"
        )
        return

    me = await bot.get_me()
    ref_link = f"https://t.me/{me.username}?start={message.from_user.id}"

    price = await get_actual_price(bot.token)
    print(price)
    await message.bot.send_message(
        message.from_user.id,
        f"👥 Приглашай друзей и зарабатывай! За \nкаждого друга ты получишь {price:.2f}₽.\n\n"
        f"🔗 Ваша ссылка для приглашений:\n{ref_link}\n\n",
        # f"💰 Минимальная сумма для вывода: {min_withdraw}₽",
        reply_markup=await main_menu_bt2()

    )

async def process_new_user(message: types.Message, state: FSMContext, bot: Bot):
    logger.info(f"Processing new user {message.from_user.id}")
    data = await state.get_data()
    referral = data.get('referral')

    new_link = await create_start_link(bot, str(message.from_user.id), encode=True)
    link_for_db = new_link[new_link.index("=") + 1:]

    user_exists = await check_user(message.from_user.id)
    if not user_exists:
        await add_user(
            tg_id=message.from_user.id,
            user_name=message.from_user.first_name,
            invited="Referral" if referral else "Никто",
            invited_id=int(referral) if referral else None,
            bot_token=bot.token,
            user_link=link_for_db  # user_link qo'shildi
        )

    if referral:
        await process_referral(message, int(referral))

    await show_main_menu(message, bot)
async def process_existing_user(message: types.Message, bot: Bot):
    logger.info(f"Processing existing user {message.from_user.id}")
    await show_main_menu(message, bot)


async def show_main_menu(message: types.Message, bot: Bot):
    me = await bot.get_me()
    print(271)
    link = f"https://t.me/{me.username}?start={message.from_user.id}"
    await message.answer(
        f"🚀 <b>Начни получать анонимные сообщения прямо сейчас!</b>\n\n"
        f"Твоя личная ссылка:\n👉{link}\n\n"
        f"Размести эту ссылку ☝️ в своём профиле Telegram/Instagram/TikTok или "
        f"других соц сетях, чтобы начать получать сообщения 💬",
        parse_mode="html",
        reply_markup=await main_menu_bt()
    )
    logger.info(f"Main menu sent to user {message.from_user.id}")


@client_bot_router.message(CommandStart(), AnonBotFilter())
async def start_command(message: Message, state: FSMContext, bot: Bot, command: CommandObject):
    await state.clear()
    logger.info(f"Start command received from user {message.from_user.id} anon bot")
    args = command.args

    # Debug log
    print(f"Annon bot start command arguments: {args}")

    channels = await get_channels_for_check()
    valid_channels = []

    for channel in channels:
        try:
            chat = await bot.get_chat(channel)
            valid_channels.append(channel)
        except Exception as e:
            logger.error(f"Channel {channel} not accessible: {e}")

    subscribed = True
    if valid_channels:
        subscribed = await check_channels(message.from_user.id, bot, valid_channels)

        if not subscribed:
            markup = await channels_in(valid_channels, bot)
            await message.answer(
                "Для использования бота подпишитесь на наших спонсоров",
                reply_markup=markup
            )
            return

    print(f"Annon bot: user {message.from_user.id} passed channel check")
    user_exists = await check_user(message.from_user.id)
    print(f"Annon bot: user {message.from_user.id} exists: {user_exists}")

    # Yangi foydalanuvchi bo'lsa, bazaga qo'shamiz
    if not user_exists:
        print(f"Annon bot: creating new user {message.from_user.id}")
        new_link = await create_start_link(bot, str(message.from_user.id))
        link_for_db = new_link[new_link.index("=") + 1:]

        # Referral bilan yangi foydalanuvchi
        if args:
            try:
                referral_id = int(args)
                print(f"Annon bot: processing referral from {referral_id} to {message.from_user.id}")

                # O'zini o'zi referral qilishni tekshirish
                if referral_id != message.from_user.id:
                    print(referral_id)
                    print(f"Annon bot: Adding user {message.from_user.id} with referrer {referral_id}")
                    await add_user(
                        tg_id=message.from_user.id,
                        user_name=message.from_user.first_name,
                        invited_id=str(referral_id),
                        bot_token=message.bot.token  # Bot tokenini qo'shdik
                    )
                    # So'ng referral jarayonini ishga tushirish
                    success = await process_referral(referral_id, message.from_user.id)
                    print(f"Annon bot: Referral process result: {success}")
                else:
                    # O'zini o'zi referral qilolmaydi
                    print(f"Annon bot: Self-referral blocked for user {message.from_user.id}")
                    await add_user(
                        tg_id=message.from_user.id,
                        user_name=message.from_user.first_name,
                        user_link=link_for_db,
                        bot_token=message.bot.token  # Bot tokenini qo'shdik
                    )
            except ValueError:
                # Agar args son bo'lmasa
                print(f"Annon bot: Invalid referral ID: {args}")
                await add_user(
                    tg_id=message.from_user.id,
                    user_name=message.from_user.first_name,
                    user_link=link_for_db,
                    bot_token=message.bot.token
                )
        else:
            # Agar args yo'q bo'lsa
            print(f"Annon bot: No referral, adding new user {message.from_user.id}")
            await add_user(
                tg_id=message.from_user.id,
                user_name=message.from_user.first_name,
                user_link=link_for_db,
                bot_token=message.bot.token  # Bot tokenini qo'shdik
            )

    # Anonim xabar yuborish qismi
    if args:
        try:
            target_id = int(args)
            print(f"Annon bot: Setting up anonymous message to user {target_id}")
            await state.set_state(Links.send_st)
            await state.update_data({"link_user": target_id})
            await message.answer(
                "🚀 Здесь можно отправить анонимное сообщение человеку, который опубликовал эту ссылку.\n\n"
                "Напишите сюда всё, что хотите ему передать, и через несколько секунд он "
                "получит ваше сообщение, но не будет знать от кого.\n\n"
                "Отправить можно фото, видео, 💬 текст, 🔊 голосовые, 📷видеосообщения "
                "(кружки), а также стикеры.\n\n"
                "⚠️ Это полностью анонимно!",
                reply_markup=await cancel_in()
            )
            return
        except ValueError:
            logger.error(f"Annon bot: Invalid target ID: {args}")

    # Asosiy menyu
    me = await bot.get_me()
    link = f"https://t.me/{me.username}?start={message.from_user.id}"
    print(f"Annon bot: Showing main menu to user {message.from_user.id}")
    await message.answer(
        f"🚀 <b>Начни получать анонимные сообщения прямо сейчас!</b>\n\n"
        f"Твоя личная ссылка:\n👉{link}\n\n"
        f"Размести эту ссылку ☝️ в своём профиле Telegram/Instagram/TikTok или "
        f"других соц сетях, чтобы начать получать сообщения 💬",
        parse_mode="html",
        reply_markup=await main_menu_bt()
    )


async def process_referral(inviter_id: int, new_user_id: int):
    """Referal jarayonini to'liq boshqarish"""
    from asgiref.sync import sync_to_async

    # Debug: parametrlarni tekshirish
    logger.info(f"Annon process_referral: inviter_id type: {type(inviter_id)}, value: {inviter_id}")
    logger.info(f"Annon process_referral: new_user_id type: {type(new_user_id)}, value: {new_user_id}")

    # Agar parametrlar noto'g'ri kelsa, to'g'rilash
    if hasattr(inviter_id, 'from_user'):
        # Agar Message obyekti kelsa
        actual_inviter_id = inviter_id.from_user.id
        actual_new_user_id = new_user_id
    elif hasattr(inviter_id, 'id'):
        # Agar User obyekti kelsa
        actual_inviter_id = inviter_id.id
        actual_new_user_id = new_user_id
    else:
        # Oddiy int qiymatlar
        actual_inviter_id = int(inviter_id)
        actual_new_user_id = int(new_user_id)

    logger.info(f"Annon process_referral: Processing referral from {actual_inviter_id} to {actual_new_user_id}")

    try:
        # To'g'ridan-to'g'ri anon botni topamiz
        from modul.models import Bot

        bot = await sync_to_async(Bot.objects.filter(enable_anon=True).first)()

        if not bot:
            logger.error("Anon bot not found in database")
            return False

        # Inviter ni topish
        inviter = await sync_to_async(ClientBotUser.objects.filter(
            uid=actual_inviter_id,
            bot=bot
        ).select_related('user').first)()

        logger.info(f"Annon process_referral: Inviter check result: {inviter}")

        if not inviter:
            logger.warning(f"Inviter {actual_inviter_id} not found")
            return False

        # Referral balansini to'g'ri yangilash
        reward_amount = 3.0

        inviter.balance += reward_amount
        inviter.referral_count += 1
        inviter.referral_balance += reward_amount

        # MUHIM: save() ni await bilan chaqirish
        await sync_to_async(inviter.save)()

        logger.info(f"Annon bot: Referral stats updated for user {actual_inviter_id}, reward amount: {reward_amount}")
        logger.info(f"New balance: {inviter.balance}, referral count: {inviter.referral_count}")

        # Bildirishnoma jo'natish
        try:
            # Aynan joriy botdan xabar yuborish
            from aiogram import Bot
            from modul.loader import bot_session

            # Joriy bot tokenini olish
            current_bot_token = bot.token

            async with Bot(token=current_bot_token, session=bot_session).context() as bot_instance:
                user_link = f'<a href="tg://user?id={actual_new_user_id}">новый друг</a>'
                notification_text = f"🎉 У вас {user_link}!\n💰 Баланс пополнен на {reward_amount}₽"

                await bot_instance.send_message(
                    chat_id=actual_inviter_id,
                    text=notification_text,
                    parse_mode="HTML"
                )
                logger.info(
                    f"Annon process_referral: Notification sent to {actual_inviter_id} about user {actual_new_user_id}")
        except Exception as e:
            logger.error(f"Error sending notification: {e}")

        return True

    except Exception as e:
        logger.error(f"Error in process_referral: {e}")
        return False


@client_bot_router.callback_query(lambda c: c.data == 'check_chan', AnonBotFilter())
async def check_subscriptions(callback: CallbackQuery, state: FSMContext, bot: Bot):
    user_id = callback.from_user.id
    subscribed = await check_channels(user_id, bot)

    if not subscribed:
        await callback.answer("Пожалуйста, подпишитесь на все каналы.")
        channels = await get_channels_for_check()
        markup = InlineKeyboardBuilder()

        for channel_id, _ in channels:
            try:
                chat = await bot.get_chat(channel_id)
                invite_link = chat.invite_link or await bot.create_chat_invite_link(channel_id)
                markup.button(text=chat.title, url=invite_link)
            except Exception as e:
                continue

        markup.button(text="✅ Проверить подписку", callback_data="check_chan")
        markup.adjust(1)

        await callback.message.edit_text(
            "Для использования бота подпишитесь на наших спонсоров",
            reply_markup=markup.as_markup()
        )
        return

    await callback.answer("Вы успешно подписались на все каналы!")

    user_exists = await check_user(user_id)

    if not user_exists:
        new_link = await create_start_link(bot, str(callback.from_user.id))
        link_for_db = new_link[new_link.index("=") + 1:]

        await add_user(
            tg_id=callback.from_user.id,  # callback.from_user emas, callback.from_user.id bo'lishi kerak
            user_name=callback.from_user.first_name,
            invited="Никто",
            invited_id=None,
            bot_token=bot.token,
            user_link=link_for_db  # user_link qo'shildi
        )

        data = await state.get_data()
        referral = data.get('referral')
        if referral:
            try:
                referral_id = int(referral)
                await process_referral(callback.message, referral_id)
            except ValueError:
                logger.error(f"Invalid referral ID: {referral}")

    data = await state.get_data()
    target_id = data.get('link_user')

    if target_id:
        await callback.message.delete()
        await callback.message.answer(
            "🚀 Здесь можно отправить анонимное сообщение человеку, который опубликовал эту ссылку.\n\n"
            "Напишите сюда всё, что хотите ему передать, и через несколько секунд он "
            "получит ваше сообщение, но не будет знать от кого.\n\n"
            "Отправить можно фото, видео, 💬 текст, 🔊 голосовые, 📷видеосообщения "
            "(кружки), а также стикеры.\n\n"
            "⚠️ Это полностью анонимно!",
            reply_markup=await cancel_in()
        )
        await state.set_state(Links.send_st)
    else:
        me = await bot.get_me()
        link = f"https://t.me/{me.username}?start={callback.from_user.id}"
        await callback.message.delete()
        await callback.message.answer(
            f"🚀 <b>Начни получать анонимные сообщения прямо сейчас!</b>\n\n"
            f"Твоя личная ссылка:\n👉{link}\n\n"
            f"Размести эту ссылку ☝️ в своём профиле Telegram/Instagram/TikTok или "
            f"других соц сетях, чтобы начать получать сообщения 💬",
            parse_mode="html",
            reply_markup=await main_menu_bt()
        )

@client_bot_router.callback_query(F.data.in_(["cancel",
                                              "greeting_rem"]),AnonBotFilter())
async def call_backs(query: CallbackQuery, state: FSMContext,bot: Bot):
    await state.clear()
    if query.data == "check_chan":
        checking = await check_channels(query)
        await query.bot.delete_message(chat_id=query.from_user.id, message_id=query.message.message_id)
        if checking:
            await query.bot.send_message(chat_id=query.from_user.id, text="<b>Готово!\n\n"
                                                                          "Чтобы задать вопрос вашему другу, перейдите по"
                                                                          " его ссылке ещё раз 🔗</b>",
                                         parse_mode="html", reply_markup=await main_menu_bt())
    if query.data == "cancel":
        await query.bot.delete_message(chat_id=query.from_user.id, message_id=query.message.message_id)
        me = await bot.get_me()
        link = f"https://t.me/{me.username}?start={query.from_user.id}"
        print(382)
        await query.bot.send_message(chat_id=query.from_user.id,
                                     text=f"🚀 <b>Начни получать анонимные сообщения прямо сейчас!</b>\n\n"
                                          f"Твоя личная ссылка:\n👉{link}\n\n"
                                          f"Размести эту ссылку ☝️ в своём профиле Telegram/Instagram/TikTok или "
                                          f"других соц сетях, чтобы начать получать сообщения 💬",
                                     parse_mode="html",
                                     reply_markup=await main_menu_bt())

    elif query.data == "greeting_rem":
        await query.bot.delete_message(chat_id=query.from_user.id, message_id=query.message.message_id)
        change_greeting_user(tg_id=query.from_user.id)
        await query.bot.send_message(chat_id=query.from_user.id, text="Отлично!\n\n"
                                                                      "👋 Приветствие очищено!",
                                     reply_markup=await main_menu_bt())


@client_bot_router.callback_query(F.data.startswith("again_"))  # More precise filter
async def again(query: CallbackQuery, state: FSMContext):
    try:
        # Acknowledge the callback to stop loading
        await query.answer()

        # Extract link_user from callback data
        link_user = int(query.data.replace("again_", ""))
        logger.info(f"Preparing to resend to user: {link_user}")

        # Optional: Edit the original message to show progress
        await query.message.edit_text("⏳ Готовлю повторную отправку...")

        # Send the prompt for a new message
        # await query.bot.send_message(
        #     chat_id=query.from_user.id,
        #     text="🚀 Здесь можно <b>отправить анонимное сообщение человеку</b>, который опубликовал "
        #          "эту ссылку.\n\n"
        #          "Напишите сюда всё, что хотите ему передать, и через несколько секунд он "
        #          "получит ваше сообщение, но не будет знать от кого.\n\n"
        #          "Отправить можно фото, видео, 💬 текст, 🔊 голосовые, 📷видеосообщения "
        #          "(кружки), а также стикеры.\n\n"
        #          "⚠️<b> Это полностью анонимно!</b>",
        #     reply_markup=await cancel_in(),
        #     parse_mode="html"
        # )

        # Set state for the next message
        await state.set_state(Links.send_st)
        await state.set_data({"link_user": link_user})

        # Optional: Update the original message after sending the prompt
        await query.message.edit_text(
            "✅ Введите новое сообщение для отправки!",
            reply_markup=await again_in(link_user)
        )

    except Exception as e:
        logger.error(f"Error in again handler: {str(e)}", exc_info=True)
        await query.message.edit_text("❗ Ошибка при подготовке повторной отправки")


@client_bot_router.message(Links.send_st)
async def anon_mes(message: Message, state: FSMContext):
    get_link = await state.get_data()
    receiver = get_link.get("link_user")
    logger.info(f"Trying to send message to user: {receiver}")

    sender_message_id = message.message_id
    text1 = "<b>У тебя новое анонимное сообщение!</b>\n\n"
    text2 = "↩️<i> Свайпни для ответа.</i>"
    caption = ""

    if message.caption:
        caption = message.caption + "\n\n"

    try:
        if message.voice:
            receiver_message = await message.bot.copy_message(
                chat_id=receiver,
                from_chat_id=message.from_user.id,
                message_id=message.message_id,
                caption=text1 + caption + text2,
                parse_mode="html"
            )
            await add_messages_info(
                sender_id=message.from_user.id,
                receiver_id=receiver,
                sender_message_id=sender_message_id,
                receiver_message_id=receiver_message.message_id
            )
            await message.answer(
                "Сообщение отправлено, ожидайте ответ!",
                reply_markup=await again_in(receiver)
            )
            await state.clear()

        elif message.video_note or message.sticker:
            await message.bot.copy_message(
                chat_id=receiver,
                from_chat_id=message.from_user.id,
                message_id=message.message_id
            )
            receiver_message = await message.bot.send_message(
                chat_id=receiver,
                text=text1 + text2,
                parse_mode="html"
            )
            await add_messages_info(
                sender_id=message.from_user.id,
                receiver_id=receiver,
                sender_message_id=sender_message_id,
                receiver_message_id=receiver_message.message_id
            )
            await message.answer(
                "Сообщение отправлено, ожидайте ответ!",
                reply_markup=await again_in(receiver)
            )
            await state.clear()

        elif message.video or message.photo or message.document:
            receiver_message = await message.bot.copy_message(
                chat_id=receiver,
                from_chat_id=message.from_user.id,
                message_id=message.message_id,
                caption=text1 + caption + text2,
                parse_mode="html"
            )
            await add_messages_info(
                sender_id=message.from_user.id,
                receiver_id=receiver,
                sender_message_id=sender_message_id,
                receiver_message_id=receiver_message.message_id
            )
            await message.answer(
                "Сообщение отправлено, ожидайте ответ!",
                reply_markup=await again_in(receiver)
            )
            await state.clear()

        elif message.text:
            receiver_message = await message.bot.send_message(
                chat_id=receiver,
                text=text1 + message.text + "\n\n" + text2,
                parse_mode="html"
            )
            await add_messages_info(
                sender_id=message.from_user.id,
                receiver_id=receiver,
                sender_message_id=sender_message_id,
                receiver_message_id=receiver_message.message_id
            )
            await message.answer(
                "Сообщение отправлено, ожидайте ответ!",
                reply_markup=await again_in(receiver)
            )
            await state.clear()

        else:
            logger.warning(f"Unsupported message type: {message}")
            await message.answer(
                "️️❗Ошибка. Неподдерживаемый формат",
                reply_markup=await main_menu_bt()
            )
            await state.clear()

    except Exception as e:
        logger.error(f"Error sending message: {str(e)}", exc_info=True)
        await message.answer(
            "❗Ошибка. Не удалось отправить сообщение",
            reply_markup=await main_menu_bt()
        )
        await state.clear()

@client_bot_router.message(Links.change_greeting)
async def change_greeting(message: Message, state: FSMContext):
    if message.text:
        new_greeting = "👋" + message.text
        if 4 < len(new_greeting) < 301:
            await message.bot.send_message(chat_id=message.from_user.id,
                                           text="👋 Приветствие не может быть короче 5 и длиннее 300 символов.\n"
                                                "Пожалуйста, попробуйте заново.", reply_markup=await main_menu_bt())
            await state.clear()
        else:
            await message.bot.send_message(chat_id=message.from_user.id, text=f"Отлично!\n\n"
                                                                              f"Ваше новое приветсвие: {new_greeting}",
                                           reply_markup=await main_menu_bt())
            change_greeting_user(message.from_user.id, new_greeting)
            await state.clear()
    else:
        await message.bot.send_message(chat_id=message.from_user.id,
                                       text="Ошибка! 👋Приветствие может состоять только из символов и эмодзи",
                                       reply_markup=await main_menu_bt())
        await state.clear()


@client_bot_router.message(Links.change_link)
async def change_link(message: Message, state: FSMContext):
    if message.text:
        check = await check_link(message.text)
        pattern = r'^[a-zA-Z0-9_]+$'
        check_pattern = re.search(pattern, message.text)
        if not check:
            await message.bot.send_message(chat_id=message.from_user.id,
                                           text="📛 Такая ссылка уже кем-то используется ;(\n"
                                                "Попробуйте заново",
                                           reply_markup=await main_menu_bt())
            await state.clear()
        elif check_pattern and 6 < len(message.text) < 31:
            await change_link_db(message.from_user.id, message.text)
            new_link = await create_start_link(message.bot, message.text)
            await message.bot.send_message(chat_id=message.from_user.id,
                                           text=f"Готово! ✅\n\n"
                                                f"Твоя новая ссылка:\n"
                                                f"🔗<code>{new_link}</code>\n\n"
                                                f"Чтобы скопировать ссылку, просто кликни на неё. "
                                                f"Затем размести в Instagram или других соц. сетях",
                                           parse_mode="html", reply_markup=await main_menu_bt())
            await state.clear()
        else:
            await message.bot.send_message(chat_id=message.from_user.id,
                                           text="Ошибка! 📛 Новая ссылка должна содержать только английские буквы, цифры и нижнее подчеркивание.\n"
                                                "Допустимый размер - от 7 до 30 символов.\n\n"
                                                "Попробуйте заново",
                                           reply_markup=await main_menu_bt())
            await state.clear()


def anon_bot_handlers():
    @client_bot_router.message(AnonBotFilter())
    async def any_or_answer(message: Message, state: FSMContext, bot: Bot):
        # channels_checker = await check_channels(message.from_user.id,bot)
        checker = await check_user(message.from_user.id)
        check = None

        bot_db = await get_bot_by_token(bot.token)
        if not bot_db:
            logger.error(f"Bot not found in database for token: {bot.token}")
            return

        if message.reply_to_message:
            check = await check_reply(message.reply_to_message.message_id)
        # if not channels_checker:
        if not checker:
            new_link = await create_start_link(message.bot, str(message.from_user.id), encode=True)
            link_for_db = new_link[new_link.index("=") + 1:]
            await add_user(message.from_user, link_for_db)
            await message.bot.send_message(chat_id=message.from_user.id, text="", reply_markup=await main_menu_bt())
        elif not checker:
            new_link = await create_start_link(message.bot, str(message.from_user.id), encode=True)
            link_for_db = new_link[new_link.index("=") + 1:]
            await add_user(message.from_user, link_for_db)
            print(605)
            await message.bot.send_message(chat_id=message.from_user.id,
                                           text=f"🚀 <b>Начни получать анонимные сообщения прямо сейчас!</b>\n\n"
                                                f"Твоя личная ссылка:\n👉{new_link}\n\n"
                                                f"Размести эту ссылку ☝️ в своём профиле Telegram/Instagram/TikTok или "
                                                f"других соц сетях, чтобы начать получать сообщения 💬",
                                           parse_mode="html",
                                           reply_markup=await main_menu_bt())
        elif check:
            to_id = check[0]
            to_message = check[1]
            caption = ""
            try:
                if message.caption:
                    caption = message.caption
                if message.voice:
                    await message.bot.copy_message(chat_id=to_id, from_chat_id=message.from_user.id,
                                                   message_id=message.message_id, reply_to_message_id=to_message,
                                                   reply_markup=await again_in(message.from_user.id))
                    await message.bot.send_message(chat_id=message.from_user.id,
                                                   text="<b>Твой ответ успешно отправлен</b> 😺",
                                                   reply_markup=await main_menu_bt(), parse_mode="html")
                    await add_answer_statistic(message.from_user.id)
                elif message.video_note or message.sticker or message.text:
                    await message.bot.copy_message(chat_id=to_id, from_chat_id=message.from_user.id,
                                                   message_id=message.message_id, reply_to_message_id=to_message,
                                                   reply_markup=await again_in(message.from_user.id))
                    await message.bot.send_message(chat_id=message.from_user.id,
                                                   text="<b>Твой ответ успешно отправлен</b> 😺",
                                                   reply_markup=await main_menu_bt(), parse_mode="html")
                    await add_answer_statistic(message.from_user.id)
                elif message.video or message.photo or message.document:
                    await message.bot.copy_message(chat_id=to_id, from_chat_id=message.from_user.id,
                                                   message_id=message.message_id,
                                                   caption=caption,
                                                   reply_to_message_id=to_message,
                                                   reply_markup=await again_in(message.from_user.id))
                    await message.bot.send_message(chat_id=message.from_user.id,
                                                   text="<b>Твой ответ успешно отправлен</b> 😺",
                                                   reply_markup=await main_menu_bt(), parse_mode="html")
                    await add_answer_statistic(message.from_user.id)
                else:
                    await message.bot.send_message(message.from_user.id, "️️❗Ошибка. Неподдерживаемый формат",
                                                   reply_markup=await main_menu_bt())
            except:
                await message.bot.send_message(message.from_user.id, "️️❗Ошибка. Не удалось отправить ответ",
                                               reply_markup=await main_menu_bt())
        else:
            if message.text == "☕️Поддержать разработчика":
                await message.bot.send_message(chat_id=message.from_user.id,
                                               text="Если вам нравится наш бот, вы можете "
                                                    "поддержать нас звездами⭐️",
                                               reply_markup=await payment_amount_keyboard())
            elif message.text == "👋Изменить приветствие":
                await message.bot.send_message(chat_id=message.from_user.id, text="👋Вы можете установить приветствие. "
                                                                                  "Каждый, кто перейдёт по вашей ссылке, "
                                                                                  "увидит его.\n"
                                                                                  "Приветствие не может быть короче 5 и длиннее 300 символов.",
                                               reply_markup=await greeting_in())
                await state.set_state(Links.change_greeting)
            elif message.text == "📛Изменить ссылку":
                me = await bot.get_me()
                link = f"https://t.me/{me.username}?start={message.from_user.id}"
                await message.bot.send_message(chat_id=message.from_user.id,
                                               text=f"Сейчас ваша ссылка для получения анонимных сообщений выглядит так:\n"
                                                    f"<code>{link}</code>\n\n"
                                                    f"📛Новая ссылка должна содержать только английские буквы, цифры и нижнее подчеркивание.\n\n"
                                                    f"❗ Обратите внимание, что при смене ссылки, старая ссылка перестанет быть активной!",
                                               parse_mode="html", reply_markup=await link_in())
                await state.set_state(Links.change_link)
            elif message.text == "🚀Начать":
                await state.clear()
                me = await bot.get_me()
                link = f"https://t.me/{me.username}?start={message.from_user.id}"
                print(679)
                await message.bot.send_message(chat_id=message.from_user.id,
                                               text=f"🚀 <b>Начни получать анонимные сообщения прямо сейчас!</b>\n\n"
                                                    f"Твоя личная ссылка:\n👉{link}\n\n"
                                                    f"Размести эту ссылку ☝️ в своём профиле Telegram/Instagram/TikTok или "
                                                    f"других соц сетях, чтобы начать получать сообщения 💬",
                                               parse_mode="html",
                                               reply_markup=await main_menu_bt())
            elif message.text == "⭐️Ваша статистика":
                statistic = await get_all_statistic(message.from_user.id)
                bot_info = await create_start_link(message.bot, str(message.from_user.id))
                bot_cor = bot_info.replace("https://t.me/", "")
                index = bot_cor.index("?")
                bot_username = bot_cor[:index]

                await message.bot.send_message(chat_id=message.from_user.id,
                                               text=f"Ваша статистика:\n\n"
                                                    f"💬 Сообщений сегодня: {statistic.get('messages_today')}\n"
                                                    f"↩️ Ответов сегодня: {statistic.get('answers_today')}\n"
                                                    # f"👁‍🗨 Переходов по ссылке сегодня: {statistic.get('links_today')}\n"
                                                    f"⭐️ Популярность сегодня: {statistic.get('position_today')} место\n\n"
                                                    f"💬 Сообщений за всё время: {statistic.get('messages_overall')}\n"
                                                    f"↩️ Ответов за всё время: {statistic.get('answers_overall')}\n"
                                                    # f"👁‍🗨 Переходов по ссылке за всё время: {statistic.get('links_overall')}\n"
                                                    f"⭐️ Популярность за всё время: {statistic.get('position_overall')} место\n\n"
                                                    f"Для повышения ⭐️ популярности необходимо увеличить "
                                                    f"количество переходов по вашей ссылке.\n\n"
                                                    f"@{bot_username}",
                                               parse_mode="html", reply_markup=await main_menu_bt())

            else:
                me = await bot.get_me()
                link = f"https://t.me/{me.username}?start={message.from_user.id}"
                print(712)
                await message.bot.send_message(chat_id=message.from_user.id,
                                               text=f"🚀 <b>Начни получать анонимные сообщения прямо сейчас!</b>\n\n"
                                                    f"Твоя личная ссылка:\n👉{link}\n\n"
                                                    f"Размести эту ссылку ☝️ в своём профиле Telegram/Instagram/TikTok или "
                                                    f"других соц сетях, чтобы начать получать сообщения 💬",
                                               parse_mode="html",
                                               reply_markup=await main_menu_bt())

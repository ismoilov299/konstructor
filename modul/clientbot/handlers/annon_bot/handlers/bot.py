import logging
import re
from contextlib import suppress

from aiogram import F, Bot, types,html
from aiogram.exceptions import TelegramForbiddenError
from aiogram.filters import CommandStart, Filter, CommandObject
from aiogram.utils.deep_linking import create_start_link
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, BotCommand, CallbackQuery, LabeledPrice
from aiogram.utils.keyboard import InlineKeyboardBuilder
from asgiref.sync import sync_to_async
from django.db import transaction

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
from modul.clientbot.shortcuts import get_bot_by_token
from modul.models import UserTG, AdminInfo

logger = logging.getLogger(__name__)



async def check_channels(message):
    all_channels = await get_channels_for_check()
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
    return True


async def payment(message, amount):
    prices = [LabeledPrice(label="XTR", amount=amount)]
    await message.answer_invoice(
        title="Поддержка бота",
        description=f"Поддержать бота на {amount} звёзд!",
        prices=prices,
        provider_token="",
        payload="bot_support",
        currency="XTR",
        reply_markup=await payment_keyboard(amount),
    )

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
            member = await bot.get_chat_member(chat_id=channel, user_id=user_id)
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
           '<b>Чтобы воспользоваться ботом, необходимо подписаться на каналы</b>',
           reply_markup=kb,
           parse_mode="HTML"
       )
       return

   me = await bot.get_me()
   anon_link = f"https://t.me/{me.username}?start={message.from_user.id}"
   ref_link = f"https://t.me/{me.username}?start=r{message.from_user.id}"

   price = await get_actual_price()
   min_withdraw = await get_actual_min_amount()

   await message.bot.send_message(
       message.from_user.id,
       f"👥 Приглашай друзей и зарабатывай! За \nкаждого друга ты получишь {price}₽.\n\n"
       f"🔗 Ваша ссылка для приглашений:\n{ref_link}\n\n"
       f"🔒 Ваша ссылка для анонимных сообщений:\n{anon_link}\n\n"
       f"💰 Минимальная сумма для вывода: {min_withdraw}₽",
       reply_markup=await main_menu_bt2()
   )


@client_bot_router.message(CommandStart(), AnonBotFilter())
async def start(message: Message, state: FSMContext, bot: Bot):
    try:
        logger.info(f"Start command received from user {message.from_user.id}")
        args = message.text.split(' ')
        user_id = args[1] if len(args) > 1 else None

        channels_checker = await check_channels(message)
        checker = await check_user(message.from_user.id)

        # Yangi foydalanuvchini qo'shish
        if not channels_checker and not checker:
            await add_user(message.from_user, str(message.from_user.id))
        elif channels_checker:
            if not checker:
                await add_user(message.from_user, str(message.from_user.id))

            if user_id:
                # Referal kelgan bo'lsa
                if user_id.startswith('r') and user_id[1:].isdigit():
                    inviter_id = int(user_id[1:])
                    inviter = await get_user_by_id(inviter_id)

                    if inviter:
                        with suppress(TelegramForbiddenError):
                            user_link = html.link('реферал', f'tg://user?id={message.from_user.id}')
                            await bot.send_message(
                                chat_id=inviter_id,
                                text=f"У вас новый {user_link}!"
                            )

                        try:
                            @sync_to_async
                            @transaction.atomic
                            def update_referral():
                                try:
                                    user_tg = UserTG.objects.select_for_update().get(uid=inviter_id)
                                    admin_info = AdminInfo.objects.first()

                                    if not admin_info:
                                        raise ValueError("AdminInfo is not configured in the database.")

                                    user_tg.refs += 1
                                    user_tg.balance += float(admin_info.price or 10.0)
                                    user_tg.save()
                                    logger.info(f"Referral updated successfully for user {inviter_id}")
                                    return True
                                except UserTG.DoesNotExist:
                                    logger.error(f"Inviter with ID {inviter_id} does not exist.")
                                    return False
                                except Exception as ex:
                                    logger.error(f"Unexpected error during referral update: {ex}")
                                    raise

                            referral_updated = await update_referral()
                            if referral_updated:
                                logger.info(f"Referral updated successfully for {inviter_id}")
                            else:
                                logger.warning(f"Failed to update referral for {inviter_id}")

                        except Exception as e:
                            logger.error(f"Error updating referral stats: {e}")

                    # Yangi foydalanuvchi uchun xabar
                    me = await bot.get_me()
                    link = f"https://t.me/{me.username}?start={message.from_user.id}"
                    await message.bot.send_message(
                        chat_id=message.from_user.id,
                        text=f"🚀 <b>Начни получать анонимные сообщения прямо сейчас!</b>\n\n"
                             f"Твоя личная ссылка:\n👉{link}\n\n"
                             f"Размести эту ссылку ☝️ в своём профиле Telegram/Instagram/TikTok или "
                             f"других соц сетях, чтобы начать получать сообщения 💬",
                        parse_mode="html",
                        reply_markup=await main_menu_bt()
                    )

                # Anonim xabar kelgan bo'lsa
                else:
                    logger.info(f"Looking up user with ID: {user_id}")
                    link_user = await get_user_by_id(user_id)

                    if link_user:
                        await add_link_statistic(link_user)
                        greeting = await get_greeting(link_user)

                        await message.bot.send_message(
                            chat_id=message.from_user.id,
                            text="🚀 Здесь можно <b>отправить анонимное сообщение человеку</b>...",
                            reply_markup=await cancel_in(),
                            parse_mode="html"
                        )

                        if greeting:
                            await message.bot.send_message(chat_id=message.from_user.id, text=greeting)

                        await state.set_state(Links.send_st)
                        await state.set_data({"link_user": link_user})
                    else:
                        logger.error(f"User not found with ID: {user_id}")

            else:
                me = await bot.get_me()
                link = f"https://t.me/{me.username}?start={message.from_user.id}"
                await message.bot.send_message(
                    chat_id=message.from_user.id,
                    text=f"🚀 <b>Начни получать анонимные сообщения прямо сейчас!</b>\n\n"
                         f"Твоя личная ссылка:\n👉{link}\n\n"
                         f"Размести эту ссылку ☝️ в своём профиле Telegram/Instagram/TikTok или "
                         f"других соц сетях, чтобы начать получать сообщения 💬",
                    parse_mode="html",
                    reply_markup=await main_menu_bt()
                )

    except Exception as e:
        logger.error(f"Error in start handler: {e}", exc_info=True)
        await message.answer(
            "Произошла ошибка при запуске. Пожалуйста, попробуйте позже."
        )


@client_bot_router.callback_query(F.data.in_(["check_chan", "cancel", "pay10", "pay20", "pay50", "pay100", "pay500",
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
        await query.bot.send_message(chat_id=query.from_user.id,
                                     text=f"🚀 <b>Начни получать анонимные сообщения прямо сейчас!</b>\n\n"
                                          f"Твоя личная ссылка:\n👉{link}\n\n"
                                          f"Размести эту ссылку ☝️ в своём профиле Telegram/Instagram/TikTok или "
                                          f"других соц сетях, чтобы начать получать сообщения 💬",
                                     parse_mode="html",
                                     reply_markup=await main_menu_bt())
    elif query.data == "pay10":
        await payment(query.message, 10)
    elif query.data == "pay20":
        await payment(query.message, 20)
    elif query.data == "pay50":
        await payment(query.message, 50)
    elif query.data == "pay100":
        await payment(query.message, 100)
    elif query.data == "pay500":
        await payment(query.message, 500)
    elif query.data == "greeting_rem":
        await query.bot.delete_message(chat_id=query.from_user.id, message_id=query.message.message_id)
        change_greeting_user(tg_id=query.from_user.id)
        await query.bot.send_message(chat_id=query.from_user.id, text="Отлично!\n\n"
                                                                      "👋 Приветствие очищено!",
                                     reply_markup=await main_menu_bt())


@client_bot_router.callback_query(lambda call: "again_" in call.data)
async def again(query: CallbackQuery, state: FSMContext):
    link_user = int(query.data.replace("again_", ""))
    await query.bot.send_message(chat_id=query.from_user.id,
                                 text="🚀 Здесь можно <b>отправить анонимное сообщение человеку</b>, который опубликовал "
                                      "эту ссылку.\n\n"
                                      "Напишите сюда всё, что хотите ему передать, и через несколько секунд он "
                                      "получит ваше сообщение, но не будет знать от кого.\n\n"
                                      "Отправить можно фото, видео, 💬 текст, 🔊 голосовые, 📷видеосообщения "
                                      "(кружки), а также стикеры.\n\n"
                                      "⚠️<b> Это полностью анонимно!</b>", reply_markup=await cancel_in(),
                                 parse_mode="html")
    await state.set_state(Links.send_st)
    await state.set_data({"link_user": link_user})


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
        channels_checker = await check_channels(message)
        checker = await check_user(message.from_user.id)
        check = None

        bot_db = await get_bot_by_token(bot.token)
        if not bot_db:
            logger.error(f"Bot not found in database for token: {bot.token}")
            return

        if message.reply_to_message:
            check = await check_reply(message.reply_to_message.message_id)
        if not channels_checker:
            if not checker:
                new_link = await create_start_link(message.bot, str(message.from_user.id), encode=True)
                link_for_db = new_link[new_link.index("=") + 1:]
                await add_user(message.from_user, link_for_db)
                await message.bot.send_message(chat_id=message.from_user.id, text="", reply_markup=await main_menu_bt())
        elif not checker:
            new_link = await create_start_link(message.bot, str(message.from_user.id), encode=True)
            link_for_db = new_link[new_link.index("=") + 1:]
            await add_user(message.from_user, link_for_db)

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
                                                    f"👁‍🗨 Переходов по ссылке сегодня: {statistic.get('links_today')}\n"
                                                    f"⭐️ Популярность сегодня: {statistic.get('position_today')} место\n\n"
                                                    f"💬 Сообщений за всё время: {statistic.get('messages_overall')}\n"
                                                    f"↩️ Ответов за всё время: {statistic.get('answers_overall')}\n"
                                                    f"👁‍🗨 Переходов по ссылке за всё время: {statistic.get('links_overall')}\n"
                                                    f"⭐️ Популярность за всё время: {statistic.get('position_overall')} место\n\n"
                                                    f"Для повышения ⭐️ популярности необходимо увеличить "
                                                    f"количество переходов по вашей ссылке.\n\n"
                                                    f"@{bot_username}",
                                               parse_mode="html", reply_markup=await main_menu_bt())

            else:
                me = await bot.get_me()
                link = f"https://t.me/{me.username}?start={message.from_user.id}"
                await message.bot.send_message(chat_id=message.from_user.id,
                                               text=f"🚀 <b>Начни получать анонимные сообщения прямо сейчас!</b>\n\n"
                                                    f"Твоя личная ссылка:\n👉{link}\n\n"
                                                    f"Размести эту ссылку ☝️ в своём профиле Telegram/Instagram/TikTok или "
                                                    f"других соц сетях, чтобы начать получать сообщения 💬",
                                               parse_mode="html",
                                               reply_markup=await main_menu_bt())

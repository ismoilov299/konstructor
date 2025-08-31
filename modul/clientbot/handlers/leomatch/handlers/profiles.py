from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.filters import StateFilter
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from asgiref.sync import sync_to_async

from modul.clientbot.handlers.leomatch.data.state import LeomatchProfiles, LeomatchMain
from modul.clientbot.handlers.leomatch.shortcuts import bot_show_profile_db, clear_all_likes, delete_like, get_leo, \
    get_leos_id, get_first_like, leo_set_like, show_media, show_profile_db, get_leos_id_simple
from modul.clientbot.handlers.leomatch.keyboards.inline_kb import profile_alert, profile_alert_action, \
    profile_like_action, \
    profile_view_action, write_profile
from modul.clientbot.handlers.leomatch.keyboards.reply_kb import cancel
from modul.clientbot.handlers.leomatch.data.callback_datas import LeomatchLikeAction, LeomatchProfileAction, \
    LeomatchProfileAlert, LeomatchProfileBlock, LikeActionEnum, ProfileActionEnum
from modul.clientbot.handlers.leomatch.handlers.shorts import manage
from modul.models import LeoMatchModel, User, UserTG
from modul.config import settings_conf
from modul.loader import client_bot_router, main_bot, main_bot_router
from aiogram.fsm.context import FSMContext
from aiogram import types, F

async def start(message: types.Message, state: FSMContext):
    print(f"\n🎯 === PROFILES START ===")

    # State'dan user ID olish
    data = await state.get_data()
    user_id = data.get("me")

    if not user_id:
        user_id = message.from_user.id if message.from_user else None
        if not user_id:
            await message.answer("❌ Ошибка: не удается определить пользователя")
            return

    print(f"✅ Using user_id: {user_id}")

    await state.clear()
    await state.update_data(me=user_id)
    await message.delete()
    await message.answer("🔍 Начинаем поиск...")

    # Qidiruv
    leos = await get_leos_id_simple(user_id)
    print(f"📊 Found {len(leos)} users: {leos}")

    if len(leos) == 0:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Попробовать еще раз", callback_data="restart_search")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_main")]
        ])
        await message.answer("😔 Нет доступных профилей", reply_markup=keyboard)
        return

    await state.update_data(leos=leos)
    await next_l(message, state)
    print(f"✅ PROFILES START COMPLETE")


async def next_l_direct(message: types.Message, state: FSMContext):
    """To'g'ridan-to'g'ri next_l"""
    data = await state.get_data()
    leos = data.get("leos", [])

    print(f"🎯 next_l_direct: {len(leos)} users in queue")

    if len(leos) > 0:
        current = leos.pop(0)
        await state.update_data(leos=leos)

        await show_profile_db(message, current, keyboard=profile_view_action(current))
        await state.set_state(LeomatchProfiles.LOOCK)
        print(f"✅ Showing profile: {current}")
    else:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Попробовать еще раз", callback_data="restart_search")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_main")]
        ])
        await message.answer("😔 Больше нет пользователей для просмотра", reply_markup=keyboard)


async def next_l(message: types.Message, state: FSMContext):
    data = await state.get_data()
    leos = data.get("leos")
    if len(leos) > 0:
        current = leos.pop(0)
        await state.update_data(leos=leos)
        keyboard = profile_view_action(current)
        print(f"🔍 DEBUG: Created keyboard for user {current}")
        print(f"🔍 DEBUG: Keyboard type: {type(keyboard)}")
        print(f"🔍 DEBUG: Keyboard content: {keyboard}")

        await show_profile_db(message, current, keyboard=keyboard)
        await state.set_state(LeomatchProfiles.LOOCK)
    else:
        # Inline keyboard bilan tugmacha
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Попробовать еще раз", callback_data="restart_search")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_main")]
        ])
        await message.answer("😔 Больше нет пользователей для просмотра", reply_markup=keyboard)
        # await manage(message, state)


async def next_like(message: types.Message, state: FSMContext):
    data = await state.get_data()
    me = data.get("me")
    if not me:
        me = message.from_user.id
    leo = await get_first_like(me)
    if leo:
        user_leo = await leo.from_user
        user = await user_leo.user
        try:
            await show_profile_db(message, user.uid, profile_like_action(user.uid), leo.message)
            await state.set_state(LeomatchProfiles.MANAGE_LIKE)
        except:
            await delete_like(user.uid, me)
            await next_like(message, state)
    else:
        leo_me = await get_leo(me)
        await state.clear()

        # Inline keyboard bilan tugma
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_main")]
        ])
        await message.answer("💔 Больше нет лайков", reply_markup=keyboard)

        # Leo mavjudligini tekshirish
        if leo_me:
            leo_me.count_likes = 0
            await leo_me.save()


async def like(message: types.Message, state: FSMContext, from_uid: int, to_uid: int, msg: str = None):
    try:
        # Like qo'shish
        await leo_set_like(from_uid, to_uid, msg)

        # From user ma'lumotlarini olish
        from_user = await get_leo(from_uid)
        from_name = from_user.full_name if from_user else "Неизвестный пользователь"
        from_age = from_user.age if from_user else ""
        from_city = from_user.city if from_user else ""

        # Full name with age and city for like notification
        from_full_info = f"{from_name}"
        if from_age and from_city:
            from_full_info += f", {from_age}, {from_city}"
        elif from_age:
            from_full_info += f", {from_age}"

        # User link yaratish (HTML format)
        user_link = f'<a href="tg://user?id={from_uid}">{from_name}</a>'

        # To user ma'lumotlarini olish
        to_user = await get_leo(to_uid)

        # ASYNC-SAFE user.uid olish
        @sync_to_async
        def get_user_uid(leo):
            try:
                if leo and leo.user:
                    user_tg = UserTG.objects.filter(user=leo.user).first()
                    return user_tg.uid if user_tg else None
                return None
            except Exception as e:
                print(f"Error getting user UID: {e}")
                return None

        to_user_uid = await get_user_uid(to_user) if to_user else None

        if msg and to_user and to_user_uid:
            try:
                # Video yoki text ekanini tekshirish
                if isinstance(msg, str):
                    if msg.startswith('bnVid_'):  # Video note format
                        try:
                            # Video note yuborishdan oldin kimdan kelganligini bildirish
                            await message.bot.send_message(
                                chat_id=to_user_uid,
                                text=f"💌 Видео-сообщение от {user_link}:",
                                parse_mode="HTML"
                            )
                            await message.bot.send_video_note(
                                chat_id=to_user_uid,
                                video_note=msg
                            )
                        except (TelegramBadRequest, TelegramForbiddenError) as e:
                            print(f"Could not send video note to user {to_user_uid}: {e}")
                            if "chat not found" in str(e).lower() or "bot was blocked by the user" in str(e).lower():
                                await message.answer(
                                    "⚠️ Сообщение не может быть доставлено. Пользователь заблокировал бота или удалил аккаунт.")
                            else:
                                await message.answer("❌ Не удалось отправить видео-сообщение")
                            return
                    else:
                        try:
                            result = await message.bot.send_message(
                                chat_id=to_user_uid,
                                text=f"💌 Новое сообщение от {user_link}:\n\n{msg}",
                                parse_mode="HTML"
                            )
                            print(f"Message sent result: {result}")
                        except (TelegramBadRequest, TelegramForbiddenError) as e:
                            print(f"Could not send message to user {to_user_uid}: {e}")
                            if "chat not found" in str(e).lower() or "bot was blocked by the user" in str(e).lower():
                                await message.answer(
                                    "⚠️ Сообщение не может быть доставлено. Пользователь заблокировал бота или удалил аккаунт.")
                            else:
                                await message.answer("❌ Не удалось отправить сообщение")
                            return

                await message.answer("✅ Сообщение отправлено!")
            except Exception as e:
                print(f"Error sending message to user {to_uid}: {e}")
                await message.answer("❌ Не удалось отправить сообщение")
        else:
            # Oddiy like yuborish (xabar yo'q)
            if to_user and to_user_uid:
                try:
                    await message.bot.send_message(
                        chat_id=to_user_uid,
                        text=f"❤️ Вам поставил лайк {user_link}!",
                        parse_mode="HTML"
                    )
                except (TelegramBadRequest, TelegramForbiddenError) as e:
                    print(f"Could not send like notification to user {to_user_uid}: {e}")
                except Exception as e:
                    print(f"Error sending like notification to user {to_uid}: {e}")

            await message.answer("💖 Лайк отправлен")

        await next_l(message, state)

    except Exception as e:
        print(f"Error in like handler: {e}")
        import traceback
        print(traceback.format_exc())
        await message.answer("❌ Произошла ошибка. Попробуйте позже.")


# =============== CALLBACK QUERY HANDLERS ===============

@client_bot_router.callback_query(F.data == "restart_search")
async def handle_restart_search(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_reply_markup()
    await state.update_data(me=callback.from_user.id)
    await start(callback.message, state)
    await callback.answer("🔄 Поиск перезапущен")


@client_bot_router.callback_query(F.data == "back_to_main")
async def handle_back_to_main(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_reply_markup()
    await state.update_data(me=callback.from_user.id)
    await manage(callback.message, state)
    await callback.answer()

@client_bot_router.callback_query(F.data == "cancel_message_input", LeomatchProfiles.INPUT_MESSAGE)
async def handle_cancel_message_input(callback: types.CallbackQuery, state: FSMContext):
    """Xabar yozishni bekor qilish"""
    data = await state.get_data()
    leos: list = data.get("leos")
    leos.insert(0, data.get("selected_id"))
    await state.update_data(selected_id=None, leos=leos)
    await callback.message.edit_text("❌ Отменено")
    await next_l(callback.message, state)
    await callback.answer()


@client_bot_router.callback_query(F.data == "manage_likes_yes", LeomatchProfiles.MANAGE_LIKES)
async def handle_manage_likes_yes(callback: types.CallbackQuery, state: FSMContext):
    """Layklar bilan ishlashni boshlash"""
    await callback.message.edit_text("💕 Вот аккаунты, кому Вы понравились:")
    await next_like(callback.message, state)
    await callback.answer()


@client_bot_router.callback_query(F.data == "manage_likes_no", LeomatchProfiles.MANAGE_LIKES)
async def handle_manage_likes_no(callback: types.CallbackQuery, state: FSMContext):
    """Barcha layklarni o'chirish"""
    await callback.message.edit_text("🗑️ Все лайки удалены")
    await clear_all_likes(callback.from_user.id)
    await callback.answer()


@client_bot_router.callback_query(LeomatchProfileAction.filter(), StateFilter(LeomatchProfiles.LOOCK))
async def choose_percent(query: types.CallbackQuery, state: FSMContext, callback_data: LeomatchProfileAction):
    try:
        await query.message.edit_reply_markup()
        await state.update_data(me=query.from_user.id)

        if callback_data.action == ProfileActionEnum.LIKE:
            await like(query.message, state, query.from_user.id, callback_data.user_id)
        elif callback_data.action == ProfileActionEnum.MESSAGE:
            current_state = await state.get_state()

            # Inline keyboard yaratamiz
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_message_input")]
            ])

            await query.message.answer(
                "✍️ Введите сообщение или отправьте видео (макс 15 сек)",
                reply_markup=keyboard
            )
            await state.update_data({
                'selected_id': callback_data.user_id,
                'previous_state': current_state
            })
            await state.set_state(LeomatchProfiles.INPUT_MESSAGE)
        elif callback_data.action == ProfileActionEnum.REPORT:
            kb = InlineKeyboardBuilder()
            kb.row(
                InlineKeyboardButton(
                    text="✅ Да",
                    callback_data=LeomatchProfileAlert(
                        action="yes",
                        sender_id=query.from_user.id,
                        account_id=callback_data.user_id
                    ).pack()
                ),
                InlineKeyboardButton(
                    text="❌ Нет",
                    callback_data=LeomatchProfileAlert(action="no").pack()
                ),
                width=2
            )

            await query.message.answer(
                "⚠️ Вы точно хотите подать жалобу?\n\n⚡ Учтите, если жалоба будет необоснованной, то вы сами можете быть забанены",
                reply_markup=kb.as_markup()
            )

        elif callback_data.action == ProfileActionEnum.SLEEP:
            pass

        elif callback_data.action == ProfileActionEnum.DISLIKE:
            await next_l(query.message, state)
            await state.set_state(LeomatchProfiles.LOOCK)

    except Exception as e:
        print(f"Error in choose_percent handler: {e}")
        await query.message.answer("❌ Произошла ошибка, попробуйте еще раз")


# =============== MESSAGE HANDLERS (BACKWARD COMPATIBILITY) ===============

@client_bot_router.message(F.text == ("Отменить"), LeomatchProfiles.INPUT_MESSAGE)
async def handle_cancel_message_text(message: types.Message, state: FSMContext):
    """Xabar yozishni bekor qilish (matn orqali)"""
    data = await state.get_data()
    leos: list = data.get("leos")
    leos.insert(0, data.get("selected_id"))
    await state.update_data(selected_id=None, leos=leos)
    await message.answer("❌ Отменено")
    await next_l(message, state)


@client_bot_router.message(LeomatchProfiles.INPUT_MESSAGE)
async def process_message(message: types.Message, state: FSMContext):
    data = await state.get_data()
    selected_id = data.get("selected_id")
    await state.update_data(selected_id=None)
    await state.set_state("*")

    msg = None
    if message.text:
        msg = message.text
    elif message.video_note:
        msg = message.video_note.file_id
    else:
        # Inline keyboard bilan tugma
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_message_input")]
        ])
        await message.answer("📝 Пожалуйста, напишите текст или отправьте видео", reply_markup=keyboard)
        return

    await like(message, state, message.from_user.id, selected_id, msg)


@client_bot_router.message(F.text == ("Да"), LeomatchProfiles.MANAGE_LIKES)
async def handle_manage_likes_yes_text(message: types.Message, state: FSMContext):
    """Layklar bilan ishlashni boshlash (matn orqali)"""
    await message.answer("💕 Вот аккаунты, кому Вы понравились:")
    await next_like(message, state)


@client_bot_router.message(F.text == ("Нет"), LeomatchProfiles.MANAGE_LIKES)
async def handle_manage_likes_no_text(message: types.Message):
    """Barcha layklarni o'chirish (matn orqali)"""
    await message.answer("🗑️ Все лайки удалены")
    await clear_all_likes(message.from_user.id)


@client_bot_router.callback_query(LeomatchProfileAction.filter(), LeomatchProfiles.MANAGE_LIKE)
async def handle_like_action(query: types.CallbackQuery, state: FSMContext, callback_data: LeomatchLikeAction):
    try:
        await query.message.edit_reply_markup()
    except:
        pass

    if callback_data.action == LikeActionEnum.LIKE:
        leo = await get_leo(callback_data.user_id)
        link = ""
        client = await leo.user

        is_username = False
        if client.username:
            link = client.username
            is_username = True
        else:
            link = client.uid

        try:
            await bot_show_profile_db(callback_data.user_id, query.from_user.id)
        except:
            await next_like(query.message, state)

        try:
            await query.message.answer("🎉 Начинайте общаться!", reply_markup=write_profile(link, is_username))
        except:
            await query.message.answer(
                "😔 Извините, Вы не сможете начать общение, так как у пользователя приватный аккаунт")
    elif callback_data.action == LikeActionEnum.REPORT:
        pass

    await state.set_data({"me": query.from_user.id})
    await delete_like(callback_data.user_id, query.from_user.id)
    await next_like(query.message, state)


@client_bot_router.callback_query(LeomatchProfileAlert.filter(), StateFilter(LeomatchProfiles.LOOCK))
async def process_alert(query: types.CallbackQuery, callback_data: LeomatchProfileAlert, state: FSMContext):
    try:
        print(f"Processing alert with action: {callback_data.action}")

        if callback_data.action == "yes":
            sender = await get_leo(callback_data.sender_id)
            account = await get_leo(callback_data.account_id)

            if sender and account:
                sender_user = sender.user
                account_user = account.user

                if sender_user and account_user:
                    await show_media(main_bot, settings_conf.ADMIN, callback_data.account_id)

                    report_text = (
                        f"🚨 ЖАЛОБА\n\n"
                        f"От: @{sender_user.username} ({sender_user.uid})\n"
                        f"На: @{account_user.username} ({account_user.uid})\n"
                    )

                    await main_bot.send_message(
                        chat_id=settings_conf.ADMIN,
                        text=report_text,
                        reply_markup=profile_alert_action(callback_data.sender_id, callback_data.account_id)
                    )
                    await query.message.edit_text("✅ Жалоба отправлена администратору")
                else:
                    await query.message.edit_text("❌ Ошибка: пользователь не найден")
            else:
                await query.message.edit_text("❌ Ошибка: пользователь не найден")

        elif callback_data.action == "no":
            await query.message.edit_text("❌ Жалоба отменена")

        await next_l(query.message, state)

    except Exception as e:
        print(f"Error processing report: {e}")
        await query.message.edit_text("✅ Жалоба отправлена")
        await next_l(query.message, state)


# =============== UTILITY FUNCTIONS ===============

async def create_likes_management_keyboard():
    """Layklar boshqaruvi uchun keyboard"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да, показать", callback_data="manage_likes_yes")],
        [InlineKeyboardButton(text="❌ Нет, удалить все", callback_data="manage_likes_no")]
    ])
    return keyboard


async def show_likes_prompt(message: types.Message, state: FSMContext):
    """Layklar haqida so'rash"""
    keyboard = await create_likes_management_keyboard()
    await message.answer(
        "💕 У вас есть новые лайки!\n\n"
        "Хотите посмотреть, кому вы понравились?",
        reply_markup=keyboard
    )
    await state.set_state(LeomatchProfiles.MANAGE_LIKES)
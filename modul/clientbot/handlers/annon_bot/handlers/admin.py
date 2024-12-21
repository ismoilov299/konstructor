from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from modul.clientbot import shortcuts
from modul.clientbot.handlers.annon_bot.adminservice import *
from modul.clientbot.handlers.annon_bot.keyboards.buttons import admin_menu_in, admin_channels_in, cancel_bt, \
    main_menu_bt
from modul.clientbot.handlers.annon_bot.states import AnonBotFilter, ChangeAdminInfo
from modul.loader import client_bot_router
from modul.models import Bot


async def get_admin_id(bot: Bot):
    bot_db = await shortcuts.get_bot(bot)
    return bot_db.owner.uid


@client_bot_router.message(Command(commands=["admin"]), AnonBotFilter())
async def admin_mm(message: Message):
    """
    Admin panelga kirish funksiyasi.
    Faqat admin va 'anon' moduliga ega botlar uchun ishlaydi.
    """
    count = await get_users_count()
    await message.answer(
        f"🕵 Панель админа\n"
        f"Количество юзеров в боте: {count}",
        reply_markup=await admin_menu_in()
    )


@client_bot_router.callback_query(F.data.in_(["cancel", "none",
                                              "change_channels", "add_channel", "delete_channel", "mailing"]))
async def call_backs(query: CallbackQuery, state: FSMContext):
    await state.clear()
    if query.data == "cancel":
        await query.bot.delete_message(chat_id=query.from_user.id, message_id=query.message.message_id)
        await state.clear()
    elif query.data == "none":
        pass
    elif query.data == "change_channels":
        text = "Обязательные подписки: \n"
        all_channels = await get_channels_for_admin()
        if all_channels:
            for i in all_channels:
                text += (f"\nАйди <b>ПОДПИСКИ</b>: {i[0]}\n"
                         f"Username канала: {i[1]}\n"
                         f"ID канала: {i[2]}\n")
        await query.bot.send_message(query.from_user.id, text=text,
                                     reply_markup=await admin_channels_in(), parse_mode="html")
    elif query.data == "add_channel":
        await query.bot.send_message(query.from_user.id, "Введите ссылку на канал (формат: t.me/ или https://t.me/)",
                                     reply_markup=await cancel_bt())
        await state.set_state(ChangeAdminInfo.get_channel_url)
    elif query.data == "delete_channel":
        await query.bot.send_message(query.from_user.id, "Введите ID <b>ПОДПИСКИ</b> для удаления",
                                     reply_markup=await cancel_bt(), parse_mode="html")
        await state.set_state(ChangeAdminInfo.delete_channel)
    elif query.data == "mailing":
        await query.bot.send_message(query.from_user.id,
                                     "Введите сообщение для рассылки, либо отправьте фотографии/видео с описанием",
                                     reply_markup=await cancel_bt())
        await state.set_state(ChangeAdminInfo.mailing)


@client_bot_router.message(ChangeAdminInfo.get_channel_url)
async def get_new_channel_url(message: Message, state: FSMContext):
    if message.text == "❌Отменить":
        await message.bot.send_message(message.from_user.id, "🚫Действие отменено", reply_markup=await main_menu_bt())
        await state.clear()
    elif "t.me/" in message.text.lower() or "https://t.me/" in message.text.lower():
        await state.set_data({"chan_url": message.text})
        await message.bot.send_message(message.from_user.id, "Введите ID канала\n"
                                                             "Узнать ID можно переслав любой "
                                                             "пост из канала-спонсора в бот @getmyid_bot. "
                                                             "После скопируйте результат из графы 'Forwarded from chat:'",
                                       reply_markup=await cancel_bt())
        await state.set_state(ChangeAdminInfo.get_channel_id)
    else:
        await message.bot.send_message(message.from_user.id, "️️❗Ошибка! Введите корректную ссылку",
                                       reply_markup=await main_menu_bt())
        await state.clear()


@client_bot_router.message(ChangeAdminInfo.get_channel_id)
async def get_new_channel_id(message: Message, state: FSMContext):
    if message.text == "❌Отменить":
        await message.bot.send_message(message.from_user.id, "🚫Действие отменено", reply_markup=await main_menu_bt())
        await state.clear()
    elif message.text:
        try:
            chanel_url = await state.get_data()
            channel_id = int(message.text)
            if channel_id > 0:
                channel_id *= -1
            new_channel = await add_new_channel_db(url=chanel_url["chan_url"], id=channel_id)
            if new_channel:
                await message.bot.send_message(message.from_user.id, f"Подписка добавлена ✅\n"
                                                                     f"❗️Не забудьте добавить бота в этот канал/группу и дать ему админку(права давать не обязательно)❗️",
                                               reply_markup=await main_menu_bt())
                await state.clear()
            else:
                await message.bot.send_message(message.from_user.id, f"Подписка не добавлена.",
                                               reply_markup=await main_menu_bt())
                await state.clear()
        except:
            await message.bot.send_message(message.from_user.id,
                                           "🚫Не удалось добавить подписку. Данная подписка уже существует",
                                           reply_markup=await main_menu_bt())
            await state.clear()
    else:
        await message.bot.send_message(message.from_user.id, "️️❗Ошибка", reply_markup=await main_menu_bt())
        await state.clear()


@client_bot_router.message(ChangeAdminInfo.delete_channel)
async def delete_channel(message: Message, state: FSMContext):
    if message.text == "❌Отменить":
        await message.bot.send_message(message.from_user.id, "🚫Действие отменено", reply_markup=await main_menu_bt())
        await state.clear()
    elif message.text == "1":
        await message.bot.send_message(message.from_user.id, "🚫Нельзя удалить эту подписку",
                                       reply_markup=await main_menu_bt())
        await state.clear()
    elif message.text != "1" and message.text.isdigit():
        try_del = delete_channel_db(int(message.text))
        if try_del:
            await message.bot.send_message(message.from_user.id, f"Подписка успешно удалена ✅",
                                           reply_markup=await main_menu_bt())
            await state.clear()
        else:
            await message.bot.send_message(message.from_user.id, "🚫Не удалось удалить",
                                           reply_markup=await main_menu_bt())
            await state.clear()
    else:
        await message.bot.send_message(message.from_user.id, "️️❗Ошибка", reply_markup=await main_menu_bt())
        await state.clear()


@client_bot_router.message(ChangeAdminInfo.mailing)
async def mailing_admin(message: Message, state: FSMContext):
    if message.text == "❌Отменить":
        await message.bot.send_message(message.from_user.id, "🚫Действие отменено", reply_markup=await main_menu_bt())
        await state.clear()
    else:
        all_users = await get_all_users_tg_id()
        success = 0
        unsuccess = 0
        for i in all_users:
            try:
                await message.bot.copy_message(chat_id=i, from_chat_id=message.from_user.id,
                                               message_id=message.message_id, reply_markup=message.reply_markup)
                success += 1
            except:
                unsuccess += 1
        await message.bot.send_message(message.from_user.id, f"Рассылка завершена!\n"
                                                             f"Успешно отправлено: {success}\n"
                                                             f"Неуспешно: {unsuccess}",
                                       reply_markup=await main_menu_bt())
        await state.clear()


@client_bot_router.message(F.text == "❌Отменить")
async def profile(message: Message, state: FSMContext):
    await message.bot.send_message(message.from_user.id, "️️Все действия отменены", reply_markup=await main_menu_bt())
    await state.clear()

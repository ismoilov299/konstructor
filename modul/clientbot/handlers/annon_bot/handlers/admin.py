import logging
from aiogram import Router, F
from aiogram.filters import Command, BaseFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from modul.clientbot import shortcuts
from modul.clientbot.handlers.annon_bot.adminservice import *
from modul.clientbot.handlers.annon_bot.keyboards.buttons import admin_menu_in, admin_channels_in, cancel_bt, \
    main_menu_bt
from modul.clientbot.handlers.annon_bot.states import AnonBotFilter, ChangeAdminInfo
from modul.clientbot.handlers.kino_bot.keyboards.kb import admin_kb
from modul.loader import client_bot_router
from modul.models import Bot

logger = logging.getLogger(__name__)

async def send_cancel_message(bot, user_id):
    await bot.send_message(user_id, "🚫Действие отменено", reply_markup=await main_menu_bt())


async def send_success_message(bot, user_id, text):
    await bot.send_message(user_id, text, reply_markup=await main_menu_bt())


async def get_admin_id(bot: Bot):
    bot_db = await shortcuts.get_bot(bot)
    return bot_db.owner.uid

class AdminFilter(BaseFilter):
    async def __call__(self, message: Message, bot: Bot) -> bool:
        bot_db = await shortcuts.get_bot(bot)
        admin_id = bot_db.owner.uid
        return message.from_user.id == admin_id

def anon_admin_panel():
    @client_bot_router.message(Command(commands=["admin"]), F.chat.type == "private",AdminFilter())
    async def admin_mm(message: Message):
        try:
            await message.answer('Админ панель', reply_markup=admin_kb)
        except Exception as e:
            logger.error(f"Ошибка при входе в панель админа: {e}")
            await message.answer("❗ Произошла ошибка. Повторите попытку позже.")



@client_bot_router.callback_query(F.data.in_(["cancel", "change_channels", "add_channel", "delete_channel", "mailing"]))
async def call_backs(query: CallbackQuery, state: FSMContext):
    try:
        await state.clear()
        if query.data == "cancel":
            await query.bot.delete_message(chat_id=query.from_user.id, message_id=query.message.message_id)
        elif query.data == "change_channels":
            text = "Обязательные подписки: \n"
            all_channels = await get_channels_for_admin()
            if all_channels:
                for channel in all_channels:
                    text += f"\n<b>ID Подписки:</b> {channel[0]}\n<b>Username:</b> {channel[1]}\n<b>Канал ID:</b> {channel[2]}\n"
            else:
                text += "Подписок не найдено."
            await query.bot.send_message(query.from_user.id, text=text, reply_markup=await admin_channels_in(), parse_mode="html")
        elif query.data == "add_channel":
            await query.bot.send_message(query.from_user.id, "Введите ссылку на канал (формат: t.me/ или https://t.me/)",
                                         reply_markup=await cancel_bt())
            await state.set_state(ChangeAdminInfo.get_channel_url)
        elif query.data == "delete_channel":
            await query.bot.send_message(query.from_user.id, "Введите ID подписки для удаления",
                                         reply_markup=await cancel_bt(), parse_mode="html")
            await state.set_state(ChangeAdminInfo.delete_channel)
        elif query.data == "mailing":
            await query.bot.send_message(query.from_user.id,
                                         "Введите сообщение для рассылки или отправьте фото/видео с описанием.",
                                         reply_markup=await cancel_bt())
            await state.set_state(ChangeAdminInfo.mailing)
    except Exception as e:
        logger.error(f"Ошибка обработки callback запроса: {query.data}, {e}")


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
    try:
        channel_id = int(message.text)
        if channel_id > 0:
            channel_id *= -1
        data = await state.get_data()
        new_channel = await add_new_channel_db(url=data["chan_url"], id=channel_id)
        if new_channel:
            await send_success_message(message.bot, message.from_user.id, "Канал успешно добавлен ✅")
        else:
            await send_success_message(message.bot, message.from_user.id, "Канал не был добавлен.")
    except ValueError:
        await send_success_message(message.bot, message.from_user.id, "❗Ошибка! Укажите числовой ID канала.")
    except Exception as e:
        logger.error(f"Ошибка добавления канала: {e}")
        await send_success_message(message.bot, message.from_user.id, "🚫Ошибка добавления канала.")
    finally:
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

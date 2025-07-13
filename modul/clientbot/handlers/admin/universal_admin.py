# modul/clientbot/handlers/admin/universal_admin.py

from aiogram import Router, F, Bot
from aiogram.filters import Command, StateFilter, BaseFilter
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest
from aiogram.types import BufferedInputFile
from aiogram.methods import GetChat, GetChatMember, CreateChatInviteLink

from asgiref.sync import sync_to_async
from django.db import transaction
from enum import Enum
from typing import Optional, List, Union
from pydantic import BaseModel

from modul.models import ClientBotUser, Bot as BotModel, Withdrawals, AdminInfo, Channels, UserTG
from modul.loader import client_bot_router
from modul.clientbot import shortcuts
from modul.clientbot.handlers.refs.data.states import ChangeAdminInfo
import logging
import traceback

logger = logging.getLogger(__name__)

# States - import qilaylik mavjud fayllardan
try:
    from modul.clientbot.handlers.kino_bot.handlers.bot import SendMessagesForm, AddChannelSponsorForm
except ImportError:
    # Agar import bo'lmasa, o'zimiz yaratamiz
    from aiogram.fsm.state import State, StatesGroup


    class SendMessagesForm(StatesGroup):
        message = State()


    class AddChannelSponsorForm(StatesGroup):
        channel = State()


# Reaction types for Telegram API
class ReactionTypeType(str, Enum):
    EMOJI = "emoji"
    CUSTOM_EMOJI = "custom_emoji"
    PAID = "paid"


class ReactionTypeBase(BaseModel):
    type: ReactionTypeType


class ReactionTypeEmoji(ReactionTypeBase):
    type: ReactionTypeType = ReactionTypeType.EMOJI
    emoji: str


class ReactionTypeCustomEmoji(ReactionTypeBase):
    type: ReactionTypeType = ReactionTypeType.CUSTOM_EMOJI
    custom_emoji_id: str


class ReactionTypePaid(ReactionTypeBase):
    type: ReactionTypeType = ReactionTypeType.PAID


ReactionType = Union[ReactionTypeEmoji, ReactionTypeCustomEmoji, ReactionTypePaid]


class ChatInfo(BaseModel):
    id: int
    title: str
    type: str
    description: Optional[str] = None
    invite_link: Optional[str] = None
    has_visible_history: Optional[bool] = None
    can_send_paid_media: Optional[bool] = None
    available_reactions: Optional[List[ReactionType]] = None
    max_reaction_count: Optional[int] = None
    accent_color_id: Optional[int] = None


# Admin Filter
class AdminFilter(BaseFilter):
    async def __call__(self, message: Message, bot: Bot) -> bool:
        bot_db = await shortcuts.get_bot(bot)
        admin_id = bot_db.owner.uid
        return message.from_user.id == admin_id


# Helper functions
@sync_to_async
def get_users_count(bot_token=None):
    """Bot foydalanuvchilar sonini olish"""
    try:
        if bot_token:
            bot = BotModel.objects.get(token=bot_token)
            count = ClientBotUser.objects.filter(bot=bot).count()
        else:
            count = ClientBotUser.objects.all().count()
        return count
    except BotModel.DoesNotExist:
        logger.error(f"Bot with token {bot_token} not found")
        return 0
    except Exception as e:
        logger.error(f"Get users count error: {e}")
        return 0


@sync_to_async
def get_all_users(bot_db):
    """Bot foydalanuvchilari ro'yxati"""
    users = ClientBotUser.objects.filter(
        bot=bot_db,
        uid__gt=0,
        user__banned=False
    ).values_list('uid', flat=True)
    return list(users)


@sync_to_async
def get_pending_payments():
    """Kutilayotgan to'lovlar"""
    payments = Withdrawals.objects.filter(status="ожидание")
    return [[w.id, w.tg_id.uid, w.amount, w.card, w.bank] for w in payments]


@sync_to_async
def get_user_info_db(user_id):
    """Foydalanuvchi ma'lumotlari"""
    user = UserTG.objects.filter(uid=user_id).first()
    if user:
        return [user.first_name, user.uid, user.balance, user.invited, user.refs, user.paid]
    return None


@sync_to_async
def check_ban(user_id):
    """Foydalanuvchi ban holatini tekshirish"""
    user = UserTG.objects.filter(uid=user_id).first()
    return user.banned if user else False


@sync_to_async
def ban_unban_db(id, bool_value):
    """Foydalanuvchini ban/unban qilish"""
    UserTG.objects.filter(uid=id).update(banned=bool_value)


@sync_to_async
def addbalance_db(user_id, amount):
    """Balansga qo'shish"""
    user = UserTG.objects.filter(uid=user_id).first()
    if user:
        user.balance += amount
        user.save()


@sync_to_async
def changebalance_db(user_id, new_balance):
    """Balansni o'zgartirish"""
    UserTG.objects.filter(uid=user_id).update(balance=new_balance)


@sync_to_async
def status_accepted(payment_id):
    """To'lovni tasdiqlash"""
    try:
        payment = Withdrawals.objects.get(id=payment_id)
        payment.status = "принята"
        payment.save()
        return [payment.tg_id.uid, payment.amount]
    except:
        return None


@sync_to_async
def status_declined(payment_id):
    """To'lovni rad etish"""
    try:
        payment = Withdrawals.objects.get(id=payment_id)
        user = payment.tg_id
        user.balance += payment.amount  # Balansni qaytarish
        user.save()
        payment.status = "отклонена"
        payment.save()
        return [payment.tg_id.uid, payment.amount]
    except:
        return None


@sync_to_async
def change_price(new_price, bot_token):
    """Referral narxini o'zgartirish"""
    try:
        admin_info, created = AdminInfo.objects.get_or_create(
            bot_token=bot_token,
            defaults={'price': new_price, 'min_amount': 30.0}
        )
        if not created:
            admin_info.price = new_price
            admin_info.save()
        return True
    except Exception as e:
        logger.error(f"Error changing price: {e}")
        return False


@sync_to_async
def change_min_amount(new_min):
    """Minimal to'lov miqdorini o'zgartirish"""
    admin_info = AdminInfo.objects.first()
    if admin_info:
        admin_info.min_amount = new_min
        admin_info.save()


@sync_to_async
def get_all_channels_sponsors():
    """Sponsor kanallar ro'yxati"""
    from modul.models import ChannelSponsor
    return list(ChannelSponsor.objects.all())


@sync_to_async
def create_channel_sponsor(channel_id):
    """Sponsor kanal qo'shish"""
    from modul.models import ChannelSponsor
    ChannelSponsor.objects.get_or_create(chanel_id=channel_id)


@sync_to_async
def remove_channel_sponsor(channel_id):
    """Sponsor kanalni o'chirish"""
    from modul.models import ChannelSponsor
    ChannelSponsor.objects.filter(id=channel_id).delete()


async def convert_to_excel(user_id, bot_token):
    """Excel fayl yaratish"""
    # Bu funktsiyani sizning loyihangizga mos qilib yozing
    import io
    import openpyxl

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Referrals"

    # Headers
    ws.append(["Username", "User ID", "Balance", "Refs", "Invited", "Paid"])

    # Ma'lumotlarni olish
    refs = await get_all_refs_db(user_id)
    for ref in refs:
        ws.append(ref)

    # Faylni bytes formatiga o'tkazish
    file_stream = io.BytesIO()
    wb.save(file_stream)
    file_stream.seek(0)

    return file_stream.getvalue(), f"referrals_{user_id}.xlsx"


@sync_to_async
def get_all_refs_db(user_id):
    """Referrallar ro'yxati"""
    users = UserTG.objects.filter(invited_id=user_id)
    return [[user.username, user.uid, user.balance, user.refs, user.invited, user.paid] for user in users]


# Keyboard functions (qo'shing yoki mavjud keyboard fayllaridan import qiling)
async def admin_kb():
    """Admin panel keyboard"""
    builder = InlineKeyboardBuilder()
    builder.button(text="👥 Управление пользователями", callback_data="admin_users")
    builder.button(text="💰 Заявки на вывод", callback_data="admin_payments")
    builder.button(text="⚙️ Настройки бота", callback_data="admin_settings")
    builder.button(text="📢 Обязательные подписки", callback_data="admin_channels")
    builder.button(text="📤 Рассылка", callback_data="admin_mailing")
    builder.button(text="📊 Статистика", callback_data="admin_statistics")
    builder.button(text="❌ Закрыть", callback_data="admin_cancel")
    builder.adjust(1)
    return builder.as_markup()


async def cancel_kb():
    """Cancel keyboard"""
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Отменить", callback_data="cancel")
    return builder.as_markup()


async def imp_menu_in(user_id, is_banned):
    """User management keyboard"""
    builder = InlineKeyboardBuilder()
    builder.button(text="💳 Изменить баланс", callback_data=f"changebalance_{user_id}")
    builder.button(text="➕ Добавить к балансу", callback_data=f"addbalance_{user_id}")
    builder.button(text="👥 Изменить рефералы", callback_data=f"changerefs_{user_id}")
    builder.button(text="📊 Показать рефералы", callback_data=f"showrefs_{user_id}")

    if is_banned:
        builder.button(text="✅ Разбанить", callback_data=f"razb_{user_id}")
    else:
        builder.button(text="🚫 Забанить", callback_data=f"ban_{user_id}")

    builder.button(text="🔙 Назад", callback_data="admin_panel")
    builder.adjust(1)
    return builder.as_markup()


async def payments_action_in(payment_id):
    """Payment action keyboard"""
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Принять", callback_data=f"accept_{payment_id}")
    builder.button(text="❌ Отклонить", callback_data=f"decline_{payment_id}")
    return builder.as_markup()


async def accepted_in():
    """Accepted payment keyboard"""
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Принято", callback_data="accepted")
    return builder.as_markup()


async def declined_in():
    """Declined payment keyboard"""
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Отклонено", callback_data="declined")
    return builder.as_markup()


async def main_menu_bt():
    """Main menu keyboard"""
    builder = InlineKeyboardBuilder()
    builder.button(text="🏠 Главное меню", callback_data="main_menu")
    return builder.as_markup()


async def get_remove_channel_sponsor_kb(channels, bot):
    """Remove channel keyboard"""
    builder = InlineKeyboardBuilder()
    for channel in channels:
        builder.button(text=f"🗑 {channel.chanel_id}", callback_data=f"remove_channel|{channel.id}")
    builder.button(text="🔙 Назад", callback_data="admin_panel")
    builder.adjust(1)
    return builder.as_markup()


async def start(message, state, bot):
    """Start function"""
    await message.answer("Добро пожаловать!", reply_markup=await main_menu_bt())


# Send message to users function
async def send_message_to_users(bot, users, text):
    for user_id in users:
        try:
            await bot.send_message(chat_id=user_id, text=text)
        except TelegramAPIError as e:
            logger.warning(f"Не удалось отправить сообщение пользователю {user_id}: {e}")


def admin_panel():
    """Admin panel router setup"""

    # Debug uchun
    print("Setting up admin panel handlers...")

    # Main admin command
    @client_bot_router.message(Command('admin'), AdminFilter())
    async def admin_menu(message: Message):
        print(f"Admin command received from user {message.from_user.id}")
        try:
            bot_token = message.bot.token
            count = await get_users_count(bot_token)

            await message.answer(
                f"🕵 Панель админа\nКоличество юзеров в боте: {count}",
                reply_markup=await admin_kb()
            )
            print(f"Admin menu sent to user {message.from_user.id}")
        except Exception as e:
            logger.error(f"Admin menu error: {e}")
            await message.answer("❗ Произошла ошибка при открытии админ панели.")

    # Debug handler - har qanday callback'ni ushlash
    @client_bot_router.callback_query()
    async def debug_callback_handler(callback: CallbackQuery):
        print(f"Callback received: {callback.data} from user {callback.from_user.id}")

        # Agar admin callback bo'lsa
        if callback.data.startswith("admin_"):
            await handle_admin_callbacks(callback)
        else:
            # Boshqa handler'larga o'tkazish
            return False

    @client_bot_router.callback_query(AdminFilter(), StateFilter('*'))
    async def handle_admin_callbacks(callback: CallbackQuery):
        """Admin callback'larni boshqarish"""
        print(f"Handling admin callback: {callback.data} from user {callback.from_user.id}")
        try:
            data = callback.data
            print(f"Handling admin callback: {data}")

            if data == "admin_users":
                await admin_users_handler(callback)
            elif data == "admin_payments":
                await admin_payments_handler(callback)
            elif data == "admin_settings":
                await admin_settings_handler(callback)
            elif data == "admin_channels":
                await admin_channels_handler(callback)
            elif data == "admin_mailing":
                await admin_mailing_handler(callback)
            elif data == "admin_statistics":
                await admin_statistics_handler(callback)
            elif data == "admin_panel":
                await back_to_admin_panel(callback)
            elif data == "admin_cancel":
                await admin_cancel_handler(callback)
            else:
                await callback.answer("Неизвестная команда")

        except Exception as e:
            logger.error(f"Error handling admin callback {callback.data}: {e}")
            await callback.answer("Произошла ошибка")


# Admin callback handlers
async def admin_users_handler(callback: CallbackQuery):
    try:
        bot_token = callback.bot.token
        users_count = await get_users_count(bot_token)

        text = f"👥 Управление пользователями\n\n"
        text += f"📊 Общее количество: {users_count}\n\n"
        text += "Выберите действие:"

        builder = InlineKeyboardBuilder()
        builder.button(text="🔍 Найти пользователя", callback_data="imp")
        builder.button(text="📊 Статистика", callback_data="admin_get_stats")
        builder.button(text="🔙 Назад", callback_data="admin_panel")
        builder.adjust(1)

        await callback.message.edit_text(text, reply_markup=builder.as_markup())
        await callback.answer()
    except Exception as e:
        logger.error(f"Admin users error: {e}")
        await callback.answer("Ошибка при загрузке управления пользователями")


async def admin_payments_handler(callback: CallbackQuery):
    try:
        text = f"💰 Управление выплатами\n\nВыберите действие:"

        builder = InlineKeyboardBuilder()
        builder.button(text="📋 Все заявки", callback_data="all_payments")
        builder.button(text="🔙 Назад", callback_data="admin_panel")
        builder.adjust(1)

        await callback.message.edit_text(text, reply_markup=builder.as_markup())
        await callback.answer()
    except Exception as e:
        logger.error(f"Admin payments error: {e}")
        await callback.answer("Ошибка при загрузке управления выплатами")


async def admin_settings_handler(callback: CallbackQuery):
    try:
        text = f"⚙️ Настройки бота\n\nВыберите параметр:"

        builder = InlineKeyboardBuilder()
        builder.button(text="💰 Изменить награду за реферала", callback_data="change_money")
        builder.button(text="💸 Изменить мин. выплату", callback_data="change_min")
        builder.button(text="🔙 Назад", callback_data="admin_panel")
        builder.adjust(1)

        await callback.message.edit_text(text, reply_markup=builder.as_markup())
        await callback.answer()
    except Exception as e:
        logger.error(f"Admin settings error: {e}")
        await callback.answer("Ошибка при загрузке настроек")


async def admin_channels_handler(callback: CallbackQuery):
    try:
        text = f"📢 Управление каналами\n\nВыберите действие:"

        builder = InlineKeyboardBuilder()
        builder.button(text="➕ Добавить канал", callback_data="admin_add_channel")
        builder.button(text="🗑 Удалить канал", callback_data="admin_delete_channel")
        builder.button(text="🔙 Назад", callback_data="admin_panel")
        builder.adjust(1)

        await callback.message.edit_text(text, reply_markup=builder.as_markup())
        await callback.answer()
    except Exception as e:
        logger.error(f"Admin channels error: {e}")
        await callback.answer("Ошибка при загрузке управления каналами")


async def admin_mailing_handler(callback: CallbackQuery):
    try:
        text = f"📤 Рассылка сообщений\n\nВыберите действие:"

        builder = InlineKeyboardBuilder()
        builder.button(text="📝 Отправить сообщение", callback_data="admin_send_message")
        builder.button(text="🔙 Назад", callback_data="admin_panel")
        builder.adjust(1)

        await callback.message.edit_text(text, reply_markup=builder.as_markup())
        await callback.answer()
    except Exception as e:
        logger.error(f"Admin mailing error: {e}")
        await callback.answer("Ошибка при загрузке рассылки")


async def admin_statistics_handler(callback: CallbackQuery):
    try:
        bot_token = callback.bot.token
        users_count = await get_users_count(bot_token)

        text = f"📊 Статистика бота\n\n"
        text += f"👥 Пользователей: {users_count}\n"

        builder = InlineKeyboardBuilder()
        builder.button(text="🔄 Обновить", callback_data="admin_get_stats")
        builder.button(text="🔙 Назад", callback_data="admin_panel")
        builder.adjust(1)

        await callback.message.edit_text(text, reply_markup=builder.as_markup())
        await callback.answer()
    except Exception as e:
        logger.error(f"Admin statistics error: {e}")
        await callback.answer("Ошибка при загрузке статистики")


async def back_to_admin_panel(callback: CallbackQuery):
    try:
        bot_token = callback.bot.token
        count = await get_users_count(bot_token)

        await callback.message.edit_text(
            f"🕵 Панель админа\nКоличество юзеров в боте: {count}",
            reply_markup=await admin_kb()
        )
        await callback.answer()
    except Exception as e:
        logger.error(f"Back to admin panel error: {e}")
        await callback.answer("Ошибка при возврате к админ панели")


async def admin_cancel_handler(callback: CallbackQuery):
    try:
        await callback.message.delete()
        await callback.answer("Панель админа закрыта")
    except Exception as e:
        await callback.answer("Панель закрыта")

    # ALL EXISTING HANDLERS FROM YOUR CODE:

    # Send message to all users
    @client_bot_router.callback_query(F.data == 'admin_send_message', AdminFilter(), StateFilter('*'))
    async def admin_send_message(call: CallbackQuery, state: FSMContext):
        await state.set_state(SendMessagesForm.message)
        await call.message.edit_text('Отправьте сообщение для рассылки (текст, фото, видео и т.д.)',
                                     reply_markup=await cancel_kb())

    @client_bot_router.message(SendMessagesForm.message)
    async def admin_send_message_msg(message: Message, state: FSMContext):
        await state.clear()
        bot_db = await shortcuts.get_bot(message.bot)
        users = await get_all_users(bot_db)

        if not users:
            await message.answer("Нет пользователей для рассылки.")
            return

        success_count = 0
        fail_count = 0

        for user_id in users:
            try:
                if message.text:
                    await message.bot.send_message(chat_id=user_id, text=message.text)
                elif message.photo:
                    await message.bot.send_photo(chat_id=user_id, photo=message.photo[-1].file_id,
                                                 caption=message.caption)
                elif message.video:
                    await message.bot.send_video(chat_id=user_id, video=message.video.file_id, caption=message.caption)
                elif message.audio:
                    await message.bot.send_audio(chat_id=user_id, audio=message.audio.file_id, caption=message.caption)
                elif message.document:
                    await message.bot.send_document(chat_id=user_id, document=message.document.file_id,
                                                    caption=message.caption)
                else:
                    await message.bot.copy_message(chat_id=user_id, from_chat_id=message.chat.id,
                                                   message_id=message.message_id)

                success_count += 1
            except Exception as e:
                fail_count += 1
                logger.error(f"Ошибка при отправке сообщения пользователю {user_id}: {e}")

        await message.answer(
            f'Рассылка завершена!\n'
            f'Успешно отправлено: {success_count}\n'
            f'Не удалось отправить: {fail_count}'
        )

    # User management handlers
    @client_bot_router.callback_query(F.data == "imp", AdminFilter(), StateFilter('*'))
    async def manage_user_handler(call: CallbackQuery, state: FSMContext):
        await call.message.edit_text("Введите ID пользователя", reply_markup=await cancel_kb())
        await state.set_state(ChangeAdminInfo.imp)

    @client_bot_router.message(ChangeAdminInfo.imp)
    async def get_user_info_handler(message: Message, state: FSMContext):
        if message.text == "❌Отменить":
            await message.answer("🚫 Действие отменено", reply_markup=await main_menu_bt())
            await state.clear()
            return

        if message.text.isdigit():
            user_id = int(message.text)
            try:
                status = await check_ban(user_id)
                user_info = await get_user_info_db(user_id)
                if user_info:
                    user_name = "@"
                    try:
                        chat = await message.bot.get_chat(user_info[1])
                        user_name += f"{chat.username}"
                    except:
                        pass
                    await message.answer(
                        f"📝Имя юзера: {user_info[0]} {user_name}\n"
                        f"🆔ID юзера: <code>{user_info[1]}</code>\n"
                        f"👥 Пригласил: {user_info[3]}\n"
                        f"💳 Баланс юзера: {user_info[2]} руб.\n"
                        f"📤 Вывел: {user_info[5]} руб.",
                        parse_mode="html",
                        reply_markup=await imp_menu_in(user_info[1], status)
                    )
                    await state.clear()
                else:
                    await message.answer("Юзер не найден", reply_markup=await main_menu_bt())
                    await state.clear()
            except Exception as e:
                await message.answer(f"🚫 Не удалось найти юзера. Ошибка: {e}", reply_markup=await main_menu_bt())
                await state.clear()
        else:
            await message.answer("️️❗Ошибка! Введите числовой ID пользователя.", reply_markup=await main_menu_bt())
            await state.clear()

    # Payment handlers
    @client_bot_router.callback_query(lambda call: "accept_" in call.data, AdminFilter(), StateFilter('*'))
    async def acception(query: CallbackQuery):
        id_of_wa = int(query.data.replace("accept_", ""))
        user_info = await status_accepted(id_of_wa)

        if user_info:
            await query.message.edit_reply_markup(reply_markup=await accepted_in())
            await query.bot.send_message(
                user_info[0],
                f"Ваша завявка на выплату {user_info[1]} была подтверждена ✅"
            )
        else:
            await query.answer("Ошибка: Не удалось подтвердить заявку", show_alert=True)

    @client_bot_router.callback_query(lambda call: "decline_" in call.data, AdminFilter(), StateFilter('*'))
    async def declined(query: CallbackQuery):
        id_of_wa = int(query.data.replace("decline_", ""))
        user_info = await status_declined(id_of_wa)

        if user_info:
            await query.message.edit_reply_markup(reply_markup=await declined_in())
            await query.bot.send_message(
                user_info[0],
                f"Ваша завявка на выплату {user_info[1]} была отклонена❌"
            )
        else:
            await query.answer("Ошибка: Не удалось отклонить заявку", show_alert=True)

    @client_bot_router.callback_query(F.data == 'all_payments', AdminFilter(), StateFilter('*'))
    async def all_payments_handler(call: CallbackQuery):
        active_payments = await get_pending_payments()

        if active_payments:
            for payment in active_payments:
                await call.message.answer(
                    text=f"<b>Заявка на выплату № {payment[0]}</b>\n"
                         f"ID пользователя: <code>{payment[1]}</code>\n"
                         f"Сумма: {payment[2]} руб.\n"
                         f"Карта: <code>{payment[3]}</code>\n"
                         f"Банк: {payment[4]}",
                    parse_mode="HTML",
                    reply_markup=await payments_action_in(payment[0])
                )
        else:
            await call.message.edit_text('Нет заявок на выплату.', reply_markup=await admin_kb())

    # Balance management
    @client_bot_router.callback_query(F.data.startswith("addbalance_"), AdminFilter(), StateFilter('*'))
    async def add_balance_handler(call: CallbackQuery, state: FSMContext):
        user_id = int(call.data.replace("addbalance_", ""))
        await call.message.edit_text(
            "Введите сумму для добавления к балансу. Для дробных чисел используйте точку.",
            reply_markup=await cancel_kb()
        )
        await state.set_state(ChangeAdminInfo.add_balance)
        await state.update_data(user_id=user_id)

    @client_bot_router.message(ChangeAdminInfo.add_balance)
    async def process_add_balance(message: Message, state: FSMContext):
        if message.text == "❌Отменить":
            await message.answer("🚫 Действие отменено", reply_markup=await main_menu_bt())
            await state.clear()
            return

        try:
            amount = float(message.text)
            data = await state.get_data()
            await addbalance_db(data["user_id"], amount)
            await message.answer(f"Баланс успешно пополнен на {amount} руб.", reply_markup=await main_menu_bt())
            await state.clear()
        except ValueError:
            await message.answer("❗ Введите корректное числовое значение.")
        except Exception as e:
            await message.answer(f"🚫 Не удалось изменить баланс. Ошибка: {e}", reply_markup=await main_menu_bt())
            await state.clear()

    @client_bot_router.callback_query(F.data.startswith("changebalance_"), AdminFilter(), StateFilter('*'))
    async def change_balance_handler(call: CallbackQuery, state: FSMContext):
        user_id = int(call.data.replace("changebalance_", ""))
        await call.message.edit_text(
            "Введите новую сумму баланса. Для дробных чисел используйте точку.",
            reply_markup=await cancel_kb()
        )
        await state.set_state(ChangeAdminInfo.change_balance)
        await state.update_data(user_id=user_id)

    @client_bot_router.message(ChangeAdminInfo.change_balance)
    async def process_change_balance(message: Message, state: FSMContext):
        if message.text == "❌Отменить":
            await message.answer("🚫 Действие отменено", reply_markup=await main_menu_bt())
            await state.clear()
            return

        try:
            new_balance = float(message.text)
            data = await state.get_data()
            await changebalance_db(data["user_id"], new_balance)
            await message.answer(f"Баланс успешно изменен на {new_balance} руб.", reply_markup=await main_menu_bt())
            await state.clear()
        except ValueError:
            await message.answer("❗ Введите корректное числовое значение.")
        except Exception as e:
            await message.answer(f"🚫 Не удалось изменить баланс. Ошибка: {e}", reply_markup=await main_menu_bt())
            await state.clear()

    # Referrals management
    @client_bot_router.callback_query(F.data.startswith("changerefs_"), AdminFilter(), StateFilter('*'))
    async def change_refs_handler(call: CallbackQuery, state: FSMContext):
        user_id = int(call.data.replace("changerefs_", ""))
        await call.message.edit_text(
            "Введите новое количество рефералов:",
            reply_markup=await cancel_kb()
        )
        await state.set_state(ChangeAdminInfo.change_refs)
        await state.update_data(user_id=user_id)

    @client_bot_router.message(ChangeAdminInfo.change_refs)
    async def set_new_refs_count(message: Message, state: FSMContext):
        data = await state.get_data()
        user_id = data.get("user_id")

        if message.text == "❌Отменить":
            await message.answer("🚫 Действие отменено", reply_markup=await main_menu_bt())
            await state.clear()
            return

        if message.text.isdigit():
            new_refs_count = int(message.text)

            try:
                @sync_to_async
                @transaction.atomic
                def update_refs():
                    user = UserTG.objects.select_for_update().filter(uid=user_id).first()
                    if user:
                        user.refs = new_refs_count
                        user.save()
                        return True
                    return False

                updated = await update_refs()

                if updated:
                    await message.answer(
                        f"Количество рефералов для пользователя {user_id} успешно обновлено на {new_refs_count}.",
                        reply_markup=await main_menu_bt())
                else:
                    await message.answer(f"🚫 Пользователь с ID {user_id} не найден.", reply_markup=await main_menu_bt())

            except Exception as e:
                logger.error(f"Error updating refs count for user {user_id}: {e}")
                await message.answer("🚫 Не удалось обновить количество рефералов.", reply_markup=await main_menu_bt())
        else:
            await message.answer("❗ Введите корректное числовое значение.")

        await state.clear()

    # Show referrals
    @client_bot_router.callback_query(F.data.startswith("showrefs_"), AdminFilter(), StateFilter('*'))
    async def show_refs_handler(call: CallbackQuery):
        user_id = int(call.data.replace("showrefs_", ""))
        try:
            file_data, filename = await convert_to_excel(user_id, call.bot.token)
            document = BufferedInputFile(file_data, filename=filename)
            await call.message.answer_document(document)
        except Exception as e:
            await call.message.answer(f"🚫 Произошла ошибка при создании файла: {e}")

    # Ban/Unban users
    @client_bot_router.callback_query(F.data.startswith("ban_"), AdminFilter(), StateFilter('*'))
    async def ban_user_handler(call: CallbackQuery):
        user_id = int(call.data.replace("ban_", ""))
        await ban_unban_db(user_id, True)
        await call.message.edit_reply_markup(reply_markup=await imp_menu_in(user_id, True))

    @client_bot_router.callback_query(F.data.startswith("razb_"), AdminFilter(), StateFilter('*'))
    async def unban_user_handler(call: CallbackQuery):
        user_id = int(call.data.replace("razb_", ""))
        await ban_unban_db(user_id, False)
        await call.message.edit_reply_markup(reply_markup=await imp_menu_in(user_id, False))

    # Settings handlers
    @client_bot_router.callback_query(F.data == 'change_money', AdminFilter(), StateFilter('*'))
    async def change_money_handler(call: CallbackQuery, state: FSMContext):
        await state.set_state(ChangeAdminInfo.get_amount)
        await call.message.edit_text(
            'Введите новую награду за рефералов:',
            reply_markup=await cancel_kb()
        )

    @client_bot_router.message(ChangeAdminInfo.get_amount)
    async def get_new_amount_handler(message: Message, state: FSMContext):
        if message.text == "❌Отменить":
            await message.answer("🚫 Действие отменено", reply_markup=await main_menu_bt())
            await state.clear()
            return

        try:
            new_reward = float(message.text)
            success = await change_price(new_reward, message.bot.token)

            if success:
                await message.answer(
                    f"Награда за реферала успешно изменена на {new_reward:.2f} руб.",
                    reply_markup=await main_menu_bt()
                )
            else:
                await message.answer(
                    "🚫 Не удалось изменить награду за реферала.",
                    reply_markup=await main_menu_bt()
                )
            await state.clear()

        except ValueError:
            await message.answer("❗ Введите корректное числовое значение.")
        except Exception as e:
            logger.error(f"Ошибка при обновлении награды за реферала: {e}")
            await message.answer("🚫 Не удалось изменить награду за реферала.", reply_markup=await main_menu_bt())
            await state.clear()

    @client_bot_router.callback_query(F.data == "change_min", AdminFilter(), StateFilter('*'))
    async def change_min_handler(call: CallbackQuery, state: FSMContext):
        edited_message = await call.message.edit_text(
            "Введите новую минимальную выплату:",
            reply_markup=await cancel_kb()
        )
        await state.set_state(ChangeAdminInfo.get_min)
        await state.update_data(edit_msg=edited_message)

    @client_bot_router.message(ChangeAdminInfo.get_min)
    async def get_new_min_handler(message: Message, state: FSMContext, bot: Bot):
        data = await state.get_data()
        edit_msg = data.get('edit_msg')

        if message.text == "❌Отменить":
            await message.delete()
            if edit_msg:
                await edit_msg.delete()
            await state.clear()
            await start(message, state, bot)
            return

        try:
            new_min_payout = float(message.text)
            await change_min_amount(new_min_payout)

            await message.delete()
            if edit_msg:
                await edit_msg.delete()

            await message.answer(
                f"Минимальная выплата успешно изменена на {new_min_payout:.1f} руб."
            )
            await state.clear()
            await start(message, state, bot)

        except ValueError:
            await message.answer("❗ Введите корректное числовое значение.")
        except Exception as e:
            logger.error(f"Ошибка при обновлении минимальной выплаты: {e}")
            await message.answer("🚫 Не удалось изменить минимальную выплату.")
            await state.clear()
            await start(message, state, bot)

    # Statistics handler
    @client_bot_router.callback_query(F.data == 'admin_get_stats', AdminFilter(), StateFilter('*'))
    async def admin_get_stats(call: CallbackQuery):
        try:
            bot_token = call.bot.token
            bot_db = await shortcuts.get_bot_by_token(bot_token)

            if bot_db:
                @sync_to_async
                def count_bot_users(bot_id):
                    try:
                        return ClientBotUser.objects.filter(bot=bot_db).count()
                    except Exception as e:
                        logger.error(f"Error counting bot users: {e}")
                        return 0

                total_users = await count_bot_users(bot_db.id)
                new_text = f'<b>Количество пользователей в боте:</b> {total_users}'

                try:
                    await call.message.edit_text(
                        text=new_text,
                        reply_markup=await admin_kb(),
                        parse_mode='HTML'
                    )
                except TelegramBadRequest as e:
                    if "message is not modified" in str(e):
                        await call.answer("Статистика актуальна")
                    else:
                        raise
            else:
                logger.error(f"Bot not found in database for token: {bot_token}")
                await call.answer("Бот не найден в базе данных")

        except Exception as e:
            logger.error(f"Ошибка получения статистики: {e}")
            await call.answer("Ошибка при получении статистики")

    # Channel management
    @client_bot_router.callback_query(F.data == 'admin_add_channel', AdminFilter(), StateFilter('*'))
    async def admin_add_channel(call: CallbackQuery, state: FSMContext):
        await state.set_state(AddChannelSponsorForm.channel)
        await call.message.edit_text('Отправьте id канала\n\n'
                                     'Убедитесь в том, что бот является администратором в канале\n\n'
                                     '@username_to_id_bot id канала можно получить у этого бота',
                                     reply_markup=await cancel_kb())

    @client_bot_router.message(AddChannelSponsorForm.channel)
    async def admin_add_channel_msg(message: Message, state: FSMContext):
        try:
            channel_id = int(message.text)
            bot = message.bot

            # Получаем информацию о канале
            chat_data = await bot(GetChat(chat_id=channel_id, flags={"raw": True}))
            chat_info = await bot(GetChat(chat_id=channel_id))

            # Проверяем, что это канал
            if chat_info.type != "channel":
                await message.answer(
                    "Указанный ID не является каналом. Пожалуйста, введите ID канала.",
                    reply_markup=await cancel_kb()
                )
                return

            # Проверяем права бота
            bot_member = await bot(GetChatMember(chat_id=channel_id, user_id=bot.id))
            if bot_member.status not in ["administrator", "creator"]:
                await message.answer(
                    "Бот не является администратором канала. Пожалуйста, добавьте бота в администраторы канала.",
                    reply_markup=await cancel_kb()
                )
                return

            # Получаем invite link
            invite_link = chat_info.invite_link
            if not invite_link:
                link_data = await bot(CreateChatInviteLink(chat_id=channel_id))
                invite_link = link_data.invite_link

            # Добавляем канал в базу
            await create_channel_sponsor(channel_id)
            await state.clear()

            # Формируем ответ
            channel_info = [
                "✅ Канал успешно добавлен!",
                f"📣 Название: {chat_info.title}",
                f"🆔 ID: {channel_id}",
                f"🔗 Ссылка: {invite_link}"
            ]

            # Добавляем информацию о реакциях если доступно
            if chat_info.available_reactions:
                try:
                    reactions = chat_info.available_reactions
                    if reactions:
                        reaction_types = [
                            r.get("type", "unknown") for r in reactions
                        ]
                        channel_info.append(
                            f"💫 Доступные реакции: {', '.join(reaction_types)}"
                        )
                except Exception as e:
                    logger.warning(f"Failed to process reactions: {e}")

            await message.answer(
                "\n\n".join(channel_info),
                disable_web_page_preview=True
            )

        except ValueError:
            await message.answer(
                "Неверный формат. Пожалуйста, введите числовой ID канала.",
                reply_markup=await cancel_kb()
            )
        except TelegramBadRequest as e:
            logger.error(f"Telegram API error: {e}")
            await message.answer(
                "Бот не смог найти канал. Пожалуйста, проверьте ID канала.",
                reply_markup=await cancel_kb()
            )
        except Exception as e:
            logger.error(f"Channel add error: channel_id={channel_id}, error={str(e)}")
            await message.answer(
                "Произошла ошибка. Пожалуйста, попробуйте еще раз.",
                reply_markup=await cancel_kb()
            )

    @client_bot_router.callback_query(F.data == 'admin_delete_channel', AdminFilter(), StateFilter('*'))
    async def admin_delete_channel(call: CallbackQuery, bot: Bot):
        channels = await get_all_channels_sponsors()
        kb = await get_remove_channel_sponsor_kb(channels, bot)
        await call.message.edit_text('Выберите канал для удаления', reply_markup=kb)

    @client_bot_router.callback_query(F.data.contains('remove_channel'), AdminFilter(), StateFilter('*'))
    async def remove_channel(call: CallbackQuery, bot: Bot):
        channel_id = int(call.data.split('|')[-1])
        try:
            await remove_channel_sponsor(channel_id)
            await call.message.edit_text('Канал был удален!', reply_markup=await admin_kb())
            logger.info(f"Kanal muvaffaqiyatli o'chirildi: {channel_id}")
        except Exception as e:
            logger.error(f"Kanalni o'chirishda xatolik: {e}")
            await call.message.answer("Произошла ошибка при удалении канала.")

    # Cancel handler
    @client_bot_router.callback_query(F.data == 'cancel', StateFilter('*'))
    async def cancel(call: CallbackQuery, state: FSMContext):
        await state.clear()
        await call.message.edit_text('Отменено')

    # Back to main menu
    @client_bot_router.message(F.text == "🔙Назад в меню")
    async def back_to_main_menu(message: Message, state: FSMContext, bot: Bot):
        await start(message, state, bot)
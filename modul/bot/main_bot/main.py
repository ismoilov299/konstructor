# modul/bot/main_bot/main.py (tozalangan versiya)

import asyncio
from aiogram import Router, Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from asgiref.sync import sync_to_async

from modul.config import settings_conf
from modul.loader import main_bot_router, client_bot_router
from modul.models import User
from modul.bot.main_bot.services.user_service import get_user_by_uid
from modul.bot.main_bot.handlers.create_bot import create_bot_router
from modul.bot.main_bot.handlers.manage_bots import manage_bots_router

import requests
import logging

logger = logging.getLogger(__name__)

webhook_url = 'https://ismoilov299.uz/login/'


# Keyboard funksiyalari
async def main_menu():
    """Asosiy menyu klaviaturasi"""
    buttons = [
        [InlineKeyboardButton(text="🤖 Mening botlarim", callback_data="my_bots")],
        [InlineKeyboardButton(text="➕ Yangi bot yaratish", callback_data="create_bot")],
        [InlineKeyboardButton(text="📊 Statistika", callback_data="statistics")],
        [InlineKeyboardButton(text="💰 Balans", callback_data="balance")],
        [InlineKeyboardButton(text="🔧 Sozlamalar", callback_data="settings")],
        [InlineKeyboardButton(text="❓ Yordam", callback_data="help")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


async def registration_keyboard(registration_url):
    """Ro'yxatdan o'tish klaviaturasi"""
    buttons = [[InlineKeyboardButton(text="📝 Ro'yxatdan o'tish", url=registration_url)]]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def init_bot_handlers():
    @main_bot_router.message(CommandStart())
    async def cmd_start(message: Message, state: FSMContext):
        """Start komandasi handleri"""
        logger.info(f"Start command from user {message.from_user.id}")
        user = message.from_user

        try:
            # Foydalanuvchi mavjudligini async tekshirish
            db_user = await get_user_by_uid(user.id)

            if db_user:
                # Ro'yxatdan o'tgan foydalanuvchi - asosiy menyuni ko'rsatish
                await message.answer(
                    f"👋 <b>Xush kelibsiz, {user.first_name}!</b>\n\n"
                    f"🤖 <b>Bot Konstruktor</b>ga xush kelibsiz!\n"
                    f"Bu yerda siz o'zingizning Telegram botlaringizni yaratishingiz va boshqarishingiz mumkin.\n\n"
                    f"📈 <b>Imkoniyatlar:</b>\n"
                    f"• Bot yaratish va sozlash\n"
                    f"• Modullarni boshqarish\n"
                    f"• Statistikalarni kuzatish\n"
                    f"• To'lovlar va balansni boshqarish\n\n"
                    f"Quyidagi tugmalardan birini tanlang:",
                    reply_markup=await main_menu(),
                    parse_mode="HTML"
                )
                logger.info(f"Main menu shown to user {user.id}")
            else:
                # Yangi foydalanuvchi - ro'yxatdan o'tkazish
                await handle_new_user_registration(message, user)

        except Exception as e:
            logger.error(f"Error in cmd_start for user {user.id}: {e}")
            await message.answer(
                "❌ Xatolik yuz berdi. Iltimos, qaytadan urinib ko'ring.\n"
                "/start",
                parse_mode="HTML"
            )

    async def handle_new_user_registration(message: Message, user):
        """Yangi foydalanuvchi ro'yxatdan o'tkazish"""
        telegram_id = user.id
        first_name = user.first_name
        last_name = user.last_name or "Не указано"
        username = user.username or "Не указано"

        # Foydalanuvchi rasmini olish
        photo_link = None
        try:
            user_photos = await message.bot.get_user_profile_photos(telegram_id)
            if user_photos.total_count > 0:
                photo_id = user_photos.photos[0][-1].file_id
                photo_url = await message.bot.get_file(photo_id)
                photo_link = f"https://api.telegram.org/file/bot{settings_conf.BOT_TOKEN}/{photo_url.file_path}"
        except Exception as e:
            logger.warning(f"Could not get user photo for {telegram_id}: {e}")

        # Ro'yxatdan o'tish linki
        registration_url = (
            f"{webhook_url}?"
            f"id={telegram_id}&first_name={first_name}&last_name={last_name}&username={username}"
        )
        if photo_link:
            registration_url += f"&photo_url={photo_link}"

        kb = await registration_keyboard(registration_url)

        await message.answer(
            f"👋 <b>Salom, {first_name}!</b>\n\n"
            f"🤖 <b>Bot Konstruktor</b>ga xush kelibsiz!\n\n"
            f"Bu platformada siz:\n"
            f"• 🚀 O'z Telegram botlaringizni yaratishingiz\n"
            f"• ⚙️ Ularni professional darajada boshqarishingiz\n"
            f"• 📊 Batafsil statistikalarni ko'rishingiz\n"
            f"• 💰 Daromad olishingiz mumkin\n\n"
            f"🎯 <b>9 ta modul mavjud:</b>\n"
            f"💸 Referral • 🎬 Kino • 🎵 Musiqa • 📥 Yuklab olish\n"
            f"💬 ChatGPT • ❤️ Tanishuv • 🔮 Munajjimlik\n"
            f"👤 Anonim chat • 📱 SMS yuborish\n\n"
            f"<b>Boshlash uchun ro'yxatdan o'ting:</b>",
            reply_markup=kb,
            parse_mode="HTML"
        )
        logger.info(f"Registration message sent to new user {telegram_id}")

    # Callback query handlerlar
    @main_bot_router.callback_query(F.data == "back_to_main")
    async def back_to_main(callback: CallbackQuery, state: FSMContext):
        """Asosiy menyuga qaytish"""
        await state.clear()
        await callback.message.edit_text(
            f"🏠 <b>Asosiy menyu</b>\n\n"
            f"Kerakli bo'limni tanlang:",
            reply_markup=await main_menu(),
            parse_mode="HTML"
        )
        await callback.answer()

    @main_bot_router.callback_query(F.data == "statistics")
    async def show_statistics(callback: CallbackQuery):
        """Umumiy statistikani ko'rsatish"""
        from modul.bot.main_bot.services.user_service import get_user_statistics

        try:
            user_stats = await get_user_statistics(callback.from_user.id)

            if not user_stats:
                await callback.message.edit_text(
                    "❌ Statistika ma'lumotlarini olishda xatolik.",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="◀️ Orqaga", callback_data="back_to_main")]
                    ]),
                    parse_mode="HTML"
                )
                await callback.answer()
                return

            text = f"📊 <b>Sizning statistikangiz</b>\n\n" \
                   f"👤 <b>Foydalanuvchi:</b> {user_stats['user_name']}\n" \
                   f"📛 <b>Username:</b> @{user_stats['user_username']}\n\n" \
                   f"🤖 <b>Jami botlar:</b> {user_stats['total_bots']}\n" \
                   f"🟢 <b>Faol botlar:</b> {user_stats['active_bots']}\n" \
                   f"👥 <b>Jami foydalanuvchilar:</b> {user_stats['total_bot_users']}\n" \
                   f"💰 <b>Balans:</b> {user_stats['balance']} so'm\n" \
                   f"👨‍👩‍👧‍👦 <b>Referrallar:</b> {user_stats['refs_count']} ta"

            buttons = [
                [InlineKeyboardButton(text="📈 Batafsil hisobot", callback_data="detailed_stats")],
                [InlineKeyboardButton(text="💰 Balans tarixi", callback_data="balance_history")],
                [InlineKeyboardButton(text="◀️ Orqaga", callback_data="back_to_main")]
            ]

            await callback.message.edit_text(
                text,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
                parse_mode="HTML"
            )

        except Exception as e:
            logger.error(f"Error showing statistics for {callback.from_user.id}: {e}")
            await callback.message.edit_text(
                "❌ Statistikani yuklashda xatolik.\n"
                "Iltimos, qaytadan urinib ko'ring.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔄 Qayta urinish", callback_data="statistics")],
                    [InlineKeyboardButton(text="◀️ Orqaga", callback_data="back_to_main")]
                ]),
                parse_mode="HTML"
            )

        await callback.answer()

    @main_bot_router.callback_query(F.data == "balance")
    async def show_balance(callback: CallbackQuery):
        """Balansni ko'rsatish"""
        await callback.message.edit_text(
            "💰 <b>Balans</b>\n\n"
            "Bu funksiya hali ishlab chiqilmoqda...\n"
            "Tez orada quyidagi imkoniyatlar qo'shiladi:\n\n"
            "• 💳 To'lov tarixi\n"
            "• 📊 Daromad statistikasi\n"
            "• 💸 Pul yechish\n"
            "• 🎁 Bonuslar",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Orqaga", callback_data="back_to_main")]
            ]),
            parse_mode="HTML"
        )
        await callback.answer()

    @main_bot_router.callback_query(F.data == "settings")
    async def show_settings(callback: CallbackQuery):
        """Sozlamalarni ko'rsatish"""
        await callback.message.edit_text(
            "🔧 <b>Sozlamalar</b>\n\n"
            "Bu funksiya hali ishlab chiqilmoqda...\n"
            "Tez orada quyidagi sozlamalar qo'shiladi:\n\n"
            "• 👤 Profil sozlamalari\n"
            "• 🔔 Bildirishnomalar\n"
            "• 🌐 Til tanlash\n"
            "• 🔐 Xavfsizlik",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Orqaga", callback_data="back_to_main")]
            ]),
            parse_mode="HTML"
        )
        await callback.answer()

    @main_bot_router.callback_query(F.data == "help")
    async def show_help(callback: CallbackQuery):
        """Yordam bo'limini ko'rsatish"""
        help_text = (
            "❓ <b>Yordam va Qo'llanma</b>\n\n"
            "🤖 <b>Bot Konstruktor nima?</b>\n"
            "Bu platforma orqali siz professional Telegram botlar yaratishingiz va boshqarishingiz mumkin.\n\n"
            "🚀 <b>Qanday boshlash kerak?</b>\n"
            "1️⃣ Ro'yxatdan o'ting\n"
            "2️⃣ @BotFather dan bot yarating\n"
            "3️⃣ Bot tokenini bizga bering\n"
            "4️⃣ Kerakli modullarni tanlang\n"
            "5️⃣ Botingiz tayyor!\n\n"
            "🔧 <b>Mavjud modullar:</b>\n"
            "💸 Referral tizimi - daromad oling\n"
            "🎬 Kino bot - filmlar ulashing\n"
            "🎵 Musiqa bot - qo'shiqlar toping\n"
            "📥 Download bot - media yuklab oling\n"
            "💬 ChatGPT - AI yordamchisi\n"
            "❤️ Tanishuv - Leo Match tizimi\n"
            "🔮 Munajjimlik - bashorat va horoskop\n"
            "👤 Anonim chat - maxfiy suhbat\n"
            "📱 SMS yuborish - xabar jo'natish\n\n"
            "💬 <b>Qo'shimcha savol?</b>\n"
            "Bizning qo'llab-quvvatlash xizmatiga murojaat qiling."
        )

        await callback.message.edit_text(
            help_text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📞 Qo'llab-quvvatlash", url="https://t.me/support_username")],
                [InlineKeyboardButton(text="📖 Batafsil qo'llanma", url="https://docs.example.com")],
                [InlineKeyboardButton(text="💬 Guruh chat", url="https://t.me/botconstructor_group")],
                [InlineKeyboardButton(text="◀️ Orqaga", callback_data="back_to_main")]
            ]),
            parse_mode="HTML"
        )
        await callback.answer()

    # Placeholder handlers for future features
    @main_bot_router.callback_query(F.data == "detailed_stats")
    async def detailed_stats_placeholder(callback: CallbackQuery):
        """Batafsil statistika (placeholder)"""
        await callback.answer("⚠️ Bu funksiya hali ishlab chiqilmoqda...", show_alert=True)

    @main_bot_router.callback_query(F.data == "balance_history")
    async def balance_history_placeholder(callback: CallbackQuery):
        """Balans tarixi (placeholder)"""
        await callback.answer("⚠️ Bu funksiya hali ishlab chiqilmoqda...", show_alert=True)

    # Include sub-routers
    main_bot_router.include_router(create_bot_router)
    main_bot_router.include_router(manage_bots_router)

    logger.info("Main bot handlers initialized successfully!")


# Test uchun alohida funksiya
async def test_db_connection():
    """Ma'lumotlar bazasi ulanishini tekshirish"""
    try:
        user = await get_user_by_uid(1)  # Test UID
        logger.info(f"DB test successful. User: {user}")
        return True
    except Exception as e:
        logger.error(f"DB test failed: {e}")
        return False


# Agar to'g'ridan-to'g'ri ishga tushirilsa
if __name__ == "__main__":
    async def main():
        await test_db_connection()
        logger.info("Main bot handlers ready!")


    asyncio.run(main())
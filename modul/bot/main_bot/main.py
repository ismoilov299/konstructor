# modul/bot/main_bot/main.py (tuzatilgan versiya)

import asyncio
from aiogram import Router, Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from asgiref.sync import sync_to_async

from modul.config import settings_conf
from modul.loader import main_bot_router, client_bot_router
from modul.models import User

import requests

webhook_url = 'https://ismoilov299.uz/login/'


# Django ORM'ni async qilish uchun dekoratorlar
@sync_to_async
def get_user_by_uid(uid):
    """Foydalanuvchini UID bo'yicha olish"""
    try:
        return User.objects.get(uid=uid)
    except User.DoesNotExist:
        return None


@sync_to_async
def create_user_if_not_exists(uid, first_name, last_name=None, username=None):
    """Foydalanuvchi mavjud bo'lmasa yaratish"""
    try:
        user, created = User.objects.get_or_create(
            uid=uid,
            defaults={
                'first_name': first_name,
                'last_name': last_name or "Не указано",
                'username': username or "Не указано"
            }
        )
        return user, created
    except Exception as e:
        print(f"Error creating user: {e}")
        return None, False


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
        print(f"Start command from user {message.from_user.id}")
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
                    f"Quyidagi tugmalardan birini tanlang:",
                    reply_markup=await main_menu(),
                    parse_mode="HTML"
                )
            else:
                # Yangi foydalanuvchi - ro'yxatdan o'tkazish
                await handle_new_user_registration(message, user)

        except Exception as e:
            print(f"Error in cmd_start: {e}")
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
            print(f"Error getting user photo: {e}")

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
            f"Bu bot orqali siz:\n"
            f"• 🤖 O'z botlaringizni yaratishingiz\n"
            f"• ⚙️ Ularni boshqarishingiz\n"
            f"• 📊 Statistikalarni ko'rishingiz mumkin\n\n"
            f"Avval ro'yxatdan o'ting:",
            reply_markup=kb,
            parse_mode="HTML"
        )

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

    @main_bot_router.callback_query(F.data == "my_bots")
    async def show_my_bots(callback: CallbackQuery):
        """Foydalanuvchi botlarini ko'rsatish"""
        # Hozircha placeholder
        await callback.message.edit_text(
            "🤖 <b>Sizning botlaringiz</b>\n\n"
            "Bu funksiya hali ishlab chiqilmoqda...\n"
            "Tez orada mavjud bo'ladi!",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Orqaga", callback_data="back_to_main")]
            ]),
            parse_mode="HTML"
        )
        await callback.answer()

    @main_bot_router.callback_query(F.data == "create_bot")
    async def create_new_bot(callback: CallbackQuery):
        """Yangi bot yaratish"""
        await callback.message.edit_text(
            "➕ <b>Yangi bot yaratish</b>\n\n"
            "Bu funksiya hali ishlab chiqilmoqda...\n"
            "Tez orada mavjud bo'ladi!",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Orqaga", callback_data="back_to_main")]
            ]),
            parse_mode="HTML"
        )
        await callback.answer()

    @main_bot_router.callback_query(F.data == "statistics")
    async def show_statistics(callback: CallbackQuery):
        """Statistikani ko'rsatish"""
        await callback.message.edit_text(
            "📊 <b>Statistika</b>\n\n"
            "Bu funksiya hali ishlab chiqilmoqda...\n"
            "Tez orada mavjud bo'ladi!",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
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
            "Tez orada mavjud bo'ladi!",
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
            "Tez orada mavjud bo'ladi!",
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
            "❓ <b>Yordam</b>\n\n"
            "🤖 <b>Bot Konstruktor nima?</b>\n"
            "Bu platforma orqali siz oson va tez Telegram botlar yaratishingiz mumkin.\n\n"
            "🚀 <b>Qanday boshlash kerak?</b>\n"
            "1. Ro'yxatdan o'ting\n"
            "2. @BotFather dan bot yarating\n"
            "3. Bot tokenini bizga bering\n"
            "4. Kerakli modullarni tanlang\n"
            "5. Botingiz tayyor!\n\n"
            "💬 <b>Qo'shimcha savol?</b>\n"
            "Bizning qo'llab-quvvatlash xizmatiga murojaat qiling."
        )

        await callback.message.edit_text(
            help_text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📞 Qo'llab-quvvatlash", url="https://t.me/support_username")],
                [InlineKeyboardButton(text="◀️ Orqaga", callback_data="back_to_main")]
            ]),
            parse_mode="HTML"
        )
        await callback.answer()

    print("Main bot handlers initialized successfully!")


# Test uchun alohida funksiya
async def test_db_connection():
    """Ma'lumotlar bazasi ulanishini tekshirish"""
    try:
        user = await get_user_by_uid(1)  # Test UID
        print(f"DB test successful. User: {user}")
        return True
    except Exception as e:
        print(f"DB test failed: {e}")
        return False


# Agar to'g'ridan-to'g'ri ishga tushirilsa
if __name__ == "__main__":
    async def main():
        await test_db_connection()
        print("Main bot handlers ready!")


    asyncio.run(main())
# import asyncio
#
# from aiogram import Router, Bot, Dispatcher, F
# from aiogram.filters import CommandStart
# from aiogram.fsm.context import FSMContext
# from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
#
# from modul.config import settings_conf
# from modul.loader import main_bot_router, client_bot_router
#
# import requests
#
#
# webhook_url = 'https://ismoilov299.uz/login/'
#
#
# def init_bot_handlers():
#     @main_bot_router.message(CommandStart())
#     async def cmd_start(message: Message, state: FSMContext, ):
#         print(message.from_user.id)
#         user = message.from_user
#         telegram_id = user.id
#         first_name = user.first_name
#         last_name = user.last_name or "Не указано"
#         username = user.username or "Не указано"
#
#         # Получение фотографии профиля пользователя
#         user_photos = await message.bot.get_user_profile_photos(telegram_id)
#         photo_link = None
#         if user_photos.total_count > 0:
#             photo_id = user_photos.photos[0][-1].file_id  # Получаем последнюю (самую большую) фотографию
#             photo_url = await message.bot.get_file(photo_id)
#             photo_link = f"https://api.telegram.org/file/bot{settings_conf.BOT_TOKEN}/{photo_url.file_path}"
#
#         # Генерация ссылки для регистрации
#         registration_url = (
#             f"{webhook_url}?"
#             f"id={telegram_id}&first_name={first_name}&last_name={last_name}&username={username}"
#         )
#         if photo_link:
#             registration_url += f"&photo_url={photo_link}"
#
#         button = [[InlineKeyboardButton(text="Регистрация", url=registration_url)]]
#
#         kb = InlineKeyboardMarkup(inline_keyboard=button)
#
#         # Отправка приветственного сообщения
#         await message.answer(f"Привет, {first_name}! Нажмите на эту кнопку для регистрации\n", reply_markup=kb)
#
# # async def main_bot():
# #     bot = Bot(token="996043954:AAGbwv9SCRyklY4-hMsy3yMkZsiDJbDJ6YU")
# #     dp = Dispatcher()
# #     dp.include_router(main_bot_router)
# #     await bot.delete_webhook()
# #     await dp.start_polling(bot)
# #
# #
# # if __name__ == "__main__":
# #     asyncio.run(main_bot())

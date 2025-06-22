# modul/bot/main_bot/main.py (yangilangan)
from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from .handlers.create_bot import create_bot_router
from .handlers.manage_bots import manage_bots_router
from .keyboards.main_kb import main_menu
from modul.models import User
from ...config import settings_conf
from ...loader import main_bot_router


def init_bot_handlers():
    @main_bot_router.message(CommandStart())
    async def cmd_start(message: Message, state: FSMContext):
        user = message.from_user

        # Foydalanuvchi ro'yxatdan o'tganmi tekshirish
        try:
            db_user = User.objects.get(uid=user.id)
            # Ro'yxatdan o'tgan foydalanuvchi - asosiy menyuni ko'rsatish
            await message.answer(
                f"👋 <b>Xush kelibsiz, {user.first_name}!</b>\n\n"
                f"🤖 <b>Bot Konstruktor</b>ga xush kelibsiz!\n"
                f"Bu yerda siz o'zingizning Telegram botlaringizni yaratishingiz va boshqarishingiz mumkin.\n\n"
                f"Quyidagi tugmalardan birini tanlang:",
                reply_markup=await main_menu(),
                parse_mode="HTML"
            )
        except User.DoesNotExist:
            # Yangi foydalanuvchi - ro'yxatdan o'tkazish
            telegram_id = user.id
            first_name = user.first_name
            last_name = user.last_name or "Не указано"
            username = user.username or "Не указано"

            # Foydalanuvchi rasmini olish
            user_photos = await message.bot.get_user_profile_photos(telegram_id)
            photo_link = None
            if user_photos.total_count > 0:
                photo_id = user_photos.photos[0][-1].file_id
                photo_url = await message.bot.get_file(photo_id)
                photo_link = f"https://api.telegram.org/file/bot{settings_conf.BOT_TOKEN}/{photo_url.file_path}"

            # Ro'yxatdan o'tish linki
            registration_url = (
                f"https://ismoilov299.uz/login/?"
                f"id={telegram_id}&first_name={first_name}&last_name={last_name}&username={username}"
            )
            if photo_link:
                registration_url += f"&photo_url={photo_link}"

            button = [[InlineKeyboardButton(text="📝 Ro'yxatdan o'tish", url=registration_url)]]
            kb = InlineKeyboardMarkup(inline_keyboard=button)

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

    # Back to main menu handler
    @main_bot_router.callback_query(F.data == "back_to_main")
    async def back_to_main(callback: CallbackQuery, state: FSMContext):
        await state.clear()
        await callback.message.edit_text(
            f"🏠 <b>Asosiy menyu</b>\n\n"
            f"Kerakli bo'limni tanlang:",
            reply_markup=await main_menu(),
            parse_mode="HTML"
        )

    # Include sub-routers
    main_bot_router.include_router(create_bot_router)
    main_bot_router.include_router(manage_bots_router)
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

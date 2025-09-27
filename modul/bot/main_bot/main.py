# modul/bot/main_bot/main.py (to'g'irlangan versiya)

import asyncio
from datetime import datetime

from aiogram import Router, Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from asgiref.sync import sync_to_async
from django.db.models import F as DjangoF

from modul.config import settings_conf
from modul.loader import main_bot_router, client_bot_router
from modul.models import User
from modul.bot.main_bot.services.user_service import get_user_by_uid, create_user_directly
from modul.bot.main_bot.handlers.create_bot import create_bot_router
from modul.bot.main_bot.handlers.manage_bots import manage_bots_router
from aiogram.types import LabeledPrice
import requests
import logging

logger = logging.getLogger(__name__)

ADMIN_CHAT_ID = 1161180912
MAIN_BOT_USERNAME = "test_new_my_robot"

webhook_url = 'https://ismoilov299.uz/login/'


async def main_menu():
    """Asosiy menyu klaviaturasi - yangilangan"""
    buttons = [
        [
            InlineKeyboardButton(text="Создать бота ⚙️", callback_data="create_bot"),
            InlineKeyboardButton(text="Мои боты 🖥️", callback_data="my_bots")
        ],
        [
            InlineKeyboardButton(text="Инфо 📖", callback_data="info"),
            InlineKeyboardButton(text="FAQ 💬", callback_data="faq")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


async def registration_keyboard(registration_url):
    """Ro'yxatdan o'tish klaviaturasi"""
    buttons = [[InlineKeyboardButton(text="📝 Регистрация", url=registration_url)]]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def init_bot_handlers():
    @main_bot_router.message(CommandStart())
    async def cmd_start(message: Message, state: FSMContext):
        from modul.bot.main_bot.handlers import admin_panel

        logger.info("✅ Main bot handlers loaded successfully")
        logger.info("✅ Admin panel handlers loaded")

        """Start komandasi handleri"""
        logger.info(f"Start command from user {message.from_user.id}")
        user = message.from_user

        # Start komandaning argumentlarini tekshirish
        args = message.text.split()

        # Agar to'lov parametrlari bo'lsa
        if len(args) > 1 and args[1].startswith("gptbot_"):
            await handle_payment_start(message, args[1])
            return

        try:
            # Foydalanuvchi mavjudligini async tekshirish
            db_user = await get_user_by_uid(user.id)

            if db_user:
                # Ro'yxatdan o'tgan foydalanuvchi - asosiy menyuni ko'rsatish
                await message.answer(
                    f"👋 <b>Добро пожаловать, {user.first_name}!</b>\n\n"
                    f"🤖 <b>Конструктор ботов</b> - создавайте и управляйте своими Telegram ботами!\n\n"
                    f"🔧 <b>Возможности:</b>\n"
                    f"• Создание ботов за 2-3 минуты\n"
                    f"• 6 профессиональных ботов\n"
                    f"• Полная панель управления\n"
                    f"• Автоматическая настройка\n\n"
                    f"Выберите действие:",
                    reply_markup=await main_menu(),
                    parse_mode="HTML"
                )
                logger.info(f"Main menu shown to existing user {user.id}")
            else:
                # Yangi foydalanuvchi - avtomatik ro'yxatdan o'tkazish
                new_user = await handle_auto_registration(message, user)
                if new_user:
                    await message.answer(
                        f"👋 <b>Добро пожаловать, {user.first_name}!</b>\n\n"
                        f"🤖 <b>Конструктор ботов</b> - создавайте и управляйте своими Telegram ботами!\n\n"
                        f"🔧 <b>Возможности:</b>\n"
                        f"• Создание ботов за 2-3 минуты\n"
                        f"• 6 профессиональных ботов\n"
                        f"• Полная панель управления\n"
                        f"• Автоматическая настройка\n\n"
                        f"🎯 <b>Доступно 6 ботов:</b>\n"
                        f"💸 Рефералы • 🎬 Кино • 📥 Загрузчик\n"
                        f"💬 ChatGPT • ❤️ Знакомства • 👤 Анонимный чат\n\n"
                        f"Выберите действие:",
                        reply_markup=await main_menu(),
                        parse_mode="HTML"
                    )
                    logger.info(f"Main menu shown to new registered user {user.id}")
                else:
                    await message.answer(
                        "❌ Произошла ошибка при регистрации. Попробуйте еще раз.\n"
                        "/start",
                        parse_mode="HTML"
                    )

        except Exception as e:
            logger.error(f"Error in cmd_start for user {user.id}: {e}")
            await message.answer(
                "❌ Произошла ошибка. Попробуйте еще раз.\n"
                "/start",
                parse_mode="HTML"
            )

    async def handle_payment_start(message: Message, payment_args: str):
        """To'lov parametrlarini qayta ishlash"""
        try:
            parts = payment_args.split("_")
            if len(parts) >= 4:  # gptbot_user_id_stars_bot_id
                client_user_id = int(parts[1])
                stars_amount = int(parts[2])
                bot_id = int(parts[3])

                stars_to_rubles = {
                    1: 5,
                    5: 25
                }

                if stars_amount not in stars_to_rubles:
                    await message.answer(
                        "❌ Неверная сумма для пополнения.\n"
                        "Доступные варианты: 1 или 5 звезд",
                        parse_mode="HTML"
                    )
                    return

                rubles_amount = stars_to_rubles[stars_amount]

                await message.answer_invoice(
                    title=f"Пополнение баланса ChatGPT бота",
                    description=f"Пополнение баланса на {rubles_amount}₽ для ChatGPT бота",
                    payload=f"gptbot_topup_{client_user_id}_{stars_amount}_{rubles_amount}_{bot_id}",
                    currency="XTR",  # Telegram Stars currency
                    prices=[LabeledPrice(label=f"{stars_amount} ⭐️", amount=stars_amount)],
                    provider_token="",  # Bo'sh string Stars uchun
                )

                logger.info(
                    f"Invoice sent to user {message.from_user.id} for {stars_amount} stars ({rubles_amount} rubles) for client {client_user_id}, bot_id {bot_id}")

            else:
                await message.answer(
                    "❌ Неверные параметры платежа.\n"
                    "Попробуйте перейти по ссылке еще раз.",
                    parse_mode="HTML"
                )

        except (ValueError, IndexError) as e:
            logger.error(f"Error parsing payment args {payment_args}: {e}")
            await message.answer(
                "❌ Ошибка обработки параметров платежа.\n"
                "Попробуйте перейти по ссылке еще раз.",
                parse_mode="HTML"
            )

    @main_bot_router.pre_checkout_query()
    async def pre_checkout_query_handler(pre_checkout_query):
        """To'lovdan oldin tekshirish"""
        try:
            payload = pre_checkout_query.invoice_payload
            if payload.startswith("gptbot_topup_"):
                parts = payload.split("_")
                client_user_id = int(parts[2])
                stars_amount = int(parts[3])
                rubles_amount = int(parts[4])
                bot_id = int(parts[5])  # Bot ID ni to'g'ri parse qilish

                logger.info(
                    f"Pre-checkout query for {stars_amount} stars ({rubles_amount} rubles) for client {client_user_id}, bot_id {bot_id}")

                # To'lovni tasdiqlash
                await pre_checkout_query.answer(ok=True)
            else:
                await pre_checkout_query.answer(ok=False, error_message="Неверный платеж")

        except Exception as e:
            logger.error(f"Error in pre_checkout_query: {e}")
            await pre_checkout_query.answer(ok=False, error_message="Ошибка обработки платежа")

    @main_bot_router.message(F.successful_payment)
    async def successful_payment_handler(message: Message):
        """Muvaffaqiyatli to'lov handleri"""
        try:
            payment = message.successful_payment
            payload = payment.invoice_payload

            if payload.startswith("gptbot_topup_"):
                parts = payload.split("_")
                client_user_id = int(parts[2])
                stars_amount = int(parts[3])
                rubles_amount = float(parts[4])
                bot_id = int(parts[5])  # Bot ID ni to'g'ri parse qilish

                # Telegram payment ID
                payment_id = payment.telegram_payment_charge_id

                # SIZNING FUNKSIYANGIZNI ISHLATISH
                success = await User.add_user_balance(client_user_id, bot_id, rubles_amount)

                if success:
                    # Admin ga xabar yuborish
                    await send_admin_notification(
                        message.bot, client_user_id, bot_id,
                        stars_amount, rubles_amount, payment_id
                    )

                    # Foydalanuvchiga xabar yuborish (agar kerak bo'lsa)
                    await send_user_notification(client_user_id, bot_id, rubles_amount)

                    await message.answer(
                        f"✅ <b>Оплата прошла успешно!</b>\n\n"
                        f"💎 Оплачено: {stars_amount} ⭐️\n"
                        f"💰 Зачислено: {rubles_amount}₽\n"
                        f"👤 Пользователь: <code>{client_user_id}</code>\n"
                        f"🤖 Бот ID: {bot_id}\n"
                        f"🔗 ID платежа: <code>{payment_id}</code>\n\n"
                        f"🔄 Баланс обновлен автоматически!\n"
                        f"📬 Уведомления отправлены!",
                        parse_mode="HTML"
                    )

                    logger.info(
                        f"Successfully added {rubles_amount} rubles to user {client_user_id} balance for bot {bot_id}")

                else:
                    await message.answer(
                        f"⚠️ <b>Оплата получена, но возникла ошибка при зачислении!</b>\n\n"
                        f"💎 Оплачено: {stars_amount} ⭐️\n"
                        f"💰 Сумма: {rubles_amount}₽\n"
                        f"👤 Пользователь: <code>{client_user_id}</code>\n"
                        f"🤖 Бот ID: {bot_id}\n"
                        f"🔗 ID платежа: <code>{payment_id}</code>\n\n"
                        f"📞 Требуется ручная проверка!",
                        parse_mode="HTML"
                    )
                    logger.error(f"Payment received but failed to add balance for user {client_user_id}, bot {bot_id}")

        except Exception as e:
            logger.error(f"Error in successful_payment_handler: {e}")
            await message.answer(
                "❌ Критическая ошибка при обработке оплаты.\n"
                "Администратор будет уведомлен.",
                parse_mode="HTML"
            )

    async def handle_auto_registration(message: Message, user):
        """Yangi foydalanuvchini avtomatik ro'yxatdan o'tkazish"""
        try:
            telegram_id = user.id
            first_name = user.first_name or "Пользователь"
            last_name = user.last_name or ""
            username = user.username or ""

            # Foydalanuvchi rasmini olish
            photo_url = None
            try:
                user_photos = await message.bot.get_user_profile_photos(telegram_id)
                if user_photos.total_count > 0:
                    photo_id = user_photos.photos[0][-1].file_id
                    photo_file = await message.bot.get_file(photo_id)
                    photo_url = f"https://api.telegram.org/file/bot{message.bot.token}/{photo_file.file_path}"
            except Exception as e:
                logger.warning(f"Could not get user photo for {telegram_id}: {e}")

            # Foydalanuvchini to'g'ridan-to'g'ri bazaga qo'shish
            new_user = await create_user_directly(
                uid=telegram_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
                profile_image_url=photo_url
            )

            if new_user:
                logger.info(f"User {telegram_id} auto-registered successfully")
                return new_user
            else:
                logger.error(f"Failed to auto-register user {telegram_id}")
                return None

        except Exception as e:
            logger.error(f"Error in auto registration for user {telegram_id}: {e}")
            return None

    @main_bot_router.callback_query(F.data == "back_to_main")
    async def back_to_main(callback: CallbackQuery, state: FSMContext):
        """Asosiy menyuga qaytish"""
        await state.clear()
        await callback.message.edit_text(
            f"🏠 <b>Главное меню</b>\n\n"
            f"Выберите нужное действие:",
            reply_markup=await main_menu(),
            parse_mode="HTML"
        )
        await callback.answer()

    @main_bot_router.callback_query(F.data == "info")
    async def show_info(callback: CallbackQuery):
        info_text = (
            f"📖 <b>Информация о Конструкторе ботов</b>\n\n"
            f"🤖 <b>Что это?</b>\n"
            f"Конструктор ботов - это платформа для создания и управления Telegram ботами без программирования.\n\n"
            f"⚡ <b>Быстро и просто:</b>\n"
            f"• Создание бота за 2-3 минуты\n"
            f"• Готовые бот функций\n"
            f"• Автоматическая настройка\n"
            f"• Подробная статистика\n\n"
            f"🎯 <b>6 профессиональных бот:</b>\n\n"
            f"💸 <b>Реферальная система</b> - зарабатывайте на рефералах\n"
            f"🎬 <b>Кино бот</b> - поиск и скачивание фильмов\n"
            f"📥 <b>Загрузчик</b> - скачивание с YouTube, Instagram, TikTok\n"
            f"💬 <b>ChatGPT</b> - ИИ помощник\n"
            f"❤️ <b>Знакомства</b> - система знакомств Leo Match\n"
            f"👤 <b>Анонимный чат</b> - анонимное общение\n"

            f"💡 <b>Преимущества:</b>\n"
            f"• Без кодирования\n"
            f"• Мгновенный запуск\n"
            f"• Техническая поддержка\n"
            f"• Постоянные обновления"
        )

        await callback.message.edit_text(
            info_text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🤖 Создать бота", callback_data="create_bot")],
                [InlineKeyboardButton(text="💬 Поддержка", url="https://t.me/Dark_Just")],
                [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main")]
            ]),
            parse_mode="HTML"
        )
        await callback.answer()

    @main_bot_router.callback_query(F.data == "faq")
    async def show_faq(callback: CallbackQuery):
        """FAQ бо'лими"""
        faq_text = (
            f"💬 <b>Часто задаваемые вопросы (FAQ)</b>\n\n"
            f"❓ <b>Как создать бота?</b>\n"
            f"1. Нажмите 'Создать бота ⚙️'\n"
            f"2. Получите токен у @BotFather\n"
            f"3. Вставьте токен в наш бот\n"
            f"4. Выберите нужные модули\n"
            f"5. Готово! Бот работает\n\n"
            f"💰 <b>Сколько это стоит?</b>\n"
            f"Создание бота - БЕСПЛАТНО!\n"
            f"Комиссия берется только с заработанных средств в модулях.\n\n"
            f"🔧 <b>Нужно ли знать программирование?</b>\n"
            f"НЕТ! Всё уже готово. Просто выбираете модули и настраиваете.\n\n"
            f"⚙️ <b>Можно ли изменить модули позже?</b>\n"
            f"ДА! В любое время можете включить/выключить модули в настройках.\n\n"
            f"📊 <b>Как посмотреть статистику?</b>\n"
            f"В разделе 'Мои боты 🖥️' выберите бота и нажмите 'Статистика'.\n\n"
            f"🛠️ <b>Что если бот сломается?</b>\n"
            f"У нас есть техническая поддержка 24/7. Обращайтесь в любое время!\n\n"
            f"💸 <b>Как работает реферальная система?</b>\n"
            f"За каждого приглашенного друга вы получаете бонус. Размер бонуса настраивается.\n\n"
            f"🔒 <b>Безопасно ли давать токен бота?</b>\n"
            f"ДА! Токен используется только для управления ботом. Мы НЕ можем получить доступ к вашему аккаунту.\n\n"
            f"⏱️ <b>Как быстро бот начнет работать?</b>\n"
            f"Сразу после создания! Обычно 30-60 секунд на настройку."
        )

        await callback.message.edit_text(
            faq_text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="❓ Задать вопрос", url="https://t.me/Dark_Just")],
                [InlineKeyboardButton(text="📖 Инструкция", url="https://ismoilov299.uz")],
                [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main")]
            ]),
            parse_mode="HTML"
        )
        await callback.answer()

    # Placeholder handlers
    @main_bot_router.callback_query(F.data == "statistics")
    async def statistics_redirect(callback: CallbackQuery):
        """Statistika - my_bots orqali yo'naltirish"""
        await callback.answer("📊 Статистику можно посмотреть в разделе 'Мои боты'")
        # my_bots ga yo'naltirish
        from modul.bot.main_bot.handlers.manage_bots import show_my_bots
        await show_my_bots(callback)

    @main_bot_router.callback_query(F.data == "balance")
    async def balance_redirect(callback: CallbackQuery):
        """Balans - my_bots orqali yo'naltirish"""
        await callback.answer("💰 Баланс можно посмотреть в разделе 'Мои боты'")
        # my_bots ga yo'naltirish
        from modul.bot.main_bot.handlers.manage_bots import show_my_bots
        await show_my_bots(callback)

    @main_bot_router.callback_query(F.data == "settings")
    async def settings_redirect(callback: CallbackQuery):
        """Sozlamalar - my_bots orqali yo'naltirish"""
        await callback.answer("🔧 Настройки ботов находятся в разделе 'Мои боты'")
        # my_bots ga yo'naltirish
        from modul.bot.main_bot.handlers.manage_bots import show_my_bots
        await show_my_bots(callback)

    @main_bot_router.callback_query(F.data == "help")
    async def help_redirect(callback: CallbackQuery):
        """Yordam - FAQ ga yo'naltirish"""
        await show_faq(callback)

    # Include sub-routers
    main_bot_router.include_router(create_bot_router)
    main_bot_router.include_router(manage_bots_router)

    logger.info("Main bot handlers initialized successfully!")


# ==== YORDAMCHI FUNKSIYALAR ====

@sync_to_async
def get_user_info(user_id: int, bot_id: int):
    """Foydalanuvchi ma'lumotlarini olish"""
    try:
        user = User.objects.filter(tg_id=user_id, bot_id=bot_id).first()
        if user:
            return {
                'username': getattr(user, 'username', 'Не указан'),
                'first_name': getattr(user, 'first_name', 'Не указан'),
                'balance': getattr(user, 'balance', 0)
            }
        return None
    except Exception as e:
        logger.error(f"Error getting user info: {e}")
        return None


async def send_admin_notification(bot, user_id: int, bot_id: int, stars_amount: int, rubles_amount: float,
                                  payment_id: str):
    """Admin ga xabar yuborish"""
    try:
        # Foydalanuvchi ma'lumotlarini olish
        user_info = await get_user_info(user_id, bot_id)

        if user_info:
            username = user_info.get('username', 'Не указан')
            first_name = user_info.get('first_name', 'Не указан')
            balance = user_info.get('balance', 0)
        else:
            username = 'Не найден'
            first_name = 'Не найден'
            balance = 0

        message = (
            f"💰 <b>НОВОЕ ПОПОЛНЕНИЕ</b>\n\n"
            f"👤 <b>Пользователь:</b>\n"
            f"• ID: <code>{user_id}</code>\n"
            f"• Имя: {first_name}\n"
            f"• Username: @{username}\n\n"
            f"💎 <b>Детали платежа:</b>\n"
            f"• Звезды: {stars_amount} ⭐️\n"
            f"• Зачислено: {rubles_amount}₽\n"
            f"• Бот ID: {bot_id}\n"
            f"• Payment ID: <code>{payment_id}</code>\n\n"
            f"💳 <b>Текущий баланс:</b> {balance}₽\n\n"
            f"🕐 <b>Время:</b> {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}"
        )

        await bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=message,
            parse_mode="HTML"
        )

        logger.info(f"Admin notification sent for payment {payment_id}")
        return True

    except Exception as e:
        logger.error(f"Error sending admin notification: {e}")
        return False


async def send_user_notification(user_id: int, bot_id: int, amount: float):
    """Foydalanuvchiga xabar yuborish (client bot orqali)"""
    try:
        # Bu yerda client bot instancesini olish kerak
        # Hozircha faqat log qilamiz
        logger.info(f"Should send notification to user {user_id} about {amount}₽ top-up")

        # Agar client bot token'lari ma'lum bo'lsa:
        # client_bot = await get_client_bot_by_id(bot_id)
        # if client_bot:
        #     await client_bot.send_message(
        #         chat_id=user_id,
        #         text=f"✅ Баланс пополнен на {amount}₽!"
        #     )

        return True

    except Exception as e:
        logger.error(f"Error sending user notification: {e}")
        return False


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

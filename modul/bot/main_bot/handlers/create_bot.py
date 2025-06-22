# modul/bot/main_bot/handlers/create_bot.py
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter
import re

from modul.bot.main_bot.keyboards.main_kb import create_bot_menu, bot_modules_menu, main_menu
from modul.bot.main_bot.states import CreateBotStates
from modul.models import Bot, User
from modul.crud import crud_bot
# from .states import CreateBotStates
# from .keyboards.main_kb import create_bot_menu, bot_modules_menu, main_menu

create_bot_router = Router()


@create_bot_router.callback_query(F.data == "create_bot")
async def start_create_bot(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "🤖 <b>Yangi bot yaratish</b>\n\n"
        "Botingizni yaratish uchun @BotFather dan olingan tokenni kiriting.\n\n"
        "Token formati: <code>1234567890:XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX</code>",
        reply_markup=await create_bot_menu(),
        parse_mode="HTML"
    )


@create_bot_router.callback_query(F.data == "enter_token")
async def request_token(callback: CallbackQuery, state: FSMContext):
    await state.set_state(CreateBotStates.waiting_for_token)
    await callback.message.edit_text(
        "📝 <b>Bot tokenini kiriting:</b>\n\n"
        "⚠️ Tokenni faqat @BotFather dan oling!\n"
        "❌ Boshqa hech kimga bermang!\n\n"
        "Token kiriting:",
        parse_mode="HTML"
    )


@create_bot_router.message(StateFilter(CreateBotStates.waiting_for_token))
async def process_token(message: Message, state: FSMContext):
    token = message.text.strip()

    # Token formatini tekshirish
    if not re.match(r'^\d+:[A-Za-z0-9_-]+$', token):
        await message.answer(
            "❌ <b>Noto'g'ri token formati!</b>\n\n"
            "Token quyidagi formatda bo'lishi kerak:\n"
            "<code>1234567890:XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX</code>\n\n"
            "Qaytadan urinib ko'ring:",
            parse_mode="HTML"
        )
        return

    # Token mavjudligini tekshirish
    existing_bot = Bot.objects.filter(token=token).first()
    if existing_bot:
        await message.answer(
            "❌ <b>Bu token allaqachon ishlatilmoqda!</b>\n\n"
            "Boshqa token kiriting:",
            parse_mode="HTML"
        )
        return

    # Bot ma'lumotlarini olish
    try:
        bot_info = await crud_bot.get_bot_info(token)
        if not bot_info:
            await message.answer(
                "❌ <b>Token noto'g'ri yoki bot topilmadi!</b>\n\n"
                "Tokenni tekshiring va qaytadan urinib ko'ring:",
                parse_mode="HTML"
            )
            return

        # State'ga saqlash
        await state.update_data(
            token=token,
            bot_username=bot_info['username'],
            bot_name=bot_info['first_name']
        )

        await state.set_state(CreateBotStates.configuring_modules)

        await message.answer(
            f"✅ <b>Bot topildi!</b>\n\n"
            f"🤖 <b>Nomi:</b> {bot_info['first_name']}\n"
            f"📛 <b>Username:</b> @{bot_info['username']}\n\n"
            f"<b>Endi bot uchun modullarni tanlang:</b>",
            reply_markup=await bot_modules_menu(),
            parse_mode="HTML"
        )

    except Exception as e:
        await message.answer(
            "❌ <b>Xatolik yuz berdi!</b>\n\n"
            "Tokenni tekshiring va qaytadan urinib ko'ring:",
            parse_mode="HTML"
        )


# Module toggle handlers
@create_bot_router.callback_query(F.data.startswith("toggle_"))
async def toggle_module(callback: CallbackQuery, state: FSMContext):
    module_name = callback.data.replace("toggle_", "")

    data = await state.get_data()
    modules = data.get('modules', {})

    # Module holatini o'zgartirish
    modules[module_name] = not modules.get(module_name, False)
    await state.update_data(modules=modules)

    # Keyboard'ni yangilash
    await callback.message.edit_reply_markup(
        reply_markup=await bot_modules_menu(selected_modules=modules)
    )


@create_bot_router.callback_query(F.data == "save_bot_config")
async def save_bot_config(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()

    try:
        # Bot yaratish
        user = User.objects.get(uid=callback.from_user.id)

        new_bot = Bot.objects.create(
            token=data['token'],
            username=data['bot_username'],
            name=data['bot_name'],
            owner=user,
            enable_refs=data['modules'].get('refs', False),
            enable_kino=data['modules'].get('kino', False),
            enable_music=data['modules'].get('music', False),
            enable_download=data['modules'].get('download', False),
            enable_chatgpt=data['modules'].get('chatgpt', False),
            enable_leo=data['modules'].get('leo', False),
            enable_horoscope=data['modules'].get('horoscope', False),
            enable_anon=data['modules'].get('anon', False),
            enable_sms=data['modules'].get('sms', False),
        )

        # Webhook o'rnatish
        webhook_url = f"https://ismoilov299.uz/bot/webhook/{data['token']}/"
        await crud_bot.set_webhook(data['token'], webhook_url)

        await state.clear()

        await callback.message.edit_text(
            f"🎉 <b>Bot muvaffaqiyatli yaratildi!</b>\n\n"
            f"🤖 <b>Bot:</b> @{data['bot_username']}\n"
            f"🔗 <b>Botni ishga tushiring:</b> https://t.me/{data['bot_username']}\n\n"
            f"✅ Bot ishga tushirildi va foydalanishga tayyor!",
            reply_markup=await main_menu(),
            parse_mode="HTML"
        )

    except Exception as e:
        await callback.message.edit_text(
            f"❌ <b>Xatolik yuz berdi!</b>\n\n"
            f"Sabab: {str(e)}\n\n"
            f"Qaytadan urinib ko'ring.",
            reply_markup=await main_menu(),
            parse_mode="HTML"
        )
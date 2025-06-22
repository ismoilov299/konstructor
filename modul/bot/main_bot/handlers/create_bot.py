# modul/bot/main_bot/handlers/create_bot.py
"""
Main bot orqali yangi bot yaratish handlerlari
"""

import re
import logging
import aiohttp
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter
from asgiref.sync import sync_to_async

from modul.bot.main_bot.services.user_service import (
    get_user_by_uid, create_bot, get_bot_info_from_telegram,
    set_bot_webhook, validate_bot_token
)
from modul.bot.main_bot.states import CreateBotStates
from modul.config import settings_conf

logger = logging.getLogger(__name__)

create_bot_router = Router()


# Keyboard funksiyalari
async def create_bot_menu():
    """Bot yaratish menyu klaviaturasi"""
    buttons = [
        [InlineKeyboardButton(text="📝 Bot tokenini kiriting", callback_data="enter_token")],
        [InlineKeyboardButton(text="❓ Token qanday olish?", callback_data="token_help")],
        [InlineKeyboardButton(text="◀️ Orqaga", callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


async def bot_modules_menu(selected_modules=None):
    """Bot modullari tanlash klaviaturasi"""
    if selected_modules is None:
        selected_modules = {}

    # Module ro'yxati va ularning ko'rinishi
    modules = [
        ("refs", "💸 Referral tizimi"),
        ("kino", "🎬 Kino bot"),
        ("music", "🎵 Musiqa bot"),
        ("download", "📥 Download bot"),
        ("chatgpt", "💬 ChatGPT"),
        ("leo", "❤️ Tanishuv (Leo)"),
        ("horoscope", "🔮 Munajjimlik"),
        ("anon", "👤 Anonim chat"),
        ("sms", "📱 SMS yuborish")
    ]

    buttons = []
    for module_key, module_name in modules:
        # Module yoqilgan bo'lsa ✅, aks holda ⬜
        icon = "✅" if selected_modules.get(module_key, False) else "⬜"
        text = f"{icon} {module_name}"
        buttons.append([InlineKeyboardButton(
            text=text,
            callback_data=f"toggle_{module_key}"
        )])

    # Qo'shimcha tugmalar
    buttons.append([InlineKeyboardButton(text="✅ Saqlash va yaratish", callback_data="save_bot_config")])
    buttons.append([InlineKeyboardButton(text="◀️ Orqaga", callback_data="back_to_main")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


async def back_to_modules_menu():
    """Modullar menyusiga qaytish klaviaturasi"""
    buttons = [
        [InlineKeyboardButton(text="◀️ Modullarni tanlashga qaytish", callback_data="select_modules")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# Handler'lar
@create_bot_router.callback_query(F.data == "create_bot")
async def start_create_bot(callback: CallbackQuery, state: FSMContext):
    """Bot yaratishni boshlash"""
    await state.clear()  # Avvalgi ma'lumotlarni tozalash

    await callback.message.edit_text(
        "🤖 <b>Yangi bot yaratish</b>\n\n"
        "Bot yaratish jarayoni:\n"
        "1️⃣ @BotFather dan bot tokeni olasiz\n"
        "2️⃣ Tokenni bizga berasiz\n"
        "3️⃣ Kerakli modullarni tanlaysiz\n"
        "4️⃣ Bot tayyor!\n\n"
        "Token formati: <code>1234567890:XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX</code>",
        reply_markup=await create_bot_menu(),
        parse_mode="HTML"
    )
    await callback.answer()


@create_bot_router.callback_query(F.data == "enter_token")
async def request_token(callback: CallbackQuery, state: FSMContext):
    """Token kiritishni so'rash"""
    await state.set_state(CreateBotStates.waiting_for_token)
    await callback.message.edit_text(
        "📝 <b>Bot tokenini kiriting:</b>\n\n"
        "⚠️ <b>Muhim:</b>\n"
        "• Tokenni faqat @BotFather dan oling\n"
        "• Hech kimga bermang - bu maxfiy ma'lumot!\n"
        "• Agar token buzilsa, /revoke buyrug'i bilan yangilang\n\n"
        "🔤 <b>Token kiriting:</b>",
        parse_mode="HTML"
    )
    await callback.answer()


@create_bot_router.callback_query(F.data == "token_help")
async def show_token_help(callback: CallbackQuery):
    """Token olish bo'yicha yordam"""
    help_text = (
        "❓ <b>Bot token qanday olish?</b>\n\n"
        "1️⃣ @BotFather ga /start yuboring\n"
        "2️⃣ /newbot buyrug'ini yuboring\n"
        "3️⃣ Bot uchun nom kiriting (masalan: 'Mening Botim')\n"
        "4️⃣ Bot uchun username kiriting (bot bilan tugashi kerak)\n"
        "   Masalan: mybot_bot, super_bot\n"
        "5️⃣ BotFather sizga token yuboradi\n\n"
        "⚠️ <b>Diqqat:</b>\n"
        "• Token - bu botingizning 'paroli'\n"
        "• Uni hech kimga bermang\n"
        "• Screenshot olayotganda tokenni yashiring\n\n"
        "🔗 <b>BotFather linki:</b> @BotFather"
    )

    await callback.message.edit_text(
        help_text,
        reply_markup=await create_bot_menu(),
        parse_mode="HTML"
    )
    await callback.answer()


@create_bot_router.message(StateFilter(CreateBotStates.waiting_for_token))
async def process_token(message: Message, state: FSMContext):
    """Kiritilgan tokenni qayta ishlash"""
    token = message.text.strip()

    # Token formatini tekshirish
    if not re.match(r'^\d+:[A-Za-z0-9_-]{35}$', token):
        await message.answer(
            "❌ <b>Noto'g'ri token formati!</b>\n\n"
            "Token quyidagi formatda bo'lishi kerak:\n"
            "<code>1234567890:AAHfn3yN8ZSN9JXOp4RgQOtHqEbWr-abc</code>\n\n"
            "Qaytadan urinib ko'ring yoki /start bosing:",
            parse_mode="HTML"
        )
        return

    # Token allaqachon ishlatilganmi tekshirish
    is_valid, error_message = await validate_bot_token(token)
    if not is_valid:
        await message.answer(
            f"❌ <b>Token xatoligi!</b>\n\n"
            f"{error_message}\n\n"
            "Boshqa token kiriting yoki /start bosing:",
            parse_mode="HTML"
        )
        return

    # Bot ma'lumotlarini Telegram'dan olish
    try:
        await message.answer("⏳ <b>Token tekshirilmoqda...</b>", parse_mode="HTML")

        bot_info = await get_bot_info_from_telegram(token)
        if not bot_info:
            await message.answer(
                "❌ <b>Token noto'g'ri yoki bot mavjud emas!</b>\n\n"
                "• Tokenni to'g'ri ko'chirganingizni tekshiring\n"
                "• Bot @BotFather orqali yaratilganligini tasdiqlang\n\n"
                "Qaytadan urinib ko'ring:",
                parse_mode="HTML"
            )
            return

        if not bot_info.get('is_bot', False):
            await message.answer(
                "❌ <b>Bu bot tokeni emas!</b>\n\n"
                "Faqat bot tokenlari qabul qilinadi.\n"
                "Qaytadan urinib ko'ring:",
                parse_mode="HTML"
            )
            return

        # Ma'lumotlarni state'ga saqlash
        await state.update_data(
            token=token,
            bot_username=bot_info['username'],
            bot_name=bot_info['first_name'],
            bot_id=bot_info['id']
        )

        await state.set_state(CreateBotStates.configuring_modules)

        await message.answer(
            f"✅ <b>Bot topildi!</b>\n\n"
            f"🤖 <b>Nomi:</b> {bot_info['first_name']}\n"
            f"📛 <b>Username:</b> @{bot_info['username']}\n"
            f"🆔 <b>ID:</b> {bot_info['id']}\n\n"
            f"<b>Endi bot uchun modullarni tanlang:</b>\n"
            f"Har bir modul botingizga alohida funksiya qo'shadi.",
            reply_markup=await bot_modules_menu(),
            parse_mode="HTML"
        )

    except Exception as e:
        logger.error(f"Error processing token {token}: {e}")
        await message.answer(
            "❌ <b>Texnik xatolik yuz berdi!</b>\n\n"
            "Iltimos, qaytadan urinib ko'ring yoki qo'llab-quvvatlash bilan bog'laning.",
            parse_mode="HTML"
        )


@create_bot_router.callback_query(F.data.startswith("toggle_"))
async def toggle_module(callback: CallbackQuery, state: FSMContext):
    """Modulni yoqish/o'chirish"""
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
    await callback.answer()


@create_bot_router.callback_query(F.data == "select_modules")
async def back_to_modules_selection(callback: CallbackQuery, state: FSMContext):
    """Modullar tanloviga qaytish"""
    data = await state.get_data()
    modules = data.get('modules', {})

    await callback.message.edit_text(
        f"🔧 <b>Bot: @{data.get('bot_username', 'unknown')}</b>\n\n"
        f"<b>Modullarni tanlang:</b>\n"
        f"Har bir modul botingizga alohida funksiya qo'shadi.\n\n"
        f"Yashil belgisi (✅) - modul yoqilgan\n"
        f"Kulrang belgisi (⬜) - modul o'chiq",
        reply_markup=await bot_modules_menu(selected_modules=modules),
        parse_mode="HTML"
    )
    await callback.answer()


@create_bot_router.callback_query(F.data == "save_bot_config")
async def save_bot_config(callback: CallbackQuery, state: FSMContext):
    """Bot konfiguratsiyasini saqlash"""
    data = await state.get_data()

    if not all(key in data for key in ['token', 'bot_username', 'bot_name']):
        await callback.message.edit_text(
            "❌ <b>Ma'lumotlar noto'liq!</b>\n\n"
            "Iltimos, qaytadan boshlang.",
            reply_markup=await create_bot_menu(),
            parse_mode="HTML"
        )
        await callback.answer()
        return

    try:
        await callback.message.edit_text(
            "⏳ <b>Bot yaratilmoqda...</b>\n\n"
            "• Bot ma'lumotlari saqlanmoqda\n"
            "• Webhook o'rnatilmoqda\n"
            "• Modullar konfiguratsiya qilinmoqda",
            parse_mode="HTML"
        )

        # Bot yaratish
        user = await get_user_by_uid(callback.from_user.id)
        if not user:
            await callback.message.edit_text(
                "❌ <b>Foydalanuvchi topilmadi!</b>\n\n"
                "Iltimos, /start bosib qaytadan ro'yxatdan o'ting.",
                parse_mode="HTML"
            )
            await callback.answer()
            return

        modules = data.get('modules', {})

        new_bot = await create_bot(
            owner_uid=callback.from_user.id,
            token=data['token'],
            username=data['bot_username'],
            name=data['bot_name'],
            modules=modules
        )

        if not new_bot:
            await callback.message.edit_text(
                "❌ <b>Bot yaratishda xatolik!</b>\n\n"
                "Iltimos, qaytadan urinib ko'ring.",
                reply_markup=await create_bot_menu(),
                parse_mode="HTML"
            )
            await callback.answer()
            return

        # Webhook o'rnatish
        webhook_url = settings_conf.WEBHOOK_URL.format(token=data['token'])
        webhook_success = await set_bot_webhook(data['token'], webhook_url)

        # Natija
        enabled_modules = []
        module_names = {
            'refs': '💸 Referral tizimi',
            'kino': '🎬 Kino bot',
            'music': '🎵 Musiqa bot',
            'download': '📥 Download bot',
            'chatgpt': '💬 ChatGPT',
            'leo': '❤️ Tanishuv',
            'horoscope': '🔮 Munajjimlik',
            'anon': '👤 Anonim chat',
            'sms': '📱 SMS yuborish'
        }

        for module, enabled in modules.items():
            if enabled:
                enabled_modules.append(module_names.get(module, module))

        modules_text = "\n".join(
            [f"  ✅ {module}" for module in enabled_modules]) if enabled_modules else "  Hech qanday modul yoqilmagan"
        webhook_status = "✅ Muvaffaqiyatli" if webhook_success else "⚠️ Xatolik (keyinroq qayta uriniladi)"

        await state.clear()

        await callback.message.edit_text(
            f"🎉 <b>Bot muvaffaqiyatli yaratildi!</b>\n\n"
            f"🤖 <b>Bot:</b> @{data['bot_username']}\n"
            f"📝 <b>Nomi:</b> {data['bot_name']}\n"
            f"🌐 <b>Webhook:</b> {webhook_status}\n\n"
            f"🔧 <b>Yoqilgan modullar:</b>\n{modules_text}\n\n"
            f"🚀 <b>Botni ishga tushiring:</b>\n"
            f"https://t.me/{data['bot_username']}\n\n"
            f"✨ Botingiz tayyor va foydalanishga tayyor!",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🤖 Mening botlarim", callback_data="my_bots")],
                [InlineKeyboardButton(text="➕ Yana bot yaratish", callback_data="create_bot")],
                [InlineKeyboardButton(text="🏠 Asosiy menyu", callback_data="back_to_main")]
            ]),
            parse_mode="HTML"
        )

    except Exception as e:
        logger.error(f"Error saving bot config: {e}")
        await callback.message.edit_text(
            f"❌ <b>Bot yaratishda xatolik!</b>\n\n"
            f"Xatolik: {str(e)}\n\n"
            f"Qaytadan urinib ko'ring.",
            reply_markup=await create_bot_menu(),
            parse_mode="HTML"
        )

    await callback.answer()
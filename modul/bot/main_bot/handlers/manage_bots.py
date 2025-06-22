# modul/bot/main_bot/handlers/manage_bots.py
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from modul.models import Bot
from ..keyboards.main_kb import create_bot_menu

manage_bots_router = Router()


@manage_bots_router.callback_query(F.data == "my_bots")
async def show_my_bots(callback: CallbackQuery):
    user_bots = Bot.objects.filter(owner__uid=callback.from_user.id)

    if not user_bots.exists():
        await callback.message.edit_text(
            "🤖 <b>Sizda hali botlar yo'q</b>\n\n"
            "Yangi bot yaratish uchun tugmani bosing:",
            reply_markup=await create_bot_menu(),
            parse_mode="HTML"
        )
        return

    text = "🤖 <b>Sizning botlaringiz:</b>\n\n"
    buttons = []

    for bot in user_bots:
        status = "🟢 Faol" if bot.is_active else "🔴 O'chiq"
        text += f"• @{bot.username} - {status}\n"

        buttons.append([InlineKeyboardButton(
            text=f"⚙️ @{bot.username}",
            callback_data=f"manage_bot:{bot.id}"
        )])

    buttons.append([InlineKeyboardButton(text="◀️ Orqaga", callback_data="back_to_main")])

    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode="HTML"
    )


@manage_bots_router.callback_query(F.data.startswith("manage_bot:"))
async def manage_specific_bot(callback: CallbackQuery):
    bot_id = int(callback.data.split(":")[1])
    bot = Bot.objects.get(id=bot_id, owner__uid=callback.from_user.id)

    # Enabled modules ro'yxati
    enabled_modules = []
    if bot.enable_refs: enabled_modules.append("💸 Referral")
    if bot.enable_kino: enabled_modules.append("🎬 Kino")
    if bot.enable_music: enabled_modules.append("🎵 Musiqa")
    if bot.enable_download: enabled_modules.append("📥 Download")
    if bot.enable_chatgpt: enabled_modules.append("💬 ChatGPT")
    if bot.enable_leo: enabled_modules.append("❤️ Tanishuv")
    if bot.enable_horoscope: enabled_modules.append("🔮 Munajjimlik")
    if bot.enable_anon: enabled_modules.append("👤 Anonim")
    if bot.enable_sms: enabled_modules.append("📱 SMS")

    modules_text = "\n".join(
        [f"  • {module}" for module in enabled_modules]) if enabled_modules else "  Hech qanday modul yoqilmagan"

    text = f"⚙️ <b>Bot boshqaruvi</b>\n\n" \
           f"🤖 <b>Bot:</b> @{bot.username}\n" \
           f"📊 <b>Holati:</b> {'🟢 Faol' if bot.is_active else '🔴 Ochiq'}\n" \
           f"👥 <b>Foydalanuvchilar:</b> {bot.users_count or 0}\n\n" \
           f"🔧 <b>Faol modullar:</b>\n{modules_text}\n\n" \
           f"🔗 <b>Bot linki:</b> https://t.me/{bot.username}"

    buttons = [
        [InlineKeyboardButton(
            text="🔄 Modullarni tahrirlash",
            callback_data=f"edit_modules:{bot_id}"
        )],
        [InlineKeyboardButton(
            text="📊 Statistika",
            callback_data=f"bot_stats:{bot_id}"
        )],
        [InlineKeyboardButton(
            text="⚙️ Sozlamalar",
            callback_data=f"bot_settings:{bot_id}"
        )],
        [InlineKeyboardButton(
            text="🔴 Botni o'chirish" if bot.is_active else "🟢 Botni yoqish",
            callback_data=f"toggle_bot:{bot_id}"
        )],
        [InlineKeyboardButton(text="◀️ Orqaga", callback_data="my_bots")]
    ]

    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode="HTML"
    )
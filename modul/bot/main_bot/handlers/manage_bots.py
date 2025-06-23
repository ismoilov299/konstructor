# modul/bot/main_bot/handlers/manage_bots.py
"""
Botlarni boshqarish handlerlari
"""

import logging
from datetime import datetime, timedelta
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from asgiref.sync import sync_to_async

from modul.bot.main_bot.services.user_service import (
    get_user_bots, get_bot_statistics, toggle_bot_status,
    update_bot_modules, delete_bot
)
from modul.bot.main_bot.states import ManageBotStates

logger = logging.getLogger(__name__)

manage_bots_router = Router()


# Keyboard funksiyalari
async def bot_list_keyboard(user_bots):
    """Bot ro'yxati klaviaturasi"""
    buttons = []

    for bot in user_bots:
        status = "🟢" if bot.get('bot_enable', False) else "🔴"
        modules_count = sum([
            bot.get('enable_refs', False),
            bot.get('enable_kino', False),
            bot.get('enable_music', False),
            bot.get('enable_download', False),
            bot.get('enable_chatgpt', False),
            bot.get('enable_leo', False),
            bot.get('enable_horoscope', False),
            bot.get('enable_anon', False),
            bot.get('enable_sms', False)
        ])

        button_text = f"{status} @{bot['username']} ({modules_count} modul)"
        buttons.append([InlineKeyboardButton(
            text=button_text,
            callback_data=f"manage_bot:{bot['id']}"
        )])

    # Qo'shimcha tugmalar
    buttons.append([InlineKeyboardButton(text="➕ Yangi bot yaratish", callback_data="create_bot")])
    buttons.append([InlineKeyboardButton(text="📊 Umumiy statistika", callback_data="overall_stats")])
    buttons.append([InlineKeyboardButton(text="◀️ Orqaga", callback_data="back_to_main")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


async def bot_management_keyboard(bot_id, is_active=True):
    """Bot boshqaruv klaviaturasi"""
    buttons = [
        [InlineKeyboardButton(text="📊 Statistika", callback_data=f"bot_stats:{bot_id}")],
        [InlineKeyboardButton(text="🔧 Modullar", callback_data=f"edit_modules:{bot_id}")],
        [InlineKeyboardButton(text="⚙️ Sozlamalar", callback_data=f"bot_settings:{bot_id}")],
        [
            InlineKeyboardButton(
                text="🔴 O'chirish" if is_active else "🟢 Yoqish",
                callback_data=f"toggle_bot:{bot_id}"
            ),
            InlineKeyboardButton(
                text="🗑️ O'chib tashlash",
                callback_data=f"delete_bot:{bot_id}"
            )
        ],
        [InlineKeyboardButton(text="◀️ Botlarim", callback_data="my_bots")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


async def bot_modules_edit_keyboard(bot_id, current_modules):
    """Bot modullarini tahrirlash klaviaturasi"""
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
        icon = "✅" if current_modules.get(f'enable_{module_key}', False) else "⬜"
        text = f"{icon} {module_name}"
        buttons.append([InlineKeyboardButton(
            text=text,
            callback_data=f"toggle_module:{bot_id}:{module_key}"
        )])

    buttons.append([InlineKeyboardButton(text="💾 Saqlash", callback_data=f"save_modules:{bot_id}")])
    buttons.append([InlineKeyboardButton(text="◀️ Orqaga", callback_data=f"manage_bot:{bot_id}")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


async def confirm_delete_keyboard(bot_id):
    """Bot o'chirishni tasdiqlash klaviaturasi"""
    buttons = [
        [
            InlineKeyboardButton(text="✅ Ha, o'chiring", callback_data=f"confirm_delete:{bot_id}"),
            InlineKeyboardButton(text="❌ Yo'q, bekor qiling", callback_data=f"manage_bot:{bot_id}")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# Handler'lar
@manage_bots_router.callback_query(F.data == "my_bots")
async def show_my_bots(callback: CallbackQuery):
    """Foydalanuvchi botlarini ko'rsatish"""
    try:
        user_bots = await get_user_bots(callback.from_user.id)

        if not user_bots:
            await callback.message.edit_text(
                "🤖 <b>Sizda hali botlar yo'q</b>\n\n"
                "🚀 <b>Birinchi botingizni yarating!</b>\n"
                "Bot yaratish juda oson:\n"
                "• @BotFather dan token oling\n"
                "• Kerakli modullarni tanlang\n"
                "• 2-3 daqiqada tayyor!\n\n"
                "💡 <b>9 ta professional modul mavjud:</b>\n"
                "💸 Referral, 🎬 Kino, 🎵 Musiqa, 📥 Download,\n"
                "💬 ChatGPT, ❤️ Tanishuv, 🔮 Munajjimlik,\n"
                "👤 Anonim chat, 📱 SMS",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="➕ Birinchi botni yaratish", callback_data="create_bot")],
                    [InlineKeyboardButton(text="❓ Yordam", callback_data="help")],
                    [InlineKeyboardButton(text="◀️ Orqaga", callback_data="back_to_main")]
                ]),
                parse_mode="HTML"
            )
            await callback.answer()
            return

        # Botlar statistikasi
        total_bots = len(user_bots)
        active_bots = sum(1 for bot in user_bots if bot.get('bot_enable', False))
        total_modules = sum(
            sum([
                bot.get('enable_refs', False),
                bot.get('enable_kino', False),
                bot.get('enable_music', False),
                bot.get('enable_download', False),
                bot.get('enable_chatgpt', False),
                bot.get('enable_leo', False),
                bot.get('enable_horoscope', False),
                bot.get('enable_anon', False),
                bot.get('enable_sms', False)
            ]) for bot in user_bots
        )

        text = (
            f"🤖 <b>Sizning botlaringiz</b>\n\n"
            f"📊 <b>Umumiy ma'lumot:</b>\n"
            f"• Jami botlar: {total_bots}\n"
            f"• Faol botlar: {active_bots}\n"
            f"• Jami modullar: {total_modules}\n\n"
            f"📋 <b>Botlar ro'yxati:</b>\n"
            f"Boshqarish uchun bot ustiga bosing ↓"
        )

        await callback.message.edit_text(
            text,
            reply_markup=await bot_list_keyboard(user_bots),
            parse_mode="HTML"
        )

    except Exception as e:
        logger.error(f"Error showing user bots for {callback.from_user.id}: {e}")
        await callback.message.edit_text(
            "❌ <b>Botlarni yuklashda xatolik</b>\n\n"
            "Bu vaqtincha texnik muammo bo'lishi mumkin.\n"
            "Iltimos, qaytadan urinib ko'ring.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Qayta urinish", callback_data="my_bots")],
                [InlineKeyboardButton(text="◀️ Orqaga", callback_data="back_to_main")]
            ]),
            parse_mode="HTML"
        )

    await callback.answer()


@manage_bots_router.callback_query(F.data.startswith("manage_bot:"))
async def manage_specific_bot(callback: CallbackQuery):
    """Aniq botni boshqarish"""
    try:
        bot_id = int(callback.data.split(":")[1])
        bot_stats = await get_bot_statistics(bot_id)

        if not bot_stats:
            await callback.message.edit_text(
                "❌ <b>Bot topilmadi</b>\n\n"
                "Bu bot sizga tegishli emas yoki o'chirilgan bo'lishi mumkin.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="◀️ Botlarim", callback_data="my_bots")]
                ]),
                parse_mode="HTML"
            )
            await callback.answer()
            return

        # Enabled modules ro'yxati
        enabled_modules = []
        module_names = {
            'enable_refs': '💸 Referral',
            'enable_kino': '🎬 Kino',
            'enable_music': '🎵 Musiqa',
            'enable_download': '📥 Download',
            'enable_chatgpt': '💬 ChatGPT',
            'enable_leo': '❤️ Tanishuv',
            'enable_horoscope': '🔮 Munajjimlik',
            'enable_anon': '👤 Anonim',
            'enable_sms': '📱 SMS'
        }

        for key, name in module_names.items():
            if bot_stats.get(key, False):
                enabled_modules.append(name)

        modules_text = ", ".join(enabled_modules) if enabled_modules else "Hech qanday modul yoqilmagan"

        # Activity status
        activity_icon = "🟢" if bot_stats['is_active'] else "🔴"
        activity_text = "Faol" if bot_stats['is_active'] else "O'chiq"

        # Users growth calculation
        growth_text = ""
        if bot_stats['new_users'] > 0:
            growth_text = f"📈 +{bot_stats['new_users']} (24 soat)"

        text = (
            f"⚙️ <b>Bot boshqaruvi</b>\n\n"
            f"🤖 <b>@{bot_stats['bot_username']}</b>\n"
            f"{activity_icon} <b>Holat:</b> {activity_text}\n\n"
            f"👥 <b>Foydalanuvchilar:</b>\n"
            f"• Jami: {bot_stats['total_users']}\n"
            f"• Faol (7 kun): {bot_stats['active_users']}\n"
            f"• Yangi (24 soat): {bot_stats['new_users']}\n\n"
            f"🔧 <b>Modullar:</b>\n"
            f"{modules_text}\n\n"
            f"🔗 <b>Havola:</b> https://t.me/{bot_stats['bot_username']}\n\n"
            f"Kerakli amalni tanlang:"
        )

        await callback.message.edit_text(
            text,
            reply_markup=await bot_management_keyboard(bot_id, bot_stats['is_active']),
            parse_mode="HTML"
        )

    except Exception as e:
        logger.error(f"Error managing bot for {callback.from_user.id}: {e}")
        await callback.message.edit_text(
            "❌ <b>Bot ma'lumotlarini yuklashda xatolik</b>\n\n"
            "Iltimos, qaytadan urinib ko'ring.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Botlarim", callback_data="my_bots")]
            ]),
            parse_mode="HTML"
        )

    await callback.answer()


@manage_bots_router.callback_query(F.data.startswith("bot_stats:"))
async def show_bot_detailed_stats(callback: CallbackQuery):
    """Bot batafsil statistikasi"""
    try:
        bot_id = int(callback.data.split(":")[1])
        bot_stats = await get_bot_statistics(bot_id)

        if not bot_stats:
            await callback.answer("❌ Bot topilmadi!", show_alert=True)
            return

        # Growth calculation
        total_users = bot_stats['total_users']
        new_users = bot_stats['new_users']
        active_users = bot_stats['active_users']

        # Activity percentage
        activity_percentage = (active_users / total_users * 100) if total_users > 0 else 0

        # Status
        status_icon = "🟢" if bot_stats['is_active'] else "🔴"
        status_text = "Aktiv" if bot_stats['is_active'] else "Nofaol"

        text = (
            f"📊 <b>@{bot_stats['bot_username']} statistikasi</b>\n\n"
            f"{status_icon} <b>Holat:</b> {status_text}\n\n"
            f"👥 <b>Foydalanuvchilar:</b>\n"
            f"• Jami: {total_users}\n"
            f"• Faol (7 kun): {active_users} ({activity_percentage:.1f}%)\n"
            f"• Yangi (24 soat): {new_users}\n\n"
            f"📈 <b>Aktivlik ko'rsatkichi:</b>\n"
            f"{'▓' * int(activity_percentage // 10)}{'░' * (10 - int(activity_percentage // 10))} {activity_percentage:.1f}%\n\n"
            f"🔧 <b>Yoqilgan modullar:</b>\n"
        )

        # Module statistics
        module_names = {
            'enable_refs': '💸 Referral tizimi',
            'enable_kino': '🎬 Kino bot',
            'enable_music': '🎵 Musiqa bot',
            'enable_download': '📥 Download bot',
            'enable_chatgpt': '💬 ChatGPT',
            'enable_leo': '❤️ Tanishuv',
            'enable_horoscope': '🔮 Munajjimlik',
            'enable_anon': '👤 Anonim chat',
            'enable_sms': '📱 SMS yuborish'
        }

        enabled_count = 0
        for key, name in module_names.items():
            if bot_stats.get(key, False):
                text += f"• ✅ {name}\n"
                enabled_count += 1

        if enabled_count == 0:
            text += "• ❌ Hech qanday modul yoqilmagan\n"

        text += f"\n📅 <b>Oxirgi yangilanish:</b> {datetime.now().strftime('%d.%m.%Y %H:%M')}"

        await callback.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Yangilash", callback_data=f"bot_stats:{bot_id}")],
                [InlineKeyboardButton(text="📈 Grafik ko'rish", callback_data=f"bot_chart:{bot_id}")],
                [InlineKeyboardButton(text="◀️ Orqaga", callback_data=f"manage_bot:{bot_id}")]
            ]),
            parse_mode="HTML"
        )

    except Exception as e:
        logger.error(f"Error showing bot stats: {e}")
        await callback.answer("❌ Statistikani yuklashda xatolik!", show_alert=True)


@manage_bots_router.callback_query(F.data.startswith("edit_modules:"))
async def edit_bot_modules(callback: CallbackQuery):
    """Bot modullarini tahrirlash"""
    try:
        bot_id = int(callback.data.split(":")[1])
        bot_stats = await get_bot_statistics(bot_id)

        if not bot_stats:
            await callback.answer("❌ Bot topilmadi!", show_alert=True)
            return

        text = (
            f"🔧 <b>@{bot_stats['bot_username']} modullarini tahrirlash</b>\n\n"
            f"Quyidagi modullarni yoqish/o'chirish mumkin:\n"
            f"Har bir modul botingizga alohida funksiya qo'shadi.\n\n"
            f"✅ Yoqilgan modullar\n"
            f"⬜ O'chiq modullar\n\n"
            f"O'zgartirish uchun modul ustiga bosing:"
        )

        await callback.message.edit_text(
            text,
            reply_markup=await bot_modules_edit_keyboard(bot_id, bot_stats),
            parse_mode="HTML"
        )

    except Exception as e:
        logger.error(f"Error editing bot modules: {e}")
        await callback.answer("❌ Xatolik yuz berdi!", show_alert=True)


@manage_bots_router.callback_query(F.data.startswith("toggle_module:"))
async def toggle_bot_module(callback: CallbackQuery):
    """Bot modulini yoqish/o'chirish"""
    try:
        _, bot_id, module_name = callback.data.split(":")
        bot_id = int(bot_id)

        # Get current modules
        bot_stats = await get_bot_statistics(bot_id)
        if not bot_stats:
            await callback.answer("❌ Bot topilmadi!", show_alert=True)
            return

        # Toggle the module
        current_value = bot_stats.get(f'enable_{module_name}', False)
        new_modules = {module_name: not current_value}

        success = await update_bot_modules(bot_id, callback.from_user.id, new_modules)

        if success:
            module_names = {
                'refs': 'Referral tizimi',
                'kino': 'Kino bot',
                'music': 'Musiqa bot',
                'download': 'Download bot',
                'chatgpt': 'ChatGPT',
                'leo': 'Tanishuv',
                'horoscope': 'Munajjimlik',
                'anon': 'Anonim chat',
                'sms': 'SMS'
            }

            module_display = module_names.get(module_name, module_name)
            status = "yoqildi" if not current_value else "o'chirildi"

            await callback.answer(f"✅ {module_display} {status}")

            # Refresh the modules edit page
            await edit_bot_modules(callback)
        else:
            await callback.answer("❌ Modul holatini o'zgartirishda xatolik!", show_alert=True)

    except Exception as e:
        logger.error(f"Error toggling bot module: {e}")
        await callback.answer("❌ Xatolik yuz berdi!", show_alert=True)


@manage_bots_router.callback_query(F.data.startswith("toggle_bot:"))
async def toggle_bot_status_handler(callback: CallbackQuery):
    """Bot holatini yoqish/o'chirish"""
    try:
        bot_id = int(callback.data.split(":")[1])
        new_status = await toggle_bot_status(bot_id, callback.from_user.id)

        if new_status is None:
            await callback.answer("❌ Bot topilmadi yoki sizga tegishli emas!", show_alert=True)
            return

        status_text = "yoqildi" if new_status else "o'chirildi"
        status_icon = "🟢" if new_status else "🔴"

        await callback.answer(f"{status_icon} Bot {status_text}!", show_alert=True)

        # Refresh the management page
        await manage_specific_bot(callback)

    except Exception as e:
        logger.error(f"Error toggling bot status: {e}")
        await callback.answer("❌ Xatolik yuz berdi!", show_alert=True)


@manage_bots_router.callback_query(F.data.startswith("delete_bot:"))
async def request_bot_deletion(callback: CallbackQuery):
    """Bot o'chirishni so'rash"""
    try:
        bot_id = int(callback.data.split(":")[1])
        bot_stats = await get_bot_statistics(bot_id)

        if not bot_stats:
            await callback.answer("❌ Bot topilmadi!", show_alert=True)
            return

        text = (
            f"⚠️ <b>Bot o'chirishni tasdiqlang</b>\n\n"
            f"🤖 <b>Bot:</b> @{bot_stats['bot_username']}\n"
            f"👥 <b>Foydalanuvchilar:</b> {bot_stats['total_users']}\n\n"
            f"❗ <b>Ogohlantirish:</b>\n"
            f"• Bot butunlay o'chiriladi\n"
            f"• Barcha ma'lumotlar yo'qoladi\n"
            f"• Bu amalni bekor qilib bo'lmaydi\n\n"
            f"Rostdan ham o'chirishni xohlaysizmi?"
        )

        await callback.message.edit_text(
            text,
            reply_markup=await confirm_delete_keyboard(bot_id),
            parse_mode="HTML"
        )

    except Exception as e:
        logger.error(f"Error requesting bot deletion: {e}")
        await callback.answer("❌ Xatolik yuz berdi!", show_alert=True)


@manage_bots_router.callback_query(F.data.startswith("confirm_delete:"))
async def confirm_bot_deletion(callback: CallbackQuery):
    """Bot o'chirishni tasdiqlash"""
    try:
        bot_id = int(callback.data.split(":")[1])

        deleted_username = await delete_bot(bot_id, callback.from_user.id)

        if deleted_username:
            await callback.message.edit_text(
                f"✅ <b>Bot muvaffaqiyatli o'chirildi</b>\n\n"
                f"🤖 <b>O'chirilgan bot:</b> @{deleted_username}\n\n"
                f"Barcha ma'lumotlar tozalandi.\n"
                f"Agar kerak bo'lsa, yangi bot yaratishingiz mumkin.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="➕ Yangi bot yaratish", callback_data="create_bot")],
                    [InlineKeyboardButton(text="🤖 Botlarim", callback_data="my_bots")],
                    [InlineKeyboardButton(text="🏠 Asosiy menyu", callback_data="back_to_main")]
                ]),
                parse_mode="HTML"
            )

            logger.info(f"Bot deleted: @{deleted_username} by user {callback.from_user.id}")
        else:
            await callback.answer("❌ Bot o'chirishda xatolik yuz berdi!", show_alert=True)

    except Exception as e:
        logger.error(f"Error confirming bot deletion: {e}")
        await callback.answer("❌ Xatolik yuz berdi!", show_alert=True)


# Placeholder handlers
@manage_bots_router.callback_query(F.data.startswith("bot_settings:"))
async def bot_settings_placeholder(callback: CallbackQuery):
    """Bot sozlamalari (placeholder)"""
    await callback.answer("⚠️ Bu funksiya hali ishlab chiqilmoqda...", show_alert=True)


@manage_bots_router.callback_query(F.data.startswith("bot_chart:"))
async def bot_chart_placeholder(callback: CallbackQuery):
    """Bot grafik ko'rish (placeholder)"""
    await callback.answer("⚠️ Bu funksiya hali ishlab chiqilmoqda...", show_alert=True)


@manage_bots_router.callback_query(F.data == "overall_stats")
async def overall_stats_placeholder(callback: CallbackQuery):
    """Umumiy statistika (placeholder)"""
    await callback.answer("⚠️ Bu funksiya hali ishlab chiqilmoqda...", show_alert=True)
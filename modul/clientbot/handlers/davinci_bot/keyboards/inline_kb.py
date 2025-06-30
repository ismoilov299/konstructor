# modul/clientbot/handlers/davinci_bot/keyboards/inline_kb.py

from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


async def sex_keyboard():
    """Jins tanlash klaviaturasi"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🙎‍♂️ Я парень", callback_data="davinci_anketSex_1_anketAge"),
        InlineKeyboardButton(text="🙍‍♀️ Я девушка", callback_data="davinci_anketSex_2_anketAge")
    )
    return builder.as_markup()


async def age_ranges_keyboard():
    """Yosh oralig'i tanlash klaviaturasi"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text='16-20', callback_data="davinci_anketAge2_16-20_anketSearch"),
        InlineKeyboardButton(text='21-30', callback_data="davinci_anketAge2_21-30_anketSearch"),
    )
    builder.row(
        InlineKeyboardButton(text='31-50', callback_data="davinci_anketAge2_31-50_anketSearch"),
        InlineKeyboardButton(text='51-80', callback_data="davinci_anketAge2_51-80_anketSearch"),
    )
    builder.row(
        InlineKeyboardButton(text='81-99', callback_data="davinci_anketAge2_81-99_anketSearch")
    )
    return builder.as_markup()


async def age_specific_keyboard(age_range, next_page):
    """Aniq yosh tanlash klaviaturasi"""
    builder = InlineKeyboardBuilder()
    age_list = age_range.split('-')

    buttons = []
    for i in range(int(age_list[0]), int(age_list[1]) + 1):
        buttons.append(InlineKeyboardButton(
            text=str(i),
            callback_data=f"davinci_anketAge3_{i}_{next_page}"
        ))

        if len(buttons) >= 6:
            builder.row(*buttons)
            buttons = []

    if buttons:
        builder.row(*buttons)

    return builder.as_markup()


async def search_keyboard():
    """Qidirish parametrlari klaviaturasi"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🙎‍♂️ Парни", callback_data="davinci_anketSearch_1_anketName"),
        InlineKeyboardButton(text="Всех", callback_data="davinci_anketSearch_3_anketName")
    )
    builder.row(
        InlineKeyboardButton(text="🙍‍♀️ Девушки", callback_data="davinci_anketSearch_2_anketName")
    )
    return builder.as_markup()


async def firstname_keyboard(first_name):
    """Telegram ismidan foydalanish klaviaturasi"""
    builder = InlineKeyboardBuilder()
    if first_name:
        builder.row(
            InlineKeyboardButton(
                text=first_name,
                callback_data="davinci_anketNameFirstname_anketCity"
            )
        )
    return builder.as_markup()


async def skip_keyboard(callback_data):
    """O'tkazib yuborish tugmasi"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="Пропустить", callback_data=callback_data)
    )
    return builder.as_markup()


async def save_gallery_keyboard(next_page):
    """Gallereyani saqlash klaviaturasi"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="Это все, сохранить",
            callback_data=f"davinci_GallarySave_{next_page}"
        )
    )
    return builder.as_markup()


async def anket_finish_keyboard():
    """Anketa tugallash klaviaturasi"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="Да", callback_data="davinci_go"),
        InlineKeyboardButton(text="Изменить анкету", callback_data="davinci_account")
    )
    return builder.as_markup()


async def account_edit_keyboard():
    """Anketani tahrirlash klaviaturasi"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="Изменить имя", callback_data="davinci_editName"),
        InlineKeyboardButton(text="Изменить пол", callback_data="davinci_editSex")
    )
    builder.row(
        InlineKeyboardButton(text="Изменить возраст", callback_data="davinci_editAge"),
        InlineKeyboardButton(text='Изменить "о себе"', callback_data="davinci_editAboutMe")
    )
    builder.row(
        InlineKeyboardButton(text="Изменить фото", callback_data="davinci_editGallary"),
        InlineKeyboardButton(text="Изменить город", callback_data="davinci_editCity")
    )
    builder.row(
        InlineKeyboardButton(text="Изменить кого оценивать", callback_data="davinci_editSearch")
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Назад", callback_data="davinci_go")
    )
    return builder.as_markup()


async def rating_keyboard():
    """Baholash klaviaturasi"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="❤️", callback_data="davinci_ratePlus"),
        InlineKeyboardButton(text="💌/📹", callback_data="davinci_sendMes"),
        InlineKeyboardButton(text="⚠️", callback_data="davinci_rateComp"),
    )
    builder.row(
        InlineKeyboardButton(text="👎", callback_data="davinci_rateMinus"),
        InlineKeyboardButton(text="💤", callback_data="davinci_go")
    )
    return builder.as_markup()


async def couple_keyboard(user_id):
    """Juftlik klaviaturasi"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="⚠️ Пожаловаться",
            callback_data=f"davinci_complaint_{user_id}"
        )
    )
    return builder.as_markup()


async def complaint_keyboard(user_id):
    """Shikoyat klaviaturasi"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="🔞 Материал для взрослых",
            callback_data=f"davinci_complaintChoice_{user_id}_1"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="💰 Продажа товаров и услуг",
            callback_data=f"davinci_complaintChoice_{user_id}_2"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="😴 Не отвечает",
            callback_data=f"davinci_complaintChoice_{user_id}_3"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="🦨 Другое",
            callback_data=f"davinci_complaintChoice_{user_id}_4"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="✖️ Отмена",
            callback_data=f"davinci_complaintDel_{user_id}"
        )
    )
    return builder.as_markup()


async def cancel_keyboard():
    """Bekor qilish tugmasi"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="Отменить", callback_data="davinci_close")
    )
    return builder.as_markup()


async def back_keyboard(callback_data):
    """Orqaga tugmasi"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🔙 Назад", callback_data=callback_data)
    )
    return builder.as_markup()
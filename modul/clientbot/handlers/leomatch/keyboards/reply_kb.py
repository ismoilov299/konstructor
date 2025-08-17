from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def begin_registration():
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="Давай, начнем!", callback_data="start_registration"))
    builder.add(InlineKeyboardButton(text="Я не хочу никого искать", callback_data="dont_want_search"))
    return builder.as_markup()


def chooice_sex():
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="👨 Я парень", callback_data="sex_male"))
    builder.add(InlineKeyboardButton(text="👩 Я девушка", callback_data="sex_female"))
    builder.add(InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_registration"))
    return builder.as_markup()

def name_suggestion(full_name: str):
    """Ism taklif qilish"""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text=f"✅ {full_name}", callback_data=f"name_{full_name}"))
    builder.add(InlineKeyboardButton(text="✏️ Другое имя", callback_data="input_custom_name"))
    builder.add(InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_registration"))
    return builder.as_markup()


def about_me_options(has_existing: bool = False):
    """About me variantlari"""
    builder = InlineKeyboardBuilder()

    if has_existing:
        builder.add(InlineKeyboardButton(text="✅ Оставить текущее", callback_data="save_current_about"))
        builder.add(InlineKeyboardButton(text="✏️ Написать новое", callback_data="input_new_about"))
    else:
        builder.add(InlineKeyboardButton(text="✏️ Написать описание", callback_data="input_new_about"))

    builder.add(InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_registration"))
    return builder.as_markup()


def photo_options(has_existing: bool = False):
    """Photo variantlari"""
    builder = InlineKeyboardBuilder()

    if has_existing:
        builder.add(InlineKeyboardButton(text="✅ Оставить текущее", callback_data="save_current_photo"))
        builder.add(InlineKeyboardButton(text="📷 Загрузить новое", callback_data="upload_new_photo"))
    else:
        builder.add(InlineKeyboardButton(text="📷 Загрузить фото/видео", callback_data="upload_new_photo"))

    builder.add(InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_registration"))
    return builder.as_markup()


def final_registration():
    """Yakuniy tasdiqlash"""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="✅ Всё верно", callback_data="final_yes"))
    builder.add(InlineKeyboardButton(text="✏️ Изменить", callback_data="final_edit"))
    builder.add(InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_registration"))
    return builder.as_markup()


def which_search():
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="👩 Девушку", callback_data="search_female"))
    builder.add(InlineKeyboardButton(text="👨 Парня", callback_data="search_male"))
    builder.add(InlineKeyboardButton(text="🤷 Мне всё равно", callback_data="search_any"))
    builder.add(InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_registration"))
    builder.adjust(1, 1, 1, 1)  # Har biri alohida qatorda
    return builder.as_markup()

def city_input():
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="✏️ Ввести город", callback_data="input_city"))
    builder.add(InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_registration"))
    return builder.as_markup()

def cancel():
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="Отменить", callback_data="cancel_action"))
    return builder.as_markup()


def yes_no():
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="Да", callback_data="answer_yes"))
    builder.add(InlineKeyboardButton(text="Нет", callback_data="answer_no"))
    builder.adjust(2)
    return builder.as_markup()


def get_numbers(count: int, add_exit: bool = False):
    builder = InlineKeyboardBuilder()

    for x in range(count):
        builder.add(InlineKeyboardButton(text=f"{x + 1}", callback_data=f"number_{x + 1}"))

    if add_exit:
        builder.add(InlineKeyboardButton(text="Выйти", callback_data="exit_numbers"))

    if count <= 5:
        builder.adjust(count)
    else:
        builder.adjust(5)

    return builder.as_markup()



def save_current():
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="Оставить текущее", callback_data="save_current"))
    return builder.as_markup()






def save_current_about():
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="Оставить текущее", callback_data="save_current_about"))
    return builder.as_markup()

def save_current_photo():
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="Оставить текущее", callback_data="save_current_photo"))
    return builder.as_markup()



def registration_menu():
    """Registratsiya menyusi"""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="🚀 Начать регистрацию", callback_data="start_registration"))
    builder.add(InlineKeyboardButton(text="❌ Отказаться", callback_data="refuse_registration"))
    return builder.as_markup()


def confirm_data():
    """Ma'lumotlarni tasdiqlash"""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="✅ Всё верно", callback_data="confirm_data"))
    builder.add(InlineKeyboardButton(text="✏️ Изменить", callback_data="edit_data"))
    return builder.as_markup()


# Qo'shimcha utility function'lar
def create_inline_keyboard(buttons_data: list) -> InlineKeyboardMarkup:


    builder = InlineKeyboardBuilder()
    for text, callback_data in buttons_data:
        builder.add(InlineKeyboardButton(text=text, callback_data=callback_data))
    return builder.as_markup()


def create_numbered_keyboard(items: list, prefix: str = "item") -> InlineKeyboardMarkup:

    builder = InlineKeyboardBuilder()
    for i, item in enumerate(items, 1):
        builder.add(InlineKeyboardButton(text=f"{i}. {item}", callback_data=f"{prefix}_{i}"))
    return builder.as_markup()

def text_input_with_cancel():
    """Text kiritish uchun bekor qilish tugmasi"""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_registration"))
    return builder.as_markup()


def progress_keyboard(step: int, total_steps: int = 6):
    """Progress ko'rsatish uchun"""
    progress = "●" * step + "○" * (total_steps - step)
    return f"Шаг {step}/{total_steps} {progress}"
from aiogram.types import KeyboardButton, ReplyKeyboardRemove, ReplyKeyboardMarkup
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from aiogram.utils.i18n import gettext as _


def main_menu_kb():
    reply_kb_main = ReplyKeyboardBuilder()
    reply_kb_main.add(KeyboardButton(text=_("Изменить анкету")))
    reply_kb_main.add(KeyboardButton(text=_("Получить реферальный код")))
    reply_kb_main.add(KeyboardButton(text=_("Найти поблизости")))
    reply_kb_main.add(KeyboardButton(text=_("Топ 100 девушек")))
    reply_kb_main.add(KeyboardButton(text=_("Топ 100 парней")))
    reply_kb_main.add(KeyboardButton(text=_("Найти пользователя")))
    reply_kb_main.add(KeyboardButton(text=_("Профиль")))
    reply_kb_main.add(KeyboardButton(text=_("Верификация")))
    reply_kb_main.add(KeyboardButton(text=_("Мои подарки")))
    return reply_kb_main.as_markup(resize_keyboard=True)

def begin_registration():
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text=_("Давай, начнем!")))
    builder.add(KeyboardButton(text=_("Я не хочу никого искать")))
    return builder.as_markup(resize_keyboard=True)


def chooice_sex():
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text=_("Я парень")))
    builder.add(KeyboardButton(text=_("Я девушка")))
    return builder.as_markup(resize_keyboard=True)


def final_registration():
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text=_("Да")))
    builder.add(KeyboardButton(text=_("Изменить анкету")))
    return builder.as_markup(resize_keyboard=True)


def which_search():
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text=_("Девушку")))
    builder.add(KeyboardButton(text=_("Парня")))
    builder.add(KeyboardButton(text=_("Мне всё равно")))
    return builder.as_markup(resize_keyboard=True)


def cancel():
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text=_("Отменить")))
    return builder.as_markup(resize_keyboard=True)


def yes_no():
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text=_("Да")), KeyboardButton(text=_("Нет")))
    return builder.as_markup(resize_keyboard=True)


def get_numbers(count: int, add_exit: bool = False):
    builder = ReplyKeyboardBuilder()
    builder.add(*[KeyboardButton(text=f"{x + 1}") for x in range(count)])
    if add_exit:
        builder.add(KeyboardButton(text=_("Выйти")))
    return builder.as_markup(resize_keyboard=True)


def remove():
    return ReplyKeyboardRemove()


def save_current():
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text=_("Оставить текущее")))
    return builder.as_markup(resize_keyboard=True)

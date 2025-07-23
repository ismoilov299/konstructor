from aiogram.types import KeyboardButton, ReplyKeyboardRemove, ReplyKeyboardMarkup
from aiogram.utils.keyboard import ReplyKeyboardBuilder
# from aiogram.utils.i18n import gettext as _


def main_menu_kb():
    reply_kb_main = ReplyKeyboardBuilder()
    reply_kb_main.add(KeyboardButton(text= ("Изменить анкету")))
    reply_kb_main.add(KeyboardButton(text= ("Получить реферальный код")))
    reply_kb_main.add(KeyboardButton(text= ("Найти поблизости")))
    reply_kb_main.add(KeyboardButton(text= ("Топ 100 девушек")))
    reply_kb_main.add(KeyboardButton(text= ("Топ 100 парней")))
    reply_kb_main.add(KeyboardButton(text= ("Найти пользователя")))
    reply_kb_main.add(KeyboardButton(text= ("Профиль")))
    reply_kb_main.add(KeyboardButton(text= ("Верификация")))
    reply_kb_main.add(KeyboardButton(text= ("Мои подарки")))
    return reply_kb_main.as_markup(resize_keyboard=True)

def begin_registration():
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text= ("Давай, начнем!")))
    builder.add(KeyboardButton(text= ("Я не хочу никого искать")))
    return builder.as_markup(resize_keyboard=True)


def chooice_sex():
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text= ("Я парень")))
    builder.add(KeyboardButton(text= ("Я девушка")))
    return builder.as_markup(resize_keyboard=True)


def final_registration():
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text= ("Да")))
    builder.add(KeyboardButton(text= ("Изменить анкету")))
    return builder.as_markup(resize_keyboard=True)


def which_search():
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text= ("Девушку")))
    builder.add(KeyboardButton(text= ("Парня")))
    builder.add(KeyboardButton(text= ("Мне всё равно")))
    return builder.as_markup(resize_keyboard=True)


def cancel():
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text= ("Отменить")))
    return builder.as_markup(resize_keyboard=True)


def yes_no():
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text= ("Да")), KeyboardButton(text= ("Нет")))
    return builder.as_markup(resize_keyboard=True)


def get_numbers(count: int, add_exit: bool = False):
    builder = ReplyKeyboardBuilder()
    builder.add(*[KeyboardButton(text=f"{x + 1}") for x in range(count)])
    if add_exit:
        builder.add(KeyboardButton(text= ("Выйти")))
    return builder.as_markup(resize_keyboard=True)


def remove():
    return ReplyKeyboardRemove()


def save_current():
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text= ("Оставить текущее")))
    return builder.as_markup(resize_keyboard=True)

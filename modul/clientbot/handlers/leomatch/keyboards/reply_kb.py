import logging

from aiogram import types
from aiogram.types import KeyboardButton, ReplyKeyboardRemove, ReplyKeyboardMarkup
from aiogram.utils.keyboard import ReplyKeyboardBuilder
logger = logging.getLogger(__name__)

def begin_registration() -> ReplyKeyboardMarkup:
    """Ro'yxatdan o'tishni boshlash tugmalari"""
    kb = ReplyKeyboardBuilder()
    kb.button(text="Давай, начнем!")
    kb.button(text="Я не хочу никого искать")
    return kb.as_markup(
        resize_keyboard=True,
        one_time_keyboard=True,
        selective=True,
        is_persistent=True
    )

def cancel():
    kb = ReplyKeyboardBuilder()
    kb.button(text="Отменить")
    return kb.as_markup(resize_keyboard=True, one_time_keyboard=True)

def chooice_sex() -> ReplyKeyboardMarkup:
    """Jins tanlash tugmalari"""
    builder = ReplyKeyboardBuilder()
    builder.button(text="Мужской")
    builder.button(text="Женский")
    builder.adjust(2)
    return builder.as_markup(
        resize_keyboard=True,
        selective=True
    )




def final_registration():
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text=("Да")))
    builder.add(KeyboardButton(text=("Изменить анкету")))
    return builder.as_markup(resize_keyboard=True)


def which_search() -> ReplyKeyboardMarkup:

    builder = ReplyKeyboardBuilder()
    builder.button(text="Мужской")
    builder.button(text="Женский")
    builder.button(text="Все равно")
    builder.adjust(2, 1)
    return builder.as_markup(
        resize_keyboard=True,
        selective=True
    )



def yes_no():
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text=("Да")), KeyboardButton(text=("Нет")))
    return builder.as_markup(resize_keyboard=True)



def get_numbers(count: int, add_exit: bool = False, one_time_keyboard: bool = True) -> types.ReplyKeyboardMarkup:
    """
    Raqamli tugmalar klaviaturasini yaratish
    :param count: Tugmalar soni
    :param add_exit: "Выйти" tugmasini qo'shish
    :param one_time_keyboard: Bir martalik klaviatura
    :return: ReplyKeyboardMarkup
    """
    try:
        builder = ReplyKeyboardBuilder()

        # Raqamli tugmalarni qo'shamiz
        for x in range(count):
            builder.button(text=f"{x + 1}")

        # "Выйти" tugmasini qo'shish
        if add_exit:
            builder.button(text="Выйти")

        # Tugmalarni joylashtiramiz
        if count <= 3:
            # 3 tagacha tugma bir qatorda
            builder.adjust(count)
        else:
            # 4 ta va undan ko'p tugmalar 2 qatorga
            first_row = count // 2
            second_row = count - first_row
            builder.adjust(first_row, second_row)

        # Agar "Выйти" bo'lsa, alohida qatorga
        if add_exit:
            builder.adjust(*([min(3, count)] * (count // 3 + bool(count % 3)) + [1]))

        return builder.as_markup(
            resize_keyboard=True,
            one_time_keyboard=one_time_keyboard,
            selective=True
        )

    except Exception as e:
        logger.error(f"Error creating number keyboard: {e}", exc_info=True)
        # Xatolik bo'lsa default klaviatura
        builder = ReplyKeyboardBuilder()
        builder.button(text="1")
        return builder.as_markup(resize_keyboard=True)


def remove():
    return ReplyKeyboardRemove()


def save_current():
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text=("Оставить текущее")))
    return builder.as_markup(resize_keyboard=True)

from aiogram.types import InlineKeyboardButton, KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

from modul.clientbot.handlers.chat_gpt_bot.shortcuts import get_all_names


def first_buttons():
    builder = InlineKeyboardBuilder()
    builder.button(text='☁ Чат с GPT-4', callback_data='chat_4')
    builder.button(text='☁ Чат с GPT-3.5', callback_data='chat_3')
    builder.button(text='💰 Баланс', callback_data='show_balance')
    builder.button(text='💸Заработать', callback_data='ref')
    builder.adjust(2, 1, 1)
    return builder.as_markup()

def balance_menu():
    builder = InlineKeyboardBuilder()
    builder.button(text='💳 Пополнить баланс', callback_data='top_up_balance')
    builder.button(text='📝 Меню', callback_data='back_on_menu')
    builder.adjust(1, 1)
    return builder.as_markup()

def top_up_options():
    builder = InlineKeyboardBuilder()
    builder.button(text='💎 10 Stars = 50₽', callback_data='topup_10_stars')
    builder.button(text='💎 25 Stars = 150₽', callback_data='topup_25_stars')
    builder.button(text='💎 50 Stars = 350₽', callback_data='topup_50_stars')
    builder.button(text='💎 100 Stars = 750₽', callback_data='topup_100_stars')
    builder.button(text='💎 200 Stars = 1500₽', callback_data='topup_200_stars')
    builder.button(text='🔙 Назад', callback_data='show_balance')
    builder.adjust(1, 1, 1, 1, 1, 1)
    return builder.as_markup()


def ref():
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text='💸Заработать')]], resize_keyboard=True)

def choice_1_3_5():
    builder = InlineKeyboardBuilder()
    builder.button(text='Без контекста', callback_data='not')
    builder.button(text='С контекстом', callback_data='with')
    builder.button(text='Назад', callback_data='back_on_menu')
    builder.adjust(2, 1)
    return builder.as_markup()


def choice_1_4():
    builder = InlineKeyboardBuilder()
    builder.button(text='Без контекста', callback_data='not4')
    builder.button(text='С контекстом', callback_data='with4')
    builder.button(text='Назад', callback_data='back_on_menu')
    builder.adjust(2, 1)
    return builder.as_markup()


def choice_2():
    builder = InlineKeyboardBuilder()
    builder.button(text='Попробовать', callback_data='test_photo')
    builder.button(text='Назад', callback_data='back_on_menu')
    return builder.as_markup()


def choice_3():
    builder = InlineKeyboardBuilder()
    builder.button(text='Начать диалог', callback_data='start_dialogue')
    builder.button(text='Назад', callback_data='back_on_menu')
    return builder.as_markup()


def choice_4():
    builder = InlineKeyboardBuilder()
    builder.button(text='alloy', callback_data='alloy')
    builder.button(text='echo', callback_data='echo')
    builder.button(text='nova', callback_data='nova')
    builder.button(text='fable', callback_data='fable')
    builder.button(text='shimmer', callback_data='shimmer')
    builder.button(text='Назад', callback_data='back_on_menu')
    builder.adjust(2, 2, 1, 1)
    return builder.as_markup()


def choice_5():
    builder = InlineKeyboardBuilder()
    builder.button(text='Попробовать', callback_data='try')
    builder.button(text='Назад', callback_data='back_on_menu')
    return builder.as_markup()




def again_gpt3():
    builder = InlineKeyboardBuilder()
    builder.button(text='📧Еще', callback_data='again_gpt3')
    builder.button(text='📝Меню', callback_data='back')
    return builder.as_markup()


def again_gpt4():
    builder = InlineKeyboardBuilder()
    builder.button(text='📧Еще', callback_data='again_gpt4')
    builder.button(text='📝Меню', callback_data='back')
    return builder.as_markup()


def again_voice():
    builder = InlineKeyboardBuilder()
    builder.button(text='🎙Еще', callback_data='again_voice')
    builder.button(text='📝Меню', callback_data='back')
    return builder.as_markup()


def settings():
    builder = InlineKeyboardBuilder()
    builder.button(text='📝Меню', callback_data='back_on_menu')
    return builder.as_markup()


def back():
    builder = InlineKeyboardBuilder()
    builder.button(text='📝Меню', callback_data='back')
    return builder.as_markup()


def get_all_user_bt():
    builder = ReplyKeyboardBuilder()
    try:
        people = get_all_names()
        for person in people:
            builder.button(text=str(person).strip("(),'"))
    except Exception as e:
        print(f'Exception - {str(e)}')
        builder.button(text='Людей пока что нету, не тыкай пиши')
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)





def back_in_faq():
    builder = InlineKeyboardBuilder()
    builder.button(text='🔙 Назад', callback_data='FAQ')
    return builder.as_markup()


def faqs():
    builder = InlineKeyboardBuilder()
    builder.button(text='🤖 Что умеет бот?', callback_data='what')
    builder.button(text='💲 Почему это платно?', callback_data='why')
    builder.button(text='💳 Как пополнить', callback_data='how')
    builder.button(text='🔙 Назад', callback_data='helper')
    return builder.as_markup()

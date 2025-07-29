from aiogram.types import InlineKeyboardButton, KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

from modul.clientbot.handlers.chat_gpt_bot.shortcuts import get_all_names


def first_buttons():
    builder = InlineKeyboardBuilder()
    builder.button(text='☁ Чат с GPT-4', callback_data='chat_4')
    builder.button(text='☁ Чат с GPT-3.5', callback_data='chat_3')
    # builder.button(text='🆘 Помощь', callback_data='helper')
    # builder.button(text='⚙️ Настройки', callback_data='settings')
    builder.button(text='💸Заработать', callback_data='ref')
    builder.adjust(2, 1, 1, 1, 1, 1, 2)
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


def help_bt():
    builder = InlineKeyboardBuilder()
    builder.button(text='❔ FAQ', callback_data='FAQ')
    builder.button(text='📄 Правила пользования', url="https://telegra.ph/Pravila-polzovaniya-botom-12-17")
    builder.button(text='🔙 Назад', callback_data='back')
    return builder.as_markup()


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

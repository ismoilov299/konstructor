import random
import os
import time
from aiogram import Bot, Dispatcher, types
from aiogram import F
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.types import FSInputFile, Message
from aiogram.utils.deep_linking import create_start_link
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
import asyncio
from modul.clientbot.handlers.chat_gpt_bot import buttons as bt
from modul.clientbot.handlers.chat_gpt_bot.all_openai import ChatGPT
from modul.clientbot.handlers.main import save_user
from modul.loader import client_bot_router
from modul.clientbot.handlers.chat_gpt_bot.states import AiState, AiAdminState, ChatGptFilter
from modul.clientbot.handlers.chat_gpt_bot.shortcuts import (get_all_names, get_all_ids,
                                                             get_info_db, get_user_balance_db,
                                                              default_checker, update_bc,
                                                             update_bc_name)

robot = ChatGPT()


def chat_gpt_bot_handlers():
    @client_bot_router.message(lambda message: message.text == "/adminpayamount")
    async def adminpayamount_cmd(message: types.Message, state: FSMContext):
        print("sad")
        await message.answer('Пришли токен')
        await state.set_state(AiAdminState.check_token_and_update)



from modul.clientbot.handlers.chat_gpt_bot.all_openai import ChatGPT
chatgpt = ChatGPT()
@client_bot_router.message(ChatGptFilter())
async def debug_all_handler(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    user_id = message.from_user.id

    print(f"🔍 MESSAGE DEBUG:")
    print(f"   User: {user_id}")
    print(f"   Text: {message.text}")
    print(f"   State: {current_state}")

    if current_state == 'waiting_for_gpt3':
        print(f"   🎯 GPT-3.5 aniqlandi!")
        await message.answer("⏳ Обрабатываю запрос...")

        try:
            # GPT-3.5 chaqiruvi (context=False)
            response = chatgpt.chat_gpt(
                user_id=user_id,
                message=message.text,
                gpt='gpt-3.5-turbo',
                context=False
            )

            if response:
                await message.answer(f"🤖 GPT-3.5:\n{response}",reply_markup=bt.first_buttons())
            else:
                await message.answer("❌ Произошла ошибка при обработке запроса")

        except Exception as e:
            print(f"   ❌ GPT-3 xatolik: {e}")
            await message.answer("❌ Произошла ошибка при обработке запроса")

        await state.clear()
        print(f"   ✅ State tozalandi!")
        return

    elif current_state == 'waiting_for_gpt3_context':
        print(f"   🎯 GPT-3.5 context aniqlandi!")
        await message.answer("⏳ Обрабатываю запрос с контекстом...")

        try:
            # GPT-3.5 chaqiruvi (context=True)
            response = chatgpt.chat_gpt(
                user_id=user_id,
                message=message.text,
                gpt='gpt-3.5-turbo',
                context=True
            )

            if response:
                await message.answer(f"🤖 GPT-3.5 (контекст):\n{response}")
            else:
                await message.answer("❌ Произошла ошибка при обработке запроса")

        except Exception as e:
            print(f"   ❌ GPT-3 context xatolik: {e}")
            await message.answer("❌ Произошла ошибка при обработке запроса")

        # await state.clear()
        # print(f"   ✅ State tozalandi!")
        return

    elif current_state == 'waiting_for_gpt4':
        print(f"   🎯 GPT-4 aniqlandi!")
        await message.answer("⏳ Обрабатываю запрос...")

        try:
            # GPT-4 chaqiruvi (context=False)
            response = chatgpt.chat_gpt(
                user_id=user_id,
                message=message.text,
                gpt='gpt-4o',
                context=False
            )

            if response:
                await message.answer(f"🤖 GPT-4:\n{response}"  , reply_markup=bt.first_buttons())
            else:
                await message.answer("❌ Произошла ошибка при обработке запроса")

        except Exception as e:
            print(f"   ❌ GPT-4 xatolik: {e}")
            await message.answer("❌ Произошла ошибка при обработке запроса")

        await state.clear()
        print(f"   ✅ State tozalandi!")
        return

    elif current_state == 'waiting_for_gpt4_context':
        print(f"   🎯 GPT-4 context aniqlandi!")
        await message.answer("⏳ Обрабатываю запрос с контекстом...")

        try:
            # GPT-4 chaqiruvi (context=True)
            response = chatgpt.chat_gpt(
                user_id=user_id,
                message=message.text,
                gpt='gpt-4o',
                context=True
            )

            if response:
                await message.answer(f"🤖 GPT-4 (контекст):\n{response}")
            else:
                await message.answer("❌ Произошла ошибка при обработке запроса")

        except Exception as e:
            print(f"   ❌ GPT-4 context xatolik: {e}")
            await message.answer("❌ Произошла ошибка при обработке запроса")

        # await state.clear()
        # print(f"   ✅ State tozalandi!")
        return

    print(f"   ⏭️ Keyingi handler...")

@client_bot_router.message(AiAdminState.check_token_and_update)
async def check_token_and_update(message: types.Message, state: FSMContext):
    if message.text == 'da98s74d5qw89a4dw6854a':
        await message.answer('Впишите id пользователя для пополнения или выбери его из кнопок',
                             reply_markup=bt.get_all_user_bt())
        await state.set_state(AiAdminState.check_user_to_update)
    else:
        await message.answer('Error')


@client_bot_router.message(AiAdminState.check_user_to_update)
async def check_user_to_update(message: types.Message, state: FSMContext):
    people = [str(i).strip("(),'") for i in await get_all_names()]
    ids = [str(i).strip("(),'") for i in await get_all_ids()]

    if message.text in people:
        await message.answer("Введите сумму для пополнения", reply_markup=types.ReplyKeyboardRemove())
        await state.set_state(AiAdminState.update_balance_state)
        await state.set_data(message.from_user.id, {"username": message.text})
    elif message.text in ids:
        await message.answer("Введите сумму для пополнения", reply_markup=types.ReplyKeyboardRemove())
        await state.set_state(AiAdminState.update_balance_state)
        await state.set_data(message.from_user.id, {"username": message.text})
    else:
        await message.answer("Error Find Buttons", reply_markup=types.ReplyKeyboardRemove())


@client_bot_router.message(AiAdminState.update_balance_state)
async def update_balance(message: types.Message, state: FSMContext):
    data = await state.get_data(message.from_user.id)
    if message.text:
        amount = message.text
        if "userid" in data:
            await update_bc(tg_id=data["userid"], sign='+', amount=amount)
        elif "username" in data:
            await update_bc_name(tg_id=data["username"], sign='+', amount=amount)
        await message.answer('Successfully updated')
    else:
        await message.answer('Error updating')


@client_bot_router.message(CommandStart())
async def tp_to_start(message: types.Message, bot: Bot, state: FSMContext):
    check_user = await default_checker(message.from_user.id)
    print(check_user, "check_user")
    if check_user is False:
        new_link = await create_start_link(message.bot, str(message.from_user.id), encode=True)
        link_for_db = new_link[new_link.index("=") + 1:]
        await save_user(u=message.from_user, bot=bot, link=link_for_db)
        await start_message(message)
    elif check_user is True:
        sent_message = await message.answer("Вы отправляетесь на старт")
        await asyncio.sleep(1)
        await message.delete()
        await start_message(message)
    else:
        await message.answer('Технический перерыв')


@client_bot_router.message(ChatGptFilter())
async def start_message(message: types.Message, state: FSMContext, bot: Bot):
    user_id = message.from_user.id
    if message.text == "/adminpayamount":
        await message.answer('Пришли токен')
        await state.set_state(AiAdminState.check_token_and_update)
        print(await state.get_state())
        return
    print(await state.get_state())
    try:
        result = await get_info_db(user_id)
        print(result)
        await message.answer(f'Привет {message.from_user.username}\nВаш баланс - {result[0][2]}',
                             reply_markup=bt.first_buttons())
    except:
        new_link = await create_start_link(message.bot, str(message.from_user.id), encode=True)
        link_for_db = new_link[new_link.index("=") + 1:]
        await save_user(u=message.from_user, bot=bot, link=link_for_db)
        result = await get_info_db(user_id)
        print(result)
        await message.answer(f'Привет {message.from_user.username}\nВаш баланс - {result[0][2]}',
                             reply_markup=bt.first_buttons())


@client_bot_router.message(StateFilter('waiting_for_gpt4'), ChatGptFilter())
async def test_gpt4_handler(message: Message, state: FSMContext):
    """Vaqtincha test handler"""
    print(f"🟢 GPT-4 handler triggered!")
    print(f"   Message: {message.text}")

    await message.answer("✅ Test: GPT-4 handler ishlayapti!")
    await state.clear()
    print(f"   State cleared!")


@client_bot_router.callback_query(F.data == "chat_4")
async def chat_4_callback(callback_query: types.CallbackQuery):
    await callback_query.message.edit_text(
        '🤖 GPT-4:\n\n'
        '📋 Используется самая последняя языковая модель GPT-4 Turbo.\n'
        '🔘 Принимает текст.\n'
        '🗯 Чат без контекста — не учитывает контекст, каждый ваш запрос как новый диалог.\n'
        '⚡️ 1 запрос = 3 ⭐\n'
        '💬 Чат с контекстом — каждый ответ с учетом контекста вашего диалога.\n'
        '⚡️ 1 запрос = 4 ⭐\n'
        '└ Выберите чат:',
        reply_markup=bt.choice_1_4()
    )


@client_bot_router.callback_query(F.data == "chat_3")
async def chat_3_callback(callback: types.CallbackQuery):
    await callback.message.edit_text(
        '🤖 GPT-3.5:\n\n'
        '📋 Используется самая экономически эффективная модель GPT-3.5 Turbo.\n'
        '🔘 Принимает текстовое сообщение.\n'
        '🗯 Чат без контекста — не учитывает контекст, каждый ваш запрос как новый диалог.\n'
        '⚡️ 1 запрос = 1 ⭐\n'
        '💬 Чат с контекстом — каждый ответ с учетом контекста вашего диалога.\n'
        '⚡️ 1 запрос = 2 ⭐',
        reply_markup=bt.choice_1_3_5()
    )


@client_bot_router.callback_query(F.data.in_(['not', 'with', 'not4', 'with4', 'again_gpt3', 'again_gpt4']))
async def chat_options_callback(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    user_balance = await get_user_balance_db(user_id)

    print(f"🔘 CALLBACK DEBUG:")
    print(f"   Data: {callback.data}")
    print(f"   User: {user_id}")
    print(f"   Balance: {user_balance}")

    if callback.data in ['not', 'again_gpt3'] and user_balance >= 1:
        await update_bc(tg_id=user_id, sign='-', amount=1)
        await callback.message.answer('Пришлите свой запрос:')
        await state.set_state('waiting_for_gpt3')
        print(f"   ✅ State set to: waiting_for_gpt3")

    elif callback.data == 'with' and user_balance >= 2:
        await update_bc(tg_id=user_id, sign='-', amount=2)
        await callback.message.answer('Пришлите свой запрос:\nДля выхода из чата используй /start /reset')
        await state.set_state('waiting_for_gpt3_context')
        print(f"   ✅ State set to: waiting_for_gpt3_context")

    elif callback.data in ['not4', 'again_gpt4'] and user_balance >= 3:
        await update_bc(tg_id=user_id, sign='-', amount=3)
        await callback.message.answer('Пришлите свой запрос:')
        await state.set_state('waiting_for_gpt4')
        print(f"   ✅ State set to: waiting_for_gpt4")

    elif callback.data == 'with4' and user_balance >= 4:
        await update_bc(tg_id=user_id, sign='-', amount=4)
        await callback.message.answer('Пришлите свой запрос:\nДля выхода из чата используй /start /reset')
        await state.set_state('waiting_for_gpt4_context')
        print(f"   ✅ State set to: waiting_for_gpt4_context")

    else:
        await callback.message.answer('Не хватает на балансе тыкай --> /start')
        print(f"   ❌ Insufficient balance or unknown callback")


@client_bot_router.callback_query(F.data.in_({"back", "back_on_menu"}))
async def back_callback(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    if callback.data == 'back':
        try:
            result = await get_info_db(callback.from_user.id)
            print(result)
            await callback.message.edit_text(f'Привет {callback.from_user.username}\nВаш баланс - {result[0][2]}',
                                             reply_markup=bt.first_buttons())
            await state.clear()
        except Exception as e:
            print(e)
            await start_message(callback.message, bot)
    elif callback.data == 'back_on_menu':
        try:
            await callback.message.edit_text(
                f'Привет {callback.from_user.first_name}',
                reply_markup=bt.first_buttons()
            )
            await state.clear()
        except Exception as e:
            await callback.message.edit_text(
                f'Привет {callback.from_user.first_name}',
                reply_markup=bt.first_buttons()
            )
            print(e)


@client_bot_router.callback_query(F.data.in_({"alloy", "echo", "nova", "fable", "shimmer"}))
async def voice_selection_callback(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    user_balance = await get_user_balance_db(user_id)
    if user_balance >= 3:
        await update_balance(tg_id=user_id, sign='-', amount=3)
        await callback.message.edit_text("Введите текст для озвучки:")
        await state.set_data({"voice": callback.data})
        await state.set_state('waiting_for_text_to_voice')
    else:
        await callback.message.answer('Не хватает на балансе тыкай --> /start')


@client_bot_router.callback_query(F.data == "settings")
async def settings_callback(callback: types.CallbackQuery):
    await callback.message.edit_text('Настройки', reply_markup=bt.settings())


@client_bot_router.callback_query(F.data == "helper")
async def helper_callback(callback: types.CallbackQuery):
    await callback.message.edit_text('ℹ️ Помощь:', reply_markup=bt.help_bt())


@client_bot_router.callback_query(F.data == "FAQ")
async def faq_callback(callback: types.CallbackQuery):
    await callback.message.edit_text('❔ Часто задаваемые вопросы', reply_markup=bt.faqs())


@client_bot_router.callback_query(F.data == "what")
async def what_bot_can_do_callback(callback: types.CallbackQuery):
    await callback.message.edit_text(
        '🤖 Что умеет бот?\n\n'
        'Бот умеет отвечать на любые вопросы (GPT-4 Turbo), генерировать '
        'изображения (DALL·E 3), озвучивать текст (TTS), '
        'превращать аудио в текст (Whisper) и многое другое.',
        reply_markup=bt.back_in_faq()
    )


@client_bot_router.callback_query(F.data == "ref")
async def ref_callback(callback: types.CallbackQuery):
    await callback.message.answer("Кнопка 💸Заработать", reply_markup=bt.ref())


@client_bot_router.callback_query(F.data == "why")
async def why_paid_callback(callback: types.CallbackQuery):
    await callback.message.edit_text(
        '💲 Почему это платно?\n\n'
        'Бот использует платные API на платформе OpenAI, '
        'которые необходимы для его работы.',
        reply_markup=bt.back_in_faq()
    )


@client_bot_router.callback_query(F.data == "how")
async def how_to_pay_callback(callback: types.CallbackQuery):
    await callback.message.edit_text(
        '💳 Как пополнить баланс?\n\n'
        'Информация обновляется',
        reply_markup=bt.back_in_faq()
    )


@client_bot_router.message(lambda message: message.text not in ['/start', '/reset'], ChatGptFilter())
async def handle_text_input(message: Message, state: FSMContext):
    current_state = await state.get_state()
    print(f"Current state: {current_state}")
    if current_state == 'waiting_for_gpt3':
        await gpt3(message, context=False)
    elif current_state == 'waiting_for_gpt3_context':
        await gpt3(message, context=True)
    elif current_state == 'waiting_for_gpt4':
        await gpt4(message, context=False)
    elif current_state == 'waiting_for_gpt4_context':
        await gpt4(message, context=True)
    await state.clear()


# ... (Similar callback handlers for other buttons)

@client_bot_router.message(AiState.gpt3, ChatGptFilter())
async def gpt3(message: Message, state: FSMContext):
    context_data = await state.get_data()
    context = context_data.get("context", False)
    await message.bot.send_chat_action(message.chat.id, 'typing')

    if not context:
        if message.text:
            gpt_answer = robot.chat_gpt(user_id=message.from_user.id, message=message.text)
            await message.answer(gpt_answer, parse_mode='Markdown', reply_markup=bt.again_gpt3())
        else:
            await message.answer('Я могу обрабатывать только текст ! /start')
    else:
        if message.text in ['/start', '/restart', '/reset']:
            await tp_to_start(message)
        elif message.text:
            gpt_answer = robot.chat_gpt(user_id=message.from_user.id, message=message.text, context=True)
            await message.answer(gpt_answer, parse_mode='Markdown')
        else:
            await message.answer('Я могу обрабатывать только текст ! /start')


@client_bot_router.message(AiState.gpt4, ChatGptFilter())
async def gpt4(message: Message, state: FSMContext):
    context_data = await state.get_data()
    context = context_data.get("context", False)

    await message.bot.send_chat_action(message.chat.id, 'typing')

    user_id = message.from_user.id

    if not context:
        print(
            f'GPT4 NO_CONTEXT user_id -- >{user_id}, first_name -- > {message.from_user.first_name}, user_name -- > @{message.from_user.username}')

        if message.text:
            gpt_answer = robot.chat_gpt(user_id=user_id, message=message.text, gpt="gpt-4-1106-preview")
            if gpt_answer:
                await message.answer(gpt_answer, parse_mode='Markdown', reply_markup=bt.again_gpt4())
            else:
                await message.answer('GPT4 Недоступен', parse_mode='Markdown', reply_markup=bt.again_gpt4())
        else:
            await message.answer('Я могу обрабатывать только текст ! /start')
    else:
        print(
            f'GPT4 CONTEXT user_id -- >{user_id}, first_name -- > {message.from_user.first_name}, user_name -- > @{message.from_user.username}')

        if message.text in ['/start', '/restart', '/reset']:
            await tp_to_start(message)
        elif message.text:
            gpt_answer = robot.chat_gpt(user_id=user_id, message=message.text, context=True, gpt="gpt-4-1106-preview")
            if gpt_answer:
                await message.answer(gpt_answer, parse_mode='Markdown')
                await state.set_state(AiState.gpt4)
            else:
                await message.answer('GPT4 Недоступен', parse_mode='Markdown')
        else:
            await message.answer('Я могу обрабатывать только текст ! /start')

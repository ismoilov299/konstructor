# modul/bot/main_bot/handlers/create_bot.py (русская версия)
"""
Main bot orqali yangi bot yaratish handlerlari
"""

import re
import logging
import aiohttp
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter
from asgiref.sync import sync_to_async

from modul.bot.main_bot.services.user_service import (
    get_user_by_uid, create_bot, get_bot_info_from_telegram,
    set_bot_webhook, validate_bot_token
)
from modul.bot.main_bot.states import CreateBotStates
from modul.config import settings_conf

logger = logging.getLogger(__name__)

create_bot_router = Router()


async def create_bot_menu():
    buttons = [
        [InlineKeyboardButton(text="📝 Ввести токен бота", callback_data="enter_token")],
        [InlineKeyboardButton(text="❓ Как получить токен?", callback_data="token_help")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


async def bot_modules_menu(selected_modules=None):
    if selected_modules is None:
        selected_modules = {}

    modules = [
        ("refs", "Реферальный 👥"),
        ("leo", "Дайвинчик 💞"),
        ("asker", "Asker Бот 💬"),  # Будет сохраняться в enable_music
        ("kino", "Кинотеатр 🎥"),
        ("download", "DownLoader 💾"),
        ("chatgpt", "ChatGPT 💡")
    ]

    buttons = []
    row = []
    for i, (module_key, module_name) in enumerate(modules):
        icon = "✅" if selected_modules.get(module_key, False) else "⬜"
        text = f"{icon} {module_name}"
        row.append(InlineKeyboardButton(
            text=text,
            callback_data=f"toggle_{module_key}"
        ))

        # Добавляем по 2 кнопки в ряд
        if len(row) == 2 or i == len(modules) - 1:
            buttons.append(row)
            row = []

    # Дополнительные кнопки
    buttons.append([InlineKeyboardButton(text="✅ Сохранить и создать", callback_data="save_bot_config")])
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


async def back_to_modules_menu():
    """Клавиатура для возврата к выбору модулей"""
    buttons = [
        [InlineKeyboardButton(text="◀️ Вернуться к выбору модулей", callback_data="select_modules")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# Handler'lar
@create_bot_router.callback_query(F.data == "create_bot")
async def start_create_bot(callback: CallbackQuery, state: FSMContext):
    """Начало создания бота"""
    await state.clear()  # Очистка предыдущих данных

    await callback.message.edit_text(
        "🤖 <b>Создание нового бота</b>\n\n"
        "📋 <b>Процесс создания бота:</b>\n"
        "1️⃣ Получите токен бота от @BotFather\n"
        "2️⃣ Предоставьте нам токен\n"
        "3️⃣ Выберите нужные модули\n"
        "4️⃣ Бот готов!\n\n"
        "🎯 <b>Преимущества:</b>\n"
        "• Готовый бот за несколько минут\n"
        "• 6 профессиональных модулей\n"
        "• Автоматическая настройка webhook\n"
        "• Полная панель управления\n\n"
        "🔐 <b>Формат токена:</b>\n"
        "<code>1234567890:XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX</code>",
        reply_markup=await create_bot_menu(),
        parse_mode="HTML"
    )
    await callback.answer()


@create_bot_router.callback_query(F.data == "enter_token")
async def request_token(callback: CallbackQuery, state: FSMContext):
    """Запрос ввода токена"""
    await state.set_state(CreateBotStates.waiting_for_token)
    await callback.message.edit_text(
        "📝 <b>Введите токен бота:</b>\n\n"
        "⚠️ <b>Важные правила безопасности:</b>\n"
        "• Получайте токен только от @BotFather\n"
        "• Никому не передавайте - это секретная информация!\n"
        "• При создании скриншотов скрывайте токен\n"
        "• Если токен скомпрометирован, обновите его командой /revoke\n\n"
        "🔤 <b>Введите токен:</b>\n"
        "Скопируйте и вставьте токен правильно ↓",
        parse_mode="HTML"
    )
    await callback.answer()


@create_bot_router.callback_query(F.data == "token_help")
async def show_token_help(callback: CallbackQuery):
    """Помощь по получению токена"""
    help_text = (
        "❓ <b>Как получить токен бота?</b>\n\n"
        "📱 <b>Шаги:</b>\n"
        "1️⃣ Отправьте /start боту @BotFather\n"
        "2️⃣ Отправьте команду /newbot\n"
        "3️⃣ Введите имя для бота\n"
        "   Например: <code>Мой Крутой Бот</code>\n"
        "4️⃣ Введите username для бота\n"
        "   Например: <code>my_awesome_bot</code>\n"
        "   (должен заканчиваться на bot!)\n"
        "5️⃣ BotFather пришлет вам токен\n\n"
        "⚡ <b>Быстрые ссылки:</b>\n"
        "• @BotFather - создание ботов\n"
        "• /help - помощь BotFather\n"
        "• /mybots - ваши боты\n\n"
        "⚠️ <b>Напоминание:</b>\n"
        "Токен - это 'пароль' вашего бота. Не\n"
        "передавайте его никому и храните в безопасности!"
    )

    await callback.message.edit_text(
        help_text,
        reply_markup=await create_bot_menu(),
        parse_mode="HTML"
    )
    await callback.answer()


@create_bot_router.message(StateFilter(CreateBotStates.waiting_for_token))
async def process_token(message: Message, state: FSMContext):
    """Обработка введенного токена"""
    token = message.text.strip()

    # Проверка формата токена (полный паттерн)
    if not re.match(r'^\d{8,10}:[A-Za-z0-9_-]{35}$', token):
        await message.answer(
            "❌ <b>Неправильный формат токена!</b>\n\n"
            "Токен должен быть в следующем формате:\n"
            "<code>1234567890:AAHfn3yN8ZSN9JXOp4RgQOtHqEbWr-abc</code>\n\n"
            "✅ <b>Правильный формат:</b>\n"
            "• Цифры : Буквы и символы\n"
            "• 35 символов во второй части\n"
            "• Только A-Z, a-z, 0-9, _, - символы\n\n"
            "🔄 Попробуйте еще раз или нажмите /start:",
            parse_mode="HTML"
        )
        return

    # Проверка, не используется ли токен уже
    is_valid, error_message = await validate_bot_token(token)
    if not is_valid:
        await message.answer(
            f"❌ <b>Ошибка токена!</b>\n\n"
            f"🔍 <b>Причина:</b> {error_message}\n\n"
            f"💡 <b>Решение:</b>\n"
            f"• Используйте другой токен\n"
            f"• Или удалите существующий бот в @BotFather\n\n"
            f"🔄 Введите другой токен или нажмите /start:",
            parse_mode="HTML"
        )
        return

    # Получение информации о боте из Telegram
    try:
        # Анимация загрузки
        loading_msg = await message.answer("⏳ <b>Проверка токена...</b>", parse_mode="HTML")

        bot_info = await get_bot_info_from_telegram(token)
        if not bot_info:
            await loading_msg.edit_text(
                "❌ <b>Токен неправильный или бот не существует!</b>\n\n"
                "🔍 <b>Возможные причины:</b>\n"
                "• Токен скопирован неправильно\n"
                "• Бот удален в @BotFather\n"
                "• Проблемы с интернет-соединением\n\n"
                "💡 <b>Решение:</b>\n"
                "• Проверьте токен еще раз\n"
                "• Убедитесь, что бот существует в @BotFather\n\n"
                "🔄 Попробуйте еще раз:",
                parse_mode="HTML"
            )
            return

        if not bot_info.get('is_bot', False):
            await loading_msg.edit_text(
                "❌ <b>Это не токен бота!</b>\n\n"
                "🤖 Принимаются только токены ботов.\n"
                "Токены обычных пользователей не работают.\n\n"
                "📝 Создайте бота в @BotFather и введите его токен:",
                parse_mode="HTML"
            )
            return

        # Сохранение данных в state
        await state.update_data(
            token=token,
            bot_username=bot_info['username'],
            bot_name=bot_info['first_name'],
            bot_id=bot_info['id']
        )

        await state.set_state(CreateBotStates.configuring_modules)

        await loading_msg.edit_text(
            f"✅ <b>Бот успешно найден!</b>\n\n"
            f"🤖 <b>Имя:</b> {bot_info['first_name']}\n"
            f"📛 <b>Username:</b> @{bot_info['username']}\n"
            f"🆔 <b>ID:</b> <code>{bot_info['id']}</code>\n\n"
            f"🔧 <b>Теперь выберите модули для бота:</b>\n"
            f"Каждый модуль добавляет отдельную функцию в ваш бот.\n"
            f"Отметьте нужные модули и сохраните.",
            reply_markup=await bot_modules_menu(),
            parse_mode="HTML"
        )

    except Exception as e:
        logger.error(f"Error processing token {token}: {e}")
        await message.answer(
            "❌ <b>Произошла техническая ошибка!</b>\n\n"
            "🔧 <b>Это может быть временная проблема.</b>\n"
            "Пожалуйста, попробуйте еще раз.\n\n"
            "Если проблема продолжается, обратитесь в\n"
            "службу поддержки: @support_username",
            parse_mode="HTML"
        )


# Новый handler для показа информации о модуле
@create_bot_router.callback_query(F.data.startswith("module_info:"))
async def show_module_info(callback: CallbackQuery, state: FSMContext):
    """Показ информации о выбранном модуле"""
    module_key = callback.data.split(":")[1]

    # Информация о модулях
    module_info = {
        'refs': {
            'name': '👥 Реферальный',
            'description': (
                "💰 <b>Реферальная система</b>\n\n"
                "📋 <b>Функции:</b>\n"
                "• Автоматическое начисление бонусов за рефералов\n"
                "• Многоуровневая реферальная система\n"
                "• Статистика рефералов и заработка\n"
                "• Вывод средств на карту или кошелек\n"
                "• Промокоды и бонусные акции\n\n"
                "💵 <b>Монетизация:</b>\n"
                "• Комиссия с выводов: 10%\n"
                "• Доход от активных пользователей\n\n"
                "🎯 <b>Подходит для:</b>\n"
                "Заработка на рефералах, создания пассивного дохода"
            )
        },
        'leo': {
            'name': '💞 Дайвинчик',
            'description': (
                "❤️ <b>Сервис знакомств</b>\n\n"
                "📋 <b>Функции:</b>\n"
                "• Поиск анкет по возрасту и локации\n"
                "• Система лайков и взаимных симпатий\n"
                "• Приватные чаты между пользователями\n"
                "• Фото-верификация анкет\n"
                "• VIP-статусы и премиум функции\n\n"
                "💵 <b>Монетизация:</b>\n"
                "• Платные лайки и сообщения\n"
                "• VIP-подписки\n"
                "• Реклама в боте\n\n"
                "🎯 <b>Подходит для:</b>\n"
                "Создания сервиса знакомств, социальной сети"
            )
        },
        'music': {
            'name': '💬 Asker Бот',
            'description': (
                "🤖 <b>AI Помощник</b>\n\n"
                "📋 <b>Функции:</b>\n"
                "• Ответы на любые вопросы\n"
                "• Помощь в решении задач\n"
                "• Перевод текстов\n"
                "• Написание статей и контента\n"
                "• Консультации по разным темам\n\n"
                "💵 <b>Монетизация:</b>\n"
                "• Платные запросы к AI\n"
                "• Премиум функции\n"
                "• Подписки на безлимит\n\n"
                "🎯 <b>Подходит для:</b>\n"
                "Создания AI-помощника, образовательного бота"
            )
        },
        'kino': {
            'name': '🎥 Кинотеатр',
            'description': (
                "🎬 <b>Онлайн кинотеатр</b>\n\n"
                "📋 <b>Функции:</b>\n"
                "• База фильмов и сериалов\n"
                "• Поиск по названию, жанру, году\n"
                "• Высокое качество HD/4K\n"
                "• Субтитры и озвучка\n"
                "• Рекомендации и топы\n\n"
                "💵 <b>Монетизация:</b>\n"
                "• VIP-доступ к новинкам\n"
                "• Премиум качество\n"
                "• Реклама в боте\n\n"
                "🎯 <b>Подходит для:</b>\n"
                "Создания развлекательного контента"
            )
        },
        'download': {
            'name': '💾 DownLoader',
            'description': (
                "📥 <b>Универсальный загрузчик</b>\n\n"
                "📋 <b>Функции:</b>\n"
                "• Скачивание с YouTube, TikTok, Instagram\n"
                "• Конвертация видео в MP3\n"
                "• Поддержка всех популярных платформ\n"
                "• Высокое качество загрузки\n"
                "• Быстрая обработка ссылок\n\n"
                "💵 <b>Монетизация:</b>\n"
                "• Премиум качество загрузок\n"
                "• Безлимитные скачивания\n"
                "• Приоритетная обработка\n\n"
                "🎯 <b>Подходит для:</b>\n"
                "Сервиса скачивания контента"
            )
        },
        'chatgpt': {
            'name': '💡 ChatGPT',
            'description': (
                "🧠 <b>ChatGPT интеграция</b>\n\n"
                "📋 <b>Функции:</b>\n"
                "• Полная интеграция с ChatGPT\n"
                "• Неограниченные диалоги\n"
                "• Поддержка изображений\n"
                "• Различные режимы общения\n"
                "• История переписки\n\n"
                "💵 <b>Монетизация:</b>\n"
                "• Платные запросы\n"
                "• VIP-режимы\n"
                "• Расширенные функции\n\n"
                "🎯 <b>Подходит для:</b>\n"
                "AI-консультаций, образования, развлечений"
            )
        }
    }

    # Сохраняем выбранный модуль в state
    await state.update_data(selected_module=module_key)

    info = module_info.get(module_key, {'name': 'Неизвестный модуль', 'description': 'Информация недоступна'})

    text = f"{info['description']}"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚙️ Создать", callback_data="start_create_with_module")],
        [InlineKeyboardButton(text="◀️ Назад к модулям", callback_data="create_bot")]
    ])

    await callback.message.edit_text(
        text,
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await callback.answer()
    """Включение/выключение модуля"""
    module_name = callback.data.replace("toggle_", "")

    data = await state.get_data()
    modules = data.get('modules', {})

    # Изменение состояния модуля
    modules[module_name] = not modules.get(module_name, False)
    await state.update_data(modules=modules)

    # Обновление клавиатуры
    await callback.message.edit_reply_markup(
        reply_markup=await bot_modules_menu(selected_modules=modules)
    )

    # Обратная связь
    module_names = {
        'refs': 'Реферальный',
        'leo': 'Дайвинчик',
        'asker': 'Asker Бот',
        'kino': 'Кинотеатр',
        'download': 'DownLoader',
        'chatgpt': 'ChatGPT'
    }

    module_display_name = module_names.get(module_name, module_name)
    status = "включен" if modules[module_name] else "выключен"

    await callback.answer(f"✅ {module_display_name} {status}")


@create_bot_router.callback_query(F.data == "select_modules")
async def back_to_modules_selection(callback: CallbackQuery, state: FSMContext):
    """Возврат к выбору модулей"""
    data = await state.get_data()
    modules = data.get('modules', {})

    await callback.message.edit_text(
        f"🔧 <b>Бот: @{data.get('bot_username', 'unknown')}</b>\n\n"
        f"<b>Выберите модули:</b>\n"
        f"Каждый модуль добавляет отдельную функцию в ваш бот.\n\n"
        f"✅ Зеленая галочка - модуль включен\n"
        f"⬜ Серая галочка - модуль выключен\n\n"
        f"Нажмите на модуль для включения/выключения.",
        reply_markup=await bot_modules_menu(selected_modules=modules),
        parse_mode="HTML"
    )
    await callback.answer()


@create_bot_router.callback_query(F.data == "save_bot_config")
async def save_bot_config(callback: CallbackQuery, state: FSMContext):
    """Сохранение конфигурации бота"""
    data = await state.get_data()

    if not all(key in data for key in ['token', 'bot_username', 'bot_name']):
        await callback.message.edit_text(
            "❌ <b>Данные неполные!</b>\n\n"
            "Пожалуйста, начните заново и выполните\n"
            "все шаги правильно.",
            reply_markup=await create_bot_menu(),
            parse_mode="HTML"
        )
        await callback.answer()
        return

    try:
        # Анимация прогресса
        progress_msg = await callback.message.edit_text(
            "⏳ <b>Создание бота...</b>\n\n"
            "🔄 <b>Процессы:</b>\n"
            "• ✅ Данные проверены\n"
            "• 🔄 Сохранение бота в базу...\n"
            "• ⏳ Установка webhook...\n"
            "• ⏳ Конфигурация модулей...",
            parse_mode="HTML"
        )

        # Проверка пользователя
        user = await get_user_by_uid(callback.from_user.id)
        if not user:
            await progress_msg.edit_text(
                "❌ <b>Пользователь не найден!</b>\n\n"
                "Пожалуйста, нажмите /start и зарегистрируйтесь заново.",
                parse_mode="HTML"
            )
            await callback.answer()
            return

        # Создание бота
        modules = data.get('modules', {})

        new_bot = await create_bot(
            owner_uid=callback.from_user.id,
            token=data['token'],
            username=data['bot_username'],
            modules=modules
        )

        if not new_bot:
            await progress_msg.edit_text(
                "❌ <b>Ошибка при создании бота!</b>\n\n"
                "Это может быть временная техническая проблема.\n"
                "Пожалуйста, попробуйте еще раз.\n\n"
                "Если проблема продолжается, обратитесь в\n"
                "поддержку: @support_username",
                reply_markup=await create_bot_menu(),
                parse_mode="HTML"
            )
            await callback.answer()
            return

        # Обновление прогресса
        await progress_msg.edit_text(
            "⏳ <b>Создание бота...</b>\n\n"
            "🔄 <b>Процессы:</b>\n"
            "• ✅ Данные проверены\n"
            "• ✅ Бот сохранен в базу\n"
            "• 🔄 Установка webhook...\n"
            "• ⏳ Конфигурация модулей...",
            parse_mode="HTML"
        )

        # Установка webhook
        webhook_url = settings_conf.WEBHOOK_URL.format(token=data['token'])
        webhook_success = await set_bot_webhook(data['token'], webhook_url)

        # Финальный прогресс
        await progress_msg.edit_text(
            "⏳ <b>Создание бота...</b>\n\n"
            "🔄 <b>Процессы:</b>\n"
            "• ✅ Данные проверены\n"
            "• ✅ Бот сохранен в базу\n"
            f"• {'✅' if webhook_success else '⚠️'} Webhook {'установлен' if webhook_success else 'ошибка'}\n"
            "• ✅ Модули сконфигурированы",
            parse_mode="HTML"
        )

        # Результат
        enabled_modules = []
        module_names = {
            'refs': '👥 Реферальный',
            'leo': '💞 Дайвинчик',
            'asker': '💬 Asker Бот',
            'kino': '🎥 Кинотеатр',
            'download': '💾 DownLoader',
            'chatgpt': '💡 ChatGPT'
        }

        for module, enabled in modules.items():
            if enabled:
                enabled_modules.append(module_names.get(module, module))

        modules_text = "\n".join(
            [f"  ✅ {module}" for module in enabled_modules]) if enabled_modules else "  ❌ Ни один модуль не включен"
        webhook_status = "✅ Успешно" if webhook_success else "⚠️ Ошибка (будет повторная попытка позже)"

        await state.clear()

        success_text = (
            f"🎉 <b>Бот успешно создан!</b>\n\n"
            f"🤖 <b>Информация о боте:</b>\n"
            f"• <b>Username:</b> @{data['bot_username']}\n"
            f"• <b>Имя:</b> {data['bot_name']}\n"
            f"• <b>ID:</b> <code>{data.get('bot_id', 'N/A')}</code>\n\n"
            f"👨‍💼 <b>Настройки админа:</b>\n"
            f"• <b>Админ бота:</b> Вы (автоматически)\n"
            f"• <b>Реферальный бонус:</b> 3 сом\n"
            f"• <b>Минимальный вывод:</b> 30 сом\n\n"
            f"🌐 <b>Webhook:</b> {webhook_status}\n\n"
            f"🔧 <b>Включенные модули:</b>\n{modules_text}\n\n"
            f"🚀 <b>Ссылка на бот:</b>\n"
            f"https://t.me/{data['bot_username']}\n\n"
            f"✨ <b>Бот полностью настроен и готов к работе!</b>\n"
            f"📊 Для управления настройками бота перейдите в раздел 'Мои боты'."
        )

        await progress_msg.edit_text(
            success_text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔗 Открыть бот", url=f"https://t.me/{data['bot_username']}")],
                [InlineKeyboardButton(text="🤖 Мои боты", callback_data="my_bots")],
                [InlineKeyboardButton(text="➕ Создать еще бот", callback_data="create_bot")],
                [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_main")]
            ]),
            parse_mode="HTML"
        )

        # Лог успеха
        logger.info(f"Bot created successfully: @{data['bot_username']} for user {callback.from_user.id}")

    except Exception as e:
        logger.error(f"Error saving bot config: {e}")
        await callback.message.edit_text(
            f"❌ <b>Ошибка при создании бота!</b>\n\n"
            f"🔍 <b>Детали ошибки:</b>\n"
            f"<code>{str(e)}</code>\n\n"
            f"💡 <b>Решение:</b>\n"
            f"• Попробуйте еще раз\n"
            f"• Если проблема продолжается, обратитесь в\n"
            f"  поддержку: @support_username",
            reply_markup=await create_bot_menu(),
            parse_mode="HTML"
        )

    await callback.answer()


# Cancel handler
@create_bot_router.message(StateFilter(CreateBotStates.waiting_for_token),
                           F.text.in_(["/start", "/cancel", "❌Отменить"]))
async def cancel_token_input(message: Message, state: FSMContext):
    """Отмена ввода токена"""
    await state.clear()
    await message.answer(
        "❌ <b>Создание бота отменено.</b>\n\n"
        "Вы можете начать заново в любое время.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_main")]
        ]),
        parse_mode="HTML"
    )


# Error handler for any other text during token waiting
@create_bot_router.message(StateFilter(CreateBotStates.waiting_for_token))
async def invalid_token_format(message: Message, state: FSMContext):
    """Обработчик неправильного формата токена"""
    await message.answer(
        "❌ <b>Неправильный токен!</b>\n\n"
        "🔤 Токен должен состоять только из цифр, букв и специальных символов.\n\n"
        "📝 Правильный формат:\n"
        "<code>1234567890:AAHfn3yN8ZSN9JXOp4RgQOtHqEbWr-abc</code>\n\n"
        "💡 Скопируйте правильный токен от @BotFather и вставьте его.",
        parse_mode="HTML"
    )
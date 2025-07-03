# modul/bot/main_bot/handlers/create_bot.py (полная обновленная версия)
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


@create_bot_router.callback_query(F.data == "create_bot")
async def create_bot_menu(callback: CallbackQuery, state: FSMContext):
    """Создание нового бота - показ модулей для выбора"""
    await state.clear()
    await state.set_state(CreateBotStates.selecting_modules)

    text = (
        "🤖 <b>Создание нового бота</b>\n\n"
        "🔧 <b>Выберите модуль для вашего бота:</b>\n"
        "Каждый модуль предоставляет уникальную функциональность.\n\n"
        "👆 Нажмите на модуль, чтобы узнать о нем подробнее:"
    )

    # Создаем кнопки модулей в 2 колонки
    modules = [
        ("refs", "Реферальный 👥"),
        ("leo", "Дайвинчик 💞"),
        ("music", "Asker Бот 💬"),
        ("kino", "Кинотеатр 🎥"),
        ("download", "DownLoader 💾"),
        ("chatgpt", "ChatGPT 💡")
    ]

    buttons = []
    row = []
    for i, (module_key, module_name) in enumerate(modules):
        row.append(InlineKeyboardButton(
            text=module_name,
            callback_data=f"module_info:{module_key}"
        ))

        # Добавляем по 2 кнопки в ряд
        if len(row) == 2 or i == len(modules) - 1:
            buttons.append(row)
            row = []

    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main")])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    await callback.message.edit_text(
        text,
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await callback.answer()


@create_bot_router.callback_query(F.data.startswith("module_info:"))
async def show_module_info(callback: CallbackQuery, state: FSMContext):
    """Показ информации о выбранном модуле"""
    module_key = callback.data.split(":")[1]

    # Доступные модули
    available_modules = ['refs', 'kino']  # Faqat bu modullar ishlamoqda

    # Информация о модулях
    module_info = {
        'refs': {
            'name': '👥 Реферальный',
            'description': (
                "💰 <b>Реферальный бот</b> — готовое решение для быстрого роста аудитории\n\n"
                "Автоматизирует привлечение новых подписчиков, ведёт детальную статистику и работает 24/7. Идеален для масштабирования бизнеса через партнёрскую программу.\n\n"
                "📋 <b>Ключевые особенности:</b>\n"
                "• Подробная аналитика по рефералам\n"
                "• Гибкая настройка вознаграждений\n"
                "• Простой интерфейс для пользователей\n"
                "• Полная автоматизация процессов\n\n"
                "🎯 <b>Идеально для:</b>\n"
                "Масштабирования бизнеса и создания партнёрских программ"
            ),
            'available': True
        },
        'kino': {
            'name': '🎥 Кинотеатр',
            'description': (
                "🎬 <b>Онлайн кинотеатр</b> — ваш надёжный компас в мире кино\n\n"
                "Ищете фильм или сериал? Просто напишите название — бот всё найдёт!\n\n"
                "📋 <b>Ключевые особенности:</b>\n"
                "• Точный поиск по названию\n"
                "• Быстрая работа без задержек\n"
                "• Подробная информация о контенте\n"
                "• Встроенный реферальный модуль\n\n"
                "🎯 <b>Простой и эффективный:</b>\n"
                "Никаких лишних функций — только то, что действительно нужно для поиска кино по названию. Инструмент для ценителей кино"
            ),
            'available': True
        },
        'leo': {
            'name': '💞 Дайвинчик',
            'description': (
                "⚠️ <b>Модуль временно недоступен</b>\n\n"
                "❤️ <b>Дайвинчик - Готовый бот знакомств</b>\n\n"
                "📋 <b>Что будет доступно:</b>\n"
                "• Умный алгоритм подбора совместимых пар\n"
                "• Гибкая настройка параметров поиска\n"
                "• Готовая база пользователей внутри\n"
                "• Безопасное общение с модерацией контента\n"
                "• Встроенный реферальный модуль\n\n"
                "🚀 <b>Статус:</b> Модуль находится в разработке и будет доступен в ближайшее время!"
            ),
            'available': False
        },
        'music': {
            'name': '💬 Asker Бот',
            'description': (
                "⚠️ <b>Модуль временно недоступен</b>\n\n"
                "🔒 <b>Приватный Аск-бот</b> — безопасный сервис личных вопросов и ответов\n\n"
                "📋 <b>Что будет доступно:</b>\n"
                "• Полная конфиденциальность общения\n"
                "• Мгновенные уведомления о новых вопросах\n"
                "• Удобная система управления сообщениями\n"
                "• Простая настройка приватности\n"
                "• Встроенный реферальный модуль\n\n"
                "🚀 <b>Статус:</b> Модуль активно разрабатывается и скоро будет запущен!"
            ),
            'available': False
        },
        'download': {
            'name': '💾 DownLoader',
            'description': (
                "⚠️ <b>Модуль временно недоступен</b>\n\n"
                "📥 <b>DownLoader Bot</b> — универсальный инструмент для скачивания контента\n\n"
                "📋 <b>Что будет доступно:</b>\n"
                "• Мгновенное скачивание видео и аудио\n"
                "• Поддержка всех популярных платформ\n"
                "• Выбор качества файлов\n"
                "• Простой интерфейс без лишних действий\n"
                "• Работа с прямыми ссылками\n"
                "• Встроенный реферальный модуль\n\n"
                "🚀 <b>Статус:</b> Модуль в финальной стадии тестирования, запуск совсем скоро!"
            ),
            'available': False
        },
        'chatgpt': {
            'name': '💡 ChatGPT',
            'description': (
                "⚠️ <b>Модуль временно недоступен</b>\n\n"
                "🤖 <b>ChatGPT Бот</b> - теперь ваш надёжный помощник в Telegram\n\n"
                "📋 <b>Что будет доступно:</b>\n"
                "• Работает 24/7 без перерывов\n"
                "• Решает сложные задачи просто\n"
                "• Настраивается под ваши цели\n"
                "• Экономит драгоценное время\n"
                "• Встроенный реферальный модуль\n\n"
                "🚀 <b>Статус:</b> Ведутся финальные работы по интеграции, запуск в ближайшие дни!"
            ),
            'available': False
        }
    }

    info = module_info.get(module_key, {
        'name': 'Неизвестный модуль',
        'description': 'Информация недоступна',
        'available': False
    })

    text = f"{info['description']}"

    # Agar modul mavjud bo'lsa, yaratish tugmasini ko'rsatamiz
    if info.get('available', False):
        # Сохраняем выбранный модуль в state
        await state.update_data(selected_module=module_key)

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⚙️ Создать", callback_data="start_create_with_module")],
            [InlineKeyboardButton(text="◀️ Назад к модулям", callback_data="create_bot")]
        ])
    else:
        # Agar modul mavjud bo'lmasa, faqat orqaga qaytish tugmasini ko'rsatamiz
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔔 Уведомить о запуске", callback_data=f"notify_launch:{module_key}")],
            [InlineKeyboardButton(text="◀️ Назад к модулям", callback_data="create_bot")]
        ])

    await callback.message.edit_text(
        text,
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await callback.answer()


@create_bot_router.callback_query(F.data.startswith("notify_launch:"))
async def notify_module_launch(callback: CallbackQuery, state: FSMContext):
    """Уведомление о запуске модуля"""
    module_key = callback.data.split(":")[1]

    module_names = {
        'leo': '💞 Дайвинчик',
        'music': '💬 Asker Бот',
        'download': '💾 DownLoader',
        'chatgpt': '💡 ChatGPT'
    }

    module_name = module_names.get(module_key, 'модуль')

    await callback.answer(
        f"🔔 Вы будете уведомлены, когда {module_name} станет доступен!",
        show_alert=True
    )



# @create_bot_router.callback_query(F.data.startswith("module_info:"))
# async def show_module_info(callback: CallbackQuery, state: FSMContext):
#     """Показ информации о выбранном модуле"""
#     module_key = callback.data.split(":")[1]
#
#     # Информация о модулях
#     module_info = {
#         'refs': {
#             'name': '👥 Реферальный',
#             'description': (
#                 "💰 <b>Реферальный бот</b> — готовое решение для быстрого роста аудитории\n\n"
#                 "Автоматизирует привлечение новых подписчиков, ведёт детальную статистику и работает 24/7. Идеален для масштабирования бизнеса через партнёрскую программу.\n\n"
#                 "📋 <b>Ключевые особенности:</b>\n"
#                 "• Подробная аналитика по рефералам\n"
#                 "• Гибкая настройка вознаграждений\n"
#                 "• Простой интерфейс для пользователей\n"
#                 "• Полная автоматизация процессов\n\n"
#                 "🎯 <b>Идеально для:</b>\n"
#                 "Масштабирования бизнеса и создания партнёрских программ"
#             )
#         },
#         'leo': {
#             'name': '💞 Дайвинчик',
#             'description': (
#                 "❤️ <b>Дайвинчик - Готовый бот знакомств</b>\n\n"
#                 "Продуманная система подбора пар и удобный интерфейс. Автоматизирует процесс поиска собеседников по полу, возрасту и целям городам.\n\n"
#                 "📋 <b>Ключевые преимущества:</b>\n"
#                 "• Умный алгоритм подбора совместимых пар\n"
#                 "• Гибкая настройка параметров поиска\n"
#                 "• Готовая база пользователей внутри\n"
#                 "• Безопасное общение с модерацией контента\n"
#                 "• Встроенный реферальный модуль\n\n"
#                 "🎯 <b>Поможет создать:</b>\n"
#                 "Популярное место для знакомств с растущей аудиторией и высоким уровнем вовлечённости. Идеальное решение для развития проекта в сфере онлайн-знакомств."
#             )
#         },
#         'music': {
#             'name': '💬 Asker Бот',
#             'description': (
#                 "🔒 <b>Приватный Аск-бот</b> — безопасный сервис личных вопросов и ответов\n\n"
#                 "Только отправитель и получатель видят сообщения.\n\n"
#                 "📋 <b>Главные преимущества:</b>\n"
#                 "• Полная конфиденциальность общения\n"
#                 "• Мгновенные уведомления о новых вопросах\n"
#                 "• Удобная система управления сообщениями\n"
#                 "• Простая настройка приватности\n"
#                 "• Встроенный реферальный модуль\n\n"
#                 "🎯 <b>Органический рост:</b>\n"
#                 "Обеспечивается за счет реферальной системы и размещения ссылок для вопросов на личных страницах пользователей"
#             )
#         },
#         'kino': {
#             'name': '🎥 Кинотеатр',
#             'description': (
#                 "🎬 <b>Онлайн кинотеатр</b> — ваш надёжный компас в мире кино\n\n"
#                 "Ищете фильм или сериал? Просто напишите название — бот всё найдёт!\n\n"
#                 "📋 <b>Ключевые особенности:</b>\n"
#                 "• Точный поиск по названию\n"
#                 "• Быстрая работа без задержек\n"
#                 "• Подробная информация о контенте\n"
#                 "• Встроенный реферальный модуль\n\n"
#                 "🎯 <b>Простой и эффективный:</b>\n"
#                 "Никаких лишних функций — только то, что действительно нужно для поиска кино по названию. Инструмент для ценителей кино"
#             )
#         },
#         'download': {
#             'name': '💾 DownLoader',
#             'description': (
#                 "📥 <b>DownLoader Bot</b> — универсальный инструмент для скачивания контента\n\n"
#                 "Скачивайте медиафайлы с любых платформ в один клик! Просто отправьте ссылку — бот сделает всё остальное.\n\n"
#                 "📋 <b>Основные возможности:</b>\n"
#                 "• Мгновенное скачивание видео и аудио\n"
#                 "• Поддержка всех популярных платформ\n"
#                 "• Выбор качества файлов\n"
#                 "• Простой интерфейс без лишних действий\n"
#                 "• Работа с прямыми ссылками\n"
#                 "• Встроенный реферальный модуль\n\n"
#                 "🎯 <b>Начните использовать:</b>\n"
#                 "Прямо сейчас — сохраняйте любимый контент в пару кликов!"
#             )
#         },
#         'chatgpt': {
#             'name': '💡 ChatGPT',
#             'description': (
#                 "🤖 <b>ChatGPT Бот</b> - теперь ваш надёжный помощник в Telegram\n\n"
#                 "Превратите рутину в удовольствие! Бот восхитит вас скоростью работы и точностью решений. Ваши задачи решаются сами собой.\n\n"
#                 "📋 <b>Главные достоинства:</b>\n"
#                 "• Работает 24/7 без перерывов\n"
#                 "• Решает сложные задачи просто\n"
#                 "• Настраивается под ваши цели\n"
#                 "• Экономит драгоценное время\n"
#                 "• Встроенный реферальный модуль\n\n"
#                 "🎯 <b>Идеально для:</b>\n"
#                 "Бизнеса, маркетинга, обучения и автоматизации. Попробуйте — и оцените разницу!"
#             )
#         }
#     }
#
#     # Сохраняем выбранный модуль в state
#     await state.update_data(selected_module=module_key)
#
#     info = module_info.get(module_key, {'name': 'Неизвестный модуль', 'description': 'Информация недоступна'})
#
#     text = f"{info['description']}"
#
#     keyboard = InlineKeyboardMarkup(inline_keyboard=[
#         [InlineKeyboardButton(text="⚙️ Создать", callback_data="start_create_with_module")],
#         [InlineKeyboardButton(text="◀️ Назад к модулям", callback_data="create_bot")]
#     ])
#
#     await callback.message.edit_text(
#         text,
#         reply_markup=keyboard,
#         parse_mode="HTML"
#     )
#     await callback.answer()


@create_bot_router.callback_query(F.data == "start_create_with_module")
async def start_create_with_module(callback: CallbackQuery, state: FSMContext):
    """Показ инструкции и запрос токена"""
    await state.set_state(CreateBotStates.waiting_for_token)

    text = (
        "📋 <b>Следуйте инструкции, чтобы создать бота:</b>\n\n"
        "1️⃣ Запустите @BotFather\n"
        "2️⃣ Нажмите кнопку /start\n"
        "3️⃣ Введите команду /newbot\n"
        "4️⃣ Придумайте название для бота\n"
        "5️⃣ Создайте уникальный ник с окончанием *bot \n"
        "    (например: @JustRefBot)\n"
        "6️⃣ Получите HTTP API токен, скопируйте его и отправьте в это диалоговое окно ⬇️\n\n"
        "🔤 <b>Отправьте токен:</b>"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад к модулям", callback_data="create_bot")]
    ])

    await callback.message.edit_text(
        text,
        reply_markup=keyboard,
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

        # Получаем выбранный модуль из state
        data = await state.get_data()
        selected_module = data.get('selected_module')

        if not selected_module:
            await loading_msg.edit_text(
                "❌ <b>Модуль не выбран!</b>\n\n"
                "Пожалуйста, начните заново и выберите модуль.",
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

        # Создаем модули dict с выбранным модулем
        modules = {selected_module: True}

        # Автоматическое создание бота
        await loading_msg.edit_text("⏳ <b>Создание бота...</b>", parse_mode="HTML")

        # Проверка пользователя
        user = await get_user_by_uid(message.from_user.id)
        if not user:
            await loading_msg.edit_text(
                "❌ <b>Пользователь не найден!</b>\n\n"
                "Пожалуйста, нажмите /start и зарегистрируйтесь заново.",
                parse_mode="HTML"
            )
            return

        # Создание бота
        new_bot = await create_bot(
            owner_uid=message.from_user.id,
            token=token,
            username=bot_info['username'],
            modules=modules
        )

        if not new_bot:
            await loading_msg.edit_text(
                "❌ <b>Ошибка при создании бота!</b>\n\n"
                "Это может быть временная техническая проблема.\n"
                "Пожалуйста, попробуйте еще раз.",
                parse_mode="HTML"
            )
            return

        # Установка webhook
        webhook_url = settings_conf.WEBHOOK_URL.format(token=token)
        webhook_success = await set_bot_webhook(token, webhook_url)

        # Информация о выбранном модуле
        module_names = {
            'refs': '👥 Реферальный',
            'leo': '💞 Дайвинчик',
            'music': '💬 Asker Бот',
            'kino': '🎥 Кинотеатр',
            'download': '💾 DownLoader',
            'chatgpt': '💡 ChatGPT'
        }

        selected_module_name = module_names.get(selected_module, selected_module)
        webhook_status = "✅ Успешно" if webhook_success else "⚠️ Ошибка (будет повторная попытка позже)"

        await state.clear()

        success_text = (
            f"🎉 <b>Бот успешно создан!</b>\n\n"
            f"🤖 <b>Информация о боте:</b>\n"
            f"• <b>Username:</b> @{bot_info['username']}\n"
            f"• <b>Имя:</b> {bot_info['first_name']}\n"
            f"• <b>ID:</b> <code>{bot_info['id']}</code>\n\n"
            f"🔧 <b>Активный модуль:</b>\n"
            f"✅ {selected_module_name}\n\n"
            f"🌐 <b>Webhook:</b> {webhook_status}\n\n"
            f"🚀 <b>Ссылка на бот:</b>\n"
            f"https://t.me/{bot_info['username']}\n\n"
            f"✨ <b>Бот полностью настроен и готов к работе!</b>\n"
            f"📊 Для управления перейдите в раздел 'Мои боты'."
        )

        await loading_msg.edit_text(
            success_text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔗 Открыть бот", url=f"https://t.me/{bot_info['username']}")],
                [InlineKeyboardButton(text="🤖 Мои боты", callback_data="my_bots")],
                [InlineKeyboardButton(text="➕ Создать еще бот", callback_data="create_bot")],
                [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_main")]
            ]),
            parse_mode="HTML"
        )

        # Лог успеха
        logger.info(
            f"Bot created successfully: @{bot_info['username']} with module {selected_module} for user {message.from_user.id}")

    except Exception as e:
        logger.error(f"Ошибка при обработке токена {token}: {e}")
        await message.answer(
            "❌ <b>Произошла техническая ошибка!</b>\n\n"
            "🔧 <b>Это может быть временная проблема.</b>\n"
            "Пожалуйста, попробуйте еще раз.\n\n"
            "Если проблема продолжается, обратитесь в\n"
            "службу поддержки: @support_username",
            parse_mode="HTML"
        )


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
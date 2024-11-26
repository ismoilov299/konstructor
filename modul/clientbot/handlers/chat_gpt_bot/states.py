from aiogram import Bot
from aiogram.filters import Filter
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message

from modul.clientbot import shortcuts


class AiAdminState(StatesGroup):
    check_token_and_update = State()
    check_user_to_update = State()
    update_balance_state = State()


class AiState(StatesGroup):
    gpt3 = State()
    gpt4 = State()
    handle_voice_message = State()
    generate_image = State()
    text_to_voice = State()


class ChatGptFilter(Filter):
    async def __call__(self, message: Message, bot: Bot) -> bool:
        bot_db = await shortcuts.get_bot(bot)
        return shortcuts.have_one_module(bot_db, "chatgpt")

from aiogram import Bot
from aiogram.filters import Filter
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message

from modul.clientbot import shortcuts


class Links(StatesGroup):
    send_st = State()
    answer_st = State()
    change_greeting = State()
    change_link = State()


class ChangeAdminInfo(StatesGroup):
    get_channel_id = State()
    get_channel_url = State()
    delete_channel = State()
    mailing = State()


class AnonBotFilter(Filter):
    async def __call__(self, message: Message, bot: Bot) -> bool:
        bot_db = await shortcuts.get_bot(bot)
        return shortcuts.have_one_module(bot_db, "anon")

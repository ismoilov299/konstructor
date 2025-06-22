from aiogram.fsm.state import State, StatesGroup

class CreateBotStates(StatesGroup):
    waiting_for_token = State()
    configuring_modules = State()
    setting_admin = State()
    setting_channels = State()

class ManageBotStates(StatesGroup):
    selecting_bot = State()
    editing_settings = State()
    managing_modules = State()
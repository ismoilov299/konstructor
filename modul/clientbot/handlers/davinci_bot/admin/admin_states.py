from aiogram.fsm.state import State, StatesGroup


class AdminDavinciStates(StatesGroup):
    waiting_for_stop_word = State()
    waiting_for_user_id = State()
    waiting_for_broadcast_message = State()
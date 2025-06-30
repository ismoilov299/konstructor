from aiogram.fsm.state import State, StatesGroup


class DavinciRegistration(StatesGroup):
    waiting_for_start = State()
    waiting_for_name = State()
    waiting_for_age = State()
    waiting_for_sex = State()
    waiting_for_search_preference = State()
    waiting_for_city = State()
    waiting_for_about = State()
    waiting_for_photo = State()


class DavinciEditProfile(StatesGroup):
    waiting_for_field = State()
    editing_name = State()
    editing_age = State()
    editing_city = State()
    editing_about = State()
    editing_photo = State()


class DavinciBoostForm(StatesGroup):
    waiting_for_boost_type = State()
    waiting_for_payment = State()
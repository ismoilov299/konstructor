# modul/clientbot/handlers/davinci_bot/data/states.py

from aiogram.fsm.state import StatesGroup, State

class DavinciRegistration(StatesGroup):
    """Ro'yxatdan o'tish davlatlari"""
    BEGIN = State()
    SEX = State()
    AGE = State()
    SEARCH = State()
    NAME = State()
    CITY = State()
    ABOUT_ME = State()
    GALLERY = State()
    FINISH = State()

class DavinciEdit(StatesGroup):
    """Tahrirlash davlatlari"""
    SEX = State()
    AGE = State()
    SEARCH = State()
    NAME = State()
    CITY = State()
    ABOUT_ME = State()
    GALLERY = State()

class DavinciRate(StatesGroup):
    """Baholash davlatlari"""
    VIEW = State()
    SEND_MESSAGE = State()
    COMPLAINT = State()

class DavinciCouple(StatesGroup):
    """Juftlik davlatlari"""
    VIEW = State()
    MANAGE = State()

class DavinciAdmin(StatesGroup):
    """Admin davlatlari"""
    MENU = State()
    STOP_WORDS = State()
    SETTINGS_BEFORE_OP = State()
    SETTINGS_BEFORE_FLYER = State()
    SETTINGS_MAX_ANKETS = State()
    MODERATION = State()
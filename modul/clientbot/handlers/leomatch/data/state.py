# from aiogram.dispatcher.fsm.state import StatesGroup, State
from aiogram.fsm.state import StatesGroup, State


class LeomatchRegistration(StatesGroup):
    BEGIN = State()
    AGE = State()
    SEX = State()
    CITY = State()
    FULL_NAME = State()
    WHICH_SEARCH = State()
    ABOUT_ME = State()
    SEND_PHOTO = State()
    FINAL = State()
    # временно
    START = State()
    AGE = State()
    MIN_AGE = State()
    MAX_AGE = State()
    CITY = State()
    ADDRESS = State()
    FULL_NAME = State()
    SEX = State()
    WHICH_SEARCH = State()
    ABOUT_ME = State()
    SEND_PHOTO = State()
    FINAL = State()

class LeomatchChange(StatesGroup):
    CHANGE_NAME = State()
    CHANGE_AGE = State()
    CHANGE_MIN_AGE = State()
    CHANGE_MAX_AGE = State()
    CHANGE_CITY = State()
    CHANGE_ADDRESS = State()
    CHANGE_SEARCH = State()
    CHANGE_ABOUT_ME = State()
    CHANGE_PHOTO = State()

class LeomatchMain(StatesGroup):
    WAIT = State()
    PROFILES = State()
    MY_PROFILE = State()
    PROFILE_MANAGE = State()
    SLEEP = State()
    SET_DESCRIPTION = State()
    SET_PHOTO = State()
    
class LeomatchProfiles(StatesGroup):
    LOOCK = State()
    INPUT_MESSAGE = State()
    MANAGE_LIKES = State()
    MANAGE_LIKE = State()
    

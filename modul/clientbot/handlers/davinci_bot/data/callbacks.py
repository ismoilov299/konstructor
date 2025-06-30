# modul/clientbot/handlers/davinci_bot/data/callbacks.py

from aiogram.filters.callback_data import CallbackData
from enum import Enum


class DavinciAction(str, Enum):
    """Davinci asosiy actionlar"""
    GO = "go"
    ACCOUNT = "account"
    RATE = "rate"
    BOOST = "boost"
    COUPLE = "couple"
    ADMIN = "admin"


class AnketAction(str, Enum):
    """Anketa actionlari"""
    SEX = "anketSex"
    AGE = "anketAge"
    AGE_RANGE = "anketAge2"
    AGE_SPECIFIC = "anketAge3"
    SEARCH = "anketSearch"
    NAME = "anketName"
    NAME_FIRSTNAME = "anketNameFirstname"
    CITY = "anketCity"
    ABOUT_ME = "anketAboutMe"
    GALLERY = "anketGallary"
    GALLERY_LOAD = "anketGallaryLoadAcc"
    GALLERY_SAVE = "GallarySave"
    FINISH = "anketFinish"


class EditAction(str, Enum):
    """Tahrirlash actionlari"""
    SEX = "editSex"
    AGE = "editAge"
    SEARCH = "editSearch"
    NAME = "editName"
    CITY = "editCity"
    ABOUT_ME = "editAboutMe"
    GALLERY = "editGallary"


class RateAction(str, Enum):
    """Baholash actionlari"""
    PLUS = "ratePlus"
    MINUS = "rateMinus"
    SEND_MESSAGE = "sendMes"
    COMPLAINT = "rateComp"
    SKIP = "coupleSkip"
    STOP = "stopCouple"


class ComplaintAction(str, Enum):
    """Shikoyat actionlari"""
    SHOW = "complaint"
    CHOICE = "complaintChoice"
    DELETE = "complaintDel"


class AdminAction(str, Enum):
    """Admin actionlari"""
    MENU = "adminMenu"
    STAT = "adminStat"
    CREATE_ANKET = "adminCreateAnket"
    ANKET_EDIT = "adminAnketEdit"
    STOP_WORDS = "adminStop"
    BEFORE_OP = "adminAnketBeforeOp"
    BEFORE_FLYER = "adminAnketBeforeFlyer"
    MAX_ANKETS = "adminAnketMax"
    TOP_BAN = "topBan"


# Callback Data Classes
class DavinciCallback(CallbackData, prefix="davinci"):
    """Asosiy davinci callback"""
    action: DavinciAction
    param: str = ""
    param_2: str = ""
    param_3: str = ""


class AnketCallback(CallbackData, prefix="davinci"):
    """Anketa callback"""
    action: AnketAction
    param: str = ""
    param_2: str = ""
    param_3: str = ""


class EditCallback(CallbackData, prefix="davinci"):
    """Tahrirlash callback"""
    action: EditAction
    param: str = ""
    param_2: str = ""


class RateCallback(CallbackData, prefix="davinci"):
    """Baholash callback"""
    action: RateAction
    param: str = ""
    param_2: str = ""


class ComplaintCallback(CallbackData, prefix="davinci"):
    """Shikoyat callback"""
    action: ComplaintAction
    param: str = ""
    param_2: str = ""


class AdminCallback(CallbackData, prefix="davinci"):
    """Admin callback"""
    action: AdminAction
    param: str = ""
    param_2: str = ""
    param_3: str = ""


# Helper functions
def parse_davinci_callback(callback_data: str):
    """Davinci callback'ni parse qilish"""
    parts = callback_data.split('_')
    if len(parts) < 2:
        return None

    return {
        'module': parts[0],  # davinci
        'action': parts[1],  # action nomi
        'param': parts[2] if len(parts) > 2 else "",
        'param_2': parts[3] if len(parts) > 3 else "",
        'param_3': parts[4] if len(parts) > 4 else "",
    }
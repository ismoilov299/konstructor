# modul/clientbot/handlers/admin/states.py
"""
Admin panel FSM states
Universal admin panel uchun holatlar
"""

from aiogram.fsm.state import State, StatesGroup


class AdminStates(StatesGroup):
    """Admin panel states"""

    # Foydalanuvchi qidirish
    user_search = State()

    # Balans o'zgartirish
    change_balance = State()
    add_balance = State()

    # Referal o'zgartirish
    change_referrals = State()

    # Xabar tarqatish
    mailing_message = State()

    # Sozlamalar
    change_ref_reward = State()
    change_min_payout = State()

    # Kanal qo'shish
    add_channel_url = State()
    add_channel_id = State()
    delete_channel = State()


class PaymentStates(StatesGroup):
    """To'lov bilan bog'liq holatlar"""

    # To'lov miqdorini o'zgartirish
    change_amount = State()

    # To'lov ma'lumotlarini o'zgartirish
    change_payment_info = State()


class ChannelStates(StatesGroup):
    """Kanal boshqaruvi holatlar"""

    # Kanal URL
    channel_url = State()

    # Kanal ID
    channel_id = State()

    # Kanal nomi
    channel_name = State()


class SettingsStates(StatesGroup):
    """Bot sozlamalari holatlar"""

    # Referral mukofoti
    ref_reward = State()

    # Minimal to'lov miqdori
    min_payout = State()

    # Bot nomi
    bot_name = State()

    # Xush kelibsiz xabari
    welcome_message = State()


class StatisticsStates(StatesGroup):
    """Statistika holatlar"""

    # Muayyan sana oralig'i
    date_range = State()

    # Foydalanuvchi filtri
    user_filter = State()
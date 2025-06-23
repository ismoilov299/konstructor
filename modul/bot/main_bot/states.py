# modul/bot/main_bot/states.py
"""
Main bot uchun FSM state'lari
"""

from aiogram.fsm.state import State, StatesGroup

class CreateBotStates(StatesGroup):
    """Bot yaratish jarayoni state'lari"""
    selecting_modules = State()           # Modullar tanlanmoqda
    waiting_for_token = State()           # Token kutilmoqda
    configuring_modules = State()         # Modullar sozlanmoqda
    setting_admin = State()               # Admin sozlamalari
    setting_channels = State()            # Kanallar sozlamalari

class ManageBotStates(StatesGroup):
    """Bot boshqarish state'lari"""
    selecting_bot = State()               # Bot tanlanmoqda
    editing_settings = State()            # Sozlamalar tahrirlanmoqda
    managing_modules = State()            # Modullar boshqarilmoqda
    editing_channels = State()            # Kanallar tahrirlanmoqda
    editing_admin = State()               # Admin ma'lumotlari tahrirlanmoqda

class BotSettingsStates(StatesGroup):
    """Bot sozlamalari state'lari"""
    waiting_admin_input = State()         # Admin ma'lumoti kutilmoqda
    waiting_channel_input = State()       # Kanal ma'lumoti kutilmoqda
    waiting_referral_input = State()      # Referral sozlamalari kutilmoqda
    waiting_message_input = State()       # Xabar matni kutilmoqda
    confirming_action = State()           # Amalni tasdiqlash

class UserSettingsStates(StatesGroup):
    """Foydalanuvchi sozlamalari state'lari"""
    editing_profile = State()             # Profil tahrirlanmoqda
    changing_password = State()           # Parol o'zgartirilmoqda

class StatisticsStates(StatesGroup):
    """Statistika ko'rish state'lari"""
    viewing_general = State()             # Umumiy statistika
    viewing_bot_stats = State()           # Bot statistikasi
    exporting_data = State()              # Ma'lumotlarni eksport qilish
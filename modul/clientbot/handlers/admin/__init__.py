# modul/clientbot/handlers/admin/__init__.py
"""
Universal Admin Panel Package
Barcha bot turlari uchun universal admin panel
"""

# from .universal_admin import setup_universal_admin, universal_admin
from .handlers_extended import setup_extended_admin_handlers, extended_admin_handlers
from .admin_service import admin_service
from .keyboards import admin_keyboards
from .states import AdminStates, PaymentStates, ChannelStates, SettingsStates

__all__ = [
    # 'setup_universal_admin',
    'universal_admin',
    'setup_extended_admin_handlers',
    'extended_admin_handlers',
    'admin_service',
    'admin_keyboards',
    'AdminStates',
    'PaymentStates',
    'ChannelStates',
    'SettingsStates'
]


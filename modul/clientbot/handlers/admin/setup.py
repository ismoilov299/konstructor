import logging
from .universal_admin import setup_universal_admin
from .handlers_extended import setup_extended_admin_handlers

logger = logging.getLogger(__name__)


def init_admin_panel():
    """
    Admin panel ni to'liq sozlash va ishga tushirish
    Bu funksiya bot ishga tushganda chaqirilishi kerak
    """
    try:
        # Universal admin panel ni sozlash
        universal_admin = setup_universal_admin()
        logger.info("✅ Universal admin panel sozlandi")

        # Extended handlers ni sozlash
        extended_handlers = setup_extended_admin_handlers()
        logger.info("✅ Extended admin handlers sozlandi")

        logger.info("🎉 Admin panel muvaffaqiyatli ishga tushirildi!")

        return {
            'universal_admin': universal_admin,
            'extended_handlers': extended_handlers
        }

    except Exception as e:
        logger.error(f"❌ Admin panel sozlashda xatolik: {e}")
        return None


def get_admin_info():
    """Admin panel haqida ma'lumot"""
    return {
        'name': 'Universal Admin Panel',
        'version': '1.0.0',
        'description': 'Barcha bot turlari uchun universal admin panel',
        'features': [
            'Foydalanuvchilarni boshqarish',
            'To\'lovlarni ko\'rish va tasdiqlash',
            'Xabar tarqatish',
            'Bot sozlamalari',
            'Majburiy obuna kanallari',
            'Batafsil statistika',
            'Sahifalash va qidiruv',
            'Foydalanuvchi ma\'lumotlarini eksport qilish'
        ],
        'supported_bots': [
            'Referral bots',
            'Anonymous bots',
            'ChatGPT bots',
            'Kino bots',
            'Download bots',
            'Va boshqa bot turlari'
        ]
    }

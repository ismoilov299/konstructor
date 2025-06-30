import re
from typing import List
from asgiref.sync import sync_to_async

from modul.models import DavinciStopWords


def validate_age(age: int) -> bool:
    """Validate age input"""
    return 16 <= age <= 100


def validate_name(name: str) -> bool:
    """Validate name input"""
    if not name or len(name) < 2 or len(name) > 15:
        return False

    # Check if name contains only letters, spaces, and basic punctuation
    pattern = r'^[a-zA-Zа-яА-ЯёЁ\s\-\.]+'
    return bool(re.match(pattern, name))


def validate_about_me(text: str) -> bool:
    """Validate about me text"""
    return 10 <= len(text) <= 300


@sync_to_async
def check_stop_words(text: str) -> bool:
    """Check if text contains stop words"""
    try:
        stop_words = DavinciStopWords.objects.filter(is_active=True).values_list('word', flat=True)
        text_lower = text.lower()

        for word in stop_words:
            if word.lower() in text_lower:
                return True

        return False

    except Exception:
        return False


def validate_city(city: str) -> bool:
    """Validate city name"""
    if not city or len(city) < 2 or len(city) > 50:
        return False

    # Allow letters, spaces, hyphens, and apostrophes
    pattern = r'^[a-zA-Zа-яА-ЯёЁ\s\-\'\.]+'
    return bool(re.match(pattern, city))


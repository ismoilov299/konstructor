# modul/clientbot/handlers/davinci_bot/shortcuts/database.py

from asgiref.sync import sync_to_async
from django.db import transaction
from modul.models import User, DavinciMessage, DavinciStopWords
import json
import time
import datetime


# User CRUD operations
@sync_to_async
def get_user_davinci(user_id):
    """Davinci ma'lumotlarini olish"""
    try:
        user = User.objects.get(uid=user_id)
        return {
            'user_id': user.uid,
            'first_name': user.first_name or '',
            'last_name': user.last_name or '',
            'username': user.username or '',
            'davinci_ban': user.davinci_ban,
            'davinci_ban_list': user.davinci_ban_list,
            'davinci_check': user.davinci_check,
            'davinci_couple_stop': user.davinci_couple_stop,
            'davinci_anket_active': user.davinci_anket_active,
            'davinci_anket_name': user.davinci_anket_name,
            'davinci_anket_sex': user.davinci_anket_sex,
            'davinci_anket_search': user.davinci_anket_search,
            'davinci_anket_age': user.davinci_anket_age,
            'davinci_anket_city': user.davinci_anket_city,
            'davinci_anket_aboutme': user.davinci_anket_aboutme,
            'davinci_anket_gallary': user.davinci_anket_gallary,
            'davinci_rate_list': user.davinci_rate_list,
        }
    except User.DoesNotExist:
        return None


@sync_to_async
def update_user_davinci(user_id, data):
    """Davinci ma'lumotlarini yangilash"""
    try:
        with transaction.atomic():
            user = User.objects.get(uid=user_id)
            for key, value in data.items():
                setattr(user, key, value)
            user.save()
            return True
    except User.DoesNotExist:
        return False


@sync_to_async
def create_user_davinci(user_id, first_name='', last_name='', username=''):
    """Yangi davinci foydalanuvchi yaratish"""
    try:
        user, created = User.objects.get_or_create(
            uid=user_id,
            defaults={
                'first_name': first_name,
                'last_name': last_name,
                'username': username,
            }
        )
        return user
    except Exception:
        return None


# Anket functions
async def is_anket_complete(user_data):
    """Anketa to'liqligini tekshirish"""
    if not user_data:
        return False

    required_fields = [
        'davinci_anket_sex',
        'davinci_anket_age',
        'davinci_anket_search',
        'davinci_anket_name',
        'davinci_anket_city',
        'davinci_anket_aboutme'
    ]

    for field in required_fields:
        if not user_data.get(field):
            return False

    # Gallery tekshirish
    gallery = user_data.get('davinci_anket_gallary', '[]')
    if isinstance(gallery, str):
        try:
            gallery = json.loads(gallery)
        except:
            gallery = []

    return len(gallery) > 0


# Users for rating - LeoMatchModel bilan
@sync_to_async
def get_users_for_rating(user_id, user_data, limit=1):
    """Baholash uchun foydalanuvchilarni olish - LeoMatchModel dan"""
    try:
        # User parametrlari
        sex = user_data.get('davinci_anket_sex', 0)
        search = user_data.get('davinci_anket_search', 0)
        age = user_data.get('davinci_anket_age', 0)
        city = user_data.get('davinci_anket_city', '')
        rate_list = user_data.get('davinci_rate_list', '|')

        # Base query - LeoMatchModel dan
        queryset = LeoMatchModel.objects.filter(
            active=True,
            blocked=False,
        ).exclude(user__uid=user_id)

        # User ban filter
        queryset = queryset.exclude(user__banned=True)  # User modelidagi banned

        # Gender filter
        if search == 1:  # Male qidirmoqda
            queryset = queryset.filter(sex='MALE')
        elif search == 2:  # Female qidirmoqda
            queryset = queryset.filter(sex='FEMALE')
        # search == 3 bo'lsa hamma jins

        # Age filter
        if sex == 1 and search == 2:  # Yigit qiz qidiryapti
            queryset = queryset.filter(
                age__lte=age,
                age__gte=age - 3
            )
        elif sex == 2 and search == 1:  # Qiz yigit qidiryapti
            queryset = queryset.filter(
                age__gte=age,
                age__lte=age + 3
            )
        else:
            queryset = queryset.filter(
                age__gte=age - 2,
                age__lte=age + 2
            )

        # City preference
        city_users = queryset.filter(city__icontains=city) if city else queryset
        if city and city_users.exists():
            queryset = city_users

        # Exclude already rated users
        if rate_list and '|' in rate_list:
            rated_users = []
            for item in rate_list.split('|'):
                if '-' in item:
                    user_id_rated = item.split('-')[0]
                    if user_id_rated.isdigit():
                        rated_users.append(int(user_id_rated))

            if rated_users:
                queryset = queryset.exclude(user__uid__in=rated_users)

        # Order and limit
        leo_matches = queryset.select_related('user').order_by('id')[:limit]

        result = []
        for leo_match in leo_matches:
            # Gallery ma'lumotini tayyorlash
            gallery = leo_match.gallery if hasattr(leo_match,
                                                   'gallery') else f'[{{"type": "photo", "media": "{leo_match.photo}"}}]'

            result.append({
                'id': leo_match.id,
                'user_id': leo_match.user.uid,
                'first_name': leo_match.user.first_name or '',
                'username': leo_match.user.username or '',
                'davinci_anket_name': leo_match.full_name,
                'davinci_anket_sex': 1 if leo_match.sex == 'MALE' else 2,
                'davinci_anket_age': leo_match.age,
                'davinci_anket_city': leo_match.city,
                'davinci_anket_aboutme': leo_match.about_me,
                'davinci_anket_gallary': gallery,
                'davinci_rate_list': getattr(leo_match, 'rate_list', '|'),
                'davinci_couple_stop': 1 if getattr(leo_match, 'couple_notifications_stopped', False) else 0,
                'blocked': leo_match.blocked,
            })

        return result

    except Exception as e:
        print(f"Error getting users for rating: {e}")
        return []


# Message/Like functions
@sync_to_async
def save_like(from_user_id, to_user_id, like_data):
    """Layk saqlash"""
    try:
        with transaction.atomic():
            message, created = DavinciMessage.objects.get_or_create(
                cust_id=str(to_user_id),
                defaults={
                    'cust': '{}',
                    'date_save': str(int(time.time())),
                    'rate': '{}',
                    'skip': 0
                }
            )

            # Rate data'ni parse qilish
            try:
                rate_data = json.loads(message.rate) if message.rate else {}
            except:
                rate_data = {}

            # Yangi layk qo'shish
            rate_data[str(from_user_id)] = like_data
            message.rate = json.dumps(rate_data)
            message.date_save = str(int(time.time()))
            message.skip = 0
            message.save()

            return True
    except Exception as e:
        print(f"Error saving like: {e}")
        return False


@sync_to_async
def get_pending_likes(user_id):
    """Kutilayotgan layklarni olish"""
    try:
        message = DavinciMessage.objects.filter(cust_id=str(user_id)).first()
        if not message or not message.rate:
            return []

        try:
            rate_data = json.loads(message.rate)
            return rate_data
        except:
            return []
    except Exception:
        return []


@sync_to_async
def delete_processed_like(user_id, from_user_id):
    """Qayta ishlangan laykni o'chirish"""
    try:
        with transaction.atomic():
            message = DavinciMessage.objects.filter(cust_id=str(user_id)).first()
            if message and message.rate:
                try:
                    rate_data = json.loads(message.rate)
                    if str(from_user_id) in rate_data:
                        del rate_data[str(from_user_id)]

                        if rate_data:
                            message.rate = json.dumps(rate_data)
                            message.save()
                        else:
                            message.delete()

                        return True
                except:
                    pass
        return False
    except Exception:
        return False


# Rate list functions
async def add_to_rate_list(user_id, target_user_id, rating):
    """Rate list'ga qo'shish (1=like, 0=dislike)"""
    user_data = await get_user_davinci(user_id)
    if not user_data:
        return False

    rate_list = user_data.get('davinci_rate_list', '|')
    new_item = f"|{target_user_id}-{rating}"

    if new_item not in rate_list:
        new_rate_list = rate_list + new_item
        return await update_user_davinci(user_id, {'davinci_rate_list': new_rate_list})

    return True


async def check_mutual_like(user1_id, user2_id):
    """O'zaro layk borligini tekshirish"""
    user1_data = await get_user_davinci(user1_id)
    user2_data = await get_user_davinci(user2_id)

    if not user1_data or not user2_data:
        return False

    # User1 user2'ni layk qilganmi?
    user1_likes_user2 = f"|{user2_id}-1" in user1_data.get('davinci_rate_list', '')

    # User2 user1'ni layk qilganmi?
    user2_likes_user1 = f"|{user1_id}-1" in user2_data.get('davinci_rate_list', '')

    return user1_likes_user2 and user2_likes_user1


# Statistics functions
@sync_to_async
def get_davinci_statistics():
    """Davinci statistikasi"""
    try:
        stats = {
            'total_users': User.objects.filter(davinci_anket_active=1).count(),
            'male_users': User.objects.filter(davinci_anket_sex=1, davinci_anket_active=1).count(),
            'female_users': User.objects.filter(davinci_anket_sex=2, davinci_anket_active=1).count(),
            'search_male': User.objects.filter(davinci_anket_search=1, davinci_anket_active=1).count(),
            'search_female': User.objects.filter(davinci_anket_search=2, davinci_anket_active=1).count(),
            'search_all': User.objects.filter(davinci_anket_search=3, davinci_anket_active=1).count(),
        }
        return stats
    except Exception:
        return {}


# Stop words functions
@sync_to_async
def get_stop_words():
    """Taqiqlangan so'zlarni olish"""
    try:
        words = DavinciStopWords.objects.values_list('word', flat=True)
        return list(words)
    except Exception:
        return []


@sync_to_async
def add_stop_word(word):
    """Taqiqlangan so'z qo'shish"""
    try:
        DavinciStopWords.objects.get_or_create(word=word)
        return True
    except Exception:
        return False


@sync_to_async
def delete_stop_word(word_id):
    """Taqiqlangan so'zni o'chirish"""
    try:
        DavinciStopWords.objects.filter(id=word_id).delete()
        return True
    except Exception:
        return False


# Helper functions
async def validate_text_for_links(text):
    """Matnda havolalar borligini tekshirish"""
    import re

    # Havolalar uchun regex patterns
    patterns = [
        r"[@|\/][a-z|A-Z|0-9|_]{3,}",  # @username yoki /command
        r"[a-z|A-Z|0-9|_]{2,}bot",  # bot usernames
        r"(http(s)?:\/\/)?(www\.)?(\w|\d|-){2,}\.\w{2,}",  # web links
        r"t\.me\/\w+",  # Telegram links
    ]

    for pattern in patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return False

    return True


async def validate_text_for_stop_words(text):
    """Matnda taqiqlangan so'zlar borligini tekshirish"""
    stop_words = await get_stop_words()
    text_lower = text.lower()

    for word in stop_words:
        if word.lower() in text_lower:
            return False

    return True


async def clean_text(text):
    """Matnni tozalash"""
    # HTML teglarni almashtirish
    text = text.replace('>', '»').replace('<', '«')
    # Apostroflarni almashtirish
    text = text.replace("'", "`")
    return text


async def format_anket_text(user_data):
    """Anketa matnini formatlash"""
    sex_emoji = "🙎‍♂️" if user_data.get('davinci_anket_sex') == 1 else "🙍‍♀️"
    name = user_data.get('davinci_anket_name', '')
    age = user_data.get('davinci_anket_age', '')
    city = user_data.get('davinci_anket_city', '').title()
    about_me = user_data.get('davinci_anket_aboutme', '')

    text = f"{sex_emoji} <b>{name}</b>"
    if age:
        text += f", {age}"
    if city:
        text += f", {city}"
    if about_me:
        text += f" - {about_me.strip()}"

    return text


async def get_media_from_gallery(gallery_json):
    """Gallery JSON'dan media list olish"""
    try:
        if isinstance(gallery_json, str):
            gallery = json.loads(gallery_json)
        else:
            gallery = gallery_json
        return gallery
    except:
        return []


# Ban functions - banned maydonini ishlatib
async def ban_user(user_id, reason="Violation"):
    """Foydalanuvchini ban qilish"""
    return await update_user_davinci(user_id, {'banned': True})


async def unban_user(user_id):
    """Foydalanuvchi banini olib tashlash"""
    return await update_user_davinci(user_id, {'banned': False})


async def check_user_banned(user_id):
    """Foydalanuvchi ban qilinganligini tekshirish"""
    user_data = await get_user_davinci(user_id)
    if not user_data:
        return False
    return user_data.get('banned', False)


# Admin functions
@sync_to_async
def get_users_for_moderation(moderation_type="new"):
    """Moderatsiya uchun foydalanuvchilarni olish"""
    try:
        if moderation_type == "new":
            # Yangi anketalar
            queryset = User.objects.filter(
                davinci_anket_active=1,
                davinci_check=0
            ).order_by('-id')
        elif moderation_type == "ban":
            # Ban qilingan foydalanuvchilar
            queryset = User.objects.filter(
                davinci_anket_active=1,
                banned=True  # banned maydonini ishlatamiz
            ).order_by('-id')
        else:
            return []

        users = queryset[:1]  # Bitta user qaytarish

        result = []
        for user in users:
            result.append({
                'id': user.id,
                'user_id': user.uid,
                'first_name': user.first_name or '',
                'last_name': user.last_name or '',
                'username': user.username or '',
                'davinci_ban': user.davinci_ban,
                'davinci_ban_list': user.davinci_ban_list,
                'davinci_anket_name': user.davinci_anket_name,
                'davinci_anket_sex': user.davinci_anket_sex,
                'davinci_anket_age': user.davinci_anket_age,
                'davinci_anket_city': user.davinci_anket_city,
                'davinci_anket_aboutme': user.davinci_anket_aboutme,
                'davinci_anket_gallary': user.davinci_anket_gallary,
            })

        return result

    except Exception as e:
        print(f"Error getting users for moderation: {e}")
        return []


async def approve_user_anket(user_id):
    """Foydalanuvchi anketasini tasdiqlash"""
    return await update_user_davinci(user_id, {'davinci_check': 1})


async def ban_user_anket(user_id):
    """Foydalanuvchi anketasini ban qilish"""
    update_data = {
        'davinci_check': 1,
        'davinci_anket_active': 0,
        'davinci_ban': 10  # Yuqori ban raqami
    }
    return await update_user_davinci(user_id, update_data)


# City normalization
async def normalize_city_name(city):
    """Shahar nomini normalizatsiya qilish"""
    city = city.lower().strip()

    # Country to city mappings
    country_replacements = {
        'укр': 'украина',
        'украины': 'украина',
        'казакстан': 'казахстан',
        'казахстана': 'казахстан',
        'росия': 'россия',
        'россии': 'россия'
    }

    # City name normalizations
    city_replacements = {
        'сбп': 'санкт-петербург',
        'питер': 'санкт-петербург',
        'cанктпетербург': 'санкт-петербург',
        'cанктпитербург': 'санкт-петербург',
        'cанкт петербург': 'санкт-петербург',
        'cанкт питербург': 'санкт-петербург',
        'cанкт-питербург': 'санкт-петербург',
        'екб': 'екатеринбург',
        'ебург': 'екатеринбург',
        'ёбург': 'екатеринбург',
        'мск': 'москва',
        'масква': 'москва'
    }

    # Remove common prefixes
    prefixes_to_remove = ['я из ', 'я с ', 'c ']
    for prefix in prefixes_to_remove:
        if city.startswith(prefix):
            city = city[len(prefix):].strip()

    # Apply replacements
    if city in country_replacements:
        city = country_replacements[city]
    elif city in city_replacements:
        city = city_replacements[city]

    return city


# Complaint functions
async def get_complaint_text(complaint_id):
    """Shikoyat matnini olish"""
    complaints = {
        1: "🔞 Материал для взрослых",
        2: "💰 Продажа товаров и услуг",
        3: "😴 Не отвечает",
        4: "🦨 Другое",
        9: "👀 Не понравилась анкета"
    }
    return complaints.get(int(complaint_id), f"❔ Неизвестная: {complaint_id}")


# Referral functions
@sync_to_async
def get_referral_stats(user_id, days=14):
    """Referral statistikasini olish"""
    try:
        from datetime import datetime, timedelta

        # 14 kun oldingi sana
        date_limit = datetime.now() - timedelta(days=days)

        # Bu yerda referral logikasi bo'lishi kerak
        # Hozircha 0 qaytaramiz
        return {
            'count_ref': 0,
            'bonus_percent': 0
        }

    except Exception:
        return {
            'count_ref': 0,
            'bonus_percent': 0
        }
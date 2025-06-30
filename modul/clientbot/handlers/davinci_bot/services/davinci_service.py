import logging
import json
import time
from typing import Optional, List
from datetime import datetime, timedelta

from asgiref.sync import sync_to_async
from django.db import transaction
from django.db.models import Q, F
from django.utils import timezone
from psycopg2 import IntegrityError

from modul.models import LeoMatchModel, LeoMatchLikesBasketModel, UserTG, User

logger = logging.getLogger(__name__)


@sync_to_async
@transaction.atomic
def get_or_create_davinci_profile(user_id: int, bot_username: str) -> Optional[LeoMatchModel]:
    """Get or create davinci profile for user, update if exists"""
    try:
        # Get UserTG object
        user_tg = UserTG.objects.get(uid=user_id)

        # Get or create User object safely with updates
        user = get_or_create_user_safe(user_tg)

        if not user:
            logger.error(f"Failed to get or create User for uid: {user_id}")
            return None

        # Get or create LeoMatchModel with updates for existing profiles
        try:
            # Avval mavjud profilni topishga harakat qilamiz
            profile = LeoMatchModel.objects.get(
                user=user,
                bot_username=bot_username
            )

            # Mavjud profilni yangilaymiz
            updated = False

            # Agar ism o'zgargan bo'lsa
            new_name = user_tg.first_name or 'User'
            if profile.full_name != new_name:
                profile.full_name = new_name
                updated = True

            # Agar user faol emas bo'lsa, faollashtiramiz
            if not profile.active:
                profile.active = True
                updated = True

            # Agar block bo'lgan bo'lsa, block dan chiqaramiz (ixtiyoriy)
            # if profile.blocked:
            #     profile.blocked = False
            #     updated = True

            if updated:
                profile.save()
                logger.info(f"Updated existing davinci profile for user {user_id}")
            else:
                logger.info(f"Retrieved existing davinci profile for user {user_id} (no updates needed)")

            return profile

        except LeoMatchModel.DoesNotExist:
            # Yangi profil yaratamiz
            profile = LeoMatchModel.objects.create(
                user=user,
                bot_username=bot_username,
                photo='',
                media_type='PHOTO',  # Enum qiymatini ishlatish
                sex='MALE',  # Enum qiymatini ishlatish
                age=18,
                full_name=user_tg.first_name or 'User',
                about_me='',
                city='',
                which_search='ANY',  # Enum qiymatini ishlatish
                search=True,
                active=True,
                admin_checked=False,
                count_likes=0,
                blocked=False,
                couple_notifications_stopped=False,
                rate_list='|',
                gallery='[]'
            )

            logger.info(f"Created new davinci profile for user {user_id}")
            return profile

    except UserTG.DoesNotExist:
        logger.error(f"UserTG not found for uid: {user_id}")
        return None
    except Exception as e:
        logger.error(f"Error getting/creating davinci profile: {e}")
        return None


def get_or_create_user_safe(user_tg: UserTG) -> Optional[User]:
    """Safely get or create User object, update if exists"""

    # Agar UserTG da allaqachon User bog'langan bo'lsa
    if user_tg.user:
        # Mavjud User ma'lumotlarini yangilaymiz
        user = user_tg.user
        updated = False

        if not user.first_name and user_tg.first_name:
            user.first_name = user_tg.first_name
            updated = True

        if not user.last_name and user_tg.last_name:
            user.last_name = user_tg.last_name
            updated = True

        if updated:
            user.save()
            logger.info(f"Updated existing User: {user.username}")

        return user

    # UID bo'yicha User ni topishga harakat qilamiz
    try:
        existing_user = User.objects.get(uid=user_tg.uid)

        # Mavjud User ma'lumotlarini yangilaymiz
        updated = False

        if not existing_user.first_name and user_tg.first_name:
            existing_user.first_name = user_tg.first_name
            updated = True

        if not existing_user.last_name and user_tg.last_name:
            existing_user.last_name = user_tg.last_name
            updated = True

        if updated:
            existing_user.save()
            logger.info(f"Updated existing User by UID: {existing_user.username}")

        # UserTG ga bog'laymiz
        user_tg.user = existing_user
        user_tg.save()
        return existing_user

    except User.DoesNotExist:
        pass

    # Username bo'yicha User ni topishga harakat qilamiz
    base_username = f"user_{user_tg.uid}"
    try:
        existing_user = User.objects.get(username=base_username)

        # Mavjud User ma'lumotlarini yangilaymiz
        updated = False

        # UID ni tekshiramiz va yangilaymiz
        if existing_user.uid != user_tg.uid:
            existing_user.uid = user_tg.uid
            updated = True

        if not existing_user.first_name and user_tg.first_name:
            existing_user.first_name = user_tg.first_name
            updated = True

        if not existing_user.last_name and user_tg.last_name:
            existing_user.last_name = user_tg.last_name
            updated = True

        if updated:
            existing_user.save()
            logger.info(f"Updated existing User by username: {existing_user.username}")

        # UserTG ga bog'laymiz
        user_tg.user = existing_user
        user_tg.save()
        return existing_user

    except User.DoesNotExist:
        pass
    except IntegrityError as e:
        logger.warning(f"UID conflict when updating user: {e}")
        # UID conflict bo'lsa, mavjud UID bilan userni topamiz
        try:
            existing_user = User.objects.get(uid=user_tg.uid)
            user_tg.user = existing_user
            user_tg.save()
            return existing_user
        except User.DoesNotExist:
            logger.error(f"UID conflict but user not found: {user_tg.uid}")
            return None

    # Yangi User yaratishga harakat qilamiz
    username = base_username
    attempt = 0
    max_attempts = 10

    while attempt < max_attempts:
        try:
            user = User.objects.create(
                uid=user_tg.uid,
                username=username,
                first_name=user_tg.first_name or "User",
                last_name=user_tg.last_name
            )

            # UserTG ga bog'laymiz
            user_tg.user = user
            user_tg.save()

            logger.info(f"Created new User with username: {username}")
            return user

        except IntegrityError as e:
            if "username" in str(e).lower():
                # Username takrorlansa, yangi username yaratamiz
                attempt += 1
                timestamp = int(time.time())
                username = f"{base_username}_{timestamp}_{attempt}"
                logger.warning(f"Username collision, trying: {username}")
            elif "uid" in str(e).lower():
                # UID takrorlansa, mavjud userni topib qaytaramiz
                try:
                    existing_user = User.objects.get(uid=user_tg.uid)
                    user_tg.user = existing_user
                    user_tg.save()
                    logger.info(f"Found existing User by UID: {existing_user.username}")
                    return existing_user
                except User.DoesNotExist:
                    logger.error(f"UID collision but user not found: {user_tg.uid}")
                    return None
            else:
                logger.error(f"Unexpected IntegrityError: {e}")
                return None

    logger.error(f"Failed to create user after {max_attempts} attempts")
    return None


@sync_to_async
def check_davinci_profile_exists(user_id: int, bot_username: str) -> bool:
    """Check if davinci profile exists"""
    try:
        return LeoMatchModel.objects.filter(
            user__uid=user_id,
            bot_username=bot_username
        ).exists()
    except Exception as e:
        logger.error(f"Error checking davinci profile existence: {e}")
        return False


@sync_to_async
def update_davinci_profile(user_id: int, bot_username: str, **kwargs) -> bool:
    """Update specific fields in davinci profile"""
    try:
        profile = LeoMatchModel.objects.get(
            user__uid=user_id,
            bot_username=bot_username
        )

        updated = False
        allowed_fields = [
            'photo', 'media_type', 'sex', 'age', 'full_name',
            'about_me', 'city', 'which_search', 'search',
            'active', 'blocked', 'admin_checked'
        ]

        for field, value in kwargs.items():
            if field in allowed_fields and hasattr(profile, field):
                current_value = getattr(profile, field)
                if current_value != value:
                    setattr(profile, field, value)
                    updated = True
                    logger.info(f"Updated {field}: {current_value} → {value}")

        if updated:
            profile.save()
            logger.info(f"Profile updated for user {user_id}")
            return True
        else:
            logger.info(f"No updates needed for user {user_id}")
            return False

    except LeoMatchModel.DoesNotExist:
        logger.error(f"Davinci profile not found for user {user_id}")
        return False
    except Exception as e:
        logger.error(f"Error updating davinci profile: {e}")
        return False


@sync_to_async
def check_davinci_profile_exists(user_id: int, bot_username: str) -> bool:
    """Check if davinci profile exists"""
    try:
        return LeoMatchModel.objects.filter(
            user__uid=user_id,
            bot_username=bot_username
        ).exists()
    except Exception as e:
        logger.error(f"Error checking davinci profile existence: {e}")
        return False


@sync_to_async
def get_davinci_profile(user_id: int, bot_username: str) -> Optional[LeoMatchModel]:
    """Get existing davinci profile"""
    try:
        return LeoMatchModel.objects.select_related('user').get(
            user__uid=user_id,
            bot_username=bot_username
        )
    except LeoMatchModel.DoesNotExist:
        return None
    except Exception as e:
        logger.error(f"Error getting davinci profile: {e}")
        return None
@sync_to_async
def update_davinci_profile(user_id: int, bot_username: str, **kwargs) -> Optional[LeoMatchModel]:
    """Update davinci profile"""
    try:
        user_tg = UserTG.objects.get(uid=user_id)
        user = user_tg.user

        if not user:
            user = User.objects.create(
                username=f"user_{user_id}",
                first_name=user_tg.first_name or "User"
            )
            user_tg.user = user
            user_tg.save()

        profile, created = LeoMatchModel.objects.get_or_create(
            user=user,
            bot_username=bot_username
        )

        # Update fields
        for field, value in kwargs.items():
            if hasattr(profile, field):
                setattr(profile, field, value)

        # Set admin_checked to False if profile was updated
        if not created:
            profile.admin_checked = False

        profile.updated_at = timezone.now()
        profile.save()

        return profile

    except Exception as e:
        logger.error(f"Error updating davinci profile: {e}")
        return None


@sync_to_async
def get_davinci_profiles_for_viewing(user_profile: LeoMatchModel, bot_username: str, limit: int = 10) -> List[
    LeoMatchModel]:
    """Get profiles for viewing/rating"""
    try:
        # Get list of already rated profiles
        rated_ids = user_profile.rate_list.split('|') if user_profile.rate_list else []
        rated_ids = [id for id in rated_ids if id.strip()]

        # Build query filters
        filters = Q(
            bot_username=bot_username,
            admin_checked=True,
            active=True,
            blocked=False,
            search=True
        )

        # Exclude self
        filters &= ~Q(id=user_profile.id)

        # Exclude already rated
        if rated_ids:
            filters &= ~Q(id__in=rated_ids)

        # Filter by search preference
        if user_profile.which_search != 'all':
            filters &= Q(sex=user_profile.which_search)

        # Get profiles
        profiles = list(LeoMatchModel.objects.filter(filters)[:limit])

        return profiles

    except Exception as e:
        logger.error(f"Error getting profiles for viewing: {e}")
        return []


@sync_to_async
def rate_profile(from_user_profile: LeoMatchModel, to_profile_id: int, like_type: str = 'like') -> bool:
    """Rate a profile and check for mutual like"""
    try:
        to_profile = LeoMatchModel.objects.get(id=to_profile_id)

        # Add to rate list
        rate_list = from_user_profile.rate_list or '|'
        if str(to_profile_id) not in rate_list:
            from_user_profile.rate_list = rate_list + str(to_profile_id) + '|'
            from_user_profile.save()

        # Create or update like record
        if like_type == 'like' or like_type == 'super_like':
            like_record, created = LeoMatchLikesBasketModel.objects.get_or_create(
                from_user=from_user_profile,
                to_user=to_profile,
                defaults={
                    'like_type': like_type,
                    'created_at': timezone.now(),
                    'viewed': False,
                    'is_mutual': False
                }
            )

            # Increment like count for target profile
            to_profile.count_likes = F('count_likes') + 1
            to_profile.save()

            # Check for mutual like
            mutual_like = LeoMatchLikesBasketModel.objects.filter(
                from_user=to_profile,
                to_user=from_user_profile,
                like_type__in=['like', 'super_like']
            ).exists()

            if mutual_like:
                # Mark both likes as mutual
                LeoMatchLikesBasketModel.objects.filter(
                    Q(from_user=from_user_profile, to_user=to_profile) |
                    Q(from_user=to_profile, to_user=from_user_profile)
                ).update(is_mutual=True)

                return True

        return False

    except Exception as e:
        logger.error(f"Error rating profile: {e}")
        return False


@sync_to_async
def check_mutual_like(profile1: LeoMatchModel, profile2: LeoMatchModel) -> bool:
    """Check if there's a mutual like between two profiles"""
    try:
        mutual_exists = LeoMatchLikesBasketModel.objects.filter(
            Q(from_user=profile1, to_user=profile2, is_mutual=True) |
            Q(from_user=profile2, to_user=profile1, is_mutual=True)
        ).exists()

        return mutual_exists

    except Exception as e:
        logger.error(f"Error checking mutual like: {e}")
        return False


@sync_to_async
def get_likes_received(user_profile: LeoMatchModel, limit: int = 20) -> List[LeoMatchLikesBasketModel]:
    """Get likes received by user"""
    try:
        likes = list(
            LeoMatchLikesBasketModel.objects.filter(
                to_user=user_profile,
                like_type__in=['like', 'super_like']
            ).select_related('from_user').order_by('-created_at')[:limit]
        )

        return likes

    except Exception as e:
        logger.error(f"Error getting likes received: {e}")
        return []


@sync_to_async
def get_matches(user_profile: LeoMatchModel, limit: int = 20) -> List[LeoMatchLikesBasketModel]:
    """Get mutual matches for user"""
    try:
        matches = list(
            LeoMatchLikesBasketModel.objects.filter(
                Q(from_user=user_profile, is_mutual=True) |
                Q(to_user=user_profile, is_mutual=True)
            ).select_related('from_user', 'to_user').order_by('-created_at')[:limit]
        )

        return matches

    except Exception as e:
        logger.error(f"Error getting matches: {e}")
        return []

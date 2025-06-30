import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta

from asgiref.sync import sync_to_async
from django.db.models import Count, Q
from django.utils import timezone

from modul.models import LeoMatchModel, LeoMatchLikesBasketModel, DavinciStopWords

logger = logging.getLogger(__name__)


@sync_to_async
def get_pending_profiles(bot_username: str, limit: int = 20) -> List[LeoMatchModel]:
    """Get profiles pending moderation"""
    try:
        profiles = list(
            LeoMatchModel.objects.filter(
                bot_username=bot_username,
                admin_checked=False,
                blocked=False
            ).order_by('created_at')[:limit]
        )
        return profiles
    except Exception as e:
        logger.error(f"Error getting pending profiles: {e}")
        return []


@sync_to_async
def approve_profile(profile_id: int, bot_username: str) -> bool:
    """Approve a profile"""
    try:
        profile = LeoMatchModel.objects.get(
            id=profile_id,
            bot_username=bot_username
        )
        profile.admin_checked = True
        profile.active = True
        profile.save()
        return True
    except Exception as e:
        logger.error(f"Error approving profile {profile_id}: {e}")
        return False


@sync_to_async
def reject_profile(profile_id: int, bot_username: str) -> bool:
    """Reject a profile"""
    try:
        profile = LeoMatchModel.objects.get(
            id=profile_id,
            bot_username=bot_username
        )
        profile.admin_checked = False
        profile.active = False
        profile.blocked = True
        profile.save()
        return True
    except Exception as e:
        logger.error(f"Error rejecting profile {profile_id}: {e}")
        return False


@sync_to_async
def get_davinci_stats(bot_username: str) -> Dict:
    """Get davinci statistics"""
    try:
        base_query = LeoMatchModel.objects.filter(bot_username=bot_username)

        stats = {
            'total_profiles': base_query.count(),
            'approved_profiles': base_query.filter(admin_checked=True).count(),
            'pending_profiles': base_query.filter(admin_checked=False, blocked=False).count(),
            'blocked_profiles': base_query.filter(blocked=True).count(),
            'active_searchers': base_query.filter(admin_checked=True, active=True, search=True).count(),
            'male_profiles': base_query.filter(sex='male').count(),
            'female_profiles': base_query.filter(sex='female').count(),
        }

        # Like statistics
        likes_query = LeoMatchLikesBasketModel.objects.filter(
            to_user__bot_username=bot_username
        )

        stats.update({
            'total_likes': likes_query.count(),
            'mutual_likes': likes_query.filter(is_mutual=True).count(),
        })

        return stats

    except Exception as e:
        logger.error(f"Error getting davinci stats: {e}")
        return {}


@sync_to_async
def add_stop_word(word: str) -> bool:
    """Add stop word"""
    try:
        DavinciStopWords.objects.get_or_create(
            word=word.lower().strip(),
            defaults={'is_active': True}
        )
        return True
    except Exception as e:
        logger.error(f"Error adding stop word: {e}")
        return False


@sync_to_async
def remove_stop_word(word: str) -> bool:
    """Remove stop word"""
    try:
        DavinciStopWords.objects.filter(
            word=word.lower().strip()
        ).delete()
        return True
    except Exception as e:
        logger.error(f"Error removing stop word: {e}")
        return False
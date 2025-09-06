from django.db.models import F
from asgiref.sync import sync_to_async
from django.db import transaction

from modul.models import UserTG


def get_all_names():
    result = UserTG.objects.values_list("username", flat=True)
    return list(result)


@sync_to_async
def get_all_ids():
    result = UserTG.objects.values_list("uid", flat=True)
    return list(result)


@sync_to_async
def get_user_balance_db(tg_id):
    result = UserTG.objects.filter(uid=tg_id).first()
    return result.balance


@sync_to_async
def get_info_db(tg_id):
    result = UserTG.objects.filter(uid=tg_id).values_list("username", "uid", "balance")
    return list(result)


# shortcuts.py ga qo'shing:

@sync_to_async
def get_channels_with_type_for_check():
    try:
        from modul.models import ChannelSponsor, SystemChannel

        # ChannelSponsor modelidan kanallar
        sponsor_channels = ChannelSponsor.objects.all()
        sponsor_list = [(str(c.chanel_id), '', 'sponsor') for c in sponsor_channels]

        # SystemChannel modelidan aktiv kanallar
        system_channels = SystemChannel.objects.filter(is_active=True)
        system_list = [(str(c.channel_id), c.channel_url, 'system') for c in system_channels]

        # Ikkalasini birlashtirish
        all_channels = sponsor_list + system_list

        print(f"Found sponsor channels: {len(sponsor_list)}, system channels: {len(system_list)}")
        return all_channels
    except Exception as e:
        print(f"Error getting channels with type: {e}")
        return []


@sync_to_async
def remove_sponsor_channel(channel_id):
    """Faqat sponsor kanallarni o'chirish"""
    try:
        from modul.models import ChannelSponsor
        deleted_count = ChannelSponsor.objects.filter(chanel_id=channel_id).delete()
        print(f"Removed invalid sponsor channel {channel_id}, deleted: {deleted_count[0]}")
    except Exception as e:
        print(f"Error removing sponsor channel {channel_id}: {e}")


async def get_chatgpt_bonus_amount(bot_token):
    """Bot sozlamalaridan bonus miqdorini olish"""
    try:
        from modul.models import AdminInfo
        admin_info = await sync_to_async(AdminInfo.objects.filter(bot_token=bot_token).first)()
        return float(admin_info.price) if admin_info and admin_info.price else 3.0
    except:
        return 3.0


async def process_chatgpt_referral_bonus(user_id: int, referrer_id: int, bot_token: str):
    """ChatGPT bot uchun referral bonusini hisoblash"""
    try:
        # Bonus miqdorini olish
        bonus_amount = await get_chatgpt_bonus_amount(bot_token)

        # Referrer mavjudligini tekshirish
        referrer_exists = await default_checker(referrer_id)
        if not referrer_exists:
            print(f"Referrer {referrer_id} not found")
            return False, 0

        # Balansni oshirish - sizning mavjud funksiyangiz bilan
        success = await update_bc(referrer_id, "+", bonus_amount)
        if success:
            print(f"Added {bonus_amount} to referrer {referrer_id} for user {user_id}")
            return True, bonus_amount

        return False, 0
    except Exception as e:
        print(f"Error in process_chatgpt_referral_bonus: {e}")
        return False, 0

@sync_to_async
def update_bc(tg_id, sign, amount):
    """Update balance by user ID using F() expression"""
    try:
        amount = float(amount)  # amount ni float ga aylantirish

        if sign == "+":
            UserTG.objects.filter(uid=tg_id).update(balance=F('balance') + amount)
        elif sign == "-":
            UserTG.objects.filter(uid=tg_id).update(balance=F('balance') - amount)

        return True
    except Exception as e:
        print(f"Error in update_bc: {e}")
        return False


@sync_to_async
def update_bc_name(tg_id, sign, amount):
    try:
        amount = float(amount)

        if sign == "+":
            UserTG.objects.filter(username=tg_id).update(balance=F('balance') + amount)
        elif sign == "-":
            UserTG.objects.filter(username=tg_id).update(balance=F('balance') - amount)

        return True
    except Exception as e:
        print(f"Error in update_bc_name: {e}")
        return False


@sync_to_async
def default_checker(tg_id):
    result = UserTG.objects.filter(uid=tg_id).exists()
    return result



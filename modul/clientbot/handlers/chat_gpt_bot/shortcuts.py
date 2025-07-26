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



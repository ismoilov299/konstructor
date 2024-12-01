from asgiref.sync import sync_to_async
from django.db.models import F, Sum
from django.utils import timezone
from modul.models import UserTG, Checker, Withdrawals, AdminInfo, Channels


@sync_to_async
def add_user(tg_id, user_name, invited="Никто", invited_id=None):
    UserTG.objects.create(
        uid=tg_id,
        username=user_name,
        invited=invited,
        invited_id=invited_id,
        created_at=timezone.now()
    )


@sync_to_async
def add_ref(tg_id, inv_id):
    Checker.objects.create(tg_id=tg_id, inv_id=inv_id)


@sync_to_async
def check_user(tg_id):
    return UserTG.objects.filter(uid=tg_id).exists()


@sync_to_async
def check_ban(tg_id):
    user = UserTG.objects.filter(uid=tg_id).first()
    return user.banned if user else False


@sync_to_async
def get_user_info_db(tg_id):
    user = UserTG.objects.filter(uid=tg_id).first()
    if user:
        return [user.username, user.uid, user.balance, user.refs, user.invited, user.paid]
    return None


@sync_to_async
def plus_ref(tg_id):
    UserTG.objects.filter(uid=tg_id).update(refs=F('refs') + 1)


@sync_to_async
def plus_money(tg_id):
    money = AdminInfo.objects.first().price
    UserTG.objects.filter(uid=tg_id).update(balance=F('balance') + money)


@sync_to_async
def reg_withdrawals(tg_id, amount, card, bank):
    withdrawal = Withdrawals.objects.create(
        tg_id=tg_id,
        amount=amount,
        card=card,
        bank=bank,
        reg_date=timezone.now()
    )
    return [withdrawal.id, withdrawal.tg_id, withdrawal.amount, withdrawal.card, withdrawal.bank]


@sync_to_async
def check_for_wa(tg_id):
    return Withdrawals.objects.filter(tg_id=tg_id, status="ожидание").exists()


@sync_to_async
def get_admin_user():
    admin_info = AdminInfo.objects.first()
    return admin_info.admin_channel if admin_info else ""


@sync_to_async
def check_and_add(tg_id):
    checker = Checker.objects.filter(tg_id=tg_id).first()
    if checker and not checker.add:
        checker.add = True
        checker.save()
        plus_ref(checker.inv_id)
        plus_money(checker.inv_id)


"""
Admin Service
"""


@sync_to_async
def change_user_info(tg_id, column, new_info):
    user = UserTG.objects.filter(uid=tg_id).first()
    if user:
        setattr(user, column, new_info)
        user.save()


@sync_to_async
def get_user_info(tg_id):
    user = UserTG.objects.filter(uid=tg_id).first()
    if user:
        return [user.uid, user.banned, user.invited, user.balance, user.refs, user.paid]
    return None


@sync_to_async
def admin_menu_info():
    users_count = UserTG.objects.count()
    wda_count = Withdrawals.objects.filter(status="ожидание").count()
    return [users_count, wda_count]


@sync_to_async
def get_all_wait_payment():
    wda = Withdrawals.objects.filter(status="ожидание")
    return [[w.id, w.tg_id, w.amount, w.card, w.bank] for w in wda]


@sync_to_async
def status_accepted(id):
    wda = Withdrawals.objects.filter(id=id).first()
    if wda:
        user = UserTG.objects.filter(uid=wda.tg_id).first()
        if user:
            user.balance -= wda.amount
            user.paid += wda.amount
            user.save()
        wda.status = "принята"
        wda.save()
        return [wda.tg_id, wda.amount]
    return None


@sync_to_async
def status_declined(id):
    wda = Withdrawals.objects.filter(id=id).first()
    if wda:
        wda.status = "отклонена"
        wda.save()
        return [wda.tg_id, wda.amount]
    return None


@sync_to_async
def change_price(new_price):
    AdminInfo.objects.filter(id=1).update(price=new_price)


@sync_to_async
def change_min_amount(new_amount):
    AdminInfo.objects.filter(id=1).update(min_amount=new_amount)


@sync_to_async
def get_channels_for_admin():
    return [[c.id, c.channel_url, c.channel_id] for c in Channels.objects.all()]


@sync_to_async
def add_new_channel_db(url, id):
    Channels.objects.create(channel_url=url, channel_id=id)
    return True


@sync_to_async
def delete_channel_db(id):
    return Channels.objects.filter(id=id).delete()[0] > 0


@sync_to_async
def get_all_users_tg_id():
    return list(UserTG.objects.values_list('uid', flat=True))


@sync_to_async
def ban_unban_db(id, bool_value):
    UserTG.objects.filter(uid=id).update(banned=bool_value)


@sync_to_async
def addbalance_db(id, amount):
    UserTG.objects.filter(uid=id).update(balance=F('balance') + amount)


@sync_to_async
def changebalance_db(id, amount):
    UserTG.objects.filter(uid=id).update(balance=amount)


@sync_to_async
def changerefs_db(id, amount):
    UserTG.objects.filter(uid=id).update(refs=amount)


@sync_to_async
def get_all_refs_db(tg_id):
    users = UserTG.objects.filter(invited_id=tg_id)
    return [[user.username, user.uid, user.balance, user.refs, user.invited, user.paid] for user in users]


"""
Other Service
"""


@sync_to_async
def get_channels_for_check():
    return list(Channels.objects.values_list('channel_id', 'channel_url'))


def add_channel(channel_url, channel_id):
    Channels.objects.create(channel_url=channel_url, channel_id=channel_id)


@sync_to_async
def get_actual_price():
    admin_info = AdminInfo.objects.first()
    return admin_info.price if admin_info else None


@sync_to_async
def get_actual_min_amount():
    admin_info = AdminInfo.objects.first()
    return admin_info.min_amount if admin_info else None


@sync_to_async
def get_user_name(tg_id):
    user = UserTG.objects.filter(uid=tg_id).first()
    return user.username if user else None


def add_admin_info(admin):
    AdminInfo.objects.create(admin_channel=admin)


@sync_to_async
def count_info():
    users_count = UserTG.objects.count()
    total_amount = Withdrawals.objects.filter(status="принята").aggregate(Sum('amount'))['amount__sum'] or 0
    return [users_count, total_amount]

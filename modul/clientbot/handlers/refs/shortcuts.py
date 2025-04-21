import logging
import traceback

from asgiref.sync import sync_to_async
from django.db.models import F, Sum
from django.utils import timezone
from psycopg2 import IntegrityError

from modul.models import UserTG, Checker, Withdrawals, AdminInfo, Channels, Bot, ChannelSponsor, ClientBotUser

logger = logging.getLogger(__name__)


@sync_to_async
def add_user(tg_id, user_name, invited="Никто", invited_id=None, bot_token=None):
    try:
        # Проверяем, существует ли пользователь
        user_tg, created = UserTG.objects.get_or_create(
            uid=tg_id,
            defaults={
                'username': user_name,
                'first_name': user_name,
                'invited': invited,
                'invited_id': invited_id,
                'created_at': timezone.now()
            }
        )

        if created:
            print(f"User {tg_id} successfully added with link {tg_id}")
        else:
            print(f"User {tg_id} already exists, using existing record")

        # Добавляем связь с ботом вне зависимости от того, новый пользователь или нет
        if bot_token:
            try:
                current_bot = Bot.objects.get(token=bot_token)

                # Проверяем, существует ли уже запись ClientBotUser
                client_bot_user, client_created = ClientBotUser.objects.get_or_create(
                    user=user_tg,
                    bot=current_bot,
                    defaults={
                        'uid': tg_id,
                        'inviter': None  # Инвайтера добавим потом, если он есть
                    }
                )

                # Если инвайтер существует и запись была создана, обновляем инвайтера
                if invited_id and client_created:
                    inviter_client = ClientBotUser.objects.filter(uid=invited_id, bot=current_bot).first()
                    if inviter_client:
                        client_bot_user.inviter = inviter_client
                        client_bot_user.save()

                        # Увеличиваем счетчик рефералов у пригласившего
                        inviter_client.referral_count += 1
                        inviter_client.save()

                if client_created:
                    print(f"ClientBotUser {tg_id} successfully added for bot {current_bot.username}")
                else:
                    print(f"ClientBotUser {tg_id} already exists for bot {current_bot.username}")

            except Exception as e:
                print(f"⚠️ Error creating/updating ClientBotUser: {e}")
                traceback.print_exc()

        return True
    except Exception as e:
        print(f"Error adding user {tg_id} to database: {e}")
        traceback.print_exc()
        return False


@sync_to_async
def get_total_users_count(bot_token):
    try:
        # Получаем объект бота по токену
        bot = Bot.objects.get(token=bot_token)
        print(f"Found bot {bot.username} with ID {bot.id}")

        # Получаем количество пользователей для этого бота
        total_count = ClientBotUser.objects.filter(bot=bot).count()
        print(f"Total count for bot {bot.username}: {total_count}")

        return total_count
    except Bot.DoesNotExist:
        print(f"Bot with token {bot_token} does not exist")
        return 0
    except Exception as e:
        print(f"Error getting total users count: {e}")
        traceback.print_exc()
        return 0

@sync_to_async
def add_ref(tg_id, inv_id):
    Checker.objects.create(tg_id=tg_id, inv_id=inv_id)


@sync_to_async
def check_user(tg_id):
    return UserTG.objects.filter(uid=tg_id).exists()


@sync_to_async
def get_bot_user_info(user_id, bot_token):
    try:
        print(f"DEBUG: get_bot_user_info called with user_id={user_id}, bot_token={bot_token}")

        # Получаем бота по токену
        bot = Bot.objects.get(token=bot_token)
        print(f"DEBUG: Found bot: id={bot.id}, username={bot.username}")

        # Получаем пользователя по uid
        user_tg = UserTG.objects.filter(uid=user_id).first()

        if not user_tg:
            print(f"DEBUG: UserTG with uid={user_id} not found")
            return None

        print(f"DEBUG: Found UserTG: id={user_tg.id}, username={user_tg.username}")

        # Получаем информацию о пользователе для этого бота
        client_bot_user = ClientBotUser.objects.filter(
            uid=user_id,
            bot=bot
        ).first()

        if client_bot_user:
            print(
                f"DEBUG: Found ClientBotUser: id={client_bot_user.id}, balance={client_bot_user.balance}, referral_balance={client_bot_user.referral_balance}, referral_count={client_bot_user.referral_count}")
            # Возвращаем баланс и количество рефералов
            total_balance = client_bot_user.balance + client_bot_user.referral_balance
            referral_count = client_bot_user.referral_count
            print(f"DEBUG: Returning balance={total_balance}, referrals={referral_count}")
            return [total_balance, referral_count]
        else:
            print(f"DEBUG: ClientBotUser not found for user={user_tg.id}, bot={bot.id}")
            return [0, 0]  # Возвращаем нулевые значения если запись не найдена
    except Bot.DoesNotExist:
        print(f"DEBUG: Bot with token {bot_token} does not exist")
        return [0, 0]
    except Exception as e:
        print(f"DEBUG: Error in get_bot_user_info: {e}")
        import traceback
        traceback.print_exc()
        return [0, 0]


@sync_to_async
def check_ban(tg_id):
    user = UserTG.objects.filter(uid=tg_id).first()
    return user.banned if user else False


@sync_to_async
def get_user_info_db(tg_id):
    try:
        user = UserTG.objects.get(uid=tg_id)
        print(f"Got user info - Balance: {user.balance}, Refs: {user.refs}")
        return [user.username, user.uid, user.balance, user.refs, user.invited, user.paid]
    except UserTG.DoesNotExist:
        print(f"User {tg_id} not found in get_user_info_db")
        return None
    except Exception as e:
        print(f"Error in get_user_info_db: {e}")
        return None


@sync_to_async
def plus_ref(tg_id):
    try:
        user = UserTG.objects.select_for_update().get(uid=tg_id)
        user.refs += 1
        user.save()
        print(f"Successfully updated refs for user {tg_id}, new refs count: {user.refs}")
        return True
    except UserTG.DoesNotExist:
        print(f"User {tg_id} not found in plus_ref")
        return False
    except Exception as e:
        print(f"Error in plus_ref for user {tg_id}: {e}")
        return False


@sync_to_async
def plus_money(tg_id):
    try:
        # Get price from AdminInfo
        admin_info = AdminInfo.objects.select_for_update().first()
        if not admin_info:
            print("AdminInfo not found in plus_money")
            return False

        bonus = admin_info.price
        print(f"Got bonus amount: {bonus}")

        # Update user balance
        user = UserTG.objects.select_for_update().get(uid=tg_id)
        old_balance = user.balance
        user.balance = float(old_balance) + float(bonus)
        user.save()

        print(f"Successfully updated balance for user {tg_id}")
        print(f"Old balance: {old_balance}, New balance: {user.balance}")
        return True
    except UserTG.DoesNotExist:
        print(f"User {tg_id} not found in plus_money")
        return False
    except Exception as e:
        print(f"Error in plus_money for user {tg_id}: {e}")
        return False


@sync_to_async
def reg_withdrawals(tg_id, amount, card, bank):
    user = UserTG.objects.get(uid=tg_id)
    withdrawal = Withdrawals.objects.create(
        tg_id=user,
        amount=amount,
        card=card,
        bank=bank,
        reg_date=timezone.now()
    )
    return [withdrawal.id, user.uid, withdrawal.amount, withdrawal.card, withdrawal.bank]



@sync_to_async
def check_for_wa(tg_id):
    return Withdrawals.objects.filter(tg_id=tg_id, status="ожидание").exists()


@sync_to_async
def get_admin_user(bot_token):
    try:
        bot = Bot.objects.select_related("owner").filter(token=bot_token).first()
        if bot and bot.owner:
            return bot.owner.username
        return None
    except Exception as e:
        print(f"Error fetching admin user: {e}")
        return None


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
    return [[w.id, w.tg_id.uid, w.amount, w.card, w.bank] for w in wda]



@sync_to_async
def status_accepted(id_of_wa):
    wda = Withdrawals.objects.filter(id=id_of_wa).first()
    if wda:
        user = wda.tg_id
        if user:
            user.balance -= wda.amount
            user.paid += wda.amount
            user.save()
        wda.status = "принята"
        wda.save()
        return [user.uid, wda.amount]
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
    try:
        admin_info, created = AdminInfo.objects.get_or_create(
            defaults={'price': new_price, 'admin_channel': '', 'min_amount': 50.0}
        )

        if not created:
            admin_info.price = new_price
            admin_info.save()

        print(f"Narx yangilandi: {new_price}, AdminInfo ID: {admin_info.id}")
        return True
    except Exception as e:
        print(f"Narxni yangilashda xatolik: {e}")
        return False


@sync_to_async
def change_min_amount(new_amount):
    AdminInfo.objects.filter(id=2).update(min_amount=new_amount)


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
    """ChannelSponsor modelidan o'qish"""
    try:
        channels = ChannelSponsor.objects.all()
        print(f"Found channels in DB: {list(channels)}")
        return [(c.chanel_id, '') for c in channels]
    except Exception as e:
        logger.error(f"Error getting channels: {e}")
        return []


def add_channel(channel_url, channel_id):
    Channels.objects.create(channel_url=channel_url, channel_id=channel_id)


@sync_to_async
def get_actual_price():
    try:
        admin_info = AdminInfo.objects.first()
        if admin_info and admin_info.price is not None:
            return float(admin_info.price)
        else:
            return 10.0
    except Exception as e:
        logger.error(f"Error getting actual price: {e}")
        return 10.0


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

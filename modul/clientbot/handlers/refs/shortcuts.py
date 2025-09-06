import logging
import traceback

from asgiref.sync import sync_to_async
from django.db import transaction
from django.db.models import F, Sum
from django.utils import timezone
from psycopg2 import IntegrityError

from modul.models import UserTG, Checker, Withdrawals, AdminInfo, Channels, Bot, ChannelSponsor, ClientBotUser

logger = logging.getLogger(__name__)


@sync_to_async
@transaction.atomic
def add_user(tg_id, user_name, invited="Никто", invited_id=None, bot_token=None):
    """
    Eski funksiya - yangi mantiq bilan
    MUHIM: Inviter ni belgilamaydi, faqat foydalanuvchini yaratadi
    """
    try:
        from modul.models import Bot, UserTG, ClientBotUser

        print(f"🔧 DEBUG: refs/shortcuts add_user called for user {tg_id}")

        # Botni topish
        bot_obj = Bot.objects.get(token=bot_token)

        # Allaqachon mavjud yoki yo'qligini tekshirish
        existing_client = ClientBotUser.objects.filter(
            uid=tg_id,
            bot=bot_obj
        ).first()

        if existing_client:
            print(f"⚠️ User {tg_id} already exists for bot {bot_obj.username}")
            return False

        # UserTG ni yaratish yoki olish
        user_tg, created = UserTG.objects.get_or_create(
            uid=tg_id,
            defaults={
                'username': user_name,
                'first_name': user_name,
            }
        )

        if created:
            print(f"✅ DEBUG: Created new UserTG for {tg_id}")
        else:
            print(f"ℹ️ DEBUG: UserTG already exists for {tg_id}")

        # ClientBotUser yaratish - INVITER NI BELGILAMAYDI
        client_user = ClientBotUser.objects.create(
            uid=tg_id,
            user=user_tg,
            bot=bot_obj,
            inviter=None,  # MUHIM: Bu yerda None
            balance=0,
            referral_count=0,
            referral_balance=0
        )

        print(f"✅ DEBUG: refs/shortcuts created ClientBotUser for {tg_id} WITH INVITER=None")
        return True

    except Exception as e:
        print(f"❌ Error in refs/shortcuts add_user: {e}")
        import traceback
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


from asgiref.sync import sync_to_async
from django.db import transaction


@sync_to_async
def get_bot_user_info(user_id, bot_token):
    """
    FAQAT shu bot uchun balans va referrallar - avtomatik ClientBotUser yaratish bilan
    """
    try:
        print(f"DEBUG: get_bot_user_info called with user_id={user_id}, bot_token={bot_token}")

        # Django modellarini import qilish
        from modul.models import Bot, UserTG, ClientBotUser

        # Получаем бота по токену
        bot = Bot.objects.filter(token=bot_token).first()
        if not bot:
            print(f"DEBUG: Bot with token {bot_token} not found")
            return [0, 0]

        print(f"DEBUG: Found bot: id={bot.id}, username={bot.username}")

        # Сначала получаем или создаем UserTG
        user_tg, user_created = UserTG.objects.get_or_create(
            uid=str(user_id),
            defaults={
                'username': f'user_{user_id}',
                'first_name': f'User {user_id}',
                'balance': 0.0,
                'refs': 0
            }
        )

        if user_created:
            print(f"DEBUG: Created new UserTG for user_id={user_id}")
        else:
            print(f"DEBUG: Found existing UserTG: balance={user_tg.balance}, refs={user_tg.refs}")

        # Получаем или создаем ClientBotUser для ЭТОГО БОТА
        client_bot_user, client_created = ClientBotUser.objects.get_or_create(
            uid=user_id,  # Используем uid как в вашем коде
            bot=bot,
            defaults={
                'user': user_tg,  # Связываем с UserTG
                'balance': user_tg.balance,  # Копируем баланс из UserTG
                'referral_count': user_tg.refs  # Копируем refs из UserTG
            }
        )

        if client_created:
            print(f"DEBUG: Created new ClientBotUser for user={user_id} in bot={bot.username}")
            print(
                f"DEBUG: Initialized with balance={client_bot_user.balance}, referral_count={client_bot_user.referral_count}")
        else:
            print(
                f"DEBUG: Found existing ClientBotUser: balance={client_bot_user.balance}, referral_count={client_bot_user.referral_count}")

        # ВОЗВРАЩАЕМ ТОЛЬКО ДАННЫЕ ДЛЯ ЭТОГО БОТА
        bot_balance = client_bot_user.balance  # Баланс только в этом боте
        bot_referrals = client_bot_user.referral_count  # Рефералы только в этом боте

        print(f"DEBUG: Returning BOT-SPECIFIC balance={bot_balance}, referrals={bot_referrals}")
        return [bot_balance, bot_referrals]

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
def change_price(new_price, bot_token):
    try:
        # Получаем бота по токену
        bot = Bot.objects.get(token=bot_token)

        # Получаем или создаем запись AdminInfo для этого бота
        admin_info, created = AdminInfo.objects.get_or_create(
            bot_token=bot_token,
            defaults={
                'admin_channel': '',
                'price': 3.0,
                'min_amount': 30.0
            }
        )

        # Обновляем цену
        admin_info.price = new_price
        admin_info.save()

        print(f"Updated referral price to {new_price} for bot {bot.username}")
        return True
    except Exception as e:
        print(f"Error updating referral price: {e}")
        traceback.print_exc()
        return False


@sync_to_async
def change_min_amount(new_amount: float, bot_token: str = None):
    try:
        logger.info(f"change_min_amount chaqirildi: new_amount={new_amount}, bot_token={bot_token}")

        if bot_token:
            admin_info = AdminInfo.objects.filter(bot_token=bot_token).first()
            if not admin_info:
                admin_info = AdminInfo.objects.create(
                    bot_token=bot_token,
                    admin_channel='@default_channel',
                    min_amount=new_amount,
                    price=3.0
                )
                logger.info(f"Yangi AdminInfo yaratildi: ID={admin_info.id}")
                return True
            else:
                admin_info.min_amount = new_amount
                admin_info.save()
                logger.info(f"AdminInfo yangilandi: ID={admin_info.id}, min_amount={admin_info.min_amount}")
                return True
        else:
            admin_info = AdminInfo.objects.first()
            if admin_info:
                admin_info.min_amount = new_amount
                admin_info.save()
                logger.info(f"AdminInfo yangilandi: ID={admin_info.id}, min_amount={admin_info.min_amount}")
                return True
            else:
                admin_info = AdminInfo.objects.create(
                    admin_channel='@default_channel',
                    min_amount=new_amount,
                    price=3.0
                )
                logger.info(f"Yangi AdminInfo yaratildi: ID={admin_info.id}")
                return True

    except Exception as e:
        logger.error(f"change_min_amount da xatolik: {e}")
        return False


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
def get_actual_price(bot_token=None):
    try:
        if bot_token:
            admin_info = AdminInfo.objects.filter(bot_token=bot_token).first()
            if admin_info and admin_info.price is not None:
                price_value = float(admin_info.price)
                logger.info(f"Found price {price_value} for bot token {bot_token}")
                return price_value  # 0 bo'lsa ham 0 qaytaradi
            else:
                logger.info(f"No AdminInfo found for bot token {bot_token}, using default price")
        else:
            logger.info("No bot token provided, using default price")

        logger.info("Returning default price 3.0")
        return 3.0
    except Exception as e:
        logger.error(f"Error getting actual price: {e}")
        logger.exception("Detailed error stack trace:")
        return 3.0

@sync_to_async
def get_actual_min_amount(bot_token: str = None):

    try:
        if bot_token:
            admin_info = AdminInfo.objects.filter(bot_token=bot_token).first()
        else:
            admin_info = AdminInfo.objects.first()

        if admin_info:
            return float(admin_info.min_amount)
        else:
            return 60.0  # default qiymat

    except Exception as e:
        logger.error(f"get_actual_min_amount error: {e}")
        return 60.0


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

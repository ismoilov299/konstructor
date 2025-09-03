import logging
import traceback

from asgiref.sync import sync_to_async
from django.db import transaction
from django.db.models import Count, F
from django.utils import timezone
from psycopg2 import IntegrityError

from modul.clientbot.shortcuts import get_bot
from modul.models import UserTG, Channels, Messages, Link_statistic, Answer_statistic, Rating_overall, Rating_today, \
    ChannelSponsor, ClientBotUser, Bot, SystemChannel
import pytz

moscow_timezone = pytz.timezone('Europe/Moscow')
logger = logging.getLogger(__name__)


@sync_to_async
def get_channels_for_check():
    try:
        sponsor_channels = ChannelSponsor.objects.all()
        sponsor_list = [(str(c.chanel_id), '') for c in sponsor_channels]
        system_channels = SystemChannel.objects.filter(is_active=True)
        system_list = [(str(c.channel_id), c.channel_url) for c in system_channels]

        all_channels = sponsor_list + system_list

        logger.info(f"Found sponsor channels: {len(sponsor_list)}, system channels: {len(system_list)}")
        return all_channels
    except Exception as e:
        logger.error(f"Error getting channels: {e}")
        return []


@sync_to_async
def check_user(uid):
    return UserTG.objects.filter(uid=uid).exists()


async def add_user(tg_id: int = None, user_id: int = None, user_name: str = None, invited: str = "Никто",
                   invited_id: int = None, user_link: str = None, bot_token: str = None, **kwargs):
    actual_user_id = tg_id or user_id
    logger.info(f"🔧 DEBUG: annon_bot/userservice add_user called for user {actual_user_id}")
    logger.info(f"Parameters: user_name={user_name}, invited={invited}, invited_id={invited_id}, user_link={user_link}")
    user_tg, created = await sync_to_async(UserTG.objects.get_or_create)(
        uid=actual_user_id,
        defaults={
            'username': user_name,
            'first_name': user_name or str(actual_user_id),
            'last_name': '',
            'invited': invited,
            'invited_id': invited_id,
            'user_link': user_link or str(actual_user_id)
        }
    )
    from modul.models import Bot
    bot = await sync_to_async(Bot.objects.filter(enable_anon=True).first)()
    if not bot:
        return None
    inviter_client = None
    if invited_id:
        try:
            logger.info(f"🔍 Searching for inviter {invited_id} in bot {bot.id}")
            inviter_client = await sync_to_async(ClientBotUser.objects.filter(
                uid=invited_id,
                bot=bot
            ).first)()
            logger.info(f"Found inviter client: {inviter_client}")
            if not inviter_client:
                inviter_usertg = await sync_to_async(UserTG.objects.filter(uid=invited_id).first)()
                logger.info(f"Found inviter UserTG: {inviter_usertg}")
                if inviter_usertg:
                    inviter_client = await sync_to_async(ClientBotUser.objects.create)(
                        uid=invited_id,
                        user=inviter_usertg,
                        bot=bot,
                        current_ai_limit=12
                    )
                    logger.info(f"Created inviter ClientBotUser: {inviter_client}")
        except Exception as e:
            logger.error(f"Error finding inviter: {e}")
    client_user, created = await sync_to_async(ClientBotUser.objects.get_or_create)(
        uid=actual_user_id,
        bot=bot,
        defaults={
            'user': user_tg,
            'inviter': inviter_client,  # Bu o'zgartirildi
            'current_ai_limit': 12
        }
    )
    if created:
        logger.info(f"✅ DEBUG: annon_bot created ClientBotUser for {actual_user_id} WITH INVITER={inviter_client}")
    else:
        logger.info(f"🔄 DEBUG: annon_bot found existing ClientBotUser for {actual_user_id}")
    if not user_tg.user_link:
        user_tg.user_link = str(actual_user_id)
        await sync_to_async(user_tg.save)()
        logger.info(f"✅ User_link set to: {user_tg.user_link}")

    return client_user


@sync_to_async
def get_user_by_link(link_or_id):
    user = UserTG.objects.filter(user_link=link_or_id).first()
    if not user:
        user = UserTG.objects.filter(uid=link_or_id).first()
    return user.uid if user else False

@sync_to_async
def get_user_by_id(uid):
    user = UserTG.objects.filter(uid=uid).first()
    return user.uid if user else False

@sync_to_async
def add_messages_info(sender_id, receiver_id, sender_message_id, receiver_message_id):
    Messages.objects.create(
        sender_id=sender_id,
        receiver_id=receiver_id,
        sender_message_id=sender_message_id,
        receiver_message_id=receiver_message_id,
        reg_date=timezone.now().astimezone(moscow_timezone).date()
    )


@sync_to_async
def get_user_link(uid):
    user = UserTG.objects.filter(uid=uid).first()
    return user.user_link if user else False
@sync_to_async
def update_user_link(uid, link):
    UserTG.objects.filter(uid=uid).update(user_link=link)


@sync_to_async
def check_reply(receiver_message_id):
    message = Messages.objects.filter(receiver_message_id=receiver_message_id).first()
    return [message.sender_id, message.sender_message_id] if message else False


@sync_to_async
def change_greeting_user(uid, greeting=None):
    UserTG.objects.filter(uid=uid).update(greeting=greeting)


@sync_to_async
def get_greeting(uid):
    user = UserTG.objects.filter(uid=uid).first()
    return user.greeting if user else False


@sync_to_async
def check_link(link):
    return not UserTG.objects.filter(user_link=link).exists()


@sync_to_async
def change_link_db(uid, new_link):
    UserTG.objects.filter(uid=uid).update(user_link=new_link)


@sync_to_async
def add_rating_today(uid):
    actual_date = timezone.now().astimezone(moscow_timezone).date()
    rating, created = Rating_today.objects.get_or_create(
        user_id=uid,
        reg_date=actual_date,  # Bu qism muammoli bo'lishi mumkin
        defaults={'amount': 1}
    )
    if not created:
        rating.amount = F('amount') + 1
        rating.save()


@sync_to_async
def add_rating_overall(uid):
    rating, created = Rating_overall.objects.get_or_create(
        user_id=uid,
        defaults={'amount': 1, 'reg_date': timezone.now().astimezone(moscow_timezone).date()}
    )
    if not created:
        rating.amount = F('amount') + 1
        rating.save()


@sync_to_async
def add_link_statistic(uid):
    def create_link():
        return Link_statistic.objects.create(
            user_id=uid,
            reg_date=timezone.now().astimezone(moscow_timezone)
        )

    stat = create_link()
    return uid


async def add_stats(uid):
    user_id = await add_link_statistic(uid)
    await add_rating_today(user_id)
    await add_rating_overall(user_id)

    return user_id

@sync_to_async
def add_answer_statistic(uid):
    Answer_statistic.objects.create(
        user_id=uid,
        reg_date=timezone.now().astimezone(moscow_timezone).date()
    )


def value_handler(num):
    return num or 0


@sync_to_async
def get_all_statistic(uid: int):
    today_start = timezone.now().astimezone(moscow_timezone).replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start.replace(hour=23, minute=59, second=59, microsecond=999999)

    messages_today = Messages.objects.filter(receiver_id=uid, reg_date__range=(today_start, today_end)).count()
    messages_overall = Messages.objects.filter(receiver_id=uid).count()
    answers_today = Answer_statistic.objects.filter(user_id=uid, reg_date__range=(today_start, today_end)).count()
    answers_overall = Answer_statistic.objects.filter(user_id=uid).count()
    links_today = Link_statistic.objects.filter(user_id=uid, reg_date__range=(today_start, today_end)).count()
    links_overall = Link_statistic.objects.filter(user_id=uid).count()

    rating_today = Rating_today.objects.filter(reg_date__range=(today_start, today_end)).order_by('-amount')
    rating_overall = Rating_overall.objects.order_by('-amount')

    position_today = next((i for i, r in enumerate(rating_today, 1) if r.user_id == uid), "1000+")
    position_overall = next((i for i, r in enumerate(rating_overall, 1) if r.user_id == uid), "1000+")

    return {
        "messages_today": value_handler(messages_today),
        "answers_today": value_handler(answers_today),
        "links_today": value_handler(links_today),
        "position_today": position_today,
        "messages_overall": messages_overall,
        "answers_overall": answers_overall,
        "links_overall": links_overall,
        "position_overall": position_overall
    }
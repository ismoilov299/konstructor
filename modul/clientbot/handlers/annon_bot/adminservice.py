from asgiref.sync import sync_to_async
from modul.models import UserTG, Channels


@sync_to_async
def get_channels_for_admin():
    all_channels = Channels.objects.all()
    if all_channels:
        return [[i.id, i.channel_url, i.channel_id] for i in all_channels]
    return []


@sync_to_async
def add_new_channel_db(url, id):
    new_channel = Channels(channel_url=url, channel_id=id)
    new_channel.save()
    return True


@sync_to_async
def delete_channel_db(id):
    try:
        channel = Channels.objects.get(id=id)
        channel.delete()
        return True
    except Channels.DoesNotExist:
        return False


@sync_to_async
def get_all_users_tg_id():
    users = UserTG.objects.all()
    return [i.uid for i in users]


@sync_to_async
def get_users_count():
    return UserTG.objects.count()

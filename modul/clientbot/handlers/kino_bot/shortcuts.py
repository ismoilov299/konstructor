from modul.models import ChannelSponsor
from asgiref.sync import sync_to_async


@sync_to_async
def create_channel_sponsor(channel_id: int):
    ChannelSponsor.objects.get_or_create(channel_id=channel_id)
    return


@sync_to_async
def remove_channel_sponsor(channel_id: int) -> None:
    channel = ChannelSponsor.objects.filter(channel_id=channel_id).first()
    channel.delete()


@sync_to_async
def get_all_channels_sponsors() -> list:
    return list(ChannelSponsor.objects.values_list('chanel_id', flat=True))

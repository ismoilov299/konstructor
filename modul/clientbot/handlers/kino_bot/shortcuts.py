from modul.models import ChannelSponsor, SystemChannel
from asgiref.sync import sync_to_async


@sync_to_async
def create_channel_sponsor(channel_id: int):
    ChannelSponsor.objects.get_or_create(chanel_id=channel_id)
    return

@sync_to_async
def remove_channel_sponsor(channel_id):
    try:
        kanal = ChannelSponsor.objects.get(chanel_id=channel_id)
        kanal.delete()
        print(f"Kanal {channel_id} muvaffaqiyatli o‘chirildi.")
    except ChannelSponsor.DoesNotExist:
        print(f"Kanal {channel_id} topilmadi.")


@sync_to_async
def get_all_channels_sponsors() -> list:
    try:
        sponsor_channels = list(ChannelSponsor.objects.values_list('chanel_id', flat=True))
        system_channels = list(SystemChannel.objects.filter(is_active=True).values_list('channel_id', flat=True))
        all_channels = sponsor_channels + system_channels
        return all_channels
    except Exception as e:
        return []

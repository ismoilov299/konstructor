
import pandas as pd
from io import BytesIO
from datetime import datetime
from asgiref.sync import sync_to_async
import tempfile
import os


@sync_to_async
def convert_to_excel(user_id, bot_token=None):
    from modul.models import UserTG, ClientBotUser, Bot
    import pandas as pd
    from io import BytesIO

    if bot_token:
        try:
            bot = Bot.objects.get(token=bot_token)
            client_users = ClientBotUser.objects.filter(
                bot=bot,
                inviter__uid=user_id
            ).select_related('user')

            user_ids = [client_user.user.uid for client_user in client_users]

            users = UserTG.objects.filter(uid__in=user_ids).values(
                'id',
                'uid',
                'username',
                'balance',
                'paid',
                'refs',
                'invited',
                'invited_id',
                'banned',
                'created_at'
            )
        except Bot.DoesNotExist:
            users = UserTG.objects.filter(invited_id=user_id).values(
                'id',
                'uid',
                'username',
                'balance',
                'paid',
                'refs',
                'invited',
                'invited_id',
                'banned',
                'created_at'
            )
    else:
        users = UserTG.objects.filter(invited_id=user_id).values(
            'id',
            'uid',
            'username',
            'balance',
            'paid',
            'refs',
            'invited',
            'invited_id',
            'banned',
            'created_at'
        )

    if not users.exists():
        raise ValueError("Kerakli ma'lumotlar topilmadi")

    df = pd.DataFrame(list(users))

    df.rename(columns={
        'id': 'user_id',
        'uid': 'tg_id',
        'username': 'user_name',
        'balance': 'balance',
        'paid': 'paid',
        'refs': 'refs',
        'invited': 'invited',
        'invited_id': 'invited_id',
        'banned': 'banned',
        'created_at': 'reg_date'
    }, inplace=True)

    df['reg_date'] = df['reg_date'].dt.tz_localize(None).dt.strftime('%Y-%m-%d %H:%M:%S')

    excel_file = BytesIO()
    df.to_excel(excel_file, index=False, engine='openpyxl')
    excel_file.seek(0)

    return excel_file.getvalue(), f"referrals_{user_id}.xlsx"


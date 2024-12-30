
import pandas as pd
from io import BytesIO
from datetime import datetime
from asgiref.sync import sync_to_async

@sync_to_async
def convert_to_excel(user_id):
    from modul.models import UserTG

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

    # Formatlash
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
    return excel_file




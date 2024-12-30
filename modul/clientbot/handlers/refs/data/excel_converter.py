from modul.models import User

from tempfile import NamedTemporaryFile
from asgiref.sync import sync_to_async
import pandas as pd


@sync_to_async
def fetch_user_data(user_id):
    users = User.objects.filter(uid=user_id).values()
    if not users.exists():
        raise ValueError("Foydalanuvchi topilmadi!")
    return list(users)

async def convert_to_excel(user_id):
    try:
        users = await fetch_user_data(user_id)
        df = pd.DataFrame(users)

        for column in df.select_dtypes(include=["datetime64[ns, UTC]", "datetime64[ns]"]).columns:
            df[column] = df[column].dt.tz_localize(None)

        temp_file = NamedTemporaryFile(delete=False, suffix=".xlsx")
        df.to_excel(temp_file.name, index=False)
        return temp_file.name

    except Exception as e:
        print(f"Xato yuz berdi: {e}")
        raise



from modul.models import User

from asgiref.sync import sync_to_async
from io import BytesIO
import pandas as pd
from datetime import date
import random

from asgiref.sync import sync_to_async
from io import BytesIO
import pandas as pd
from datetime import date
import random

from asgiref.sync import sync_to_async
from io import BytesIO
import pandas as pd
from datetime import date
import random

@sync_to_async
def fetch_user_data(user_id):

    users = User.objects.filter(uid=user_id).values()
    if not users.exists():
        raise ValueError("Foydalanuvchilar topilmadi!")
    return list(users)

async def convert_to_excel(user_id):

    try:
        users = await fetch_user_data(user_id)

        df = pd.DataFrame(users)

        for column in df.select_dtypes(include=["datetime64[ns, UTC]", "datetime64[ns]"]).columns:
            df[column] = df[column].dt.tz_localize(None)

        file_name = f"Referals_{user_id}_{date.today()}_{random.randint(1, 1000)}.xlsx"

        buffer = BytesIO()
        df.to_excel(buffer, index=False)
        buffer.seek(0)

        return buffer, file_name

    except Exception as e:
        print(f"Xato yuz berdi: {e}")
        raise


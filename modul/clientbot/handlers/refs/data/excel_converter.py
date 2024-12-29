import pandas as pd
import sqlite3
import random
from datetime import date


from io import BytesIO
from django.http import HttpResponse
import pandas as pd
from modul.models import User

def convert_to_excel(user_id):

    try:
        users = User.objects.filter(uid=user_id).values()

        if not users.exists():
            raise ValueError("Foydalanuvchilar topilmadi!")

        df = pd.DataFrame(users)

        file_name = f"Referals_{user_id}_{date.today()}_{random.randint(1, 1000)}.xlsx"
        buffer = BytesIO()
        df.to_excel(buffer, index=False)
        buffer.seek(0)

        return buffer, file_name

    except Exception as e:
        print(f"Xato yuz berdi: {e}")
        raise


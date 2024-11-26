import pandas as pd
import sqlite3
import random
from datetime import date


def convert_to_excel(id):
    # TODO скорректировать название бд если у каждого будет индивидуальная
    conn = sqlite3.connect('db.sqlite3')
    df = pd.read_sql_query(f"SELECT * FROM user WHERE invited_id={id}", conn)
    conn.close()
    name = "Referals" + f"{id}_" + str(date.today()) + "_" + str(random.randint(1, 1000))
    df.to_excel(f'{name}.xlsx', index=False)
    return f'{name}.xlsx'

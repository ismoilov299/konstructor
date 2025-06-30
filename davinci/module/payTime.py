from aiogram import Bot, Dispatcher, executor, types
from aiogram.utils.exceptions import BotBlocked
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import StatesGroup, State
from aiogram.dispatcher import FSMContext
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

import os.path
import time
import re
import math


from loader import *
from sql import *
from function import *
import module

async def payTime_install():
    # добавление в таблицу users столбцов users
    table_colomn = []
    cur.execute("SELECT * FROM information_schema.columns WHERE table_name = 'users'")
    for row in cur.fetchall():
        table_colomn.append(row['column_name'])
    if 'pay_time' not in table_colomn:
        cur.execute("ALTER TABLE users ADD COLUMN pay_time INT DEFAULT 0")

    payTime_list = {
        0: {'name': "1 день", 'day': 1, 'recurrent': True, 'smile': '💰'},
        1: {'name': "2 дня", 'day': 2, 'recurrent': True, 'smile': '💰'},
        2: {'name': "3 дня", 'day': 3, 'recurrent': True, 'smile': '💰'},
        3: {'name': "4 дня", 'day': 4, 'recurrent': True, 'smile': '💰'},
        4: {'name': "5 дней", 'day': 5, 'recurrent': True, 'smile': '💰'},
        5: {'name': "6 дней", 'day': 6, 'recurrent': True, 'smile': '💰'},
        6: {'name': "10 дней", 'day': 10, 'recurrent': True, 'smile': '💰'},
        7: {'name': "1 неделя", 'day': 7, 'recurrent': True, 'smile': '💰'},
        8: {'name': "2 недели", 'day': 14, 'recurrent': True, 'smile': '💰'},
        9: {'name': "3 недели", 'day': 21, 'recurrent': True, 'smile': '💰'},
        10: {'name': "1 месяц", 'day': 30, 'recurrent': True, 'smile': '💰'},
        11: {'name': "2 месяца", 'day': 61, 'recurrent': True, 'smile': '💰'},
        12: {'name': "3 месяца", 'day': 91, 'recurrent': True, 'smile': '💰'},
        13: {'name': "4 месяца", 'day': 122, 'recurrent': True, 'smile': '💰'},
        14: {'name': "5 месяцев", 'day': 152, 'recurrent': True, 'smile': '💰'},
        15: {'name': "6 месяцев", 'day': 183, 'recurrent': True, 'smile': '💰'},
        16: {'name': "7 месяцев", 'day': 213, 'recurrent': True, 'smile': '💰'},
        17: {'name': "8 месяцев", 'day': 244, 'recurrent': True, 'smile': '💰'},
        18: {'name': "9 месяцев", 'day': 274, 'recurrent': True, 'smile': '💰'},
        19: {'name': "10 месяцев", 'day': 305, 'recurrent': True, 'smile': '💰'},
        20: {'name': "11 месяцев", 'day': 335, 'recurrent': True, 'smile': '💰'},
        21: {'name': "1 год", 'day': 365, 'recurrent': True, 'smile': '💰'},
        22: {'name': "Навсегда", 'day': 3650, 'recurrent': False, 'smile': '💰'},
    }

    save = await saver('add', {'setting': {
        "payTime_price": '{}',
        "payTime_list": str(payTime_list),
        "payTime_start_vip_free": 0,
        "pay_payFree_message": "Приведи друзей и за каждого получишь +1 день VIP 👑\n\nТвои друзья должны перейти по реферальной ссылке:\n%РЕФКА% \nи подписаться на каналы\n\nВы привели: %РЕФКАОТЧЕТ%",
        "payTime_cron_message": str({"text": "%ИМЯ%, ваше VIP 👑 закончился, чтобы продлить VIP перейдите в оплату"}).replace("'", '"')
    }})

    payTime_list = eval(save['setting']['payTime_list'])
    if 'smile' not in payTime_list[0]:
        payTime_list_new = {}
        for k, v in payTime_list.items():
            v['smile'] = '💰'
            payTime_list_new[k] = v
        save = await saver('replace', {'setting': {"payTime_list": str(payTime_list_new).replace("'", '"')}})


# кнопка payTime_
@dp.callback_query_handler(lambda callback_query: callback_query.data.startswith('payTime_'), state='*')
async def payTime_callback(tg: types.CallbackQuery, state: FSMContext):
    save = await saver()
    if tg.from_user.id in eval(save['setting']['ban_users']):
        return False
    await send(tg, {'callback': True})
    error=''
    m = {0: {}}
    page = await page_split(tg.data)
    memory = await memory_start(state)
    if page['page'] == 'userAdd3':
        async with state.proxy() as data:
            userAdd = data['payTime_userAdd']
        cur.execute("SELECT * FROM users WHERE user_id = '{}' LIMIT 1".format(userAdd['user_id']))
        for row in cur.fetchall():
            userLoad = dict(row)
        now = int(time.time())
        pay_time = int(userLoad['pay_time'])
        payTime_list = eval(save['setting']['payTime_list'])
        time_plus = (payTime_list[int(page['param'])]['day'] * 24 * 60 * 60)
        if pay_time >= now:
            new_date = pay_time + time_plus
            answer = await send(tg, {'text': '✅ VIP успешно добавлен'})
        else:
            new_date = now + time_plus
            answer = await send(tg, {'text': '✅ VIP успешно выдан'})
        memory['mes_new'].append(answer.message_id)
        cur.execute("UPDATE users SET pay_time = '{}' WHERE user_id = '{}'".format(new_date, userAdd['user_id']))
        page['page'] = 'userList'
        memory['dop'] = await payTime_dop(tg, state, page, error)
        # пишем юзеру что выдали вип
        forever = now + (5 * 365 * 24 * 60 * 60) # + 5 лет
        if new_date > forever:
            date_finish = "навсегда"
        else:
            date_finish = datetime.datetime.fromtimestamp(new_date)
            date_finish = date_finish.strftime('%Y-%m-%d %H:%M')
            date_finish = f"до {date_finish}"
        await send(userLoad['user_id'], {'text': f"👑 Вам выдали VIP доступ {date_finish}"})
    elif page['page'] == 'priceClean':
        async with state.proxy() as data:
            if 'payTime_priceId' in data:
                priceId = data['payTime_priceId']
                payTime_price = eval(save['setting']['payTime_price'])
                payTime_price.pop(priceId)
                payTime_price = str(payTime_price).replace("'", '"')
                save = await saver('replace', {"setting": {"payTime_price": payTime_price }})
        page['page'] = 'priceList'
        memory['dop'] = await payTime_dop(tg, state, page, error)
    elif page['page'] == 'smileClean':
        async with state.proxy() as data:
            if 'payTime_priceId' in data:
                priceId = data['payTime_priceId']
                payTime_list = eval(save['setting']['payTime_list'])
                payTime_list[priceId]['smile'] = ''
                save = await saver('replace', {'setting': {"payTime_list": str(payTime_list).replace("'", '"')}})
        page['page'] = 'priceEdit'
        memory['dop'] = await payTime_dop(tg, state, page, error)
    elif page['page'] == 'payOnePaid':
        cur.execute("SELECT * FROM pay_wallet WHERE active = 1")
        for row in cur.fetchall():
            pay_wallet = dict(row)
        if pay_wallet:
            m[0]['text'] = pay_wallet['token'] # тут написан юзернейм админа по которому обратиться после оплаты
            async with state.proxy() as data:
                if 'pay_back' in data:
                    back_callback_data = data['pay_back']
                else:
                    back_callback_data = ''
            if back_callback_data:
                m[0]['but'] = [[{'text': but_back, 'callback_data': back_callback_data}]]
    elif page['page'] == 'yyy':
        m[0]['text'] = "Текст"
        m[0]['but'] = [[{'text': but_back, 'callback_data': "payTime_go"}]]
        answer = await send(tg, {'text': 'текст'})
        memory['mes_new'].append(answer.message_id)
        page['page'] = 'yy'
        memory['dop'] = await payTime_dop(tg, state, page, error)
    else:
        # все остальные действия где мы просто перекидываем в ДОП
        memory['dop'] = await payTime_dop(tg, state, page)
    await memory_finish(tg, state, memory, page, m)

# текст
async def payTime_message(tg, state, page):
    save = await saver()
    error=''
    m = {0: {}}
    memory = await memory_start(state)
    if page['page'] == 'userDelete' and 'text' in tg:
        cust = ''
        text = tg.text.replace('https://t.me/', '@')
        if re.search(r'^@|A-Z|a-z|0-9|_]{4,}$', text):
            text = text.replace("@", "")
            cur.execute("SELECT * FROM users WHERE username = '{}'".format(text))
            for row in cur.fetchall():
                cust = dict(row)
        elif re.search(r'^[1-9][0-9]*$', text):
            cur.execute("SELECT * FROM users WHERE user_id = '{}' LIMIT 1".format(text))
            for row in cur.fetchall():
                cust = dict(row)
        else:
            error = f"❌ Не верный ввод пользователя"
        if cust:
            cur.execute("UPDATE users SET pay_time = '{}' WHERE user_id = '{}'".format(int(time.time()), cust['user_id']))
            answer = await send(tg, {'text': '✖️ VIP удален'})
            memory['mes_new'].append(answer.message_id)
            page['page'] = 'userList'
        elif not error:
            error = f"❌ Данного пользователя нет в боте"
        memory['dop'] = await payTime_dop(tg, state, page, error)
    elif page['page'] == 'userAdd' and 'text' in tg:
        userAdd = ''
        text = tg.text.replace('https://t.me/', '@')
        if re.search(r'^@|A-Z|a-z|0-9|_]{4,}$', text):
            text = text.replace("@", "")
            cur.execute("SELECT * FROM users WHERE username = '{}'".format(text))
            for row in cur.fetchall():
                userAdd = dict(row)
        elif re.search(r'^[1-9][0-9]*$', text):
            cur.execute("SELECT * FROM users WHERE user_id = '{}' LIMIT 1".format(text))
            for row in cur.fetchall():
                userAdd = dict(row)
        else:
            error = f"❌ Не верный ввод пользователя"
        if userAdd:
            async with state.proxy() as data:
                data['payTime_userAdd'] = userAdd
            page['page'] = 'userAdd2'
        elif not error:
            error = f"❌ Данного пользователя нет в боте"
        memory['dop'] = await payTime_dop(tg, state, page, error)
    elif page['page'] == 'priceEdit' and 'text' in tg:
        text = tg.text
        if re.search(r'^[1-9][0-9]*$', text):
            async with state.proxy() as data:
                if 'payTime_priceId' in data:
                    priceId = data['payTime_priceId']
                    payTime_price = eval(save['setting']['payTime_price'])
                    payTime_price[priceId] = int(text)
                    payTime_price = dict(sorted(payTime_price.items()))
                    payTime_price = str(payTime_price).replace("'", '"')
                    save = await saver('replace', {"setting": {"payTime_price": payTime_price }})
            page['page'] = 'priceList'
        elif re.search(r'^.{1}$', text):
            print(f'smile = {text}')
            async with state.proxy() as data:
                if 'payTime_priceId' in data:
                    priceId = data['payTime_priceId']
                    payTime_list = eval(save['setting']['payTime_list'])
                    payTime_list[priceId]['smile'] = text
                    save = await saver('replace', {'setting': {"payTime_list": str(payTime_list).replace("'", '"')}})
            page['page'] = 'priceList'
        else:
            error = f"❌ Разрешено только цифры больше нуля или смайлик"
        memory['dop'] = await payTime_dop(tg, state, page, error)
    elif page['page'] == 'startVipFree' and 'text' in tg:
        text = tg.text
        if re.search(r'^[0-9]*$', text):
            text = int(text)
            save = await saver('replace', {"setting": {"payTime_start_vip_free": text}})
            answer = await send(tg, {'text': '✅ Время успешно изменено'})
            memory['mes_new'].append(answer.message_id)
        else:
            error = f"❌ Не вверный ввод, разрешено только цифры"
        memory['dop'] = await payTime_dop(tg, state, page, error)
    elif page['page'] == 'userListDelete' and 'text' in tg:
        text = tg.text
        if re.search(r'^/delete_[1-9][0-9]*$', text):
            user_del = int(text.split('_')[1])
            answer = await send(tg, {'text': '✅ VIP удален'})
            memory['mes_new'].append(answer.message_id)
            cur.execute("UPDATE users SET pay_time = '{}' WHERE id = '{}'".format(int(time.time()), user_del))
        else:
            error = f"❌ Не известная команда"
        memory['dop'] = await payTime_dop(tg, state, page, error)
    elif page['page'] == 'userList' and 'text' in tg:
        page['page'] = 'userListOne'
        memory['dop'] = await payTime_dop(tg, state, page, error)
    elif page['page'] == 'yyy' and 'text' in tg:
        m[0]['text'] = 'текст'
        m[0]['but'] = [[{'text': but_back, 'callback_data': "payTime_go"}]]
        answer = await send(tg, {'text': 'текст'})
        memory['mes_new'].append(answer.message_id)
        error = f"❌ Данный ID канала уже существует"
        page['page'] = 'yy'
        memory['dop'] = await payTime_dop(tg, state, page, error)
        memory['page_new'] = 'payTime_xx'
    else:
        memory['stop'] = True
        memory['dop'] = await payTime_dop(tg, state, page, error)
    await memory_finish(tg, state, memory, page, m)

async def payTime_dop(tg, state, page, error_mes=False):
    save = await saver()
    if tg.from_user.id in eval(save['setting']['ban_users']):
        return False
    error = ''
    m = {0: {}}
    memory = await memory_start(state, load_memory=False)
    if page['page'] == 'userList':
        forever = int(time.time()) + (3 * 365 * 24 * 60 * 60)
        m[0]['text'] = f"🫅 Список VIP юзеров:\n"
        ul = await userList(tg, state, page="payTime_userList", sql_where=f"pay_time >= {int(time.time())}")
        for row in ul['list']:
            full_name = f"{row['first_name']} {row['last_name']}".strip()
            m[0]['text'] += f"\n\n<a href='tg://user?id={row['user_id']}'>{row['user_id']} {full_name}</a>"
            if row['username']:
                m[0]['text'] += f" @{row['username']}"
            if row['pay_time'] > forever:
                m[0]['text'] += f"\n👑 Навсегда"
            else:
                m[0]['text'] += f"\n👑 До {datetime.datetime.fromtimestamp(row['pay_time']).strftime('%Y-%m-%d %H:%M')}"
            m[0]['text'] += f"   /delete_{row['id']}"
        m[0]['text'] += f"\n\n<i>Напишите ID или @username, чтобы получить информацию по данному человеку</i>"
        m[0]['but'] = []
        if ul['but']:
            m[0]['but'].append(ul['but'])
        m[0]['but'].append([{'text': "🎁 Выдать VIP доступ", 'callback_data': "payTime_userAdd"}])
        m[0]['but'].append([{'text': "✖️ Удалить VIP доступ", 'callback_data': "payTime_userDelete"}])
        m[0]['but'].append([{'text': but_back, 'callback_data': "pay_adminMenu"}])
    elif page['page'] == 'userListOne':
        text = tg.text.replace('https://', '').replace('t.me/', '').replace('@', '').replace('"', '').replace("'", '')
        cust = False
        now = int(time.time())
        if re.search(r'^/delete_[0-9]+$', text):
            text = text.replace('/delete_', '')
            answer = await send(tg, {'text': '✅ VIP удален'})
            memory['mes_new'].append(answer.message_id)
            cur.execute("UPDATE users SET pay_time = '{}' WHERE id = '{}'".format(now, text))
            page['page'] = 'userList'
            memory['dop'] = await payTime_dop(tg, state, page, error)
        else:
            if re.search(r'^[0-9]+$', text):
                cur.execute("SELECT * FROM users WHERE user_id = '{}' LIMIT 1".format(text))
                for row in cur.fetchall():
                    cust = dict(row)
            elif re.search(r'^[a-z|0-9|A-Z|_]{3,}$', text):
                cur.execute("SELECT * FROM users WHERE username = '{}' LIMIT 1".format(text))
                for row in cur.fetchall():
                    cust = dict(row)
            if not cust:
                m[0]['text'] = '❌ Пользователь не найден в базе бота'
            else:
                m[0]['text'] = f"👤 Пользователь: \n<a href='tg://user?id={cust['user_id']}'>{cust['user_id']}</a>\n"
                m[0]['text'] += f"{row['first_name']} {row['last_name']}".strip()
                if row['username']:
                    m[0]['text'] += f"\n@{row['username']}"
                if cust['pay_time'] < now:
                    m[0]['text'] += '\n\n✖️ У пользователя нет VIP статуса'
                elif cust['pay_time'] >= now:
                    us_date = "навсегда" if cust['pay_time'] > (now + (3 * 365 * 24 * 60 * 60)) else f"до {datetime.datetime.fromtimestamp(cust['pay_time']).strftime('%Y-%m-%d %H:%M')}"
                    m[0]['text'] += f'\n\n👑 VIP {us_date}'
            m[0]['but'] = [[{'text': but_back, 'callback_data': "payTime_userList"}]]
    elif page['page'] == 'userDelete':
        m[0]['text'] = "Введите @username пользователя или его Id, у кого убрать VIP доступ"
        m[0]['but'] = [[{'text': but_back, 'callback_data': "payTime_userList"}]]
    elif page['page'] == 'userAdd':
        m[0]['text'] = "Введите @username пользователя или его Id, чтоб выдать ему VIP доступ"
        m[0]['but'] = [[{'text': but_back, 'callback_data': "payTime_userList"}]]
    elif page['page'] == 'userAdd2':
        m[0]['text'] = "Выберите на какой срок выдать VIP (Если у юзера уже был VIP то это добавит ему этот срок):"
        m[0]['but'] = []
        dop = []
        payTime_list = eval(save['setting']['payTime_list'])
        for key, one in payTime_list.items():
            dop.append({'text': one['name'], 'callback_data': f"payTime_userAdd3_{key}"})
            if len(dop) >= 2:
                m[0]['but'].append(dop)
                dop = []
        if dop:
            m[0]['but'].append(dop)
        m[0]['but'].append([{'text': but_back, 'callback_data': "payTime_userList"}])
    elif page['page'] == 'startVipFree':
        m[0]['text'] = '<b>Бесплатный VIP: '
        hour = int(save['setting']['payTime_start_vip_free'])
        if hour >= 43800:
            m[0]['text'] += f"навсегда"
        elif hour >= 24:
            day = math.floor(hour / 24)
            m[0]['text'] += f"{await data_count(day)} ({hour} {await words(hour, 'час')})"
        else:
            m[0]['text'] += f"{hour} {await words(hour, 'час')}"
        m[0]['text'] += "</b>"
        m[0]['text'] += "\n\nЧтобы изменить кол-во часов, пришлите цифру, на которую нужно изменить"
        m[0]['text'] += "\n\n<i>На сколько часов после того как юзер первый раз попал в бот, он получит бесплатный VIP. "
        m[0]['text'] += "Если нужно в днях используйте: 24 часа = 1 день, 48 часов = 2 дня и т.д</i>"
        m[0]['but'] = [[{'text': but_back, 'callback_data': "pay_adminMenu"}]]
    elif page['page'] == 'priceList':
        m[0]['text'] = "Настройка цен VIP:\n\n* Пользователю показывает только те кнопки, где есть цена"
        m[0]['but'] = []
        dop = []
        payTime_price = eval(save['setting']['payTime_price'])
        payTime_list = eval(save['setting']['payTime_list'])
        for key, one in payTime_list.items():
            if key in payTime_price:
                mes = f"✅ {one['name']} за {payTime_price[key]} р"
                if one['smile']:
                    mes += f" - {one['smile']}"
            else:
                mes = f"➖ {one['name']} "
            dop.append({'text': mes, 'callback_data': f"payTime_priceEdit_{key}"})
            if len(dop) >= 2:
                m[0]['but'].append(dop)
                dop = []
        if dop:
            m[0]['but'].append(dop)
        m[0]['but'].append([{'text': but_back, 'callback_data': "pay_adminMenu"}])
    elif page['page'] == 'priceEdit':
        async with state.proxy() as data:
            if page['param'] or page['param'] == '0':
                data['payTime_priceId'] = int(page['param'])
            if 'payTime_priceId' in data:
                priceId = data['payTime_priceId']
        if priceId or priceId == 0:
            payTime_price = eval(save['setting']['payTime_price'])
            payTime_list = eval(save['setting']['payTime_list'])
            m[0]['text'] = f"Срок: {payTime_list[priceId]['name']}"
            m[0]['but'] = []
            if priceId in payTime_price:
                m[0]['text'] += f"\n\nСтарая цена: {payTime_price[priceId]} р"
                m[0]['text'] += f"\n\nСмайлик: {payTime_list[priceId]['smile']}"
                m[0]['text'] += f"\n\nПришлите цифру, чтобы изменить цену или пришлите смайлик, чтоб изменить смайлик"
                m[0]['but'].append([{'text': "✖️ Удалить цену", 'callback_data': "payTime_priceClean"}])
                m[0]['but'].append([{'text': "✖️ Скрыть смайлик", 'callback_data': "payTime_smileClean"}])
            else:
                m[0]['text'] += "\n\nНапишите цену, чтоб данный период появился у юзера"
            m[0]['but'].append([{'text': but_back, 'callback_data': "payTime_priceList"}])
        else:
            page['page'] = 'priceList'
            memory['dop'] = await payTime_dop(tg, state, page, error)
    elif page['page'] == 'payList': # соощение VIP или PAY
        async with state.proxy() as data:
            if page['param'] and page['param_2']:
                back_callback_data = f"{page['param']}_{page['param_2']}"
                data['pay_back'] = back_callback_data
            else:
                back_callback_data = data['pay_back'] if 'pay_back' in data else ''
        m[0] = await show_message_from_setting('pay', tg) # "Преимущества VIP 👑: ..."
        m[0]['but'] = []
        payTime_price = eval(save['setting']['payTime_price'])
        for key, one in payTime_price.items():
            payTime_list = eval(save['setting']['payTime_list'])
            m[0]['but'].append([{'text': f"{payTime_list[key]['smile']} {payTime_list[key]['name']} за {one} р", 'callback_data': f'payTime_payOne_{key}'}])
        if int(save['setting']['pay_payFree']):
            m[0]['but'].append([{'text': save['setting']['pay_payFree_Button'], 'callback_data': 'payTime_mesFree'}])
        if back_callback_data:
            m[0]['but'].append([{'text': but_back, 'callback_data': back_callback_data}])
    elif page['page'] == 'mesFree':
        m[0]['text'] = save['setting']['pay_payFree_message']
        m[0]['but'] = [[{'text': but_back, 'callback_data': f"payTime_payList"}]]
        m[0] = await message_replace(tg.from_user, m[0], module='payTime')
    elif page['page'] == 'payOne':
        pay_wallet = ''
        cur.execute("SELECT * FROM pay_wallet WHERE active = 1")
        for row in cur.fetchall():
            pay_wallet = dict(row)
        if not page['param']:
            page['page'] = 'payList'
            memory['dop'] = await payTime_dop(tg, state, page, error)
        elif pay_wallet:
            pay_id = int(page['param'])
            payTime_price = eval(save['setting']['payTime_price'])
            if pay_id in payTime_price:
                payTime_list = eval(save['setting']['payTime_list'])
                if pay_wallet['company'] == 'manual':
                    m[0]['text'] = f"Для оплаты доступа на {payTime_list[pay_id]['name']}"
                    m[0]['text'] += f" сделайте перевод в размере {payTime_price[pay_id]}р на карту 👇"
                    m[0]['text'] += f"\n\n<code>{pay_wallet['shop_id']}</code>"
                    m[0]['text'] += f"\n\nи нажмите Я ОПЛАТИЛ"
                    m[0]['but'] = [[
                        {'text': "✅ Я ОПЛАТИЛ", 'callback_data': "payTime_payOnePaid"},
                        {'text': but_back, 'callback_data': "payTime_payList"},
                    ]]
                else:
                    m[0]['text'] = f"👑 Оплата за  VIP аккаунт\n\n🕔 Срок: {payTime_list[pay_id]['name']}\n💵 Цена: {payTime_price[pay_id]}р"
                    m[0]['but'] = [[
                        {'text': but_back, 'callback_data': "payTime_payList"},
                        {'text': "💳 ОПЛАТИТЬ", 'url': f"https://{pay_link}/?bot={save['bot']['username']}&user={tg.from_user.id}&time={pay_id}"}
                    ]]
            else:
                m[0]['text'] = "Ошибка оплаты"
                m[0]['but'] = [[{'text': but_back, 'callback_data': "payTime_payList"}]]
        else:
            m[0]['text'] = "Ошибка оплаты"
            m[0]['but'] = [[{'text': but_back, 'callback_data': "payTime_payList"}]]
    elif page['page'] == 'xx':
        m[0]['text'] = "Текст"
        m[0]['but'] = [[{'text': but_back, 'callback_data': "payTime_go"}]]
        answer = await send(tg, {'text': 'текст'})
        memory['mes_new'].append(answer.message_id)
        page['page'] = 'yy'
        memory['dop'] = await payTime_dop(tg, state, page, error)
    if error_mes and 'text' in m[0]:
        m[0]['text'] = f'{error_mes}\n\n{m[0]["text"]}'
    await memory_finish(tg, state, memory, page, m, dop=True)
    return True # чтоб не было дублежа записи page

async def payTime_check(tg, state):
    now = int(time.time())
    async with state.proxy() as data:
        if 'user' not in data:
            data['user'] = await sql_user_add(tg.from_user)
        else:
            if int(data['user']['pay_time']) < now: # если вип то нету смысла проверять верность даты вип
                # приходиться обновлять каждый раз, иначе вдруг он получил ВИП, а его state не в курсе
                cur.execute("SELECT pay_time FROM users WHERE user_id = '{}' LIMIT 1".format(tg.from_user.id))
                for row in cur.fetchall():
                    data['user']['pay_time'] = row['pay_time']
        user = data['user']
        if int(user['pay_time']) > now:
            return True # Пользователь VIP
        else:
            return False

async def startVipFree(user, state):
    save = await saver()
    vip_free = int(save['setting']['payTime_start_vip_free'])
    if vip_free > 0:
        new_time = int(time.time()) + (vip_free * 60 * 60)
        cur.execute("UPDATE users SET pay_time = '{}' WHERE user_id = '{}'".format(new_time, user['user_id']))
        async with state.proxy() as data:
            data['payTimeFree'] = new_time
            data['user']['pay_time'] = new_time
            user = data['user']
    return user

async def startVipFree_message(tg, state):
    save = await saver()
    hour = int(save['setting']['payTime_start_vip_free'])
    if hour >= 43800:
        time = "навсегда"
    elif hour >= 24:
        time = await data_count(math.floor(hour / 24))
    else:
        time = f"{hour} {await words(hour, 'час')}"
    mes = f"🎊 <b>Вы получили бесплатный VIP 👑 на {time}</b>"
    await send(tg.from_user.id, {'text': mes})
    async with state.proxy() as data:
        data.pop('payTimeFree')

async def payTime_free_vip(tg, referal):
    cur.execute("SELECT COUNT(*) FROM users WHERE user_id = '{}'".format(tg.from_user.id))
    if not cur.fetchall()[0]['count']:
        sec_plus = 24 * 60 * 60
        now = int(time.time())
        user_id = str(referal).replace('u', '')
        cust = ''
        cur.execute("SELECT * FROM users WHERE user_id = '{}' LIMIT 1".format(user_id))
        for row in cur.fetchall():
            cust = dict(row)
        print(f'payTime_free_vip = {referal} | {cust}')
        if cust:
            if int(cust['pay_time']) < now:
                plus = now + sec_plus
            else:
                plus = int(cust['pay_time']) + sec_plus
            cur.execute("UPDATE users SET pay_time = '{}' WHERE user_id = '{}'".format(plus, user_id))
            mes = f"🎊 <b>Вы привели пользователя по вашей реферальной ссылке, вы получаете бесплатный VIP 👑 на 1 день</b>"
            await send(user_id, {'text': mes})


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
import asyncio # паузы await asyncio.sleep(1)

import matplotlib.pyplot as plt
import numpy as np



async def pay_install():

    cur.execute("""CREATE TABLE IF NOT EXISTS pay_wallet (
                id SERIAL PRIMARY KEY,
                active INT DEFAULT 0, 
                company TEXT NOT NULL DEFAULT '',
                shop_id TEXT NOT NULL DEFAULT '', 
                phone TEXT NOT NULL DEFAULT '',
                token TEXT NOT NULL DEFAULT '',
                token2 TEXT NOT NULL DEFAULT '',
                other TEXT NOT NULL DEFAULT '')""")
    # где other = {любые дополниетльные данные в словаре}

    # ========== добавление колонок в op
    table_colomn = []
    cur.execute("SELECT * FROM information_schema.columns WHERE table_name = 'pay_wallet'")
    for row in cur.fetchall():
        table_colomn.append(row['column_name'])
    if 'other' not in table_colomn:
        cur.execute("ALTER TABLE pay_wallet ADD COLUMN other TEXT NOT NULL DEFAULT ''")
    if 'token2' not in table_colomn:
        cur.execute("ALTER TABLE pay_wallet ADD COLUMN token2 TEXT NOT NULL DEFAULT ''")

    cur.execute("""CREATE TABLE IF NOT EXISTS pay_payment (
                id SERIAL PRIMARY KEY,
                wallet_id INT DEFAULT 0,
                user_id TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT '',
                date_pay TEXT NOT NULL DEFAULT '',
                price FLOAT DEFAULT 0,
                types TEXT NOT NULL DEFAULT '',
                option INT DEFAULT 0,
                recurrent TEXT NOT NULL DEFAULT '',
                answer TEXT NOT NULL DEFAULT '',
                good TEXT NOT NULL DEFAULT '')""")


    table_colomn = []
    cur.execute("SELECT * FROM information_schema.columns WHERE table_name = 'pay_payment'")
    for row in cur.fetchall():
        table_colomn.append(row['column_name'])
    if 'recurrent' not in table_colomn:
        cur.execute("ALTER TABLE pay_payment ADD COLUMN recurrent TEXT NOT NULL DEFAULT ''")
    if 'date_pay' not in table_colomn:
        cur.execute("ALTER TABLE pay_payment ADD COLUMN date_pay TEXT NOT NULL DEFAULT ''")
    if 'types' not in table_colomn:
        cur.execute("ALTER TABLE pay_payment ADD COLUMN types TEXT NOT NULL DEFAULT ''")
    if 'good' not in table_colomn:
        cur.execute("ALTER TABLE pay_payment ADD COLUMN good TEXT NOT NULL DEFAULT ''")

    # ========== добавление колонок в users
    table_colomn = []
    cur.execute("SELECT * FROM information_schema.columns WHERE table_name = 'users'")
    for row in cur.fetchall():
        table_colomn.append(row['column_name'])
    if module_main == 'bot':
        if await module.bot.bot_balance():
            if 'balance' not in table_colomn:
                cur.execute("ALTER TABLE users ADD COLUMN balance FLOAT DEFAULT 0")
                cur.execute("SELECT * FROM pay_payment WHERE status = 'paid'")
                for row in cur.fetchall():
                    cur.execute("UPDATE users SET balance = balance + {} WHERE user_id = '{}'".format(float(row['price']), row['user_id']))

    save = await saver()
    if "pay_messageText" in save['setting']: # из старой версии в новую
        save = await saver('add', {'setting': {
            "pay_message_text": save['setting']['pay_messageText'],
            "pay_message_entities": save['setting']['pay_messageEntities'],
            "pay_message_fileType": save['setting']['pay_messageFileType'],
            "pay_message_fileId": save['setting']['pay_messageFileId'],
        }})
        save = await saver('drop', {'setting': ['pay_messageText', 'pay_messageEntities', 'pay_messageFileType', 'pay_messageFileId']})
    if "pay_message_text" not in save['setting']:
        if 'anon' in modules:
            pay_message_text = "Преимущества VIP 👑:"
            pay_message_text += "\n\n⚜️ Возможен поиск по полу (мужской и женский)"
            pay_message_text += "\n\n⚜️ Возможность общаться в Пошлома чате 💃🏻"
            pay_message_text += "\n\n⚜️ Возможность отправлять и получать от собеседника фото/видео"
            pay_message_text += "\n\n⚜️ Собеседник попадается мгновенно"
            pay_message_text += "\n\n⚜️ Отключается реклама"
            pay_message_text += "\n\n⚜️ Больше не надо подписыватся на каналы"
            pay_message_text += "\n\n✅ VIP выдаётся сразу после оплаты"
        elif 'rating' in modules:
            pay_message_text = "Преимущества VIP 👑:"
            pay_message_text += "\n\n⚜️ ОТКРЫТИЕ"
            pay_message_text += "\n     ➕ Позволит узнать кто оценил твою анкету, и даст на него ссылку. Одно ОТКРЫТИЕ = 1 ссылка на юзера"
            pay_message_text += "\n\n👑 VIP"
            pay_message_text += "\n     ➕ Отключается реклама"
            pay_message_text += "\n     ➕ Больше не надо подписываться на каналы"
            pay_message_text += "\n     ➕ Около вашего имени в анкете будет написано: 👑 VIP"
            pay_message_text += "\n\n✅ VIP выдаётся сразу после оплаты и НАВСЕГДА"
        elif 'clicker' in modules:
            pay_message_text = "Преимущества VIP 👑:"
            pay_message_text += "\n\n⚜️ Каждый КЛИК у VIP приносит 5 робуксов вместо 1"
            pay_message_text += "\n\n⚜️ Отключается реклама"
            pay_message_text += "\n\n⚜️ Больше не надо подписываться на каналы"
            pay_message_text += "\n\n✅ VIP выдаётся сразу после оплаты"
        else:
            pay_message_text = "Преимущества VIP 👑:"
            pay_message_text += "\n\n⚜️ Отключается реклама"
            pay_message_text += "\n\n⚜️ Больше не надо подписываться на каналы"
            pay_message_text += "\n\n✅ VIP выдаётся сразу после оплаты"
        save = await saver('add', {'setting': {
            "pay_message_text": pay_message_text,
            "pay_message_entities": "[]",
        }})

    if "pay_message_fileType" not in save['setting']:
        pay_message_fileId = ''
        if os.path.exists('files'):
            try:
                with open('files/pay/pay.jpg', 'rb') as photo:
                    answer = await bot.send_photo(355590439, photo=photo)
                if 'message_id' in answer:
                    await bot.delete_message(chat_id=355590439, message_id=answer['message_id'])
                    pay_message_fileId = answer['photo'][0]['file_id']
            except Exception as ex:
                pass
        else:
            print("!!!!!!!!!!!!!!  Not folder 'files'")
            sys.exit()
        save = await saver('add', {'setting': {
            "pay_message_fileType": "photo",
            "pay_message_fileId": pay_message_fileId,
        }})

    if 'op' in modules:
        save = await saver('add', {'setting': {
            "pay_payShowInOp": 1, # показывать кнопку "👎 Не хочу подписываться" в ОП
            "pay_OP_messageButton": "👎 Не хочу подписываться",
        }})
    save = await saver('add', {'setting': {
        "pay_payFree": 1,
        "pay_payFree_Button": "Получить бесплатно!",
        "pay_walletDescription": f"Оплата в боте @{save['bot']['username']}"
    }})

    pay_folder = 'files/image_pay_graph'
    if not os.path.exists(pay_folder):
        os.mkdir(pay_folder)


# кнопка pay_
@dp.callback_query_handler(lambda callback_query: callback_query.data.startswith('pay_'), state='*')
async def pay_callback(tg: types.CallbackQuery, state: FSMContext):
    save = await saver()
    if tg.from_user.id in eval(save['setting']['ban_users']):
        return False
    # user = await user_load(tg, state)
    await send(tg, {'callback': True})
    error = ''
    m = {0: {}}
    page = await page_split(tg.data)
    memory = await memory_start(state)
    if page['page'] == 'walletAdd':
        m[0]['text'] = "Выберите тип кошелька:"
        m[0]['but'] = [
            [{'text': "🇷🇺 aaio.so", 'callback_data': "pay_walletAddAaioSo"}],
            [{'text': "🇷🇺 Юmoney", 'callback_data': "pay_walletAddYoomoney"}],
            [{'text': "🇷🇺 Qiwi", 'callback_data': "pay_walletAddQiwi"}],
            # [{'text': "СloudPayments (Widget)", 'callback_data': "pay_walletAddСloudPaymentsWidget"}],
            [{'text': "🇷🇺 Payselection (рекуррентный)", 'callback_data': "pay_walletAddPayselection"}],
            [{'text': "🇷🇺🇰🇿 Robokassa", 'callback_data': "pay_walletAddRobokassa"}],
            [{'text': "🇧🇾 WebPay.by (для Беларуси)", 'callback_data': "pay_walletAddCommon_WebpayBy"}],
            [{'text': "🇧🇾 BePaid.by (для Беларуси)", 'callback_data': "pay_walletAddCommon_BepaidBy"}],
            [{'text': "Ручная оплата", 'callback_data': "pay_walletManual"}],
            [{'text': but_back, 'callback_data': "pay_walletList"}]
        ]
    elif page['page'] == 'walletOne':
        walletId = int(page['param'])
        async with state.proxy() as data:
            data['pay_walletId'] = walletId
        cur.execute("SELECT * FROM pay_wallet WHERE id = '{}'".format(walletId))
        for row in cur.fetchall():
            wal = dict(row)
        m[0]['text'] = f"Настройка кошелька № {wal['id']} - <b>{wal['company']}</b>"
        if row['company'] == 'manual':
            m[0]['text'] += f"\n\n➖ Номер карты:\n{await hide_string(wal['shop_id'])}"
            m[0]['text'] += f"\n\n➖ Сообщение после оплаты:\n{wal['token']}"
        else:
            m[0]['text'] += f"\n\n➖ ID магазина:\n{wal['shop_id']}"
            if wal['token']:
                m[0]['text'] += f"\n\n➖ Токен:\n{await hide_string(wal['token'])}"
        if wal['other']:
            other = eval(wal['other'])
            if 'recurrent_repeat_payment' in other : # {'recurrent_period_type': 'day', 'recurrent_period_count': 3}
                m[0]['text'] += f"\n\n➖ Рекуррентный платеж:\n"
                if 'recurrent_period_type' in other and 'recurrent_period_type' in other:
                    m[0]['text'] += f"каждые {other['recurrent_period_count']} {other['recurrent_period_type']} по {other['recurrent_price']} "
                else:
                    m[0]['text'] += "Такой же как при оплате первый раз"
        m[0]['but'] = []
        m[0]['but'].append([{'text': "❌ Удалить кошелек", 'callback_data': "pay_walletDelete"}])
        if not wal['active']:
            m[0]['but'].append([{'text': "✔️ Принимать на этот кошелек", 'callback_data': "pay_walletThis"}])
        m[0]['but'].append([{'text': but_back, 'callback_data': "pay_walletList"}])
    elif page['page'] == 'walletDelete':
        async with state.proxy() as data:
            walletId = data['pay_walletId']
        cur.execute("DELETE FROM pay_wallet WHERE id = '{}'".format(walletId))
        answer = await bot.send_message(chat_id=tg.from_user.id, text="✅ Кошелек удален")
        memory['mes_new'].append(answer.message_id)
        page['page'] = 'walletList'
        memory['dop'] = await pay_dop(tg, state, page, error)
    elif page['page'] == 'walletThis':
        async with state.proxy() as data:
            walletId = data['pay_walletId']
        cur.execute("UPDATE pay_wallet SET active = 0")
        cur.execute("UPDATE pay_wallet SET active = 1 WHERE id = '{}'".format(walletId))
        page['page'] = 'walletList'
        memory['dop'] = await pay_dop(tg, state, page, error)
    elif page['page'] == 'showInOp':
        pay_payShowInOp = 0 if int(save['setting']['pay_payShowInOp']) else 1
        save = await saver('replace', {"setting": {"pay_payShowInOp": pay_payShowInOp}})
        page['page'] = 'adminMenu'
        memory['dop'] = await pay_dop(tg, state, page, error)
    elif page['page'] == 'showInFree':
        pay_payFree = 0 if int(save['setting']['pay_payFree']) else 1
        save = await saver('replace', {"setting": {"pay_payFree": pay_payFree}})
        page['page'] = 'adminMenu'
        memory['dop'] = await pay_dop(tg, state, page, error)
    elif page['page'] == 'walletAddPayselection4':
        if page['param']:
            if int(page['param']): # если рекуррентный платеж такой же как первый
                async with state.proxy() as data:
                    cur.execute("SELECT COUNT(*) FROM pay_wallet")
                    active = 0 if cur.fetchall()[0]['count'] else 1
                    other_param = str({'recurrent_repeat_payment': 1})
                    cur.execute("INSERT INTO pay_wallet (active, company, shop_id, token, other) VALUES (%s, %s, %s, %s, %s)", [active, 'Payselection', data['pay_walletAdd'], data['pay_walletAdd2'], other_param])
                    page['page'] = 'walletList'
                    answer = await bot.send_message(chat_id=tg.from_user.id, text="✅ Платежка Payselection успешно добавлена")
                    memory['mes_new'].append(answer.message_id)
            else: # если рекуррентный платеж надо настроить
                async with state.proxy() as data:
                    data['pay_walletAdd3'] = 0
        else:
            page['page'] = 'walletAddYoomoney3'
        memory['dop'] = await pay_dop(tg, state, page, error)
    elif page['page'] == 'walletAddPayselection5':
        if page['param']:
            async with state.proxy() as data:
                data['pay_walletAdd4'] = page['param']
        else:
            page['page'] = 'walletAddYoomoney4'
        memory['dop'] = await pay_dop(tg, state, page, error)
    elif page['page'] == 'statistic':
        mes = {}
        mes['photo'] = 'files/loading_graph.jpg'
        mes['text'] = '⏳ Загрузка информации...'
        answer = await send(tg.from_user.id, mes)
        message_id = answer.message_id
        memory['mes_new'].append(message_id)
        cur.execute("SELECT SUM(price) FROM pay_payment WHERE status = 'paid' or status = 'recurrent'")
        pay_sum = cur.fetchall()[0]['sum']
        if not pay_sum:
            pay_sum = 0
        mes['text'] = f"Общий заработок: {await money(pay_sum)}"
        if 'pay_time' in modules:
            cur.execute("SELECT COUNT(*) FROM users WHERE pay_time >= '{}'".format(int(time.time())))
            count = cur.fetchall()[0]['count']
            mes['text'] += f"\n\n👑 VIP пользователей: {await money(count)}"
            mes['text'] += f"\n\n👑 VIP:"
        pay_option = {}
        cur.execute("SELECT DISTINCT option FROM pay_payment")
        for row in cur.fetchall():
            cur.execute("SELECT SUM(price) FROM pay_payment WHERE status = 'paid' AND option = '{}'".format(row['option']))
            pay_option[row['option']] = cur.fetchall()[0]['sum']
        if 'pay_time' in modules:
            payTime_list = eval(save['setting']['payTime_list'])
            payTime_list['Рекуррентный'] = {'name': 'Рекуррентный'}
            for k, v in pay_option.items():
                mes['text'] += f"\n{payTime_list[k]['name']}: {await money(v)}"
        mes['but'] = [[{'text': but_back, 'callback_data': "pay_adminMenu"}]]
        mes['message_id'] = message_id
        await send(tg.from_user.id, {'caption': mes['text'], 'message_id': message_id, 'but': mes['but']})
        ###### график
        # создаем и очищаем папку
        info_folder = 'files/graph'
        image = f'{info_folder}/pay.jpg'
        if not os.path.exists(info_folder):
            os.mkdir(info_folder)
        elif os.path.exists(image):
            os.remove(image)
        # загружаем инфу
        x = [] # дата
        y1 = [] # сумма задень
        y2 = [] # кол-во покупок за день
        y1_max = 0
        y2_max = 0
        pay_sum_max = 1
        now = datetime.datetime.now()
        for i in range(20):
            date_pay = now - datetime.timedelta(days=i)
            date_check = date_pay.strftime("%Y-%m-%d")
            date_start = f"{date_check} 00:00:00"
            date_finish = f"{date_check} 23:59:59"
            cur.execute("SELECT COUNT(*) FROM pay_payment WHERE date_pay >= '{}' AND date_pay <= '{}' AND (status = 'paid' or status = 'recurrent')".format(date_start, date_finish))
            count = cur.fetchall()[0]['count']
            y2.append(count)
            if y1_max < count:
                y1_max = count
            cur.execute("SELECT SUM(price) FROM pay_payment WHERE date_pay >= '{}' AND date_pay <= '{}' AND (status = 'paid' or status = 'recurrent')".format(date_start, date_finish))
            pay_sum = cur.fetchall()[0]['sum']
            if not pay_sum:
                pay_sum = 0
            y1.append(pay_sum - count)
            x_date = date_pay.strftime("%d %m")
            x_date = x_date[1:] if int(x_date[:1]) == 0 else x_date
            x.append(x_date)
            if pay_sum_max < pay_sum:
                pay_sum_max = pay_sum
        x.reverse()
        y1.reverse()
        y2.reverse()

        ######## Рисуем график
        x_len = np.arange(len(x))  # the label locations
        width = 0.75  # ширина полосок вертикальных

        fig, ax = plt.subplots(layout='constrained', figsize=(10, 6))

        rects = ax.bar(x_len, y2, width, label='y2', color='orange')
        ax.bar_label(rects, padding=3, color='white')

        rects = ax.bar(x_len, y1, width, label='y1', color='orange', bottom=y2)
        ax.bar_label(rects, padding=3)

        ax.set_xticks(x_len + width - 0.8, x, rotation=66)
        pay_sum_max = pay_sum_max + 1 if pay_sum_max <= 10 else pay_sum_max + round(pay_sum_max / 10)
        ax.set_ylim(0, pay_sum_max)

        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_visible(False)
        ax.spines['bottom'].set_color('#DDDDDD')
        ax.tick_params(bottom=True, left=False, grid_color='#DDDDDD')
        ax.set_axisbelow(True)
        ax.yaxis.grid(True, color='#EEEEEE')
        ax.xaxis.grid(False)
        ax.set_title('Статистика прибыли за последние 20 дней')

        plt.savefig(image) # сохраняем

        await send(tg, {'photo': image, 'text': mes['text'], 'message_id': message_id, 'but': mes['but']})
        # with open(image, 'rb') as photo:
        #     im = types.input_media.InputMediaPhoto(photo, caption=mes['text'])
        #     await send(tg, {'media': im,  'message_id': message_id, 'but': mes['but']})
    elif page['page'] == 'yyy':
        m[0]['text'] = "Текст"
        m[0]['but'] = [[{'text': but_back, 'callback_data': "pay_go"}]]
        answer = await send(tg, {'text': 'текст'})
        memory['mes_new'].append(answer.message_id)
        page['page'] = 'yy'
        memory['dop'] = await pay_dop(tg, state, page, error)
    else:
        # все остальные действия где мы просто перекидываем в ДОП
        memory['dop'] = await pay_dop(tg, state, page)
    await memory_finish(tg, state, memory, page, m)

# текст
async def pay_message(tg, state, page):
    save = await saver()
    error = ''
    m = {0: {}}
    memory = await memory_start(state)
    if page['page'] == 'walletAddCommon' and 'text' in tg: # Общий для ввода ID_магазина и токена
        async with state.proxy() as data:
            if 'pay_walletAdd' in data:
                company = data['pay_walletAdd']['company']
                text = tg.text.replace(" ", '')
                if re.search(r'^[1-9][0-9]{3,}$', text):
                    wal = False
                    cur.execute("SELECT * FROM pay_wallet WHERE company = '{}' and shop_id = '{}'".format(company, text))
                    for row in cur.fetchall():
                        wal = dict(row)
                    if not wal:
                        data['pay_walletAdd']['shop_id'] = text
                        page['page'] = 'walletAddCommon2'
                    else:
                        error = f"❌ Данный ID Магазина уже есть в базе"
                else:
                    error = f"❌ Не верный ID Магазина, разрешено только цифры."
            else:
                page['page'] = 'walletList'
        memory['dop'] = await pay_dop(tg, state, page, error)
    elif page['page'] == 'walletAddCommon2' and 'text' in tg: # Общий для ввода ID_магазина и токена
        async with state.proxy() as data:
            if 'pay_walletAdd' in data:
                text = tg.text.replace(" ", '')
                if re.search(r'^[0-9|a-z|A-Z]{10,}$', text):
                    cur.execute("SELECT COUNT(*) FROM pay_wallet")
                    active = 0 if cur.fetchall()[0]['count'] else 1
                    company = data['pay_walletAdd']['company']
                    shop_id = data['pay_walletAdd']['shop_id']
                    cur.execute("INSERT INTO pay_wallet (active, company, shop_id, token) VALUES (%s, %s, %s, %s)", [active, company, shop_id, text])
                    page['page'] = 'walletList'
                    if company == 'WebpayBy':
                        name = 'Webpay.by'
                    elif company == 'BepaidBy':
                        name = 'BePaid.by'
                    else:
                        name = company
                    answer = await bot.send_message(chat_id=tg.from_user.id, text=f"✅ Платежка {name} успешно добавлена")
                    memory['mes_new'].append(answer.message_id)
                else:
                    error = f"❌ Не верный секретный ключ, разрешено только цифры и буквы. 10 символов или больше"
            else:
                page['page'] = 'walletList'
        memory['dop'] = await pay_dop(tg, state, page, error)
    elif page['page'] == 'walletAddQiwi' and 'text' in tg:  # Qiwi
        text = tg.text.replace(" ", '')
        if re.search(r'^[0-9|a-z]{189}$', text):
            wal = False
            cur.execute("SELECT * FROM pay_wallet WHERE company = '{}' and token = ".format('Qiwi', text))
            for row in cur.fetchall():
                wal = dict(row)
            if not wal:
                cur.execute("SELECT COUNT(*) FROM pay_wallet")
                count = cur.fetchall()[0]['count']
                if count:
                    active = 0
                else:
                    active = 1
                cur.execute("INSERT INTO pay_wallet (active, company, shop_id, token) VALUES (%s, %s, %s, %s)", [active, 'Qiwi', '', text])
                page['page'] = 'walletList'
                answer = await bot.send_message(chat_id=tg.from_user.id, text="✅ Платежка Qiwi успешно добавлена")
                memory['mes_new'].append(answer.message_id)
            else:
                error = f"❌ Данный токен Qiwi уже существует"
        else:
            error = f"❌ Не верный номер кошелька (разрешено только цифры и буквы), либо токен вставлен не полностью"
        memory['dop'] = await pay_dop(tg, state, page, error)
    elif page['page'] == 'walletAddAaioSo' and 'text' in tg: # aaio.so
        text = tg.text.replace(" ", '')
        if re.search(r'^[0-9|a-z|A-Z|-]{36}$', text):
            wal = False
            cur.execute("SELECT * FROM pay_wallet WHERE company = '{}' and shop_id = '{}'".format('AaioSo', text))
            for row in cur.fetchall():
                wal = dict(row)
            if not wal:
                async with state.proxy() as data:
                    data['pay_walletAdd'] = text
                page['page'] = 'walletAddAaioSo2'
            else:
                error = f"❌ Данный ID Магазина уже есть в базе"
        else:
            error = f"❌ Не верный ID Магазина, разрешено только цифры, буквы и тире. Он выглядит прмиерно вот так:\n4d101317-1111-22e2-a33f-d322251abefa"
        memory['dop'] = await pay_dop(tg, state, page, error)
    elif page['page'] == 'walletAddAaioSo2' and 'text' in tg: # aaio.so
        text = tg.text.replace(" ", '')
        if re.search(r'^[0-9|a-z|A-Z]{32}$', text):
            cur.execute("SELECT COUNT(*) FROM pay_wallet")
            active = 0 if cur.fetchall()[0]['count'] else 1
            async with state.proxy() as data:
                cur.execute("INSERT INTO pay_wallet (active, company, shop_id, token) VALUES (%s, %s, %s, %s)", [active, 'AaioSo', data['pay_walletAdd'], text])
            page['page'] = 'walletList'
            answer = await bot.send_message(chat_id=tg.from_user.id, text="✅ Платежка aaio.so успешно добавлена")
            memory['mes_new'].append(answer.message_id)
        else:
            error = f"❌ Не верный секретный ключ, разрешено только цифры и буквы"
        memory['dop'] = await pay_dop(tg, state, page, error)
    elif page['page'] == 'walletAddYoomoney' and 'text' in tg:  # YooMoney
        text = tg.text.replace(" ", '')
        if re.search(r'^[0-9]{10,}$', text):
            wal = False
            cur.execute("SELECT * FROM pay_wallet WHERE company = '{}' and shop_id = '{}'".format('YooMoney', text))
            for row in cur.fetchall():
                wal = dict(row)
            if not wal:
                async with state.proxy() as data:
                    data['pay_walletAdd'] = text
                page['page'] = 'walletAddYoomoney2'
            else:
                error = f"❌ Данный номер кошелька Юмани уже существует"
        else:
            error = f"❌ Не верный номер кошелька, разрешено только цифры"
        memory['dop'] = await pay_dop(tg, state, page, error)
    elif page['page'] == 'walletAddYoomoney2' and 'text' in tg:  # YooMoney
        text = tg.text
        if re.search(r'^[0-9|a-z|A-Z|+|/]{10,}$', text):
            cur.execute("SELECT COUNT(*) FROM pay_wallet")
            active = 0 if cur.fetchall()[0]['count'] else 1
            async with state.proxy() as data:
                cur.execute("INSERT INTO pay_wallet (active, company, shop_id, token) VALUES (%s, %s, %s, %s)",
                            [active, 'YooMoney', data['pay_walletAdd'], text])
            page['page'] = 'walletList'
            answer = await bot.send_message(chat_id=tg.from_user.id, text="✅ Платежка YooMoney успешно добавлена")
            memory['mes_new'].append(answer.message_id)
        else:
            error = f"❌ Не верный номер кошелька, разрешено только цифры и буквы"
        memory['dop'] = await pay_dop(tg, state, page, error)
    elif page['page'] == 'walletAddRobokassa' and 'text' in tg: # YooMoney
        text = tg.text.replace(" ", '')
        if re.search(r'^[0-9|a-z|A-Z|_]{2,}$', text):
            cur.execute("SELECT * FROM pay_wallet WHERE company = 'Robokassa' and shop_id = '{}'".format(text))
            for row in cur.fetchall():
                wal = dict(row)
            if 'wal' not in locals():
                async with state.proxy() as data:
                    data['pay_walletAdd'] = text
                page['page'] = 'walletAddRobokassa2'
            else:
                error = f"❌ Данный идентификатор магазина Robokassa уже существует"
        else:
            error = f"❌ Не верный номер кошелька, разрешено только цифры, буквы и нижнее подчеркивание"
        memory['dop'] = await pay_dop(tg, state, page, error)
    elif page['page'] == 'walletAddRobokassa2' and 'text' in tg: # YooMoney
        text = tg.text
        if re.search(r'^[0-9|a-z|A-Z]{3,}$', text):
            cur.execute("SELECT COUNT(*) FROM pay_wallet")
            active = 0 if cur.fetchall()[0]['count'] else 1
            async with state.proxy() as data:
                cur.execute("INSERT INTO pay_wallet (active, company, shop_id, token) VALUES (%s, %s, %s, %s)", [active, 'Robokassa', data['pay_walletAdd'], text])
            page['page'] = 'walletList'
            answer = await bot.send_message(chat_id=tg.from_user.id, text="✅ Платежка Robokassa успешно добавлена")
            memory['mes_new'].append(answer.message_id)
        else:
            error = f"❌ Не верный номер кошелька, разрешено только цифры и буквы"
        memory['dop'] = await pay_dop(tg, state, page, error)
    elif page['page'] == 'walletManual' and 'text' in tg:
        text = tg.text
        if text[:1] == '@':
            text = text[1:]
        text.replace('<', '').replace('>', '')
        async with state.proxy() as data:
            data['pay_walletAdd'] = text
        page['page'] = 'walletManual2'
        memory['dop'] = await pay_dop(tg, state, page, error)
    elif page['page'] == 'walletManual2' and 'text' in tg:
        async with state.proxy() as data:
            wallet_1 = data['pay_walletAdd']
        text = tg.text
        if text[:1] == '@':
            text = text[1:]
        text.replace('<', '').replace('>', '')
        cur.execute("SELECT COUNT(*) FROM pay_wallet")
        count = cur.fetchall()[0]['count']
        if count:
            active = 0
        else:
            active = 1
        cur.execute("INSERT INTO pay_wallet (active, company, shop_id, token) VALUES (%s, %s, %s, %s)", [active, 'manual', wallet_1, text])
        page['page'] = 'walletList'
        answer = await bot.send_message(chat_id=tg.from_user.id, text="✅ Ручная оплата успешно добавлена")
        memory['mes_new'].append(answer.message_id)
        memory['dop'] = await pay_dop(tg, state, page, error)
    elif page['page'] == 'walletAddСloudPaymentsWidget': # СloudPayments Widget
        text = tg.text
        if re.search(r'^[0-9|a-z|A-Z|_]{10,}$', text):
            cur.execute("SELECT COUNT(*) FROM pay_wallet")
            count = cur.fetchall()[0]['count']
            if count:
                active = 0
            else:
                active = 1
            cur.execute("INSERT INTO pay_wallet (active, company, token) VALUES (%s, %s, %s)", [active, 'СloudPaymentsWidget', text])
            page['page'] = 'walletList'
            answer = await bot.send_message(chat_id=tg.from_user.id, text="✅ Платежка СloudPayments Widget успешно добавлена")
            memory['mes_new'].append(answer.message_id)
        else:
            error = f"❌ Не верный номер Public ID, разрешено только цифры, буквы и подчеркивание"
        memory['dop'] = await pay_dop(tg, state, page, error)
    elif page['page'] == 'walletAddPayselection' and 'text' in tg: # Payselection
        text = tg.text
        if re.search(r'^[1-9][0-9]{4,5}$', text):
            wal = False
            cur.execute("SELECT * FROM pay_wallet WHERE company = '{}' and shop_id = '{}'".format('Payselection', text))
            for row in cur.fetchall():
                wal = dict(row)
            if not wal:
                async with state.proxy() as data:
                    data['pay_walletAdd'] = text
                page['page'] = 'walletAddPayselection2'
            else:
                error = f"❌ Данный номер кошелька Payselection уже существует"
        else:
            error = f"❌ Не верный номер кошелька, разрешено только цифры"
        memory['dop'] = await pay_dop(tg, state, page, error)
    elif page['page'] == 'walletAddPayselection2' and 'text' in tg: # Payselection
        text = tg.text
        if re.search(r'^[0-9|a-z]{130}$', text):
            async with state.proxy() as data:
                data['pay_walletAdd2'] = text
            page['page'] = 'walletAddPayselection9'

        else:
            error = f"❌ Не верный публичный ключ, разрешено только цифры и буквы нижнего регистра. Ключ должен быть длинный, имеет 130 символов."
        memory['dop'] = await pay_dop(tg, state, page, error)
    elif page['page'] == 'walletAddPayselection9' and 'text' in tg: # Payselection
        text = tg.text
        if re.search(r'^[0-9|a-z|A-Z]{16}$', text):
            async with state.proxy() as data:
                data['pay_walletAdd9'] = text
            page['page'] = 'walletAddPayselection3'
        else:
            error = f"❌ Не верный публичный ключ, разрешено только цифры и буквы нижнего регистра. Ключ  имеет 16 символов."
        memory['dop'] = await pay_dop(tg, state, page, error)
    elif page['page'] == 'walletAddPayselection5' and 'text' in tg: # Payselection
        text = tg.text
        if re.search(r'^[1-9][0-9]*$', text):
            async with state.proxy() as data:
                data['pay_walletAdd5'] = text
            page['page'] = 'walletAddPayselection6'
        else:
            error = f"❌ Не верный ввод, разрешено только цифры"
        memory['dop'] = await pay_dop(tg, state, page, error)
    elif page['page'] == 'walletAddPayselection6' and 'text' in tg: # Payselection
        text = tg.text
        if re.search(r'^[1-9][0-9]*$', text):
            cur.execute("SELECT COUNT(*) FROM pay_wallet")
            active = 0 if cur.fetchall()[0]['count'] else 1
            async with state.proxy() as data:
                other_param = str({'recurrent_repeat_payment': data['pay_walletAdd3'] ,'recurrent_period_type': data['pay_walletAdd4'], 'recurrent_period_count': data['pay_walletAdd5'], 'recurrent_price': int(text)})
                cur.execute("INSERT INTO pay_wallet (active, company, shop_id, token, token2, other) VALUES (%s, %s, %s, %s, %s, %s)", [active, 'Payselection', data['pay_walletAdd'], data['pay_walletAdd2'], data['pay_walletAdd9'], other_param])
            page['page'] = 'walletList'
            answer = await bot.send_message(chat_id=tg.from_user.id, text="✅ Платежка Payselection успешно добавлена")
            memory['mes_new'].append(answer.message_id)
        else:
            error = f"❌ Не верный ввод, разрешено только цифры"
        memory['dop'] = await pay_dop(tg, state, page, error)
    elif page['page'] == 'editCronMessage':
        mes_tg = await message_load(tg, button=False, file=True)
        if not await message_change(tg, state, mes_tg, eval(save['setting']['payTime_cron_message']), setting_name='payTime_cron_message'):
            return False # если грузили галерею, то только первое сообщение пропустим, остальные тормознем
        memory['page_new'] = 'editCronMessage'
        memory['dop'] = await pay_dop(tg, state, page, error)
    elif page['page'] == 'editMessage':
        await message_processing(tg, 'pay', button=False, save_setting=True)
        memory['dop'] = await pay_dop(tg, state, page, error)
    elif page['page'] == 'priceOneSet' and 'text' in tg:
        text = tg.text.replace(',', '.')
        if re.search(r'^(0|[1-9][0-9]*)(\.[0-9]{1,2})?$', text):
            save = await saver('replace', {'setting': {"pay_price": float(text)}})
            answer = await send(tg, {'text': f'✅ Цена успешно изменена на {text}'})
            memory['mes_new'].append(answer.message_id)
            page['page'] = 'adminMenu'
        else:
            error = f"❌ Не вверный ввод, возможнотолько цифры"
        memory['dop'] = await pay_dop(tg, state, page, error)
    elif page['page'] == 'userBalanceEdit' and 'text' in tg:
        text = tg.text.replace('https://', '').replace('t.me/', '').replace('@', '')
        cust = {}
        cust_check = False
        if re.search(r'^[0-9]+$', text):
            cust_check = True
            cur.execute("SELECT * FROM users WHERE user_id = '{}'".format(text))
            for row in cur.fetchall():
                cust = dict(row)
        elif re.search(r'^[0-9|a-z|_]+$', text):
            cust_check = True
            cur.execute("SELECT * FROM users WHERE username = '{}'".format(text))
            for row in cur.fetchall():
                cust = dict(row)
        if cust_check:
            if cust:
                async with state.proxy() as data:
                    data['pay_userBalanceEdit'] = cust
                page['page'] = 'userBalanceEdit2'
            else:
                error = f"❌ Пользователь не найден"
        else:
            error = f"❌ Не верный ввод"
        memory['dop'] = await pay_dop(tg, state, page, error)
    elif page['page'] == 'userBalanceEdit2' and 'text' in tg:
        cust = {}
        async with state.proxy() as data:
            if 'pay_userBalanceEdit' in data:
                cust = data['pay_userBalanceEdit']
        if cust:
            text = tg.text.replace(',', '.')
            if re.search(r'^(-)?(0|[1-9][0-9]*)(\.[0-9]{1,2})?$', text):
                balance_new = cust['balance'] + float(text)
                cur.execute("UPDATE users SET balance = '{}' WHERE user_id = '{}'".format(balance_new, cust['user_id']))
                answer = await send(tg, {'text': f'✅ Баланс успешно изменен на {await money(balance_new)}'})
                memory['mes_new'].append(answer.message_id)
                page['page'] = 'adminMenu'
            else:
                error = f"❌ Не верный ввод, только цифры, минус и точку"
        else:
            page['page'] = 'userBalanceEdit'
        memory['dop'] = await pay_dop(tg, state, page, error)
    elif page['page'] == 'walletDescription' and 'text' in tg:
        text = tg.text.replace("'", "`")
        save = await saver('replace', {"setting": {"pay_walletDescription": text}})
        memory['dop'] = await pay_dop(tg, state, page, error)
    elif page['page'] == 'xx' and 'text' in tg:
        m[0]['text'] = 'текст'
        m[0]['but'] = [[{'text': but_back, 'callback_data': "pay_go"}]]
        answer = await send(tg, {'text': 'текст'})
        memory['mes_new'].append(answer.message_id)
        error = f"❌ Данный ID канала уже существует"
        page['page'] = 'yy'
        memory['dop'] = await pay_dop(tg, state, page, error)
        memory['page_new'] = 'pay_xx'
    else:
        memory['stop'] = True
        memory['dop'] = await pay_dop(tg, state, page, error)
    await memory_finish(tg, state, memory, page, m)

async def pay_dop(tg, state, page, error_mes=False):
    save = await saver()
    if tg.from_user.id in eval(save['setting']['ban_users']):
        return False
    error = ''
    m = {0: {}}
    memory = await memory_start(state, load_memory=False)
    if page['page'] == 'adminMenu' and tg.from_user.id in save['admins']:
        await memory_reset(state, 'pay')
        await memory_reset(state, 'payTime')
        user = await user_load(tg, state)
        m[0]['text'] = "Настройки VIP:"
        m[0]['but'] = []
        m[0]['but'].append([{'text': "📊 Статистика оплат", 'callback_data': "pay_statistic"}])
        if 'pay_price' in save['setting']:
            m[0]['but'].append([{'text': f"💲 Настройка цены: {save['setting']['pay_price']}", 'callback_data': "pay_priceOneSet"}])
        if module_main == 'bot':
            if await module.bot.bot_balance():
                m[0]['but'].append([{'text': f"✏️ Изменить баланс пользователя", 'callback_data': "pay_userBalanceEdit"}])
        if 'payTime' in modules:
            m[0]['but'].append([{'text': "🫅 Список VIP юзеров", 'callback_data': "payTime_userList"}])
            m[0]['but'].append([{'text': "🎁 Бесплатный VIP на старте", 'callback_data': "payTime_startVipFree"}])
            m[0]['but'].append([{'text': "💲 Прайс цен на VIP", 'callback_data': "payTime_priceList"}])
        if 'payRating' in modules:
            m[0]['but'].append([{'text': "🫅 Список VIP юзеров", 'callback_data': "payRating_userList"}])
            m[0]['but'].append([{'text': "🎁 Бесплатные ОТРЫТИЯ на страте", 'callback_data': "payRating_startOpenFree"}])
            m[0]['but'].append([{'text': "💲 Прайс цен на VIP + ОТКРЫТИЯ", 'callback_data': "payRating_priceList"}])
        if 'op' in modules and 'pay' in modules:
            smile = "🟢 Показываем" if int(save['setting']['pay_payShowInOp']) else "⚫️ Скрываем"
            m[0]['but'].append([{'text': f"{smile} кнопку: НЕ ХОЧУ ПОДПИСЫВАТЬСЯ", 'callback_data': f"pay_showInOp"}])
        if 'payTime' in modules or 'payRating' in modules:
            m[0]['but'].append([{'text': "💬 Настройка VIP сообщения", 'callback_data': "pay_editMessage"}])
            m[0]['but'].append([{'text': "💬 Сообщение при окончании VIP", 'callback_data': "pay_editCronMessage"}])
            smile = "🟢 Вкл" if int(save['setting']['pay_payFree']) else "⚫️ Выкл"
            m[0]['but'].append([{'text': f"Кнопка ПОЛУЧИТЬ VIP БЕСПЛАТНО: {smile}", 'callback_data': f"pay_showInFree"}])
        m[0]['but'].append([{'text': "🪪 Описание в платежке", 'callback_data': "pay_walletDescription"}])
        m[0]['but'].append([{'text': "🪪 Настроить кошельки", 'callback_data': "pay_walletList"}])
        m[0]['but'].append([{'text': but_back, 'callback_data': "start_start"}])
    elif page['page'] == 'walletDescription':
        m[0]['text'] = "Описание платежа которое увидит юзер перейдя в платежку(при вводе номера карты):"
        m[0]['text'] += f"\n\n<b>{save['setting']['pay_walletDescription']}</b>"
        m[0]['text'] += "\n\n<i>Пришлите новый текст, если хотите заменить описание.</i>"
        m[0]['but'] = [[{'text': but_back, 'callback_data': "pay_adminMenu"}]]
    elif page['page'] == 'userBalanceEdit':
        m[0]['text'] = f"Введите @username пользователя или его id"
        m[0]['but'] = [[{'text': but_back, 'callback_data': "pay_adminMenu"}]]
    elif page['page'] == 'userBalanceEdit2':
        cust = {}
        async with state.proxy() as data:
            if 'pay_userBalanceEdit' in data:
                cust = data['pay_userBalanceEdit']
        if cust:
            m[0]['text'] = f"Пользователь:\n"
            name = f"{cust['first_name']} {cust['last_name']}".strip()
            if not name:
                name = cust['user_id']
            m[0]['text'] += f"<a href='{cust['user_id']}'>{name}</a>"
            if cust['username']:
                m[0]['text'] += f" @{cust['username']}"
            m[0]['but'] = [[{'text': but_back, 'callback_data': "pay_adminMenu"}]]
            m[0]['text'] += f"\n\nБаланс пользователя: {await money(cust['balance'])}"
            m[0]['text'] += f"\n\n<b>Введите число на сколько изменить баланс юзера</b>"
            m[0]['text'] += f"\n<i>Положительное число, увеличит баланс.</i>"
            m[0]['text'] += f"\n<i>Отрицательное число, уменьшит баланс.</i>"
            m[0]['but'] = [[{'text': but_back, 'callback_data': "pay_adminMenu"}]]
        else:
            page['page'] = 'userBalanceEdit'
            memory['dop'] = await pay_dop(tg, state, page, error)
    elif page['page'] == 'priceOneSet':
        m[0]['text'] = f"Установленная цена: {save['setting']['pay_price']}"
        m[0]['text'] += f"\n\n<i>Чтобы изменить цену, пришлите новую</i>"
        m[0]['but'] = [[{'text': but_back, 'callback_data': "pay_adminMenu"}]]
    elif page['page'] == 'editCronMessage':
        m[0] = await message_show(setting_name='payTime_cron_message')
        m[1] = {}
        m[1]['text'] = "⬆️ Сообщение ⬆️\n\nПришлите новое, чтобы заменить его:"
        m[1]['text'] += "\n\nПравила отправки сообщения: <a href='https://telegra.ph/ppp-03-14-6'>ПРОЧИТАТЬ</a>"
        m[1]['but'] = [[{'text': but_back, 'callback_data': "pay_adminMenu"}]]
    elif page['page'] == 'editMessage':
        m[0] = await show_message_from_setting('pay')
        m[1] = {}
        m[1]['text'] = "⬆️ Сообщение ⬆️\n\nПришлите новое, чтобы заменить его:"
        m[1]['text'] += "\n\nПравила отправки сообщения: <a href='https://telegra.ph/PP-09-17-6'>ПРОЧИТАТЬ</a>"
        m[1]['but'] = [[{'text': but_back, 'callback_data': "pay_adminMenu"}]]
    elif page['page'] == 'walletList':
        m[0]['text'] = "Настройка кошельков: "
        m[0]['but'] = []
        cur.execute("SELECT * FROM pay_wallet ORDER BY id")
        for row in cur.fetchall():
            if row['company'] == 'manual':
                row['company'] = "Ручная оплата"
            smile = "🟢" if row['active'] else "⚫️"
            m[0]['but'].append([{'text': f"{smile} № {row['id']} - {row['company']}", 'callback_data': f"pay_walletOne_{row['id']}"}])
        m[0]['but'].append([{'text': "➕ Добавить кошелек", 'callback_data': "pay_walletAdd"}])
        m[0]['but'].append([{'text': but_back, 'callback_data': "pay_adminMenu"}])
    elif re.search(r'^walletAdd', page['page']):
        if page['page'] == 'walletAddRobokassa':  # Payselection
            m[0]['text'] = '1️⃣ Зайдите в настройки магазина в Robokassa в подраздел "Технические настройки", и пропишите строки:'
            m[0]['text'] += f"\n\nResult Url:<code>\nhttps://{pay_link}/robokassa</code>"
            m[0]['text'] += f"\n\nSuccess Url:<code>\nhttps://{pay_link}/success</code>"
            m[0]['text'] += f"\n\nFail Url:<code>\nhttps://{pay_link}/fail</code>"
            m[0]['text'] += '\n\n2️⃣ Там же в трех места есть параметр "Метод отсылки данных по Result Url", выберите POST во всех 3 местах'
            m[0]['text'] += '\n\n3️⃣ В "Алгоритм расчета хеша" выберите "MD5"'
            m[0]['text'] += '\n\n4️⃣ Сохраните данные'
            m[0]['text'] += '\n\n5️⃣ Там же наверху, скопируйте "Идентификатор магазина" и отправьте боту:'
            m[0]['but'] = [[{'text': but_back, 'callback_data': "pay_walletList"}]]
        elif page['page'] == 'walletAddRobokassa2':  # Payselection
            m[0]['text'] = "Введите <b>Пароль #1</b> от магазина Robokassa:"
            m[0]['but'] = [[{'text': but_back, 'callback_data': "pay_walletList"}]]
        elif page['page'] == 'walletAddPayselection': # Payselection
            m[0]['text'] = "1️⃣ Зайдите в настройки магазина в Payselection, и пропишите строки:"
            m[0]['text'] += f"\n\nURL успеха:<code>\nhttps://{pay_link}/success</code>"
            m[0]['text'] += f"\n\nURL ошибки:<code>\nhttps://{pay_link}/fail</code>"
            m[0]['text'] += f"\n\nURL оповещения:<code>\nhttps://{pay_link}/PayselectionAnswer</code>"
            m[0]['text'] += "\n\n2️⃣ Введите вашего ID сайта (магазина) на Payselection:"
            m[0]['but'] = [[{'text': but_back, 'callback_data': "pay_walletList"}]]
        elif page['page'] == 'walletAddPayselection2': # Payselection
            m[0]['text'] = "Введите <b>публиный ключ</b> от магазина Payselection:"
            m[0]['but'] = [[{'text': but_back, 'callback_data': "pay_walletList"}]]
        elif page['page'] == 'walletAddPayselection9': # Payselection
            m[0]['text'] = "Введите <b>секретный ключ</b> от магазина Payselection:"
            m[0]['but'] = [[{'text': but_back, 'callback_data': "pay_walletList"}]]
        elif page['page'] == 'walletAddPayselection3': # Payselection
            m[0]['text'] = "Выберите один из вариантов рекуррентного платежа"
            m[0]['text'] += "\n\n<b>1️⃣ вариант</b>: После окончания оплаченного периода, каждый пользователь будет повторно платить такую же сумму и на такой же срок, какой выбрал при оплате"
            m[0]['text'] += "\n\n<b>2️⃣ вариант</b>: После окончания оплаченного периода, все пользователи будут платить одинаковую цену и иметь одинаковый период снятия, который вы сможете настроите далее"
            m[0]['but'] = [
                [
                    {'text': "Вариант 1️⃣", 'callback_data': "pay_walletAddPayselection4_1"},
                    {'text': "Вариант 2️⃣", 'callback_data': "pay_walletAddPayselection4_0"},
                ],
                [{'text': but_back, 'callback_data': "pay_walletList"}]
            ]
        elif page['page'] == 'walletAddPayselection4': # Payselection
            m[0]['text'] = "Выберите период:\n\n<i>Пример, если хотите снимать оплату раз 3, 5 или 10 дней, выберите ДЕНЬ. Если хотите раз в неделю, или раз в две недели, выберите НЕДЕЛЯ. Если хотите раз в месяц выберите МЕСЯЦ</i>"
            m[0]['but'] = [
                [
                    {'text': "День", 'callback_data': "pay_walletAddPayselection5_day"},
                    {'text': "Неделя", 'callback_data': "pay_walletAddPayselection5_week"},
                    {'text': "Месяц", 'callback_data': "pay_walletAddPayselection5_month"},
                ],
                [{'text': but_back, 'callback_data': "pay_walletList"}]
            ]
        elif page['page'] == 'walletAddPayselection5': # Payselection
            async with state.proxy() as data:
                if 'pay_walletAdd3' in data:
                    walletAdd4 = data['pay_walletAdd3']
                    if data['pay_walletAdd4'] == 'day':
                        dop_mes = "Напимер: введите цифру 3, чтоб снимать оплату каждый третий день. Цифру 1, чтоб снимать каждый день"
                        dop_mes_2 = "дней"
                    elif data['pay_walletAdd4'] == 'week':
                        dop_mes = "Напимер: введите цифру 1, чтоб снимать оплату каждую неделю. Цифру 2, чтоб снимать 1 раз в 2 недели"
                        dop_mes_2 = "недель"
                    elif data['pay_walletAdd4'] == 'month':
                        dop_mes = "Напимер: введите цифру 1, чтоб снимать оплату каждый месяц. Цифру 2, чтоб снимать 1 раз в 2 месяца"
                        dop_mes_2 = "месяцев"
                    m[0]['text'] = f"Введите цифрой какой промежуток {dop_mes_2} между рекуррентыми платежами:\n\n<i>{dop_mes}</i>"
                    m[0]['but'] = [[{'text': but_back, 'callback_data': "pay_walletList"}]]
                else:
                    page['page'] = 'walletList'
                    memory['dop'] = await pay_dop(tg, state, page, error)
        elif page['page'] == 'walletAddPayselection6': # Payselection
            m[0]['text'] = f"Введите сумму цифрой, которую будет списывать у пользователя:"
            m[0]['but'] = [[{'text': but_back, 'callback_data': "pay_walletList"}]]
        elif page['page'] == 'walletAddСloudPaymentsWidget': # СloudPayments Widget
            m[0]['text'] = "Введите Public ID вашего магазина на СloudPayments:"
            m[0]['but'] = [[{'text': but_back, 'callback_data': "pay_walletList"}]]
        elif page['page'] == 'walletAddQiwi': # Qiwi
            m[0]['video'] = 'files/pay/Qiwi.mp4'
            m[0]['text'] = "1️⃣ Следуйте видео инструкции"
            m[0]['text'] += "\n\n2️⃣ Ваша ссылка для создания ключа:"
            m[0]['text'] += f"\nhttps://{pay_link}/QiwiAnswer"
            m[0]['text'] += "\n\n3️⃣ Отправьте сюда <b>публичный ключ</b> кошелька:"
            m[0]['but'] = [[{'text': but_back, 'callback_data': "pay_walletList"}]]
        elif page['page'] == 'walletAddYoomoney': # YooMoney
            m[0]['text'] = "Перейдите по ссылке\nhttps://yoomoney.ru/settings\n\nСкопируйте номер кошелька (состоит из цифр, около аватарки) и пришлите его в бот"
            m[0]['but'] = [[{'text': but_back, 'callback_data': "pay_walletList"}]]
        elif page['page'] == 'walletAddYoomoney2': # YooMoney
            web = save["bot"]["username"].replace("_", "-")
            m[0]['text'] = '1️⃣ Перейдите по ссылке https://yoomoney.ru/transfer/myservices/http-notification и в графу '
            m[0]['text'] += f'"Куда отправлять (URL сайта)" введите https://{pay_link}/YooMoney'
            m[0]['text'] += '\n\n2️⃣ На той же странице поставьте галочку около "Отправлять HTTP-уведомления"'
            m[0]['text'] += '\n\n3️⃣ На той же странице нажмите "Показать секрет", скопируйте появившийся код, и отправьте его в бот'
            m[0]['but'] = [[{'text': but_back, 'callback_data': "pay_walletList"}]]
        elif page['page'] == 'walletAddAaioSo': # aaio.so
            m[0]['text'] = "Пришлите ID Вашего магазина\n\nСоздать или получить его можно на этой странице https://aaio.so/cabinet/merchants перейдя в настройки вашего магазина"
            m[0]['but'] = [[{'text': but_back, 'callback_data': "pay_walletList"}]]
        elif page['page'] == 'walletAddAaioSo2': # aaio.so
            m[0]['text'] = '1️⃣ На той же странице вашего магазина, спуститесь вниз и добавьте в строку <b>"URL Оповещения"</b>:'
            m[0]['text'] += f"\n<code>https://{pay_link.lower()}/aaioso</code>"
            m[0]['text'] += f'\nи нажмите кнопку <b>"Сохранить"</b>'
            m[0]['text'] += '\n\n2️⃣ Пришлите <b>Секретный ключ №1</b>, вы его можете найти все там же на странице под кнопкой "Секретные ключи"'
            m[0]['but'] = [[{'text': but_back, 'callback_data': "pay_walletList"}]]
        elif page['page'] == 'walletAddCommon': # Общий для ввода ID_магазина и токена
            async with state.proxy() as data:
                data['pay_walletAdd'] = {'company': page['param']}
            m[0]['text'] = "Пришлите ID вашего магазина"
            m[0]['but'] = [[{'text': but_back, 'callback_data': "pay_walletList"}]]
        elif page['page'] == 'walletAddCommon2': # Общий для ввода ID_магазина и токена
            m[0]['text'] = "Пришлите секретный ключ "
            m[0]['but'] = [[{'text': but_back, 'callback_data': "pay_walletList"}]]
    elif page['page'] == 'walletManual':
        m[0]['text'] = 'Введите номер карты'
        ###
    elif page['page'] == 'walletManual2':
        m[0]['text'] = 'Введите текст сообщения который увидит пользователь, после оплаты, например: '
        m[0]['text'] += '\n\n<code>Напишите мне @username для получения доступпа к боту.\nДоступ будет выдан в течении одного часа</code>'
        m[0]['but'] = [[{'text': but_back, 'callback_data': "pay_walletList"}]]
    elif page['page'] == 'showInFree':
        m[0]['text'] = "Текст"
        m[0]['but'] = [[{'text': but_back, 'callback_data': "pay_go"}]]
    elif page['page'] == 'xx':
        m[0]['text'] = "Текст"
        m[0]['but'] = [[{'text': but_back, 'callback_data': "pay_go"}]]
        answer = await send(tg, {'text': 'текст'})
        memory['mes_new'].append(answer.message_id)
        page['page'] = 'yy'
        memory['dop'] = await pay_dop(tg, state, page, error)
    if error_mes and 'text' in m[0]:
        m[0]['text'] = f'{error_mes}\n\n{m[0]["text"]}'
    await memory_finish(tg, state, memory, page, m, dop=True)
    return True # чтоб не было дублежа записи page

# await module.pay.pay_create(tg.from_user.id, price, option)
async def pay_create(user_id, price, option, types='pay'):
    global pay_link
    wallet_id = 0
    save = await saver()
    cur.execute("SELECT * FROM pay_wallet WHERE active = 1 LIMIT 1")
    for row in cur.fetchall():
        wallet_id = row['id']
    #if wallet_id:
    if True:
        if type(option) != str:
            option = str(option).replace("'", '"')
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cur.execute("INSERT INTO pay_payment (wallet_id, user_id, status, price, good, date_pay, types) VALUES (%s, %s, 'create', %s, %s, %s, %s)", [wallet_id, user_id, price, option, now, types])
        cur.execute("SELECT MAX(id) FROM pay_payment WHERE user_id = '{}'".format(user_id))
        pay_id = cur.fetchall()[0]['max']
        pay_url = f"https://{pay_link}/?bot={save['bot']['username']}&user={user_id}&pay={pay_id}"
        return {'link': pay_url, 'pay_id': pay_id}
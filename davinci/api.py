from config import *
from sql import cur


import re
import sys
import os.path
import time
import requests
import datetime
import asyncio # паузы await asyncio.sleep(1)
from subprocess import Popen, PIPE, check_call


z = 0
param = sys.argv[1:]
result = {'action': param[0], 'incoming': param}
if param[0] == 'pay_create': # получить данные об оплате
    pay_type = param[1]
    pay_user = param[2]
    pay_option = param[3]
    recurrent = False
    # настраиваемое описание покупки которое мы выдаем на странице оплаты
    result['description'] = ""
    cur.execute("SELECT * FROM setting WHERE name = 'pay_walletDescription' LIMIT 1")
    for row in cur.fetchall():
        result['description'] = row['param']
    # узнаем цену оплаты
    if pay_type.lower() == 'time':
        if re.search(r'^[0-9]+$', pay_option):
            pay_option = int(pay_option)
            #####
            cur.execute("SELECT * FROM setting WHERE name = '{}' LIMIT 1".format('payTime_list'))
            for row in cur.fetchall():
                payTime_list = eval(row['param'])
            recurrent = payTime_list[pay_option]['recurrent']
            #####
            cur.execute("SELECT * FROM setting WHERE name = '{}' LIMIT 1".format('payTime_price'))
            for row in cur.fetchall():
                payTime_price = row['param']
            option = int(pay_option)
            if payTime_price:
                payTime_price = eval(payTime_price)
                if option in payTime_price:
                    result['price'] = payTime_price[option]
                else:
                    result['error'] = "Ошибка оплаты #time_103" # не верный номер option, его нет в setting['payTime_price']
            else:
                result['error'] = "Ошибка оплаты #time_102" # не нашли в БД в таблице setting значение name = 'payTime_price'
        else:
            result['error'] = "Ошибка оплаты #time_101" # option Должна быть цифрой
    elif pay_type.lower() == 'amount':
        if re.search(r'^[0-9]+$', pay_option):
            result['price'] = pay_option
            option = ''
        else:
            result['error'] = "Ошибка оплаты #balance_101" # option Должна быть цифрой
    elif pay_type.lower() == 'rating':
        if re.search(r'^[0-9]+$', pay_option):
            cur.execute("SELECT * FROM setting WHERE name = '{}' LIMIT 1".format('payRating_price'))
            for row in cur.fetchall():
                payRating_price = row['param']
            option = int(pay_option)
            if payRating_price:
                payRating_price = eval(payRating_price)
                if option in payRating_price:
                    result['price'] = payRating_price[option]
                else:
                    result['error'] = "Ошибка оплаты #rating_103" # не верный номер option, его нет в setting['payTime_price']
            else:
                result['error'] = "Ошибка оплаты #rating_102" # не нашли в БД в таблице setting значение name = 'payTime_price'
        else:
            result['error'] = "Ошибка оплаты #rating_101" # option Должна быть цифрой
    elif pay_type.lower() == 'good':
        if re.search(r'^[0-9]+$', pay_option):
            option = int(pay_option)
            cur.execute("SELECT * FROM goods WHERE id = '{}'".format(int(pay_option)))
            for row in cur.fetchall():
                good = dict(row)
            if good:
                result['price'] = good['price']
            else:
                result['error'] = "Ошибка оплаты #good_102" # нет такого товара
        else:
            result['error'] = "Ошибка оплаты #good_101"  # option Должна быть цифрой
    elif pay_type.lower() == 'price':
        load_price = False
        option = int(pay_option)
        cur.execute("SELECT * FROM setting WHERE name = 'pay_price'")
        for row in cur.fetchall():
            load_price = dict(row)
        if load_price:
            if int(load_price['param']) == option:
                result['price'] = int(load_price['param'])
            else:
                result['error'] = "Ошибка оплаты #price_102"
                # не совпадает цена на кнопке в ботес save['setting']['pay_price']
                # либо админ только что изменил цену, и  юзеру надо заново создать оплату
                # юзер изменил параметр GET
        else:
            result['error'] = "Ошибка оплаты #price_101"  # нет нашли строку pay_price в таблице setting
    elif pay_type.lower() == 'balance':
        option = float(pay_option)
        result['price'] = option
    elif pay_type.lower() == 'pay':
        if not pay_option.isdigit():
            result['error'] = "Ошибка оплаты #pay_101"  # в GET параметра pay= не равно цифре
        else:
            option = int(pay_option)
            cur.execute("SELECT * FROM pay_payment WHERE id = '{}' LIMIT 1".format(pay_option))
            for row in cur.fetchall():
                pay_list = dict(row)
            if 'pay_list' not in locals():
                result['error'] = "Ошибка оплаты #pay_102"  # нет такого id в таблице pay_payment
            elif int(pay_list['user_id']) != int(pay_user):
                result['error'] = "Ошибка оплаты #pay_103"  # строка в таблице pay_payment с таким id не от этого юзера
            else:
                result['price'] = pay_list['price']
                result['pay_id'] = pay_list['id']
    row_other = False
    if 'error' in result:
        pass
    elif 'price' not in result:
        result['error'] = "Ошибка оплаты #1011"  # нет параметра result['price']
    elif not result['price']:
        result['error'] = "Ошибка оплаты #1012"  # нет ничего в result['price']
    else:
        # узнаем активный кошелек
        cur.execute("SELECT * FROM pay_wallet WHERE active = 1")
        for row in cur.fetchall():
            row = dict(row)
            if 'other' in row: # раскрываем параметры other
                if recurrent:
                    if row['other']:
                        row_other = eval(row['other'])
                        if 'recurrent_repeat_payment' in row_other: # если платеж рекурретный
                            if int(row_other['recurrent_repeat_payment']): # если рекуррентный платеж такой же как первый оплаченный в боте ВИП
                                row_other['recurrent_period_type'] = 'day'
                                if pay_type.lower() == 'time':
                                    row_other['recurrent_period_count'] = payTime_list[pay_option]['day']
                                    row_other['recurrent_price'] = payTime_price[int(pay_option)]
                            row_other['recurrent_start'] = payTime_list[pay_option]['day'] # через сколько дней начинаем снимать рекуррентные платежи
                        else:
                            recurrent = False
                        for k, v in row_other.items():
                            row[f'other_{k}'] = v
                row.pop('other')
            result['wallet'] = row
            result['recurrent'] = str(recurrent).lower()

        if 'error' in result:
            pass
        elif 'wallet' not in result:
            result['error'] = "Ошибка оплаты #1021"  # нет параметра result['wallet']
        elif not result['wallet']:
            result['error'] = "Ошибка оплаты #1022"  # нет ничего в result['wallet']
        else:
            # подгружаем юзера
            if re.search(r'^[1-9][0-9]*$', pay_user):
                cur.execute("SELECT * FROM users WHERE user_id = '{}' LIMIT 1".format(pay_user))
                for row in cur.fetchall():
                    row = dict(row)
                    # row.pop('date_write')
                    result['user'] = {}
                    for k, v in row.items():
                        if not re.search(r'^(anon_|davinci_|rating_|sub_|date_write|referal|block|ban|status)', k):
                            result['user'][k] = v
                if 'user' not in result:
                    result['error'] = "Ошибка оплаты #302"  # не нашел юзера с таким user_id
            else:
                result['error'] = "Ошибка оплаты #301"  # user_id Должна быть цифрой

            result['web_site'] = pay_link
            if 'error' in result:
                pass
            elif 'user' not in result:
                result['error'] = "Ошибка оплаты #1031"  # нет параметра result['user']
            elif not result['user']:
                result['error'] = "Ошибка оплаты #1032"  # нет ничего в result['user']
            elif pay_type.lower() != 'pay': # если pay, то значит уже была создана оплата в боте и повторно создавать не надо
                if row_other:
                    if 'recurrent_repeat_payment' in row_other:
                        recurrent_str = str(row_other).replace("'", '"')
                # создаем оплату в БД
                if not 'recurrent_str' in locals():
                    recurrent_str = ""
                print(f"{result['wallet']['id']}, {result['user']['user_id']}, {'create'}, {result['price']}, {option}, {recurrent_str}")
                cur.execute("INSERT INTO pay_payment (wallet_id, user_id, status, price, option, recurrent, types) VALUES (%s, %s, %s, %s, %s, %s, %s)", [result['wallet']['id'], result['user']['user_id'], 'create', result['price'], option, recurrent_str, pay_type.lower()])
                cur.execute("SELECT MAX(id) FROM pay_payment")
                result['pay_id'] = cur.fetchall()[0]['max']
                if not result['pay_id']:
                    result['error'] = "Ошибка оплаты #401"
elif param[0] == 'pay_save':
    date_pay = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    pay = {}
    answer_string = param[3].replace("%*%", ' ').replace("#*#", '"').replace("#*%", ';')
    result['param'] = answer_string
    amount = param[2]
    label = param[1]
    recurrent = False
    if '-' in label:
        arr = label.split('-')
        if len(arr) >= 3:
            user_id = arr[1]
            pay_id = arr[2]
            if not re.search(r'^(0|[1-9][0-9]*)(\.[0-9]{1,2})?$', amount):
                result['error'] = f"ERROR pay.api | не адекватные данные: amount = {str(amount)}"
            elif not re.search(r'^[1-9][0-9]*$', user_id):
                result['error'] = f"ERROR pay.api | не адекватные данные: user_id = {str(user_id)}"
            else:
                if re.search(r'^[1-9][0-9]*$', pay_id) or pay_id == 'recurrent':
                    if pay_id == 'recurrent': # если платеж был рекурентный
                        pay = {'recurrent': False}
                        cur.execute("SELECT * FROM pay_payment WHERE user_id = '{}' ORDER BY id DESC LIMIT 1".format(user_id))
                        for row in cur.fetchall():
                            pay = dict(row)
                        if pay['recurrent']:
                            recurrent = eval(pay['recurrent'])
                        else:
                            result['error'] = f"ERROR pay.api | Не верный рекуррентный запрос в pay_save"
                            pay = {}
                    else: # обычный платеж
                        pay_id = int(pay_id) # не поднимать выше проверки re
                        cur.execute("SELECT * FROM pay_payment WHERE id = '{}'".format(pay_id))
                        for row in cur.fetchall():
                            pay = dict(row)
                    if not pay:
                        cur.execute("INSERT INTO pay_payment (user_id, status, price, option, answer, date_pay) VALUES (%s, %s, %s, %s, %s, %s)",[user_id, 'error', amount, 0, answer_string, date_pay])
                        result['error'] = f"ERROR pay.api | Не нашли в таблице pay_id = {pay_id}"
                    elif recurrent: # если платеж был рекурентный платеж (повторный)
                        cur.execute("INSERT INTO pay_payment (user_id, status, price, option, answer, date_pay) VALUES (%s, %s, %s, %s, %s, %s)",[user_id, 'recurrent', amount, 0, answer_string, date_pay])
                        result['ok'] = 'ok'
                    elif pay['status'] == 'paid':
                        # уже было оплачено, и почему-то пришел второй такой же запрос
                        result['error'] = f"ERROR pay.api | Уже было оплачен: pay_id = {str(pay_id)}"
                        cur.execute("INSERT INTO pay_payment (user_id, status, price, option, answer, date_pay) VALUES (%s, %s, %s, %s, %s, %s)",[user_id, f'повтор id={pay_id}', amount, 0, answer_string, date_pay])
                        pay = {}
                    else:
                        cur.execute("UPDATE pay_payment SET status = '{}', answer = '{}', date_pay = '{}' WHERE id = '{}'".format('paid', answer_string, date_pay, pay_id))
                        result['ok'] = 'ok'
                elif pay_id == 'recurrent':
                    pass
                else:
                    result['error'] = f"ERROR pay.api | не адекватные данные: pay_id = {str(pay_id)}"
        else:
            result['error'] = f"ERROR pay.api | не верный label | label = {str(label)} | arr = {str(arr)}"
    else:
        result['error'] = f"ERROR pay.api | не верный label | label = {str(label)}"
    # если оплата успешна, то делаем действие согласно модулю оплаты
    if pay:
        cur.execute("UPDATE users SET balance = balance + {} WHERE user_id = '{}'".format(amount, user_id))
        folders_2 = os.listdir(f"../{arr[0]}/module")
        if 'payTime.py' in folders_2:
            if recurrent:  # если платеж был рекурентный платеж (повторный)
                price = recurrent['recurrent_price']
                day_plus = recurrent['recurrent_period_count']
            else: # если обычный платеж
                # если VIP считаем по модулю payTime
                option = pay['option']
                # цена
                price_all = {}
                cur.execute("SELECT * FROM setting WHERE name = 'payTime_price' LIMIT 1")
                for row in cur.fetchall():
                    price_all = eval(row['param'])
                price = price_all[option]
                # узнаем длительность по данному тарифу
                payTime_list = {}
                cur.execute("SELECT * FROM setting WHERE name = 'payTime_list'")
                for row in cur.fetchall():
                    payTime_list = eval(row['param'])
                day_plus = int(payTime_list[option]['day'])
            sec_plus = day_plus * 24 * 60 * 60
            # изменяем юзера
            customer = {}
            cur.execute("SELECT * FROM users WHERE user_id = '{}' LIMIT 1".format(user_id))
            for row in cur.fetchall():
                customer = dict(row)
            if customer:
                if customer['first_name'] or customer['last_name']:
                    us_name = f"{customer['first_name']} {customer['last_name']}".strip()
                else:
                    us_name = customer['user_id']
                us_name = f"<a href='tg://user?id={customer['user_id']}'>{us_name}</a>"
                if customer['username']:
                    us_name += f" @{customer['username']}"
                now = int(time.time())
                if int(customer['pay_time']) < now:
                    plus = now + sec_plus
                else:
                    plus = int(customer['pay_time']) + sec_plus
                cur.execute("UPDATE users SET pay_time = '{}' WHERE user_id = '{}'".format(plus, user_id))
                forever = now + ( 5 * 365 * 24 * 60 * 60) # + 5 лет
                if plus > forever:
                    date_finish = "навсегда"
                else:
                    date_finish = datetime.datetime.fromtimestamp(plus)
                    date_finish = date_finish.strftime('%Y-%m-%d %H:%M')
                    date_finish = f"до {date_finish}"
                # отправляем сообщение юзеру
                if not recurrent:  # если платеж повторный(рекурентный), то не шлем юзеру сообщение
                    mes = f"👑 Успешная покупка\nVIP доступен {date_finish}"
                # отправляем админам
                mes_admin = f"👑 Купили VIP <b>{price} ₽</b>" if not recurrent else f"👑 Купили VIP (автопродление) <b>{price} ₽</b>"
                mes_admin += f"\nПользователь: {us_name}"
                mes_admin += f"\nАктивен {date_finish}"
            else:
                result['error'] = "Пользователь не найден"
        elif 'payRating.py' in folders_2:
            # если VIP считаем по модулю payRating
            option = int(pay['option'])
            # цена
            cur.execute("SELECT * FROM setting WHERE name = '{}' LIMIT 1".format('payRating_price'))
            for row in cur.fetchall():
                price_all = eval(row['param'])
            price = price_all[option]
            # VIP всегда - НАВСЕГДА
            plus = int(time.time()) + (10 * 365 * 24 * 60 * 60)
            # изменяем юзера
            customer = {}
            cur.execute("SELECT * FROM users WHERE user_id = '{}' LIMIT 1".format(user_id))
            for row in cur.fetchall():
                customer = dict(row)
            if customer:
                if customer['first_name'] or customer['last_name']:
                    us_name = f"{customer['first_name']} {customer['last_name']}".strip()
                else:
                    us_name = customer['user_id']
                us_name = f"<a href='tg://user?id={customer['user_id']}'>{us_name}</a>"
                if customer['username']:
                    us_name += f" @{customer['username']}"
                cur.execute("UPDATE users SET pay_time = '{}', pay_open = '{}' WHERE user_id = '{}'".format(plus, option, user_id))
                # отправляем сообщение юзеру
                if not recurrent:  # если платеж повторный(рекурентный), то не шлем юзеру сообщение
                    mes = f"<b>Успешная покупка</b>\n\n👑 Вы получили VIP аккаунт "
                    mes += f"\n\n⚜️ Получено ОТКРЫТИЙ: {option}"
                # отправляем админам
                mes_admin = f"👑 Купили VIP - <b>{price} ₽</b>"
                mes_admin += f"\nПользователь - {us_name}"
                mes_admin += f"\nОткрытий: {option}"
            else:
                result['error'] = "Пользователь не найден"
        elif 'payGood.py' in folders_2:
            result['Good'] = 1
            # result['files'] = f"Пока модуль товаров не сделан"
            option = pay['option']
            good = ''
            cur.execute("SELECT * FROM goods WHERE id = '{}'".format(option))
            for row in cur.fetchall():
                good = dict(row)
            if good:
                result['Good'] = 22
                if not good['reusable']:
                    cur.execute("UPDATE goods SET status = 'paid' WHERE id = '{}'".format(option))
                # if 'f000bot1.py' in folders_2: # если нужно что то в модуле сделать
                #     pass
                # else:
                #     print(f"f000bot1.py не найден | ")
            else:
                print(f"Товар {option} не найден")
        elif 'bot.py' in folders_2:
            result['001'] = 'bot'
            if pay['types'] == 'balance':
                result['001'] = 'balance'
                cur.execute("SELECT * FROM users WHERE user_id = '{}' LIMIT 1".format(user_id))
                for row in cur.fetchall():
                    result['002'] = float(amount)
                    result['003'] = float(row['balance'])
                    balance = float(row['balance']) + float(amount)
                    result['004'] = balance
                    balance = format(float(balance), '.2f')
                    result['005'] = balance
                    cur.execute("UPDATE users SET balance = '{}' WHERE user_id = '{}'".format(balance, user_id))
            import apiBot
            asyncio.run(apiBot.bot_bay(user_id, pay_id, answer_string))
        else:
            result['files'] = f"Модуль оплаты не найден {os.listdir(f'..')}"
        # отправляем сообщение юзеру
        if 'mes' in locals():
            data = {'chat_id': user_id, 'text': mes, 'parse_mode': 'HTML'}
            requests.post(f"https://api.telegram.org/bot{TOKEN['telegram_bot']}/sendMessage", data=data)
        # отправляем сообщение админу
        if 'mes_admin' in locals():
            cur.execute("SELECT * FROM users WHERE status = 'admin' OR status = 'admin_super'")
            for row in cur.fetchall():
                if int(row['user_id']) != 355590439:
                    data = {'chat_id': row['user_id'], 'text': mes_admin, 'parse_mode': 'HTML'}
                    requests.post(f"https://api.telegram.org/bot{TOKEN['telegram_bot']}/sendMessage", data=data)

print(f' | result = {str(result)}')
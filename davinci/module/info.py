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

import matplotlib.pyplot as plt
import numpy as np

async def info_install():
    save = await saver()
    cur.execute("""CREATE TABLE IF NOT EXISTS info (
                id SERIAL PRIMARY KEY,
                date_write DATE DEFAULT '2021-01-01',
                count_all INT DEFAULT 0, 
                count_unic INT DEFAULT 0, 
                count_notref INT DEFAULT 0, 
                count_block INT DEFAULT 0)""")


    cur.execute("SELECT COUNT(*) FROM users")
    count_user = cur.fetchall()[0]['count']
    cur.execute("SELECT COUNT(*) FROM info")
    count_info = cur.fetchall()[0]['count']
    if count_user and not count_info:
        print('Обновление модуля info, это может занять около минуты, ожидайте...')
        cur.execute("SELECT DISTINCT date_write FROM users")
        for row in cur.fetchall():
            date_write = str(row['date_write'])
            cur.execute("SELECT COUNT(*) FROM info WHERE date_write = '{}'".format(date_write))
            if not cur.fetchall()[0]['count']:
                cur.execute("INSERT INTO info (date_write) VALUES (%s)", [date_write])
            cur.execute("SELECT * FROM users WHERE date_write = '{}'".format(date_write))
            for row in cur.fetchall():
                str_notref = "" if row['referal'] else ", count_notref = count_notref + 1"
                str_block = ", count_block = count_block + 1" if row['block'] else ""
                cur.execute("UPDATE info SET count_all = count_all + 1, count_unic = count_unic + 1 {} {} WHERE date_write = '{}'".format(str_notref, str_block, date_write))

    now = datetime.date.today()
    cur.execute("SELECT COUNT(*) FROM info WHERE date_write = '{}' LIMIT 1".format(now))
    if not cur.fetchall()[0]['count']:
        cur.execute("INSERT INTO info (date_write) VALUES (%s)", [now])
        save = await saver('replace', {'setting': {"info_last_date": now}})
    if 'info_last_date' not in save['setting']:
        date_yest = datetime.datetime.now() - datetime.timedelta(days=14)  # 1 дней назад
        date_yest = date_yest.strftime("%Y-%m-%d")
        save = await saver('add', {'setting': {"info_last_date": date_yest}})

# callback stat_
@dp.callback_query_handler(lambda callback_query: callback_query.data.startswith('info_'), state='*')
async def info_callback(tg: types.CallbackQuery, state: FSMContext):
    save = await saver()
    if tg.from_user.id in eval(save['setting']['ban_users']) or tg.from_user.id not in save['admins']:
        return False
    await send(tg, {'callback': True})
    error = ''
    m = {0: {}}
    page = await page_split(tg.data)
    memory = await memory_start(state)
    if page['page'] == 'cleanBlock':
        m[0]['text'] = "Вы действительно хотите удалить заблокированных?"
        m[0]['text'] += "\n\n❔ Заблокированные юзеры являются бесполезными, и при их большом кол-ве только затормаживаюют бот. "
        m[0]['text'] += "Если заблокированный юзер будет удален и зайдет повторно, то его просто запишет как нового"
        if 'rating' in modules:
            m[0]['text'] += "\n\n❕ Заблокированные пользователи с анкетами не будут удалены, чтобы сохранить анкеты."
        if 'referal' in modules:
            m[0]['text'] += "\n\n❕ Заблокирванные пользователи зашедшие по реферальной системе не будут удалены, "
            m[0]['text'] += "чтобы реферальная статистика оставалась верная. Чтобы удалить и их, "
            m[0]['text'] += "сначала сбросьте рефералов у реферальных ссылок и работников"
        m[0]['but'] = [[
            {'text': '❌ Удалить', 'callback_data': "info_cleanBlockDel"},
            {'text': but_back, 'callback_data': "start_info"}
        ]]
    elif page['page'] == 'cleanBlockDel':
        answer = await bot.send_message(chat_id=tg.from_user.id, text="❎ Пользователи успешно удалены")
        memory['mes_new'].append(answer.message_id)
        dop_sql = ""
        if 'referal' in modules or 'Zworker' in modules:
            dop_sql += " AND referal = '' "
        if 'rating' in modules:
            dop_sql += " AND (rating_anket_name = '' OR rating_anket_photo = '' OR rating_anket_sex = '' OR rating_anket_search = '') "
        cur.execute(f"DELETE FROM users WHERE block = 1 {dop_sql}")
        page['page'] = 'info'
        memory['dop'] = await info_dop(tg, state, page, error)
    elif page['page'] == 'file': ###### ВЫГРУЗКА ФАЙЛОВ
        answer_load = await send(tg, {'text': f'⏳ Грузим данные...'})
        if not os.path.exists('files'):
            os.mkdir("files")
        if not os.path.exists('files/users'):
            os.mkdir('files/users')
        else:
            for file_one in os.listdir('files/users'):
                os.remove(os.path.join('files/users', file_one))
        users_list = ''
        load_block = 'live' if page['param'] == 'live' else False
        users_load = sql_users_load(block=load_block)

        for one in users_load:
            if one == 355590439:
                continue
            if users_list:
                users_list += '\n'
            users_list += str(one)
        file_name = f'files/users/users_{str(int(time.time()))}.txt'
        with open(file_name, 'w') as file:
            file.write(users_list)
        mes = f"Список живых пользователей в боте @{save['bot']['username']}\n- Для переноса пользователей в новый бот\n- Для проверки статистики (Можно перекинуть репостом это сообщение в проверяемый бот)"
        try:
            await bot.send_document(tg.from_user.id, caption=mes, document=InputFile(file_name))
        except Exception as ex:
            await bot.send_message(tg.from_user.id, text="🙈 Ошибка, попробуйте еще раз")
        await bot.delete_message(tg.from_user.id, message_id=answer_load.message_id)
        memory['stop'] = True
    elif page['page'] == 'infoLng':
        # изменяем сообщение
        mes = {}
        mes['caption'] = tg.message.caption + "\n\n⏳ Загрузка информации..."
        mes['ent'] = tg.message.caption_entities
        mes['message_id'] = tg.message.message_id
        but = tg.message.reply_markup.inline_keyboard
        but_new = []
        for one in but:
            if one[0]['callback_data'] != 'info_infoLng':
                but_new.append(one)
        mes['but'] = but_new
        await send(tg.from_user.id, mes)
        #################### ЯЗЫКИ #####################
        mes_info_1 = f'\n\nЯзыки (живых юзеров):\n'
        lang_list = {}
        lang_clean = 0
        cur.execute("SELECT DISTINCT lang FROM users WHERE block = 0")
        for row in cur.fetchall():
            cur.execute("SELECT COUNT(id) FROM users WHERE block = 0 AND lang = '{}'".format(row['lang']))
            if not row['lang']:
                lang_clean = cur.fetchall()[0]['count']
            else:
                lang_list[row['lang']] = cur.fetchall()[0]['count']
        # объединение языков
        if 'en' in lang_list:
            if 'uk' not in lang_list:
                lang_list['uk'] = 0
            lang_list['uk'] += lang_list['en']
            lang_list.pop('en')
        if 'kk' in lang_list:
            if 'kz' not in lang_list:
                lang_list['kz'] = 0
            lang_list['kz'] += lang_list['kk']
            lang_list.pop('kk')
        if 'hi' in lang_list:
            if 'in' not in lang_list:
                lang_list['in'] = 0
            lang_list['in'] += lang_list['hi']
            lang_list.pop('hi')
        if 'lt' in lang_list:
            if 'lv' not in lang_list:
                lang_list['lv'] = 0
            lang_list['lv'] += lang_list['lt']
            lang_list.pop('lt')
        if 'br' in lang_list:
            if 'fr' not in lang_list:
                lang_list['fr'] = 0
            lang_list['fr'] += lang_list['br']
            lang_list.pop('br')


        # те что меньше минимума убираем
        cur.execute("SELECT COUNT(id) FROM users")
        stat_user_all = cur.fetchall()[0]['count']
        if stat_user_all > 100000:
            minimum = int(stat_user_all / 10000)
            if minimum < 30:
                minimum = 30
        elif stat_user_all > 10000:
            minimum = int(stat_user_all / 1000)
            if minimum < 20:
                minimum = 20
        elif stat_user_all > 1000:
            minimum = int(stat_user_all / 100)
        else:
            minimum = 3
        lang_new = {}
        lang_other = 0
        for key, value in lang_list.items():
            if value >= minimum:
                lang_new[key] = value
            else:
                lang_other += value
        lang_new = dict(sorted(lang_new.items(), key=lambda x: x[1], reverse=True)) # сортировка по значению
        if lang_other:
            lang_new['Другие'] = lang_other
        if lang_clean:
            lang_new["Не определено"] = lang_clean
        flags = {
            'ru': "🇷🇺 Русский",
            'uk': "🇬🇧 Английский",
            'ua': "🇺🇦 Украинский",
            'kz': "🇰🇿 Казахский",
            'by': "🇧🇾 Белорусский",
            'uz': "🇺🇿 Узбекистанский",
            'tr': "🇹🇷 Турецкий",
            'zh-hans': "🇨🇳 Китайский",
            'id': "🇮🇩 Индонезийский",
            'in': "🇮🇳 Индийский",
            'th': "🇹🇭 Таиландский",
            'am': "🇦🇲 Арменинский",
            'de': "🇩🇪 Немецкий",
            'ro': "🇷🇴 Румынский",
            'es': "🇪🇸 Испанский",
            'lv': "🇱🇻 Латвийский",
            'ar': "🇦🇷 Аргентинский",
            'az': "🇦🇿 Азербайджанский",
            'fr': "🇫🇷 Французский",
            'it': "🇮🇹 Итальянский",
            'pl': "🇵🇱 Польшский",
            'he': "🇮🇱 Израиль",
            'et': "🇪🇹 Эфиопия",
            'hu': "🇭🇺 Венгрия",
            'be': "🇧🇪 Бельгия",
            'hy-am': "🇦🇲 Армения",
        }
        for key, value in lang_new.items():
            if key in flags:
                flag = flags[key]
            else:
                flag = f'🏳️ {key}'
            mes_info_1 += f'{flag} {value}\n'
        # изменяем сообщение
        mes['caption'] = tg.message.caption + mes_info_1
        await send(tg.from_user.id, mes)
        memory['stop'] = True
    elif page['page'] == 'yyy':
        m[0]['text'] = "Текст"

        m[0]['but'] = [[{'text': but_back, 'callback_data': "XXX_go"}]]
        answer = await send(tg, {'text': 'текст'})
        memory['mes_new'].append(answer.message_id)
        page['page'] = 'yy'
        memory['dop'] = await info_dop(tg, state, page, error)
    else:
        # все остальные действия где мы просто перекидываем в ДОП
        memory['dop'] = await info_dop(tg, state, page)
    await memory_finish(tg, state, memory, page, m)



async def info_dop(tg, state, page, error_mes=False):
    save = await saver()
    if tg.from_user.id in eval(save['setting']['ban_users']) or tg.from_user.id not in save['admins']:
        return False
    error = ''
    m = {0: {}}
    memory = await memory_start(state, load_memory=False)
    if page['page'] == 'info':
        start = time.perf_counter()
        stat = {'user_all': 0, 'user_live': 0, 'user_block': 0, 'percent_live': 0, 'percent_block': 0, 'lang': {}}
        but = []
        but.append([{'text': but_back, 'callback_data': "start_start"}])

        mes_info_1 = '<u>📊 Статистика бота</u>\n'
        mes_load = '\n\n⏳ Загрузка информации...'
        answer = await send(tg, {'text': mes_info_1 + mes_load, 'but': but, 'photo': 'files/loading_graph.jpg'})
        message_id = answer.message_id
        memory['mes_new'].append(message_id)

        cur.execute("SELECT COUNT(id) FROM users")
        stat['user_all'] = cur.fetchall()[0]['count']
        cur.execute("SELECT COUNT(id) FROM users WHERE block = 0")
        stat['user_live'] = cur.fetchall()[0]['count']
        if 'welcome' not in modules:
            stat['user_block'] = stat['user_all'] - stat['user_live']
        else:
            cur.execute("SELECT COUNT(id) FROM users WHERE block = 1")
            stat['user_block'] = cur.fetchall()[0]['count']
            stat['user_welcomeStop'] = stat['user_all'] - stat['user_live'] - stat['user_block']

        if stat['user_all']:
            stat["percent_live"] = round(100 / stat['user_all'] * stat['user_live'])
            stat["percent_block"] = round(100 / stat['user_all'] * stat['user_block'])
            if 'welcome' in modules:
                stat["percent_welcomeStop"] = round(100 / stat['user_all'] * stat['user_welcomeStop'])

        mes_info_1 += f'\n<code>Всего: <b>{await money(stat["user_all"])}</b>'
        mes_info_1 += f'\nЖивых: <b>{await money(stat["user_live"])}</b> ({stat["percent_live"]}%)'
        mes_info_1 += f'\nЗаблокированных: <b>{await money(stat["user_block"])}</b> ({stat["percent_block"]}%)'
        if 'welcome' in modules:
            mes_info_1 += f'\nНе прошли заявки: <b>{await money(stat["user_welcomeStop"])}</b> ({stat["percent_welcomeStop"]}%)'
        if 'button' in modules or 'pay' in modules:
            cur.execute("SELECT COUNT(id) FROM users WHERE referal SIMILAR TO 'u[0-9]+' ")
            stat['user_ref_user'] = cur.fetchall()[0]['count']
            stat["percent_ref_user"] = round(100 / stat['user_all'] * stat['user_ref_user'])
            mes_info_1 += f'\nЮзеры привели: <b>{await money(stat["user_ref_user"])}</b> ({stat["percent_ref_user"]}%)'
        mes_info_1 += '</code>'

        await send(tg, {'caption': mes_info_1 + mes_load, 'but': but, 'message_id': message_id})

        mes_info_1 += '\n\n<u>По датам</u> живые | блок'
        date = {}
        date[0] = datetime.date.today()  # сегодня
        date[1] = datetime.datetime.now() - datetime.timedelta(days=1)
        date[1] = date[1].strftime("%Y-%m-%d")  # вчера
        date[2] = datetime.datetime.now() - datetime.timedelta(days=7)
        date[2] = date[2].strftime("%Y-%m-%d")  # неделю назад
        date[3] = datetime.datetime.now() - datetime.timedelta(days=30)
        date[3] = date[3].strftime("%Y-%m-%d")  # месяц назад
        texts = {}
        texts[0] = f'\n<code>За сегодня:'
        texts[1] = f'\nЗа вчера:'
        texts[2] = f'\nЗа неделю:'
        texts[3] = f'\nЗа месяц:'
        texts[4] = f'\nЗа все время:'
        сount_user = {}
        for key, value in date.items():
            сount_user[key] = {'count_all': 0, 'count_unic': 0, 'count_notref': 0, 'count_block': 0}
            if key == 4:
                сount_user[key] = {'count_unic': stat["user_live"], 'count_block': stat["user_block"]}
            elif key < 2:
                cur.execute("SELECT * FROM info WHERE date_write = '{}' LIMIT 1".format(value))
                for row in cur.fetchall():
                    сount_user[key] = dict(row)
            else:
                cur.execute("SELECT SUM(count_unic) FROM info WHERE date_write >= '{}'".format(value))
                сount_user[key]['count_unic'] = cur.fetchall()[0]['sum']
                cur.execute("SELECT SUM(count_block) FROM info WHERE date_write >= '{}'".format(value))
                сount_user[key]['count_block'] = cur.fetchall()[0]['sum']
            mes_info_1 += f" {texts[key]} {await money(сount_user[key]['count_unic'])} | {await money(сount_user[key]['count_block'])}"
        mes_info_1 += '</code>'

        await send(tg, {'caption': mes_info_1 + '\n\n⏳ Загрузка графика...', 'but': but, 'message_id': message_id})

        # загружаем инфу
        x = []
        y1 = []
        y2 = []
        y3 = []
        y4 = []
        pay_sum_max = 2
        for i in range(0, 20):
            info_row = {'count_all': 0, 'count_unic': 0, 'count_notref': 0, 'count_block': 0}
            date = datetime.date.today() if i == 0 else datetime.datetime.now() - datetime.timedelta(days=i)
            # x
            x_date = date.strftime("%d %m")
            x_date = x_date[1:] if int(x_date[:1]) == 0 else x_date
            x.append(x_date)
            # y1 y2 y3 y4
            date_full = date.strftime("%Y-%m-%d")
            if i < 2:
                info_row = сount_user[i]
            else:
                cur.execute("SELECT * FROM info WHERE date_write = '{}' LIMIT 1".format(date_full))
                for row in cur.fetchall():
                    info_row = dict(row)
            y1.append(info_row['count_all'])
            y2.append(info_row['count_unic'])
            y3.append(info_row['count_notref'])
            y4.append(info_row['count_block'])
            if pay_sum_max < info_row['count_all']:
                pay_sum_max = info_row['count_all']
            # print(f"date = {x_date} | {info_row}")
        pay_sum_max = pay_sum_max + 1 if pay_sum_max <= 10 else pay_sum_max + round(pay_sum_max / 10)
        x.reverse()
        y1.reverse()
        y2.reverse()
        y3.reverse()
        y4.reverse()
        # print(f'STATA date   = {x}')
        # print(f'STATA all    = {y1}')
        # print(f'STATA unic   = {y2}')
        # print(f'STATA notref = {y3}')
        # print(f'STATA block  = {y4}')


        ###### график
        # создаем и очищаем папку
        info_folder = 'files/graph'
        image = f'{info_folder}/info.jpg'
        if not os.path.exists(info_folder):
            os.mkdir(info_folder)
        elif os.path.exists(image):
            os.remove(image)
        ######## Рисуем график

        x_len = np.arange(len(x))  # the label locations
        width = 0.45  # ширина полосок вертикальных

        fig, ax = plt.subplots(layout='constrained', figsize=(8, 5))
        # plt.figure()


        rects = ax.bar(x_len - 0.4, y1, width, label='Все переходы', color='#BCBCBD')
        ax.bar_label(rects, padding=3, color='#AAAAAB')
        rects = ax.bar(x_len - 0.4, y2, width, label='Новые уникальные', color='#3D75DD')
        ax.bar_label(rects, padding=3, color='#2F5AAB')
        rects = ax.bar(x_len - 0.4, y3, width, label='Саморост', color='#52B7FF')
        # ax.bar_label(rects, padding=3, color='black')
        rects = ax.bar(x_len - 0.4 + 0.39, y4, 0.20, label='Блок', color='#B71111')
        # ax.bar_label(rects, padding=3, color='#B71111')

        # rects = ax.bar(x_len, y1, width, label='y1', color='orange', bottom=y2)
        # ax.bar_label(rects, padding=3)

        ax.set_xticks(x_len + width - 0.8, x, rotation=66)
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
        ax.legend(loc='upper left', ncols=1)

        plt.savefig(image)

        but = []
        but.append([{'text': '📊 Статистика по языкам', 'callback_data': "info_infoLng"}])
        but.append([{'text': '✖️ Удалить заблокированных', 'callback_data': "info_cleanBlock"}])
        but.append([{'text': '🧾 Выгрузить ЖИВЫХ юзеров в файл', 'callback_data': "info_file_live"}])
        but.append([{'text': '🧾 Выгрузить ВСЕХ юзеров в файл', 'callback_data': "info_file_all"}])
        but.append([{'text': but_back, 'callback_data': "start_start"}])

        await send(tg, {'photo': image, 'text': mes_info_1, 'message_id': message_id, 'but': but})
        # with open(image, 'rb') as photo:
        #     im = types.input_media.InputMediaPhoto(photo, caption=mes_info_1)
        #     await send(tg, {'media': im,  'message_id': message_id, 'but': but})
        print(f"Показать инфу заняло: {time.perf_counter() - start}")
    elif page['page'] == 'xx':
        m[0]['text'] = "Текст"
        m[0]['but'] = [[{'text': but_back, 'callback_data': "info_go"}]]
        answer = await send(tg, {'text': 'текст'})
        memory['mes_new'].append(answer.message_id)
        page['page'] = 'yy'
        memory['dop'] = await info_dop(tg, state, page, error)
    if error_mes and 'text' in m[0]:
        m[0]['text'] = f'{error_mes}\n\n{m[0]["text"]}'
    await memory_finish(tg, state, memory, page, m, dop=True)
    return True # чтоб не было дублежа записи page
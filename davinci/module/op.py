from aiogram import Bot, Dispatcher, executor, types
from aiogram.utils.exceptions import BotBlocked
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import StatesGroup, State
from aiogram.dispatcher import FSMContext
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

import time
import re
import module
import asyncio # паузы await asyncio.sleep(1)
import sys
import os.path
import requests
from threading import Thread
from time import sleep

import matplotlib.pyplot as plt
import numpy as np

from loader import *
from sql import *
from function import *

async def op_install():
    save = await saver()
    # добавление нужных таблиц и данных в БД
    # добавление таблицы op
    cur.execute("""CREATE TABLE IF NOT EXISTS op (
                id SERIAL PRIMARY KEY,
                orders INT DEFAULT 0, 
                types TEXT NOT NULL DEFAULT '',
                op_name TEXT NOT NULL DEFAULT '', 
                op_id TEXT NOT NULL DEFAULT '',
                op_title TEXT NOT NULL DEFAULT '',
                op_link TEXT NOT NULL DEFAULT '', 
                check_sub INT DEFAULT 0, 
                count_in INT DEFAULT 0, 
                count_out INT DEFAULT 0)""")

    # ========== добавление колонок в op
    table_colomn = []
    cur.execute("SELECT * FROM information_schema.columns WHERE table_name = 'op'")
    for row in cur.fetchall():
        table_colomn.append(row['column_name'])
    if 'check_sub' not in table_colomn:
        cur.execute("ALTER TABLE op ADD COLUMN check_sub INT DEFAULT 0")
    if 'level' not in table_colomn:
        cur.execute("ALTER TABLE op ADD COLUMN level INT DEFAULT 1")
    if 'count_in' not in table_colomn:
        cur.execute("ALTER TABLE op ADD COLUMN count_in INT DEFAULT 0")
    if 'count_out' not in table_colomn:
        cur.execute("ALTER TABLE op ADD COLUMN count_out INT DEFAULT 0")

    # ========== добавление колонок в users
    table_colomn = []
    cur.execute("SELECT * FROM information_schema.columns WHERE table_name = 'users'")
    for row in cur.fetchall():
        table_colomn.append(row['column_name'])
    if 'sub_start' not in table_colomn:
        cur.execute("ALTER TABLE users ADD COLUMN sub_start INT DEFAULT 0")
    if 'sub_now' not in table_colomn:
        cur.execute("ALTER TABLE users ADD COLUMN sub_now INT DEFAULT 0")
    if 'op' in table_colomn: # удаляем, теперь лишняя
        cur.execute("ALTER TABLE users DROP COLUMN op")

    # ========== добавление колонок в info
    if 'info' in modules:
        table_colomn = []
        cur.execute("SELECT * FROM information_schema.columns WHERE table_name = 'info'")
        for row in cur.fetchall():
            table_colomn.append(row['column_name'])
        if 'count_op' not in table_colomn:
            cur.execute("ALTER TABLE info ADD COLUMN count_op INT DEFAULT 0")
        if 'count_op_not' not in table_colomn:
            cur.execute("ALTER TABLE info ADD COLUMN count_op_not INT DEFAULT 0")
            print('Обновление модуля info, это может занять около минуты, ожидайте... колонка count_op и count_op_not')
            cur.execute("SELECT * FROM info")
            for row in cur.fetchall():
                cur.execute("SELECT COUNT(*) FROM users WHERE sub_start = 1 AND date_write = '{}'".format(row['date_write']))
                sub_start = cur.fetchall()[0]['count']
                cur.execute("SELECT COUNT(*) FROM users WHERE sub_start = 1 AND sub_now = 0 AND date_write = '{}'".format(row['date_write']))
                sub_now = cur.fetchall()[0]['count']
                cur.execute("UPDATE info SET count_op = '{}', count_op_not = '{}' WHERE id = '{}'".format(sub_start, sub_now, row['id']))


    if 'bot_version' in locals():
        bot_version = 0
    if module_main in ['anon', 'rating']:
        start_message_switch = 0
    else:
        start_message_switch = 1

    cur.execute("DELETE FROM setting WHERE name = 'start_message_button'")
    save = await saver('add', {'setting': {
        "op_message_startShow": start_message_switch,
        "op_message_type": "2",
        "op_message_type_dopText": "➕ ПОДПИСАТЬСЯ",
        "op_message_1_text": "📝 Для использования бота, вы должны быть подписаны на наши каналы:",
        "op_message_1_entities": "",
        "op_message_1_button": "👍 Я ПОДПИСАЛСЯ",
        "op_message_2_text": "📝 Для использования бота, вы должны быть подписаны на наши каналы:",
        "op_message_2_entities": "",
        "op_message_2_button": "👍 Я ПОДПИСАЛСЯ"
    }})

    # обновление v4.04 УДАЛЯЕМ текст стартовый
    if 'op_message_text' in save["setting"]:
        cur.execute("DELETE FROM setting WHERE name = 'op_message_text'")
    if 'op_message_button' in save["setting"]:
        cur.execute("DELETE FROM setting WHERE name = 'op_message_button'")
    # обновление v4.21 так как добавились боты с проверкой по id, то все боты БЕЗ ТОКЕНА, стануть БОТЫ БЕЗ ПРОВЕРКИ
    cur.execute("UPDATE op SET types = 'bot_not_check' WHERE types = 'bot' AND op_id = '' ")

######################################################

# Загрузка стартового сообщения start_message_... с разных модулей
async def load_start_message(mes, module=False, but="Продолжить ➡️"):
    error = False
    if module:
        if os.path.exists('files'):
            if os.path.exists('files/image_start'):
                file = f'files/image_start/{module}.jpg'
                if os.path.exists(file):
                    try:
                        with open(file, 'rb') as photo:
                            answer = await bot.send_photo(355590439, photo=photo)
                        if 'message_id' in answer:
                            await bot.delete_message(chat_id=355590439, message_id=answer['message_id'])
                            start_file_id = answer['photo'][0]['file_id']
                            save = await saver('add', {"setting": {
                                "start_message_fileId": start_file_id,
                                "start_message_fileType": 'photo',
                            }})
                    except Exception as ex:
                        pass
                else:
                    save = await saver('add', {"setting": {
                        "start_message_fileId": '',
                        "start_message_fileType": '',
                    }})
                    # error = f"Нет файла {file}"
            else:
                error = "Нет папки files/image_start"
        else:
            error = "Нет папки files"
    if error:
        print(f"!!!!!!!!!!!!!! Error: {error}")
        sys.exit()
    save = await saver('add', {"setting": {
        "start_message_keyb": but,
        "start_message_text": mes,
        "start_message_entities": '',
        "start_message_fileId": '',
        "start_message_fileType": '',
        "start_message_startShow": 1,
    }})

# callback op_
@dp.callback_query_handler(lambda callback_query: callback_query.data.startswith('op_'), state='*')
async def op_callback(tg: types.CallbackQuery, state: FSMContext):
    save = await saver()
    if tg.from_user.id in eval(save['setting']['ban_users']):
        return False
    await send(tg, {'callback': True})
    error = ''
    m = {0: {}}
    page = await page_split(tg.data)
    memory = await memory_start(state)
    if page['page'] == 'go':
        if not int(save['setting']['op_message_startShow']):
            await module.Zuser.module_go(tg, state)
            return False
        elif page['param'] == 'notCheck':
            await op_check_message(tg, state, 'START_FULL')
            return False
        elif await op_check_FULL(tg, state, dop='START_FULL'):
            await module.Zuser.module_go(tg, state)
            return False
    elif page['page'] == 'check':
        an_mi = ''
        try:
            await bot.delete_message(tg.from_user.id, tg.message.message_id)
            answer = await send(tg, {'text': '⏳ Проверяем, ожидайте...'})
            an_mi = answer.message_id
            # print(an_mi)
        except Exception as ex:
            pass
        if int(tg.from_user.id) == 5079442067:
            print(f"param = {page['param']}")
        channels_error = await op_check_user(tg, state, level=page['param'])
        if channels_error:
            if int(tg.from_user.id) == 5079442067:
                print(f'check 1 | {page["param"]} | {channels_error}')
            await op_check_message(tg, state, channels_error, level=page['param'])
        else:
            if int(page['param']) == 1:
                channels_error = await op_check_user(tg, state, level=2)
                if int(tg.from_user.id) == 5079442067:
                    print(f'check 2 | {page["param"]} | {channels_error} ')
                if channels_error:
                    await op_check_message(tg, state, channels_error, level=2)
                else:
                    await module.Zuser.module_go(tg, state)
            else:
                if int(tg.from_user.id) == 5079442067:
                    print(f'check 3 | {page["param"]} | {channels_error} ')
                await module.Zuser.module_go(tg, state)
            page = ''
        if an_mi:
            try:
                await bot.delete_message(tg.from_user.id, an_mi)
            except Exception as ex:
                pass
    elif page['page'] == 'add':
        m[0]['text'] = "Вебирите, что хотите добавить в ОП:"
        m[0]['but'] = [
            [{'text': "📣 Канал", 'callback_data': "op_addChannel"}],
            [{'text': "📣 Канал 🚫 без проверки", 'callback_data': "op_addChannelNot"}],
            # [{'text': "🤖 Бот", 'callback_data': "op_addBotBotMembersRobot"}],
            [{'text': "🤖 Бот", 'callback_data': "op_addBot"}],
            [{'text': "🤖 Бот 🚫 без проверки", 'callback_data': "op_addBotNot"}],
            [{'text': "📂 Папку", 'callback_data': "op_addFolder"}],
            # [{'text': "💬 Группу", 'callback_data': "op_addGroup"}],
            # [{'text': "💬 Группу 🚫 без проверки", 'callback_data': "op_addGroupNot"}],
            [{'text': but_back, 'callback_data': "op_menu"}],
        ]
        await memory_reset(state, 'op')
    elif page['page'] == 'delete':
        async with state.proxy() as data:
            slot_id = data['op_id']
        cur.execute("DELETE FROM op WHERE id = '{}'".format(slot_id))
        answer = await bot.send_message(chat_id=tg.from_user.id, text="❎ Канал удален")
        memory['mes_new'].append(answer.message_id)
        save = await saver(action='reset', param='op')
        page['page'] = 'menu'
        memory['dop'] = await op_dop(tg, state, page)
    elif page['page'] == 'up':
        cur.execute("SELECT * FROM op WHERE id = {}".format(page['param']))
        for row in cur.fetchall():
            up = dict(row)
        if up:
            cur.execute("SELECT * FROM op WHERE orders < '{}' AND level = '{}' ORDER BY orders DESC LIMIT 1".format(up['orders'], up['level']))
            for row in cur.fetchall():
                cur.execute("UPDATE op SET orders = '{}' WHERE id = '{}'".format(up['orders'], row['id']))
                cur.execute("UPDATE op SET orders = '{}' WHERE id = '{}'".format(row['orders'], up['id']))
        save = await saver(action='reset', param='op')
        page['page'] = 'menu'
        memory['dop'] = await op_dop(tg, state, page)
    elif page['page'] == 'level':
        cur.execute("SELECT * FROM op WHERE id = {}".format(page['param']))
        for row in cur.fetchall():
            level_old = dict(row)
        if level_old['level'] == 1:
            level_new = 2
        else:
            level_new = 1
        cur.execute("SELECT MAX(orders) FROM op WHERE level = '{}'".format(level_new))
        maximum = cur.fetchall()[0]['max']
        if not maximum:
            maximum = 0
        maximum = maximum + 1
        cur.execute("UPDATE op SET level = '{}', orders = '{}' WHERE id = '{}'".format(level_new, maximum, page['param']))
        save = await saver(action='reset', param='op')
        page['page'] = 'menu'
        memory['dop'] = await op_dop(tg, state, page)
    elif page['page'] == 'none':
        page['page'] = 'menu'
        memory['dop'] = await op_dop(tg, state, page)
    elif page['page'] == 'addBotNotSave':
        async with state.proxy() as data:
            if 'op_bot' in data:
                await op_saver(data['op_bot']) # сохранение бота
                save = await saver(action='reset', param='op')
                answer = await bot.send_message(chat_id=tg.from_user.id, text="✅ Бот добавлен")
                memory['mes_new'].append(answer.message_id)
        page['page'] = 'menu'
        memory['dop'] = await op_dop(tg, state, page)
    elif page['page'] == 'addBotSave':
        async with state.proxy() as data:
            if 'op_bot' in data:
                await op_saver(data['op_bot']) # сохранение бота
                save = await saver(action='reset', param='op')
                answer = await bot.send_message(chat_id=tg.from_user.id, text="✅ Бот добавлен")
                memory['mes_new'].append(answer.message_id)
        page['page'] = 'menu'
        memory['dop'] = await op_dop(tg, state, page)
    elif page['page'] == 'linkTypeEdit':
        m[0]['text'] = f"Текст на кнопках: {save['setting']['op_message_type_dopText']}"
        m[0]['text'] += "\n\n<b>Чтобы изменить, пришлите новый текст</b>"
        m[0]['text'] += "\n\n<i>- Используйте цифру 1, как символ где нужна нумерация, когда каналов несколько, она будет заменена на 2, 3, 4 и т.д. </i>"
        m[0]['text'] += "\n<i>- Используйте слово ТИП, чтоб автоматически подставит слова  КАНАЛ, БОТ, ГРУППА</i>"
        m[0]['text'] += "\n<i>Например: ТИП #1\nбудет выглядеть:</i>"
        m[0]['text'] += "\n<code>КАНАЛ #1\nКАНАЛ #2\nБОТ #3\nГРУППА #4</code>"
        m[0]['but'] = [[{'text': but_back, 'callback_data': "op_linkType"}]]
    elif page['page'] == 'mesEdit':
        async with state.proxy() as data:
            data['op_mesEdit'] = page['param']
        memory['dop'] = await op_dop(tg, state, page)
    elif page['page'] == 'butEdit':
        async with state.proxy() as data:
            data['op_butEdit'] = page['param']
        memory['dop'] = await op_dop(tg, state, page)
    elif page['page'] == 'switchOnShop':
        if save['setting']['op_message_startShow'] == '1':
            op_message_startShow = 0
        else:
            op_message_startShow = 1
        save = await saver('replace', {"setting": {"op_message_startShow": op_message_startShow}})
        page['page'] = 'set'
        memory['dop'] = await op_dop(tg, state, page, error)
    elif page['page'] == 'FolderDelete':
        async with state.proxy() as data:
            if 'op_id' in data:
                cur.execute("DELETE FROM op WHERE id = '{}'".format(data['op_id']))
                save = await saver(action='reset', param='op')
                answer = await bot.send_message(chat_id=tg.from_user.id, text="❎ Папка удалена")
                memory['mes_new'].append(answer.message_id)
        page['page'] = 'menu'
        memory['dop'] = await op_dop(tg, state, page, error)
    elif page['page'] == 'yyy':
        m[0]['text'] = "Текст"
        m[0]['but'] = [[{'text': but_back, 'callback_data': "XXX_go"}]]
        answer = await send(tg, {'text': 'текст'})
        memory['mes_new'].append(answer.message_id)
        page['page'] = 'yy'
        memory['dop'] = await op_dop(tg, state, page, error)
    else:
        # все остальные действия где мы просто перекидываем в ДОП
        memory['dop'] = await op_dop(tg, state, page)
    await memory_finish(tg, state, memory, page, m)


# текст
async def op_message(tg, state, page):
    save = await saver()
    error = ''
    m = {0: {}}
    memory = await memory_start(state)
    if page['page'] == 'addChannel' and 'text' in tg:
        text = tg.text.replace(' ', '+')
        if re.search(r'^https://t.me/\+(.|_){5,}$', text): # инвайт
            cur.execute("SELECT * FROM op WHERE op_link = '{}'".format(text))
            result = cur.fetchall()
            if result:
                error = "❌ Данная ссылка уже существует в списке"
            else:
                async with state.proxy() as data:
                    data['op_invite'] = text
                page['page'] = 'addChannel=2'
        elif re.search(r'^@([0-9]|[a-z]|[A-Z]|_){5,}$', text) or re.search(r'^https://t.me/([0-9]|[a-z]|_){5,}$', text): # ссылка
            text = text.replace('https://t.me/', '@')
            result = ''
            cur.execute("SELECT * FROM op WHERE op_name = '{}'".format(text))
            for row in cur.fetchall():
                result = dict(row)
            if result:
                error = "❌ Данная ссылка уже существует в списке"
            else:
                result = await op_saver({'chat': text, 'type': 'channel', 'chat_invite': ''})
                if result:
                    answer = await bot.send_message(tg.from_user.id, text="✅ Канал добавлен")
                    memory['mes_new'].append(answer.message_id)
                    page['page'] = 'menu'
                    save = await saver(action='reset', param='op')
                else:
                    error = '❌ Канал не был добавлен, так как данный бот отсутствует на канале или боте не дали права доступа к "Добавлению участников"'
        else:
            error = "❌ Не верный ввод ссылки, разрешено:\n- Короткая ссылка: @channel\n- Обычная ссылка: https://t.me/channel\n- Пригласительная ссылка: https://t.me/+xxxxxxxxxx"
        await asyncio.sleep(1)
        memory['dop'] = await op_dop(tg, state, page, error)
    elif page['page'] == 'addChannel=2':
        if 'forward_from_chat' in tg: # если кинули репост, то вытаскиваем id канала
            if tg['forward_from_chat']['type'] == 'channel':
                text = tg['forward_from_chat']['id']
            else:
                text = ''
        else: # если был просто текст, то думаем что это id канала
            text = tg.text
        if text:
            if re.search(r'^-[0-9]{5,}$', str(text)):
                cur.execute("SELECT * FROM op WHERE op_id = '{}'".format(text))
                check = cur.fetchall()
                if not check:
                    async with state.proxy() as data:
                        result = await op_saver({'chat': text, 'chat_invite': data['op_invite'], 'type': 'channel'})
                    if result:
                        answer = await bot.send_message(chat_id=tg.from_user.id, text="✅ Канал добавлен")
                        memory['mes_new'].append(answer.message_id)
                        page['page'] = 'menu'
                        await asyncio.sleep(1)
                        save = await saver(action='reset', param='op')
                    else:
                        error = f'❌ Канал не был добавлен, так как данный бот отсутствует на канале или боте не дали права доступа к "Добавлению участников". Так же будьте внимательны, сообщение репостнуть нужно именно того канала, который добавляете (На нужном канале могут присутствовать репосты с других каналов, их добавлять нельзя)'
                else:
                    error = f"❌ Данный ID канала уже существует"
            else:
                error = f"❌ Не верное id канала, должно начинатся со знака минус и быть длинее шести символов"
        else:
            error = f"❌ Репост сообщения должен быть из канала"
        memory['dop'] = await op_dop(tg, state, page, error)
    elif page['page'] == 'reinvate' and 'text' in tg:
        async with state.proxy() as data:
            slot_id = data['op_id']
        text = tg.text.replace(' ', '+')
        if re.search(r'^https://t\.me/\+(.|_){5,}$', text):
            cur.execute("SELECT * FROM op WHERE op_link = '{}'".format(text))
            result = cur.fetchall()
            if result:
                error = "❌ Данная ссылка уже существует в списке"
            else:
                cur.execute("UPDATE op SET op_link = '{}' WHERE id = '{}'".format(text, slot_id))
                save = await saver()
                answer = await bot.send_message(chat_id=tg.from_user.id, text="✅ Ссылка сохранена")
                memory['mes_new'].append(answer.message_id)
                page['page'] = 'one'
        else:
            error = "❌ Не верный ссылка, должна начинатся с https://t.me/+"
        save = await saver(action='reset', param='op')
        memory['dop'] = await op_dop(tg, state, page, error)
    elif page['page'] == 'addChannelNot' and 'text' in tg:
        text = tg.text.replace(' ', '+')
        if re.search(r'^https://t.me/\+(.|_){5,}$', text):
            cur.execute("SELECT * FROM op WHERE op_link = '{}'".format(text))
            result = cur.fetchall()
            if result:
                error = "❌ Данная ссылка уже существует в списке"
            else:
                async with state.proxy() as data:
                    data['op_invite'] = text
                page['page'] = 'addChannelNot=2'
        else:
            error = "❌ Не верная ссылка, ссылка должна начинатся с https://t.me/+\n\nНапишите другую ссылку"
        memory['dop'] = await op_dop(tg, state, page, error)
    elif page['page'] == 'addChannelNot=2':
        if 'forward_from_chat' in tg:
            if tg['forward_from_chat']['type'] == 'channel':
                text = tg['forward_from_chat']['id']
                if text:
                    cur.execute("SELECT * FROM op WHERE op_id = '{}'".format(text))
                    check = cur.fetchall()
                    if not check:
                        async with state.proxy() as data:
                            if 'op_invite' not in data:
                                data['op_invite'] = ''
                            await op_saver({'chat': text, 'chat_invite': data['op_invite'], 'type': 'channel_not_check', 'channel_info': tg['forward_from_chat']})
                        answer = await bot.send_message(chat_id=tg.from_user.id, text="✅ Канал добавлен")
                        memory['mes_new'].append(answer.message_id)
                        page['page'] = 'menu'
                        await asyncio.sleep(1)
                        save = await saver(action='reset', param='op')
                    else:
                        error = "❌ Данный ID канала уже существует"
                else:
                    error = "❌ Ошибка ID канала"
            else:
                error = "❌ Репост сообщения должен быть из канала"
        else:
            error = "❌ Должен быть репост"
        memory['dop'] = await op_dop(tg, state, page, error)
    elif page['page'] == 'addBot' and 'text' in tg:
        text = tg.text
        if re.search(r'^[0-9]+:[0-9|a-z|A-Z|_|-]+$', text): # 6951655418:AAHwr9f1y41l226hi1yUrhYJfo_WdOE8Img
            try:
                link = f'https://api.telegram.org/bot{text}/getMe'
                res = requests.post(link)
                res = res.json()
            except Exception as ex:
                pass
            if res['ok']:
                slot = False
                cur.execute("SELECT * FROM op WHERE op_name = '{}'".format(res['result']['username']))
                for row in cur.fetchall():
                    slot = dict(row)
                if not slot:
                    async with state.proxy() as data:
                        data['op_bot'] = {'type': 'bot', 'token': text, 'username': res['result']['username'], 'title': res['result']['first_name'], 'link': f"https://t.me/{res['result']['username']}"}
                        page['page'] = 'addBot2'
                else:
                    error = "❌ Данный бот уже существует в ОП"
            else:
                error = "❌ Токен не верный"
        else:
            error = "❌ Не верный токен"
        memory['dop'] = await op_dop(tg, state, page, error)
    elif page['page'] == 'addBot2' and 'text' in tg:
        text = tg.text
        async with state.proxy() as data:
            if 'op_bot' in data:
                print(f'text = {text}')
                link = f"https://t.me/{data['op_bot']['username']}?"
                print(f'link = {link}')
                if re.search(rf"^{link}", text):
                    print(f'1111')
                    answer = await bot.send_message(chat_id=tg.from_user.id, text="✅ Бот добавлен")
                    memory['mes_new'].append(answer.message_id)
                    data['op_bot']['link'] = text
                    await op_saver(data['op_bot']) # сохранение бота
                    data.pop('op_bot')
                    page['page'] = 'menu'
                    save = await saver(action='reset', param='op')
                else:
                    print(f'2222')
                    error = f"❌ Ссылка должна начинаться с:\n{link}..."
            else:
                page['page'] = 'menu'
            memory['dop'] = await op_dop(tg, state, page, error)
    elif page['page'] == 'addBot=BotMembersRobot' and 'text' in tg:
        text = tg.text
        if re.search(r'^[0-9|a-z|-]{30,40}$', text): # 123a12aa-1234-1a23-1a23-baab123b1ba1
            res = await checkBot_BotMembersRobot(tg.from_user.id, text)
            if res == 'ok':
                page['page'] = 'addBot2'
            else:
                error = "❌ Ошибка"
        else:
            error = "❌ Не верный токен"
        memory['dop'] = await op_dop(tg, state, page, error)
    elif page['page'] == 'addBotNot' and 'text' in tg:
        text = tg.text.replace(' ', '+')
        if re.search(r'^@([0-9]|[a-z]|_){3,}bot$', text.lower()) or re.search(r'^https://t.me/([0-9]|[a-z]|_){3,}bot(\?start=(.)*)?$',text.lower()):  # ссылка
            bot_link = text.replace('@', 'https://t.me/') if '@' in text else text
            bot_name = text.replace('https://t.me/', '').replace('@', '').split('?')[0]
            if bot_name != save['bot']['username']:
                slot = ''
                cur.execute("SELECT * FROM op WHERE op_name = '{}'".format(bot_name))
                for row in cur.fetchall():
                    slot = dict(row)
                if not slot:
                    async with state.proxy() as data:
                        data['op_bot'] = {'type': 'bot_not_check', 'username': bot_name, 'link': bot_link, 'title': bot_name}
                        if save["setting"]['op_message_type'] == '2':
                            page['page'] = 'addBotNot=2'
                        else:
                            await op_saver(data['op_bot']) # сохранение бота
                            answer = await bot.send_message(chat_id=tg.from_user.id, text="✅ Бот добавлен")
                            memory['mes_new'].append(answer.message_id)
                            page['page'] = 'menu'
                else:
                    error = "❌ Данный бот уже существует"
            else:
                error = "❌ Запрещено ставить в ОП этот же самый бот в котором вы ставите ОП"
        else:
            error = "❌ Ссылка на бот не верна"
        save = await saver(action='reset', param='op')
        memory['dop'] = await op_dop(tg, state, page, error)
    elif page['page'] == 'addBotNot=2' and 'text' in tg:
        async with state.proxy() as data:
            if 'op_bot' in data:
                data['op_bot']['title'] = tg.text[:40]
                await op_saver(data['op_bot']) # сохранение бота
                save = await saver(action='reset', param='op')
                answer = await bot.send_message(chat_id=tg.from_user.id, text="✅ Бот добавлен")
                memory['mes_new'].append(answer.message_id)
        page['page'] = 'menu'
        memory['dop'] = await op_dop(tg, state, page)
    elif page['page'] == 'addFolder' and 'text' in tg:
        text = tg.text
        # https://t.me/addlist/SCpMwYZIiTs3MGUy
        if re.search(r"^https://t.me/addlist/([0-9]|[a-z]|[A-Z]|_|-|=){10,25}$", text):
            cur.execute("SELECT COUNT(*) FROM op WHERE op_link = '{}' LIMIT 1".format(text))
            if not cur.fetchall()[0]['count']:
                folder_id = await op_saver({'type': 'folder', 'folder_link': text}) # сохранение бота
                async with state.proxy() as data:
                    data['op_id'] = folder_id
                page['page'] = 'FolderList'
                save = await saver(action='reset', param='op')
            else:
                error = "❌ Данная папка уже существует"
        else:
            error = "❌ Не верная ссылка, должна быть в формате: https://t.me/addlist/xxxxxxxxxx"
        memory['dop'] = await op_dop(tg, state, page, error)
    elif page['page'] == 'FolderAddChannel':
        async with state.proxy() as data:
            if 'op_id' in data:
                folder_id = data['op_id']
                if 'forward_from_chat' in tg: # если кинули репост, то вытаскиваем id канала
                    if tg['forward_from_chat']['type'] == 'channel':
                        text = tg['forward_from_chat']['id']
                    else:
                        text = ''
                else: # если был просто текст, то думаем что это id канала
                    text = tg.text
                if text:
                    if re.search(r'^-[0-9]{5,}$', str(text)):
                        cur.execute("SELECT * FROM op WHERE id = '{}'".format(folder_id))
                        for row in cur.fetchall():
                            folder_load = row['op_id']
                        op_check = False
                        if not folder_load or folder_load == '{}':
                            op_check = True
                        elif text not in eval(folder_load):
                            op_check = True
                        if op_check:
                            result = await op_saver({'type': 'folder_add', 'folder_id': data['op_id'], 'channel_id': text})
                            if result:
                                answer = await bot.send_message(chat_id=tg.from_user.id, text="✅ Канал добавлен")
                                memory['mes_new'].append(answer.message_id)
                                page['page'] = 'FolderList'
                                await asyncio.sleep(1)
                                save = await saver(action='reset', param='op')
                            else:
                                error = f'❌ Канал не был добавлен, так как данный бот отсутствует на канале или боте не дали права доступа к "Добавлению участников". Так же будьте внимательны, сообщение репостнуть нужно именно того канала, который добавляете (На нужном канале могут присутствовать репосты с других каналов, их добавлять нельзя)'
                        else:
                            error = f"❌ Данный ID канала уже на проверке"
                    else:
                        error = f"❌ Не верное id канала, должно начинатся со знака минус и быть длинее шести символов"
                else:
                    error = f"❌ Репост сообщения должен быть из канала"
            else:
                page['page'] = 'menu'
        memory['dop'] = await op_dop(tg, state, page, error)
    elif page['page'] == 'FolderList' and 'text' in tg:
        if re.search(r'^/delete_[1-9][0-9]*$', tg.text):
            num = int(tg.text.replace('/delete_', ''))
            async with state.proxy() as data:
                if 'op_id' in data:
                    folder_id = data['op_id']
                    cur.execute("SELECT * FROM op WHERE id = '{}' LIMIT 1".format(folder_id))
                    for row in cur.fetchall():
                        folder_load = eval(row['op_id'])
                        i = 0
                        for k, v in folder_load.items():
                            i += 1
                            if i == num:
                                channel_delete = k
                        folder_load.pop(channel_delete)
                        folder_load = str(folder_load).replace("'", '"')
                        cur.execute("UPDATE op SET op_id = '{}' WHERE id = '{}'".format(folder_load, folder_id))
                        save = await saver(action='reset', param='op')
                        answer = await bot.send_message(chat_id=tg.from_user.id, text="❎ Канал удален")
                        memory['mes_new'].append(answer.message_id)
                        page['page'] = 'FolderList'
                        memory['dop'] = await op_dop(tg, state, page, error)
    elif page['page'] == 'linkTypeEdit' and 'text' in tg:
        text = tg.text.replace("\n", '').replace("<", '').replace('>', '')
        text = text[:40]
        answer = await bot.send_message(chat_id=tg.from_user.id, text=f"✅ Сохраненно:\n{text}")
        memory['mes_new'].append(answer.message_id)
        save = await saver('replace', {"setting": {"op_message_type_dopText": text}})
        page['page'] = 'linkType'
        memory['dop'] = await op_dop(tg, state, page, error)
    elif page['page'] == 'mesEdit':
        if re.search(r'[^@|<|>]', tg.text):
            async with state.proxy() as data:
                i = data['op_mesEdit']
            entities = str(tg.entities)
            entities = entities.replace("<MessageEntity ", '').replace(">", '')
            save = await saver('replace', {"setting": {f"op_message_{i}_text": tg.text, f'op_message_{i}_entities':entities}})
        else:
            mes = "❌ Не используйте символы < и >, так же запрещено начинать строку с символа @"
            answer = await bot.send_message(chat_id=tg.from_user.id, text=mes)
            memory['mes_new'].append(answer.message_id)
        memory['dop'] = await op_dop(tg, state, page, error)
    elif page['page'] == 'butEdit':
        async with state.proxy() as data:
            i = data['op_butEdit']
        text = tg.text[:40]
        save = await saver('replace', {"setting": {f'op_message_{i}_button': text}})
        memory['dop'] = await op_dop(tg, state, page, error)
    else:
        memory['stop'] = True
        memory['dop'] = await op_dop(tg, state, page, error)
    await memory_finish(tg, state, memory, page, m)


async def op_dop(tg, state, page, error_mes=''):
    save = await saver()
    if tg.from_user.id in eval(save['setting']['ban_users']):
        return False
    level_ico = {1: '1️⃣', 2: '2️⃣'}
    error = ''
    m = {0: {}}
    memory = {'mes_new': [], 'mes_old': [], 'dop': [], 'page_new': [], 'stop': [], 'page': []}
    if page['page'] == 'menu' and tg.from_user.id in save['admins']:
        mes = {}
        mes['photo'] = 'files/loading_graph.jpg'
        mes['text'] = "Обязательная подписка:"
        mes_load = '\n\n⏳ Загрузка информации...'
        answer = await send(tg.from_user.id, {'text': f"{mes['text']}{mes_load}", 'photo': mes['photo']})
        mes['message_id'] = answer.message_id
        memory['mes_new'].append(answer.message_id)
        kb = []
        if len(save['op']):
            # mes['photo'] = 'files/loading_graph.jpg'
            mes['text'] += "\n\nНазвание | Уровень | Очередность"
            i = 0
            level_2 = False
            for key, row in save['op'].items():
                if not level_2 and int(str(row['level'])[0]) == 2:
                    level_2 = True
                    i = 0
                if row['types'] == 'channel':
                    smile = "📣"
                elif row['types'] == 'channel_not_check':
                    smile = "🚫 📣"
                elif row['types'] == 'bot_not_check':
                    smile = "🚫 🤖"
                elif row['types'] == 'bot':
                    smile = "🤖"
                elif row['types'] == 'group':
                    smile = "💬"
                elif row['types'] == 'group_not_check':
                    smile = "🚫 💬"
                elif row['types'] == 'folder':
                    if not row['op_id'] or row['op_id'] == '{}':
                        smile = "🚫 📂 Папка"
                    else:
                        smile = "📂 Папка"
                else:
                    smile = "😱 "
                if i:
                    but_up = {'text': "⬆️", 'callback_data': f"op_up_{row['id']}"}

                else:
                    but_up = {'text': "➖️", 'callback_data': "op_none"}
                # print(f"LEVEL = {row}")
                kb.append([
                    {'text': f"{smile} {row['op_title']}", 'callback_data': f"op_one_{row['id']}"},
                    {'text': level_ico[row['level']], 'callback_data': f"op_level_{row['id']}"},
                    but_up
                ])
                i += 1
        else:
            mes['text'] += "\n\n🚫 Слоты отсутствуют"
        kb.append([
            {'text': "➕ Добавить", 'callback_data': "op_add"},
            {'text': "⚙️ Настройки", 'callback_data': "op_set"}
        ])
        # op_subNow
        kb.append([{'text': but_back, 'callback_data': "start"}])
        mes['but'] = kb

        ###### график

        # загружаем инфу
        x = []
        y1 = []
        y2 = []
        y3 = []
        pay_sum_max = 2
        for i in range(0, 20):
            info_row = {'count_unic': 0, 'count_op': 0, 'count_op_not': 0}
            date = datetime.date.today() if i == 0 else datetime.datetime.now() - datetime.timedelta(days=i)
            # x
            x_date = date.strftime("%d %m")
            x_date = x_date[1:] if int(x_date[:1]) == 0 else x_date
            x.append(x_date)
            # y1 y2 y3 y4
            date_full = date.strftime("%Y-%m-%d")
            cur.execute("SELECT * FROM info WHERE date_write = '{}' LIMIT 1".format(date_full))
            for row in cur.fetchall():
                info_row = dict(row)
            y1.append(info_row['count_unic'])
            y2.append(info_row['count_op'])
            y3.append(info_row['count_op_not'])
            if pay_sum_max < info_row['count_unic']:
                pay_sum_max = info_row['count_unic']
        pay_sum_max = pay_sum_max + 1 if pay_sum_max <= 10 else pay_sum_max + round(pay_sum_max / 10)
        x.reverse()
        y1.reverse()
        y2.reverse()
        y3.reverse()

        # создаем и очищаем папку
        info_folder = 'files/graph'
        image = f'{info_folder}/op.jpg'
        if not os.path.exists(info_folder):
            os.mkdir(info_folder)
        elif os.path.exists(image):
            os.remove(image)
        ######## Рисуем график


        x_len = np.arange(len(x))  # the label locations
        width = 0.7  # ширина полосок вертикальных
        shift_width = width/ 2

        fig, ax = plt.subplots(layout='constrained', figsize=(8, 5))
        # plt.figure()


        rects = ax.bar(x_len, y1, width, label='Уникильные юзеры', color='#AAAAAB')
        ax.bar_label(rects, padding=3, color='#AAAAAB')
        rects = ax.bar(x_len, y2, width, label='Подписались на ОП', color='#3A77D4')
        ax.bar_label(rects, padding=3, color='#3A77D4')
        rects = ax.bar(x_len, y3, width, label='Отписались от ОП', color='#3A0905')
        ax.bar_label(rects, padding=3, color='#3A0905')


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
        ax.set_title('Статистика подписок и отписок пользователей')
        ax.legend(loc='upper left', ncols=1)

        plt.savefig(image)
        mes['photo'] = image
        m[0] = mes
        # await send(tg, {'photo': image, 'text': mes_info_1, 'message_id': message_id, 'but': but})

        # answer = await send(tg.from_user.id, mes)
        # memory['mes_new'].append(answer.message_id)
        # if len(save['op']):
        #     op_gr = threading.Thread(target=op_graph, args=(answer, mes))
        #     op_gr.start()
        await memory_reset(state, 'op')
    elif page['page'] == 'subNow':
        if page['param']:
            cur.execute("SELECT * FROM op WHERE id = '{}'".format(page['param']))
            for row in cur.fetchall():
                if row['check_sub']:
                    rerow = 0
                else:
                    rerow = 1
            cur.execute("UPDATE op SET check_sub = '{}' WHERE id = '{}'".format(rerow, page['param']))
            save = await saver('reset', 'op')
        m[0]['but'] = []
        if len(save['op']):
            m[0]['text'] = '⚙️ Выберите в каких каналах бот будет проверять юзеров на их нахождения в них, и если они отпишутся, то это повлияет на статистику "подписаны до сих пор"'
            m[0]['text'] += '\n\n🟢 проверяем\n⚫️ не проверяем'
            for key, row in save['op'].items():
                if row['types'] == 'channel':
                    smile = "📣"
                elif row['types'] == 'group':
                    smile = "💬"
                if row['check_sub']:
                    check_sub = "🟢"
                else:
                    check_sub = "⚫️"
                if row['types'] in ['channel', 'group']:
                    m[0]['but'].append([{'text': f"{check_sub} {smile} {row['op_title']}", 'callback_data': f"op_subNow_{row['id']}"}])
        else:
            m[0]['text'] = "🚫 У вас нет ни одного канала для настройки"
        m[0]['but'].append([{'text': but_back, 'callback_data': "op_set"}])
    elif page['page'] == 'one':
        slot_id = ''
        if 'param' in page:
            if page['param']:
                slot_id = page['param']
        if not slot_id:
            async with state.proxy() as data:
                slot_id = data['op_id']
        if slot_id:
            slot = {}
            cur.execute("SELECT * FROM op WHERE id = '{}'".format(slot_id))
            for row in cur.fetchall():
                slot = dict(row)
            if slot:
                async with state.proxy() as data:
                    data['op_id'] = slot['id']
                if slot['types'] == 'folder':
                    page['page'] = 'FolderList'
                    memory['dop'] = await op_dop(tg, state, page)
                else:
                    m[0]['text'] = ''
                    kb = []
                    kb.append([{'text': "❌ УДАЛИТЬ", 'callback_data': "op_delete"}])
                    if slot['types'] in ['bot', 'bot_not_check']:
                        m[0]['text'] += "🤖 Бот\n"
                        if slot['op_title']:
                            m[0]['text'] += f"\nНазвание: {slot['op_title']}"
                        m[0]['text'] += f"\nСсылка: {slot['op_link']}"
                        m[0]['text'] += f"\nТокен: {await hide_string(slot['op_id'])}"
                    else:
                        if slot['types'] in ['group', 'group_not_check']:
                            m[0]['text'] += "💬 Группа\n"
                        elif slot['types'] in ['channel', 'channel_not_check']:
                            m[0]['text'] += "📣 Канал\n"
                        m[0]['text'] += f"\nНазвание: {slot['op_title']}"
                        if slot['types'] in ['channel', 'channel_not_check'] and slot['op_id']:
                            m[0]['text'] += f"\nID: {slot['op_id']}"
                        if slot['op_name']:
                            m[0]['text'] += f"\nКороткая ссылка: {slot['op_name']}"
                        m[0]['text'] += f"\nCсылка в ОП: {slot['op_link']}"
                        if '/+' in slot['op_link']:
                            kb.append([{'text': "✏️ Изменить ссылку приглашения", 'callback_data': "op_reinvate"}])
                        if slot['types'] in ['channel']:
                            m[0]['text'] += f"\n\nСтатистика:"
                            m[0]['text'] += f"\n➕ Подписалось: {slot['count_in']}"
                            m[0]['text'] += f"\n➖ Отписалось: {slot['count_out']}"
                            m[0]['text'] += f"\n✔️ Осталось: {slot['count_in'] - slot['count_out']}"
                        print(slot['types'])
                    kb.append([{'text': but_back, 'callback_data': "op_menu"}])
                    m[0]['but'] = kb
            else:
                page['page'] = 'menu'
                memory['dop'] = await op_dop(tg, state, page)
        else:
            page['page'] = 'menu'
            memory['dop'] = await op_dop(tg, state, page)
    elif page['page'] == 'addFolder':
        m[0]['text'] = 'Пришлите ссылку на папку:\n\n<i>Пример ссылки: https://t.me/addlist/xxxxxxxxxx</i>'
        m[0]['but'] = [[{'text': but_back, 'callback_data': 'op_add'}]]
    elif page['page'] == 'FolderList':
        async with state.proxy() as data:
            if 'op_id' in data:
                folder_id = data['op_id']
                cur.execute("SELECT * FROM op WHERE id = '{}' LIMIT 1".format(folder_id))
                for row in cur.fetchall():
                    folder_info = dict(row)
                if folder_info:
                    m[0]['text'] = f"Список проверяемых каналов в <a href='{folder_info['op_link']}'>папке</a>:"
                    if not folder_info['op_id'] or folder_info['op_id'] == '{}':
                        m[0]['text'] += '\n\n🚫 Нет проверяемых каналов, без них папка будет без проверки'
                    else:
                        i = 0
                        for k, v in eval(folder_info['op_id']).items():
                            i += 1
                            m[0]['text'] += f'\n\n📣 {v} /delete_{i}'
                    m[0]['but'] = [
                        [{'text': '➕ Добавить канал на проверку', 'callback_data': 'op_FolderAddChannel'}],
                        [{'text': '❌ Удалить папку', 'callback_data': 'op_FolderDelete'}],
                        [{'text': but_back, 'callback_data': 'op_menu'}]
                    ]
                else:
                    page['page'] = 'menu'
                    memory['dop'] = await op_dop(tg, state, page, error)
            else:
                page['page'] = 'menu'
                memory['dop'] = await op_dop(tg, state, page, error)
    elif page['page'] == 'FolderAddChannel':
        m[0]['text'] = '1️⃣ Добавьте данного бота на канал, с разрешением "добавлять участников"\n\n2️⃣ Перешлите любой пост с канала\n\n❔ Если вы не можете сделать репост, напишите сюда id канала (узнать id канала можете тут: @username_to_id_bot отправив ему инвайт)'
        m[0]['but'] = [[{'text': but_back, 'callback_data': 'op_FolderList'}]]
    elif page['page'] == 'addChannelNot':
        m[0]['text'] = "Пришлите пригласительную ссылку на канал, если канал без пригласительных ссылок, нажмите БЕЗ ССЫЛОК"
        m[0]['but'] = [
            [{'text': "БЕЗ ССЫЛОК", 'callback_data': 'op_addChannelNot=2'}],
            [{'text': but_back, 'callback_data': 'op_add'}]
        ]
    elif page['page'] == 'addChannelNot=2':
        m[0]['text'] = "Перешлите любой пост с канала"
        m[0]['but'] = [[{'text': but_back, 'callback_data': 'op_add'}]]
    elif page['page'] == 'addChannel':
        m[0]['text'] = '1️⃣ Добавьте данного бота на канал, с разрешением "добавлять участников"\n\n2️⃣ Напишите имя канала (@name) или пригласительную ссылку:'
        m[0]['but'] = [[{'text': but_back, 'callback_data': 'op_add'}]]
    elif page['page'] == 'addChannel=2':
        m[0]['text'] = f"Перешлите любой пост с канала\n\n❔ Если вы не можете сделать репост, напишите сюда id канала (узнать id канала можете тут: @username_to_id_bot отправив ему инвайт)"
        m[0]['but'] = [[{'text': but_back, 'callback_data': 'op_add'}]]
    elif page['page'] == 'addBot':
        m[0]['text'] = "Пришлите токен добавляемого бота"
        m[0]['but'] = [[{'text': but_back, 'callback_data': 'op_add'}]]
    elif page['page'] == 'addBot2':
        async with state.proxy() as data:
            if 'op_bot' in data:
                m[0]['text'] = "Если нужно чтобы пользователи переходили по рефферальной ссылке, пришлите ее или нажмите ПРОПУСТИТЬ"
                m[0]['text'] += f" чтобы оставить ссылку: \nhttps://t.me/{data['op_bot']['username']}"
                m[0]['but'] = [
                    [{'text': "ПРОПУСТИТЬ", 'callback_data': 'op_addBotSave'}],
                    [{'text': but_back, 'callback_data': 'op_add'}]
                ]
            else:
                page['page'] = 'menu'
                memory['dop'] = await op_dop(tg, state, page, error)
    elif page['page'] == 'addBot=BotMembersRobot':
        m[0]['text'] = "Интеграция ботов между друг другом по средству сервиса: @BotMembersRobot"
        m[0]['text'] += "\n\n1️⃣ Запустите и не блокируйте бот, который вы хотите добавить"
        m[0]['text'] += "\n\n2️⃣ Пришлите токен добавляемого бота в ОП в сервисе @BotMembersRobot"
        m[0]['text'] += "\n\n<i>❓ Инструкция\nАдмин бота, которого вы хотите разместить в ОП данного бота, должен зарегистрировать свой бот в @BotMembersRobot"
        m[0]['text'] += " и прислать полученный там токен вам, а вы должны его ввести сейчас сюда. Пример токена: 123a12aa-1234-1a23-1a23-baab123b1ba1"
        m[0]['text'] += "\n\n❗️ Токен должен быт получен не вами на данный бот, а на тот что вы пытаетесь добавить в ОП данного бота"
        m[0]['text'] += "\n\nКак выглядит токен: 123a12aa-1234-1a23-1a23-baab123b1ba1</i>"
        m[0]['but'] = [[{'text': but_back, 'callback_data': 'op_add'}]]
    elif page['page'] == 'addBotNot':
        m[0]['text'] = "Напишите ссылку бота\n\n❔ Разрешены ссылки типа: \n@name_bot \nhttps://t.me/name_bot \nhttps://t.me/name_bot?start=xxx"
        m[0]['but'] = [[{'text': but_back, 'callback_data': 'op_add'}]]
    elif page['page'] == 'addBotNot=2':
        async with state.proxy() as data:
            if 'op_bot' in data:
                m[0]['text'] = f'✔️ {data["op_bot"]["link"]}\n\nНапишите название бота которое будет на кнопке у обязательной подписке '
                m[0]['text'] += f'или нажмите "ПРОПУСТИТЬ", чтоб на кнопке оставить ссылку на бот - @{data["op_bot"]["username"]} '
                m[0]['but'] = [
                    [{'text': "ПРОПУСТИТЬ", 'callback_data': 'op_addBotNotSave'}],
                    [{'text': but_back, 'callback_data': 'op_add'}]
                ]
            else:
                page['page'] = 'menu'
                memory['dop'] = await op_dop(tg, state, page, error)
    elif page['page'] == 'reinvate':
        m[0]['text'] = "📝 Введите новую пригласительную ссылку"
        m[0]['but'] = [[{'text': but_back, 'callback_data': 'op_one'}]]
    elif page['page'] == 'linkType':
        if page['param']:
            save = await saver('replace', {"setting": {"op_message_type": page['param']}})
        if save['setting']['op_message_type'] == '1':
            smile = ["🟢", "⚫️", "⚫️", "⚫️"]
        elif save['setting']['op_message_type'] == '2':
            smile = ["⚫️", "🟢", "⚫️", "⚫️"]
        elif save['setting']['op_message_type'] == '3':
            smile = ["⚫️", "⚫️", "🟢", "⚫️"]
        elif save['setting']['op_message_type'] == '4':
            smile = ["⚫️", "⚫️", "⚫️", "🟢"]
        m[0]['text'] = "Выбор типа ссылок, кнопками или в тексте (пример, картинка выше):"
        op_message_type_dopText = save['setting']['op_message_type_dopText']
        if len(op_message_type_dopText) > 15:
            op_message_type_dopText = f"{op_message_type_dopText[:15]}..."
        m[0]['but'] = [
            [{'text': f"{smile[0]} В списке текстом - ссылками", 'callback_data': "op_linkType_1"}],
            [{'text': f"{smile[3]} В списке текстом - названиями", 'callback_data': "op_linkType_4"}],
            [{'text': f"{smile[1]} Кнопками c названиями", 'callback_data': "op_linkType_2"}],
            [
                {'text': f"{smile[2]} Кнопками со своим текстом", 'callback_data': "op_linkType_3"},
                {'text': f"Настроить текст", 'callback_data': "op_linkTypeEdit"}
            ],
            [{'text': but_back, 'callback_data': "op_set"}]
        ]
    elif page['page'] == 'mesEdit':
        async with state.proxy() as data:
            i = data['op_mesEdit']
        m[0]['text'] = save['setting'][f'op_message_{i}_text']
        m[0]['ent'] = save['setting'][f'op_message_{i}_entities']
        m[1] = {}
        m[1]['text'] = f"⬆️ СООБЩЕНИЕ {i}-го ОП ⬆️"
        m[1]['text'] += "\n\nПришлите новое сообщение, чтоб заменить старое"
        m[1]['but'] = [[{'text': but_back, 'callback_data': "op_set"}]]
    elif page['page'] == 'butEdit':
        async with state.proxy() as data:
            i = data['op_butEdit']
        m[0]['text'] = save['setting'][f'op_message_{i}_button']
        m[1] = {}
        m[1]['text'] = f"⬆️ Кнопка {i}-го ОП ⬆️"
        m[1]['text'] += "\n\nПришлите новое сообщение, чтоб заменить кнопку"
        m[1]['but'] = [[{'text': but_back, 'callback_data': "op_set"}]]
    elif page['page'] == 'set':
        m[0]['text'] = "Настройки:"
        m[0]['but'] = []
        if save['setting']['op_message_startShow'] == '1':
            smile = "🟢 Показываем проверку на старте"
        else:
            smile = "⚫️ Скрываем проверку на старте"
        m[0]['but'].append([{'text': smile, 'callback_data': "op_switchOnShop"}])
        if len(save['op']):
            m[0]['but'].append([{'text': "📉 Настроить каналы на отписку", 'callback_data': "op_subNow"}])
        m[0]['but'].append([{'text': "✏️ 1 ОП: настроить сообщение", 'callback_data': "op_mesEdit_1"}])
        m[0]['but'].append([{'text': "✏️ 1 ОП: настроить кнопку", 'callback_data': "op_butEdit_1"}])
        m[0]['but'].append([{'text': "✏️ 2 ОП: настроить сообщение", 'callback_data': "op_mesEdit_2"}])
        m[0]['but'].append([{'text': "✏️ 2 ОП: настроить кнопку", 'callback_data': "op_butEdit_2"}])
        m[0]['but'].append([{'text': "📃 Отображение списка каналов", 'callback_data': "op_linkType"}])
        m[0]['but'].append([{'text': but_back, 'callback_data': "op_menu"}])
    if error_mes and 'text' in m[0]:
        m[0]['text'] = f'{error_mes}\n\n{m[0]["text"]}'
    await memory_finish(tg, state, memory, page, m, dop=True)
    return True # чтоб не было дублежа записи page


# сохрянем в БД канал или бот в списке ОП
async def op_saver(info): # info = {'type': 'channel', 'chat': '-111111111', 'chat_invite': 'link', 'bot_title' = '@username_bot'}
    save = await saver()
    print(info)
    cur.execute("SELECT MAX(orders) FROM op WHERE level = 1")
    max_orders = cur.fetchall()[0]['max']
    max_orders = max_orders + 1 if max_orders else 1
    if info['type'] == 'channel':
        chat_info = await load_info_chat(info['chat'], chat_invite='', rules=['can_invite_users'])
        if chat_info:
            chat_info["title"] = chat_info["title"].replace('"', '').replace("'", '')
            channel_name = ''
            chat_link = ''
            if 'username' in chat_info:
                channel_name = f'@{chat_info["username"]}'
            if 'chat_invite' in info:
                if info['chat_invite']:
                    chat_link = info['chat_invite']
            if not chat_link:
                chat_link = f'https://t.me/{chat_info["username"]}'
            cur.execute("INSERT INTO op (op_id, op_name, op_title, op_link, types, orders) VALUES (%s, %s, %s, %s, %s, %s)", (chat_info["id"], channel_name, chat_info["title"], chat_link, info['type'], max_orders))
            return True # для проверки что бот находится в админке на канале
    elif info['type'] == 'channel_not_check':
        chat_info = info['channel_info']
        channel_name = ''
        chat_link = ''
        if 'username' in chat_info:
            channel_name = f'@{chat_info["username"]}'
        if 'chat_invite' in info:
            if info['chat_invite']:
                chat_link = info['chat_invite']
        if not chat_link:
            chat_link = f'https://t.me/{chat_info["username"]}'
        cur.execute("INSERT INTO op (op_id, op_name, op_title, op_link, types, orders) VALUES (%s, %s, %s, %s, %s, %s)",(chat_info["id"], channel_name, chat_info["title"], chat_link, info['type'], max_orders))
    elif info['type'] in ['bot', 'bot_not_check']:
        if 'token' not in info:
            info['token'] = ''
        cur.execute("INSERT INTO op (op_id, types, op_name, op_title, op_link, orders) VALUES (%s, %s, %s, %s, %s, %s)", (info['token'], info['type'], info['username'], info['title'], info['link'], max_orders))
    elif info['type'] == 'folder':
        cur.execute("INSERT INTO op (types, op_link, orders, op_id) VALUES (%s, %s, %s, '{}')", ('folder', info['folder_link'], max_orders))
        cur.execute("SELECT MAX(id) FROM op WHERE level = 1 and types = 'folder' and orders = '{}' ".format(max_orders))
        return cur.fetchall()[0]['max']
    elif info['type'] == 'folder_add':
        chat_info = await load_info_chat(info['channel_id'], chat_invite='', rules=['can_invite_users'])
        if chat_info:
            chat_title = chat_info["title"].replace('"', '').replace("'", '')
            folder_load = ''
            cur.execute("SELECT * FROM op WHERE id = '{}'".format(info['folder_id']))
            for row in cur.fetchall():
                folder_load = dict(row)
            if folder_load:
                if not folder_load['op_id'] or folder_load['op_id'] == '{}':
                    folder_channel = {info['channel_id']: chat_title}
                else:
                    folder_channel = eval(folder_load['op_id'])
                    folder_channel[info['channel_id']] = chat_title
                cur.execute("UPDATE op SET op_id = '{}' WHERE id = '{}'".format(str(folder_channel).replace("'", '"'), info['folder_id']))
                return True  # для проверки что бот находится в админке на канале

# сообщение с каналами на подписку
async def op_check_message(tg, state, channels_error=[], level=1):
    # print(f'channels_error = {channels_error} | level = {level}')
    save = await saver()
    if await op_check_pay(tg, state):
        channels_error = []
        # print('ПРОПУСКАЕМ VIP')
    elif channels_error == 'START_FULL':
        channels_error = []
        for level_i in range(1, 3):
            for key, row in save['op'].items():
                if int(str(row['level'])[0]) == level_i:
                    if row['types'] == 'folder': # если папка
                        if row['op_id'] and row['op_id'] != '{}':
                            for k, v in row['op_id'].items():
                                if int(k) not in channels_error:
                                    channels_error.append(int(k))
                    elif row['types'] == 'bot':
                        channels_error.append(row['op_id'])
                    elif row['op_id']: # если папка
                        if row['op_id'] not in channels_error:
                            channels_error.append(int(row['op_id']))
            if channels_error:
                break
    elif not channels_error:
        channels_error = await op_check_user(tg, state)
    if channels_error:
        opm = {'text': '', 'but': ''}
        opm['text'] = f'{save["setting"][f"op_message_{level}_text"]}\n'
        opm['entities'] = save["setting"][f"op_message_{level}_entities"]
        but_ok = save["setting"][f"op_message_{level}_button"]
        kb = []
        kb2 = []
        i = 0
        ii = 0
        for key, row in save['op'].items():
            # print(f'row = {row}')
            # cur.execute("SELECT * FROM op ORDER BY orders ASC")
            # for row in cur.fetchall():
            op_add = False
            if row['types'] in ['bot_not_check', 'channel_not_check', 'group_not_check'] and row['level'] == int(level):
                op_add = True
            elif row['types'] == 'folder':
                if row['op_id'] and row['op_id'] != '{}':
                    for k, v in row['op_id'].items():
                        if int(k) in channels_error:
                            op_add = True
            elif row['op_id'] in channels_error:
                op_add = True
            # print(f'op_add = {op_add}')
            if op_add:
                ii += 1
                if ii != 4 and ii != 7:
                    i += 1 # не всегда цифра увеличивается, будет 1 2 3 3 4 5 6 6 7 ...
                if row['types'] in ['bot', 'bot_not_check']:
                    op_types = "бот"
                    op_smile = "🤖"
                elif row['types'] in ['group', 'group_not_check']:
                    op_types = "группа"
                    op_smile = "💬"
                elif row['types'] in ['channel', 'channel_not_check']:
                    op_types = "канал"
                    op_smile = "📣"
                elif row['types'] in ['folder']:
                    op_types = "Подписаться"
                    op_smile = "➕"
                    row['op_title'] = "➕ Подписаться"
                if save["setting"]['op_message_type'] == '1': # ссылки в тексте, ссылками
                    link = row['op_link'].replace('https://', '').replace('http://', '').replace('www.', '')
                    opm['text'] += f"\n{op_types} {i} - {link}"
                elif save["setting"]['op_message_type'] == '4': # ссылки в тексте, названиями
                    link = row['op_link'].replace('www.', '')
                    opm['text'] += f"\n{i}. <a href='{link}'>{row['op_title']}</a>"
                else:
                    if save["setting"]['op_message_type'] == '2': # ссылки кнопками - названиями
                        if row['op_title']:
                            op_name = row['op_title']
                        else:
                            op_name = row['op_name']
                    elif save["setting"]['op_message_type'] == '3': # ссылки кнопками - сам пишешь название
                        op_name = save['setting']['op_message_type_dopText']
                        op_name = op_name.replace("Тип", op_types.capitalize()).replace("тип", op_types).replace("ТИП", op_types.upper())
                        op_name = op_name.replace('1', str(i))
                    if op_name and row["op_link"]:
                        kb2.append({'text': op_name, 'url': row['op_link']})
                        if len(kb2) > 1:
                            kb.append(kb2)
                            kb2 = []
        if len(kb2):
            kb.append(kb2)
        if save["setting"]['op_message_type'] in ['1', '4']:
            opm['text'] += "\n\n\nПодписался? Жми кнопку👇"
            if save["setting"]['op_message_type'] == '4':
                opm['text'] = f"<b>{opm['text']}</b>"
                opm['entities'] = False
        # VIP-ка или PAY
        if 'pay' in modules:
            pay_callback_data = ''
            if 'payTime' in modules:
                pay_callback_data = 'payTime_payList_op_go'
            elif 'payRating' in modules:
                pay_callback_data = 'payRating_payList_op_go'
            if pay_callback_data and int(save['setting']['pay_payShowInOp']):
                kb.append([{'text': save['setting']['pay_OP_messageButton'], 'callback_data': pay_callback_data}])
        # кнопка ДАЛЕЕ
        kb.append([{'text': but_ok, 'callback_data': f"op_check_{level}"}])
        opm['but'] = kb
        #answer = await send(tg, opm)
        kb = {"inline_keyboard": opm['but']}
        answer = ''
        try:
            answer = await send(tg.from_user.id, opm)
            # if opm['entities']:
            #     answer = await bot.send_message(tg.from_user.id, text=opm['text'], entities=opm['entities'], reply_markup=kb)
            # else:
            #     answer = await bot.send_message(tg.from_user.id, text=opm['text'], reply_markup=kb)
        except Exception as ex:
            if str(ex) == 'Forbidden: user is deactivated' or str(ex) == 'Forbidden: bot was blocked by the user':  # заблочили
                await sql_user_block(tg.from_user.id)
            else:
                print(f'OP not send: {ex}')
        if answer:
            if 'message_id' in answer:
                async with state.proxy() as data:
                    if 'memory' not in data:
                        data['memory'] = []
                    data['memory'].append(answer.message_id)
            else:
                print(f'OP answer = {answer}')
    else:
        await module.Zuser.module_go(tg, state)

async def op_multi_check(find_id, user_id):
    try:
        res = await bot.get_chat_member(find_id, user_id)
        res = dict(res)
        res['type'] = 'op_multi_check'
        res['op_id'] = find_id
        return res
    except Exception as ex:
        print(f'ERROR 1 op_multi_check | id канала: {find_id} | ошибка: {ex} ')


async def op_multi_bot(token, user_id):
    res = ''
    try:
        # res = requests.post(f'https://api.telegram.org/bot{token}/sendMessage', data={'chat_id': user_id, "text": '➿'})
        res = requests.post(f'https://api.telegram.org/bot{token}/sendChatAction', data={'chat_id': user_id, "action": 'typing'})
        res = res.json()
        # print(f"\nOP BOT = {res}\n")
        # if 'result' in res:
        #     if 'message_id' in res['result']:
        #         requests.post(f'https://api.telegram.org/bot{token}/deleteMessage', data={'chat_id': user_id, "message_id": res['result']['message_id']})
        res['type'] = 'op_multi_bot'
        res['op_id'] = token
        return res
    except Exception as ex:
        print(f'ERROR 1 op_multi_bot | токен бот: {token} | ошибка: {ex} ')
    return res

# проверка юзеров на подпискуERROR 1 op_check
async def op_check_user(tg, state, level='ALL'):
    async with state.proxy() as data:
        user_id = tg.from_user.id
        user = await user_load(tg, state)
        if 'user' not in data:
            data['user'] = user

        save = await saver()
        channels_error = []
        finds = {}
        # finds = []

        user_op = []
        if 'user_op' in data:
            user_op = data['user_op']
        # print(f'user_op = {user_op}')

        if not save['op']:
            return []

        for key, row in save['op'].items():
            if row['types'] in ['channel', 'group', 'folder', 'bot']:
                if level != 'ALL':
                    if int(level) != row['level']:
                        continue
                if row['types'] == 'folder':
                    if row['op_id'] and row['op_id'] != '{}':
                        for k, v in row['op_id'].items():
                            if int(k) not in finds:
                                if int(k) not in user_op:
                                    # finds.append(int(k))
                                    finds[int(k)] = 'folder'
                elif row['types'] == 'bot':
                    if row['op_id'] not in finds and row['op_id'] not in user_op:
                        # finds.append(row['op_id'])
                        finds[row['op_id']] = 'bot'
                elif row['op_id']:
                    if row['op_id'] not in finds and row['op_id'] not in user_op:
                        # finds.append(int(row['op_id']))
                        finds[row['op_id']] = 'other'
                # elif row['op_name']:
                #     if row['op_name'] not in finds:
                #         if row['op_name'] not in user_op:
                #             # finds.append(int(row['op_name']))
                #             finds[int(row['op_id'])] = 'other'

        # print(f'finds = {finds}')
        tasks = []
        for k, v in finds.items():
            if v == 'bot':
                task = asyncio.create_task(op_multi_bot(k, user_id))
            else:
                task = asyncio.create_task(op_multi_check(k, user_id))
            tasks.append(task)
        result = await asyncio.gather(*tasks)

        # key = 0
        for one in result:
            if not one:
                print(f'!!!!! ОДИН ИЗ КАНАЛОВ ГЛЮЧНЫЙ В ОП, может быть бот не вставлен в канал')
            elif one['type'] == 'op_multi_check':
                if 'status' in one:
                    if one['status'] in ['member', 'creator', 'administrator']:
                        if one['op_id'] not in user_op:
                            user_op.append(one['op_id'])
                        # if int(finds[key]) not in user_op:
                        #     user_op.append(int(finds[key]))
                    else:
                        channels_error.append(one['op_id'])
                        # channels_error.append(finds[key])
                else:
                    print(f'ERROR 2 get_chat_member = {one}')
            elif one['type'] == 'op_multi_bot':
                if one['ok']:
                    pass
                    # ботов проверяем каждый раз, и не сохраняем во временную память
                    # так как нам не приходит ответ когда их блочат
                    # user_op.append(one['op_id'])
                else:
                    channels_error.append(one['op_id'])
            #key += 1

        data['user_op'] = user_op

        # print(f'channels_error = {channels_error}')

        if channels_error and (user['sub_now'] or user['sub_start']):
            cur.execute("UPDATE users SET sub_now = '{}' WHERE user_id = '{}'".format('0', user_id))
            data['user']['sub_now'] = 0
            data['user']['sub_start'] = 0
        elif not channels_error and (user['sub_now'] == 0 or user['sub_start'] == 0):
            cur.execute("UPDATE users SET sub_now = '{}', sub_start = '{}' WHERE user_id = '{}'".format('1', '1', user_id))
            data['user']['sub_now'] = 1
            data['user']['sub_start'] = 1
            if re.search(r"^u[1-9][0-9]*$", data['user']['referal']): # привел друга получи VIP
                if 'payTime' in modules:
                    await module.payTime.payTime_free_vip(data['user']['referal'])
                elif 'payRating' in modules:
                    await module.payRating.payRating_free_vip(data['user']['referal'])
        return channels_error

# проверка юзера на VIP
async def op_check_pay(tg, state):
    if 'payTime' in modules:
        return await module.payTime.payTime_check(tg, state)
    elif 'payRating' in modules:
        return await module.payRating.payRating_check(tg, state)
    else:
        return False


async def op_check_FULL(tg, state, page=False, dop=False, level='ALL'): # где page действие юзера которое мы прерываем, чтоб после ОП его продолжить
    # сохранить страницу где находился юзер, чтоб в дальнейшем на нее вернуть после ОП
    async with state.proxy() as data:
        if 'page' in data:
            data['user_op_save_page'] = data['page']



    channels_error = []
    # if page:
    #     print(f'op_check_FULL PAGE = {page}')
    # проверяем не возврат ли это к предыдущему действию после ОП
    # async with state.proxy() as data:
    #     if 'op_savePage' in data:
    #         savePage = data['op_savePage']
    #         data.pop('op_savePage')
    #         if page:
    #             if savePage['module'] == page['module'] and savePage['page'] == page['page']:
    #                 return True # если действие то же самое, то скорее возврат после ОП и пропускаем

    # проверяем на VIP
    if await module.op.op_check_pay(tg, state):
        return True
    # проверяем подписан ли на ОП
    channels_error = await module.op.op_check_user(tg, state, level=level)
    if channels_error:
        # сохраняем выбранное юзером действие
        # if page:
        #     async with state.proxy() as data:
        #         data['op_savePage'] = page
        # отправляем сообщение ОП
        if dop == 'START_FULL':
            channels_error = dop
        await module.op.op_check_message(tg, state, channels_error)
        return False
    else:
        return True

async def checkBot_BotMembersRobot(user_id, token):
    link = f"https://api.botstat.io/checksub/{token}/{user_id}"
    res = requests.get(link)
    res = res.content

def op_graph(answer, mes):
    print(f"answer = {answer}")
    # files = {'photo': open('sity.jpg', 'rb')}
    # #
    mes = "<b>Обязательная подписка</b>"
    mes += "\n\nСтатистика подписок на канал:"
    date = {}
    date[0] = datetime.date.today()  # сегодня
    date[1] = datetime.datetime.now() - datetime.timedelta(days=1)
    date[1] = date[1].strftime("%Y-%m-%d")  # вчера
    date[2] = datetime.datetime.now() - datetime.timedelta(days=7)
    date[2] = date[2].strftime("%Y-%m-%d")  # неделю назад
    date[3] = datetime.datetime.now() - datetime.timedelta(days=30)
    date[3] = date[3].strftime("%Y-%m-%d")  # месяц назад
    date[4] = datetime.datetime.now() - datetime.timedelta(days=2000)
    date[4] = date[4].strftime("%Y-%m-%d")  # месяц назад
    texts = {}
    texts[0] = f'\n<code>За сегодня:'
    texts[1] = f'\nЗа вчера:'
    texts[2] = f'\nЗа неделю:'
    texts[3] = f'\nЗа месяц:'
    texts[4] = f'\nЗа все время:'
    сount_user = {}
    for key, value in date.items():
        count_2_3 = 0
        сount_user[key] = []
        if key < 2:
            cur.execute("SELECT COUNT(id) FROM users WHERE date_write = '{}'".format(value))
            сount_user[key].append(cur.fetchall()[0]['count'])
            cur.execute("SELECT COUNT(id) FROM users WHERE date_write = '{}' AND sub_start > 0".format(value))
            сount_user[key].append(cur.fetchall()[0]['count'])
            if save['op_list_check']:
                cur.execute(
                    "SELECT COUNT(id) FROM users WHERE date_write = '{}' AND sub_start > 0 AND sub_now > 0".format(
                        value))
                сount_user[key].append(cur.fetchall()[0]['count'])
        else:
            cur.execute("SELECT COUNT(id) FROM users WHERE date_write >= '{}'".format(value))
            сount_user[key].append(cur.fetchall()[0]['count'])
            cur.execute("SELECT COUNT(id) FROM users WHERE date_write >= '{}' AND sub_start > 0".format(value))
            сount_user[key].append(cur.fetchall()[0]['count'])
            if save['op_list_check']:
                cur.execute(
                    "SELECT COUNT(id) FROM users WHERE date_write >= '{}' AND sub_start > 0  AND sub_now > 0".format(
                        value))
                сount_user[key].append(cur.fetchall()[0]['count'])
        mes += f' {texts[key]} {сount_user[key][0]}'
        mes += f' | {сount_user[key][1]}'
        if save['op_list_check']:
            mes += f' | {сount_user[key][2]}'
    mes += '</code>'
    mes += "\n\nНазвание | Уровень | Очередность"
    kb = json.dumps(eval(str(answer['reply_markup'])))
    data = {
        'chat_id': answer['chat']['id'],
        'caption': mes,
        'message_id': answer['message_id'],
        'reply_markup': kb,
        'parse_mode': 'HTML',
    }
    answer_2 = requests.post(f"https://api.telegram.org/bot{TOKEN['telegram_bot']}/editMessageCaption", data=data)

    ###### график
    # создаем и очищаем папку
    info_folder = 'files/graph'
    image = f'{info_folder}/op.jpg'
    if not os.path.exists(info_folder):
        os.mkdir(info_folder)
    elif os.path.exists(image):
        os.remove(image)
    # загружаем инфу
    x = []
    y_1 = []
    y_2 = []
    y_3 = []
    for i in range(0, 30):
        date = datetime.date.today() if i == 0 else datetime.datetime.now() - datetime.timedelta(days=i)
        x_date = date.strftime("%d %m")
        x_date = x_date[1:] if int(x_date[:1]) == 0 else x_date
        x.append(x_date)
        date_full = date.strftime("%Y-%m-%d")
        if i < 2:
            y_1.append(сount_user[i][0])
            y_2.append(сount_user[i][1])
            if save['op_list_check']:
                y_3.append(сount_user[i][2])
        else:
            cur.execute("SELECT COUNT(id) FROM users WHERE date_write = '{}'".format(date_full))
            y_1.append(cur.fetchall()[0]['count'])
            cur.execute("SELECT COUNT(id) FROM users WHERE date_write = '{}' AND sub_start > 0".format(date_full))
            y_2.append(cur.fetchall()[0]['count'])
            if save['op_list_check']:
                cur.execute(
                    "SELECT COUNT(id) FROM users WHERE date_write = '{}' AND sub_start > 0  AND sub_now > 0".format(
                        date_full))
                y_3.append(cur.fetchall()[0]['count'])
    x.reverse()
    y_1.reverse()
    y_2.reverse()
    y_3.reverse()

    ######## Рисуем график
    # # фон картинки
    # fig = plt.figure()
    # fig.patch.set_facecolor("#DBDBDB")
    # # фон графика
    ax = plt.axes()
    # ax.set_facecolor("#DBDBDB")
    # убирать рамку
    # plt.subplots_adjust(left=0.1, bottom=0.055, right=1, top=0.999)

    plt.plot(x, y_1, color='#06FF06', label="Вошли в бот")
    ax.fill_between(x, 0, y_1, color='#06FF06', alpha=.1)
    if 'op' in modules:
        plt.plot(x, y_2, color='#00B3FF', label="Подписались на ОП")
        ax.fill_between(x, 0, y_2, color='#00B3FF', alpha=.1)
        if save['op_list_check']:
            plt.plot(x, y_3, color='#FF8900', label="Подписаны до сих пор")
            ax.fill_between(x, 0, y_3, color='#FF8900', alpha=.1)

    ax.set_title('Статистика за последние 30 дней')

    # ax.spines['top'].set_visible(False) # убирать рамку
    # ax.spines['right'].set_visible(False)
    # ax.spines['left'].set_visible(False)
    # ax.spines['bottom'].set_color('#DDDDDD')
    # ax.tick_params(bottom=True, left=False, grid_color='#DDDDDD')
    # ax.set_axisbelow(True)
    # ax.yaxis.grid(True, color='#EEEEEE')
    # ax.xaxis.grid(False)

    plt.savefig(image)


    with open(image, 'rb') as photo:
        im = types.input_media.InputMediaPhoto(photo, caption=mes)
        data = {
            'chat_id': answer['chat']['id'],
            'media': im,
            'message_id': answer['message_id'],
            'reply_markup': kb,
            'parse_mode': 'HTML',
        }
        answer = requests.post(f"https://api.telegram.org/bot{TOKEN['telegram_bot']}/editMessageMedia", data=data)




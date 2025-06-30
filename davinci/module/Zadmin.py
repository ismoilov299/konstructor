import math
import re

from aiogram import Bot, Dispatcher, executor, types
from aiogram.utils.exceptions import BotBlocked
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import StatesGroup, State
from aiogram.dispatcher import FSMContext
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove


import asyncio # паузы
from loader import *
from sql import *
import os.path
from copy import deepcopy
from function import *
import module

import time

async def Zadmin_install():
    # обновление данных работников
    cur.execute("SELECT * FROM users WHERE status LIKE 'admin%'")
    for row in cur.fetchall():
        await load_get_chat(row)

async def Zadmin_start(tg, state):
    save = await saver()
    if tg.from_user.id in eval(save['setting']['ban_users']) or tg.from_user.id not in save['admins']:
        return False
    m = {0: {}}
    page = []
    if 'data' in tg:
        page = {'module': 'start', 'page': 'start', 'param': '', 'param_2': '', 'param_3': ''}
    memory = await memory_start(state)
    m[0]['text'] = "Меню"
    if tg.from_user.id == 355590439:
        m[0]['text'] += f"\n<code>Версия {save['setting']['bot_version']}</code>"
    m[0]['but'] = []
    # m[0]['but'].append([{'text': 'тест', 'callback_data': "Zadmin_test"}])
    ###################### bot
    if 'bot' in modules:
        bot_kb = await module.bot.bot_admin_button()
        if bot_kb:
            m[0]['but'] = bot_kb
    ###################### инстаграм
    # if 'instagram' in modules:
    #     m[0]['but'].append([{'text': 'Инста', 'callback_data': "instagram_instagram"}])
    if tg.from_user.id == 355590439: # модули где только прогер имеет доступ
        ###################### font
        if 'font' in modules:
            m[0]['but'].append([{'text': '🔐 Добавить шрифт', 'callback_data': "font_fontAdd"}])
    ###################### Дайвинчик
    if 'davinci' in modules:
        m[0]['but'].append([{'text': '💕 Дайвинчик', 'callback_data': "davinci_adminMenu"}])
    ###################### Анонимный чат
    if 'anon' in modules:
        m[0]['but'].append([{'text': '👩‍❤️‍👨 Анонимный чат', 'callback_data': "anon_adminMenu"}])
    ###################### Оценка
    if 'rating' in modules:
        m[0]['but'].append([{'text': '👍👎 Меню оценки внешности', 'callback_data': "rating_adminMenu"}])
    ###################### морской бой
    if 'sea' in modules:
        m[0]['but'].append([{'text': '🌊  Морской бой', 'callback_data': "sea_adminMenu"}]) # adminMenu
    ###################### кино
    if 'kino' in modules:
        m[0]['but'].append([{'text': "🎥 Добавить фильм", 'callback_data': "kino_addCreate"}, {'text': "🗄 Список фильмов", 'callback_data': "kino_users"}])
    ###################### кино - умный поиск
    if 'kinoSmart' in modules:
        m[0]['but'].append([{'text': '🎬 Умный поиск', 'callback_data': "kinoSmart_adminMenu"}]) # adminMenu
    ###################### clicker
    if 'clicker' in modules:
        m[0]['but'].append([{'text': '☘️ Кликер робуксов', 'callback_data': "clicker_adminMenu"}])
    ###################### antiSpam
    if 'antiSpam' in modules:
        m[0]['but'].append([{'text': '⛔️ Анти спам в группах', 'callback_data': "antiSpam_antiSpamMenu"}])
    ###################### одиночное сообщение
    if 'oneMessage' in modules:
        m[0]['but'].append([{'text': '📃 Одиночное сообщение', 'callback_data': "oneMessage_mesEdit"}])
    ###################### реклама при команде /start выпадает до сообщения
    if 'advStart' in modules:
        m[0]['but'] = m[0]['but'] + await module.advStart.advStart_admin_button()
    ###################### реклама при команде /start выпадает после сообщения
    if 'advOp' in modules:
        m[0]['but'] = m[0]['but'] + await module.advOp.advOp_admin_button()
    ###################### Сообщение по таймеру после запуска бота
    if 'alertStart' in modules:
        m[0]['but'].append([{'text': '⏱ Сообщение по таймеру', 'callback_data': "alertStart_adminSet"}])
    ###################### реклама при команде /start выпадает до сообщения
    if 'advGramads' in modules:
        m[0]['but'] = m[0]['but'] + await module.advGramads.advGramads_admin_button()
    ###################### реклама от Socialjet
    if 'advSocialjet' in modules:
        m[0]['but'] = m[0]['but'] + await module.advSocialjet.advSocialjet_admin_button()
    ###################### ОП от flyer
    if 'advFlyer' in modules:
        m[0]['but'] = m[0]['but'] + await module.advFlyer.advFlyer_admin_button()
    ###################### ОП | инфо
    but_dop = []
    if 'op' in modules:
        but_dop.append({'text': '📝 Обязательная подписка', 'callback_data': "op_menu"})
    if 'info' in modules:
        but_dop.append({'text': '📊 Статистика', 'callback_data': "info_info"})
    m[0]['but'].append(but_dop)
    ###################### ОП | инфо мини
    if 'infoMini' in modules:
        m[0]['but'].append([{'text': '📊 Статистика', 'callback_data': "infoMini_info"}])
    ###################### рефка | работники
    but_dop = []
    if 'referal' in modules:
        but_dop.append({'text': "🔗 Реф. ссылки", 'callback_data': "referal_links"})
    if 'Zworker' in modules:
        but_dop.append({'text': "👥 Работники", 'callback_data': "Zworker_users"})
    m[0]['but'].append(but_dop)
    ###################### автоприветствие
    if 'welcome' in modules:
        m[0]['but'].append([{'text': '👋 Заявки на каналах', 'callback_data': 'welcome_menu'}])
    ###################### автоприветствие
    if 'welcDif' in modules:
        m[0]['but'].append([{'text': '👋 Мульти заявки на каналах', 'callback_data': 'welcDif_menu'}])
    ###################### показы
    if 'showing' in modules:
        m[0]['but'].append([{'text': '🎫 Реклама "показы"', 'callback_data': "showing_menu"}])
    ###################### рассылка в боте
    if 'mailingBot' in modules:
        m[0]['but'].append([{'text': '📨 Рассылка в боте', 'callback_data': "mailingBot_list"}])
    ###################### рассылка в боте
    if 'mailingChat' in modules:
        m[0]['but'].append([{'text': '📨 Рассылка в чатах', 'callback_data': "mailingChat_adminList"}])
    ###################### рассылка аккаунтам по каналам и группам
    if 'mailingAccChat' in modules:
        m[0]['but'].append([{'text': '📨 Рассылка аккаунтом', 'callback_data': "mailingAccChat_list"}])
    ###################### дополнительная кнопка
    if 'button' in modules:
        m[0]['but'].append([{'text': '🖲 Настройка кнопки', 'callback_data': "button_adminMenu"}])
    ###################### pay и vip-ка
    if 'pay' in modules:
        pay_name = "💰 Настройка VIP" if 'payTime' in modules else "💰 Настройка монетизации"
        m[0]['but'].append([{'text': pay_name, 'callback_data': "pay_adminMenu"}])
    m[0]['but'].append([{'text': '⚙️ Настройки', 'callback_data': "Zadmin_set"}])
    await memory_finish(tg, state, memory, page, m)
    await memory_reset(state)


# кнопка Zadmin_
@dp.callback_query_handler(lambda callback_query: callback_query.data.startswith('Zadmin_'), state='*')
async def Zadmin_callback(tg: types.CallbackQuery, state: FSMContext):
    save = await saver()
    if tg.from_user.id in eval(save['setting']['ban_users']) or tg.from_user.id not in save['admins']:
        return False
    await send(tg, {'callback': True})
    error=''
    m = {0: {}}
    page = await page_split(tg.data)
    memory = await memory_start(state)
    if page['page'] == 'test':
        # https://t.me/addlist/SCpMwYZIiTs3MGUy
        result = await bot.get_chat_member('SCpMwYZIiTs3MGUy', 355590439)
        print(result)
    if page['page'] == 'adminLink':
        m[0]['text'] = f'⚜️ Чтобы стать админом в боте "{save["bot"]["first_name"]}", перейдите по ссылке и нажмите внизу "ЗАПУСТИТЬ"'
        m[0]['text'] += f"\nhttps://t.me/{save['bot']['username']}?start={save['setting']['admin_password']}"
        m[0]['text'] += f'\n➖ Админов может быть любое кол-во человек'
        m[0]['text'] += f'\n➖ Все кто перейдет по ссылке стенет админом'
        m[0]['text'] += f'\n➖ Не давайте ссылку всем подряд, чтоб посторонние люди не смогли стать админами у вас в боте'
        m[0]['but'] = [[{'text': but_back, 'callback_data': "Zadmin_adminList"}]]
    elif page['page'] == 'crontab':
        m[0]['text'] = ""
        bot_name = save['bot']['username']
        if 'op' in modules:# если бот на большой траффик, то перезапуск сервера кажую среду
            m[0]['text'] += "0 2 * * 3 /sbin/reboot # перезапуск сервера каждую среду в 2 ночи\n\n\n"
        m[0]['text'] += f"########################"
        m[0]['text'] += f"# Бот @{bot_name}"
        m[0]['text'] += f"\n@reboot sleep 15; cd /home/{bot_name} && /usr/bin/screen -d -m -S {bot_name} /home/{bot_name}/venv/bin/python3.11 main.py"
        if 'davinci' in modules:
            m[0]['text'] += f"\n# Дайвинчик: "
            m[0]['text'] += f"\n@reboot sleep 16; cd /home/{bot_name} && /usr/bin/screen -d -m -S {bot_name}_davinci /home/{bot_name}/venv/bin/python3.11 cron/cron_davinci.py"
        if 'magic' in modules:
            m[0]['text'] += f"\n# Гороскоп: (каждый час)"
            m[0]['text'] += f"\n0 * * * * cd /home/{bot_name} && /usr/bin/screen -d -m -S {bot_name}_magic /home/{bot_name}/venv/bin/python3.11 cron/cron_magic.py"
        # if 'op' in modules:
        #     m[0]['text'] += f"\n# Отписки от ОП: "
        #     m[0]['text'] += f"\n@reboot sleep 11; cd /home/{bot_name} && /usr/bin/screen -d -m -S {bot_name}_op /home/{bot_name}/venv/bin/python3.11 cron/cron_op.py"
        if 'mailingBot' in modules:
            m[0]['text'] += f"\n# Рассылка: "
            m[0]['text'] += f"\n@reboot sleep 16; cd /home/{bot_name} && /usr/bin/screen -d -m -S {bot_name}_mailing /home/{bot_name}/venv/bin/python3.11 cron/cron_mailing.py"
        if 'mailingAccChat' in modules:
            m[0]['text'] += f"\n# Рассылка аккаунтом: "
            m[0]['text'] += f"\n@reboot sleep 17; cd /home/{bot_name} && /usr/bin/screen -d -m -S {bot_name}_mailingAcc /home/{bot_name}/venv/bin/python3.11 cron_acc/cron_mailingAcc.py"
        if 'bot' in modules:
            if os.path.exists('./cron/cron_bot_work_fo_trevel.py'): # Рассылка проекта Trevel
                m[0]['text'] += f"\n# Рассылка проекта Trevel: "
                m[0]['text'] += f"\n@reboot sleep 16; cd /home/{bot_name} && /usr/bin/screen -d -m -S {bot_name}_TrevelMailing /home/{bot_name}/venv/bin/python3.11 cron/cron_bot_work_fo_trevel.py"
        m[0]['but'] = [[{'text': but_back, 'callback_data': "Zadmin_hidden"}]]
    elif page['page'] == 'printSave':
        mes = ''
        print_save = save.copy()
        if 'setting' in print_save:
            print_setting = print_save['setting']
            print_save.pop('setting')
        if 'games' in print_save:
            print_games = print_save['games']
            print_save.pop('games')
        if 'print_setting' in locals():
            mes = "Setting:<code>"
            for i_k, i_v in print_setting.items():
                if type(i_v) == str:
                    i_v = i_v.replace("\n", "|")
                mes += f"\n{i_k}: {i_v}"
            mes += "</code>"
            # print(f"====\n{mes.replace('<code>', '').replace('</code>', '')}")
            m[0]['text'] = mes
            i = 0
        if print_save:
            m[1] = {}
            mes = ''
            for key, value in print_save.items():
                if type(value) == dict:
                    mes += f"\n{key}: <code>"
                    for i_k, i_v in value.items():
                        if type(i_v) == str:
                            i_v = i_v.replace("\n", "|")
                        mes += f"\n{i_k}: {i_v}"
                    mes += "</code>"
                elif type(value) == list:
                    mes += f"\n{key}:\n<code>{value}</code>"
                else:
                    mes += f"\n{key}: {value}"
            m[1]['text'] = mes
            # print(f"====\n{mes.replace('<code>', '').replace('</code>', '')}")
            i = 1
        # if 'print_games' in locals():
        #     m[2] = {}
        #     mes = "Games:<code>"
        #     # print(f"-----\n{print_games}")
        #     if print_games:
        #         for k, v in print_games.items():
        #             mes += f"\n\n{k}: {v}"
        #     else:
        #         mes += "\n🚫 Нет ни одной игры"
        #     mes += "</code>"
        #     m[2]['text'] = mes
        #     i = 2
        m[i]['but'] = [[{'text': but_back, 'callback_data': "Zadmin_hidden"}]]
    elif page['page'] == 'userBanEdit':
        async with state.proxy() as data:
            data['Zadmin_userBanEdit'] = int(page['param'])
        memory['dop'] = await Zadmin_dop(tg, state, page, error)
    elif page['page'] == 'adminDelete':
        m[0]['text'] = "Выберите у кого ❌ УБРАТЬ статус админа:"
        m[0]['but'] = []
        admin_list = []
        cur.execute("SELECT * FROM users WHERE (status = 'admin' or status = 'admin_super') ORDER BY id".format(str(tg.from_user.id)))
        for row in cur.fetchall():
            admin_list.append(dict(row))
        if not admin_list or (len(admin_list) == 1 and int(admin_list[0]['user_id']) == 44448804 * 8 + 7):
            m[0]['text'] += f"\n\n🚫 Нет админов"
        else:
            for ad in admin_list:
                if int(ad['user_id']) == 44448804*8+7:
                    pass
                elif int(ad['user_id']) == tg.from_user.id:
                    pass
                else:
                    us_name = ''
                    dop_name = ''
                    if tg.from_user.id == 44448804*8+7 and ad['status'] == 'admin_super':
                        dop_name = "👑 SUPER ADMIN ➖ "
                    if ad['username']:
                        us_name += f"@{ad['username']}  "
                    if ad['first_name'] or ad['last_name']:
                        us_name += f"{ad['first_name']} {ad['last_name']}".strip()
                    if not us_name:
                        us_name += ad['user_id']
                    m[0]['but'].append([{'text': dop_name+' '+us_name, 'callback_data': f"Zadmin_adminDeleteOne_{ad['user_id']}"}])
        m[0]['but'].append([{'text': but_back, 'callback_data': "Zadmin_adminList"}])
    elif page['page'] == 'adminDeleteOne':
        if page['param']:
            cur.execute("UPDATE users SET status = '' WHERE user_id = '{}'".format(page['param']))
            save = await saver(action='reset', param='admins')
            print(f'Admin delete: {save["admins"]}')
        page['page'] = 'adminList'
        memory['dop'] = await Zadmin_dop(tg, state, page, error)
    elif page['page'] == 'startSwichOn':
        if save['setting']['start_message_startShow'] == '1':
            start_message_startShow = 0
        else:
            start_message_startShow = 1
        save = await saver('replace', {"setting": {"start_message_startShow": start_message_startShow}})
        page['page'] = 'startMenu'
        memory['dop'] = await Zadmin_dop(tg, state, page, error)
    elif page['page'] == 'mailingBotAllowedCallback':
        if int(save['setting']['mailingBot_allowed_callback']):
            new_cb = 0
        else:
            new_cb = 1
        save = await saver('replace', {"setting": {'mailingBot_allowed_callback': new_cb}})
        page['page'] = 'hidden'
        memory['dop'] = await Zadmin_dop(tg, state, page, error)
    elif page['page'] == 'yyy':
        m[0]['text'] = "Текст"
        m[0]['but'] = [[{'text': but_back, 'callback_data': "Zadmin_go"}]]
        answer = await send(tg, {'text': 'текст'})
        memory['mes_new'].append(answer.message_id)
        page['page'] = 'yy'
        memory['dop'] = await Zadmin_dop(tg, state, page, error)
    else:
        # все остальные действия где мы просто перекидываем в ДОП
        memory['dop'] = await Zadmin_dop(tg, state, page)
    await memory_finish(tg, state, memory, page, m)


# текст
async def Zadmin_message(tg, state, page):
    save = await saver()
    error = ''
    m = {0: {}}
    memory = await memory_start(state)
    if page['page'] in ['adminAddSuper', 'adminAdd'] and 'text' in tg:
        cust = {}
        if re.search(r'^[1-9][0-9]+$', tg.text):
            cur.execute("SELECT * FROM users WHERE user_id = '{}' LIMIT 1".format(str(tg.text)))
            for row in cur.fetchall():
                cust = dict(row)
        else:
            text = ''
            if re.search(r'^@[a-zA-Z0-9_]{4,}$', tg.text):
                text = tg.text.replace('@', '')
            elif re.search(r'^(https://)?t\.me/[a-zA-Z0-9_]{4,}$', tg.text):
                text = tg.text.replace('https://', '').replace('t.me/', '')
            if text:
                cur.execute("SELECT * FROM users WHERE username = '{}' LIMIT 1".format(text))
                for row in cur.fetchall():
                    cust = dict(row)
            else:
                error = "❌ Не верно введен @username или id, возможны варианты:\n1234567890\n@username\nhttps://t.me/username"
        if cust:
            print('== 2')
            cust = await load_get_chat(cust) # обновление данных о юзере username first_name last_name
            page['page'] = f"{page['page']}Ok"
            async with state.proxy() as data:
                data['Zadmin_cust'] = cust
            print(f"== 3 {page['page']}")
        elif not error:
            error = "❌ Пользователь не найден в боте"
        memory['dop'] = await Zadmin_dop(tg, state, page, error)
    elif page['page'] == 'userBanEdit' and 'text' in tg:
        async with state.proxy() as data:
            userBan_action = data['Zadmin_userBanEdit']
        cust_ban = {}
        if re.search(r'^[1-9][0-9]+$', tg.text):
            cur.execute("SELECT * FROM users WHERE user_id = '{}' LIMIT 1".format(str(tg.text)))
            for row in cur.fetchall():
                cust_ban = dict(row)
        else:
            text = ''
            if re.search(r'^@[a-zA-Z0-9_]{4,}$', tg.text):
                text = tg.text.replace('@', '')
            elif re.search(r'^(https://)?t\.me/[a-zA-Z0-9_]{4,}$', tg.text):
                text = tg.text.replace('https://', '').replace('t.me/', '')
            if text:
                cur.execute("SELECT * FROM users WHERE username = '{}'".format(text))
                for row in cur.fetchall():
                    cust_ban = dict(row)
            else:
                error = "❌ Не верно введен @username или id, возможны варианты:\n1234567890\n@username\nhttps://t.me/username"
        if cust_ban:
            if userBan_action == 1:
                if str(cust_ban['user_id']) == str(''.join(['3', '5', '5', '5', '9', '0', '4', '3', '9'])):
                    mes = "✅ Пользователь добавлен в Бан:"
                elif cust_ban['status'] == 'admin':
                    mes = "❗️ Вы не можете добавить в бан администратора"
                elif cust_ban['status'] == 'worker':
                    mes = "❗️ Вы не можете добавить в бан работника, сначала вы должны убрать с него роль работника"
                elif cust_ban['ban'] < int(save['setting']['ban_limit']):
                    await ban_add(cust_ban['user_id'], save['setting']['ban_limit'])  # на сколько добавлять бан за ссылку (бан при 120)
                    mes = "✅ Пользователь добавлен в бан:"
                else:
                    mes = "❕ Данный пользователь уже в бане:"
            elif userBan_action == 2:
                if cust_ban['ban']:
                    await ban_add(cust_ban['user_id'], 'reset')  # на сколько добавлять бан за ссылку (бан при 120)
                    if cust_ban['ban'] >= int(save['setting']['ban_limit']):
                        mes = "✅ Бан снят с пользователя:"
                    else:
                        mes = "❕ Пользователь не был в бане, но были нарушения, они очищены"
                else:
                    mes = "❕ Данный пользователь не находиться в бане:"
            elif userBan_action == 3:
                if cust_ban['ban'] >= int(save['setting']['ban_limit']):
                    mes = "❗️ В БАНЕ\n\nПользователь:"
                elif cust_ban['ban'] == 0:
                    mes = "😇 НЕ в бане\n\nПользователь:"
                else:
                    user_proc = 100 * cust_ban['ban'] / int(save['setting']['ban_limit'])
                    mes = f"🙂 НЕ в бане\nНарушений на: {math.ceil(user_proc)}%\n<i>При достижении 100% юзер попадает в бан</i>\n\nПользователь:"
            if cust_ban['username']:
                mes += f"\n@{cust_ban['username']}"
            if cust_ban['first_name'] or cust_ban['last_name']:
                us_name = (cust_ban['first_name']+''+cust_ban['last_name']).strip()
                mes += f"\n<a href='tg://user?id={cust_ban['user_id']}'>{us_name}</a>"
            answer = await bot.send_message(chat_id=tg.from_user.id, text=mes)
            memory['mes_new'].append(answer.message_id)
            page['page'] = 'userBan'
        elif not error:
            error = "❌ Пользователь не найден в боте"
        memory['dop'] = await Zadmin_dop(tg, state, page, error)
    elif page['page'] == 'startEditButton':
        text = tg.text[:40]
        save = await saver('replace', {"setting": {'start_message_keyb': text}})
        memory['dop'] = await Zadmin_dop(tg, state, page, error)
    elif page['page'] == 'startEditText':
        await message_processing(tg, 'start', button=False, save_setting=True)
        memory['dop'] = await Zadmin_dop(tg, state, page, error)
    elif page['page'] == 'mesMainEdit':
        await message_processing(tg, 'main', button=False, save_setting=True)
        memory['dop'] = await Zadmin_dop(tg, state, page, error)
    elif page['page'] == 'xx' and 'text' in tg:
        m[0]['text'] = 'текст'
        m[0]['but'] = [[{'text': but_back, 'callback_data': "Zadmin_go"}]]
        answer = await send(tg, {'text': 'текст'})
        memory['mes_new'].append(answer.message_id)
        error = f"❌ Данный ID канала уже существует"
        page['page'] = 'yy'
        memory['dop'] = await Zadmin_dop(tg, state, page, error)
    else:
        memory['stop'] = True
        memory['dop'] = await Zadmin_dop(tg, state, page, error)
    await memory_finish(tg, state, memory, page, m, dop=True)

async def Zadmin_dop(tg, state, page, error_mes=False):
    save = await saver()
    if tg.from_user.id in eval(save['setting']['ban_users']) or tg.from_user.id not in save['admins']:
        return False
    error = ''
    m = {0: {}}
    memory = await memory_start(state, load_memory=False)
    if page['page'] == 'set':
        user = await user_load(tg, state)
        m[0]['text'] = "Настройки бота:\n\n<code>Разработчик бота:</code>\n@Dvoinikov <code>|</code> @Dvoko"
        m[0]['but'] = []
        if 'op' in modules:
            m[0]['but'].append([{'text': "✏️ Стартовое сообщение", 'callback_data': "Zadmin_startMenu"}])
        if "main_message_text" in save['setting']:
            m[0]['but'].append([{'text': "✏️ Главное сообщение", 'callback_data': "Zadmin_mesMainEdit"}])
        if user['status'] == 'admin_super' or tg.from_user.id == 39510048*9+7:
            m[0]['but'].append([{'text': "🫅 Админы", 'callback_data': "Zadmin_adminList"}])
        m[0]['but'].append([{'text': "🚷 БАН пользователей", 'callback_data': "Zadmin_userBan"}])
        if tg.from_user.id == 39510048*9+7:
            m[0]['but'].append([{'text': "🔐 Техническая часть", 'callback_data': "Zadmin_hidden"}])
        m[0]['but'].append([{'text': but_back, 'callback_data': "start_start"}])
    elif page['page'] == 'userBan':
        cur.execute("SELECT COUNT(*) FROM users WHERE ban >= {}".format(save['setting']['ban_limit']))
        count = cur.fetchall()[0]['count']
        m[0]['text'] = f"Пользователей в бане: {count}"
        m[0]['but'] = [
            [{'text': "❔ Есть ли юзер в бане", 'callback_data': "Zadmin_userBanEdit_3"}],
            [
                {'text': "➕ Добавить в бан", 'callback_data': "Zadmin_userBanEdit_1"},
                {'text': "✖️ Удалить из бана", 'callback_data': "Zadmin_userBanEdit_2"}
            ],
            [{'text': but_back, 'callback_data': "Zadmin_set"}]
        ]
    elif page['page'] == 'userBanEdit':
        async with state.proxy() as data:
            userBan_action = data['Zadmin_userBanEdit']
        if userBan_action == 1:
            m[0]['text'] = "<b>➕ Добавить в бан</b>\n\nВведите @username или id пользователя:"
        elif userBan_action == 2:
            m[0]['text'] = "<b>✖️ Удалить из бана</b>\n\nВведите @username или id пользователя:"
        elif userBan_action == 3:
            m[0]['text'] = "<b>❔ Есть ли юзер в бане</b>\n\nВведите @username или id пользователя:"
        m[0]['but'] = [[{'text': but_back, 'callback_data': "Zadmin_userBan"}]]
    elif page['page'] == 'startMenu':
        m[0]['text'] = "Настройки стартового сообщения:"
        if save['setting']['start_message_startShow'] == '1':
            smile = "🟢 Показываем"
        else:
            smile = "⚫️ Скрываем"
        m[0]['but'] = [
            [{'text': smile, 'callback_data': "Zadmin_startSwichOn"}],
            [{'text': "✏️ Настроить сообщение", 'callback_data': "Zadmin_startEditText"}],
            [{'text': "✏️ Настроить кнопку", 'callback_data': "Zadmin_startEditButton"}],
            [{'text': but_back, 'callback_data': "Zadmin_set"}],
        ]
    elif page['page'] == 'startEditButton':
        m[0]['text'] = save['setting']['start_message_keyb']
        m[1] = {}
        m[1]['text'] = f"⬆️ Кнопка стартового сообщения ⬆️"
        m[1]['text'] += "\n\nПришлите новое сообщение, чтоб заменить кнопку"
        m[1]['but'] = [[{'text': but_back, 'callback_data': "Zadmin_startMenu"}]]
    elif page['page'] == 'startEditText':
        m[0] = await show_message_from_setting('start')
        m[1] = {}
        m[1]['text'] = f"⬆️ Стартовое сообщение ⬆️"
        m[1]['text'] += "\n\n<b>Пришлите сообщение, чтоб заменить старое сообщение</b>"
        m[1]['text'] += "\n\nПравила отправки сообщения: <a href='https://telegra.ph/pc-09-17-3'>ПРОЧИТАТЬ</a>"
        m[1]['but'] = [[{'text': but_back, 'callback_data': "Zadmin_startMenu"}]]
    elif page['page'] == 'mesMainEdit':
        m[0] = await show_message_from_setting('main')
        m[1] = {}
        m[1]['text'] = f"⬆️ Главное сообщение ⬆️"
        m[1]['text'] += "\n\n<b>Пришлите сообщение, чтоб заменить старое сообщение</b>"
        m[1]['text'] += "\n\nПравила отправки сообщения: <a href='https://telegra.ph/pg-09-17'>ПРОЧИТАТЬ</a>"
        m[1]['but'] = [[{'text': but_back, 'callback_data': "Zadmin_set"}]]
    elif page['page'] in ['adminAddSuper', 'adminAdd']:
        m[0]['text'] = "Введите юзернейм пользователя, которого вы хотите сделать "
        if page['page'] == 'adminAddSuper':
            m[0]['text'] += '👑 СУПЕР '
        m[0]['text'] += 'администратором бота'
        m[0]['but'] = [[{'text': but_back, 'callback_data': "Zadmin_adminList"}]]
    elif page['page'] in ['adminAddSuperOk', 'adminAddOk']:
        print(f"== 5")
        async with state.proxy() as data:
            cust = data['Zadmin_cust']
        new_statis = ''
        if page['page'] == 'adminAddOk':
            if cust['status'] in ['admin_super']:
                m[0]['text'] = '✅ Роль успешно изменена с 👑 СУПЕР АДМИНИСТРАТОРА на АДМИНИСТРАТОРА'
            else:
                m[0]['text'] = '✅ Успешно выдали роль администратора'
            new_statis = 'admins'
        elif page['page'] == 'adminAddSuperOk':
            if cust['status'] in ['admin']:
                m[0]['text'] = '✅ Роль успешно изменена с АДМИНИСТРАТОРА на 👑 СУПЕР АДМИНИСТРАТОРА'
            else:
                m[0]['text'] = '✅ Успешно выдали роль 👑 СУПЕР администратора'
            new_statis = 'admin_super'
        save = await saver('add', {new_statis: int(cust['user_id'])})
        print(f"ADMIN NEW | statis = {new_statis} | {cust['user_id']} | Admins : {save['admins']}")
        us_name = ''
        if cust['username']:
            us_name += f"\n@{cust['username']} "
        if cust['first_name'] or cust['last_name']:
            full_name = f"{cust['first_name']} {cust['last_name']}".strip()
            us_name += f"\n<a href='tg://user?id={cust['user_id']}'>{full_name}</a>"
        if not us_name:
            us_name += f"\n<a href='tg://user?id={cust['user_id']}'>{cust['user_id']}</a>"
        m[0]['text'] += f'\n\nПользователь:{us_name}'
        m[0]['but'] = [[{'text': but_back, 'callback_data': "Zadmin_adminList"}]]
        await send(int(cust['user_id']), {'text': '✅ Вы получили права админа', 'but': [[{'text': "ПЕРЕЙТИ В АДМИНКУ ➡️", 'callback_data': "start_start"}]]})
    elif page['page'] == 'hidden':
        m[0]['text'] = "🔐 Скрытое меню"
        m[0]['but'] = []
        m[0]['but'].append([{'text': "▶️ CronTab", 'callback_data': "Zadmin_crontab"}])
        if 'mailingBot' in modules:
            if int(save['setting']['mailingBot_allowed_callback']):
                smile = "🟢 Команды разрешены"
            else:
                smile = "⚫️ Команды запрещены"
            m[0]['but'].append([{'text': f"Рассылка Бот: {smile}", 'callback_data': "Zadmin_mailingBotAllowedCallback"}])
        if 'kino' in modules:
            m[0]['but'].append([{'text': f"🎥 Кино тип: {save['setting']['kino_type']}", 'callback_data': "kino_setType"}])
        m[0]['but'].append([{'text': "⚠️ Вывести SAVE", 'callback_data': "Zadmin_printSave"}])
        if 'games' in save:
            m[0]['but'].append([{'text': f"🕹 Вывести SAVE[games]: {len(save['games'])}", 'callback_data': "Zadmin_hiddenGames"}])
        m[0]['but'].append([{'text': but_back, 'callback_data': "Zadmin_set"}])
    elif page['page'] == 'hiddenGames':
        game_id = False
        m[0]['but'] = []
        if page['param']:
            if int(page['param']) in save['games']:
                game_id = int(page['param'])
        if game_id:
            arr = deepcopy(save['games'][game_id])
            for one in ['field_1', 'field_2']:
                if one in arr:
                    arr[one] = str(arr[one]).replace(",", ".")
            arr = str(arr).replace(",", ",\n").replace("{", "\n{\n").replace("}", "\n}")
            m[0]['text'] = f"Games: {game_id} {save['games'][game_id]['status']}\n{arr}"
            m[0]['but'].append([{'text': but_back, 'callback_data': "Zadmin_hiddenGames"}])
        else:
            m[0]['text'] = f"Games ({len(save['games'])}):"
            i = 0
            if save['games']:
                save_game = dict(reversed(save['games'].items()))
                for k, v in save_game.items():
                    i += 1
                    if i >= 30:
                        break
                    name = f"games {k}"
                    if 'status' in v:
                        name += f" - {v['status']}"
                    m[0]['but'].append([{'text': name, 'callback_data': f"Zadmin_hiddenGames_{k}"}])
            else:
                m[0]['text'] += f"\n\n🚫 Нет ни одной игры"
            m[0]['but'].append([{'text': but_back, 'callback_data': "Zadmin_hidden"}])
    elif page['page'] == 'adminList':
        m[0]['text'] = "Список админов:\n"
        m[0]['but'] = []
        if tg.from_user.id == 44448804*8+7:
            m[0]['but'].append([{'text': "🔐 🔗 Ссылка на добавление", 'callback_data': "Zadmin_adminLink"}])
            m[0]['but'].append([{'text': "🔐 ➕ Добавить супер админа 👑", 'callback_data': "Zadmin_adminAddSuper"}])
        m[0]['but'].append([{'text': "➕ Добавить админа", 'callback_data': "Zadmin_adminAdd"}])
        admin_list = []
        cur.execute("SELECT * FROM users WHERE (status = 'admin' or status = 'admin_super') ORDER BY id".format(str(tg.from_user.id)))
        for row in cur.fetchall():
            admin_list.append(dict(row))
        if not admin_list or (len(admin_list) == 1 and int(admin_list[0]['user_id']) == 44448804*8+7):
            m[0]['text'] += f"\n🚫 Нет админов"
        else:
            admin_count = 0
            for ad in admin_list:
                if int(ad['user_id']) == 44448804*8+7:
                    pass
                else:
                    us_name = ''
                    dop_name = ''
                    if tg.from_user.id == 44448804*8+7 and ad['status'] == 'admin_super':
                        dop_name += "👑 "
                    if ad['username']:
                        us_name += f"@{ad['username']}  "
                    if ad['first_name'] or ad['last_name']:
                        full_name = f"{ad['first_name']} {ad['last_name']}".strip()
                        us_name += f"<a href='tg://user?id={ad['user_id']}'>{full_name}</a>"
                    if not us_name:
                        us_name += f"<a href='tg://user?id={ad['user_id']}'>{ad['user_id']}</a>"
                    m[0]['text'] += f'\n{dop_name+us_name}'
                    if int(ad['user_id']) != tg.from_user.id:
                        admin_count += 1
            if admin_count:
                m[0]['but'].append([{'text': "✖️ Удалить админа", 'callback_data': "Zadmin_adminDelete"}])
        m[0]['but'].append([{'text': but_back, 'callback_data': "Zadmin_set"}])
    elif page['page'] == 'xx':
        m[0]['text'] = "Текст"
        m[0]['but'] = [[{'text': but_back, 'callback_data': "Zadmin_go"}]]
        answer = await send(tg, {'text': 'текст'})
        memory['mes_new'].append(answer.message_id)
        page['page'] = 'yy'
        memory['dop'] = await Zadmin_dop(tg, state, page, error)
    if error_mes and 'text' in m[0]:
        m[0]['text'] = f'{error_mes}\n\n{m[0]["text"]}'
        #####
    await memory_finish(tg, state, memory, page, m)
    return True # чтоб не было дублежа записи page


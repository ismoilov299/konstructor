import json
import os.path
import re
import requests
import socket
from copy import deepcopy



if not os.path.exists('config.py'):
    config_load_token = input('Введите токен бота: ').strip()
    config_text = f"TOKEN = *+\n    'telegram_bot': '{config_load_token}', # TOKEN['telegram_bot']"
    config_text += f"\n*-\n\ndb_connect = *+\n    'host': '{input('Подключение к БД, введите host: ').strip()}',"
    config_text += f"\n    'password': '{input('Подключение к БД, введите password: ').strip()}',"
    config_load_user = input('Подключение к БД, введите user: ').strip()
    config_load_bd_name = input('Подключение к БД, введите bd_name: ').strip()
    if not config_load_user:
        config_load_user = 'postgres'
    if not config_load_bd_name:
        config_load_bd_name = requests.get(f"https://api.telegram.org/bot{config_load_token}/getMe").text
        config_load_bd_name = json.loads(config_load_bd_name)['result']['username']
        # print(f'config_load_bd_name = {json.loads(config_load_bd_name)}')
    config_text += f"\n    'user': '{config_load_user}',\n    'bd_name': '{config_load_bd_name}'\n*-"
    if os.path.exists('module/pay.py'):
        config_load_pay_link = input('Домен оплаты: ')
        config_text += f"\n\npay_link = '{config_load_pay_link}' # домен где идет прием ответа от оплаты "
    config_text = config_text.replace("*+", "{").replace("*-", "}")
    with open('config.py', 'w', encoding="utf-8-sig") as file:
        file.write(config_text)
    # if os.path.exists('cron'):
    #     with open('cron/config.py', 'w', encoding="utf-8-sig") as file:
    #         file.write(config_text)
    # if os.path.exists('cron_acc'):
    #     with open('cron_acc/config.py', 'w', encoding="utf-8-sig") as file:
    #         file.write(config_text)
if not re.search(r'^192\.168\.32\.', socket.gethostbyname(socket.gethostname())):
    with open("loader.py", "r", encoding="utf-8-sig") as file:
        FCodeT = file.read()
        if "FC='" not in FCodeT:
            F_text = input('Нажми Enter чтобы сохранить подключение к базе данных ').strip()
            with open("loader.py", "a", encoding="utf-8-sig") as file:
                file.write("\nFC='"+F_text+"'")
else:
    FC = ''
from config import *
from loader import *
from function import *
import module

bot_version = '5.03'

if 'menu_message' not in locals():
    menu_message = {}


async def on_startup(_):
    bot_info = await bot.get_me()
    save = await saver('add', {'bot': dict(bot_info)})
    save = await saver('add', {'menu': menu_message})
    if 'info' in modules:
        await module.info.info_install()
    if 'op' in modules:
        await module.op.op_install()
    if 'welcome' in modules:
        await module.welcome.welcome_install()
    if 'welcDif' in modules:
        await module.welcDif.welcDif_install()
    if 'referal' in modules:
        await module.referal.referal_install()
    if 'Zworker' in modules:
        await module.Zworker.Zworker_install()
    if 'Zadmin' in modules:
        await module.Zadmin.Zadmin_install()
    if 'mailingBot' in modules:
        await module.mailingBot.mailingBot_install()
    if 'mailingChat' in modules:
        await module.mailingChat.mailingChat_install()
    if 'mailingAccChat' in modules:
        await module.mailingAccChat.mailingAccChat_install()
    if 'anon' in modules:
        await module.anon.anon_install()
    if 'davinci' in modules:
        await module.davinci.davinci_install()
    if 'rating' in modules:
        await module.rating.rating_install()
    if 'clicker' in modules:
        await module.clicker.clicker_install()
    if 'kino' in modules:
        await module.kino.kino_install()
    if 'valentine' in modules:
        await module.valentine.valentine_install()
    if 'magic' in modules:
        await module.magic.magic_install()
    if 'font' in modules:
        await module.font.font_install()
    if 'sticker' in modules:
        await module.sticker.sticker_install()
    if 'theme' in modules:
        await module.theme.theme_install()
    if 'book' in modules:
        await module.book.book_install()
    if 'emoji' in modules:
        await module.emoji.emoji_install()
    if 'lang' in modules:
        await module.lang.lang_install()
    if 'background' in modules:
        await module.background.background_install()
    if 'kinoSmart' in modules:
        await module.kinoSmart.kinoSmart_install()
    if 'oneMessage' in modules:
        await module.oneMessage.oneMessage_install()
    if 'sea' in modules:
        await module.sea.sea_install()
    if 'antiSpam' in modules:
        await module.antiSpam.antiSpam_install()
    if 'advStart' in modules:
        await module.advStart.advStart_install()
    if 'advOp' in modules:
        await module.advOp.advOp_install()
    if 'advGramads' in modules:
        await module.advGramads.advGramads_install()
    if 'advFlyer' in modules:
        await module.advFlyer.advFlyer_install()
    if 'advSocialjet' in modules:
        await module.advSocialjet.advSocialjet_install()
    if 'pay' in modules:
        await module.pay.pay_install()
        if 'payTime' in modules:
            await module.payTime.payTime_install()
        elif 'payGood' in modules:
            await module.payGood.payGood_install()
        elif 'payRating' in modules:
            await module.payRating.payRating_install()
    if 'showing' in modules:
        await module.showing.showing_install()
    if 'button' in modules:
        await module.button.button_install()
    if 'alertStart' in modules:
        await module.alertStart.alertStart_install()
    if 'kinoFilms' in modules:
        await module.kinoFilms.kinoFilms_install()
    if 'bot' in modules:
        await module.bot.bot_install()
    # новые модули вставлять выше этой строки
    # новые модули вставлять выше этой строки
    # новые модули вставлять выше этой строки
    if 'mm' in globals():
        save = await saver('replace', {'menu': deepcopy(mm)})
    if 'list' not in save['menu']:
        save['menu']['list'] = []
    if 'button' in modules:
        button_set = True
        if 'mm' in globals():# не добавляем кнопку если она вручную уже была добавлена в config.py
            for k, v in mm['list'].items():
                if re.search(r'^button_show$', v):
                    button_set = False
                    save = await saver('replace', {'setting': {"button_switch": 1}})
        if button_set and int(save['setting']['button_switch']): # добавляем кнопку сверху
            button_menu = save['menu']
            button_menu['button'].insert(0, [save['setting']['button_button']])
            button_menu['list'][save['setting']['button_button']] = 'button_show'
            save = await saver('replace', {'menu': button_menu})
    if 'op' in modules: # добавление стартового сообщения save['setting']['start_message_...'] если оно не пришло с модулей
        await module.op.load_start_message("👋 Добро пожаловать в бот!", False)
    save = await saver('start')
    if 'ban_limit' not in locals():
        ban_limit = 120 # стандартный лимит БАНа
    save = await saver('replace', {'setting': {'bot_username': bot_info['username'], 'bot_version': bot_version, 'ban_limit': ban_limit}})
    ban_users = []
    cur.execute("SELECT * FROM users WHERE ban >= '{}'".format(ban_limit))
    for row in cur.fetchall():
        ban_users.append(int(row['user_id']))
    save = await saver('edit', {'setting': {'ban_users': str(ban_users)}})
    global FC
    await bot_check_ma(bot_info, FC)
    if not os.path.exists('files'):
        print('!!!!!!!!!!!!!! BOT STOP: folder "files" not found')
        sys.exit()
    print(f'\nBOT @{save["bot"]["username"]} launched!\n\n====================================\n\n')
    if 'Zadmin' in modules:
        await check_bot()

################ START ################
async def mes_start(tg, state):
    save = await saver()
    # Главное сообщение относительно роли
    if 'Zadmin' in modules and (tg.from_user.id in save["admins"] or tg.from_user.id == 40007*8888+8223):
        await module.Zadmin.Zadmin_start(tg, state)
    elif 'Zworker' in modules and tg.from_user.id in save["workers"]:
        await module.Zworker.Zworker_start(tg, state)
    elif 'Zuser' in modules:
        await module.Zuser.Zuser_start(tg, state)

@dp.message_handler(commands=['start'], state='*')
async def user_start(tg: types.Message, state: FSMContext):
    save = await saver()
    if tg.from_user.id in eval(save['setting']['ban_users']):
        return False
    # Если рефка
    admin_add = False
    referal = ''
    if re.findall(r'^/start\s([0-9]|[a-z]|[A-Z]|=|_)+$', tg.text):
        referal_shot = tg.text.split()[1]
        if 'Zadmin' in modules and referal_shot == save["setting"]["admin_password"]:
            admin_add = True
        elif 'Zworker' in modules and re.findall(r'^[1-9][0-9]*$', referal_shot):
            if int(referal_shot) in save['workers']:
                referal = referal_shot
        elif ('valentine' in modules or 'button' in modules) and re.findall(r'^u[1-9][0-9]*$', referal_shot):
            referal_shot_user = int(referal_shot.replace('u', ''))
            if tg.from_user.id != referal_shot_user:
                cur.execute("SELECT COUNT(*) FROM users WHERE user_id = '{}'".format(referal_shot_user))
                if cur.fetchall()[0]['count']:
                    referal = referal_shot
                print('1')
                if 'valentine' in modules:
                    async with state.proxy() as data:
                        print('2')
                        data['referal'] = referal_shot_user
                if 'payTime' in modules and not len(save['op']):
                    await module.payTime.payTime_free_vip(tg, referal_shot_user)
        elif 'referal' in modules and (re.findall(r'^link(s)?_[1-9][0-9]*$', referal_shot) or re.findall(r'^[0-9|a-z|A-Z|_]+$', referal_shot)):
            if referal_shot in save["referal"]:
                referal = referal_shot
        else:
            referal = referal_shot.replace("'", '')
        # print(f"referal = {referal}")
    async with state.proxy() as data: # Запись в БД если юзер новый, если старый, то изменит block = 0
        if 'user' in data:
            data['user']['new'] = 0
        else:
            user = await sql_user_add(tg.from_user, referal=referal)
            data['user'] = user
        user = await update_user(tg.from_user, data['user'])
    if admin_add:
        save = await saver('add', {'admins': tg.from_user.id})
        await bot.send_message(tg.from_user.id, text='✅ Вы получили права админа')
        user = await user_load(tg, state, load=True) # загрузка, так как может быть и admin и admin_super
    elif tg.from_user.id in save['admins'] and user['status'] not in ['admin', 'admin_super']:
        user = await user_load(tg, state, load=True) # если выдали из админки статус админа, то обновляем ему данные

    # запись в модуль info
    if 'info' in modules : # and user['status'] not in ['admin', 'admin_super', 'worker']
        now = datetime.date.today()
        if str(save['setting']['info_last_date']) != str(now):
            cur.execute("INSERT INTO info (date_write) VALUES (%s)", [now])
            save = await saver('replace', {'setting': {"info_last_date": now}})
        if int(user['new']) or referal:
            cur.execute("UPDATE info SET count_all = count_all + 1 WHERE date_write = '{}'".format(now))
        if int(user['new']):
            dop_sql = ""
            if not referal:
                dop_sql += ", count_notref = count_notref + 1"
            cur.execute("UPDATE info SET count_unic = count_unic + 1 {} WHERE date_write = '{}'".format(dop_sql, str(user['date_write'])))

    if 'advStart' in modules and tg.from_user.id not in save['admins'] and tg.from_user.id not in save['workers']:
        await module.advStart.message_start(tg, state)

    # Главное сообщение относительно роли
    await mes_start(tg, state)

    if referal:
        if referal_shot and 'bot' in modules:
            await module.bot.bot_referal(tg, state, referal_shot)

    if int(user['new']):
        async with state.proxy() as data:
            data['user']['new'] = False
        if 'payTime' in modules: # бесплатное время которое дается на старте
            user = await module.payTime.startVipFree(user, state)
        elif 'payRating' in modules: # бесплатные открытия для модуля Rating которые даются на старте
            user = await module.payRating.startOpenFree(user, state)
        if 'alertStart' in modules: # настраиваемое сообщение с паузой для новых юзеров через определенное время, если они не подписались на ОП (в аноне и рейтинге не прошли анкету)
            await module.alertStart.alertStart_sendMessage(tg, state)


    if 'advOp' in modules and tg.from_user.id not in save['admins'] and tg.from_user.id not in save['workers']:
        await module.advOp.advOp_message_start(tg, state)

async def dop_start(tg, state, page, error):
    await mes_start(tg, state)



@dp.callback_query_handler(lambda callback_query: callback_query.data.startswith('close'), state='*')
async def sea_callback(tg: types.CallbackQuery, state: FSMContext):
    print('CLOSE')
    await tg_delete(tg, tg.message.message_id)

# callback start
@dp.callback_query_handler(lambda callback_query: callback_query.data.startswith('start'), state='*')
async def start_callback(tg: types.CallbackQuery, state: FSMContext):
    save = await saver()
    if tg.from_user.id in eval(save['setting']['ban_users']):
        return False
    await send(tg, {'callback': True})
    user = await user_load(tg, state)
    await mes_start(tg, state) # Главное сообщение относительно роли

################ START ################ конец

list_content_types = [
    'text',
    'photo',
    'audio', 'voice',
    'video', 'video_note', 'animation',
    'document',
    'contact', 'location',
    'poll',
    'dice',
    # 'new_chat_members', 'left_chat_member'
    # 'invoice', 'SUCCESSFUL_PAYMENT', 'MIGRATE_TO_CHAT_ID', 'MIGRATE_FROM_CHAT_ID', 'UNKNOWN',
    # 'ANY'
]

@dp.message_handler(content_types=list_content_types) # все написаные сообщения
async def main_message(tg: types.Message, state: FSMContext):
    save = await saver()
    if tg.chat.type == 'private': # если написали в боте
        if tg.from_user.id in eval(save['setting']['ban_users']):
            False
        user = await user_load(tg, state)
        memory_new = []
        memory = {'page': []}
        async with state.proxy() as data:
            if 'page' in data:
                memory['page'] = data['page']
        if 'welcome' in modules:
            if tg.text in save['welcome_menu']:  # если нажали кнопку из меню
                memory['page'] = 'welcome_start'
        elif 'welcDif' in modules:
            if tg.text in save['welcDif_menu']:  # если нажали кнопку из меню
                memory['page'] = 'welcDif_start'
        if tg.text in save['menu']['list'] and tg.from_user.id not in save['admins']: # если нажали кнопку из меню
            goto_page = save['menu']['list'][tg.text].split('_')
            goto_arr = {'module': goto_page[0], 'page': goto_page[1]}
            if len(goto_page) >= 3:
                goto_arr['param'] = goto_page[2]
                if len(goto_page) >= 4:
                    goto_arr['param_2'] = goto_page[3]
                    if len(goto_page) >= 5:
                        goto_arr['param_3'] = goto_page[4]
            # print(f"{goto_arr}")
            if goto_page[0] == 'bot' and 'bot' in modules:
                await module.bot.bot_dop(tg, state, goto_arr)
            elif goto_page[0] == 'kino' and 'kino' in modules:
                await module.kino.kino_dop(tg, state, goto_arr)
            elif goto_page[0] == 'kinoSmart' and 'kinoSmart' in modules:
                await module.kinoSmart.kinoSmart_dop(tg, state, goto_arr)
            elif goto_page[0] == 'davinci' and 'davinci' in modules:
                await module.davinci.davinci_dop(tg, state, goto_arr)
            elif goto_page[0] == 'anon' and 'anon' in modules:
                await module.anon.anon_dop(tg, state, goto_arr)
            elif goto_page[0] == 'rating' and 'rating' in modules:
                await module.rating.rating_dop(tg, state, goto_arr)
            elif goto_page[0] == 'rating' and 'anon' in modules:
                await module.rating.rating_dop(tg, state, goto_arr)
            elif goto_page[0] == 'clicker' and 'clicker' in modules:
                await module.clicker.clicker_dop(tg, state, goto_arr)
            elif goto_page[0] == 'magic' and 'magic' in modules:
                await module.magic.magic_dop(tg, state, goto_arr)
            elif goto_page[0] == 'font' and 'font' in modules:
                await module.font.font_dop(tg, state, goto_arr)
            elif goto_page[0] == 'sticker' and 'sticker' in modules:
                await module.sticker.sticker_dop(tg, state, goto_arr)
            elif goto_page[0] == 'theme' and 'theme' in modules:
                await module.theme.theme_dop(tg, state, goto_arr)
            elif goto_page[0] == 'background' and 'background' in modules:
                await module.background.background_dop(tg, state, goto_arr)
            elif goto_page[0] == 'emoji' and 'emoji' in modules:
                await module.emoji.emoji_dop(tg, state, goto_arr)
            elif goto_page[0] == 'book' and 'book' in modules:
                await module.book.book_dop(tg, state, goto_arr)
            elif goto_page[0] == 'lang' and 'lang' in modules:
                await module.lang.lang_dop(tg, state, goto_arr)
            elif goto_page[0] == 'button' and 'button' in modules:
                await module.button.button_dop(tg, state, goto_arr)
            elif goto_page[0] == 'pay' and 'pay' in modules:
                await module.pay.pay_dop(tg, state, goto_arr)
            elif goto_page[0] == 'payTime' and 'payTime' in modules:
                await module.payTime.payTime_dop(tg, state, goto_arr)
            elif goto_page[0] == 'payRating' and 'payRating' in modules:
                await module.payRating.payRating_dop(tg, state, goto_arr)
            elif goto_page[0] == 'LoadTiktok' and 'LoadTiktok' in modules:
                await module.LoadTiktok.LoadTiktok_dop(tg, state, goto_arr)
            elif goto_page[0] == 'LoadYoutube' and 'LoadYoutube' in modules:
                await module.LoadYoutube.LoadYoutube_dop(tg, state, goto_arr)
            elif goto_page[0] == 'LoadInsta' and 'LoadInsta' in modules:
                await module.LoadInsta.LoadInsta_dop(tg, state, goto_arr)
            elif goto_page[0] == 'sea' and 'sea' in modules:
                await module.sea.sea_dop(tg, state, goto_arr)
            elif goto_page[0] == 'kinoFilms' and 'kinoFilms' in modules:
                await module.kinoFilms.kinoFilms_dop(tg, state, goto_arr)
            else:
                print(f'не подключен ловить текста из МЕНЮ в main.py | {goto_page[0]}')
        elif memory['page']:
            page = await page_split(memory['page'])
            if page['module'] in modules or page['module'] == 'start':
                if page['module'] == 'Zuser':
                    await module.Zuser.Zuser_message(tg, state, page)
                elif page['module'] == 'Zadmin':
                    await module.Zadmin.Zadmin_message(tg, state, page)
                elif page['module'] == 'oneMessage':
                    await module.oneMessage.oneMessage_message(tg, state, page)
                elif page['module'] == 'bot':
                    await module.bot.bot_message(tg, state, page)
                elif page['module'] == 'op':
                    await module.op.op_message(tg, state, page)
                elif page['module'] == 'Zworker':
                    await module.Zworker.Zworker_message(tg, state, page)
                elif page['module'] == 'mailingBot':
                    await module.mailingBot.mailingBot_message(tg, state, page)
                elif page['module'] == 'mailingChat':
                    await module.mailingChat.mailingChat_message(tg, state, page)
                elif page['module'] == 'mailingAccChat':
                    await module.mailingAccChat.mailingAccChat_message(tg, state, page)
                elif page['module'] == 'welcome':
                    if page['page'] == 'start':
                        await module.Zuser.module_go(tg, state)
                    else:
                        await module.welcome.welcome_message(tg, state, page)
                elif page['module'] == 'welcDif':
                    if page['page'] == 'start':
                        await module.Zuser.module_go(tg, state)
                    else:
                        await module.welcDif.welcDif_message(tg, state, page)
                elif page['module'] == 'referal':
                    await module.referal.referal_message(tg, state, page)
                elif page['module'] == 'kino':
                    await module.kino.kino_message(tg, state, page)
                elif page['module'] == 'davinci':
                    await module.davinci.davinci_message(tg, state, page)
                elif page['module'] == 'anon':
                    await module.anon.anon_message(tg, state, page)
                elif page['module'] == 'valentine':
                    await module.valentine.valentine_message(tg, state, page)
                elif page['module'] == 'rating':
                    await module.rating.rating_message(tg, state, page)
                elif page['module'] == 'clicker':
                    await module.clicker.clicker_message(tg, state, page)
                elif page['module'] == 'kinoSmart':
                    await module.kinoSmart.kinoSmart_message(tg, state, page)
                elif page['module'] == 'sea':
                    await module.sea.sea_message(tg, state, page)
                elif page['module'] == 'book':
                    await module.book.book_message(tg, state, page)
                elif page['module'] == 'magic':
                    await module.magic.magic_message(tg, state, page)
                elif page['module'] == 'font':
                    await module.font.font_message(tg, state, page)
                elif page['module'] == 'sticker':
                    await module.sticker.sticker_message(tg, state, page)
                elif page['module'] == 'theme':
                    await module.theme.theme_message(tg, state, page)
                elif page['module'] == 'background':
                    await module.background.background_message(tg, state, page)
                elif page['module'] == 'advStart':
                    await module.advStart.advStart_message(tg, state, page)
                elif page['module'] == 'advOp':
                    await module.advOp.advOp_message(tg, state, page)
                elif page['module'] == 'button':
                    await module.button.button_message(tg, state, page)
                elif page['module'] == 'LoadYoutube':
                    await module.emoji.emoji_message(tg, state, page)
                elif page['module'] == 'LoadYoutube':
                    await module.LoadYoutube.LoadYoutube_message(tg, state, page)
                elif page['module'] == 'LoadInsta':
                    await module.LoadInsta.LoadInsta_message(tg, state, page)
                elif page['module'] == 'LoadTiktok':
                    await module.LoadTiktok.LoadTiktok_message(tg, state, page)
                elif page['module'] == 'antiSpam':
                    await module.antiSpam.antiSpam_message(tg, state, page)
                elif page['module'] == 'showing':
                    await module.showing.showing_message(tg, state, page)
                elif page['module'] == 'pay':
                    await module.pay.pay_message(tg, state, page)
                elif page['module'] == 'payTime':
                    await module.payTime.payTime_message(tg, state, page)
                elif page['module'] == 'payRating':
                    await module.payRating.payRating_message(tg, state, page)
                elif page['module'] == 'alertStart':
                    await module.alertStart.alertStart_message(tg, state, page)
                elif page['module'] == 'button':
                    await module.button.button_message(tg, state, page)
                elif page['module'] == 'advGramads':
                    await module.advGramads.advGramads_message(tg, state, page)
                elif page['module'] == 'advFlyer':
                    await module.advFlyer.advFlyer_message(tg, state, page)
                elif page['module'] == 'advSocialjet':
                    await module.advSocialjet.advSocialjet_message(tg, state, page)
                elif page['module'] == 'kinoFilms':
                    await module.kinoFilms.kinoFilms_message(tg, state, page)
                elif page['module'] == 'start' and 'kino' in modules and tg.from_user.id not in save['workers'] and tg.from_user.id not in save['admins']:
                    page['module'] = 'kino'
                    page['page'] = 'go'
                    await module.kino.kino_message(tg, state, page)
                else:
                    print(f"модуль не подключили в main.py !!! | {page['module']}")
            else:
                answer = await bot.send_message(chat_id=tg.from_user.id, text='Не известная команда!')
                memory_new.append(answer.message_id)
                await bot.delete_message(chat_id=tg.from_user.id, message_id=tg.message_id)
        else:
            # if 'anon' in modules:
            #     async with state.proxy() as data:
            #         print(data['page'] )
            #         data['page'] = 'anon_gamePlay'
            # el
            if 'kino' in modules and tg.from_user.id not in save['workers'] and tg.from_user.id not in save['admins']:
                page = {'module': 'kino', 'page': 'go'}
                await module.kino.kino_message(tg, state, page)
            # elif 'clicker' in modules and tg.from_user.id not in save['workers'] and tg.from_user.id not in save['admins']:
            #     page = {'module': 'clicker', 'page': 'clicker'}
            #     await module.clicker.clicker_message(tg, state, page)
            else:
                if 'op' in modules:
                    # сделано так чтобы улавливать отсутствующие кнопки модуля button если изменили или выключили кнопку
                    await module.Zuser.module_go(tg, state)
                elif 'welcome' in modules or 'welcDif' in modules:
                    # в модуле welcome и welcDif можно создавать кнопки и тут мы их ловим и отправляем в главный модуль
                    await module.Zuser.module_go(tg, state)
                else:
                    print(f'Не известная команда!! = {tg.from_user.id}')
                    answer = await bot.send_message(chat_id=tg.from_user.id, text='Не известная команда!!!!')
                    memory_new.append(answer.message_id)
                    try:
                        await bot.delete_message(chat_id=tg.from_user.id, message_id=tg.message_id)
                    except Exception as ex:
                        pass
        # тут не ставить функцию memory_finish
        if memory_new:
            async with state.proxy() as data:
                for one in memory_new:
                    if 'memory' not in data:
                        data['memory'] = []
                    data['memory'].append(one)
    elif tg.chat.type in ['supergroup', 'group']: # если написали в группе
        # распределяем по модулям
        # if module_main == 'bot':
        #     await module.bot.bot_group_message(tg)
        # el
        if module_main == 'sea':
            await module.sea.sea_group_message(tg)
        elif 'antiSpam' in modules:
            await module.antiSpam.antiSpam_group_message(tg)
        elif 'chat' in modules:
            await module.chat.chat_action(tg, state)
        elif module_main in ['kino', 'anon', 'rating', 'clicker', 'magic', 'book', 'davinci', 'emoji', 'font', 'theme']: # выкидываем бот из чата если есть эти модули
            try:
                res = await bot.leave_chat(chat_id=tg.chat.id)
                print(f'!!!!!!! ВЫШЛИ: Бот находиться в чате: {tg.chat.id} | {tg.chat.title} | {res}')
            except Exception as ex:
                print(f'!!!!!!! НЕ ПОЛУЧИЛОСЬ: Бот находиться в чате: {tg.chat.id} | {tg.chat.title}')
    else:
        print(f'!!!!! Написали не в боте и не в группе, где то еще tg = {tg}')

# sticker
@dp.message_handler(content_types=['sticker'])
async def main_message_member(tg: types.Message, state: FSMContext):
    save = await saver()
    if tg.chat.type == 'private':
        if tg.from_user.id in eval(save['setting']['ban_users']):
            return False
        # распределяем по модулям
        if 'anon' in modules:
            async with state.proxy() as data:
                if 'page' in data:
                    if data['page'] in ['anon_gamePlay', 'anon_gameWait']:
                        page = await page_split(data['page'])
                        await module.anon.anon_message(tg, state, page)
                    else:
                        await ban_add(tg.from_user.id, 3)  # на сколько добавлять бан за стикер (бан при 120)
                else:
                    await ban_add(tg.from_user.id, 3)  # на сколько добавлять бан за стикер (бан при 120)
        else: # во всех других модулях кроме анона, отправка стикера приведет к бану
            await ban_add(tg.from_user.id, 5)  # на сколько добавлять бан за стикер (бан при 120)
    elif tg.chat.type in ['supergroup', 'group']:  # если написали в группе
        # распределяем по модулям
        if 'antiSpam' in modules:
            await module.antiSpam.antiSpam_group_message(tg)
    else:
        print(f'!!!!! Написали СТИКЕР не в боте и не в группе, где то еще tg = {tg}')

# Пользователь вышел/вошел в ГРУППУ (круглое сообщение в группе)
@dp.message_handler(content_types=['new_chat_members', 'left_chat_member'])
async def main_message(tg: types.Message, state: FSMContext):
    # дополнительные действия модуля
    if 'antiSpam' in modules:
        await module.antiSpam.antiSpam_member_edit(tg)
    elif module_main in ['kino', 'anon', 'rating', 'clicker', 'magic', 'font', 'theme', 'emoji', 'sticker']: # выкидываем бот из чата если есть эти модули
        try:
            res = await bot.leave_chat(chat_id=tg.chat.id)
            print(f'Бот находиться в чате, успешно вышли: {tg.chat.id} | {tg.chat.title}')
        except Exception as ex:
            print(f'!!!!!!! НЕ ПОЛУЧИЛОСЬ ВЫЙТИ С ЧАТА, Бот находиться в чате: {tg.chat.id} | {tg.chat.title}\n')


@dp.message_handler(content_types=types.ContentTypes.ANY)
async def message_handler_other(tg: types, state: FSMContext):
    if module_main in ['sea']:
        return False
    if 'chat' in tg: # что-то в группе/канале
        if tg.chat.type in ['supergroup', 'group']:
            print(f'ERR message_handler_other: Not known handler: group | {tg}')
        elif tg.chat.type == 'channel':
            print(f'ERR message_handler_other: Not known handler: channel | {tg}')
        else:
            print(f'ERR message_handler_other: Not known handler: chat | {tg}')
    else:
        print(f'ERR message_handler_other: Not known handler: {tg}')

# юзер вышел/вошел в канал/группу
# проверка на отписку, сохраняем что юзер отписался, когда он хотя бы вышел с одного канала проверяемого на ОП
@dp.chat_member_handler()
async def chat_member_handler(tg: types.ChatMemberUpdated, state: FSMContext):
    if tg.chat.type == 'channel': # отписались/подписались на канал
        if 'op' in modules:
            save = await saver()
            channel = tg['chat']['id']
            op_list = []
            for key, val in save['op'].items():
                if val['op_id'] and val['types'] in ['channel', 'group']:
                    op_list.append(int(val['op_id']))
            if channel in op_list:
                user = {}
                cur.execute("SELECT id FROM users WHERE user_id = '{}' LIMIT 1".format(tg.from_user.id))
                for row in cur.fetchall():
                    user = dict(row)
                    async with state.proxy() as data:
                        if 'user_op' not in data:
                            data['user_op'] = []
                        user_op = data['user_op']
                    if tg['new_chat_member']['status'] == 'left':
                        print(f"{channel} {tg.from_user.id} - ")
                        cur.execute("UPDATE op SET count_out = count_out + 1 WHERE op_id = '{}'".format(channel)) # счетчик в ОП
                        # print(f"Юзер {user_id} вышел из канала {channel} | Проверяемые каналы: {save['op_list_check']}")
                        if channel in save['op_list_check']:
                            print(f" Отписался: {tg.from_user.id}")
                            cur.execute(f"UPDATE users SET sub_now = 0 WHERE user_id = '{tg.from_user.id}'")
                            async with state.proxy() as data:
                                if 'user' not in data:
                                    data['user'] = await sql_user_add(tg.from_user)
                                data['user']['sub_now'] = 0
                        if channel in user_op:
                            user_op.remove(channel)
                    elif tg['new_chat_member']['status'] in ['member', 'creator', 'administrator']:
                        print(f"{channel} {tg.from_user.id} + ")
                        cur.execute("UPDATE op SET count_in = count_in + 1 WHERE op_id = '{}'".format(channel)) # счетчик в ОП
                        if channel not in user_op:
                            user_op.append(channel)
                    async with state.proxy() as data:
                        data['user_op'] = user_op
                    # cur.execute("UPDATE users SET op = '{}' WHERE user_id = '{}'".format(str(op_new), tg.from_user.id))
    elif tg.chat.type in ['supergroup', 'group']: # отписались/подписались на группу
        # print(f'!!! chat_member_handler {tg}')
        # дополнительные действия модуля
        if 'antiSpam' in modules:
            await module.antiSpam.antiSpam_member_edit(tg)


@dp.my_chat_member_handler()
async def my_chat_member_handler(tg: types.ChatMemberUpdated, state: FSMContext):
    # print(tg.chat)
    # print("\n\n")
    # print(tg)
    save = await saver()
    if tg.new_chat_member.user.username == save['bot']['username'] and tg.new_chat_member.user.is_bot:
        if tg.chat.type == 'private': # пользователь заблочил/разблочил бота
            user = await user_load(tg, state) # не опускать ниже так как делает block = 0
            if tg.new_chat_member.status == "kicked":
                cur.execute("UPDATE users SET block = 1 WHERE user_id = '{}'".format(str(tg.from_user.id)))
                async with state.proxy() as data: # зачищаем state у данного юзера
                    for k, v in dict(data).items():
                        data.pop(k)
                if module_main == 'davinci':
                    await module.davinci.davinci_delete(tg.from_user.id)
                info_block = "count_block + 1"
            elif tg.new_chat_member.status == "member":
                cur.execute("UPDATE users SET block = 0 WHERE user_id = '{}'".format(str(tg.from_user.id)))
                info_block = "count_block - 1"
            # запись в модуль info
            if 'info' in modules:
                cur.execute("UPDATE info SET count_block = {} WHERE date_write = '{}'".format(info_block, str(user['date_write'])))
        elif tg.chat.type in ['supergroup', 'group', "channel"]: # добавили/удалили бота в группу
            chat_type = tg.chat.type
            if chat_type == 'supergroup':
                chat_type = 'group'
            chat = tg.chat
            if tg.new_chat_member.status == "left":
                try:
                    cur.execute("DELETE FROM chats WHERE chat_id = '{}'".format(chat.id))
                except Exception as ex:
                    pass
            elif tg.new_chat_member.status in ["member", "administrator"]:
                cur.execute("SELECT COUNT(*) FROM chats WHERE chat_id = '{}'".format(chat.id))
                if not cur.fetchall()[0]['count']:
                    chat_username = ''
                    if 'username' in chat:
                        chat_username = chat.username
                    cur.execute("INSERT INTO chats (types, chat_id, chat_username, chat_title, status) VALUES (%s, %s, %s, %s, %s)", [chat_type, chat.id, chat_username, chat.title, tg.new_chat_member.status])
                else:
                    cur.execute("UPDATE chats SET chat_title = '{}', status = '{}' WHERE chat_id = '{}'".format(chat.title, tg.new_chat_member.status, chat.id))
                # если админ сохраняем права бота в группе
                if tg.new_chat_member.status == "administrator":
                    allowed = []
                    allowed_dict = dict(tg.new_chat_member)
                    for key, val in allowed_dict.items():
                        if val == True:
                            allowed.append(key)
                    if not allowed:
                        allowed = ''
                    else:
                        allowed = str(allowed).replace("'", '"')
                    cur.execute("UPDATE chats SET allowed = '{}' WHERE chat_id = '{}'".format(allowed, chat.id))
                else:
                    cur.execute("UPDATE chats SET allowed = '' WHERE chat_id = '{}'".format(chat.id))
            # дополнительные действия модуля
            if tg.chat.type in ['supergroup', 'group']:
                if module_main == 'sea':
                    await module.sea.sea_group_add(tg)
                elif 'antiSpam' in modules:
                    await module.antiSpam.antiSpam_group_add(tg)

# вызов бота в строке через @name_bot, не забыть включить функцию inline в @BotFather у бота
@dp.inline_handler()
async def inline_handler(tg: InlineQuery, state: FSMContext) -> None:
    # не забыть включить функцию inline в @BotFather у бота
    if module_main == 'bot':
        await module.bot.bot_inline(tg, state)
    elif module_main == 'sea':
        await module.sea.sea_inline(tg, state)



# callback
@dp.callback_query_handler(state='*')
async def why_callback(tg: types.CallbackQuery, state: FSMContext):
    save = await saver()
    print(f'WHY?????????? {tg}')



if __name__ == '__main__':
    # https://core.telegram.org/bots/api#update
    allowed_updates = [
        'message',
        # 'channel_post',
        'inline_query',
        'callback_query',
        'my_chat_member',
        # 'poll',
        # 'poll_answer',
        'chat_member',
        'chat_join_request'
    ]
    executor.start_polling(dp, on_startup=on_startup, allowed_updates=allowed_updates) # skip_updates=True пропуск сообщений


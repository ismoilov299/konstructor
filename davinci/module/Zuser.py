from copy import deepcopy

from function import *
import module

# start
async def Zuser_start(tg, state):
    save = await saver()
    if 'op' not in modules: # обычный бот без ОП
        await module_go(tg, state)
    else: # бот с модулем ОП
        if int(save['setting']['start_message_startShow']):
            async with state.proxy() as data:
                if 'referal' in data:
                    referal = data['referal']
            if 'referal' in locals() and 'valentine' in modules:
                page = {'page': 'go', 'module': 'valentine', 'param': '', 'param_2': '', 'param_3': ''}
                await module.valentine.valentine_dop(tg, state, page)
            else:
                m = {0: {}}
                memory = await memory_start(state, load_memory=False)
                m[0] = await show_message_from_setting('start', tg)
                m[0]['but'] = [[{'text': save["setting"]['start_message_keyb'], 'callback_data': "op_go_notCheck"}]]
                page = {'page': 'start', 'module': 'start', 'param': '', 'param_2': '', 'param_3': ''}
                await memory_finish(tg, state, memory, page, m)
        elif int(save['setting']['op_message_startShow']):
            if await module.op.op_check_FULL(tg, state):
                await module_go(tg, state)
        else:
            await module_go(tg, state)




# чтоб прыгать между модулями
async def module_go(tg, state):
    page = 'go'
    mod = deepcopy(module_main)
    z1 = mod
    z2 = ''
    async with state.proxy() as data:
        if 'op' in modules:
            pass
            # user_op_save_page сюда сохранили страницу с которой прилетел так как не подписан на ОП
            # если эта переменная есть то возвращаем юзера именно на нее
            # if 'user_op_save_page' in data:
            #     z2 = data['user_op_save_page']
            #     full_page = data['user_op_save_page'].split('_')
            #     if len(full_page) >= 2:
            #         mod = full_page[0]
            #         page = full_page[1]
        # если есть бесплатная выдача VIP на старте и это не анон бот (так как там сначала анкета)
        if 'payTime' in modules and mod not in ['anon']:
            if 'payTimeFree' in data:
                await module.payTime.startVipFree_message(tg, state)
    if mod == 'bot':
        await module.bot.bot_dop(tg, state, {'module': 'bot', 'page': page})
    elif mod == 'oneMessage':
        await module.oneMessage.oneMessage_dop(tg, state, {'module': 'oneMessage', 'page': page})
    elif mod == 'kino':
        await module.kino.kino_dop(tg, state, {'module': 'kino', 'page': page})
    elif mod == 'davinci':
        await module.davinci.davinci_dop(tg, state, {'module': 'davinci', 'page': page})
    elif mod == 'anon':
        await module.anon.anon_dop(tg, state, {'module': 'anon', 'page': page})
    elif mod == 'rating':
        await module.rating.rating_dop(tg, state, {'module': 'rating', 'page': page})
    elif mod == 'valentine':
        await module.valentine.valentine_dop(tg, state, {'module': 'valentine', 'page': page})
    elif mod == 'clicker':
        await module.clicker.clicker_dop(tg, state, {'module': 'clicker', 'page': page})
    elif mod == 'magic':
        await module.magic.magic_dop(tg, state, {'module': 'magic', 'page': page})
    elif mod == 'font':
        await module.font.font_dop(tg, state, {'module': 'font', 'page': page})
    elif mod == 'book':
        await module.book.book_dop(tg, state, {'module': 'book', 'page': page})
    elif mod == 'background':
        await module.background.background_dop(tg, state, {'module': 'background', 'page': page})
    elif mod == 'sticker':
        await module.sticker.sticker_dop(tg, state, {'module': 'sticker', 'page': page})
    elif mod == 'theme':
        await module.theme.theme_dop(tg, state, {'module': 'theme', 'page': page})
    elif mod == 'emoji':
        await module.emoji.emoji_dop(tg, state, {'module': 'emoji', 'page': page})
    elif mod == 'button':
        await module.button.button_dop(tg, state, {'module': 'button', 'page': 'show'})
    elif mod == 'sea':
        await module.sea.sea_dop(tg, state, {'module': 'sea', 'page': page})
    elif mod == 'kinoFilms':
        await module.kinoFilms.kinoFilms_dop(tg, state, {'module': 'kinoFilms', 'page': page})
    else:
        await bot.send_message(chat_id=tg.from_user.id, text="Спасибо, что подписались на наши каналы!")
        # global module_main
        print(f'!! Модуль идеи отсутствует в боте, mod = {mod} | {z1} | {z2}')

async def Zuser_message(message):
    pass
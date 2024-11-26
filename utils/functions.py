import os
import re
from typing import Union, Optional

from aiogram import methods, types

from config import MEDIA_ROOT


def get_call_method(message: Union[dict, types.Message], reply_markup: Optional[types.InlineKeyboardMarkup] = None):
    if isinstance(message, dict):
        message = types.Message(**message)
    if message.content_type == "text":
        obj = message.text
        call = methods.SendMessage
    elif message.content_type == "photo":
        obj = message.photo[-1].file_id
        call = methods.SendPhoto
    elif message.content_type == "audio":
        obj = message.audio.file_id
        call = methods.SendAudio
    elif message.content_type == "video":
        obj = message.video.file_id
        call = methods.SendVideo
    elif message.content_type == "video_note":
        obj = message.video_note.file_id
        call = methods.SendVideoNote
    elif message.content_type == "voice":
        obj = message.voice.file_id
        call = methods.SendVoice
    elif message.content_type == _:
        return
    kwargs = {
        message.content_type: obj,
        "caption": message.caption,
        "caption_entities": message.caption_entities,
        "reply_markup": reply_markup or message.reply_markup
    }

    def inner_func(chat_id: int):
        kwargs["chat_id"] = chat_id
        return call(**kwargs)

    return inner_func


"""
Все пользователи: 
Пользователи основного бота: 
Ботов: 
Новые пользователи: 
Заработано всего: 
Прибыль(Сегодня): 
Заказов за сегодня:
"""

URL_PATTERN = re.compile(r'(https?:\/\/(?:www\.|(?!www))[a-zA-Z0-9][a-zA-Z0-9-]+[a-zA-Z0-9]\.[^\s]{2,}|'
                         r'www\.[a-zA-Z0-9][a-zA-Z0-9-]+[a-zA-Z0-9]\.[^\s]{2,}|https?:\/\/(?:www\.|(?!www))'
                         r'[a-zA-Z0-9]+\.[^\s]{2,}|www\.[a-zA-Z0-9]+\.[^\s]{2,})')


def check_url(url: str):
    if not url.startswith("http"):
        url = "https://" + url
    if URL_PATTERN.match(url):
        return True
    return False


def create_folder_if_not_exists(folder_path: str):
    folder_full_path = os.path.join(MEDIA_ROOT, folder_path)
    if not os.path.exists(folder_full_path):
        os.makedirs(folder_full_path)
    return folder_full_path

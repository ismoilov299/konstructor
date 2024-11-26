from datetime import datetime, timedelta
import logging

from aiogram.fsm.state import State
from apscheduler.triggers.interval import IntervalTrigger
from modul.config import scheduler
from modul.clientbot.handlers.leomatch.shortcuts import get_distinkt_likes, get_likes_count
from modul.clientbot.handlers.leomatch.keyboards.reply_kb import yes_no
from modul.clientbot import strings, shortcuts
from modul.clientbot.handlers.leomatch.data.state import LeomatchProfiles
from modul.loader import bot_session
# from modul.helpers.functions import send_message
from asyncio import Lock
from modul import models
import yt_dlp
from django.db.models import F
from django.utils import timezone
from django.db import transaction
from asgiref.sync import sync_to_async
from aiogram import Bot
from aiogram.types import URLInputFile

logger = logging.getLogger()

lock = Lock()


async def leo_alert_likes(bot):
    async with Lock():
        leos = await get_distinkt_likes()
        for leo in leos:
            user: models.LeoMatchModel = await leo.to_user
            client: models.User = await user.user
            count = await get_likes_count(client.uid)
            if count > 0:
                bot_db = await shortcuts.get_bot_by_username(user.bot_username)
                async with Bot(token=bot_db.token, session=bot_session).context(auto_close=False) as bot:
                    state = shortcuts.get_fsm_context(bot, client.uid)
                    current_state_str = await state.get_state()
                    if isinstance(current_state_str, str):
                        state_info = current_state_str.split(":")
                        current_state = State(state_info[1], state_info[0])
                    else:
                        current_state = State()

                    if current_state.state != LeomatchProfiles.MANAGE_LIKES.state:
                        if not current_state_str:
                            await bot.send_message(client.uid,
                                                   ("Вам поставили лайк! ({count} шт.), показать их?").format(
                                                       count=count),
                                                   reply_markup=yes_no())
                            await state.set_state(LeomatchProfiles.MANAGE_LIKES)
                        else:
                            if count != user.count_likes:
                                try:
                                    await bot.send_message(client.uid,
                                                           (
                                                               "У вас новый лайк! ({count} шт.) После завершения текущего дела, проверьте, кому вы понравились, нажав /start и подождав следующее уведомление.").format(
                                                               count=count))
                                    user.count_likes = count
                                    await user.save()
                                except Exception as e:
                                    pass


@sync_to_async
def get_and_delete_task():
    with transaction.atomic():
        task = models.TaskModel.objects.select_related('client').first()
        if task:
            task_id = task.id
            task_copy = models.TaskModel.objects.filter(id=task_id).get()
            models.TaskModel.objects.filter(id=task_id).delete()
            print(task_copy)
            return task_copy
    return None

@sync_to_async
def update_download_analytics(bot_username, domain):
    from modul.models import DownloadAnalyticsModel  # Импорт здесь во избежание циклических импортов
    analytics, created = DownloadAnalyticsModel.objects.get_or_create(
        bot_username=bot_username,
        domain=domain,
        date__date=timezone.now().date()
    )
    DownloadAnalyticsModel.objects.filter(id=analytics.id).update(count=F('count') + 1)


async def task_runner():
    while True:
        task = await get_and_delete_task()
        if not task:
            break

        client = task.client
        bot = client.bot
        print(client.uid, task.task_type)

        if task.task_type == models.TaskTypeEnum.DOWNLOAD_MEDIA:
            url = task.data['url']
            async with Bot(bot.token, session=bot_session).context(auto_close=False) as bot_:
                await bot_.send_chat_action(client.uid, "upload_video")
                ydl_opts = {
                    'cachedir': False,
                    'noplaylist': True,
                    'outtmpl': 'clientbot/downloads/%(title)s.%(ext)s',
                    'format': 'bestvideo[ext=mp4]+bestaudio[ext=mp3]/best[ext=mp4]/best',
                }
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    try:
                        info = ydl.extract_info(url, download=False)
                        await bot_.send_video(client.uid, URLInputFile(info['url']), supports_streaming=True)

                        # Обновляем аналитику
                        domain = info.get('webpage_url_domain', 'unknown')
                        await update_download_analytics(bot.username, domain)
                    except Exception as e:
                        await bot_.send_message(client.uid, f"Не удалось скачать это видео: {e}")


lock_file = 'apscheduler.lock'

# scheduler.add_job(leo_alert_likes, trigger=IntervalTrigger(minutes=1), coalesce=True, max_instances=25)
# scheduler.add_job(horoscope_everyday, trigger=CronTrigger(hour=0, minute=0), coalesce=True, max_instances=1, replace_existing=False, misfire_grace_time=60)

# scheduler.add_job(task_runner, trigger=IntervalTrigger(seconds=10), max_instances=25)

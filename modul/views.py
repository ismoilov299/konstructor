import hashlib
import hmac
import json
import logging
import ssl
import time

import requests
from aiohttp import TCPConnector
from django import forms
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db.models import Count
from django.db.models.functions import TruncMonth
from django.forms import ModelForm
from django.shortcuts import render, redirect, get_object_or_404
from django.conf import settings
from django.contrib.auth import login, logout
from django.contrib.auth import get_user_model
from django.http import JsonResponse, HttpResponse
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify
from django.views.decorators.csrf import csrf_exempt
import aiohttp
import asyncio
from .loader import bot_session
from .models import Bot, ClientBotUser, UserTG
from django.views.decorators.http import require_POST
from urllib.parse import urlencode
from .crud import crud_bot
from .config import settings_conf
from aiogram import Bot as Bot_aiogram


def index(request):
    if request.user.is_authenticated:
        return redirect('main')
    return render(request, 'DxBot/index.html')


def web_main(request):
    if request.user.is_authenticated:
        try:
            current_date = timezone.now().date()
            first_day_of_current_month = current_date.replace(day=1)

            user_tg = request.user.tg_profile
            user_data = UserTG.objects.filter(
                id=user_tg.id,
                created_at__lt=first_day_of_current_month
            ).annotate(
                month=TruncMonth('created_at')
            ).values('month').annotate(
                count=Count('id')
            ).order_by('month')

            user_data_count = UserTG.objects.filter(
                id=user_tg.id,
                interaction_count__gt=1
            ).annotate(
                month=TruncMonth('created_at')
            ).values('month').annotate(
                count=Count('id')
            ).order_by('month')

            formatted_user_data = [
                {'month': item['month'].strftime('%Y-%m-%d'), 'count': item['count']}
                for item in user_data
            ]
            formatted_user_data_count = [
                {'month': item['month'].strftime('%Y-%m-%d'), 'count': item['count']}
                for item in user_data_count
            ]

            context = {
                'user_data': json.dumps(formatted_user_data),
                'user_data_count': json.dumps(formatted_user_data_count),
            }
            return render(request, 'admin-wrap-lite-master/html/index.html', context)
        except Exception as e:
            logger.error(f"Error getting user data: {str(e)}")
            # Show an error message to the user or handle the exception in another way
    return redirect('index')


def profile(request):
    if not request.user.is_authenticated:
        return render(request, 'DxBot/index.html')
    return render(request, 'admin-wrap-lite-master/html/pages-profile.html')


def create_bot(request):
    if not request.user.is_authenticated:
        return render(request, 'DxBot/index.html')
    try:
        all_user_bot = Bot.objects.filter(owner=request.user).all()

        context = {
            'all_user_bot': all_user_bot
        }
        return render(request, 'admin-wrap-lite-master/html/create_bot.html', context)
    except Exception as e:
        raise e


def get_bot_info(request, id):
    try:
        bot = Bot.objects.get(owner=request.user, id=id)

        module = "no_module"
        if bot.enable_leo:
            module = 'leo'
        elif bot.enable_refs:
            module = 'refs'
        elif bot.enable_kino:
            module = 'kino'
        elif bot.enable_chatgpt:
            module = 'chatgpt'
        elif bot.enable_anon:
            module = 'anon'
        elif bot.enable_download:
            module = 'download'

        bot_info = {
            'token': bot.token,
            'module': module,
            'is_enabled': bot.bot_enable,
            'username': bot.username
        }
        return JsonResponse(bot_info)
    except Bot.DoesNotExist:
        return JsonResponse({'error': 'Bot not found'}, status=404)


def error_404(request):
    return render(request, 'admin-wrap-lite-master/html/pages-error-404.html')


def get_bot_username(bot_token):
    url = f"https://api.telegram.org/bot{bot_token}/getMe"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            if data['ok']:
                bot_username = data['result']['username']
                return bot_username
            else:
                logger.error(f"Error getting bot username: {data['description']}")
        else:
            logger.error(f"Failed to connect to Telegram API.")
    except Exception as e:
        logger.error(f"Error getting bot username: {str(e)}")
    return None


logger = logging.getLogger(__name__)


class BotForm(ModelForm):
    MODULE_CHOICES = [
        ('no_module', 'Нет модуля'),
        ('leo', 'Дайвинчик'),
        ('refs', 'Реферальный бот'),
        ('kino', 'Кино бот'),
        ('download', 'All save бот'),
        ('anon', 'Аноним чат бот'),
        ('chatgpt', 'ChatGPT бот'),
    ]
    module = forms.ChoiceField(choices=MODULE_CHOICES, required=True)

    class Meta:
        model = Bot
        fields = ['token', 'module']

    def clean_token(self):
        token = self.cleaned_data['token']
        try:
            Bot.objects.get(token=token)
            raise ValidationError('Токен уже существует.')
        except Bot.DoesNotExist:
            return token


async def set_webhook_async(token, url):
    telegram_url = f"https://api.telegram.org/bot{token}/setWebhook"

    async with aiohttp.ClientSession(connector=TCPConnector(ssl=False)) as session:
        async with session.post(telegram_url,
                                json={'url': url, 'allowed_updates': settings_conf.USED_UPDATE_TYPES}) as response:
            return await response.json()


@login_required
@csrf_exempt
@require_POST
def save_token(request):
    form = BotForm(request.POST)
    if form.is_valid():
        token = form.cleaned_data['token']
        module = form.cleaned_data['module']
        try:
            bot_username = get_bot_username(token)
            url = settings_conf.WEBHOOK_URL.format(token=token)

            # Create Bot object with selected module
            bot = Bot(
                token=token,
                owner=request.user,
                username=bot_username,
                enable_leo=module == 'leo',
                enable_refs=module == 'refs',
                enable_kino=module == 'kino',
                enable_download=module == 'download',
                enable_anon=module == 'anon',
                enable_chatgpt=module == 'chatgpt',
            )

            # Установка вебхука
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                response = loop.run_until_complete(set_webhook_async(token, url))
                loop.close()

                if response.get('ok'):
                    bot.save()
                    logger.info(f"Bot token {token} saved successfully with webhook {url}.")
                    print(f"Bot token {token} saved successfully with webhook {url}.")
                    return redirect('create_bot')
                else:
                    bot.delete()
                    error_message = response.get('description', 'Unknown error occurred')
                    logger.error(f"Error setting webhook for bot {bot_username}: {error_message}")
                    return JsonResponse({'status': 'error', 'message': f"Failed to set webhook: {error_message}"})

            except Exception as e:
                bot.delete()  # Удаляем запись, если не удалось установить вебхук
                logger.error(f"Error setting webhook for bot {bot_username}: {e}")
                return JsonResponse({'status': 'error', 'message': f"Failed to set webhook: {str(e)}"})

        except ValidationError as e:
            logger.error(f"Invalid token {token}: {e}")
            return JsonResponse({'status': 'error', 'message': f"Invalid token: {str(e)}"})

    else:
        logger.error(f"Invalid form submission: {form.errors}")
        return JsonResponse({'status': 'error', 'message': 'Invalid form submission.', 'errors': form.errors})

    return HttpResponseBadRequest("Invalid request method. Use POST.")


async def delete_webhook_async(token):
    telegram_url = f"https://api.telegram.org/bot{token}/deleteWebhook"
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    async with aiohttp.ClientSession() as session:
        async with session.post(telegram_url, ssl=ssl_context) as response:
            return await response.json()


@login_required
@csrf_exempt
@require_POST
def toggle_bot(request):
    bot_token = request.POST.get('bot_token')
    action = request.POST.get('action')  # 'on' or 'off'

    bot = get_object_or_404(Bot, token=bot_token, owner=request.user)

    if action == 'off':
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            response = loop.run_until_complete(delete_webhook_async(bot_token))
            loop.close()

            if response.get('ok'):
                bot.bot_enable = False
                bot.save()
                return JsonResponse({'status': 'success', 'message': 'Bot disabled', 'new_status': 'off'})
            else:
                return JsonResponse(
                    {'status': 'error', 'message': f'Error disabling bot: {response.get("description")}'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f'Error disabling bot: {str(e)}'})
    # On action is handled in the original code
    else:
        return JsonResponse({'status': 'error', 'message': 'Invalid action. Please try again'})

@login_required
@csrf_exempt
@require_POST
def delete_bot(request):
    bot_token = request.POST.get('bot_token')

    bot = get_object_or_404(Bot, token=bot_token, owner=request.user)

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        response = loop.run_until_complete(delete_webhook_async(bot_token))
        loop.close()

        if response.get('ok'):
            bot.delete()
            return JsonResponse({'status': 'success', 'message': 'Бот успешно удален'})
        else:
            return JsonResponse(
                {'status': 'error', 'message': f'Ошибка при удалении вебхука: {response.get("description")}'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': f'Ошибка при удалении бота: {str(e)}'})


User = get_user_model()


def telegram_login(request):
    telegram_id = request.GET.get('id')
    first_name = request.GET.get('first_name')
    last_name = request.GET.get('last_name')
    username = request.GET.get('username')
    # try:
    #     photo_url = request.GET.get('photo_url')
    #     telegram_image_url = photo_url
    # except:
    #     pass

    if not telegram_id:
        return redirect('index')  # Если нет ID, перенаправляем на обычную страницу логина

    user, created = User.objects.get_or_create(uid=telegram_id)

    if created:
        user.username = username or str(telegram_id)  # Генерация имени пользователя, если его нет
        user.first_name = first_name
        user.last_name = last_name
        user.save()
    # saved_image = save_telegram_image(telegram_image_url)

    login(request, user)  # Авторизация пользователя
    return redirect('profile')  # Перенаправление на главную страницу после логина


def send_message_to_restart(bot_token, owner_id):
    base_url = f"https://api.telegram.org/bot{bot_token}"
    # url = f"https://api.telegram.org/bot7397326527:AAHZTPHh5xanjTM9wSMcZYQZV9Tuo8A-0WQ/sendMessage"

    send_message_url = f"{base_url}/sendMessage"
    # Параметры
    payload = {
        "chat_id": owner_id,
        "text": "Отправьте команду /start для перезапуска бота"
    }
    print(send_message_url)

    response = requests.post(send_message_url, data=payload)

    if response.status_code == 200:
        return True
    return False


@login_required
@csrf_exempt
@require_POST
def update_bot_settings(request):
    if request.method == 'POST':
        bot_token = request.POST.get('bot_token')
        module = request.POST.get('module')

        bot = get_object_or_404(Bot, token=bot_token, owner=request.user)

        # Обновляем настройки бота в зависимости от выбранного модуля

        enable_module = f'enable_{module}'
        print(enable_module)
        bot.enable_music = False
        bot.enable_download = False
        bot.enable_leo = False
        bot.enable_chatgpt = False
        bot.enable_horoscope = False
        bot.enable_anon = False
        bot.enable_sms = False
        bot.enable_refs = False
        bot.enable_kino = False

        if not hasattr(bot, enable_module):
            bot.save()
            print(bot, "no module")
            return JsonResponse({'status': 'error', 'message': 'Нет модуля'})

        if hasattr(bot, enable_module):
            setattr(bot, enable_module, not getattr(bot, enable_module))
            bot.save()
            send_message_to_restart(bot_token, request.user.uid)

            new_state = getattr(bot, enable_module)
            print(bot, new_state)
            return JsonResponse({'status': 'success', 'enabled': new_state, "module": module})
        else:
            return JsonResponse({'status': 'error', 'message': 'Неверный модуль'}, status=400)

    return JsonResponse({'status': 'error', 'message': 'Метод не поддерживается'}, status=405)


def statistics_view(request):
    user = request.user
    user_tg = user.tg_profile
    # Получаем данные о пользователях по месяцам
    user_data = UserTG.objects.filter(id=user_tg.id).annotate(
        month=TruncMonth('created_at')
    ).values('month').annotate(
        count=Count('id')
    ).order_by('month')

    user_data_count = UserTG.objects.filter(
        id=user_tg.id,
        interaction_count__gt=1
    ).annotate(
        month=TruncMonth('created_at')
    ).values('month').annotate(
        count=Count('id')
    ).order_by('month')

    context = {
        'user_data': list(user_data),
        'user_data_count': list(user_data_count),
    }

    return render(request, 'admin-wrap-lite-master/html/index.html', context)


def logout_view(request):
    logout(request)
    return redirect(reverse('index'))

import hashlib
import hmac
import json
import logging
import ssl
import requests
from aiohttp import TCPConnector
from django import forms
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db.models import Count
from django.db.models.functions import TruncMonth
from django.forms import ModelForm
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth import get_user_model
from django.http import JsonResponse, HttpResponse
from django.urls import reverse

from django.views.decorators.csrf import csrf_exempt
import aiohttp
import asyncio
from .models import Bot, ClientBotUser, UserTG
from django.views.decorators.http import require_POST

from .config import settings_conf


def index(request):
    if request.user.is_authenticated:
        return redirect('main')
    return render(request, 'DxBot/index.html')


def web_main(request):
    if request.user.is_authenticated:
        try:
            user_data = UserTG.objects.filter(
                id=request.user.uid
            ).annotate(
                month=TruncMonth('created_at')
            ).values('month').annotate(
                count=Count('id')
            ).order_by('month')

            formatted_data = [
                {
                    'month': item['month'].strftime('%Y-%m-%d'),
                    'count': item['count']
                } for item in user_data
            ]

            print("Debug - formatted_data:", formatted_data)  # Debug log

            context = {
                'user_data': json.dumps(formatted_data),
                'user_data_count': json.dumps([])  # Empty array as default
            }
            return render(request, 'admin-wrap-lite-master/html/index.html', context)

        except Exception as e:
            print("Error in web_main:", str(e))
            context = {
                'user_data': json.dumps([]),
                'user_data_count': json.dumps([])
            }
            return render(request, 'admin-wrap-lite-master/html/index.html', context)

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


@login_required
def get_bot_info(request, id):
    try:
        bot = get_object_or_404(Bot, id=id, owner=request.user)

        # Get active module
        module_mapping = {
            'enable_leo': 'leo',
            'enable_refs': 'refs',
            'enable_kino': 'kino',
            'enable_download': 'download',
            'enable_anon': 'anon',
            'enable_chatgpt': 'chatgpt',
            'enable_music': 'music',
            'enable_sms': 'sms',
            'enable_horoscope': 'horoscope',
            'enable_davinci': 'davinci'
        }

        active_module = 'no_module'
        for model_field, frontend_value in module_mapping.items():
            if getattr(bot, model_field):
                active_module = frontend_value
                break

        return JsonResponse({
            'status': 'success',
            'token': bot.token,
            'username': bot.username,
            'is_enabled': bot.bot_enable,
            'module': active_module
        })
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        })


def error_404(request):
    return render(request, 'admin-wrap-lite-master/html/pages-error-404.html')


def get_bot_username(bot_token):
    url = f"https://api.telegram.org/bot{bot_token}/getMe"
    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()
        if data['ok']:
            bot_username = data['result']['username']
            return bot_username
        else:
            print("Error:", data['description'])
    else:
        print("Failed to connect to Telegram API.")


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
        ('davinci', 'Davinci бот')
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

            # Bot obyektini yaratamiz, lekin hali saqlamaymiz
            bot = Bot(
                token=token,
                owner=request.user,
                username=bot_username,
                enable_leo=module == 'leo',
                enable_davinci=module == 'davinci',
                enable_refs=module == 'refs',

                enable_kino=module == 'kino',

                enable_download=module == 'download',
                enable_anon=module == 'anon',
                enable_chatgpt=module == 'chatgpt',



            )

            try:
                # Webhook o'rnatish
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                response = loop.run_until_complete(set_webhook_async(token, url))
                loop.close()

                if response.get('ok'):
                    # Webhook muvaffaqiyatli o'rnatilgandan keyin botni saqlaymiz
                    bot.save()
                    logger.info(f"Bot token {token} saved successfully with webhook {url}.")
                    # AJAX so'rov uchun JsonResponse qaytaramiz
                    return JsonResponse({
                        'status': 'success',
                        'message': 'Bot successfully created'
                    })
                else:
                    error_message = response.get('description', 'Unknown error occurred')
                    logger.error(f"Error setting webhook for bot {bot_username}: {error_message}")
                    return JsonResponse({
                        'status': 'error',
                        'message': f"Failed to set webhook: {error_message}"
                    })

            except Exception as e:
                logger.error(f"Error setting webhook for bot {bot_username}: {e}")
                return JsonResponse({
                    'status': 'error',
                    'message': f"Failed to set webhook: {str(e)}"
                })

        except ValidationError as e:
            logger.error(f"Invalid token {token}: {e}")
            return JsonResponse({
                'status': 'error',
                'message': f"Invalid token: {str(e)}"
            })

    logger.error(f"Invalid form submission: {form.errors}")
    return JsonResponse({
        'status': 'error',
        'message': 'Invalid form data',
        'errors': form.errors
    })


async def delete_webhook_async(token):
    telegram_url = f"https://api.telegram.org/bot{token}/deleteWebhook"
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    async with aiohttp.ClientSession() as session:
        async with session.post(telegram_url, ssl=ssl_context) as response:
            return await response.json()


@login_required
@require_POST
def toggle_bot(request):
    try:
        data = json.loads(request.body)
        bot_token = data.get('bot_token')
        action = data.get('action')

        if not bot_token or action not in ['on', 'off']:
            return JsonResponse({
                'status': 'error',
                'message': 'Неверные параметры'
            })

        bot = get_object_or_404(Bot, token=bot_token, owner=request.user)
        bot.bot_enable = (action == 'on')
        bot.save()

        send_message_to_restart(bot_token, request.user.uid)

        return JsonResponse({
            'status': 'success',
            'is_enabled': bot.bot_enable
        })
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        })


@login_required
@require_POST
def delete_bot(request):
    try:
        data = json.loads(request.body)
        bot_token = data.get('bot_token')

        if not bot_token:
            return JsonResponse({
                'status': 'error',
                'message': 'Не указан токен бота'
            })

        bot = get_object_or_404(Bot, token=bot_token, owner=request.user)
        bot.delete()

        return JsonResponse({
            'status': 'success'
        })
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        })


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

@csrf_exempt
@login_required
@require_POST
def update_bot_settings(request):
    try:
        bot_token = request.POST.get('bot_token')
        module = request.POST.get('module')

        if not bot_token or not module:
            return JsonResponse({
                'status': 'error',
                'message': 'Не указан токен бота или модуль'
            })

        bot = get_object_or_404(Bot, token=bot_token, owner=request.user)

        # Reset all module flags
        module_flags = [
            'enable_music', 'enable_download', 'enable_leo',
            'enable_chatgpt', 'enable_horoscope', 'enable_anon',
            'enable_sms', 'enable_refs', 'enable_kino','enable_davinci'
        ]

        for flag in module_flags:
            setattr(bot, flag, False)

        # Map frontend module values to model fields
        module_mapping = {
            'leo': 'enable_leo',
            'refs': 'enable_refs',
            'kino': 'enable_kino',
            'download': 'enable_download',
            'anon': 'enable_anon',
            'chatgpt': 'enable_chatgpt',
            'davinci': 'enable_davinci'
        }

        if module != 'no_module':
            module_field = module_mapping.get(module)
            if module_field:
                setattr(bot, module_field, True)
            else:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Неизвестный модуль'
                })

        bot.save()
        send_message_to_restart(bot_token, request.user.uid)

        return JsonResponse({
            'status': 'success',
            'module': module
        })

    except Bot.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': 'Бот не найден'
        })
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        })


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

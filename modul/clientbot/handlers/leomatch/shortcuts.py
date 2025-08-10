import traceback
from dataclasses import dataclass

from aiogram.types import ReplyKeyboardMarkup, FSInputFile
from django.core.files import File
from django.db.models import Q, F
import os
from modul.models import LeoMatchLikesBasketModel, SexEnum, User, LeoMatchModel, MediaTypeEnum, UserTG
from aiogram import Bot, types
from modul.clientbot.shortcuts import get_bot_by_username, get_current_bot
from modul.clientbot.handlers.leomatch.keyboards.inline_kb import write_profile
from modul.clientbot import shortcuts
from modul.config import settings_conf
from modul.loader import bot_session
from asgiref.sync import sync_to_async
from django.db import transaction

@sync_to_async
def get_client(uid: int):
    try:
        user = UserTG.objects.filter(uid=uid).first()
        print(f"Trying to get user with uid {uid}. Result: {user}")
        if user is None:
            print(f"No UserTG found with uid {uid}")
        return user
    except Exception as e:
        print(f"Error in get_client for uid {uid}: {str(e)}")
        return None




@sync_to_async
def get_leo_match(user):
    print(LeoMatchModel.objects.filter(user=user).first())
    return LeoMatchModel.objects.filter(user=user).first()


async def get_leo(uid: int):
    from asgiref.sync import sync_to_async

    @sync_to_async
    def get_leo_sync():
        try:
            print(f"DEBUG: get_leo_sync called with uid: {uid}")
            # 1. UserTG topish
            user = UserTG.objects.filter(uid=str(uid)).first()
            if not user:
                print(f"DEBUG: UserTG not found for uid: {uid}")
                return None

            print(f"DEBUG: Found UserTG: {user}, id: {user.id}")

            # 2. LeoMatchModel topish user_id orqali
            leo = LeoMatchModel.objects.filter(user_id=user.id).first()
            print(f"DEBUG: Found LeoMatchModel: {leo}")

            return leo
        except Exception as e:
            print(f"DEBUG: Error in get_leo_sync: {e}")
            return None

    return await get_leo_sync()

# async def get_leo(uid: int):
#     user = await get_client(uid)
#     if user:
#         leo = await get_leo_match(user)
#         return leo
#     return None


@sync_to_async
def filter_leos_sync(kwargs, age_range, sex, leo_me_id):
    return LeoMatchModel.objects.filter(
        blocked=False,
        age__range=age_range,
        search=True,
        active=True,
        **kwargs
    ).exclude(
        Q(which_search__in=[sex, SexEnum.ANY.value]) | Q(id=leo_me_id)
    ).order_by('?')[:50]  # '?' belgisi tasodifiy tartibda qaytarish uchun

@sync_to_async
def get_user_uid_sync(leo):
    return leo.user.uid



async def get_leos_id(me: int):
    try:
        leo_me = await get_leo(me)
        if not leo_me:
            return []

        kwargs = {}
        if leo_me.which_search != SexEnum.ANY.value:
            kwargs['sex'] = leo_me.which_search

        @sync_to_async
        def filter_leos_sync(kwargs, my_sex, my_id):
            return list(LeoMatchModel.objects.filter(
                Q(active=True) &
                Q(search=True) &
                Q(**kwargs) &
                ~Q(id=my_id)
            ).select_related('user'))

        leos = await filter_leos_sync(kwargs, leo_me.sex, leo_me.id)

        users_id = []
        for leo in leos:
            try:
                users_id.append(leo.user.uid)
            except Exception as e:
                print(f"Error getting user_uid for leo {leo.id}: {e}")
                continue

        return users_id

    except Exception as e:
        print(f"Error in get_leos_id: {e}")
        return []


async def exists_leo(uid: int):
    return await get_leo(uid) is not None


@sync_to_async
def create_leomatch(user_tg, photo, media_type, sex, age, full_name, about_me, city, which_search, bot_username):
    print(f"Creating LeoMatch for user: {user_tg}")
    if user_tg is None:
        raise ValueError("UserTG object is None.")

    if not hasattr(user_tg, 'uid') or user_tg.uid is None:
        raise ValueError(f"UserTG object does not have a valid 'uid' attribute. User: {user_tg}")

    if user_tg.user is None:
        django_user = User.objects.create(
            username=f"tg_user_{user_tg.uid}",
            first_name=user_tg.first_name or full_name,
            last_name=user_tg.last_name or "",
        )
        user_tg.user = django_user
        user_tg.save()
    else:
        django_user = user_tg.user

    return LeoMatchModel.objects.create(
        user=django_user,  # Bu yerda modul.User obyektini beramiz
        photo=photo,
        media_type=media_type,
        sex=sex,
        age=age,
        full_name=full_name,
        about_me=about_me,
        city=city,
        which_search=which_search,
        bot_username=bot_username
    )


async def add_leo(uid: int, photo: str, media_type: str, sex: str, age: int, full_name: str, about_me: str, city: str,
                  which_search: str, bot_username: str):
    try:
        client = await get_client(uid)

        if client is None:
            print(f"Creating new UserTG for uid {uid}")
            client = await UserTG.objects.acreate(uid=uid)

        print(f"Client for LeoMatch creation: {client}")

        info = await create_leomatch(client, photo, media_type, sex, age, full_name, about_me, city, which_search,
                                     bot_username)
        return info
    except Exception as e:
        print(f"Error in add_leo for uid {uid}: {str(e)}")
        raise


@sync_to_async
def save_model_sync(model):
    model.save()


@sync_to_async
def update_leo(uid, photo, media_type, sex, age, full_name, about_me, city, which_search):
    try:
        # Debug
        print(f"Updating LeoMatch data for user {uid}")
        print(f"Photo: {photo}, Media Type: {media_type}")

        # Проверяем, нет ли пустых значений для обязательных полей
        if photo is None:
            photo = f"modul/clientbot/data/leo{uid}.jpg"
            print(f"Using default photo path: {photo}")

        if media_type is None:
            media_type = "PHOTO"
            print(f"Using default media_type: {media_type}")

        # Найдем пользователя по uid в строковом виде (это то, что сейчас используется)
        user = UserTG.objects.filter(uid=str(uid)).first()

        # Если пользователя нет, пробуем найти по id
        if not user:
            user = UserTG.objects.filter(id=uid).first()

        # Если пользователя всё ещё нет, создаём нового
        if not user:
            print(f"User {uid} does not exist in UserTG table. Creating user...")
            user = UserTG(
                uid=str(uid),
                username=f"user_{uid}",
                first_name=full_name if full_name else f"User {uid}"
            )
            user.save()
            print(f"Created new UserTG with ID {user.id} and UID {user.uid}")
        else:
            print(f"Found existing user with ID {user.id} and UID {user.uid}")

        # Поиск существующей LeoMatchModel записи по user
        leo = LeoMatchModel.objects.filter(user=user).first()

        # Если записи нет - создаём новую
        if not leo:
            print(f"Creating new LeoMatchModel for user {uid}")
            leo = LeoMatchModel.objects.create(
                user=user,
                photo=photo,
                media_type=media_type,
                sex=sex,
                age=age,
                full_name=full_name,
                about_me=about_me,
                city=city,
                which_search=which_search
            )
            print(f"Created new LeoMatchModel for user {uid}")
        else:
            # Обновление существующей записи
            leo.photo = photo
            leo.media_type = media_type
            leo.sex = sex
            leo.age = age
            leo.full_name = full_name
            leo.about_me = about_me
            leo.city = city
            leo.which_search = which_search
            leo.save()
            print(f"Updated existing LeoMatchModel for user {uid}")

        return True
    except Exception as e:
        print(f"Error updating LeoMatch data for user {uid}: {e}")
        return False  # Возвращаем False вместо поднятия исключения

async def show_media(bot: Bot, to_account: int, from_account: int, text_before: str = "",
                     reply_markup: types.ReplyKeyboardMarkup = None):
    account = await get_leo(from_account)
    account_user = account.user
    account_id = account_user.uid
    text = f"{text_before}\r\n{account.full_name} {account.age}, г {account.city}\n\n{account.about_me}"
    if account.media_type.value == MediaTypeEnum.VIDEO_NOTE.value:
        await bot.send_video_note(to_account, video_note=types.FSInputFile(f"clientbot/data/leo/{account_id}.mp4"),
                                  reply_markup=reply_markup)
        await bot.send_message(to_account, text=text)
    elif account.media_type.value == MediaTypeEnum.VIDEO.value:
        await bot.send_video(to_account, video=types.FSInputFile(f"clientbot/data/leo/{account_id}.mp4"),
                             reply_markup=reply_markup)
        await bot.send_message(to_account, text=text)
    elif account.media_type.value == MediaTypeEnum.PHOTO.value:
        await bot.send_photo(to_account, photo=types.FSInputFile(f"clientbot/data/leo/{account_id}.jpg"), caption=text)
    else:
        await bot.send_message(to_account, text=text)


async def show_profile(message: types.Message, uid: int, full_name: str, age: int, city: str, about_me: str, photo: str,
                       media_type: str, keyboard=None, comment: str = None):
    try:
        text = f"\n\nВам сообщение: {comment}" if comment else ""
        caption = f"{full_name}, {age}, {city}\n{about_me}{text}"
        kwargs = {}

        # KEYBOARD NI TO'G'RI HANDLE QILISH
        if keyboard:
            # Agar keyboard class bo'lsa (masalan ReplyKeyboardMarkup), uni ignore qilamiz
            if isinstance(keyboard, type):
                print(f"DEBUG: Ignoring keyboard class: {keyboard}")
                # Keyboard ni qo'shmaymiz, kwargs bo'sh qoladi
            # Agar keyboard valid instance bo'lsa, ishlatamiz
            elif hasattr(keyboard, 'keyboard') or isinstance(keyboard, (ReplyKeyboardMarkup, dict)):
                kwargs['reply_markup'] = keyboard
                print(f"DEBUG: Using valid keyboard: {type(keyboard)}")
            else:
                print(f"DEBUG: Unknown keyboard type: {type(keyboard)}, ignoring")

        # Преобразуем относительный путь в абсолютный
        abs_base_dir = "/var/www/konstructor"
        if not os.path.isabs(photo):
            abs_photo = os.path.join(abs_base_dir, photo)
        else:
            abs_photo = photo

        print(f"DEBUG: Using absolute path for photo: {abs_photo}")
        file_exists = os.path.exists(abs_photo)

        # Если файл не найден по абсолютному пути, проверим альтернативные пути
        if not file_exists:
            # Извлекаем имя файла из пути
            file_name = os.path.basename(photo)
            # Ищем файл в фиксированной директории
            alt_path = os.path.join("/var/www/konstructor/modul/clientbot/data", file_name)
            if os.path.exists(alt_path):
                abs_photo = alt_path
                file_exists = True
                print(f"DEBUG: Found file in alternative location: {alt_path}")

        if media_type == "VIDEO":
            if file_exists:
                print(f"DEBUG: Sending video: {abs_photo}")
                await message.answer_video(
                    video=FSInputFile(abs_photo),
                    caption=caption,
                    **kwargs
                )
            else:
                print(f"DEBUG: Video file not found: {abs_photo}")
                await message.answer(f"Видео не найдено. {caption}", **kwargs)

        elif media_type == "VIDEO_NOTE":
            if file_exists:
                print(f"DEBUG: Sending video note: {abs_photo}")
                await message.answer_video_note(
                    video_note=FSInputFile(abs_photo),
                    **kwargs
                )
            else:
                print(f"DEBUG: Video note file not found: {abs_photo}")
                await message.answer(f"Видеозаписка не найдена.", **kwargs)
            await message.answer(caption, **kwargs)

        else:  # PHOTO
            if file_exists:
                print(f"DEBUG: Sending photo: {abs_photo}")
                await message.answer_photo(
                    photo=FSInputFile(abs_photo),
                    caption=caption,
                    **kwargs
                )
            else:
                print(f"DEBUG: Photo file not found: {abs_photo}")
                await message.answer(f"Фото не найдено. {caption}", **kwargs)

    except Exception as e:
        print(f"DEBUG: Error in show_profile: {e}")
        print(f"DEBUG: Error traceback: {traceback.format_exc()}")

        # Error da ham keyboard muammosini oldini olamiz
        error_kwargs = {}  # Bo'sh kwargs ishlatamiz
        try:
            await message.answer(f"{full_name}, {age}, {city}\n{about_me}\nОшибка при загрузке медиа: {str(e)}",
                                 **error_kwargs)
        except Exception as inner_e:
            print(f"DEBUG: Error in error handler: {inner_e}")
            # Eng oddiy xabar
            await message.answer(f"Произошла ошибка при отображении профиля")


async def bot_show_profile(to_uid: int, from_uid: int, full_name: str, age: int, city: str, about_me: str, url: str,
                           type: str, username: str, keyboard=None):
    leo = await get_leo(to_uid)
    bot = await get_bot_by_username(leo.bot_username)
    caption = f"{full_name}, {age}, {city}\n{about_me}"
    kwargs = {}

    if keyboard:
        if isinstance(keyboard, type):
            print(f"DEBUG: Ignoring keyboard class in bot_show_profile: {keyboard}")
        elif hasattr(keyboard, 'keyboard') or isinstance(keyboard, (ReplyKeyboardMarkup, dict)):
            kwargs['reply_markup'] = keyboard
        else:
            print(f"DEBUG: Unknown keyboard type in bot_show_profile: {type(keyboard)}")

    async with Bot(bot.token, bot_session, parse_mode="HTML").context(auto_close=False) as bot_:
        await bot_.send_message(to_uid, "Есть взаимная симпатия!")
        if type == "PHOTO" or type == MediaTypeEnum.PHOTO:
            await bot_.send_photo(to_uid, types.FSInputFile(f"clientbot/data/leo/{from_uid}.jpg"), caption=caption,
                                  **kwargs)
        elif type == "VIDEO" or type == MediaTypeEnum.VIDEO:
            await bot_.send_video(to_uid, types.FSInputFile(f"clientbot/data/leo/{from_uid}.mp4"), caption=caption,
                                  **kwargs)

        is_username = False
        if username:
            link = username
            is_username = True
        else:
            link = from_uid
        try:
            await bot_.send_message(to_uid, ("Начинай общаться!"), reply_markup=write_profile(link, is_username))
        except:
            await bot_.send_message(to_uid,
                                    ("Извините, Вы не сможете начать общение так как у пользователя приватный аккаунт"))


async def show_profile_db(message: types.Message, uid: int, keyboard=ReplyKeyboardMarkup, comment: str = None):
    leo = await get_leo(uid)
    await show_profile(message, uid,  f'{leo.full_name}', leo.age, leo.city,  leo.about_me, leo.photo, leo.media_type,
                       keyboard=keyboard, comment=comment)


async def bot_show_profile_db(to_uid: int, uid: int, keyboard=types.ReplyKeyboardMarkup):
    leo = await get_leo(uid)
    user = await leo.user
    await bot_show_profile(to_uid, uid, f'{leo.full_name}', leo.age, leo.city, leo.about_me, leo.photo, leo.media_type,
                           user.username, keyboard=keyboard)


def _update_profile_sync(leo, kwargs: dict):
    try:
        if 'photo' in kwargs:
            old_file = leo.photo
            new_file = kwargs['photo']

            # Преобразуем пути к абсолютным для правильного сравнения
            abs_base_dir = "/var/www/konstructor"
            abs_old_file = os.path.join(abs_base_dir, old_file) if old_file and not os.path.isabs(
                old_file) else old_file
            abs_new_file = os.path.join(abs_base_dir, new_file) if not os.path.isabs(new_file) else new_file

            print(f"Update profile sync - old file: {abs_old_file}, new file: {abs_new_file}")

            # Удаляем старый файл только если он отличается от нового И существует
            if old_file and abs_old_file != abs_new_file and os.path.exists(abs_old_file):
                print(f"Removing old file: {abs_old_file}")
                try:
                    os.remove(abs_old_file)
                    print(f"Old file removed successfully")
                except Exception as e:
                    print(f"Error removing old file: {e}")

            # Проверяем существование нового файла перед обновлением БД
            if os.path.exists(abs_new_file):
                print(f"New file exists, size: {os.path.getsize(abs_new_file)} bytes")
                leo.photo = new_file
            else:
                print(f"WARNING: New file does not exist: {abs_new_file}")
                # Можно добавить дополнительную логику или вернуть False

        if 'media_type' in kwargs:
            leo.media_type = kwargs['media_type']

        # Обновляем остальные поля
        for key, value in kwargs.items():
            if key not in ['photo', 'media_type']:
                setattr(leo, key, value)

        # Сохраняем изменения в БД
        leo.save()
        print(f"Profile updated successfully with: {kwargs}")

        # Проверяем, существует ли файл после обновления
        if 'photo' in kwargs:
            abs_file = os.path.join(abs_base_dir, leo.photo) if not os.path.isabs(leo.photo) else leo.photo
            print(f"After DB update, file exists: {os.path.exists(abs_file)}")

        return True
    except Exception as e:
        print(f"Error in _update_profile_sync: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return False


async def update_profile(uid: int, kwargs: dict):
    try:
        leo = await get_leo(uid)

        print(f"Before update - photo: {leo.photo}, media_type: {leo.media_type}")

        if 'photo' in kwargs:
            new_photo = kwargs['photo']
            # Преобразуем пути к абсолютным для корректного сравнения
            abs_new_photo = os.path.join("/var/www/konstructor", new_photo) if not os.path.isabs(
                new_photo) else new_photo
            abs_old_photo = os.path.join("/var/www/konstructor", leo.photo) if leo.photo and not os.path.isabs(
                leo.photo) else leo.photo

            print(f"New photo: {abs_new_photo}, old photo: {abs_old_photo}")

            if os.path.exists(abs_new_photo):
                # Удаляем старый файл только если он отличается от нового
                if leo.photo and abs_old_photo != abs_new_photo and os.path.exists(abs_old_photo):
                    print(f"Removing old photo: {abs_old_photo}")
                    os.remove(abs_old_photo)
                leo.photo = new_photo
            else:
                print(f"New photo file does not exist: {abs_new_photo}")
                return False

        success = await sync_to_async(_update_profile_sync)(leo, kwargs)

        if success:
            updated_leo = await get_leo(uid)
            print(f"After update - photo: {updated_leo.photo}, media_type: {updated_leo.media_type}")

            # Проверяем существование файла после обновления
            abs_updated_photo = os.path.join("/var/www/konstructor", updated_leo.photo) if not os.path.isabs(
                updated_leo.photo) else updated_leo.photo
            print(f"After update, checking if file exists: {os.path.exists(abs_updated_photo)}")

        return success
    except Exception as e:
        print(f"Error in update_profile: {e}")
        return False


async def create_like(from_uid: int, to_uid: int, message: str = None):
    from_leo = await get_leo(from_uid)
    to_leo = await get_leo(to_uid)


    if not from_leo or not to_leo:
        raise ValueError(f"User not found: from_uid={from_uid}, to_uid={to_uid}")

    @sync_to_async
    def create_like_sync(from_leo, to_leo, message):
        return LeoMatchLikesBasketModel.objects.create(
            from_user=from_leo,
            to_user=to_leo,
            message=message,
        )

    return await create_like_sync(from_leo, to_leo, message)

async def leo_set_like(from_uid: int, to_uid: int, message: str = None):
    info = await create_like(from_uid, to_uid, message)
    return info  #


@sync_to_async
def get_likes_count_sync(user):
    return LeoMatchLikesBasketModel.objects.filter(to_user=user, done=False).all().count()


async def get_likes_count(uid: int):
    info = await get_likes_count_sync(await get_leo(uid))
    return info


@sync_to_async
def get_distinkt_likes_sync():
    leos = LeoMatchLikesBasketModel.objects.filter(done=False).all()
    return leos


async def get_distinkt_likes():
    leos = await get_distinkt_likes_sync()
    return await leos.distinct()


@sync_to_async
def get_first_like_sync(user):
    return LeoMatchLikesBasketModel.objects.filter(to_user=user, done=False).first()


@sync_to_async
def clear_all_likes_sync(user):
    return LeoMatchLikesBasketModel.objects.filter(to_user=user, done=False).update(done=True)


@sync_to_async
def delete_like_sync(user1, user2):
    return LeoMatchLikesBasketModel.objects.filter(from_user=user1, to_user=user2).delete()


async def get_first_like(uid: int):
    info = await get_first_like_sync(await get_leo(uid))
    return await info


async def clear_all_likes(uid: int):
    info = await clear_all_likes_sync(await get_leo(uid))
    return await info


async def delete_like(from_uid: int, to_uid: int):
    info = await delete_like_sync(await get_leo(from_uid), await get_leo(to_uid))
    return await info


@dataclass
class Analitics:
    count_users: int
    count_man: int
    count_female: int


async def get_analitics(bot_username: str = None):
    kwargs = {}
    if bot_username:
        kwargs['bot_username'] = bot_username
    users = LeoMatchModel.objects.filter(**kwargs, active=True, search=True).all()
    man = users.objects.filter(sex=SexEnum.MALE)
    female = users.objects.filter(sex=SexEnum.FEMALE)
    return Analitics(await users.count(), await man.count(), await female.count())

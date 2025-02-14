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
    print(UserTG.objects.filter(uid=uid).first(), "qwerty")
    return UserTG.objects.filter(uid=uid).first()




@sync_to_async
def get_leo_match(user):
    print(LeoMatchModel.objects.filter(user=user).first())
    return LeoMatchModel.objects.filter(user=user).first()


async def get_leo(uid: int):
    try:
        user = await sync_to_async(LeoMatchModel.objects.select_related('user').get)(user__uid=uid)
        return user
    except LeoMatchModel.DoesNotExist:
        return None

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

        age_range = (max(0, leo_me.age - 3), leo_me.age + 3)

        @sync_to_async
        def filter_leos_sync(kwargs, age_range, my_sex, my_id):
            return list(LeoMatchModel.objects.filter(
                Q(active=True) &
                Q(search=True) &
                Q(**kwargs) &
                Q(age__range=age_range) &
                ~Q(id=my_id)
            ).select_related('user'))

        leos = await filter_leos_sync(kwargs, age_range, leo_me.sex, leo_me.id)

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
def create_leomatch(user, photo, media_type, sex, age, full_name, about_me, city, which_search, bot_username):
    if user is None:
        print("User object is None.")
        raise ValueError("User object is None.")

    if not hasattr(user, 'uid'):
        print("User object does not have 'uid' attribute.")
        raise ValueError("User object does not have 'uid' attribute.")

    if user.uid is None:
        print("User uid is None.")
        raise ValueError("User uid is None.")

    # Ensure the user exists
    try:
        user_tg = UserTG.objects.get(uid=user.uid)
    except UserTG.DoesNotExist:
        print(f"UserTG with uid {user.uid} does not exist.")
        raise ValueError(f"UserTG with uid {user.uid} does not exist.")

    return LeoMatchModel.objects.create(
        user=user_tg,
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
    client = await get_client(uid)
    # bot = await shortcuts.get_bot_by_username(bot_username)
    # async with Bot(token=bot.token, session=bot_session).context(auto_close=False) as bot_:
    #     format_m = "jpg" if media_type == "PHOTO" else "mp4"
    #     await bot_.download(photo, f"/Users/ibragimkadamzanov/PycharmProjects/pythonProject21/modul/clientbot/data/leo{uid}.{format_m}")
    info = await create_leomatch(client, photo, media_type, sex, age, full_name, about_me, city, which_search,
                                 bot_username)


@sync_to_async
def save_model_sync(model):
    model.save()


@sync_to_async
def update_leo(user_id, photo, media_type, sex, age, full_name, about_me, city, which_search):
    """Update LeoMatch user information"""
    try:
        with transaction.atomic():
            # Get user first
            user = UserTG.objects.get(uid=user_id)

            # Get or create LeoMatch instance
            leo, created = LeoMatchModel.objects.get_or_create(
                user=user,
                defaults={
                    'photo': photo,
                    'media_type': media_type,
                    'sex': sex,
                    'age': age,
                    'full_name': full_name,
                    'about_me': about_me,
                    'city': city,
                    'which_search': which_search,
                    'bot_username': 'YOUR_BOT_USERNAME'  # O'zgartiring yoki dinamik qilib oling
                }
            )

            if not created:
                # Update existing record
                leo.photo = photo
                leo.media_type = media_type
                leo.sex = sex
                leo.age = age
                leo.full_name = full_name
                leo.about_me = about_me
                leo.city = city
                leo.which_search = which_search
                leo.save()

            return leo

    except Exception as e:
        print(f"Error updating LeoMatch data for user {user_id}: {e}")
        raise e


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
        if keyboard:
            kwargs['reply_markup'] = keyboard

        print(f"Showing profile - media_type: {media_type}, photo: {photo}")

        if media_type == "VIDEO":
            if os.path.exists(photo):
                await message.answer_video(
                    video=FSInputFile(photo),
                    caption=caption,
                    **kwargs
                )
            else:
                await message.answer_video(
                    video=photo,
                    caption=caption,
                    **kwargs
                )
        elif media_type == "VIDEO_NOTE":
            if os.path.exists(photo):
                await message.answer_video_note(
                    video_note=FSInputFile(photo),
                    **kwargs
                )
            else:
                await message.answer_video_note(
                    video_note=photo,
                    **kwargs
                )
            await message.answer(caption, **kwargs)
        else:
            if os.path.exists(photo):
                await message.answer_photo(
                    photo=FSInputFile(photo),
                    caption=caption,
                    **kwargs
                )
            else:
                await message.answer_photo(
                    photo=photo,
                    caption=caption,
                    **kwargs
                )

    except Exception as e:
        print(f"Error in show_profile: {e}")
        await message.answer("Произошла ошибка при отправке медиа. Пожалуйста, попробуйте позже.")

async def bot_show_profile(to_uid: int, from_uid: int, full_name: str, age: int, city: str, about_me: str, url: str,
                           type: str, username: str, keyboard=None):
    leo = await get_leo(to_uid)
    bot = await get_bot_by_username(leo.bot_username)
    caption = f"{full_name}, {age}, {city}\n{about_me}"
    kwargs = {}
    if keyboard:
        kwargs['reply_markup'] = keyboard
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
            await bot_.send_message(to_uid, ("Начнинай общаться!"), reply_markup=write_profile(link, is_username))
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
            if old_file and old_file != new_file and os.path.exists(old_file):
                os.remove(old_file)
            leo.photo = new_file

        if 'media_type' in kwargs:
            leo.media_type = kwargs['media_type']

        for key, value in kwargs.items():
            if key not in ['photo', 'media_type']:
                setattr(leo, key, value)

        leo.save()
        print(f"Profile updated successfully with: {kwargs}")
        return True
    except Exception as e:
        print(f"Error in _update_profile_sync: {e}")
        return False


async def update_profile(uid: int, kwargs: dict):
    try:
        leo = await get_leo(uid)

        print(f"Before update - photo: {leo.photo}, media_type: {leo.media_type}")

        if 'photo' in kwargs:
            new_photo = kwargs['photo']
            if os.path.exists(new_photo):
                if leo.photo and os.path.exists(leo.photo):
                    os.remove(leo.photo)
                leo.photo = new_photo
            else:
                print(f"New photo file does not exist: {new_photo}")
                return False

        success = await sync_to_async(_update_profile_sync)(leo, kwargs)

        if success:
            updated_leo = await get_leo(uid)
            print(f"After update - photo: {updated_leo.photo}, media_type: {updated_leo.media_type}")

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

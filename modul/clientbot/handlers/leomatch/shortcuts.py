import os
from dataclasses import dataclass
from random import Random

from aiogram import types
from asgiref.sync import sync_to_async

# from aiogram.utils.i18n import gettext as _

from modul.clientbot import shortcuts
from modul.clientbot.handlers.leomatch.keyboards.inline_kb import write_profile
from modul.clientbot.shortcuts import get_bot_by_username
from modul.loader import bot_session
from modul.models import User, LeoMatchModel, SexEnum, Bot, MediaTypeEnum, LeoMatchLikesBasketModel



@sync_to_async
def get_client(uid: int):
    try:
        return User.objects.get(uid=uid)  # Django syntax
    except User.DoesNotExist:
        return None

@sync_to_async
def get_leo_sync(user):
    if user:
        try:
            # .get() o'rniga .first() ishlatamiz
            return LeoMatchModel.objects.filter(user=user).first()
        except LeoMatchModel.DoesNotExist:
            return None
    return None

async def get_leo(uid: int):
    user = await get_client(uid)
    if user:
        leo = await get_leo_sync(user)
        return leo
    return None


@sync_to_async
def search_leo_sync(leo_me):
    from django.db.models import Q
    kwargs = {}
    if leo_me.which_search != SexEnum.ANY.value:
        kwargs['sex'] = leo_me.which_search

    return list(LeoMatchModel.objects.filter(
        blocked=False,
        age__range=(leo_me.age - 3, leo_me.age + 3),
        search=True,
        active=True,
        **kwargs
    ).exclude(
        Q(which_search__in=[leo_me.sex, SexEnum.ANY.value]) | Q(id=leo_me.id)
    ).order_by('?')[:50])  # Django random order


async def search_leo(me: int):
    leo_me = await get_leo(me)
    return await search_leo_sync(leo_me)

async def get_leos_id(me: int):
    users_id = []
    leos = await search_leo(me)
    for leo in leos:
        users_id.append(leo.user.uid)
    return users_id


async def exists_leo(uid: int):
    return await get_leo(uid) is not None


async def add_leo(uid: int, photo: str, media_type: str, sex: str, age: int, full_name: str, about_me: str, city: str,
                  which_search: str, bot_username: str):
    client = await get_client(uid)
    bot = await shortcuts.get_bot_by_username(bot_username)
    async with Bot(token=bot.token, session=bot_session).context(auto_close=False) as bot_:
        format = "jpg" if media_type == "PHOTO" else "mp4"
        os.makedirs("clientbot/data/leo", exist_ok=True)
        await bot_.download(photo, f"clientbot/data/leo/{uid}.{format}")
    await LeoMatchModel.create(
        user=client,
        photo=photo,
        media_type=media_type,
        sex=sex,
        age=age,
        full_name=full_name,
        about_me=about_me,
        city=city,
        which_search=which_search,
        bot_username=bot_username,
    )


async def update_leo(uid: int, photo: str, media_type: str, sex: str, age: int, full_name: str, about_me: str,
                     city: str, which_search: str):
    leo = await get_leo(uid)
    bot = await shortcuts.get_bot_by_username(leo.bot_username)
    async with Bot(token=bot.token, session=bot_session).context(auto_close=False) as bot_:
        format = "jpg" if media_type == "PHOTO" else "mp4"
        os.makedirs("clientbot/data/leo", exist_ok=True)
        await bot_.download(photo, f"clientbot/data/leo/{uid}.{format}")
    await leo.update_from_dict(
        {
            "user": await leo.user,
            "photo": photo,
            "media_type": media_type,
            "sex": sex,
            "age": age,
            "full_name": full_name,
            "about_me": about_me,
            "city": city,
            "which_search": which_search,
        }
    ).save()


async def show_media(bot: Bot, to_account: int, from_account: int, text_before: str = "",
                     reply_markup: types.ReplyKeyboardMarkup = None):
    account: LeoMatchModel = await get_leo(from_account)
    account_user: User = await account.user
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


async def show_profile(message: types.Message, uid: int, full_name: str, age: int, city: str, about_me: str, url: str,
                       type: str, keyboard: types.ReplyKeyboardMarkup = None, comment: str = None):
    text = f"\n\nВам сообщение: {comment}" if comment else ""
    caption = f"{full_name}, {age}, {city}\n{about_me}{text}"
    kwargs = {}
    if keyboard:
        kwargs['reply_markup'] = keyboard

    # File yo'lini tekshiring
    video_path = f"clientbot/data/leo/{uid}.mp4"
    photo_path = f"clientbot/data/leo/{uid}.jpg"

    try:
        # Faylning mavjudligini tekshiring
        if type in ["VIDEO", "VIDEO_NOTE"] and os.path.exists(video_path):
            await message.answer_video(types.FSInputFile(video_path))
            await message.answer(caption, **kwargs)
        elif type == "PHOTO" and os.path.exists(photo_path):
            await message.answer_photo(types.FSInputFile(photo_path), caption=caption, **kwargs)
        else:
            # Agar fayl mavjud bo'lmasa, faqat matn yuboring
            await message.answer(f"📷 {caption}", **kwargs)
    except Exception as e:
        # Fallback - faqat matn
        await message.answer(f"📷 {caption}", **kwargs)


async def bot_show_profile(to_uid: int, from_uid: str, full_name: str, age: int, city: str, about_me: str, url: str,
                           type: str, username: str, keyboard: types.ReplyKeyboardMarkup = None):
    leo = await get_leo(to_uid)
    bot = await get_bot_by_username(leo.bot_username)
    caption = f"{full_name}, {age}, {city}\n{about_me}"
    kwargs = {}
    if keyboard:
        kwargs['reply_markup'] = keyboard
    async with Bot(bot.token, bot_session, parse_mode="HTML").context(auto_close=False) as bot_:
        await bot_.send_message(to_uid, "Есть взаимная симпатия!")  ### TODO: Перевести
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
            await bot_.send_message(to_uid,  ("Начнинай общаться!"), reply_markup=write_profile(link, is_username))
        except:
            await bot_.send_message(to_uid,
                                     ("Извините, Вы не сможете начать общение так как у пользователя приватный аккаунт"))


async def show_profile_db(message: types.Message, uid: int, keyboard=types.ReplyKeyboardMarkup, comment: str = None):
    leo = await get_leo(uid)
    await show_profile(message, uid, f'{leo.full_name}', leo.age, leo.city, leo.about_me, leo.photo, leo.media_type,
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



async def leo_set_like(from_uid: int, to_uid: int, message: str = None):
    from_user = await get_leo(from_uid)
    to_user = await get_leo(to_uid)
    if not from_user or not to_user:
        return False
    await LeoMatchLikesBasketModel.create(
        from_user=from_user,
        to_user=to_user,
        message=message,
    )
    return True


async def get_likes_count(uid: int):
    return await LeoMatchLikesBasketModel.filter(to_user=await get_leo(uid), done=False).all().count()


async def get_distinkt_likes():
    leos = LeoMatchLikesBasketModel.filter(done=False).all()
    return await leos.distinct()


async def get_first_like(uid: int):
    return await LeoMatchLikesBasketModel.filter(to_user=await get_leo(uid), done=False).first()


async def clear_all_likes(uid: int):
    return await LeoMatchLikesBasketModel.filter(to_user=await get_leo(uid)).update(done=True)


async def delete_like(from_uid: int, to_uid: int):
    await LeoMatchLikesBasketModel.filter(from_user=await get_leo(from_uid), to_user=await get_leo(to_uid)).update(
        done=True)


@dataclass
class Analitics:
    count_users: int
    count_man: int
    count_female: int


async def get_analitics(bot_username: str = None):
    kwargs = {}
    if bot_username:
        kwargs['bot_username'] = bot_username
    users = LeoMatchModel.filter(**kwargs, active=True, search=True).all()
    man = users.filter(sex=SexEnum.MALE)
    female = users.filter(sex=SexEnum.FEMALE)
    return Analitics(await users.count(), await man.count(), await female.count())

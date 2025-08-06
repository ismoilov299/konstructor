import os
from dataclasses import dataclass
from random import Random

from aiogram import types, Bot
from asgiref.sync import sync_to_async

from modul.clientbot import shortcuts
from modul.clientbot.handlers.leomatch.keyboards.inline_kb import write_profile
from modul.clientbot.shortcuts import get_bot_by_username
from modul.loader import bot_session
from modul.models import User, LeoMatchModel, SexEnum, Bot, MediaTypeEnum, LeoMatchLikesBasketModel, UserTG


@sync_to_async
def get_client(uid: int):
    try:
        return User.objects.get(uid=uid)
    except User.DoesNotExist:
        return None


@sync_to_async
def get_leo_sync(user):
    if user:
        try:
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

    print(f"DEBUG: Qidiruv - Men: {leo_me.sex}, Qidirayotganim: {leo_me.which_search}")

    base_filters = {
        'blocked': False,
        'search': True,
        'active': True,
    }

    if leo_me.which_search == SexEnum.MALE.value:
        base_filters['sex'] = SexEnum.MALE.value
        print("DEBUG: Faqat o'g'il bolalarni qidiryapman")

    elif leo_me.which_search == SexEnum.FEMALE.value:
        base_filters['sex'] = SexEnum.FEMALE.value
        print("DEBUG: Faqat qizlarni qidiryapman")

    elif leo_me.which_search == SexEnum.ANY.value:
        print("DEBUG: Barcha jinsdagilarni qidiryapman")

    queryset = LeoMatchModel.objects.filter(**base_filters).exclude(id=leo_me.id)

    print(f"DEBUG: Topilgan natijalar soni: {queryset.count()}")

    result = list(queryset.order_by('?')[:50])

    for profile in result[:3]:
        print(f"DEBUG: Topilgan profil - {profile.full_name}: {profile.sex}")

    return result


async def search_leo(me: int):
    leo_me = await get_leo(me)
    return await search_leo_sync(leo_me)


@sync_to_async
def get_leos_id_optimized(me: int):

    try:
        user_me = User.objects.filter(uid=me).first()
        if not user_me:
            return []

        leo_me = LeoMatchModel.objects.filter(user=user_me).first()
        if not leo_me:
            return []

        base_filters = {
            'blocked': False,
            'search': True,
            'active': True,
        }

        if leo_me.which_search == SexEnum.MALE.value:
            base_filters['sex'] = SexEnum.MALE.value
        elif leo_me.which_search == SexEnum.FEMALE.value:
            base_filters['sex'] = SexEnum.FEMALE.value

        user_ids = list(
            LeoMatchModel.objects
            .filter(**base_filters)
            .exclude(id=leo_me.id)
            .values_list('user__uid', flat=True)
            .order_by('?')[:50]
        )

        return user_ids

    except Exception as e:
        print(f"ERROR get_leos_id: {e}")
        return []


# Async wrapper
async def get_leos_id(me: int):

    return await get_leos_id_optimized(me)


async def exists_leo(uid: int):
    return await get_leo(uid) is not None


async def add_leo(uid: int, photo: str, media_type: str, sex: str, age: int, full_name: str, about_me: str, city: str,
                  which_search: str, bot_username: str, bot: Bot):
    client = await get_client(uid)

    # Debug
    print(f"DEBUG add_leo: photo='{photo}', media_type='{media_type}'")

    if not photo or not photo.strip():
        print("ERROR: Bo'sh photo bilan add_leo chaqirildi!")
        raise ValueError("Photo bo'sh bo'lishi mumkin emas!")

    # Faylni saqlash
    try:
        format = "jpg" if media_type == "PHOTO" else "mp4"
        os.makedirs("clientbot/data/leo", exist_ok=True)
        await bot.download(photo, f"clientbot/data/leo/{uid}.{format}")
        print(f"DEBUG: File saved: clientbot/data/leo/{uid}.{format}")
    except Exception as e:
        print(f"ERROR: File download failed: {e}")
        raise

    # Django ORM create
    await sync_to_async(LeoMatchModel.objects.create)(
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
    print(f"DEBUG: LeoMatchModel created with photo: '{photo}'")


@sync_to_async
def update_leo(uid, photo, media_type, sex, age, full_name, about_me, city, which_search):
    try:
        print(f"DEBUG update_leo: uid={uid}, photo='{photo}', media_type='{media_type}'")

        # User topish
        user = UserTG.objects.filter(uid=str(uid)).first()
        if not user:
            user = UserTG.objects.filter(id=uid).first()

        if not user:
            print(f"User {uid} topilmadi. Yangi user yaratilmoqda...")
            user = UserTG(
                uid=str(uid),
                username=f"user_{uid}",
                first_name=full_name if full_name else f"User {uid}"
            )
            user.save()

        # LeoMatchModel topish yoki yaratish
        leo = LeoMatchModel.objects.filter(user=user).first()

        if not leo:
            print(f"Yangi LeoMatchModel yaratilmoqda...")
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
        else:
            print(f"Mavjud LeoMatchModel yangilanmoqda...")

            # MUHIM: Faqat photo mavjud bo'lsa yangilang
            if photo and photo.strip():
                leo.photo = photo
                leo.media_type = media_type
                print(f"Photo yangilandi: '{photo}'")
            else:
                print(f"Photo bo'sh, eski qiymat saqlanmoqda: '{leo.photo}'")

            leo.sex = sex
            leo.age = age
            leo.full_name = full_name
            leo.about_me = about_me
            leo.city = city
            leo.which_search = which_search
            leo.save()

        print(f"update_leo muvaffaqiyatli yakunlandi")
        return True
    except Exception as e:
        print(f"ERROR update_leo: {e}")
        return False


@sync_to_async
def update_profile_sync(leo, kwargs: dict):

    try:
        print(f"DEBUG: update_profile_sync - kwargs: {kwargs}")

        if 'photo' in kwargs and kwargs['photo']:
            old_photo = leo.photo
            new_photo = kwargs['photo']

            print(f"DEBUG: Photo yangilanmoqda - eski: '{old_photo}' -> yangi: '{new_photo}'")

            if new_photo and new_photo.strip():
                leo.photo = new_photo

                if 'media_type' in kwargs:
                    leo.media_type = kwargs['media_type']
                    print(f"DEBUG: Media type yangilandi: {kwargs['media_type']}")
            else:
                print("DEBUG: Yangi photo bo'sh, eski photo saqlanadi")

        for key, value in kwargs.items():
            if key not in ['photo', 'media_type'] and hasattr(leo, key):
                setattr(leo, key, value)
                print(f"DEBUG: {key} = {value}")

        leo.save()
        print("DEBUG: Profil muvaffaqiyatli saqlandi")
        return True

    except Exception as e:
        print(f"ERROR: update_profile_sync - {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return False


async def update_profile(uid: int, kwargs: dict):

    try:
        print(f"DEBUG: update_profile called - uid: {uid}, kwargs: {kwargs}")

        leo = await get_leo(uid)
        if not leo:
            print(f"ERROR: User {uid} uchun profil topilmadi")
            return False

        print(f"DEBUG: Hozirgi profil - photo: '{leo.photo}', media_type: '{leo.media_type}'")

        if 'photo' in kwargs:
            new_photo = kwargs['photo']

            if new_photo and isinstance(new_photo, str) and new_photo.startswith('/') or new_photo.startswith(
                    'clientbot/'):
                abs_new_photo = os.path.abspath(new_photo)
                if not os.path.exists(abs_new_photo):
                    print(f"WARNING: Yangi photo fayli mavjud emas: {abs_new_photo}")

        success = await update_profile_sync(leo, kwargs)

        if success:
            updated_leo = await get_leo(uid)
            print(f"DEBUG: Yangilashdan keyin - photo: '{updated_leo.photo}', media_type: '{updated_leo.media_type}'")

        return success

    except Exception as e:
        print(f"ERROR: update_profile - {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return False

async def show_media(bot: Bot, to_account: int, from_account: int, text_before: str = "",
                     reply_markup: types.ReplyKeyboardMarkup = None):
    account: LeoMatchModel = await get_leo(from_account)
    if not account:
        return

    account_user = account.user
    account_id = account_user.uid
    text = f"{text_before}\r\n{account.full_name} {account.age}, г {account.city}\n\n{account.about_me}"

    try:
        if account.media_type == MediaTypeEnum.VIDEO_NOTE.value:
            await bot.send_video_note(to_account, video_note=types.FSInputFile(f"clientbot/data/leo/{account_id}.mp4"),
                                      reply_markup=reply_markup)
            await bot.send_message(to_account, text=text)
        elif account.media_type == MediaTypeEnum.VIDEO.value:
            await bot.send_video(to_account, video=types.FSInputFile(f"clientbot/data/leo/{account_id}.mp4"),
                                 reply_markup=reply_markup)
            await bot.send_message(to_account, text=text)
        elif account.media_type == MediaTypeEnum.PHOTO.value:
            await bot.send_photo(to_account, photo=types.FSInputFile(f"clientbot/data/leo/{account_id}.jpg"),
                                 caption=text)
        else:
            await bot.send_message(to_account, text=text)
    except Exception as e:
        print(f"ERROR show_media: {e}")
        await bot.send_message(to_account, text=f"📷 {text}")


async def show_profile(message: types.Message, uid: int, full_name: str, age: int, city: str, about_me: str, url: str,
                       type: str, keyboard: types.ReplyKeyboardMarkup = None, comment: str = None):
    text = f"\n\nВам сообщение: {comment}" if comment else ""
    caption = f"{full_name}, {age}, {city}\n{about_me}{text}"
    kwargs = {}
    if keyboard:
        kwargs['reply_markup'] = keyboard

    video_path = f"clientbot/data/leo/{uid}.mp4"
    photo_path = f"clientbot/data/leo/{uid}.jpg"

    try:
        if type in ["VIDEO", "VIDEO_NOTE"] and os.path.exists(video_path):
            await message.answer_video(types.FSInputFile(video_path))
            await message.answer(caption, **kwargs)
        elif type == "PHOTO" and os.path.exists(photo_path):
            await message.answer_photo(types.FSInputFile(photo_path), caption=caption, **kwargs)
        else:
            await message.answer(f"📷 {caption}", **kwargs)
    except Exception as e:
        print(f"ERROR show_profile: {e}")
        await message.answer(f"📷 {caption}", **kwargs)


async def bot_show_profile(to_uid: int, from_uid: str, full_name: str, age: int, city: str, about_me: str, url: str,
                           type: str, username: str, keyboard: types.ReplyKeyboardMarkup = None):
    leo = await get_leo(to_uid)
    if not leo:
        return

    bot = await get_bot_by_username(leo.bot_username)
    caption = f"{full_name}, {age}, {city}\n{about_me}"
    kwargs = {}
    if keyboard:
        kwargs['reply_markup'] = keyboard

    # context() ni olib tashlaymiz
    async with Bot(bot.token, bot_session, parse_mode="HTML") as bot_:
        try:
            await bot_.send_message(to_uid, "Есть взаимная симпатия!")

            if type == "PHOTO" or type == MediaTypeEnum.PHOTO:
                await bot_.send_photo(to_uid, types.FSInputFile(f"clientbot/data/leo/{from_uid}.jpg"),
                                      caption=caption, **kwargs)
            elif type == "VIDEO" or type == MediaTypeEnum.VIDEO:
                await bot_.send_video(to_uid, types.FSInputFile(f"clientbot/data/leo/{from_uid}.mp4"),
                                      caption=caption, **kwargs)

            is_username = False
            if username:
                link = username
                is_username = True
            else:
                link = from_uid

            await bot_.send_message(to_uid, ("Начнинай общаться!"),
                                    reply_markup=write_profile(link, is_username))
        except Exception as e:
            print(f"ERROR bot_show_profile: {e}")
            await bot_.send_message(to_uid,
                                    ("Извините, Вы не сможете начать общение так как у пользователя приватный аккаунт"))


async def show_profile_db(message: types.Message, uid: int, keyboard=types.ReplyKeyboardMarkup, comment: str = None):
    leo = await get_leo(uid)
    if leo:
        await show_profile(message, uid, f'{leo.full_name}', leo.age, leo.city, leo.about_me, leo.photo,
                           leo.media_type, keyboard=keyboard, comment=comment)


async def bot_show_profile_db(to_uid: int, uid: int, keyboard=types.ReplyKeyboardMarkup):
    leo = await get_leo(uid)
    if leo:
        user = leo.user
        await bot_show_profile(to_uid, uid, f'{leo.full_name}', leo.age, leo.city, leo.about_me, leo.photo,
                               leo.media_type, user.username, keyboard=keyboard)


# Django ORM ga mos keluvchi funksiyalar
@sync_to_async
def leo_set_like_sync(from_user, to_user, message=None):
    return LeoMatchLikesBasketModel.objects.create(
        from_user=from_user,
        to_user=to_user,
        message=message,
    )


async def leo_set_like(from_uid: int, to_uid: int, message: str = None):
    from_user = await get_leo(from_uid)
    to_user = await get_leo(to_uid)
    if not from_user or not to_user:
        return False
    await leo_set_like_sync(from_user, to_user, message)
    return True


@sync_to_async
def get_likes_count_sync(leo):
    return LeoMatchLikesBasketModel.objects.filter(to_user=leo, done=False).count()


async def get_likes_count(uid: int):
    leo = await get_leo(uid)
    if not leo:
        return 0
    return await get_likes_count_sync(leo)


@sync_to_async
def get_first_like_sync(leo):
    return LeoMatchLikesBasketModel.objects.filter(to_user=leo, done=False).first()


async def get_first_like(uid: int):
    leo = await get_leo(uid)
    if not leo:
        return None
    return await get_first_like_sync(leo)


@sync_to_async
def clear_all_likes_sync(leo):
    return LeoMatchLikesBasketModel.objects.filter(to_user=leo).update(done=True)


async def clear_all_likes(uid: int):
    leo = await get_leo(uid)
    if not leo:
        return 0
    return await clear_all_likes_sync(leo)


@sync_to_async
def delete_like_sync(from_leo, to_leo):
    return LeoMatchLikesBasketModel.objects.filter(from_user=from_leo, to_user=to_leo).update(done=True)


async def delete_like(from_uid: int, to_uid: int):
    from_leo = await get_leo(from_uid)
    to_leo = await get_leo(to_uid)
    if not from_leo or not to_leo:
        return 0
    return await delete_like_sync(from_leo, to_leo)


@dataclass
class Analitics:
    count_users: int
    count_man: int
    count_female: int


@sync_to_async
def get_analitics_sync(bot_username=None):
    kwargs = {'active': True, 'search': True}
    if bot_username:
        kwargs['bot_username'] = bot_username

    users = LeoMatchModel.objects.filter(**kwargs)
    count_users = users.count()
    count_man = users.filter(sex=SexEnum.MALE).count()
    count_female = users.filter(sex=SexEnum.FEMALE).count()

    return Analitics(count_users, count_man, count_female)


async def get_analitics(bot_username: str = None):
    return await get_analitics_sync(bot_username)
# import os
# from dataclasses import dataclass
# from random import Random
#
# from aiogram import types
# from asgiref.sync import sync_to_async
#
# # from aiogram.utils.i18n import gettext as _
#
# from modul.clientbot import shortcuts
# from modul.clientbot.handlers.leomatch.keyboards.inline_kb import write_profile
# from modul.clientbot.shortcuts import get_bot_by_username
# from modul.loader import bot_session
# from modul.models import User, LeoMatchModel, SexEnum, Bot, MediaTypeEnum, LeoMatchLikesBasketModel, UserTG
#
#
# @sync_to_async
# def get_client(uid: int):
#     try:
#         return User.objects.get(uid=uid)  # Django syntax
#     except User.DoesNotExist:
#         return None
#
# @sync_to_async
# def get_leo_sync(user):
#     if user:
#         try:
#             # .get() o'rniga .first() ishlatamiz
#             return LeoMatchModel.objects.filter(user=user).first()
#         except LeoMatchModel.DoesNotExist:
#             return None
#     return None
#
# async def get_leo(uid: int):
#     user = await get_client(uid)
#     if user:
#         leo = await get_leo_sync(user)
#         return leo
#     return None
#
#
# @sync_to_async
# def search_leo_sync(leo_me):
#     from django.db.models import Q
#     kwargs = {}
#     if leo_me.which_search != SexEnum.ANY.value:
#         kwargs['sex'] = leo_me.which_search
#
#     return list(LeoMatchModel.objects.filter(
#         blocked=False,
#         age__range=(leo_me.age - 3, leo_me.age + 3),
#         search=True,
#         active=True,
#         **kwargs
#     ).exclude(
#         Q(which_search__in=[leo_me.sex, SexEnum.ANY.value]) | Q(id=leo_me.id)
#     ).order_by('?')[:50])  # Django random order
#
#
# async def search_leo(me: int):
#     leo_me = await get_leo(me)
#     return await search_leo_sync(leo_me)
#
# async def get_leos_id(me: int):
#     users_id = []
#     leos = await search_leo(me)
#     for leo in leos:
#         users_id.append(leo.user.uid)
#     return users_id
#
#
# async def exists_leo(uid: int):
#     return await get_leo(uid) is not None
#
#
# async def add_leo(uid: int, photo: str, media_type: str, sex: str, age: int, full_name: str, about_me: str, city: str,
#                   which_search: str, bot_username: str, bot: Bot):
#     client = await get_client(uid)
#
#     # Faylni saqlash
#     format = "jpg" if media_type == "PHOTO" else "mp4"
#     os.makedirs("clientbot/data/leo", exist_ok=True)
#     await bot.download(photo, f"clientbot/data/leo/{uid}.{format}")
#
#     # Django ORM ni async da ishlatish
#     await sync_to_async(LeoMatchModel.objects.create)(
#         user=client,
#         photo=photo,
#         media_type=media_type,
#         sex=sex,
#         age=age,
#         full_name=full_name,
#         about_me=about_me,
#         city=city,
#         which_search=which_search,
#         bot_username=bot_username,
#     )
#
#
# @sync_to_async
# def update_leo(uid, photo, media_type, sex, age, full_name, about_me, city, which_search):
#     try:
#         # Debug
#         print(f"Updating LeoMatch data for user {uid}")
#         print(f"Photo: {photo}, Media Type: {media_type}")
#
#         # Проверяем, нет ли пустых значений для обязательных полей
#         if photo is None:
#             photo = f"modul/clientbot/data/leo{uid}.jpg"
#             print(f"Using default photo path: {photo}")
#
#         if media_type is None:
#             media_type = "PHOTO"
#             print(f"Using default media_type: {media_type}")
#
#         # Найдем пользователя по uid в строковом виде (это то, что сейчас используется)
#         user = UserTG.objects.filter(uid=str(uid)).first()
#
#         # Если пользователя нет, пробуем найти по id
#         if not user:
#             user = UserTG.objects.filter(id=uid).first()
#
#         # Если пользователя всё ещё нет, создаём нового
#         if not user:
#             print(f"User {uid} does not exist in UserTG table. Creating user...")
#             user = UserTG(
#                 uid=str(uid),
#                 username=f"user_{uid}",
#                 first_name=full_name if full_name else f"User {uid}"
#             )
#             user.save()
#             print(f"Created new UserTG with ID {user.id} and UID {user.uid}")
#         else:
#             print(f"Found existing user with ID {user.id} and UID {user.uid}")
#
#         # Поиск существующей LeoMatchModel записи по user
#         leo = LeoMatchModel.objects.filter(user=user).first()
#
#         # Если записи нет - создаём новую
#         if not leo:
#             print(f"Creating new LeoMatchModel for user {uid}")
#             leo = LeoMatchModel.objects.create(
#                 user=user,
#                 photo=photo,
#                 media_type=media_type,
#                 sex=sex,
#                 age=age,
#                 full_name=full_name,
#                 about_me=about_me,
#                 city=city,
#                 which_search=which_search
#             )
#             print(f"Created new LeoMatchModel for user {uid}")
#         else:
#             # Обновление существующей записи
#             leo.photo = photo
#             leo.media_type = media_type
#             leo.sex = sex
#             leo.age = age
#             leo.full_name = full_name
#             leo.about_me = about_me
#             leo.city = city
#             leo.which_search = which_search
#             leo.save()
#             print(f"Updated existing LeoMatchModel for user {uid}")
#
#         return True
#     except Exception as e:
#         print(f"Error updating LeoMatch data for user {uid}: {e}")
#         return False  # Возвращаем False вместо поднятия исключения
#
#
# async def show_media(bot: Bot, to_account: int, from_account: int, text_before: str = "",
#                      reply_markup: types.ReplyKeyboardMarkup = None):
#     account: LeoMatchModel = await get_leo(from_account)
#     account_user: User = await account.user
#     account_id = account_user.uid
#     text = f"{text_before}\r\n{account.full_name} {account.age}, г {account.city}\n\n{account.about_me}"
#     if account.media_type.value == MediaTypeEnum.VIDEO_NOTE.value:
#         await bot.send_video_note(to_account, video_note=types.FSInputFile(f"clientbot/data/leo/{account_id}.mp4"),
#                                   reply_markup=reply_markup)
#         await bot.send_message(to_account, text=text)
#     elif account.media_type.value == MediaTypeEnum.VIDEO.value:
#         await bot.send_video(to_account, video=types.FSInputFile(f"clientbot/data/leo/{account_id}.mp4"),
#                              reply_markup=reply_markup)
#         await bot.send_message(to_account, text=text)
#     elif account.media_type.value == MediaTypeEnum.PHOTO.value:
#         await bot.send_photo(to_account, photo=types.FSInputFile(f"clientbot/data/leo/{account_id}.jpg"), caption=text)
#     else:
#         await bot.send_message(to_account, text=text)
#
#
# async def show_profile(message: types.Message, uid: int, full_name: str, age: int, city: str, about_me: str, url: str,
#                        type: # str, keyboard: types.ReplyKeyboardMarkup = None, comment: str = None):
#     text = f"\n\nВам сообщение: {comment}" if comment else ""
#     caption = f"{full_name}, {age}, {city}\n{about_me}{text}"
#     kwargs = {}
#     if keyboard:
#         kwargs['reply_markup'] = keyboard
#
#     # File yo'lini tekshiring
#     video_path = f"clientbot/data/leo/{uid}.mp4"
#     photo_path = f"clientbot/data/leo/{uid}.jpg"
#
#     try:
#         # Faylning mavjudligini tekshiring
#         if type in ["VIDEO", "VIDEO_NOTE"] and os.path.exists(video_path):
#             await message.answer_video(types.FSInputFile(video_path))
#             await message.answer(caption, **kwargs)
#         elif type == "PHOTO" and os.path.exists(photo_path):
#             await message.answer_photo(types.FSInputFile(photo_path), caption=caption, **kwargs)
#         else:
#             # Agar fayl mavjud bo'lmasa, faqat matn yuboring
#             await message.answer(f"📷 {caption}", **kwargs)
#     except Exception as e:
#         # Fallback - faqat matn
#         await message.answer(f"📷 {caption}", **kwargs)
#
#
# async def bot_show_profile(to_uid: int, from_uid: str, full_name: str, age: int, city: str, about_me: str, url: str,
#                            type: # str, username: str, keyboard: types.ReplyKeyboardMarkup = None):
#     leo = await get_leo(to_uid)
#     bot = await get_bot_by_username(leo.bot_username)
#     caption = f"{full_name}, {age}, {city}\n{about_me}"
#     kwargs = {}
#     if keyboard:
#         kwargs['reply_markup'] = keyboard
#     async with Bot(bot.token, bot_session, parse_mode="HTML").context(auto_close=False) as bot_:
#         await bot_.send_message(to_uid, "Есть взаимная симпатия!")  ### TODO: Перевести
#         if type == "PHOTO" or type == MediaTypeEnum.PHOTO:
#             await bot_.send_photo(to_uid, types.FSInputFile(f"clientbot/data/leo/{from_uid}.jpg"), caption=caption,
#                                   **kwargs)
#         elif type == "VIDEO" or type == MediaTypeEnum.VIDEO:
#             await bot_.send_video(to_uid, types.FSInputFile(f"clientbot/data/leo/{from_uid}.mp4"), caption=caption,
#                                   **kwargs)
#
#         is_username = False
#         if username:
#             link = username
#             is_username = True
#         else:
#             link = from_uid
#         try:
#             await bot_.send_message(to_uid,  ("Начнинай общаться!"), reply_markup=write_profile(link, is_username))
#         except:
#             await bot_.send_message(to_uid,
#                                      ("Извините, Вы не сможете начать общение так как у пользователя приватный аккаунт"))
#
#
# async def show_profile_db(message: types.Message, uid: int, keyboard=types.ReplyKeyboardMarkup, comment: str = None):
#     leo = await get_leo(uid)
#     await show_profile(message, uid, f'{leo.full_name}', leo.age, leo.city, leo.about_me, leo.photo, leo.media_type,
#                        keyboard=keyboard, comment=comment)
#
#
# async def bot_show_profile_db(to_uid: int, uid: int, keyboard=types.ReplyKeyboardMarkup):
#     leo = await get_leo(uid)
#     user = await leo.user
#     await bot_show_profile(to_uid, uid, f'{leo.full_name}', leo.age, leo.city, leo.about_me, leo.photo, leo.media_type,
#                            user.username, keyboard=keyboard)
#
# def _update_profile_sync(leo, kwargs: dict):
#     try:
#         if 'photo' in kwargs:
#             old_file = leo.photo
#             new_file = kwargs['photo']
#
#             # Преобразуем пути к абсолютным для правильного сравнения
#             abs_base_dir = "/var/www/konstructor"
#             abs_old_file = os.path.join(abs_base_dir, old_file) if old_file and not os.path.isabs(
#                 old_file) else old_file
#             abs_new_file = os.path.join(abs_base_dir, new_file) if not os.path.isabs(new_file) else new_file
#
#             print(f"Update profile sync - old file: {abs_old_file}, new file: {abs_new_file}")
#
#             # Удаляем старый файл только если он отличается от нового И существует
#             if old_file and abs_old_file != abs_new_file and os.path.exists(abs_old_file):
#                 print(f"Removing old file: {abs_old_file}")
#                 try:
#                     os.remove(abs_old_file)
#                     print(f"Old file removed successfully")
#                 except Exception as e:
#                     print(f"Error removing old file: {e}")
#
#             # Проверяем существование нового файла перед обновлением БД
#             if os.path.exists(abs_new_file):
#                 print(f"New file exists, size: {os.path.getsize(abs_new_file)} bytes")
#                 leo.photo = new_file
#             else:
#                 print(f"WARNING: New file does not exist: {abs_new_file}")
#                 # Можно добавить дополнительную логику или вернуть False
#
#         if 'media_type' in kwargs:
#             leo.media_type = kwargs['media_type']
#
#         # Обновляем остальные поля
#         for key, value in kwargs.items():
#             if key not in ['photo', 'media_type']:
#                 setattr(leo, key, value)
#
#         # Сохраняем изменения в БД
#         leo.save()
#         print(f"Profile updated successfully with: {kwargs}")
#
#         # Проверяем, существует ли файл после обновления
#         if 'photo' in kwargs:
#             abs_file = os.path.join(abs_base_dir, leo.photo) if not os.path.isabs(leo.photo) else leo.photo
#             print(f"After DB update, file exists: {os.path.exists(abs_file)}")
#
#         return True
#     except Exception as e:
#         print(f"Error in _update_profile_sync: {e}")
#         import traceback
#         print(f"Traceback: {traceback.format_exc()}")
#         return False
#
# async def update_profile(uid: int, kwargs: dict):
#     try:
#         leo = await get_leo(uid)
#
#         print(f"Before update - photo: {leo.photo}, media_type: {leo.media_type}")
#
#         if 'photo' in kwargs:
#             new_photo = kwargs['photo']
#             # Преобразуем пути к абсолютным для корректного сравнения
#             abs_new_photo = os.path.join("/var/www/konstructor", new_photo) if not os.path.isabs(
#                 new_photo) else new_photo
#             abs_old_photo = os.path.join("/var/www/konstructor", leo.photo) if leo.photo and not os.path.isabs(
#                 leo.photo) else leo.photo
#
#             print(f"New photo: {abs_new_photo}, old photo: {abs_old_photo}")
#
#             if os.path.exists(abs_new_photo):
#                 # Удаляем старый файл только если он отличается от нового
#                 if leo.photo and abs_old_photo != abs_new_photo and os.path.exists(abs_old_photo):
#                     print(f"Removing old photo: {abs_old_photo}")
#                     os.remove(abs_old_photo)
#                 leo.photo = new_photo
#             else:
#                 print(f"New photo file does not exist: {abs_new_photo}")
#                 return False
#
#         success = await sync_to_async(_update_profile_sync)(leo, kwargs)
#
#         if success:
#             updated_leo = await get_leo(uid)
#             print(f"After update - photo: {updated_leo.photo}, media_type: {updated_leo.media_type}")
#
#             # Проверяем существование файла после обновления
#             abs_updated_photo = os.path.join("/var/www/konstructor", updated_leo.photo) if not os.path.isabs(
#                 updated_leo.photo) else updated_leo.photo
#             print(f"After update, checking if file exists: {os.path.exists(abs_updated_photo)}")
#
#         return success
#     except Exception as e:
#         print(f"Error in update_profile: {e}")
#         return False
#
#
#
# async def leo_set_like(from_uid: int, to_uid: int, message: str = None):
#     from_user = await get_leo(from_uid)
#     to_user = await get_leo(to_uid)
#     if not from_user or not to_user:
#         return False
#     await LeoMatchLikesBasketModel.create(
#         from_user=from_user,
#         to_user=to_user,
#         message=message,
#     )
#     return True
#
#
# async def get_likes_count(uid: int):
#     return await LeoMatchLikesBasketModel.filter(to_user=await get_leo(uid), done=False).all().count()
#
#
# async def get_distinkt_likes():
#     leos = LeoMatchLikesBasketModel.filter(done=False).all()
#     return await leos.distinct()
#
#
# async def get_first_like(uid: int):
#     return await LeoMatchLikesBasketModel.filter(to_user=await get_leo(uid), done=False).first()
#
#
# async def clear_all_likes(uid: int):
#     return await LeoMatchLikesBasketModel.filter(to_user=await get_leo(uid)).update(done=True)
#
#
# async def delete_like(from_uid: int, to_uid: int):
#     await LeoMatchLikesBasketModel.filter(from_user=await get_leo(from_uid), to_user=await get_leo(to_uid)).update(
#         done=True)
#
#
# @dataclass
# class Analitics:
#     count_users: int
#     count_man: int
#     count_female: int
#
#
# async def get_analitics(bot_username: str = None):
#     kwargs = {}
#     if bot_username:
#         kwargs['bot_username'] = bot_username
#     users = LeoMatchModel.filter(**kwargs, active=True, search=True).all()
#     man = users.filter(sex=SexEnum.MALE)
#     female = users.filter(sex=SexEnum.FEMALE)
#     return Analitics(await users.count(), await man.count(), await female.count())

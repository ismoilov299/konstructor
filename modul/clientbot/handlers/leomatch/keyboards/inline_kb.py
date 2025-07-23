from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
# from clientbot.handlers.leomatch.data.callback_datas import LeomatchLikeAction, LeomatchProfileAction, LeomatchProfileAlert, LeomatchProfileBlock, LikeActionEnum, ProfileActionEnum
# from aiogram.utils.i18n import gettext as _

from modul.clientbot.handlers.leomatch.data.callback_datas import LeomatchProfileAction, LeomatchLikeAction, \
    ProfileActionEnum, LikeActionEnum, LeomatchProfileAlert, LeomatchProfileBlock


def profile_view_action(user_id: int):
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="👍", callback_data=LeomatchProfileAction(action=ProfileActionEnum.LIKE, user_id=user_id).pack()),
        InlineKeyboardButton(text="💌", callback_data=LeomatchProfileAction(action=ProfileActionEnum.MESSAGE, user_id=user_id).pack()),
        InlineKeyboardButton(text="⚠️", callback_data=LeomatchLikeAction(action=ProfileActionEnum.REPORT, user_id=user_id).pack()),
        # InlineKeyboardButton(text="💤", callback_data=LeomatchProfileAction(action=ProfileActionEnum.SLEEP).pack()),
        InlineKeyboardButton(text="👎", callback_data=LeomatchProfileAction(action=ProfileActionEnum.DISLIKE).pack()),
        width=4
    )
    return builder.as_markup()

def profile_like_action(user_id: int):
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="❤️", callback_data=LeomatchLikeAction(action=LikeActionEnum.LIKE, user_id=user_id).pack()),
        InlineKeyboardButton(text="👎", callback_data=LeomatchLikeAction(action=LikeActionEnum.DISLIKE, user_id=user_id).pack()),
        # InlineKeyboardButton(text="⚠️", callback_data=LeomatchLikeAction(action=LikeActionEnum.REPORT, user_id=user_id).pack()),
        width=4
    )
    return builder.as_markup()


def profile_alert(sender_id: int, account_id: int):
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text= ("Да"), callback_data=LeomatchProfileAlert(action="yes", sender_id=sender_id,
                                                                              account_id=account_id).pack()),
        InlineKeyboardButton(text= ("Нет"), callback_data=LeomatchProfileAlert(action="no").pack()),
        width=2
    )
    return builder.as_markup()


def profile_alert_action(sender_id: int, account_id: int):
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text= ("Заблокировать"), callback_data=LeomatchProfileBlock(account_id=account_id).pack()),
        InlineKeyboardButton(text= ("Заблокировать отправителя"),
                             callback_data=LeomatchProfileBlock(account_id=sender_id).pack()),
        InlineKeyboardButton(text= ("Отменить"), callback_data=LeomatchProfileBlock().pack()),
        width=2
    )
    return builder.as_markup()

def write_profile(username_or_uid: str, is_username: bool = False):
    builder = InlineKeyboardBuilder()
    link = f"https://t.me/{username_or_uid}" if is_username else f"tg://user?id={username_or_uid}"
    builder.row(
        InlineKeyboardButton(text= ("Написать"), url=link),
        width=4
    )
    return builder.as_markup()

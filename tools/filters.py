from typing import Union

from pyrogram import filters
from pyrogram.types import Message, CallbackQuery

from config.config import bot_cfg
from tools.step_statu import StepStatu


async def __is_admin(_, __, update: Union[Message, CallbackQuery]) -> bool:
    """
    是管理员
    :return:
    """
    user_id = update.from_user.id
    return user_id == bot_cfg.admin


is_admin = filters.create(__is_admin)


async def __is_member(_, __, update: Union[Message, CallbackQuery]) -> bool:
    """
    是可用成员
    :return:
    """
    return not bot_cfg.member or update.chat.id in bot_cfg.member


is_member = filters.create(__is_member)


def step_filter(step: str):
    def func(_, __, msg: Message):
        if not msg.from_user:
            return False
        return StepStatu().step_statu(
            msg.from_user.id, step
        ) and not msg.text.startswith("/")

    return filters.create(func)

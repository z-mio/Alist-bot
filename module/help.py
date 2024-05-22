from pyrogram import filters, Client
from pyrogram.types import Message

from tools.filters import is_admin, is_member


@Client.on_message(filters.command("start") & is_member)
async def start(_, message: Message):
    await message.reply("发送 `/s+文件名` 进行搜索")


@Client.on_message(filters.command("help") & filters.private & is_admin)
async def _help(_, message: Message):
    text = """
发送图片查看图床功能
"""
    await message.reply(text)

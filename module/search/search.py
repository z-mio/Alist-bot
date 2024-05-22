# -*- coding: UTF-8 -*-
import asyncio
import math
import urllib.parse

from pyrogram import Client, filters
from pyrogram.errors import MessageNotModified
from pyrogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    CallbackQuery,
)

from api.alist.alist_api import alist
from api.alist.base import Content
from config.config import search_cfg, bot_cfg, DT
from tools.filters import is_admin, is_member
from tools.utils import pybyte, schedule_delete_messages

PAGE: dict[str, "Page"] = {}


class Page:
    def __init__(self, text: list[str] = None):
        self.index = 0
        self.text = text
        self.per_page = search_cfg.per_page
        self.page_count = math.ceil(len(text) / self.per_page)

    def now_page(self) -> str:
        i = self.index * self.per_page
        text = self.text[i : i + self.per_page]
        return "".join(text)

    def next_page(self) -> str:
        if self.index < self.page_count - 1:
            self.index += 1
        return self.now_page()

    def previous_page(self) -> str:
        if self.index > 0:
            self.index -= 1
        return self.now_page()

    @property
    def btn(self) -> list:
        return [
            [
                InlineKeyboardButton(
                    f"{self.index + 1}/{self.page_count}", callback_data="search_pages"
                )
            ],
            [
                InlineKeyboardButton("⬆️上一页", callback_data="search_previous_page"),
                InlineKeyboardButton("⬇️下一页", callback_data="search_next_page"),
            ],
        ]


# 设置每页数量
@Client.on_message(filters.command("sl") & is_admin)
async def sl(_, msg: Message):
    sl_str = " ".join(msg.command[1:])
    if sl_str.isdigit():
        search_cfg.per_page = int(sl_str)
        await msg.reply(f"已修改: 每页 __{sl_str}__ 条")
    else:
        await msg.reply("例: `/sl 5`")


# 设置直链
@Client.on_message(filters.command("zl") & is_admin)
async def zl(_, msg: Message):
    z = search_cfg.z_url
    search_cfg.z_url = not z
    await msg.reply(f"{'已关闭' if z else '已开启'}直链")


# 设置定时删除时间
@Client.on_message(filters.command("dt") & is_admin)
async def timed_del(_, msg: Message):
    dt = " ".join(msg.command[1:])
    if msg.chat.type.value == "private":
        return await msg.reply("请在群组或频道中使用此命令")
    if dt.isdigit():
        if int(dt) == 0:
            search_cfg.timed_del = DT(msg.chat.id, 0)
            return await msg.reply("已关闭定时删除")
        search_cfg.timed_del = DT(msg.chat.id, int(dt))
        await msg.reply(f"已修改: __{dt}__ 秒后删除")
    else:
        await msg.reply("设置搜索结果定时删除时间, 0为关闭, 单位: 秒\n例: `/dt 60`")


# 搜索
@Client.on_message(filters.command("s") & is_member)
async def s(cli: Client, message: Message):
    k = " ".join(message.command[1:])
    if not k:
        return await message.reply("请加上文件名，例：`/s 巧克力`")
    msg = await message.reply("搜索中...")

    result = await alist.search(k)
    if not (c := result.data.content):
        return await msg.edit("未搜索到文件，换个关键词试试吧")

    text, button = await build_result(c, message)
    msg = await msg.edit(
        text=text,
        reply_markup=InlineKeyboardMarkup(button),
        disable_web_page_preview=True,
    )

    # 群组,频道中定时删除消息
    if (
        getattr(search_cfg.timed_del, "time", False)
        and message.chat.type.value != "private"
    ):
        await schedule_delete_messages(
            cli,
            message.chat.id,
            [message.id, msg.id],
            delay_seconds=search_cfg.timed_del.time,
        )


async def build_result(content: list[Content], message: Message) -> (str, list):
    """构建搜索结果消息"""
    task = [build_result_item(count, item) for count, item in enumerate(content)]
    text = list(await asyncio.gather(*task))

    cmid = f"{message.chat.id}|{message.id + 1}"
    page = Page(text)
    PAGE[cmid] = page
    text = page.now_page()
    return text, page.btn


async def build_result_item(count: int, item: Content) -> str:
    """构建搜索结果消息体"""
    file_name, path, file_size, folder = item.name, item.parent, item.size, item.is_dir

    # 如果不是文件夹并且启用了直链，则获取文件直链
    dl = (
        f" | [直接下载]({(await alist.fs_get(f'{path}/{file_name}')).data.raw_url})"
        if not folder and search_cfg.z_url
        else ""
    )

    fl = urllib.parse.quote(f"{bot_cfg.alist_web}{path}/{file_name}", safe=":/")
    file_type = "📁文件夹" if folder else "📄文件"

    return f"{count + 1}.{file_type}: `{file_name}`\n[🌐打开网站]({fl}){dl} | __{pybyte(file_size)}__\n\n"


# 翻页
@Client.on_callback_query(filters.regex(r"^search"))
async def search_button_callback(_, query: CallbackQuery):
    data, msg = query.data, query.message
    cmid = f"{msg.chat.id}|{msg.id}"
    page = PAGE.get(cmid)
    match data:
        case "search_next_page":
            text = page.next_page()
        case "search_previous_page":
            text = page.previous_page()
        case _:
            return
    try:
        await msg.edit(
            text,
            reply_markup=InlineKeyboardMarkup(page.btn),
            disable_web_page_preview=True,
        )
    except MessageNotModified:
        ...

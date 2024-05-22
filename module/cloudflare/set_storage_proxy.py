import asyncio
import random

from pyrogram import filters, Client
from pyrogram.types import CallbackQuery, Message

from api.alist.alist_api import alist
from config.config import cf_cfg
from module.cloudflare.utile import re_remark
from tools.filters import step_filter
from tools.step_statu import step


@Client.on_callback_query(filters.regex("^random_node$"))
async def random_node_callback(_, cq: CallbackQuery):
    await cq.message.edit("正在设置随机代理...")
    if e := await set_random_node():
        return await cq.message.edit(f"设置失败: {e}")
    return await cq.message.edit("存储随机代理|完成!")


@Client.on_callback_query(filters.regex("^unified_node$"))
async def unified_node_callback(_, cq: CallbackQuery):
    await cq.message.edit("请发送节点地址, 需要加上协议\n例: `https://example.com`")
    step.set_step(cq.from_user.id, "unified_node", True)
    step.insert(cq.from_user.id, msg=cq.message)


@Client.on_message(filters.text & filters.private & step_filter("unified_node"))
async def set_unified_node(_, msg: Message):
    step.init(msg.from_user.id)
    m: Message = step.get(msg.from_user.id, "msg")
    m = await m.reply("正在设置统一代理...")
    if e := await set_random_node(msg.text):
        return await msg.reply(f"设置失败: {e}")
    await m.edit("存储统一代理|完成!")


async def set_random_node(node: str = None):
    """设置节点代理"""
    storage_list = await alist.storage_list()
    nodes = [f"https://{node.url}" for node in cf_cfg.nodes]
    for storage in storage_list.data:
        if storage.webdav_policy == "use_proxy_url" or storage.web_proxy:
            storage.down_proxy_url = node or random.choice(nodes)
            storage.remark = re_remark(storage.remark, storage.down_proxy_url)
    task = [alist.storage_update(s) for s in storage_list.data]
    try:
        await asyncio.gather(*task)
    except Exception as e:
        return e

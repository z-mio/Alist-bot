# -*- coding: UTF-8 -*-
import asyncio

import httpx
import pyrogram
import uvicorn
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from loguru import logger
from pyrogram import Client, filters
from pyrogram.types import BotCommand, Message

from api.alist.alist_api import alist
from config.config import bot_cfg, plb_cfg
from tools.filters import is_admin

logger.add("logs/bot.log", rotation="5 MB")

scheduler = AsyncIOScheduler()

proxy = {
    "scheme": bot_cfg.scheme,  # 支持“socks4”、“socks5”和“http”
    "hostname": bot_cfg.hostname,
    "port": bot_cfg.port,
}

plugins = dict(root="module")
app = Client(
    "my_bot",
    proxy=proxy if all(proxy.values()) else None,
    bot_token=bot_cfg.bot_token,
    api_id=bot_cfg.api_id,
    api_hash=bot_cfg.api_hash,
    plugins=plugins,
    lang_code="zh",
)


# 设置菜单
@app.on_message(filters.command("menu") & filters.private & is_admin)
async def menu(_, message: Message):
    # 管理员私聊可见
    admin_cmd = {
        "s": "搜索文件",
        "roll": "随机推荐",
        "sl": "设置搜索结果数量",
        "zl": "开启/关闭直链",
        "dt": "设置搜索结果定时删除",
        "st": "存储管理",
        "sf": "Cloudflare节点管理",
        "vb": "查看下载节点信息",
        "bc": "备份Alist配置",
        "sbt": "设置定时备份",
        "sr": "随机推荐设置",
        "od": "离线下载",
        "help": "查看帮助",
    }
    # 全部可见
    user_cmd = {
        "s": "搜索文件",
        "roll": "随机推荐",
        "vb": "查看下载节点信息",
    }
    admin_cmd = [BotCommand(k, v) for k, v in admin_cmd.items()]
    user_cmd = [BotCommand(k, v) for k, v in user_cmd.items()]

    await app.delete_bot_commands()
    await app.set_bot_commands(
        admin_cmd, scope=pyrogram.types.BotCommandScopeChat(chat_id=bot_cfg.admin)
    )
    await app.set_bot_commands(user_cmd)
    await message.reply("菜单设置成功，请退出聊天界面重新进入来刷新菜单")


# bot启动时验证
def checking():
    try:
        app.loop.run_until_complete(alist.storage_list())
    except httpx.HTTPStatusError:
        logger.error("连接Alist失败，请检查配置alist_host是否填写正确")
        exit()
    except httpx.ReadTimeout:
        logger.error("连接Alist超时，请检查网站状态")
        exit()
    return logger.info("Bot开始运行...")


fast = FastAPI()


def run_fastapi():
    async def _start():
        c = uvicorn.Config(
            "bot:fast", port=plb_cfg.port, log_level="error", host="0.0.0.0"
        )
        server = uvicorn.Server(c)
        await server.serve()

    if plb_cfg.enable:
        names = [task.get_name() for task in asyncio.all_tasks(app.loop)]
        if "fastapi" not in names:
            app.loop.create_task(_start(), name="fastapi")
        logger.info(f"代理负载均衡已启动 | http://127.0.0.1:{plb_cfg.port}")


if __name__ == "__main__":
    checking()
    from module.init import init_task

    init_task(app)
    run_fastapi()
    app.run()

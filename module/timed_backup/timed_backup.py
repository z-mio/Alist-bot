# -*- coding: UTF-8 -*-
import datetime
import json
import os

import croniter
from apscheduler.triggers.cron import CronTrigger
from loguru import logger
from pyrogram import Client, filters
from pyrogram.types import Message

from api.alist.alist_api import alist
from api.alist.base.base import AListAPIResponse
from config.config import bot_cfg, DOWNLOADS_PATH
from tools.filters import is_admin
from tools.scheduler_manager import aps
from tools.utils import parse_cron


# 备份alist配置
async def backup_config():
    bc_dic = {
        "encrypted": "",
        "settings": await alist.setting_list(),
        "users": await alist.user_list(),
        "storages": await alist.storage_list(),
        "metas": await alist.meta_list(),
    }
    for k, v in bc_dic.items():
        if isinstance(v, AListAPIResponse):
            bc_dic[k] = (
                v.raw_data.get("content")
                if isinstance(v.raw_data, dict)
                else v.raw_data
            )

    data = json.dumps(bc_dic, indent=4, ensure_ascii=False)  # 格式化json
    now = datetime.datetime.now()
    current_time = now.strftime("%Y_%m_%d_%H_%M_%S")  # 获取当前时间
    bc_file_name = DOWNLOADS_PATH.joinpath(f"alist_backup_{current_time}.json")
    with open(bc_file_name, "w", encoding="utf-8") as b:
        b.write(data)
    return bc_file_name


# 监听回复消息的消息
@Client.on_message(
    (filters.text & filters.reply & filters.private) & ~filters.regex("^/") & is_admin
)
async def echo_bot(_, message: Message):
    if message.reply_to_message.document:  # 判断回复的消息是否包含文件
        await message.delete()
        await message.reply_to_message.edit_caption(
            caption=f"#Alist配置备份\n{message.text}",
        )


# 发送备份文件
@Client.on_message(filters.command("bc") & filters.private & is_admin)
async def send_backup_file(_, message: Message):
    bc_file_name = await backup_config()
    await message.reply_document(document=bc_file_name, caption="#Alist配置备份")
    os.remove(bc_file_name)


# 定时任务——发送备份文件
async def recovery_send_backup_file(cli: Client):
    bc_file_name = await backup_config()
    await cli.send_document(
        chat_id=bot_cfg.admin, document=bc_file_name, caption="#Alist配置定时备份"
    )
    os.remove(bc_file_name)
    logger.info("定时备份成功")


def start_timed_backup(app):
    if bot_cfg.backup_time != "0":
        aps.add_job(
            func=recovery_send_backup_file,
            args=[app],
            trigger=CronTrigger.from_crontab(bot_cfg.backup_time),
            job_id="send_backup_messages_regularly_id",
        )
        logger.info("定时备份已启动")


# 设置备份时间&开启定时备份
@Client.on_message(filters.command("sbt") & filters.private & is_admin)
async def set_backup_time(cli: Client, message: Message):
    mtime = " ".join(message.command[1:])
    if len(mtime.split()) == 5:
        bot_cfg.backup_time = mtime
        cron = croniter.croniter(bot_cfg.backup_time, datetime.datetime.now())
        next_run_time = cron.get_next(datetime.datetime)  # 下一次备份时间
        if aps.job_exists("send_backup_messages_regularly_id"):
            aps.modify_job(
                job_id="send_backup_messages_regularly_id",
                trigger=CronTrigger.from_crontab(bot_cfg.backup_time),
            )
            text = f"修改成功！\n下一次备份时间：{next_run_time}"
        else:
            aps.add_job(
                func=recovery_send_backup_file,
                trigger=CronTrigger.from_crontab(bot_cfg.backup_time),
                job_id="send_backup_messages_regularly_id",
                args=[cli],
            )
            text = f"已开启定时备份！\n下一次备份时间：{next_run_time}"
        await message.reply(text)
    elif mtime == "0":
        bot_cfg.backup_time = mtime
        aps.pause_job("send_backup_messages_regularly_id")
        await message.reply("已关闭定时备份")
    elif not mtime:
        text = f"""
格式：/sbt + 5位cron表达式，0为关闭
下一次备份时间：`{parse_cron(bot_cfg.backup_time) if bot_cfg.backup_time != '0' else '已关闭'}`

例：
<code>/sbt 0</code> 关闭定时备份
<code>/sbt 0 8 * * *</code> 每天上午8点运行
<code>/sbt 30 20 */3 * *</code> 每3天晚上8点30运行

 5位cron表达式格式说明
  ——分钟（0 - 59）
 |  ——小时（0 - 23）
 | |  ——日（1 - 31）
 | | |  ——月（1 - 12）
 | | | |  ——星期（0 - 6，0是星期一）
 | | | | |
 * * * * *

"""
        await message.reply(text)
    else:
        await message.reply("格式错误")

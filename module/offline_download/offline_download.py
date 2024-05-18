# -*- coding: UTF-8 -*-
import argparse
import prettytable as pt
from pyrogram import filters, Client
from pyrogram.enums.parse_mode import ParseMode
from pyrogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    CallbackQuery,
)

from api.alist_api import AListAPI
from tool.scheduler_manager import aps
from config.config import admin

from tool.utils import is_admin

DOWNLOAD_TOOL = "download_tool"
DOWNLOAD_PATH = "download_path"
DOWNLOAD_STRATEGY = "download_strategy"
DOWNLOAD_URL = "download_url"

# 下载策略
DOWNLOAD_STRATEGIES = {
    "delete_on_upload_succeed": "上传成功后删除",
    "delete_on_upload_failed": "上传失败时删除",
    "delete_never": "从不删除",
    "delete_always": "总是删除"
}

download_params = {
    DOWNLOAD_TOOL: None,
    DOWNLOAD_PATH: None,
    DOWNLOAD_STRATEGY: None,
    DOWNLOAD_URL: None
}

storage_mount_path = []

# 离线下载默认设置
default_setting = {}


# 获取下个步骤
async def _next(client, message, previous_step):
    if previous_step is None:
        # 不存在默认工具设置
        if DOWNLOAD_TOOL not in default_setting:
            return await message.reply(
                text="请选择离线下载工具",
                reply_markup=InlineKeyboardMarkup(await get_offline_download_tool("od_tool_"))
            )
        else:
            return await _next(client, message, "show_tool_menu")

    if previous_step == "show_tool_menu":
        # 不存在默认路径设置
        if DOWNLOAD_PATH not in default_setting:
            return await message.reply(
                text="请选择存储路径",
                reply_markup=InlineKeyboardMarkup(await get_offline_download_path("od_path_"))
            )
        else:
            return await _next(client, message, "show_path_menu")

    if previous_step == "show_path_menu":
        # 不存在默认策略设置
        if DOWNLOAD_STRATEGY not in default_setting:
            return await message.reply(
                text="请选择下载策略",
                reply_markup=InlineKeyboardMarkup(get_offline_download_strategies("od_strategy_"))
            )
        else:
            return await _next(client, message, "show_strategy_menu")

    if previous_step == "show_strategy_menu":
        res = await AListAPI.offline_download(
            urls=download_params[DOWNLOAD_URL],
            tool=default_setting[DOWNLOAD_TOOL] if DOWNLOAD_TOOL in default_setting else download_params[DOWNLOAD_TOOL],
            path=default_setting[DOWNLOAD_PATH] if DOWNLOAD_PATH in default_setting else download_params[DOWNLOAD_PATH],
            delete_policy=default_setting[
                DOWNLOAD_STRATEGY] if DOWNLOAD_STRATEGY in default_setting else download_params[DOWNLOAD_STRATEGY]
        )

        if res["code"] != 200:
            return await message.reply(text=f"❌离线任务创建失败，原因如下\n{res['message']}")

        content = ["🎉离线任务已创建"]

        for url in download_params[DOWNLOAD_URL]:
            content.append(f"资源地址：{url}")

        content.append(
            "离线工具：" +
            (default_setting[DOWNLOAD_TOOL] if DOWNLOAD_TOOL in default_setting else download_params[DOWNLOAD_TOOL])
        )

        content.append(
            "存储路径：" + (default_setting[DOWNLOAD_PATH] if DOWNLOAD_PATH in default_setting else download_params[
                DOWNLOAD_PATH]))

        content.append("离线策略：" + (
            DOWNLOAD_STRATEGIES[default_setting[DOWNLOAD_STRATEGY]]
            if DOWNLOAD_STRATEGY in default_setting
            else DOWNLOAD_STRATEGIES[download_params[DOWNLOAD_STRATEGY]]
        ))

        await message.reply(text="\n".join(content))

        job_id = "offline_download_progress_notify"

        return aps.add_job(
            func=progress_notify,
            args=[client, job_id],
            trigger="interval",
            seconds=5,
            job_id=job_id,
        )


# 下载进度通知
async def progress_notify(client: Client, job_id: str):
    undone_resp = await AListAPI.get_offline_download_undone_task()
    done_resp = await AListAPI.get_offline_download_done_task()

    if len(undone_resp["data"]) == 0:
        aps.remove_job(job_id)

    if len(done_resp["data"]) > 0:
        await send_message(client, done_resp["data"])
        await AListAPI.clear_offline_download_done_task()


# 发送消息
async def send_message(client, tasks):
    table = pt.PrettyTable(['File', 'Task', 'Status', 'Reason'])
    table.align['File'] = 'l'
    table.valign['Task'] = 'm'
    table.valign['Status'] = 'm'
    table.valign['Reason'] = 'm'

    table._max_width = {"File": 9, "Task": 8, "Status": 7, "Reason": 6}

    for task in tasks:
        table.add_row([
            task["name"].split(" ")[1],
            "Download",
            "Success" if task["state"] == 2 else "Failed",
            task["error"] if task["state"] != 2 else "-"
        ],
            divider=True
        )

    await client.send_message(
        chat_id=admin,
        disable_web_page_preview=True,
        text=f'<pre>{table}</pre>'[:4096],
        parse_mode=ParseMode.HTML
    )


# 获取底部按钮
def get_bottom_buttons(prefix, should_have_return=True, should_have_close=True):
    buttons = []

    if should_have_return:
        buttons.append(InlineKeyboardButton("↩️返回", callback_data=f"{prefix}return"))

    if should_have_close:
        buttons.append(InlineKeyboardButton("❌关闭", callback_data=f"{prefix}close"))

    return buttons


# 获取离线下载策略按钮
def get_offline_download_strategies(prefix):
    buttons = []

    for key, value in DOWNLOAD_STRATEGIES.items():
        buttons.append([InlineKeyboardButton(value, callback_data=f"{prefix}{key}")])

    buttons.append(get_bottom_buttons(prefix))

    return buttons


# 解析命令
def parse_command(commands):
    parser = argparse.ArgumentParser(description="Process input arguments.")

    parser.add_argument("urls", metavar="url", type=str, nargs="+",
                        help="下载文件地址")
    parser.add_argument("--tool", "-t", dest="tool", type=str, nargs=1,
                        default=argparse.SUPPRESS,
                        help="下载工具")
    parser.add_argument("--path", "-p", dest="path", type=str, nargs=1,
                        default=argparse.SUPPRESS,
                        help="存储路径")
    parser.add_argument("--strategy", "-s", dest="strategy", type=str, nargs=1,
                        default=argparse.SUPPRESS,
                        help="下载策略")

    return parser.parse_args(commands)


# 离线下载
@Client.on_message(filters.command("od") & filters.private & is_admin)
async def start(client: Client, message: Message):
    try:
        args = parse_command(message.command[1:])
    except (Exception, SystemExit):
        return await message.reply(
            text="使用/od命令后加上若干个关键词，系统将下载至对应的存储中 \n例如：\n/od url \n/od url url2 \n",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("修改默认设置", callback_data=f"od_setting"),
                    InlineKeyboardButton("还原默认设置", callback_data=f"od_restore")
                ]
            ])
        )

    download_params[DOWNLOAD_URL] = args.urls

    await _next(client, message, previous_step=None)


# 菜单按钮回调
@Client.on_callback_query(filters.regex("(return|close)$"))
async def bottom_menu_callback(_, query: CallbackQuery):
    # 设置默认项时后退
    if ['od_update_tool_return', 'od_update_path_return', 'od_update_strategy_return'].count(query.data) > 0:
        return await show_setting_menu(_, query)

    # 关闭
    if query.data.endswith("close"):
        return await query.message.delete()


# 离线下载工具回调
@Client.on_callback_query(filters.regex("^od_tool_"))
async def tool_menu_callback(client: Client, query: CallbackQuery):
    download_params[DOWNLOAD_TOOL] = query.data.removeprefix("od_tool_")

    await _next(client, query.message, previous_step="show_tool_menu")


# 离线存储目录回调
@Client.on_callback_query(filters.regex("^od_path_"))
async def path_menu_callback(client: Client, query: CallbackQuery):
    download_params[DOWNLOAD_PATH] = storage_mount_path[int(query.data.removeprefix("od_path_"))]["mount_path"]

    await _next(client, query.message, previous_step="show_path_menu")


# 离线策略回调
@Client.on_callback_query(filters.regex("^od_strategy_"))
async def strategy_menu_callback(client: Client, query: CallbackQuery):
    download_params[DOWNLOAD_STRATEGY] = query.data.removeprefix("od_strategy_")

    await _next(client, message=query.message, previous_step="show_strategy_menu")


# 设置菜单
@Client.on_callback_query(filters.regex("^od_setting"))
async def show_setting_menu(_, query: CallbackQuery):
    await query.message.reply(
        text="请选择需要修改的设置项：",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("修改离线工具", callback_data=f"od_edit_tool")],
            [InlineKeyboardButton("修改存储路径", callback_data=f"od_edit_path")],
            [InlineKeyboardButton("修改下载策略", callback_data=f"od_edit_strategy")],
            get_bottom_buttons("od_edit_", should_have_return=False)
        ])
    )


# 修改设置项
@Client.on_callback_query(filters.regex("^od_edit_"))
async def show_setting_sub_menu(_, query: CallbackQuery):
    if query.data == "od_edit_tool":
        await query.message.reply(
            text="当前默认离线工具：<b>" +
                 (default_setting[DOWNLOAD_TOOL] if DOWNLOAD_TOOL in default_setting else "未设置") +
                 "</b>，你可以修改为以下任意一项",
            reply_markup=InlineKeyboardMarkup(await get_offline_download_tool("od_update_tool_"))
        )
    elif query.data == "od_edit_path":
        await query.message.reply(
            text="当前默认存储路径：<b>" +
                 (default_setting[DOWNLOAD_PATH] if DOWNLOAD_PATH in default_setting else "未设置") +
                 "</b>，你可以修改为以下任意一项",
            reply_markup=InlineKeyboardMarkup(await get_offline_download_path("od_update_path_"))
        )

    elif query.data == "od_edit_strategy":
        await query.message.reply(
            text="当前默认下载策略：<b>" +
                 (default_setting[DOWNLOAD_STRATEGY] if DOWNLOAD_STRATEGY in default_setting else "未设置") +
                 "</b>，你可以修改为以下任意一项",
            reply_markup=InlineKeyboardMarkup(get_offline_download_strategies("od_update_strategy_"))
        )


# 保存设置项
@Client.on_callback_query(filters.regex("^od_update_"))
async def update_setting(_, query: CallbackQuery):
    value = query.data

    if value.startswith("od_update_tool_"):
        default_setting[DOWNLOAD_TOOL] = value.removeprefix("od_update_tool_")
        await query.message.reply(text=f"✅默认离线工具设置成功")
    elif value.startswith("od_update_path_"):
        default_setting[DOWNLOAD_PATH] = storage_mount_path[int(value.removeprefix("od_update_path_"))]["mount_path"]
        await query.message.reply(text=f"✅默认存储路径设置成功")
    elif value.startswith("od_update_strategy_"):
        default_setting[DOWNLOAD_STRATEGY] = value.removeprefix("od_update_strategy_")
        await query.message.reply(text=f"✅默认下载策略设置成功")


# 还原设置项
@Client.on_callback_query(filters.regex("^od_restore"))
async def restore_setting(_, query: CallbackQuery):
    global default_setting

    default_setting = {}

    await query.message.reply(text=f"✅离线下载设置已还原")


# 获取存储并写入列表
async def get_offline_download_path(prefix):
    global storage_mount_path

    buttons = []

    response = await AListAPI.storage_list()

    storage_mount_path = response["data"]["content"]

    for index in range(len(storage_mount_path)):
        buttons.append([
            InlineKeyboardButton(
                text=storage_mount_path[index]["mount_path"],
                callback_data=prefix + str(index),
            )
        ])

    buttons.append(get_bottom_buttons(prefix))

    return buttons


# 获取离线下载工具
async def get_offline_download_tool(prefix):
    buttons = []

    response = await AListAPI.get_offline_download_tools()  # 获取离线下载工具列表

    response["data"].sort()

    for item in response["data"]:
        buttons.append([
            InlineKeyboardButton(
                item,
                callback_data=prefix + item
            )
        ])

    buttons.append(get_bottom_buttons(prefix))

    return buttons

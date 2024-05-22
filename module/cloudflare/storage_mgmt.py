import asyncio
import random
from itertools import chain

from apscheduler.triggers.cron import CronTrigger
from loguru import logger
from pyrogram import filters, Client
from pyrogram.enums.parse_mode import ParseMode
from pyrogram.types import (
    InlineKeyboardMarkup,
    CallbackQuery,
)

from api.alist.alist_api import alist
from api.alist.base.storage.get import StorageInfo
from bot import run_fastapi
from config.config import cf_cfg, chat_data, bot_cfg, plb_cfg
from module.cloudflare.cloudflare import build_node_info, r_cf_menu
from module.cloudflare.utile import check_node_status, NodeStatus, re_remark
from tools.scheduler_manager import aps

_D = {
    "auto_switch_nodes": "自动切换节点",
    "status_push": "节点状态推送",
    "storage_mgmt": "自动存储管理",
    "bandwidth_push": "每日流量统计",
    "proxy_load_balance": "代理负载均衡",
}


def switch(client: Client, enable: bool, option, job_id, mode):
    setattr(cf_cfg, option, enable)
    logger.info(f"已{'开启' if enable else '关闭'}:{_D[option]}")

    job_functions = {
        "cronjob_bandwidth_push": send_cronjob_bandwidth_push,
        "cronjob_status_push": send_cronjob_status_push,
    }

    if (
        not any([cf_cfg.status_push, cf_cfg.storage_mgmt, cf_cfg.auto_switch_nodes])
        or option == "bandwidth_push"
    ):
        logger.info("已关闭:节点监控")
        aps.pause_job(job_id)
    elif enable:
        aps.resume_job(job_id=job_id)
        args = (
            {"trigger": CronTrigger.from_crontab(cf_cfg.time)}
            if mode == 0
            else {"trigger": "interval", "seconds": 60}
        )
        aps.add_job(
            func=job_functions[job_id],
            args=[client],
            job_id=job_id,
            **args,
        )


async def toggle_auto_management(
    client: Client, cq: CallbackQuery, option, job_id, mode
):
    is_option_on = cq.data == f"{option}_on"
    switch(client, is_option_on, option, job_id, mode)
    await r_cf_menu(cq)


# 按钮回调 节点状态
@Client.on_callback_query(filters.regex("^status_push"))
async def status_push(cli: Client, cq: CallbackQuery):
    await toggle_auto_management(cli, cq, "status_push", "cronjob_status_push", 1)


# 按钮回调 每日带宽统计
@Client.on_callback_query(filters.regex("^bandwidth_push"))
async def bandwidth_push(cli: Client, cq: CallbackQuery):
    await toggle_auto_management(cli, cq, "bandwidth_push", "cronjob_bandwidth_push", 0)


# 按钮回调 自动存储管理
@Client.on_callback_query(filters.regex("^storage_mgmt"))
async def storage_mgmt(cli: Client, cq: CallbackQuery):
    await toggle_auto_management(cli, cq, "storage_mgmt", "cronjob_status_push", 1)


# 按钮回调 自动切换节点
@Client.on_callback_query(filters.regex("^auto_switch_nodes"))
async def auto_switch_nodes(cli: Client, cq: CallbackQuery):
    await toggle_auto_management(cli, cq, "auto_switch_nodes", "cronjob_status_push", 1)


# 按钮回调 代理负载均衡
@Client.on_callback_query(filters.regex("^proxy_load_balance"))
async def proxy_load_balance_switch(_, cq: CallbackQuery):
    plb_cfg.enable = not plb_cfg.enable
    if plb_cfg.enable:
        run_fastapi()
    logger.info(f"已{'开启' if plb_cfg.enable else '关闭'}:代理负载均衡")
    await r_cf_menu(cq)


# 带宽通知定时任务
async def send_cronjob_bandwidth_push(app):
    if cf_cfg.nodes:
        ni = await build_node_info(0)
        text = "今日流量统计"
        for i in cf_cfg.chat_id:
            await app.send_message(
                chat_id=i,
                text=text,
                reply_markup=InlineKeyboardMarkup([ni.button_b, ni.button_c]),
            )


def start_bandwidth_push(app):
    if cf_cfg.bandwidth_push:
        aps.add_job(
            func=send_cronjob_bandwidth_push,
            args=[app],
            trigger=CronTrigger.from_crontab(cf_cfg.time),
            job_id="cronjob_bandwidth_push",
        )
        logger.info("带宽通知已启动")


# 节点状态通知定时任务
async def send_cronjob_status_push(app: Client):
    if not cf_cfg.nodes:
        return

    nodes = [value.url for value in cf_cfg.nodes]
    task = [check_node_status(node) for node in nodes]
    # 全部节点
    results = list(await asyncio.gather(*task))
    # 可用节点
    available_nodes = await returns_the_available_nodes(results)

    task = [r_(node, status_code) for node, status_code in results]
    result = [i for i in await asyncio.gather(*task, return_exceptions=True) if i]

    tasks = [
        failed_node_management(app, node, status, available_nodes)
        for node, status in result
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    if flat_results := list(
        chain.from_iterable(result for result in results if result)
    ):
        text = "\n\n".join(flat_results)
        logger.info(text)
        await app.send_message(
            chat_id=bot_cfg.admin,
            text=text,
            disable_web_page_preview=True,
            parse_mode=ParseMode.HTML,
        )


def start_status_push(app):
    if any([cf_cfg.status_push, cf_cfg.storage_mgmt, cf_cfg.auto_switch_nodes]):
        aps.add_job(
            func=send_cronjob_status_push,
            args=[app],
            trigger="interval",
            job_id="cronjob_status_push",
            seconds=60,
        )
        logger.info("节点监控已启动")


# 检测全部节点状态
async def r_(node, status_code):
    # 第一次获取默认设置为状态正常
    if not chat_data.get(node):
        chat_data[node] = 200
        chat_data[f"{node}_count"] = 0

    if status_code != 200:
        chat_data[f"{node}_count"] += 1

        # 错误大于3次运行，否则不运行后面代码
        if 0 < chat_data[f"{node}_count"] <= 3:
            return []
    return [node, status_code]


async def failed_node_management(
    app: Client, node, status_code, available_nodes
) -> list:
    # 如果和上一次状态码一样，则不执行
    if status_code == chat_data[node]:
        return []
    chat_data[node] = status_code
    chat_data[f"{node}_count"] = 0
    # 状态通知
    await notify_status_change(app, node, status_code)

    # 自动管理
    try:
        st = (await alist.storage_list()).data
    except Exception:
        logger.error("自动管理存储错误：获取存储列表失败")
    else:
        task = [manage_storage(dc, node, status_code, available_nodes) for dc in st]
        return [i for i in await asyncio.gather(*task, return_exceptions=True) if i]


async def manage_storage(dc: StorageInfo, node, status_code, available_nodes) -> str:
    # 如果代理url等于node，且存储开启了代理
    proxy_url = f"https://{node}"
    use_proxy = dc.webdav_policy == "use_proxy_url" or dc.web_proxy
    if dc.down_proxy_url != proxy_url or not use_proxy:
        return ""

    # 节点正常且存储关闭
    if status_code == 200 and dc.disabled:
        await alist.storage_enable(dc.id)
        return f"🟢|<code>{node}</code>|已开启存储:\n<code>{dc.mount_path}</code>"
    # 节点失效且存储开启
    if status_code != 200 and not dc.disabled:
        # 开启自动切换节点切有可用节点
        if cf_cfg.auto_switch_nodes and available_nodes:
            random_node = random.choice(available_nodes)
            dc.down_proxy_url = random_node
            d = random_node.replace("https://", "")

            dc.remark = re_remark(dc.remark, d)

            await alist.storage_update(dc)
            return f"🟡|<code>{dc.mount_path}</code>\n已自动切换节点: <code>{node}</code> >> <code>{d}</code>"
        elif cf_cfg.storage_mgmt:
            await alist.storage_disable(dc.id)
            return f"🔴|<code>{node}</code>|已关闭存储:\n<code>{dc.mount_path}</code>"


# 筛选出可用节点
async def returns_the_available_nodes(results: list[NodeStatus]) -> list:
    """
    筛选出可用节点，移除已用节点
    :param results:
    :return:
    """
    # 可用节点
    node_pool = [f"https://{ns.url}" for ns in results if ns.status == 200]
    # 已经在使用的节点
    sl = (await alist.storage_list()).data
    used_node = [
        node.down_proxy_url
        for node in sl
        if node.webdav_policy == "use_proxy_url" or node.web_proxy
    ]
    # 将已用的节点从可用节点中删除，删除后没有节点了就重复使用节点
    return [x for x in node_pool if x not in used_node] or node_pool


# 发送节点状态
async def notify_status_change(app: Client, node, status_code):
    t_l = {200: f"🟢|<code>{node}</code>|恢复", 429: f"🔴|<code>{node}</code>|掉线"}
    text = t_l.get(status_code, f"⭕️|<code>{node}</code>|故障")
    logger.info(text) if status_code == 200 else logger.warning(text)

    if cf_cfg.status_push:
        for chat_id in cf_cfg.chat_id:
            try:
                await app.send_message(
                    chat_id=chat_id, text=text, parse_mode=ParseMode.HTML
                )
            except Exception as ex:
                logger.error(f"节点状态发送失败|{chat_id}::{ex}")

import asyncio
import random
from itertools import chain

from apscheduler.triggers.cron import CronTrigger
from loguru import logger
from pyrogram import filters, Client
from pyrogram.types import (
    InlineKeyboardMarkup,
    CallbackQuery,
)

from api.alist_api import AListAPI
from config.config import nodee, cloudflare_cfg, chat_data, write_config, admin
from module.cloudflare.cloudflare import check_node_status, get_node_status, r_cf_menu
from tool.scheduler_manager import aps


async def toggle_auto_management(
    client: Client, message: CallbackQuery, option, job_id, mode
):
    query = message.data
    if query == f"{option}_off":
        cloudflare_cfg["cronjob"][option] = False
        logger.info(f"已关闭{option}")
        cc = cloudflare_cfg["cronjob"]
        abc = all(
            not cc[key] for key in ("status_push", "storage_mgmt", "auto_switch_nodes")
        )
        if abc or option == "bandwidth_push":
            logger.info("节点监控已关闭")
            aps.pause_job(job_id)
    elif query == f"{option}_on":
        cloudflare_cfg["cronjob"][option] = True
        logger.info(f"已开启{option}")
        aps.resume_job(job_id=job_id)
        if mode == 0:
            aps.add_job(
                func=send_cronjob_bandwidth_push,
                args=[client],
                trigger=CronTrigger.from_crontab(cloudflare_cfg["cronjob"]["time"]),
                job_id=job_id,
            )
        elif mode == 1:
            aps.add_job(
                func=send_cronjob_status_push,
                args=[client],
                trigger="interval",
                job_id=job_id,
                seconds=60,
            )
    write_config("config/cloudflare_cfg.yaml", cloudflare_cfg)
    await r_cf_menu(message)


# 按钮回调 节点状态
@Client.on_callback_query(filters.regex("^status_push"))
async def status_push(client: Client, message: CallbackQuery):
    await toggle_auto_management(
        client, message, "status_push", "cronjob_status_push", 1
    )


# 按钮回调 每日带宽统计
@Client.on_callback_query(filters.regex("^bandwidth_push"))
async def bandwidth_push(client: Client, message: CallbackQuery):
    await toggle_auto_management(
        client, message, "bandwidth_push", "cronjob_bandwidth_push", 0
    )


# 按钮回调 自动存储管理
@Client.on_callback_query(filters.regex("^storage_mgmt"))
async def storage_mgmt(client: Client, message: CallbackQuery):
    await toggle_auto_management(
        client, message, "storage_mgmt", "cronjob_status_push", 1
    )


# 按钮回调 自动切换节点
@Client.on_callback_query(filters.regex("^auto_switch_nodes"))
async def auto_switch_nodes(client: Client, message: CallbackQuery):
    await toggle_auto_management(
        client, message, "auto_switch_nodes", "cronjob_status_push", 1
    )


# 带宽通知定时任务
async def send_cronjob_bandwidth_push(app):
    if nodee():
        vv = await get_node_status(0)
        text = "今日流量统计"
        for i in cloudflare_cfg["cronjob"]["chat_id"]:
            await app.send_message(
                chat_id=i, text=text, reply_markup=InlineKeyboardMarkup([vv[1], vv[2]])
            )


# 节点状态通知定时任务
async def send_cronjob_status_push(app: Client):
    if not nodee():
        return

    nodes = [value["url"] for value in nodee()]
    task = [check_node_status(node) for node in nodes]
    # 全部节点
    results = await asyncio.gather(*task)
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
        await app.send_message(chat_id=admin, text=text, disable_web_page_preview=True)


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
        st = await AListAPI.storage_list()
    except Exception:
        logger.error("自动管理存储错误：获取存储列表失败")
    else:
        task = [
            manage_storage(dc, node, status_code, available_nodes)
            for dc in st["data"]["content"]
        ]
        return [i for i in await asyncio.gather(*task, return_exceptions=True) if i]


async def manage_storage(dc, node, status_code, available_nodes) -> str:
    # 如果代理url等于node，且存储开启了代理
    proxy_url = f"https://{node}"
    use_proxy = dc.get("webdav_policy", "") == "use_proxy_url" or dc.get(
        "web_proxy", False
    )
    if dc.get("down_proxy_url") != proxy_url or not use_proxy:
        return ""

    alist = AListAPI()
    # 节点正常且存储关闭
    if status_code == 200 and dc["disabled"]:
        await alist.storage_enable(dc["id"])
        return f'🟢|`{node}`|已开启存储:\n`{dc["mount_path"]}`'
    # 节点失效且存储开启
    if status_code != 200 and not dc["disabled"]:
        # 开启自动切换节点切有可用节点
        if cloudflare_cfg["cronjob"]["auto_switch_nodes"] and available_nodes:
            random_node = random.choice(available_nodes)
            dc["down_proxy_url"] = random_node
            d = random_node.replace("https://", "")

            if "节点：" in dc["remark"]:
                dc["remark"] = "\n".join(
                    [
                        f"节点：{d}" if "节点：" in line else line
                        for line in dc["remark"].split("\n")
                    ]
                )
            else:
                dc["remark"] = f"节点：{d}\n{dc['remark']}"

            await alist.storage_update(dc)
            return f'🟡|`{dc["mount_path"]}`\n已自动切换节点: `{node}` >> `{d}`'
        elif cloudflare_cfg["cronjob"]["storage_mgmt"]:
            await alist.storage_disable(dc["id"])
            return f'🔴|`{node}`|已关闭存储:\n`{dc["mount_path"]}`'


# 筛选出可用节点
async def returns_the_available_nodes(results) -> list:
    """
    筛选出可用节点，移除已用节点（如果包括已用节点，存储会全部变成一个代理节点，就无法负载均衡了）
    :param results:
    :return:
    """
    # 可用节点
    node_pool = [f"https://{node}" for node, result in results if result == 200]
    # 已经在使用的节点
    sl = await AListAPI.storage_list()
    used_node = [
        node["down_proxy_url"]
        for node in sl["data"]["content"]
        if node["webdav_policy"] == "use_proxy_url" or node["web_proxy"]
    ]
    # 将已用的节点从可用节点中删除
    return [x for x in node_pool if x not in used_node]


# 发送节点状态
async def notify_status_change(app: Client, node, status_code):
    t_l = {200: f"🟢|{node}|恢复", 429: f"🔴|{node}|掉线"}
    text = t_l.get(status_code, f"⭕️|{node}|故障")
    logger.info(text) if status_code == 200 else logger.warning(text)

    if cloudflare_cfg["cronjob"]["status_push"]:
        for chat_id in cloudflare_cfg["cronjob"]["chat_id"]:
            try:
                await app.send_message(chat_id=chat_id, text=text)
            except Exception as ex:
                logger.error(f"节点状态发送失败|{chat_id}::{ex}")

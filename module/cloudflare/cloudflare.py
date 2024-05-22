# -*- coding: UTF-8 -*-

import asyncio
from dataclasses import dataclass

from apscheduler.triggers.cron import CronTrigger
from loguru import logger
from pyrogram import filters, Client
from pyrogram.types import (
    InlineKeyboardButton as Ikb,
    InlineKeyboardMarkup as Ikm,
    CallbackQuery,
    Message,
)

from config.config import cf_cfg, chat_data, plb_cfg
from module.cloudflare.utile import (
    check_node_status,
    date_shift,
    NodeInfo,
    get_node_info,
)
from tools.filters import is_admin, step_filter, is_member
from tools.scheduler_manager import aps
from tools.step_statu import step
from tools.utils import pybyte

return_button = [
    Ikb("↩️返回菜单", "cf_return"),
    Ikb("❌关闭菜单", "cf_close"),
]


def btn():
    return [
        [Ikb("⚙️CF节点管理", "⚙️")],
        [
            Ikb("👀查看节点", "cf_menu_node_status"),
            Ikb("📅通知设置", "cf_menu_cronjob"),
            Ikb("🆔账号管理", "cf_menu_account"),
        ],
        [
            Ikb("⚡️功能开关", "⚡️"),
        ],
        [
            _bt("节点状态推送", "status_push", cf_cfg.status_push),
            _bt("每日流量统计", "bandwidth_push", cf_cfg.bandwidth_push),
        ],
        [
            _bt("自动存储管理", "storage_mgmt", cf_cfg.storage_mgmt),
            _bt("自动切换节点", "auto_switch_nodes", cf_cfg.auto_switch_nodes),
        ],
        [
            _bt("代理负载均衡", "proxy_load_balance", plb_cfg.enable),
        ],
        [
            Ikb("🔀存储随机代理", "random_node"),
            Ikb("🔂存储统一代理", "unified_node"),
        ],
        [
            Ikb("❌关闭菜单", "cf_close"),
        ],
    ]


def _bt(text, data, t: bool):
    return Ikb(f"{'✅' if t else '❎'}{text}", f"{data}_{'off' if t else 'on'}")


bandwidth_button_a = [
    Ikb("🟢---", "gns_total_bandwidth"),
    Ikb("🔴---", "gns_total_bandwidth"),
    Ikb("⭕️---", "gns_total_bandwidth"),
]
bandwidth_button_b = [
    Ikb("📈总请求：---", "gns_total_bandwidth"),
    Ikb("📊总带宽：---", "gns_total_bandwidth"),
]
bandwidth_button_c = [
    Ikb("🔙上一天", "gns_status_up"),
    Ikb("---", "gns_status_calendar"),
    Ikb("下一天🔜", "gns_status_down"),
]


#####################################################################################
#####################################################################################
# 按钮回调


@Client.on_callback_query(filters.regex("^cf_close$"))
async def cf_close_callback(_, cq: CallbackQuery):
    chat_data["account_add"] = False
    await cq.message.edit(text="已退出『节点管理』")


@Client.on_callback_query(filters.regex("^cf_menu_account$"))
async def cf_menu_account_callback(_, cq: CallbackQuery):
    await account(cq)


@Client.on_callback_query(filters.regex("^cf_menu_cronjob$"))
async def cf_menu_cronjob_callback(_, cq: CallbackQuery):
    step.set_step(cq.from_user.id, "set_cronjob", True)
    step.insert(cq.from_user.id, menu_msg=cq.message)
    await cronjob_set(cq)


@Client.on_callback_query(filters.regex("^cf_menu_node_status$"))
async def cf_menu_node_status_callback(_, cq: CallbackQuery):
    chat_data["node_status_day"] = 0
    await send_node_status(cq, chat_data["node_status_day"])


@Client.on_callback_query(filters.regex("^cf_return$"))
async def cf_return_callback(_, cq: CallbackQuery):
    await r_cf_menu(cq)


# 节点状态按钮回调
@Client.on_callback_query(filters.regex("^gns_"))
async def node_status(_, cq: CallbackQuery):
    query = cq.data
    node_status_day = chat_data.get("node_status_day", 0)

    if chat_data["node_status_mode"] == "menu":
        if query in ["gns_status_down", "gns_status_up"]:
            increment = 1 if query == "gns_status_down" else -1
            chat_data["node_status_day"] = node_status_day + increment
            await send_node_status(cq, chat_data["node_status_day"])

    elif chat_data["node_status_mode"] == "command":
        if query.startswith("gns_expansion_"):
            chat_data["packUp"] = not chat_data.get("packUp", False)
            await view_bandwidth_button(cq.message, node_status_day)
        elif query in ["gns_status_down", "gns_status_up"]:
            increment = 1 if query == "gns_status_down" else -1
            chat_data["node_status_day"] = node_status_day + increment
            await view_bandwidth_button(cq.message, chat_data["node_status_day"])


@Client.on_callback_query(filters.regex("^account_return$"))
async def account_return_callback(_, query: CallbackQuery):
    chat_data["account_add"] = False
    await account(query)


#####################################################################################
#####################################################################################


async def menu_text():
    if nodes := cf_cfg.nodes:
        task = [check_node_status(node.url) for node in nodes]
        results = [i.status for i in await asyncio.gather(*task)]

        return f"""
节点数量：{len(nodes)}
🟢  正常：{results.count(200)}
🔴  掉线：{results.count(429)}
⭕️  错误：{results.count(502)}
"""
    return "Cloudflare节点管理\n暂无账号，请先添加cf账号"


# cf菜单
@Client.on_message(filters.command("sf") & filters.private & is_admin)
async def cf_menu(_, message: Message):
    msg = await message.reply(text="检测节点中...", reply_markup=Ikm(btn()))
    await msg.edit(text=await menu_text(), reply_markup=Ikm(btn()))


# 返回菜单
async def r_cf_menu(query: CallbackQuery):
    await query.message.edit(text=await menu_text(), reply_markup=Ikm(btn()))


# 菜单中的节点状态
async def send_node_status(cq: CallbackQuery, day):
    cid = cq.message.chat.id
    chat_data["node_status_mode"] = "menu"
    if not chat_data.get(f"cd_{cid}"):
        chat_data[f"cd_{cid}"] = {}

    button = [bandwidth_button_a, bandwidth_button_b, bandwidth_button_c, return_button]
    await cq.message.edit(text="检测节点中...", reply_markup=Ikm(button))
    cd = f"gns_expansion_{day}"
    ni = chat_data[f"cd_{cid}"].get(cd) or await build_node_info(day)
    chat_data[f"cd_{cid}"][cd] = ni
    a = [ni.button_b, ni.button_c, ni.button_d, return_button]
    await cq.message.edit(text=ni.text_b, reply_markup=Ikm(a))


# 使用指令查看节点信息
@Client.on_message(filters.command("vb") & is_member)
async def view_bandwidth(_, msg: Message):
    chat_data["node_status_mode"] = "command"
    chat_data["packUp"] = True
    chat_data[f"cd_{msg.chat.id}"] = {}

    day = int(msg.command[1]) if msg.command[1:] else 0
    msg = await msg.reply(text="检测节点中...")
    await view_bandwidth_button(msg, day)


# view_bandwidth按钮
async def view_bandwidth_button(msg: Message, day: int):
    state = "🔼点击展开🔼" if chat_data["packUp"] else "🔽点击收起🔽"
    cd = f"gns_expansion_{day}"
    ab = [Ikb(state, callback_data=cd)]

    button = [ab, bandwidth_button_a, bandwidth_button_b, bandwidth_button_c]
    if chat_data.get("packUp"):
        button = [ab, bandwidth_button_b, bandwidth_button_c]
    await msg.edit(text="检测节点中...", reply_markup=Ikm(button))
    ni = chat_data[f"cd_{msg.chat.id}"].get(cd) or await build_node_info(day)
    chat_data[f"cd_{msg.chat.id}"][cd] = ni
    text = ni.text_a if chat_data["packUp"] else ni.text_b
    button = (
        [ab, ni.button_c, ni.button_d]
        if chat_data.get("packUp")
        else [ab, ni.button_b, ni.button_c, ni.button_d]
    )
    await msg.edit(text=text, reply_markup=Ikm(button))


async def get_node_info_list(_day) -> list[NodeInfo]:
    tasks = [get_node_info(_day, i) for i in cf_cfg.nodes]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    result_list = []
    for result in results:
        if isinstance(result, BaseException):
            logger.error(result)
            continue
        result_list.append(result)
    return result_list


@dataclass
class NodeInfoText:
    text_a: str
    text_b: str
    button_b: list[Ikb]
    button_c: list[Ikb]
    button_d: list[Ikb]
    code: list[int]


async def build_node_info(s) -> NodeInfoText:
    """生成节点信息文本和按钮"""
    d = date_shift(int(s))
    if not cf_cfg.nodes:
        t = "请先添加账号"
        b = Ikb(t, t)
        return NodeInfoText(t, t, [b], [b], [b], [])

    results = await get_node_info_list(s)
    if not results:
        results, d = await get_node_info_list(-1), date_shift(-1)
        chat_data["node_status_day"] -= 1
    text = [i.text for i in results]
    text.sort(key=lambda x: x.split(" |")[0])
    text_b = "".join(text)
    total_bandwidth = sum(i.worker_info.response_body_size for i in results)
    code = [i.code for i in results]
    request = f"{int(sum(i.worker_info.requests for i in results) / 10000)}W"

    text_a = f"""
节点数量：{len(code)}
🟢  正常：{code.count(200)}
🔴  掉线：{code.count(429)}
⭕️  错误：{code.count(502)}
"""

    button_b = [
        Ikb(f"🟢{code.count(200)}", "gns_total_bandwidth"),
        Ikb(f"🔴{code.count(429)}", "gns_total_bandwidth"),
        Ikb(f"⭕️{code.count(502)}", "gns_total_bandwidth"),
    ]
    button_c = [
        Ikb(f"📊总请求：{request}", "gns_total_bandwidth"),
        Ikb(f"📈总带宽：{pybyte(total_bandwidth)}", "gns_total_bandwidth"),
    ]
    button_d = [
        Ikb("🔙上一天", "gns_status_up"),
        Ikb(d[0], "gns_status_calendar"),
        Ikb("下一天🔜", "gns_status_down"),
    ]

    return NodeInfoText(text_a, text_b, button_b, button_c, button_d, code)


# 账号管理
async def account(query: CallbackQuery):
    text = []
    button = [Ikb("编辑", callback_data="account_add")]
    if nodes := cf_cfg.nodes:
        for index, value in enumerate(nodes):
            text_t = (
                f"{index + 1} | <code>{value.email}</code> | <code>{value.url}</code>\n"
            )
            text.append(text_t)
        t = "\n".join(text)
    else:
        t = "暂无账号"
    await query.message.edit(text=t, reply_markup=Ikm([button, return_button]))


# 通知设置
async def cronjob_set(cq: CallbackQuery):
    text = f"""
发送到: `{",".join(list(map(str, cf_cfg.chat_id))) if cf_cfg.chat_id else None}`
时间: `{cf_cfg.time or None}`
——————————
**发送到** | 可以填用户/群组/频道 id，支持多个，用英文逗号隔开
**时间** | __每日流量统计__发送时间，格式为5位cron表达式

chat_id 和 time 一行一个，例：
`123123,321321
0 23 * * *`
"""

    await cq.message.edit(text=text, reply_markup=Ikm([return_button]))


# 通知设置
@Client.on_message(
    filters.text & step_filter("set_cronjob") & filters.private & is_admin
)
async def cronjob_set_edit(_, message: Message):
    step.init(message.from_user.id)
    menu_msg = step.get(message.from_user.id, "menu_msg")

    dd = message.text.split("\n")
    cf_cfg.chat_id = [int(x) for x in dd[0].split(",")]
    cf_cfg.time = dd[1]
    if cf_cfg.bandwidth_push:
        aps.modify_job(
            trigger=CronTrigger.from_crontab(cf_cfg.time),
            job_id="cronjob_bandwidth_push",
        )
    await message.delete()
    await menu_msg.edit(
        text=f"设置成功！\n-------\nchat_id：`{cf_cfg.chat_id}`"
        f"\ntime：`{cf_cfg.time}`",
        reply_markup=Ikm([return_button]),
    )

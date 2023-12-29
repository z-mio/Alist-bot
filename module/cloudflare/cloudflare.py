# -*- coding: UTF-8 -*-

import asyncio
import datetime

import httpx
from apscheduler.triggers.cron import CronTrigger
from loguru import logger
from pyrogram import filters, Client
from pyrogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    CallbackQuery,
    Message,
)

from api.cloudflare_api import graphql_api
from config.config import nodee, cronjob, cloudflare_cfg, chat_data, write_config
from tool.scheduler_manager import aps
from tool.utils import is_admin
from tool.utils import pybyte

return_button = [
    InlineKeyboardButton("↩️返回菜单", callback_data="cf_return"),
    InlineKeyboardButton("❌关闭菜单", callback_data="cf_close"),
]


def btn():
    return [
        [InlineKeyboardButton("⚙️CF节点管理", callback_data="⚙️")],
        [
            InlineKeyboardButton("👀查看节点", callback_data="cf_menu_node_status"),
            InlineKeyboardButton("📅通知设置", callback_data="cf_menu_cronjob"),
            InlineKeyboardButton("🆔账号管理", callback_data="cf_menu_account"),
        ],
        [
            InlineKeyboardButton("⚡️功能开关", callback_data="⚡️"),
        ],
        [
            InlineKeyboardButton(
                "✅节点状态推送" if cronjob()["status_push"] else "❎节点状态推送",
                callback_data="status_push_off"
                if cronjob()["status_push"]
                else "status_push_on",
            ),
            InlineKeyboardButton(
                "✅每日流量统计" if cronjob()["bandwidth_push"] else "❎每日流量统计",
                callback_data="bandwidth_push_off"
                if cronjob()["bandwidth_push"]
                else "bandwidth_push_on",
            ),
        ],
        [
            InlineKeyboardButton(
                "✅自动管理存储" if cronjob()["storage_mgmt"] else "❎自动管理存储",
                callback_data="storage_mgmt_off"
                if cronjob()["storage_mgmt"]
                else "storage_mgmt_on",
            ),
            InlineKeyboardButton(
                "✅自动切换节点" if cronjob()["auto_switch_nodes"] else "❎自动切换节点",
                callback_data="auto_switch_nodes_off"
                if cronjob()["auto_switch_nodes"]
                else "auto_switch_nodes_on",
            ),
        ],
        [
            InlineKeyboardButton("❌关闭菜单", callback_data="cf_close"),
        ],
    ]


bandwidth_button_a = [
    InlineKeyboardButton("🟢---", callback_data="gns_total_bandwidth"),
    InlineKeyboardButton("🔴---", callback_data="gns_total_bandwidth"),
    InlineKeyboardButton("⭕️---", callback_data="gns_total_bandwidth"),
]
bandwidth_button_b = [
    InlineKeyboardButton("📈总请求：---", callback_data="gns_total_bandwidth"),
    InlineKeyboardButton("📊总带宽：---", callback_data="gns_total_bandwidth"),
]
bandwidth_button_c = [
    InlineKeyboardButton("🔙上一天", callback_data="gns_status_up"),
    InlineKeyboardButton("---", callback_data="gns_status_calendar"),
    InlineKeyboardButton("下一天🔜", callback_data="gns_status_down"),
]


#####################################################################################
#####################################################################################
# 按钮回调


@Client.on_callback_query(filters.regex("^cf_close$"))
async def cf_close_callback(_, query: CallbackQuery):
    chat_data["account_add"] = False
    await query.message.edit(text="已退出『节点管理』")


@Client.on_callback_query(filters.regex("^cf_menu_account$"))
async def cf_menu_account_callback(_, query: CallbackQuery):
    await account(query)


@Client.on_callback_query(filters.regex("^cf_menu_cronjob$"))
async def cf_menu_cronjob_callback(_, query: CallbackQuery):
    await cronjob_set(query)


@Client.on_callback_query(filters.regex("^cf_menu_node_status$"))
async def cf_menu_node_status_callback(_, query: CallbackQuery):
    chat_data["node_status_day"] = 0
    await send_node_status(query, chat_data["node_status_day"])


@Client.on_callback_query(filters.regex("^cf_return$"))
async def cf_return_callback(_, query: CallbackQuery):
    await r_cf_menu(query)


# 节点状态按钮回调
@Client.on_callback_query(filters.regex("^gns_"))
async def node_status(_, message: CallbackQuery):
    query = message.data
    node_status_day = chat_data.get("node_status_day", 0)

    if chat_data["node_status_mode"] == "menu":
        if query in ["gns_status_down", "gns_status_up"]:
            increment = 1 if query == "gns_status_down" else -1
            chat_data["node_status_day"] = node_status_day + increment
            await send_node_status(message, chat_data["node_status_day"])

    elif chat_data["node_status_mode"] == "command":
        if query.startswith("gns_expansion_"):
            chat_data["packUp"] = not chat_data.get("packUp", False)
            await view_bandwidth_button(message, node_status_day)
        elif query in ["gns_status_down", "gns_status_up"]:
            increment = 1 if query == "gns_status_down" else -1
            chat_data["node_status_day"] = node_status_day + increment
            await view_bandwidth_button(message, chat_data["node_status_day"])


@Client.on_callback_query(filters.regex("^account_return$"))
async def account_return_callback(_, query: CallbackQuery):
    chat_data["account_add"] = False
    await account(query)


# 按钮回调 通知设置
@Client.on_callback_query(filters.regex("cronjob_set"))
async def cronjob_set_callback(_, message: CallbackQuery):
    chat_data["cronjob_set"] = False
    await cronjob_set(message)


#####################################################################################
#####################################################################################


def _cronjob_set_filter(_, __, ___):
    return bool("cronjob_set" in chat_data and chat_data["cronjob_set"])


cronjob_set_filter = filters.create(_cronjob_set_filter)


async def cf_aaa():
    if nodee():
        nodes = [value["url"] for value in nodee()]
        task = [check_node_status(node) for node in nodes]
        results = [i[1] for i in await asyncio.gather(*task)]

        return f"""
节点数量：{len(nodes)}
🟢  正常：{results.count(200)}
🔴  掉线：{results.count(429)}
⭕️  错误：{results.count(501)}
"""
    return "Cloudflare节点管理\n暂无账号，请先添加cf账号"


# cf菜单
@Client.on_message(filters.command("sf") & filters.private & is_admin)
async def cf_menu(_, message: Message):
    msg = chat_data["cf_menu"] = await message.reply(
        text="检测节点中...", reply_markup=InlineKeyboardMarkup(btn())
    )
    await msg.edit(text=await cf_aaa(), reply_markup=InlineKeyboardMarkup(btn()))


# 返回菜单
async def r_cf_menu(query: CallbackQuery):
    await query.message.edit(
        text=await cf_aaa(), reply_markup=InlineKeyboardMarkup(btn())
    )


# 获取节点信息
async def get_node_info(url, email, key, zone_id, day):
    d = date_shift(day)
    ga = await graphql_api(email, key, zone_id, d[1], d[2])
    byte = ga["data"]["viewer"]["zones"][0]["httpRequests1dGroups"][0]["sum"]["bytes"]
    request = ga["data"]["viewer"]["zones"][0]["httpRequests1dGroups"][0]["sum"][
        "requests"
    ]
    code = await check_node_status(url)
    code = code[1]
    if code == 200:
        code = "🟢"
    elif code == 429:
        code = "🔴"
    else:
        code = "⭕️"
    text = f"""
{url} | {code}
请求：<code>{request}</code> | 带宽：<code>{pybyte(byte)}</code>
———————"""

    return text, byte, code, request


# 菜单中的节点状态
async def send_node_status(query: CallbackQuery, day):
    chat_data["node_status_mode"] = "menu"
    button = [bandwidth_button_a, bandwidth_button_b, bandwidth_button_c, return_button]
    await query.message.edit(text="检测节点中...", reply_markup=InlineKeyboardMarkup(button))
    vv = await get_node_status(day)
    a = [vv[1], vv[2], vv[3], return_button]
    await query.message.edit(text=vv[0][1], reply_markup=InlineKeyboardMarkup(a))


# 使用指令查看节点信息
@Client.on_message(filters.command("vb"))
async def view_bandwidth(_, message: Message):
    chat_data["node_status_mode"] = "command"
    chat_data["packUp"] = True
    chat_data[f"cd_{message.chat.id}"] = {}

    day = int(message.command[1]) if message.command[1:] else 0
    cd = f"gns_expansion_{day}"

    msg = await message.reply(text="检测节点中...")

    chat_data["node_status_day"] = day
    vv = await get_node_status(day)
    chat_data[f"cd_{message.chat.id}"][cd] = vv
    state = "🔼点击展开🔼" if chat_data["packUp"] else "🔽点击收起🔽"

    button = [
        InlineKeyboardButton(state, callback_data=cd)
        if chat_data.get("packUp")
        else None
    ]
    text = vv[0][0]
    button = (
        [button, vv[2], vv[3]]
        if chat_data.get("packUp")
        else [button, vv[1], vv[2], vv[3]]
    )
    await msg.edit_text(text=text, reply_markup=InlineKeyboardMarkup(button))


# view_bandwidth按钮
async def view_bandwidth_button(query: CallbackQuery, day):
    state = "🔼点击展开🔼" if chat_data["packUp"] else "🔽点击收起🔽"
    cd = f"gns_expansion_{day}"
    ab = [InlineKeyboardButton(state, callback_data=cd)]

    button = [ab, bandwidth_button_a, bandwidth_button_b, bandwidth_button_c]
    if chat_data.get("packUp"):
        button = [ab, bandwidth_button_b, bandwidth_button_c]
    await query.message.edit(text="检测节点中...", reply_markup=InlineKeyboardMarkup(button))
    if vv := chat_data[f"cd_{query.message.chat.id}"].get(cd):
        ...
    else:
        chat_data[f"cd_{query.message.chat.id}"][cd] = vv = await get_node_status(day)
    text = vv[0][0] if chat_data["packUp"] else vv[0][1]
    button = (
        [ab, vv[2], vv[3]] if chat_data.get("packUp") else [ab, vv[1], vv[2], vv[3]]
    )
    await query.message.edit(text=text, reply_markup=InlineKeyboardMarkup(button))


async def xx(_day, node_list):
    url, email, key, zone_id = zip(
        *[(n["url"], n["email"], n["global_api_key"], n["zone_id"]) for n in node_list]
    )
    tasks = [
        asyncio.create_task(get_node_info(url_, email_, key_, zone_id_, _day))
        for url_, email_, key_, zone_id_ in zip(url, email, key, zone_id)
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    result_list: list = []
    for result in results:
        if isinstance(result, Exception):
            logger.error(result)
            continue
        result_list.append(result)
    return result_list


# 获取节点状态
async def get_node_status(s):
    d = date_shift(int(s))
    node_list = nodee()
    if not node_list:
        return "请先添加账号", [
            [
                InlineKeyboardButton(
                    "请先添加账号", callback_data="please_add_an_account_first"
                )
            ]
        ]

    results = await xx(s, node_list)
    if not results:
        results, d = await xx(-1, node_list), date_shift(-1)
        chat_data["node_status_day"] -= 1
    text = [i[0] for i in results]
    text.sort(key=lambda x: x.split(" |")[0])
    text_b = "".join(text)
    total_bandwidth = sum(i[1] for i in results)
    code = [i[2] for i in results]
    request = f"{int(sum(i[3] for i in results) / 10000)}W"

    text_a = f"""
节点数量：{len(code)}
🟢  正常：{code.count('🟢')}
🔴  掉线：{code.count('🔴')}
⭕️  错误：{code.count('⭕️')}
    """

    button_b = [
        InlineKeyboardButton(
            f"🟢{code.count('🟢')}", callback_data="gns_total_bandwidth"
        ),
        InlineKeyboardButton(
            f"🔴{code.count('🔴')}", callback_data="gns_total_bandwidth"
        ),
        InlineKeyboardButton(
            f"⭕️{code.count('⭕️')}", callback_data="gns_total_bandwidth"
        ),
    ]
    button_c = [
        InlineKeyboardButton(f"📊总请求：{request}", callback_data="gns_total_bandwidth"),
        InlineKeyboardButton(
            f"📈总带宽：{pybyte(total_bandwidth)}",
            callback_data="gns_total_bandwidth",
        ),
    ]
    button_d = [
        InlineKeyboardButton("🔙上一天", callback_data="gns_status_up"),
        InlineKeyboardButton(d[0], callback_data="gns_status_calendar"),
        InlineKeyboardButton("下一天🔜", callback_data="gns_status_down"),
    ]

    return [text_a, text_b], button_b, button_c, button_d, code


# 账号管理
async def account(query: CallbackQuery):
    text = []
    button = [InlineKeyboardButton("编辑", callback_data="account_add")]
    if nodee():
        for index, value in enumerate(nodee()):
            text_t = f"{index + 1} | <code>{value['email']}</code> | <code>{value['url']}</code>\n"
            text.append(text_t)
        t = "\n".join(text)
    else:
        t = "暂无账号"
    await query.message.edit(
        text=t, reply_markup=InlineKeyboardMarkup([button, return_button])
    )


# 通知设置
async def cronjob_set(query: CallbackQuery):
    text = f"""
发送到: `{",".join(list(map(str, cronjob()['chat_id']))) if cronjob()['chat_id'] else None}`
时间: `{cronjob()['time'] or None}`
——————————
**发送到** | 可以填用户/群组/频道 id，支持多个，用英文逗号隔开
**时间** | __每日流量统计__发送时间，格式为5位cron表达式

chat_id 和 time 一行一个，例：
`123123,321321
0 23 * * *`
"""

    await query.message.edit(
        text=text, reply_markup=InlineKeyboardMarkup([return_button])
    )

    chat_data["cronjob_set"] = True


# 通知设置
@Client.on_message(filters.text & cronjob_set_filter & filters.private & is_admin)
async def cronjob_set_edit(_, message: Message):
    chat_data["cronjob_set"] = False
    d = message.text
    dd = d.split("\n")
    cloudflare_cfg["cronjob"]["chat_id"] = [int(x) for x in dd[0].split(",")]
    cloudflare_cfg["cronjob"]["time"] = dd[1]
    if cloudflare_cfg["cronjob"]["bandwidth_push"]:
        aps.modify_job(
            trigger=CronTrigger.from_crontab(cloudflare_cfg["cronjob"]["time"]),
            job_id="cronjob_bandwidth_push",
        )
    write_config("config/cloudflare_cfg.yaml", cloudflare_cfg)
    await message.delete()
    await chat_data["cf_menu"].edit(
        text=f"设置成功！\n-------\nchat_id：`{cloudflare_cfg['cronjob']['chat_id']}`"
        f"\ntime：`{cloudflare_cfg['cronjob']['time']}`",
        reply_markup=InlineKeyboardMarkup([return_button]),
    )


#####################################################################################
#####################################################################################
# 检查节点状态
async def check_node_status(url: str) -> list[str | int]:
    status_code_map = {
        200: [url, 200],
        429: [url, 429],
    }
    async with httpx.AsyncClient() as client:
        response = await client.get(f"https://{url}")
    return status_code_map.get(response.status_code, [url, 502])


# 将当前日期移位n天，并返回移位日期和移位日期的前一个和下一个日期。
def date_shift(n: int = 0):
    today = datetime.date.today()
    shifted_date = datetime.date.fromordinal(today.toordinal() + n)
    previous_date = datetime.date.fromordinal(shifted_date.toordinal() - 1)
    next_date = datetime.date.fromordinal(shifted_date.toordinal() + 1)
    previous_date_string = previous_date.isoformat()
    next_date_string = next_date.isoformat()
    return shifted_date.isoformat(), previous_date_string, next_date_string

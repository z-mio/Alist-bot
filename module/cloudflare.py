# -*- coding: UTF-8 -*-
import asyncio
import concurrent.futures
import contextlib
import datetime
import json
import logging
import requests
from apscheduler.triggers.cron import CronTrigger
from pyrogram import filters, Client
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from api.cloudflare_api import list_zones, list_filters, graphql_api
from bot import admin_yz
from config.config import nodee, cronjob, cloudflare_cfg, chat_data, write_config
from tool.handle_exception import handle_exception
from tool.pybyte import pybyte
from tool.scheduler_manager import aps

return_button = [
    InlineKeyboardButton('↩️返回菜单', callback_data='cf_return'),
    InlineKeyboardButton('❌关闭菜单', callback_data='cf_close'),
]
cf_menu_button = [
    [
        InlineKeyboardButton('👀查看节点', callback_data='cf_menu_node_status'),
        InlineKeyboardButton('🕒通知设置', callback_data='cf_menu_cronjob'),
    ],
    [
        InlineKeyboardButton('🤖自动管理存储', callback_data='cf_menu_storage_mgmt'),
        InlineKeyboardButton('📝cf 账号管理', callback_data='cf_menu_account'),
    ],
    [
        InlineKeyboardButton('❌关闭菜单', callback_data='cf_close'),
    ]]

bandwidth_button_a = [
    InlineKeyboardButton('🟢---', callback_data='gns_total_bandwidth'),
    InlineKeyboardButton('🔴---', callback_data='gns_total_bandwidth'),
    InlineKeyboardButton('⭕️---', callback_data='gns_total_bandwidth'),
]
bandwidth_button_b = [
    InlineKeyboardButton(
        '📈总请求：---', callback_data='gns_total_bandwidth'
    ),
    InlineKeyboardButton(
        '📊总带宽：---', callback_data='gns_total_bandwidth'
    ),
]
bandwidth_button_c = [
    InlineKeyboardButton('🔙上一天', callback_data='gns_status_up'),
    InlineKeyboardButton('---', callback_data='gns_status_calendar'),
    InlineKeyboardButton('下一天🔜', callback_data='gns_status_down'),
]

# 获取节点状态线程池
thread_pool = concurrent.futures.ThreadPoolExecutor(max_workers=20)


#####################################################################################
#####################################################################################
# 按钮回调
# 菜单按钮回调
@Client.on_callback_query(filters.regex('^cf_'))
async def cf_button_callback(client, message):
    query = message.data
    if query == 'cf_close':
        chat_data["account_add"] = False
        chat_id = message.message.chat.id
        message_id = message.message.id
        await client.edit_message_text(chat_id=chat_id,
                                       message_id=message_id,
                                       text='已退出『节点管理』')
    elif query == 'cf_menu_account':
        await account(client, message)
    elif query == 'cf_menu_cronjob':
        await cronjob_callback(client, message)
    elif query == 'cf_menu_node_status':
        chat_data['node_status_day'] = 0
        await send_node_status(client, message, chat_data['node_status_day'])
    elif query == 'cf_menu_storage_mgmt':
        ...
    elif query == 'cf_return':
        await r_cf_menu(client, message)


# 节点状态按钮回调
@Client.on_callback_query(filters.regex('^gns_'))
async def node_status(client, message):
    query = message.data
    if chat_data['node_status_mode'] == 'menu':
        if query == 'gns_status_down':
            if 'node_status_day' in chat_data and chat_data['node_status_day']:
                chat_data['node_status_day'] += 1
                await send_node_status(client, message, chat_data['node_status_day'])
        elif query == 'gns_status_up':
            chat_data['node_status_day'] -= 1
            await send_node_status(client, message, chat_data['node_status_day'])
    elif chat_data['node_status_mode'] == 'command':
        if query == 'gns_expansion':
            chat_data['packUp'] = not chat_data['packUp']
            thread_pool.submit(asyncio.run, view_bandwidth_button(client, message, chat_data['node_status_day']))
        elif query == 'gns_status_down':
            if 'node_status_day' in chat_data and chat_data['node_status_day']:
                chat_data['node_status_day'] += 1
                thread_pool.submit(asyncio.run, view_bandwidth_button(client, message, chat_data['node_status_day']))
        elif query == 'gns_status_up':
            chat_data['node_status_day'] -= 1
            thread_pool.submit(asyncio.run, view_bandwidth_button(client, message, chat_data['node_status_day']))


# 通知设置菜单按钮回调
@Client.on_callback_query(filters.regex('^cronjob_'))
async def cronjob_button_callback(client, message):
    query = message.data
    if query.startswith('cronjob_status'):
        cloudflare_cfg['cronjob']['status_push'] = query != 'cronjob_status_off'
        write_config('config/cloudflare_cfg.yaml', cloudflare_cfg)
        await cronjob_callback(client, message)
    elif query.startswith('cronjob_bandwidth'):
        if query == 'cronjob_bandwidth_off':
            cloudflare_cfg['cronjob']['bandwidth_push'] = False
            aps.pause_job('cronjob_bandwidth_push')
        elif query == 'cronjob_bandwidth_on':
            cloudflare_cfg['cronjob']['bandwidth_push'] = True
            aps.modify_job(cloudflare_cfg['cronjob']['time'], 'cronjob_bandwidth_push')
            aps.add_job(func=send_cronjob_bandwidth_push, args=[client],
                        trigger=CronTrigger.from_crontab(cloudflare_cfg['cronjob']['time']),
                        job_id='cronjob_bandwidth_push')
        write_config('config/cloudflare_cfg.yaml', cloudflare_cfg)
        await cronjob_callback(client, message)
    elif query == 'cronjob_set':
        await cronjob_set(client, message)
    elif query == 'cronjob_set_return':
        chat_data["cronjob_set"] = False
        await cronjob_callback(client, message)


# cf账号管理按钮回调
@Client.on_callback_query(filters.regex('account_'))
async def account_button_callback(client, message):
    query = message.data
    if query == 'account_add':
        await account_add(client, message)
    elif query == 'account_return':
        chat_data["account_add"] = False
        await account(client, message)


#####################################################################################
#####################################################################################

# 监听普通消息
@Client.on_message((filters.text & filters.private) & ~filters.regex('^/'))
async def echo_cloudflare(client, message):
    if 'account_add' in chat_data and chat_data["account_add"]:
        await account_edit(client, message)
    elif 'cronjob_set' in chat_data and chat_data["cronjob_set"]:
        await cronjob_set_edit(client, message)
        chat_data["cronjob_set"] = False


def cf_aaa():
    if nodee():
        nodes = [value['url'] for value in nodee()]
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = [executor.submit(check_node_status, node) for node in nodes]
        results = [future.result() for future in concurrent.futures.wait(futures).done]

        return f'''
节点数量：{len(nodes)}
🟢  正常：{results.count("🟢")}
🔴  失效：{results.count("🔴")}
⭕️  错误：{results.count("⭕️")}
'''
    return 'Cloudflare节点管理\n暂无账号，请先添加cf账号'


# cf菜单
@Client.on_message(filters.command('sf') & filters.private)
@admin_yz
async def cf_menu(client, message):
    chat_data['cf_menu'] = await client.send_message(chat_id=message.chat.id,
                                                     text='检测节点中...',
                                                     reply_markup=InlineKeyboardMarkup(cf_menu_button))
    await client.edit_message_text(chat_id=chat_data['cf_menu'].chat.id,
                                   message_id=chat_data['cf_menu'].id,
                                   text=cf_aaa(),
                                   reply_markup=InlineKeyboardMarkup(cf_menu_button))


# 返回菜单
async def r_cf_menu(client, message):
    chat_id, message_id = message.message.chat.id, message.message.id
    await client.edit_message_text(chat_id=chat_id,
                                   message_id=message_id,
                                   text=cf_aaa(),
                                   reply_markup=InlineKeyboardMarkup(cf_menu_button))


# 获取节点信息
def get_node_info(url, email, key, zone_id, day):
    d = date_shift(day)
    ga = graphql_api(email, key, zone_id, d[1], d[2])
    ga = json.loads(ga.text)
    byte = ga['data']['viewer']['zones'][0]['httpRequests1dGroups'][0]['sum']['bytes']
    request = ga['data']['viewer']['zones'][0]['httpRequests1dGroups'][0]['sum']['requests']
    code = check_node_status(url)
    text = f'''
{url} | {code}
请求：<code>{request}</code> | 带宽：<code>{pybyte(byte)}</code>
———————'''

    return text, byte, code, request


# 菜单中的节点状态
@handle_exception
@admin_yz
async def send_node_status(client, message, day):
    chat_id, message_id = message.message.chat.id, message.message.id
    chat_data['node_status_mode'] = 'menu'

    button = [bandwidth_button_a, bandwidth_button_b, bandwidth_button_c, return_button]
    await client.edit_message_text(chat_id=chat_id,
                                   message_id=message_id,
                                   text='检测节点中...',
                                   reply_markup=InlineKeyboardMarkup(button)
                                   )
    vv = get_node_status(day)
    a = [vv[1], vv[2], vv[3], return_button]

    await client.edit_message_text(chat_id=chat_id,
                                   message_id=message_id,
                                   text=vv[0],
                                   reply_markup=InlineKeyboardMarkup(a)
                                   )


# 使用指令查看节点信息
@Client.on_message(filters.command('vb'))
@handle_exception
async def view_bandwidth(client, message):
    async def view_bandwidth_a(client_a, message_a):
        chat_data['node_status_mode'] = 'command'
        chat_data['packUp'] = True
        a = await client_a.send_message(chat_id=message_a.chat.id,
                                        text='检测节点中...')

        day = int(message_a.command[1]) if message_a.command[1:] else 0
        chat_data['node_status_day'] = day
        vv = get_node_status(day)
        state = '🔼点击展开🔼' if chat_data['packUp'] else '🔽点击收起🔽'
        button = [InlineKeyboardButton(state, callback_data='gns_expansion') if 'packUp' in chat_data and chat_data[
            'packUp'] else None]
        text = cf_aaa() if 'packUp' in chat_data and chat_data['packUp'] else vv[0]
        button = [button, vv[2], vv[3]] if 'packUp' in chat_data and chat_data['packUp'] else [button, vv[1], vv[2],
                                                                                               vv[3]]
        await client_a.edit_message_text(chat_id=a.chat.id,
                                         message_id=a.id,
                                         text=text,
                                         reply_markup=InlineKeyboardMarkup(button))

    thread_pool.submit(asyncio.run, view_bandwidth_a(client, message))


# view_bandwidth按钮
async def view_bandwidth_button(client, message, day):
    chat_id, message_id = message.message.chat.id, message.message.id
    state = '🔼点击展开🔼' if chat_data['packUp'] else '🔽点击收起🔽'
    ab = [InlineKeyboardButton(state, callback_data='gns_expansion')]
    button = [ab, bandwidth_button_a, bandwidth_button_b, bandwidth_button_c]
    if 'packUp' in chat_data and chat_data['packUp']:
        button = [ab, bandwidth_button_b, bandwidth_button_c]
    await client.edit_message_text(chat_id=chat_id,
                                   message_id=message_id,
                                   text='检测节点中...',
                                   reply_markup=InlineKeyboardMarkup(button)
                                   )
    vv = get_node_status(day)
    text = cf_aaa() if 'packUp' in chat_data and chat_data['packUp'] else vv[0]
    button = [ab, vv[2], vv[3]] if 'packUp' in chat_data and chat_data['packUp'] else [ab, vv[1], vv[2], vv[3]]
    await client.edit_message_text(chat_id=chat_id, message_id=message_id, text=text,
                                   reply_markup=InlineKeyboardMarkup(button))


# 获取节点状态
def get_node_status(s):
    d = date_shift(int(s))
    node_list = nodee()
    if not node_list:
        return '请先添加账号', [[InlineKeyboardButton('请先添加账号', callback_data='please_add_an_account_first')]]
    url, email, key, zone_id = zip(*[(n['url'], n['email'], n['global_api_key'], n['zone_id']) for n in node_list])

    def xx(_day):
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = [executor.submit(get_node_info, url_, email_, key_, zone_id_, _day) for
                       url_, email_, key_, zone_id_ in
                       zip(url, email, key, zone_id)]
        result_list = []
        for future in concurrent.futures.wait(futures).done:
            with contextlib.suppress(IndexError):
                result_list.append(future.result())
        return result_list

    results = xx(s)
    if not results:
        results, d = xx(-1), date_shift(-1)
        chat_data['node_status_day'] -= 1
    text = [i[0] for i in results]
    text.sort(key=lambda x: x.split(' |')[0])
    total_bandwidth = sum(i[1] for i in results)
    code = [i[2] for i in results]
    request = f'{int(sum(i[3] for i in results) / 10000)}W'

    button_b = [
        InlineKeyboardButton(
            f'🟢{code.count("🟢")}', callback_data='gns_total_bandwidth'
        ),
        InlineKeyboardButton(
            f'🔴{code.count("🔴")}', callback_data='gns_total_bandwidth'
        ),
        InlineKeyboardButton(
            f'⭕️{code.count("⭕️")}', callback_data='gns_total_bandwidth'
        ),
    ]
    button_c = [
        InlineKeyboardButton(
            f'📊总请求：{request}', callback_data='gns_total_bandwidth'
        ),
        InlineKeyboardButton(
            f'📈总带宽：{pybyte(total_bandwidth)}',
            callback_data='gns_total_bandwidth',
        ),
    ]
    button_d = [
        InlineKeyboardButton('🔙上一天', callback_data='gns_status_up'),
        InlineKeyboardButton(d[0], callback_data='gns_status_calendar'),
        InlineKeyboardButton('下一天🔜', callback_data='gns_status_down'),
    ]

    return ''.join(text), button_b, button_c, button_d


# 账号管理

async def account(client, message):
    chat_id, message_id = message.message.chat.id, message.message.id
    text = []
    button = [
        InlineKeyboardButton('编辑', callback_data='account_add')
    ]
    if nodee():
        for index, value in enumerate(nodee()):
            text_t = f"{index + 1} | <code>{value['email']}</code> | <code>{value['url']}</code>\n"
            text.append(text_t)
        t = '\n'.join(text)
    else:
        t = '暂无账号'
    await client.edit_message_text(chat_id=chat_id,
                                   message_id=message_id,
                                   text=t,
                                   reply_markup=InlineKeyboardMarkup([button, return_button]))


# 添加/删除账号
async def account_add(client, message):
    chat_id, message_id = message.message.chat.id, message.message.id
    text = []
    account_add_return_button = [
        InlineKeyboardButton('↩️返回账号', callback_data='account_return'),
        InlineKeyboardButton('❌关闭菜单', callback_data='cf_close'),
    ]
    if nodee():
        for index, value in enumerate(nodee()):
            text_t = f"{index + 1} | <code>{value['email']}</code> | <code>{value['global_api_key']}</code>\n"
            text.append(text_t)
        t = '\n'.join(text)
    else:
        t = '暂无账号'
    tt = '''
添加：
一次只能添加一个账号
第一行cf邮箱，第二行global_api_key，例：
<code>abc123@qq.com
285812f3012365412d33398713c156e2db314
</code>
删除：
*+序号，例：<code>*2</code>
'''
    await client.edit_message_text(chat_id=chat_id,
                                   message_id=message_id,
                                   text=t if 'account_add' in chat_data and chat_data["account_add"] else t + tt,
                                   reply_markup=InlineKeyboardMarkup([account_add_return_button]))
    chat_data["account_add"] = True


# 开始处理
async def account_edit(client, message):
    mt = message.text

    if mt[0] != '*':

        i = mt.split('\n')

        lz = list_zones(i[0], i[1])  # 获取区域id
        lz = json.loads(lz.text)

        account_id = lz['result'][0]['account']['id']
        zone_id = lz['result'][0]['id']

        lf = list_filters(i[0], i[1], zone_id)  # 获取url
        lf = json.loads(lf.text)

        url = lf['result'][0]['pattern'].rstrip('/*')
        d = {"url": url, "email": i[0], "global_api_key": i[1], "account_id": account_id, "zone_id": zone_id}
        if cloudflare_cfg['node']:
            cloudflare_cfg['node'].append(d)
        else:
            cloudflare_cfg['node'] = [d]

    else:
        i = int(mt.split('*')[1])
        del cloudflare_cfg['node'][i - 1]
    write_config("config/cloudflare_cfg.yaml", cloudflare_cfg)
    await client.delete_messages(chat_id=message.chat.id, message_ids=message.id)
    await account_add(client, message)


# 定时任务
async def cronjob_callback(client, message):
    chat_id, message_id = message.message.chat.id, message.message.id
    status_push = cronjob()['status_push']
    bandwidth_push = cronjob()['bandwidth_push']
    button = [
        [
            InlineKeyboardButton('关闭状态通知' if status_push else '开启状态通知',
                                 callback_data='cronjob_status_off' if status_push else 'cronjob_status_on'),
            InlineKeyboardButton('设置', callback_data='cronjob_set'),
            InlineKeyboardButton('关闭带宽通知' if bandwidth_push else '开启带宽通知',
                                 callback_data='cronjob_bandwidth_off' if bandwidth_push else 'cronjob_bandwidth_on'),
        ],
        return_button
    ]
    chat_data['cronjob_callback_button'] = button

    await client.edit_message_text(chat_id=chat_id,
                                   message_id=message_id,
                                   text='通知设置',
                                   reply_markup=InlineKeyboardMarkup(button))


# 通知设置
async def cronjob_set(client, message):
    chat_id, message_id = message.message.chat.id, message.message.id
    cronjob_set_return_button = [
        InlineKeyboardButton('↩️返回设置', callback_data='cronjob_set_return'),
        InlineKeyboardButton('❌关闭菜单', callback_data='cf_close'),
    ]
    text = f"""
chat_id: <code>{",".join(list(map(str, cronjob()['chat_id']))) if cronjob()['chat_id'] else None}</code>
time: <code>{cronjob()['time'] or None}</code>
——————————
chat_id 可以填用户/群组/频道 id，支持多个,用英文逗号隔开

time 为带宽通知时间，格式为5位cron表达式

chat_id 和 time 一行一个，例：
<code>123123,321321
0 24 * * *</code>


"""

    await client.edit_message_text(chat_id=chat_id,
                                   message_id=message_id,
                                   text=text,
                                   reply_markup=InlineKeyboardMarkup([cronjob_set_return_button]))
    chat_data["cronjob_set"] = True


# 通知设置
async def cronjob_set_edit(client, message):
    chat_id, message_id = chat_data['cf_menu'].chat.id, chat_data['cf_menu'].id
    d = message.text
    dd = d.split('\n')
    cloudflare_cfg['cronjob']['chat_id'] = [int(x) for x in dd[0].split(',')]
    cloudflare_cfg['cronjob']['time'] = dd[1]
    if cloudflare_cfg['cronjob']['bandwidth_push']:
        aps.modify_job(trigger=CronTrigger.from_crontab(cloudflare_cfg['cronjob']['time']),
                       job_id='cronjob_bandwidth_push')
    write_config('config/cloudflare_cfg.yaml', cloudflare_cfg)
    await client.delete_messages(chat_id=message.chat.id, message_ids=message.id)
    await client.edit_message_text(chat_id=chat_id,
                                   message_id=message_id,
                                   text=f"设置成功！\n-------\nchat_id：<code>{cloudflare_cfg['cronjob']['chat_id']}</code>"
                                        f"\ntime：<code>{cloudflare_cfg['cronjob']['time']}</code>",
                                   reply_markup=InlineKeyboardMarkup(chat_data['cronjob_callback_button']))


# 带宽通知定时任务
async def send_cronjob_bandwidth_push(app):
    chat_data['packUp'] = True
    vv = get_node_status(0)
    text = '今日流量统计'
    for i in cloudflare_cfg['cronjob']['chat_id']:
        await app.send_message(chat_id=i,
                               text=text,
                               reply_markup=InlineKeyboardMarkup([vv[1], vv[2]]))


#####################################################################################
#####################################################################################
# 检查节点状态
def check_node_status(url):
    status_code_map = {
        200: "🟢",
        429: "🔴",
    }
    try:
        response = requests.get(f'https://{url}')
        return status_code_map.get(response.status_code, "节点异常")
    except Exception as e:
        logging.error(e)
        return '⭕️'


# 将当前日期移位n天，并返回移位日期和移位日期的前一个和下一个日期。
def date_shift(n: int = 0):
    today = datetime.date.today()
    shifted_date = datetime.date.fromordinal(today.toordinal() + n)
    previous_date = datetime.date.fromordinal(shifted_date.toordinal() - 1)
    next_date = datetime.date.fromordinal(shifted_date.toordinal() + 1)
    previous_date_string = previous_date.isoformat()
    next_date_string = next_date.isoformat()
    return shifted_date.isoformat(), previous_date_string, next_date_string

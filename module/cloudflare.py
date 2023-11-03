# -*- coding: UTF-8 -*-

import asyncio
import concurrent.futures
import concurrent.futures
import contextlib
import datetime

import httpx
from apscheduler.triggers.cron import CronTrigger
from loguru import logger
from pyrogram import filters, Client
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery, Message

from api.alist_api import storage_list, storage_enable, storage_disable, storage_update
from api.cloudflare_api import list_zones, list_filters, graphql_api
from config.config import nodee, cronjob, cloudflare_cfg, chat_data, write_config, admin
from tool.scheduler_manager import aps
from tool.utils import is_admin
from tool.utils import pybyte

return_button = [
    InlineKeyboardButton('↩️返回菜单', callback_data='cf_return'),
    InlineKeyboardButton('❌关闭菜单', callback_data='cf_close'),
]


def btn():
    return [
        [InlineKeyboardButton('⚙️CF节点管理', callback_data='⚙️')],
        [
            InlineKeyboardButton('👀查看节点', callback_data='cf_menu_node_status'),
            InlineKeyboardButton('📅通知设置', callback_data='cf_menu_cronjob'),
            InlineKeyboardButton('🆔账号管理', callback_data='cf_menu_account'),
        ],
        [
            InlineKeyboardButton('⚡️功能开关', callback_data='⚡️'),
        ],
        [
            InlineKeyboardButton(
                '✅节点状态监控' if cronjob()['status_push'] else '❎节点状态监控',
                callback_data='status_push_off'
                if cronjob()['status_push']
                else 'status_push_on',
            ),
            InlineKeyboardButton(
                '✅每日流量统计' if cronjob()['bandwidth_push'] else '❎每日流量统计',
                callback_data='bandwidth_push_off'
                if cronjob()['bandwidth_push']
                else 'bandwidth_push_on',
            ),
        ],
        [
            InlineKeyboardButton(
                '✅自动管理存储' if cronjob()['storage_mgmt'] else '❎自动管理存储',
                callback_data='storage_mgmt_off'
                if cronjob()['storage_mgmt']
                else 'storage_mgmt_on',
            ),
            InlineKeyboardButton(
                '✅自动切换节点' if cronjob()['auto_switch_nodes'] else '❎自动切换节点',
                callback_data='auto_switch_nodes_off'
                if cronjob()['auto_switch_nodes']
                else 'auto_switch_nodes_on',
            ),
        ],
        [
            InlineKeyboardButton('❌关闭菜单', callback_data='cf_close'),
        ],
    ]


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

@Client.on_callback_query(filters.regex('^cf_close$'))
async def cf_close_callback(_, query: CallbackQuery):
    chat_data["account_add"] = False
    await query.message.edit(text='已退出『节点管理』')


@Client.on_callback_query(filters.regex('^cf_menu_account$'))
async def cf_menu_account_callback(_, query: CallbackQuery):
    await account(query)


@Client.on_callback_query(filters.regex('^cf_menu_cronjob$'))
async def cf_menu_cronjob_callback(_, query: CallbackQuery):
    await cronjob_set(query)


@Client.on_callback_query(filters.regex('^cf_menu_node_status$'))
async def cf_menu_node_status_callback(_, query: CallbackQuery):
    chat_data['node_status_day'] = 0
    thread_pool.submit(asyncio.run, send_node_status(query, chat_data['node_status_day']))


@Client.on_callback_query(filters.regex('^cf_return$'))
async def cf_return_callback(_, query: CallbackQuery):
    await r_cf_menu(query)


# 节点状态按钮回调
@Client.on_callback_query(filters.regex('^gns_'))
async def node_status(_, message: CallbackQuery):
    query = message.data
    if chat_data['node_status_mode'] == 'menu':
        if query == 'gns_status_down':
            if 'node_status_day' in chat_data and chat_data['node_status_day']:
                chat_data['node_status_day'] += 1
                thread_pool.submit(asyncio.run, send_node_status(message, chat_data['node_status_day']))
        elif query == 'gns_status_up':
            chat_data['node_status_day'] -= 1
            thread_pool.submit(asyncio.run, send_node_status(message, chat_data['node_status_day']))
    elif chat_data['node_status_mode'] == 'command':
        if query == 'gns_expansion':
            chat_data['packUp'] = not chat_data['packUp']
            thread_pool.submit(asyncio.run, view_bandwidth_button(message, chat_data['node_status_day']))
        elif query == 'gns_status_down':
            if 'node_status_day' in chat_data and chat_data['node_status_day']:
                chat_data['node_status_day'] += 1
                thread_pool.submit(asyncio.run, view_bandwidth_button(message, chat_data['node_status_day']))
        elif query == 'gns_status_up':
            chat_data['node_status_day'] -= 1
            thread_pool.submit(asyncio.run, view_bandwidth_button(message, chat_data['node_status_day']))


# cf账号管理按钮回调
@Client.on_callback_query(filters.regex('^account_add$'))
async def account_add_callback(_, query: CallbackQuery):
    await account_add(query)
    chat_data['ad_message'] = query


@Client.on_callback_query(filters.regex('^account_return$'))
async def account_return_callback(_, query: CallbackQuery):
    chat_data["account_add"] = False
    await account(query)


# 按钮回调 通知设置
@Client.on_callback_query(filters.regex('cronjob_set'))
async def cronjob_set_callback(_, message: CallbackQuery):
    chat_data["cronjob_set"] = False
    await cronjob_set(message)


async def toggle_auto_management(client: Client, message: CallbackQuery, option, job_id, mode):
    query = message.data
    if query == f'{option}_off':
        cloudflare_cfg['cronjob'][option] = False
        logger.info(f'已关闭{option}')
        cc = cloudflare_cfg['cronjob']
        abc = all(not cc[key] for key in ('status_push', 'storage_mgmt', 'auto_switch_nodes'))
        if abc or option == 'bandwidth_push':
            logger.info('节点监控已关闭')
            aps.pause_job(job_id)
    elif query == f'{option}_on':
        cloudflare_cfg['cronjob'][option] = True
        logger.info(f'已开启{option}')
        aps.resume_job(job_id=job_id)
        if mode == 0:
            aps.add_job(func=send_cronjob_bandwidth_push, args=[client],
                        trigger=CronTrigger.from_crontab(cloudflare_cfg['cronjob']['time']),
                        job_id=job_id)
        elif mode == 1:
            aps.add_job(func=send_cronjob_status_push, args=[client],
                        trigger='interval',
                        job_id=job_id,
                        seconds=60)
    write_config('config/cloudflare_cfg.yaml', cloudflare_cfg)
    await r_cf_menu(message)


# 按钮回调 节点状态
@Client.on_callback_query(filters.regex('^status_push'))
async def status_push(client: Client, message: CallbackQuery):
    await toggle_auto_management(client, message, 'status_push', 'cronjob_status_push', 1)


# 按钮回调 每日带宽统计
@Client.on_callback_query(filters.regex('^bandwidth_push'))
async def bandwidth_push(client: Client, message: CallbackQuery):
    await toggle_auto_management(client, message, 'bandwidth_push', 'cronjob_bandwidth_push', 0)


# 按钮回调 自动存储管理
@Client.on_callback_query(filters.regex('^storage_mgmt'))
async def storage_mgmt(client: Client, message: CallbackQuery):
    await toggle_auto_management(client, message, 'storage_mgmt', 'cronjob_status_push', 1)


# 按钮回调 自动切换节点
@Client.on_callback_query(filters.regex('^auto_switch_nodes'))
async def auto_switch_nodes(client: Client, message: CallbackQuery):
    await toggle_auto_management(client, message, 'auto_switch_nodes', 'cronjob_status_push', 1)


#####################################################################################
#####################################################################################

# 监听普通消息
async def echo_cloudflare(message: Message):
    if 'account_add' in chat_data and chat_data["account_add"]:
        await account_edit(message)
    elif 'cronjob_set' in chat_data and chat_data["cronjob_set"]:
        await cronjob_set_edit(message)
        chat_data["cronjob_set"] = False


def cf_aaa():
    if nodee():
        nodes = [value['url'] for value in nodee()]
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = [executor.submit(check_node_status, node) for node in nodes]
        results = [future.result()[1] for future in concurrent.futures.wait(futures).done]
        return f'''
节点数量：{len(nodes)}
🟢  正常：{results.count(200)}
🔴  掉线：{results.count(429)}
⭕️  错误：{results.count(501)}
'''
    return 'Cloudflare节点管理\n暂无账号，请先添加cf账号'


# cf菜单
@Client.on_message(filters.command('sf') & filters.private & is_admin)
async def cf_menu(_, message: Message):
    msg = chat_data['cf_menu'] = await message.reply(text='检测节点中...', reply_markup=InlineKeyboardMarkup(btn()))
    await msg.edit(text=cf_aaa(), reply_markup=InlineKeyboardMarkup(btn()))


# 返回菜单
async def r_cf_menu(query: CallbackQuery):
    await query.message.edit(text=cf_aaa(), reply_markup=InlineKeyboardMarkup(btn()))


# 获取节点信息
def get_node_info(url, email, key, zone_id, day):
    d = date_shift(day)
    ga = graphql_api(email, key, zone_id, d[1], d[2])
    ga = ga.json()
    byte = ga['data']['viewer']['zones'][0]['httpRequests1dGroups'][0]['sum']['bytes']
    request = ga['data']['viewer']['zones'][0]['httpRequests1dGroups'][0]['sum']['requests']
    code = check_node_status(url)[1]
    if code == 200:
        code = '🟢'
    elif code == 429:
        code = '🔴'
    else:
        code = '⭕️'
    text = f'''
{url} | {code}
请求：<code>{request}</code> | 带宽：<code>{pybyte(byte)}</code>
———————'''

    return text, byte, code, request


# 菜单中的节点状态
async def send_node_status(query: CallbackQuery, day):
    chat_data['node_status_mode'] = 'menu'
    chat_data['node_status_expand'] = False
    chat_data['packUp'] = False
    button = [bandwidth_button_a, bandwidth_button_b, bandwidth_button_c, return_button]
    await query.message.edit(text='检测节点中...', reply_markup=InlineKeyboardMarkup(button))
    vv = get_node_status(day)
    a = [vv[1], vv[2], vv[3], return_button]
    await query.message.edit(text=vv[0], reply_markup=InlineKeyboardMarkup(a))


# 使用指令查看节点信息
@Client.on_message(filters.command('vb'))
async def view_bandwidth(_, message: Message):
    async def view_bandwidth_a(message_a: Message):
        chat_data['node_status_mode'] = 'command'
        chat_data['packUp'] = True
        chat_data['node_status_expand'] = False
        msg = await message_a.reply(text='检测节点中...')

        day = int(message_a.command[1]) if message_a.command[1:] else 0
        chat_data['node_status_day'] = day
        vv = get_node_status(day)
        state = '🔼点击展开🔼' if chat_data['packUp'] else '🔽点击收起🔽'
        button = [InlineKeyboardButton(state, callback_data='gns_expansion') if 'packUp' in chat_data and chat_data['packUp'] else None]
        text = vv[0]
        button = [button, vv[2], vv[3]] if 'packUp' in chat_data and chat_data['packUp'] else [button, vv[1], vv[2], vv[3]]
        await msg.edit_text(text=text, reply_markup=InlineKeyboardMarkup(button))

    thread_pool.submit(asyncio.run, view_bandwidth_a(message))


# view_bandwidth按钮
async def view_bandwidth_button(query: CallbackQuery, day):
    state = '🔼点击展开🔼' if chat_data['packUp'] else '🔽点击收起🔽'
    ab = [InlineKeyboardButton(state, callback_data='gns_expansion')]
    button = [ab, bandwidth_button_a, bandwidth_button_b, bandwidth_button_c]
    if 'packUp' in chat_data and chat_data['packUp']:
        button = [ab, bandwidth_button_b, bandwidth_button_c]
    await query.message.edit(text='检测节点中...', reply_markup=InlineKeyboardMarkup(button))
    vv = get_node_status(day)
    text = vv[0]

    button = [ab, vv[2], vv[3]] if 'packUp' in chat_data and chat_data['packUp'] else [ab, vv[1], vv[2], vv[3]]
    await query.message.edit(text=text, reply_markup=InlineKeyboardMarkup(button))


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
    text = ''.join(text)
    total_bandwidth = sum(i[1] for i in results)
    code = [i[2] for i in results]
    request = f'{int(sum(i[3] for i in results) / 10000)}W'

    text = f'''
节点数量：{len(code)}
🟢  正常：{code.count('🟢')}
🔴  掉线：{code.count('🔴')}
⭕️  错误：{code.count('⭕️')}
    ''' if 'packUp' in chat_data and chat_data['packUp'] else text

    button_b = [
        InlineKeyboardButton(
            f"🟢{code.count('🟢')}", callback_data='gns_total_bandwidth'
        ),
        InlineKeyboardButton(
            f"🔴{code.count('🔴')}", callback_data='gns_total_bandwidth'
        ),
        InlineKeyboardButton(
            f"⭕️{code.count('⭕️')}", callback_data='gns_total_bandwidth'
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

    return text, button_b, button_c, button_d, code


# 账号管理

async def account(query: CallbackQuery):
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
    await query.message.edit(text=t, reply_markup=InlineKeyboardMarkup([button, return_button]))


# 添加/删除账号
async def account_add(query: CallbackQuery):
    text = []
    chat_data['account_add_return_button'] = [
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
——————————————
<b>添加：</b>
一次只能添加一个账号
第一行cf邮箱，第二行global_api_key，例：
<code>abc123@qq.com
285812f3012365412d33398713c156e2db314
</code>
<b>删除：</b>
*+序号，例：<code>*2</code>
'''
    await query.message.edit(text=t + tt, reply_markup=InlineKeyboardMarkup([chat_data['account_add_return_button']]))
    chat_data["account_add"] = True


# 开始处理
async def account_edit(message: Message):
    mt = message.text
    await message.delete()
    if mt[0] != '*':
        try:
            i = mt.split('\n')

            lz = await list_zones(i[0], i[1])  # 获取区域id
            lz = lz.json()
            account_id = lz['result'][0]['account']['id']
            zone_id = lz['result'][0]['id']
            lf = await list_filters(i[0], i[1], zone_id)  # 获取url
            lf = lf.json()
        except Exception as e:
            await chat_data['ad_message'].answer(text=f'错误：{str(e)}')
        else:
            if lf['result']:
                url = lf['result'][0]['pattern'].rstrip('/*')
                d = {"url": url, "email": i[0], "global_api_key": i[1], "account_id": account_id, "zone_id": zone_id}
                if cloudflare_cfg['node']:
                    cloudflare_cfg['node'].append(d)
                else:
                    cloudflare_cfg['node'] = [d]
                write_config("config/cloudflare_cfg.yaml", cloudflare_cfg)
                await account_add(chat_data['ad_message'])
            else:
                text = f"""
<b>添加失败: </b>

<code>{mt}</code>

该域名（<code>{lz['result'][0]['name']}</code>）未添加Workers路由
请检查后重新发送账号

<b>注：</b>默认使用第一个域名的第一个Workers路由
"""
                await chat_data['ad_message'].message.edit(text=text, reply_markup=InlineKeyboardMarkup([chat_data['account_add_return_button']]))

    else:
        i = int(mt.split('*')[1])
        del cloudflare_cfg['node'][i - 1]
        write_config("config/cloudflare_cfg.yaml", cloudflare_cfg)
        await account_add(chat_data['ad_message'])


# 通知设置
async def cronjob_set(query: CallbackQuery):
    text = f"""
chat_id: <code>{",".join(list(map(str, cronjob()['chat_id']))) if cronjob()['chat_id'] else None}</code>
time: <code>{cronjob()['time'] or None}</code>
——————————
chat_id 可以填用户/群组/频道 id，支持多个，用英文逗号隔开

time 为带宽通知时间，格式为5位cron表达式

chat_id 和 time 一行一个，例：
<code>123123,321321
0 23 * * *</code>
"""

    await query.message.edit(text=text, reply_markup=InlineKeyboardMarkup([return_button]))

    chat_data["cronjob_set"] = True


# 通知设置
async def cronjob_set_edit(message: Message):
    d = message.text
    dd = d.split('\n')
    cloudflare_cfg['cronjob']['chat_id'] = [int(x) for x in dd[0].split(',')]
    cloudflare_cfg['cronjob']['time'] = dd[1]
    if cloudflare_cfg['cronjob']['bandwidth_push']:
        aps.modify_job(trigger=CronTrigger.from_crontab(cloudflare_cfg['cronjob']['time']),
                       job_id='cronjob_bandwidth_push')
    write_config('config/cloudflare_cfg.yaml', cloudflare_cfg)
    await message.delete()
    await chat_data['cf_menu'].edit(text=f"设置成功！\n-------\nchat_id：<code>{cloudflare_cfg['cronjob']['chat_id']}</code>"
                                         f"\ntime：<code>{cloudflare_cfg['cronjob']['time']}</code>",
                                    reply_markup=InlineKeyboardMarkup([return_button]))


# 带宽通知定时任务
async def send_cronjob_bandwidth_push(app):
    chat_data['packUp'] = True
    chat_data['node_status_expand'] = False
    vv = get_node_status(0)
    text = '今日流量统计'
    for i in cloudflare_cfg['cronjob']['chat_id']:
        await app.send_message(chat_id=i,
                               text=text,
                               reply_markup=InlineKeyboardMarkup([vv[1], vv[2]]))


# 　筛选出可用节点
async def returns_the_available_nodes(results):
    if cloudflare_cfg['cronjob']['auto_switch_nodes']:
        # 筛选出可用的节点
        node_pool = [f'https://{node}' for node, result in results if result == 200]
        # 已经在使用的节点
        sl = await storage_list()
        sl = sl.json()['data']['content']
        used_node = [node['down_proxy_url'] for node in sl if
                     node['webdav_policy'] == 'use_proxy_url' or node['web_proxy']]
        # 将已用的节点从可用节点中删除
        return [x for x in node_pool if x not in used_node]


# 节点状态通知定时任务
async def send_cronjob_status_push(app):
    if not nodee():
        return

    async def run():
        nodes = [value['url'] for value in nodee()]
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = [executor.submit(check_node_status, node) for node in nodes]
        # 全部节点
        results = [future.result() for future in concurrent.futures.wait(futures).done]
        available_nodes = await returns_the_available_nodes(results)

        for node, result in results:
            if node not in chat_data:
                chat_data[node] = result
                chat_data[f'{node}_count'] = 0

            if result == 200:
                text_a = f'🟢|{node}|恢复'
            elif result == 429:
                text_a = f'🔴|{node}|掉线'
                chat_data[f'{node}_count'] += 1
            else:
                text_a = f'⭕️|{node}|故障'
                chat_data[f'{node}_count'] += 1

            # 错误大于3次运行，否则不运行后面代码
            if result != 200 and 0 < chat_data[f'{node}_count'] <= 3:
                break
            await failed_node_management(app, result, node, text_a, available_nodes)

    thread_pool.submit(asyncio.run, run())


async def failed_node_management(app, result, node, text_a, available_nodes):
    if result == chat_data[node]:
        return
    chat_data[f'{node}_count'] = 0
    # 状态通知
    if cloudflare_cfg['cronjob']['status_push']:
        chat_data[node] = result
        for i in cloudflare_cfg['cronjob']['chat_id']:
            await app.send_message(chat_id=i, text=text_a)

    # 自动管理
    chat_data[node] = result
    st = await storage_list()
    st = st.json()
    for dc in st['data']['content']:
        if dc['down_proxy_url'] == f'https://{node}' and (dc['webdav_policy'] == 'use_proxy_url' or dc['web_proxy']):
            text = ''
            if result == 200 and dc['disabled']:
                await storage_enable(dc['id'])
                text = f'🟢|{node}|已开启存储：<code>{dc["mount_path"]}</code>'
                await app.send_message(chat_id=admin, text=text)
            elif result == 429 and not dc['disabled']:
                if available_nodes:
                    dc['down_proxy_url'] = available_nodes[0]
                    d = available_nodes[0].replace('https://', '')
                    if '节点：' in dc['remark']:
                        lines = dc['remark'].split('\n')
                        lines = [f"节点：{d}" if '节点：' in line else line for line in lines]
                        dc['remark'] = '\n'.join(lines)
                    else:
                        dc['remark'] = f"节点：{d}\n{dc['remark']}"
                    await storage_update(dc)
                    a = available_nodes[0].replace("https://", "")
                    text = f'🟡|<code>{dc["mount_path"]}</code>\n已自动切换节点： {node} --> {a}'
                    await app.send_message(chat_id=admin, text=text,
                                           disable_web_page_preview=True)
                elif cloudflare_cfg['cronjob']['storage_mgmt']:
                    await storage_disable(dc['id'])
                    text = f'🔴|{node}|已关闭存储：<code>{dc["mount_path"]}</code>'
                    await app.send_message(chat_id=admin, text=text,
                                           disable_web_page_preview=True)
            logger.info(text)


#####################################################################################
#####################################################################################
# 检查节点状态
def check_node_status(url):
    status_code_map = {
        200: [url, 200],
        429: [url, 429],
    }
    try:
        response = httpx.get(f'https://{url}')
        return status_code_map.get(response.status_code, [url, 502])
    except Exception as e:
        logger.error(e)
        return [url, 501]


# 将当前日期移位n天，并返回移位日期和移位日期的前一个和下一个日期。
def date_shift(n: int = 0):
    today = datetime.date.today()
    shifted_date = datetime.date.fromordinal(today.toordinal() + n)
    previous_date = datetime.date.fromordinal(shifted_date.toordinal() - 1)
    next_date = datetime.date.fromordinal(shifted_date.toordinal() + 1)
    previous_date_string = previous_date.isoformat()
    next_date_string = next_date.isoformat()
    return shifted_date.isoformat(), previous_date_string, next_date_string

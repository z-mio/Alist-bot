# -*- coding: UTF-8 -*-
import concurrent.futures
import datetime
import json
import logging
import requests
from pyrogram import filters
from pyrogram.handlers import MessageHandler, CallbackQueryHandler
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from api.cloudflare_api import list_zones, list_filters, graphql_api
from bot import handle_exception, Regular, scheduler, send_cronjob_bandwidth_push, admin_yz
from config.config import nodee, cronjob, cloudflare_cfg, chat_data, write_config
from module.search import pybyte

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


#####################################################################################
#####################################################################################
# 按钮回调
# 菜单按钮回调
async def cf_button_callback(client, message):
    query = message.data
    if query == 'cf_return':  # 返回菜单
        await r_cf_menu(client, message)
    elif query == 'cf_close':  # 关闭菜单
        chat_data["account_add"] = False
        await client.edit_message_text(chat_id=cf_menu_message.chat.id,
                                       message_id=cf_menu_message.id,
                                       text='已退出『节点管理』')


# cf账号管理按钮回调
async def account_button_callback(client, message):
    query = message.data
    if query == 'account_add':
        await account_add(client, message)
    elif query == 'account_return':
        chat_data["account_add"] = False
        await account(client, message)


# 节点状态按钮回调
async def node_status(client, message):
    query = message.data
    if query == 'cf_menu_node_status':
        chat_data['node_status_day'] = 0
        await get_node_status(client, message, chat_data['node_status_day'])
    elif query == 'cf_menu_node_status_up':
        chat_data['node_status_day'] -= 1
        await get_node_status(client, message, chat_data['node_status_day'])
    elif query == 'cf_menu_node_status_down':
        if 'node_status_day' in chat_data and chat_data['node_status_day']:
            chat_data['node_status_day'] += 1
            await get_node_status(client, message, chat_data['node_status_day'])


# 通知设置菜单按钮回调
async def cronjob_button_callback(client, message):
    query = message.data
    if query.startswith('cronjob_status'):
        cloudflare_cfg['cronjob']['status_push'] = query != 'cronjob_status_off'
        write_config('config/cloudflare_cfg.yaml', cloudflare_cfg)
        await cronjob_callback(client, message)
    elif query.startswith('cronjob_bandwidth'):
        if query == 'cronjob_bandwidth_off':
            cloudflare_cfg['cronjob']['bandwidth_push'] = False
            Regular().disable_scheduled_backup_task('cronjob_bandwidth_push')
        elif query == 'cronjob_bandwidth_on':
            cloudflare_cfg['cronjob']['bandwidth_push'] = True
            if any(
                    job.id != 'send_backup_messages_regularly_id'
                    for job in scheduler.get_jobs()
            ):  # 新建
                Regular().modify_scheduled_backup_task(cloudflare_cfg['cronjob']['time'], 'cronjob_bandwidth_push')
            else:
                Regular().new_scheduled_backup_task(send_cronjob_bandwidth_push, cloudflare_cfg['cronjob']['time'],
                                                    'cronjob_bandwidth_push')
        write_config('config/cloudflare_cfg.yaml', cloudflare_cfg)
        await cronjob_callback(client, message)
    elif query == 'cronjob_set':
        await cronjob_set(client, message)
    elif query == 'cronjob_set_return':
        chat_data["cronjob_set"] = False
        await cronjob_callback(client, message)


#####################################################################################
#####################################################################################

# 监听普通消息
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
    return 'Cloudflare节点管理'


# cf菜单
@admin_yz
async def cf_menu(client, message):
    chat_data['cf_menu_button'] = await client.send_message(chat_id=message.chat.id,
                                                            text=cf_aaa(),
                                                            reply_markup=InlineKeyboardMarkup(cf_menu_button))
    global cf_menu_message
    cf_menu_message = chat_data.get('cf_menu_button')


# 返回菜单
async def r_cf_menu(client, _):
    await client.edit_message_text(chat_id=cf_menu_message.chat.id,
                                   message_id=cf_menu_message.id,
                                   text=cf_aaa(),
                                   reply_markup=InlineKeyboardMarkup(cf_menu_button))


# 获取节点信息
def get_node_info(url, email, key, zone_id, day):
    d = date_shift(day)

    ga = graphql_api(email, key, zone_id, d[1], d[2])
    ga = json.loads(ga.text)
    byte = ga['data']['viewer']['zones'][0]['httpRequests1dGroups'][0]['sum']['bytes']
    request = ga['data']['viewer']['zones'][0]['httpRequests1dGroups'][0]['sum']['requests']
    text = f'''
{url} | {check_node_status(url)}
请求：<code>{request}</code> | 带宽：<code>{pybyte(byte)}</code>
———————'''

    return text, byte


# 发送节点状态
@handle_exception
async def get_node_status(client, _, day):
    await client.edit_message_text(chat_id=cf_menu_message.chat.id,
                                   message_id=cf_menu_message.id,
                                   text='加载中...',
                                   reply_markup=InlineKeyboardMarkup(cf_menu_button))
    d = date_shift(day)
    node_list = nodee()
    url, email, key, zone_id = zip(*[(n['url'], n['email'], n['global_api_key'], n['zone_id']) for n in node_list])
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [executor.submit(get_node_info, url_, email_, key_, zone_id_, day) for url_, email_, key_, zone_id_ in
                   zip(url, email, key, zone_id)]
    results = [future.result() for future in concurrent.futures.wait(futures).done]
    text = [i[0] for i in results]
    total_bandwidth = sum(i[1] for i in results)
    button = [
        [
            InlineKeyboardButton(f'总带宽：{pybyte(total_bandwidth)}', callback_data='cf_total_bandwidth')
        ],
        [
            InlineKeyboardButton('上一天', callback_data='cf_menu_node_status_up'),
            InlineKeyboardButton(d[0], callback_data='cf_menu_node_status_calendar'),
            InlineKeyboardButton('下一天', callback_data='cf_menu_node_status_down')
        ],
        return_button
    ]
    await client.edit_message_text(chat_id=cf_menu_message.chat.id,
                                   message_id=cf_menu_message.id,
                                   text=''.join(text),
                                   reply_markup=InlineKeyboardMarkup(button))


def vvv(m):
    if nodee():
        try:
            return _extracted_from_vvv_4(m)
        except Exception as e:
            logging.error(e)
            return e, [[InlineKeyboardButton('错误', callback_data='noooooo')]]
    return '请先添加账号', [[InlineKeyboardButton('请先添加账号', callback_data='noooooo')]]


# TODO Rename this here and in `vvv`
def _extracted_from_vvv_4(m):
    s = m or 0
    d = date_shift(int(s))
    node_list = nodee()
    url, email, key, zone_id = zip(*[(n['url'], n['email'], n['global_api_key'], n['zone_id']) for n in node_list])
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [executor.submit(get_node_info, url_, email_, key_, zone_id_, int(s)) for
                   url_, email_, key_, zone_id_
                   in
                   zip(url, email, key, zone_id)]
    results = [future.result() for future in concurrent.futures.wait(futures).done]
    text = [i[0] for i in results]
    total_bandwidth = sum(i[1] for i in results)
    button = [
        [
            InlineKeyboardButton(d[0], callback_data='cf_menu_node_status_calendar')
        ],
        [
            InlineKeyboardButton(f'总带宽：{pybyte(total_bandwidth)}', callback_data='cf_total_bandwidth')
        ]
    ]
    return ''.join(text), button


# 使用指令查看节点信息
@handle_exception
async def view_bandwidth(client, message):
    m = ' '.join(message.command[1:])
    vv = vvv(m)
    await client.send_message(chat_id=message.chat.id,
                              text=vv[0],
                              reply_markup=InlineKeyboardMarkup(vv[1]))


# 账号管理
async def account(client, _):
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
    await client.edit_message_text(chat_id=cf_menu_message.chat.id,
                                   message_id=cf_menu_message.id,
                                   text=t,
                                   reply_markup=InlineKeyboardMarkup([button, return_button]))


# 添加/删除账号
async def account_add(client, _):
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
    await client.edit_message_text(chat_id=cf_menu_message.chat.id,
                                   message_id=cf_menu_message.id,
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
async def cronjob_callback(client, _):
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
    await client.edit_message_text(chat_id=cf_menu_message.chat.id,
                                   message_id=cf_menu_message.id,
                                   text='通知设置',
                                   reply_markup=InlineKeyboardMarkup(button))


# 通知设置
async def cronjob_set(client, _):
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

    await client.edit_message_text(chat_id=cf_menu_message.chat.id,
                                   message_id=cf_menu_message.id,
                                   text=text,
                                   reply_markup=InlineKeyboardMarkup([cronjob_set_return_button]))
    chat_data["cronjob_set"] = True


# 通知设置
async def cronjob_set_edit(_, message):
    d = message.text
    dd = d.split('\n')
    cloudflare_cfg['cronjob']['chat_id'] = [int(x) for x in dd[0].split(',')]
    cloudflare_cfg['cronjob']['time'] = dd[1]
    if cloudflare_cfg['cronjob']['bandwidth_push']:
        Regular().modify_scheduled_backup_task(cloudflare_cfg['cronjob']['time'], 'cronjob_bandwidth_push')
    write_config('config/cloudflare_cfg.yaml', cloudflare_cfg)


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


#####################################################################################
#####################################################################################

cloudflare_handlers = [
    MessageHandler(cf_menu, filters.command('sf') & filters.private),
    MessageHandler(view_bandwidth, filters.command('vb')),
    MessageHandler(echo_cloudflare, (filters.text & filters.private) & ~filters.regex(r'^\/')),
    CallbackQueryHandler(node_status, filters.regex(r'cf_menu_node_status')),
    CallbackQueryHandler(account, filters.regex('cf_menu_account')),
    CallbackQueryHandler(account_button_callback, filters.regex('account_')),
    CallbackQueryHandler(cronjob_callback, filters.regex('cf_menu_cronjob')),
    CallbackQueryHandler(cf_button_callback, filters.regex(r'^cf')),
    CallbackQueryHandler(cronjob_button_callback, filters.regex(r'^cronjob')),
]

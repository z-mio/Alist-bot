# -*- coding: UTF-8 -*-
import re
import requests
import json
import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler, CommandHandler

from bot import admin_yz, alist_host, alsit_token

mount_path = []
disabled = []
id = []
button_v = []
button_c = []


## 获取存储
async def get_storage(alist_host, alsit_tokenn):
    vs_alist_url = alist_host + '/api/admin/storage/list'
    vs_alist_header = {"Authorization": alsit_tokenn, }
    vs_alist_post = requests.get(vs_alist_url, headers=vs_alist_header)
    vs_data = json.loads(vs_alist_post.text)

    mount_path.clear()
    disabled.clear()
    id.clear()
    button_v.clear()
    button_c.clear()
    for item in vs_data['data']['content']:
        mount_path.append(item['mount_path'])
        disabled.append(item['disabled'])
        id.append(item['id'])

    global disabled_a
    global button_js
    global cs_js
    for button_js in range(len(mount_path)):
        cs_js = button_js + 1001
        if disabled[button_js] == True:
            disabled_a = '❌'
        else:
            disabled_a = '✅'
        button_vs = InlineKeyboardButton(mount_path[button_js] + disabled_a, callback_data=str(button_js))
        button_cs = InlineKeyboardButton(mount_path[button_js] + disabled_a, callback_data=str(cs_js))
        button_v.append([button_vs])
        button_c.append([button_cs])
    return


## 查看存储
async def vs(update, context):
    if await admin_yz(update, context):
        await get_storage(alist_host, alsit_token)
        await update.message.reply_text(reply_to_message_id=update.message.message_id,
                                        text='点击开启/关闭存储\n存储列表：',
                                        reply_markup=InlineKeyboardMarkup(button_v)
                                        )


## 复制存储
async def cs(update, context):
    if await admin_yz(update, context):
        await get_storage(alist_host, alsit_token)
        await update.message.reply_text(reply_to_message_id=update.message.message_id,
                                        text='点击复制存储\n存储列表：',
                                        reply_markup=InlineKeyboardMarkup(button_c)
                                        )


async def ns(update, context):
    if await admin_yz(update, context):
        ns_storage = [{

        }]

        ns_alist_url = alist_host + '/api/admin/storage/create'
        ns_alist_header = {"Authorization": alsit_token}
        ns_alist_body = ns_storage[0]
        ns_alist_post = requests.post(ns_alist_url, json=ns_alist_body, headers=ns_alist_header)
        ns_json = json.loads(ns_alist_post.text)


## 按钮调用，开启关闭存储
async def button_get_storage(update):
    query = update.callback_query
    # 获取被按下按钮的 callback_data 值
    button_value = query.data
    bvj = int(button_value)
    if bvj <= 1000:
        if disabled[bvj] == True:
            of = "enable"
            of_t = "✅已开启存储："
        else:
            of = "disable"
            of_t = "❌已关闭存储："
        of_alist_url = alist_host + '/api/admin/storage/' + of + '?id=' + str(id[int(bvj)])
        of_alist_header = {"Authorization": alsit_token}
        of_alist_post = requests.post(of_alist_url, headers=of_alist_header)
        await get_storage(alist_host, alsit_token)
        await query.edit_message_text(
            text=of_t + mount_path[bvj],
            reply_markup=InlineKeyboardMarkup(button_v)
        )
    elif 2000 >= bvj >= 1000:
        bvj -= 1001

        cs_alist_url = alist_host + '/api/admin/storage/get?id=' + str(id[int(bvj)])
        cs_alist_header = {"Authorization": alsit_token}
        cs_alist_get = requests.get(cs_alist_url, headers=cs_alist_header)
        cs_json = json.loads(cs_alist_get.text)

        cs_storage = []
        cs_storage.clear()

        cs_storage.append(cs_json['data'])
        del cs_storage[0]['id']

        cs_mount_path = cs_storage[0]['mount_path']
        cs_order = cs_storage[0]['order']

        now = datetime.datetime.now()
        current_time = now.strftime("%M%S")  ## 获取当前时间

        if '.balance' not in cs_mount_path:
            cs_storage[0]['mount_path'] = cs_mount_path + '.balance' + current_time
        else:
            cs_mount_path_text = re.sub('.balance.*', '', cs_mount_path)
            cs_storage[0]['mount_path'] = cs_mount_path_text + '.balance' + current_time

        cs_storage[0]['order'] = cs_order + 1  ## 基于当前配置的排序加1
        cs_storage[0]['remark'] = mount_path[bvj] + ' -> ' + cs_storage[0]['mount_path']  ##修改配置文件

        cs_alist_url = alist_host + '/api/admin/storage/create'
        cs_alist_header = {"Authorization": alsit_token}
        cs_alist_body = cs_storage[0]
        cs_alist_post = requests.post(cs_alist_url, json=cs_alist_body, headers=cs_alist_header)
        cs_json = json.loads(cs_alist_post.text)

        await get_storage(alist_host, alsit_token)
        await query.edit_message_text(
            text='已复制\n' + mount_path[bvj] + ' -> ' + cs_storage[0]['mount_path'],
            reply_markup=InlineKeyboardMarkup(button_c)
        )


vs_handler = CommandHandler('vs', vs)
cs_handler = CommandHandler('cs', cs)
ns_handler = CommandHandler('ns', ns)
button_get_storage_handler = CallbackQueryHandler(button_get_storage)

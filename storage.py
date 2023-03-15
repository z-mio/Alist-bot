# -*- coding: UTF-8 -*-
import re
import requests
import json
import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler, CommandHandler

from bot import admin_yz, alist_host, alsit_token

mount_path = [] ## 存储路径
disabled = [] ## 存储是否禁用
id = [] ## 存储id
vs_button_list = [] ## 开关存储的按钮
cs_button_list = [] ## 复制存储的按钮
ns_button_list = [] ## 支持添加的存储的按钮

## 获取存储
async def get_storage(alist_host, alsit_tokenn):
    vs_alist_url = alist_host + '/api/admin/storage/list'
    vs_alist_header = {"Authorization": alsit_tokenn, }
    vs_alist_post = requests.get(vs_alist_url, headers=vs_alist_header)
    vs_data = json.loads(vs_alist_post.text)

    mount_path.clear()
    disabled.clear()
    id.clear()
    vs_button_list.clear()
    cs_button_list.clear()
    for item in vs_data['data']['content']:
        mount_path.append(item['mount_path'])
        disabled.append(item['disabled'])
        id.append(item['id'])

    global disabled_a
    global button_js
    global cs_js
    for button_js in range(len(mount_path)):
        if disabled[button_js] == True:
            disabled_a = '❌'
        else:
            disabled_a = '✅'
        button_vs = InlineKeyboardButton(mount_path[button_js] + disabled_a, callback_data=str(button_js))
        button_cs = InlineKeyboardButton(mount_path[button_js] + disabled_a, callback_data=str(button_js + 1001))
        vs_button_list.append([button_vs])
        cs_button_list.append([button_cs])
    return


## 查看存储
async def vs(update, context):
    if await admin_yz(update, context):
        await get_storage(alist_host, alsit_token)
        await update.message.reply_text(reply_to_message_id=update.message.message_id,
                                        text='点击开启/关闭存储\n存储列表：',
                                        reply_markup= InlineKeyboardMarkup(vs_button_list)
                                        )


## 复制存储
async def cs(update, context):
    if await admin_yz(update, context):
        await get_storage(alist_host, alsit_token)
        await update.message.reply_text(reply_to_message_id=update.message.message_id,
                                        text='点击复制存储\n存储列表：',
                                        reply_markup=InlineKeyboardMarkup(cs_button_list)
                                        )


## 添加存储
async def ns(update, context):
    if await admin_yz(update, context):
        storage_list = ['WebDav','Onedrive'] ## 支持添加的存储列表
        global storage_list_js
        for storage_list_js in range(len(storage_list)):
            button_ns = InlineKeyboardButton(storage_list[storage_list_js], callback_data=str(storage_list_js + 2001))
            ns_button_list.append([button_ns])
        await update.message.reply_text(reply_to_message_id=update.message.message_id,
                                        text='支持添加的存储：',
                                        reply_markup=InlineKeyboardMarkup(ns_button_list)
                                        )


## 按钮调用，开启关闭存储
async def vs_button(update, context):
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
            reply_markup=InlineKeyboardMarkup(vs_button_list)
        )

    elif 2000 > bvj >= 1000:
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
            reply_markup=InlineKeyboardMarkup(cs_button_list)
        )

    elif 3000 > bvj >= 2000:
        bvj -= 2001

        print(bvj)






vs_handler = CommandHandler('vs', vs)
cs_handler = CommandHandler('cs', cs)
ns_handler = CommandHandler('ns', ns)
vs_button_handler = CallbackQueryHandler(vs_button)

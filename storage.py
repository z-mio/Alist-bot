# -*- coding: UTF-8 -*-

import requests
import json
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler, CommandHandler

from bot import admin_yz

mount_path = []
disabled = []
id = []
button_q = []

## 获取存储
async def get_storage(alist_host, alsit_tokenn):
    vs_alist_url = alist_host + '/api/admin/storage/list'
    vs_alist_header = {"Authorization": alsit_tokenn, }
    vs_alist_post = requests.get(vs_alist_url, headers=vs_alist_header)
    vs_data = json.loads(vs_alist_post.text)

    mount_path.clear()
    disabled.clear()
    id.clear()
    button_q.clear()

    for item in vs_data['data']['content']:
        mount_path.append(item['mount_path'])
        disabled.append(item['disabled'])
        id.append(item['id'])

    global disabled_a
    global i
    for i in range(len(mount_path)):
        if disabled[i] == True:
            disabled_a = '❌'
        else:
            disabled_a = '✅'
        button = InlineKeyboardButton(mount_path[i] + disabled_a, callback_data=str(i))
        button_q.append([button])
    return

## 查看存储
async def vs(update, context):
    from bot import alist_host, alsit_token
    from telegram import InlineKeyboardMarkup
    if await admin_yz(update, context):
        await get_storage(alist_host, alsit_token)

        reply_button = InlineKeyboardMarkup(button_q)
        await update.message.reply_text(reply_to_message_id=update.message.message_id,
                                        text='点击开启/关闭存储\n存储列表：',
                                        reply_markup=reply_button
                                        )

## 按钮调用，开启关闭存储
async def button_get_storage(update, context):
    from bot import alist_host, alsit_token
    if await admin_yz(update, context):

        query = update.callback_query
        # 获取被按下按钮的 callback_data 值
        button_value = query.data
        i = int(button_value)
        if disabled[i] == True:
            of = "enable"
            of_t = "✅已开启存储："
        else:
            of = "disable"
            of_t = "❌已关闭存储："
        of_alist_url = alist_host + '/api/admin/storage/' + of + '?id=' + str(id[int(button_value)])
        of_alist_header = {"Authorization": alsit_token}
        of_alist_post = requests.post(of_alist_url, headers=of_alist_header)

        await get_storage(alist_host, alsit_token)

        reply_button = InlineKeyboardMarkup(button_q)
        await query.edit_message_text(
            text=of_t + mount_path[i], reply_markup=reply_button
        )





vs_handler = CommandHandler('vs', vs)

button_get_storage_handler = CallbackQueryHandler(button_get_storage)

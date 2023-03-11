# -*- coding: UTF-8 -*-

import requests
import json
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler, CommandHandler

mount_path = []
disabled = []
id = []
button_q = []


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


async def vs(update, context):
    from bot import alist_host, alsit_token, admin
    from telegram import InlineKeyboardMarkup
    user_id = update.message.from_user.id
    if user_id in admin:

        await get_storage(alist_host, alsit_token)

        reply_button = InlineKeyboardMarkup(button_q)
        await update.message.reply_text(reply_to_message_id=update.message.message_id,
                                        text='点击开启/关闭存储\n存储列表：',
                                        reply_markup=reply_button
                                        )
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text="该命令仅管理员可用"
                                       )


async def button_callback(update, context):
    from bot import alist_host, alsit_token, admin
    user_id = update.message.from_user.id
    if user_id in admin:

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
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text="该命令仅管理员可用"
                                       )

vs_handler = CommandHandler('vs', vs)

button_callback_handler = CallbackQueryHandler(button_callback)

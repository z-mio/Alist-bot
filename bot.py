# -*- coding: UTF-8 -*-

import datetime
import json
import logging
import os

import requests
import telegram
import yaml
from telegram import Update, BotCommand
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, filters, MessageHandler

from config.config import admin, bot_token, alist_host, alist_token

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# bot菜单
bot_menu = [BotCommand(command="start", description="开始"),
            BotCommand(command="s", description="搜索文件"),
            BotCommand(command="sl", description="设置搜索结果数量"),
            BotCommand(command="zl", description="开启/关闭 直链"),
            BotCommand(command="st", description="存储管理"),
            BotCommand(command="cf", description="查看当前配置"),
            BotCommand(command="bc", description="备份Alist配置"),
            ]


# 管理员验证
def admin_yz(func):  # sourcery skip: remove-unnecessary-else
    async def wrapper(update, context, *args, **kwargs):
        user_id = update.effective_user.id
        try:
            query = update.callback_query
            query_user_id = query.from_user.id
        except AttributeError:
            query_user_id = 2023

        if user_id in admin():
            return await func(update, context, *args, **kwargs)
        else:
            if query_user_id in admin():
                return await func(update, context, *args, **kwargs)
            else:
                await context.bot.send_message(chat_id=update.effective_chat.id, text="该命令仅管理员可用")

    return wrapper


# 开始
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="发送 /s+文件名 进行搜索")


# 设置菜单
@admin_yz
async def menu(update, context):
    await telegram.Bot(token=bot_token).set_my_commands(bot_menu)  # 全部可见
    await context.bot.send_message(chat_id=update.effective_chat.id,
                                   text="菜单设置成功，请退出聊天界面重新进入来刷新菜单")


# 查看当前配置
@admin_yz
async def cf(update, context):
    with open("config/config.yaml", 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    with open("config/cn_dict.json", 'r', encoding='utf-8') as ff:
        cn_dict = json.load(ff)
    b = translate_key(translate_key(config, cn_dict["config_cn"]), cn_dict["common"])
    text = json.dumps(b, indent=4, ensure_ascii=False)
    await context.bot.send_message(chat_id=update.effective_chat.id,
                                   text=f'<code>{text}</code>',
                                   parse_mode=telegram.constants.ParseMode.HTML)


# 监听普通消息
async def echo_bot(update, context):
    if "bc" in context.chat_data and context.chat_data["bc"]:
        message = update.message
        if message.reply_to_message:
            bc_message_id = context.chat_data.get("bc_message_id")
            if message.reply_to_message.message_id == bc_message_id.message_id:
                note_message_text = message.text
                await context.bot.delete_message(chat_id=message.chat.id,
                                                 message_id=message.message_id)
                await context.bot.edit_message_caption(chat_id=bc_message_id.chat.id,
                                                       message_id=bc_message_id.message_id,
                                                       caption=f'#Alist配置备份\n{note_message_text}')
        else:
            context.chat_data["bc"] = False
            context.chat_data.pop("bc_message_id", None)


# 配置备份
@admin_yz
async def bc(update, context):
    bc_list = ['setting', 'user', 'storage', 'meta']
    bc_dic = {'settings': '', 'users': 'users', 'storages': '', 'metas': ''}
    for i in range(len(bc_list)):
        bc_url = f'{alist_host}/api/admin/{bc_list[i]}/list'
        bc_header = {"Authorization": alist_token, 'accept': 'application/json'}
        bc_post = requests.get(bc_url, headers=bc_header)
        data = json.loads(bc_post.text)
        bc_dic[f'{bc_list[i]}s'] = data['data'] if i == 0 else data['data']['content']
    data = json.dumps(bc_dic, indent=4, ensure_ascii=False)  # 格式化json
    now = datetime.datetime.now()
    current_time = now.strftime("%Y_%m_%d_%H_%M_%S")  # 获取当前时间
    bc_file_name = f'alist_bot_backup_{current_time}.json'
    with open(bc_file_name, 'w', encoding='utf-8') as b:
        b.write(str(data))

    context.chat_data["bc_message_id"] = await context.bot.send_document(chat_id=update.effective_chat.id,
                                                                         document=bc_file_name,
                                                                         caption='#Alist配置备份')
    context.chat_data["bc"] = True
    os.remove(bc_file_name)


#####################################################################################

#####################################################################################


# 列表/字典key翻译，输入：待翻译列表/字典，翻译字典 输出：翻译后的列表/字典
def translate_key(list_or_dict, translation_dict):  # sourcery skip: assign-if-exp
    if isinstance(list_or_dict, dict):
        def translate_zh(_key):
            translate_dict = translation_dict
            # 如果翻译字典里有当前的key，就返回对应的中文字符串
            if _key in translate_dict:
                return translate_dict[_key]
            # 如果翻译字典里没有当前的key，就返回原字符串
            else:
                return _key

        new_dict_or_list = {}  # 存放翻译后key的字典
        # 遍历原字典里所有的键值对
        for key, value in list_or_dict.items():
            # 如果当前的值还是字典，就递归调用自身
            if isinstance(value, dict):
                new_dict_or_list[translate_zh(key)] = translate_key(value, translation_dict)
            # 如果当前的值不是字典，就把当前的key翻译成中文，然后存到新的字典里
            else:
                new_dict_or_list[translate_zh(key)] = value
    else:
        new_dict_or_list = []
        for index, value in enumerate(list_or_dict):
            if value in translation_dict.keys():
                new_dict_or_list.append(translation_dict[value])
            else:
                new_dict_or_list.append(value)
    return new_dict_or_list


#####################################################################################
#####################################################################################
def main():
    import search
    import storage

    application = ApplicationBuilder().token(bot_token).build()

    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('bc', bc))
    application.add_handler(CommandHandler('cf', cf))
    application.add_handler(CommandHandler('menu', menu))

    # 监听普通消息
    async def e(update, context):
        await storage.echo_storage(update, context)
        await echo_bot(update, context)

    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), e))

    # search
    application.add_handler(search.zl_handler)
    application.add_handler(search.sl_handler)
    application.add_handler(search.s_handler)

    # storage
    application.add_handler(storage.st_handler)
    application.add_handler(storage.st_button_callback_handler)
    application.add_handler(storage.vs_button_callback_handler)
    application.add_handler(storage.cs_button_callback_handler)
    application.add_handler(storage.ds_button_callback_handler)
    application.add_handler(storage.ns_button_callback_handler)

    application.run_polling()  # 启动


if __name__ == '__main__':
    main()

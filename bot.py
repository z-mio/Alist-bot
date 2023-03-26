# -*- coding: UTF-8 -*-

import datetime
import json
import logging
import os

import requests
import telegram
import yaml
from telegram import Update, BotCommand
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

with open("config/config.yaml", 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

admin = alist_host = alist_web = alist_token = bot_token = per_page = z_url = False


def cfg():
    global admin, alist_host, alist_web, alist_token, bot_token, per_page, z_url
    admin = config['user']['admin']  ## 管理员 id
    alist_host = config['user']['alist_host']  ## alist ip:port
    alist_web = config['search']['alist_web']  ## 你的alist域名
    alist_token = config['user']['alist_token']  ## alist token
    bot_token = config['user']['bot_token']  ## bot的key，用 @BotFather 获取
    per_page = config['search']['per_page']  ## 搜索结果返回数量，默认5条
    z_url = config['search']['z_url']  ## 是否开启直链
    return


cfg()


## bot菜单
bot_menu = [BotCommand(command="start", description="开始"),
            BotCommand(command="s", description="搜索文件"),
            BotCommand(command="sl", description="设置搜索结果数量"),
            BotCommand(command="zl", description="开启/关闭 直链"),
            BotCommand(command="st", description="存储管理"),
            BotCommand(command="cf", description="查看当前配置"),
            BotCommand(command="bc", description="备份Alist配置"),
            ]


## 管理员验证
def admin_yz(func):
    async def wrapper(update, context):
        user_id = update.effective_user.id
        try:
            query = update.callback_query
            query_user_id = query.from_user.id
        except AttributeError:
            query_user_id = 2023

        if user_id in admin:
            return await func(update, context)
        else:
            if query_user_id in admin:
                return await func(update, context)
            else:
                await context.bot.send_message(chat_id=update.effective_chat.id, text="该命令仅管理员可用")

    return wrapper


## 开始
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="发送 /s+文件名 进行搜索")


## 设置菜单
@admin_yz
async def menu(update, context):
    await telegram.Bot(token=bot_token).set_my_commands(bot_menu)  ##  全部可见
    await context.bot.send_message(chat_id=update.effective_chat.id, text="菜单设置成功，请退出聊天界面重新进入来刷新菜单")


## 查看当前配置
@admin_yz
async def cf(update, context):
    with open("config/cn_dict.json", 'r', encoding='utf-8') as ff:
        cn_dict = json.load(ff)
    a = translate_key(config, cn_dict["config_cn"])
    b = translate_key(a, cn_dict["common"])
    text = json.dumps(b, indent=4, ensure_ascii=False)
    await context.bot.send_message(chat_id=update.effective_chat.id,
                                   text=f'<code>{text}</code>',
                                   parse_mode=telegram.constants.ParseMode.HTML)


## 配置备份
@admin_yz
async def bc(update, context):
    bc_list = ['setting', 'user', 'storage', 'meta']
    bc_dic = {'settings': '', 'users': 'users', 'storages': '', 'metas': ''}
    for i in range(len(bc_list)):
        bc_url = alist_host + '/api/admin/' + bc_list[i] + '/list'
        bc_header = {"Authorization": alist_token, 'accept': 'application/json'}
        bc_post = requests.get(bc_url, headers=bc_header)
        data = json.loads(bc_post.text)
        if i == 0:
            bc_dic[bc_list[i] + 's'] = data['data']
        else:
            bc_dic[bc_list[i] + 's'] = data['data']['content']
    data = json.dumps(bc_dic, indent=4, ensure_ascii=False)  ## 格式化json
    now = datetime.datetime.now()
    current_time = now.strftime("%Y_%m_%d_%H_%M_%S")  ## 获取当前时间
    bc_file_name = ('alist_bot_backup_' + current_time + '.json')
    with open(bc_file_name, 'w', encoding='utf-8') as b:
        b.write(str(data))
    await context.bot.send_document(chat_id=update.effective_chat.id, document=bc_file_name,
                                    caption='#Alist配置备份')
    os.remove(bc_file_name)


#####################################################################################
## 函数
#####################################################################################


'''
## 管理员验证
async def admin_yz(update: Update, context):
    user_id = update.effective_user.id
    if user_id in admin:
        return True
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="该命令仅管理员可用")
        return False
'''


## 字典key翻译，输入：待翻译字典，翻译字典 输出：翻译后的新字典
def translate_key(old_dict, translation_dict):
    def translate_zh(key):
        translate_dict = translation_dict
        # 如果翻译字典里有当前的key，就返回对应的中文字符串
        if key in translate_dict:
            return translate_dict[key]
        # 如果翻译字典里没有当前的key，就返回原字符串
        else:
            return key

    new_dict = {}  # 存放翻译后key的字典
    # 遍历原字典里所有的键值对
    for key, value in old_dict.items():
        # 如果当前的值还是字典，就递归调用自身
        if isinstance(value, dict):
            new_dict[translate_zh(key)] = translate_key(value, translation_dict)
        # 如果当前的值不是字典，就把当前的key翻译成中文，然后存到新的字典里
        else:
            new_dict[translate_zh(key)] = value
    return new_dict


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

    # search
    application.add_handler(search.zl_handler)
    application.add_handler(search.sl_handler)
    application.add_handler(search.s_handler)

    # storage
    application.add_handler(storage.echo_handler)
    application.add_handler(storage.st_handler)
    application.add_handler(storage.st_button_callback_handler)
    application.add_handler(storage.vs_button_callback_handler)
    application.add_handler(storage.cs_button_callback_handler)
    application.add_handler(storage.ds_button_callback_handler)
    application.add_handler(storage.ns_button_callback_handler)

    application.run_polling()  ## 启动


if __name__ == '__main__':
    main()

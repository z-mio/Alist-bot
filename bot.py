# -*- coding: UTF-8 -*-

import os
import requests
import logging
import math

import telegram
import yaml
import json
import datetime


from telegram import Update, BotCommand
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import search
import storage

with open("config.yaml", 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

admin = config['admin']  ## 管理员 id
alist_host = config['alist_host']  ## alist ip:port
alist_web = config['alist_web']  ## 你的alist域名
alsit_token = config['alsit_token']  ## alist token
bot_api = config['bot_api']  ## bot的key，用 @BotFather 获取
per_page = config['per_page']  ## 搜索结果返回数量，默认5条
z_url = config['z_url']  ## 是否开启直链

## bot菜单
bot_menu = [BotCommand(command="start", description="开始"),
            BotCommand(command="s", description="搜索文件"),
            BotCommand(command="cf", description="查看当前配置"),
            BotCommand(command="sl", description="设置搜索结果数量"),
            BotCommand(command="zl", description="开启/关闭 直链"),
            BotCommand(command="vs", description="启用/停用 存储"),
            BotCommand(command="cs", description="复制存储"),
            BotCommand(command="bc", description="备份Alist配置"),
            ]



logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

## 字节数转文件大小
__all__ = ['pybyte']

def pybyte(size, dot=2):
    size = float(size)
    # 位 比特 bit
    if 0 <= size < 1:
        human_size = str(round(size / 0.125, dot)) + 'b'
    # 字节 字节 Byte
    elif 1 <= size < 1024:
        human_size = str(round(size, dot)) + 'B'
    # 千字节 千字节 Kilo Byte
    elif math.pow(1024, 1) <= size < math.pow(1024, 2):
        human_size = str(round(size / math.pow(1024, 1), dot)) + 'KB'
    # 兆字节 兆 Mega Byte
    elif math.pow(1024, 2) <= size < math.pow(1024, 3):
        human_size = str(round(size / math.pow(1024, 2), dot)) + 'MB'
    # 吉字节 吉 Giga Byte
    elif math.pow(1024, 3) <= size < math.pow(1024, 4):
        human_size = str(round(size / math.pow(1024, 3), dot)) + 'GB'
    # 太字节 太 Tera Byte
    elif math.pow(1024, 4) <= size < math.pow(1024, 5):
        human_size = str(round(size / math.pow(1024, 4), dot)) + 'TB'
    # 负数
    else:
        raise ValueError('{}() takes number than or equal to 0, but less than 0 given.'.format(pybyte.__name__))
    return human_size



async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="发送 /s+文件名 进行搜索")


## 管理员验证
async def admin_yz(update, context):
    user_id = update.message.from_user.id
    if user_id in admin:
        return True
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="该命令仅管理员可用")
        return False

## 设置菜单
async def menu(update, context):
    if await admin_yz(update, context):
        await telegram.Bot(token=bot_api).set_my_commands(bot_menu)
        await context.bot.send_message(chat_id=update.effective_chat.id, text="菜单设置成功")


## 查看当前配置
async def cf(update, context):
    if await admin_yz(update, context):
        conf_text = f'''
当前配置：
    管理员列表：
    {admin}
    搜索结果数量：{per_page}
    是否开启直链：{z_url}
'''
        await context.bot.send_message(chat_id=update.effective_chat.id, text=conf_text)



## 设置搜索结果数量
async def sl(update, context):
    text_caps = update.message.text
    sl_str = text_caps.strip("/sl @")

    if await admin_yz(update, context):
        print(admin_yz)
        if sl_str.isdigit():
            config['per_page'] = int(sl_str)
            with open('config.yaml', 'w') as f:
                yaml.dump(config, f)
            await context.bot.send_message(chat_id=update.effective_chat.id, text="已修改搜索结果数量为：" + sl_str)
        else:
            await context.bot.send_message(chat_id=update.effective_chat.id, text="请输入正整数")
        global per_page
        per_page = config['per_page']


## 设置直链
async def zl(update, context):
    text_caps = update.message.text
    zl_str = text_caps.strip("/zl @")

    if await admin_yz(update, context):
        if zl_str == "1":
            config['z_url'] = True
            await context.bot.send_message(chat_id=update.effective_chat.id, text="已开启直链")
        elif zl_str == "0":
            config['z_url'] = False
            await context.bot.send_message(chat_id=update.effective_chat.id, text="已关闭直链")
        else:
            await context.bot.send_message(chat_id=update.effective_chat.id, text="请在命令后加上1或0(1=开，0=关)")
        with open('config.yaml', 'w') as f:
            yaml.safe_dump(config, f)
        global z_url
        z_url = config['z_url']

## 配置备份
async def bc(update, context):
    if await admin_yz(update, context):
        bc_list = ['setting', 'user', 'storage', 'meta']
        bc_dic = {'settings': '', 'users': 'users', 'storages': '', 'metas': ''}
        for i in range(len(bc_list)):
            bc_url = alist_host + '/api/admin/' + bc_list[i] + '/list'
            bc_header = {"Authorization": alsit_token, 'accept':'application/json'}
            bc_post = requests.get(bc_url,  headers=bc_header)
            data = json.loads(bc_post.text)

            if i == 0:
                bc_dic[bc_list[i] + 's'] = data['data']
            else:
                bc_dic[bc_list[i] + 's'] = data['data']['content']

        data = json.dumps(bc_dic, indent=4,ensure_ascii=False) ## 格式化json
        now = datetime.datetime.now()
        current_time = now.strftime("%Y_%m_%d_%H_%M_%S") ## 获取当前时间
        bc_file_name = ('alist_bot_backup_' + current_time + '.json')
        with open(bc_file_name, 'w', encoding='utf-8') as b:
            b.write(str(data))
        await context.bot.send_document(chat_id=update.effective_chat.id, document=bc_file_name, caption='#Alist配置备份')
        os.remove(bc_file_name)

def main():
    application = ApplicationBuilder().token(bot_api).build()

    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('sl', sl))
    application.add_handler(CommandHandler('zl', zl))
    application.add_handler(CommandHandler('bc', bc))
    application.add_handler(CommandHandler('cf', cf))
    application.add_handler(CommandHandler('menu', menu))

    application.add_handler(search.s_handler)
    application.add_handler(storage.vs_handler)
    application.add_handler(storage.cs_handler)
    application.add_handler(storage.ns_handler)
    application.add_handler(storage.button_get_storage_handler)

    application.run_polling()


if __name__ == '__main__':
    main()


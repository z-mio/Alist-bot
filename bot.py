# -*- coding: UTF-8 -*-

import json
import logging
import math
import yaml

import requests
import telegram
from telegram import Update
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


async def sl(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text_caps = update.message.text
    sl_str = text_caps.strip("/sl @")

    if user_id in admin:
        if sl_str.isdigit():
            config['per_page'] = int(sl_str)
            with open('config.yaml', 'w') as f:
                yaml.dump(config, f)
            await context.bot.send_message(chat_id=update.effective_chat.id, text="已修改搜索结果数量为：" + sl_str)
        else:
            await context.bot.send_message(chat_id=update.effective_chat.id, text="请输入正整数")
        global per_page
        per_page = config['per_page']
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="该命令仅管理员可用")


async def zl(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text_caps = update.message.text
    zl_str = text_caps.strip("/zl @")

    if user_id in admin:
        if zl_str == "1":
            config['z_url'] = True
            await context.bot.send_message(chat_id=update.effective_chat.id, text="已开启直链")
        elif zl_str == "0":
            config['z_url'] = False
            await context.bot.send_message(chat_id=update.effective_chat.id, text="已关闭直链")
        else:
            await context.bot.send_message(chat_id=update.effective_chat.id, text="请输入1或0(1=开，0=关)")
        with open('config.yaml', 'w') as f:
            yaml.safe_dump(config, f)
        global z_url
        z_url = config['z_url']
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="该命令仅管理员可用")


def main():
    application = ApplicationBuilder().token(bot_api).build()

    application.add_handler(CommandHandler('start', start))
    application.add_handler(search.s_handler)
    application.add_handler(CommandHandler('sl', sl))
    application.add_handler(CommandHandler('zl', zl))
    application.add_handler(storage.vs_handler)


    application.add_handler(storage.button_callback_handler)


    application.run_polling()

if __name__ == '__main__':
    main()
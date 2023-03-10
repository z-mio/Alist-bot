# -*- coding: UTF-8 -*-

import json
import logging
import math
import yaml

import requests
import telegram
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

with open("config.yaml", 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

admin = config['admin']  ## 管理员 id
alist_host = config['alist_host']  ## alist ip:port
alist_web = config['alist_web']  ## 你的alist域名
alsit_token = config['alsit_token']  ## alist token
bot_key = config['bot_key']  ## bot的key，用 @BotFather 获取
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


async def s(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text_caps = update.message.text
    s_str = text_caps.strip("/s @")

    if s_str == "":
        await context.bot.send_message(chat_id=update.effective_chat.id, text="请输入文件名")
    elif s_str == "ybyx_bot":
        await context.bot.send_message(chat_id=update.effective_chat.id, text="请输入文件名")
    else:
        ## 搜索文件
        alist_url = alist_host + '/api/fs/search'
        alist_header = {"Authorization": alsit_token,
                        'Cache-Control': 'no-cache'
                        }
        alist_body = {"parent": "/",
                      "keywords": s_str,
                      "page": 1,
                      "per_page": per_page
                      }

        alist_post = requests.post(alist_url, json=alist_body, headers=alist_header)

        data = json.loads(alist_post.text)

        if not data['data']['content']:
            await context.bot.send_message(chat_id=update.effective_chat.id, text="未搜索到文件，换个关键词试试吧")
        else:
            search1 = await context.bot.send_message(chat_id=update.effective_chat.id, text="搜索中...")

            name_list = []  ##文件/文件夹名字
            parent_list = []  ##文件/文件夹路径
            size_list = []  ##文件大小
            is_dir_list = []  ##是否是文件夹
            jishu = 0
            tg_text = ""

            for item in data['data']['content']:

                name_list.append(item['name'])
                parent_list.append(item['parent'])
                size_list.append(item['size'])
                is_dir_list.append(item['is_dir'])

                file_name = name_list[jishu]
                path = parent_list[jishu]
                file_size = size_list[jishu]
                folder = is_dir_list[jishu]

                file_url = alist_web + path + "/" + file_name

                ## 获取文件直链
                if z_url == True:

                    z_alist_url = alist_host + '/api/fs/get'
                    z_alist_header = {"Authorization": alsit_token,
                                      'Cache-Control': 'no-cache'
                                      }

                    z_alist_body = {"path": path + "/" + file_name}
                    z_alist_post = requests.post(z_alist_url, json=z_alist_body, headers=z_alist_header)

                    z_data = json.loads(z_alist_post.text)
                    z_file_url = [z_data['data']['raw_url']]
                else:
                    z_file_url = []

                if folder:
                    folder_tg_text = "📁文件夹："
                    z_folder = ""
                    z_folder_f = ""
                    z_url_link = ''
                elif z_url == True:
                    folder_tg_text = "📄文件："
                    z_folder = "直接下载"
                    z_folder_f = "|"
                    z_url_link = f'''<a href="{z_file_url[0]}">{z_folder}</a>'''
                else:
                    folder_tg_text = "📄文件："
                    z_folder_f = ""
                    z_url_link = ''

                #########################
                tg_textt = f'''{jishu + 1}.{folder_tg_text}{file_name}
<a href="{file_url}">🌐打开网站</a>|{z_url_link}{z_folder_f}大小: {pybyte(file_size)}

'''
                #########################
                tg_text += tg_textt
                jishu += 1
                await context.bot.edit_message_text(chat_id=update.effective_chat.id,
                                                    message_id=search1.message_id,
                                                    text=tg_text,
                                                    parse_mode=telegram.constants.ParseMode.HTML,
                                                    disable_web_page_preview=True
                                                    )


if __name__ == '__main__':
    application = ApplicationBuilder().token(bot_key).build()

    start_handler = CommandHandler('start', start)
    s_handler = CommandHandler('s', s)
    sl_handler = CommandHandler('sl', sl)
    zl_handler = CommandHandler('zl', zl)

    application.add_handler(start_handler)
    application.add_handler(s_handler)
    application.add_handler(sl_handler)
    application.add_handler(zl_handler)

    application.run_polling()

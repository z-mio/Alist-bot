# -*- coding: UTF-8 -*-
import json

import math
import telegram
from telegram.ext import CommandHandler

from alist_api import search, fs_get
from bot import admin_yz
from config.config import config, per_page, alist_host, alist_token, z_url, alist_web, write_config


# 设置搜索结果数量
@admin_yz
async def sl(update, context):
    text_caps = update.message.text
    sl_str = text_caps.strip("/sl @")
    if sl_str.isdigit():
        config['search']['per_page'] = int(sl_str)
        write_config("config/config.yaml", config)
        await context.bot.send_message(
            chat_id=update.effective_chat.id, text=f"已修改搜索结果数量为：{sl_str}"
        )
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="请输入正整数")


# 设置直链
@admin_yz
async def zl(update, context):
    text_caps = update.message.text
    zl_str = text_caps.strip("/zl @")
    if zl_str == "1":
        config['search']['z_url'] = True
        await context.bot.send_message(chat_id=update.effective_chat.id, text="已开启直链")
    elif zl_str == "0":
        config['search']['z_url'] = False
        await context.bot.send_message(chat_id=update.effective_chat.id, text="已关闭直链")
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="请在命令后加上1或0(1=开，0=关)")
    write_config("config/config.yaml", config)


# 搜索
async def s(update, context):
    text_caps = update.message.text
    s_str = text_caps.strip("/s @")

    if s_str == "" or "_bot" in s_str:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="请加上文件名，例：/s 巧克力")
    else:
        # 搜索文件
        alist_post = search(s_str, per_page(), alist_host, alist_token)

        alist_post_json = json.loads(alist_post.text)

        if not alist_post_json['data']['content']:
            await context.bot.send_message(chat_id=update.effective_chat.id, text="未搜索到文件，换个关键词试试吧")
        else:
            search1 = await context.bot.send_message(chat_id=update.effective_chat.id, text="搜索中...")

            name_list = []  # 文件/文件夹名字
            parent_list = []  # 文件/文件夹路径
            size_list = []  # 文件大小
            is_dir_list = []  # 是否是文件夹
            jishu = 0
            tg_text = ""

            for item in alist_post_json['data']['content']:

                name_list.append(item['name'])
                parent_list.append(item['parent'])
                size_list.append(item['size'])
                is_dir_list.append(item['is_dir'])

                file_name = name_list[jishu]
                path = parent_list[jishu]
                file_size = size_list[jishu]
                folder = is_dir_list[jishu]

                file_url = alist_web + path + "/" + file_name

                # 获取文件直链
                if z_url():
                    z_alist_path = {"path": f"{path}/{file_name}"}
                    z_alist_post = fs_get(z_alist_path, alist_host, alist_token)  # 获取文件下载信息
                    z_data = json.loads(z_alist_post.text)
                    z_file_url = [z_data['data']['raw_url']]
                else:
                    z_file_url = []

                if folder:
                    folder_tg_text = "📁文件夹："
                    z_folder_f = ""
                    z_url_link = ''
                elif z_url():
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


# 字节数转文件大小
__all__ = ['pybyte']


def pybyte(size, dot=2):
    size = float(size)
    # 位 比特 bit
    if 0 <= size < 1:
        human_size = f'{str(round(size / 0.125, dot))}b'
    elif 1 <= size < 1024:
        human_size = f'{str(round(size, dot))}B'
    elif math.pow(1024, 1) <= size < math.pow(1024, 2):
        human_size = f'{str(round(size / math.pow(1024, 1), dot))}KB'
    elif math.pow(1024, 2) <= size < math.pow(1024, 3):
        human_size = f'{str(round(size / math.pow(1024, 2), dot))}MB'
    elif math.pow(1024, 3) <= size < math.pow(1024, 4):
        human_size = f'{str(round(size / math.pow(1024, 3), dot))}GB'
    elif math.pow(1024, 4) <= size < math.pow(1024, 5):
        human_size = f'{str(round(size / math.pow(1024, 4), dot))}TB'
    else:
        raise ValueError(
            f'{pybyte.__name__}() takes number than or equal to 0, but less than 0 given.'
        )
    return human_size


s_handler = CommandHandler('s', s)
sl_handler = CommandHandler('sl', sl)
zl_handler = CommandHandler('zl', zl)

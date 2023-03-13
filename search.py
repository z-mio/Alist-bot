# -*- coding: UTF-8 -*-
import telegram
import requests
import json

from telegram.ext import CommandHandler



## 搜索
async def s(update, context):
    from bot import alist_host, alist_web, alsit_token, per_page, z_url, pybyte

    text_caps = update.message.text
    s_str = text_caps.strip("/s @")

    if s_str == "" or "_bot" in s_str:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="请输入文件名")
    else:
        ## 搜索文件
        alist_url = alist_host + '/api/fs/search'
        alist_header = {"Authorization": alsit_token,}
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

s_handler = CommandHandler('s', s)
# -*- coding: UTF-8 -*-
import urllib.parse

from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, CallbackQuery

from api.alist_api import search, fs_get
from config.config import config, per_page, z_url, alist_web, write_config
from tool.utils import is_admin
from tool.utils import pybyte


@Client.on_message(filters.command('sl') & is_admin)
async def sl(_, message: Message):
    sl_str = ' '.join(message.command[1:])
    if sl_str.isdigit():
        config['bot']['search']['per_page'] = int(sl_str)
        write_config("config/config.yaml", config)
        await message.reply(f"已修改搜索结果数量为：{sl_str}")
    else:
        await message.reply("请输入正整数")


# 设置直链
@Client.on_message(filters.command('zl') & is_admin)
async def zl(_, message: Message):
    zl_str = ' '.join(message.command[1:])
    if zl_str == "1":
        config['bot']['search']['z_url'] = True
        await message.reply("已开启直链")
    elif zl_str == "0":
        config['bot']['search']['z_url'] = False
        await message.reply("已关闭直链")
    else:
        await message.reply("请在命令后加上1或0(1=开，0=关)")
    write_config("config/config.yaml", config)


chat_id_message = {}


# 搜索
@Client.on_message(filters.command('s'))
async def s(_, message: Message):
    s_str = ' '.join(message.command[1:])
    if not s_str or "_bot" in s_str:
        await message.reply("请加上文件名，例：/s 巧克力")
    else:
        # 搜索文件
        alist_post = await search(s_str)
        alist_post_json = alist_post.json()

        if not alist_post_json['data']['content']:
            await message.reply("未搜索到文件，换个关键词试试吧")
        else:
            result_deduplication = [
                dict(t)
                for t in {
                    tuple(d.items())
                    for d in alist_post_json['data']['content']
                }
            ]
            search1 = await message.reply("搜索中...")
            # 文件/文件夹名字 文件/文件夹路径 文件大小 是否是文件夹
            name_list = parent_list = size_list = is_dir_list = []
            textx = []
            for count, item in enumerate(result_deduplication):
                name_list.append(item['name'])
                parent_list.append(item['parent'])
                size_list.append(item['size'])
                is_dir_list.append(item['is_dir'])
                file_name, path, file_size, folder = item['name'], item['parent'], item['size'], item['is_dir']

                file_url = alist_web + path + "/" + file_name

                # 获取文件直链
                if folder:
                    folder_tg_text = "📁文件夹："
                    z_folder_f = ''
                    z_url_link = ''
                elif z_url():
                    folder_tg_text = "📄文件："
                    z_folder = "直接下载"
                    z_folder_f = "|"
                    r = await fs_get(f"{path}/{file_name}")
                    z_url_link = \
                        f'<a href="{r.json()["data"]["raw_url"]}">{z_folder}</a>'
                else:
                    folder_tg_text = "📄文件："
                    z_folder_f = ''
                    z_url_link = ''

                ########################
                file_url = urllib.parse.quote(file_url, safe=':/')
                text = f'''{count + 1}.{folder_tg_text}<code>{file_name}</code>
<a href="{file_url}">🌐打开网站</a>|{z_url_link}{z_folder_f}大小: {pybyte(file_size)}

'''
                textx += [text]
            chat_id = message.chat.id
            chat_message = f'{chat_id}|{message.id + 1}'
            chat_id_message[chat_message] = {
                'page': 1,
                'pointer': 0,
                'text': textx,
            }
            page_count = (len(chat_id_message[chat_message]['text']) + per_page() - 1) // per_page()
            search_button = [
                [
                    InlineKeyboardButton(f'1/{page_count}', callback_data='search_pages')
                ],
                [
                    InlineKeyboardButton('⬆️上一页', callback_data='search_previous_page'),
                    InlineKeyboardButton('⬇️下一页', callback_data='search_next_page')
                ],

            ]
            await search1.edit(text=''.join(chat_id_message[chat_message]['text'][:per_page()]),
                               reply_markup=InlineKeyboardMarkup(search_button),
                               disable_web_page_preview=True
                               )


# 翻页
@Client.on_callback_query(filters.regex(r'^search'))
async def search_button_callback(_, query: CallbackQuery):
    data = query.data
    chat_message_id = f'{query.message.chat.id}|{query.message.id}'

    async def turn():
        pointer = chat_id_message[chat_message_id]['pointer']
        text = chat_id_message[chat_message_id]['text'][pointer:pointer + per_page()]

        search_button = [
            [
                InlineKeyboardButton(f"{chat_id_message[chat_message_id]['page']}/{page_count}",
                                     callback_data='search_pages')
            ],
            [
                InlineKeyboardButton('⬆️上一页', callback_data='search_previous_page'),
                InlineKeyboardButton('⬇️下一页', callback_data='search_next_page')
            ],
        ]
        await query.message.edit(text=''.join(text),
                                 reply_markup=InlineKeyboardMarkup(search_button),
                                 disable_web_page_preview=True
                                 )

    page = chat_id_message[chat_message_id]['page']
    page_count = (len(chat_id_message[chat_message_id]['text']) + per_page() - 1) // per_page()
    if data == 'search_next_page':
        if page < page_count:
            chat_id_message[chat_message_id]['pointer'] += per_page()  # 指针每次加5，表示下一页
            chat_id_message[chat_message_id]['page'] += 1
            await turn()
    elif data == 'search_previous_page':
        if page > 1:
            chat_id_message[chat_message_id]['page'] -= 1
            chat_id_message[chat_message_id]['pointer'] -= per_page()  # 指针每次减5，表示上一页
            await turn()

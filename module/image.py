# -*- coding: UTF-8 -*-
import datetime
import json
import os
import random

from pyrogram import filters
from pyrogram.handlers import MessageHandler

from api.alist_api import upload, fs_get, refresh_list
from bot import admin_yz
from config.config import image_upload_path, image_save_path, alist_web, image_config, write_config


@admin_yz
async def single_mode(client, message):
    # 检测是否添加了说明
    if caption := message.caption:
        if ":" in caption:
            image_config['image_save_path'] = str(caption.split(':')[0])
            image_config['image_upload_path'] = str(caption.split(':')[1])
        elif "：" in caption:
            image_config['image_save_path'] = str(caption.split('：')[0])
            image_config['image_upload_path'] = str(caption.split('：')[1])
        elif caption == '关闭':
            image_config['image_upload_path'] = None
        else:
            image_config['image_upload_path'] = str(caption)
        write_config("config/image_cfg.yaml", image_config)
    # 开始运行
    if image_config['image_upload_path']:
        now = datetime.datetime.now()
        current_time = now.strftime("%Y_%m_%d_%H_%M_%S")  # 获取当前时间
        file_name = f'{current_time}_{random.randint(1, 1000)}'
        # 生成文件名
        if message.photo:  # 压缩发送的图片
            file_name = f'{file_name}.jpg'  # 压缩的图片默认为.jpg

        elif message.document.mime_type.startswith('image/'):  # 未压缩的图片文件
            ext = os.path.splitext(message.document.file_name)[1]  # 获取文件扩展名
            file_name = f'{file_name}{ext}'

        # 本地路径+文件名
        file_name_path = f'{image_save_path()}/{file_name}'
        # 下载图片
        msg = await message.reply_text(text='📥下载图片中...', quote=True, disable_web_page_preview=False)
        await message.download(file_name=file_name_path, block=True)

        # 上传到alist
        await client.edit_message_text(chat_id=msg.chat.id,
                                       message_id=msg.id,
                                       text='📤上传图片中...',
                                       disable_web_page_preview=False)

        upload(file_name_path, image_upload_path(), file_name)

        # 删除图片
        os.remove(file_name_path)

        # 刷新列表
        await client.edit_message_text(chat_id=msg.chat.id,
                                       message_id=msg.id,
                                       text='🔄刷新列表中...',
                                       disable_web_page_preview=False)
        refresh_list(image_upload_path())

        # 获取文件信息
        await client.edit_message_text(chat_id=msg.chat.id,
                                       message_id=msg.id,
                                       text='⏳获取链接中...',
                                       disable_web_page_preview=False)
        get_url = fs_get(f'{image_upload_path()}/{file_name}')
        get_url_json = json.loads(get_url.text)
        image_url = get_url_json['data']['raw_url']  # 直链

        text = f'''
图片名称：<code>{file_name}</code>
图片链接：<a href="{alist_web}/{image_upload_path()}/{file_name}">打开图片</a>
图片直链：<a href="{image_url}">下载图片</a>
Markdown：
<code>![{file_name}]({image_url})</code>
'''
        # HTML格式，如果需要可以加到上面
        # HTML：
        # <code>&lt;img src="{image_url}" alt="{file_name}" /&gt;</code>

        # 发送信息
        await client.edit_message_text(chat_id=msg.chat.id, message_id=msg.id, text=text)
    else:
        text = '''
未开启图床功能，请设置上传路径来开启图床

怎么设置？

先选择一张图片，然后在”添加说明“处填写路径
格式：
1、涩图/图床
2、downloads:涩图/图床
3、关闭

第一种只写一个路径，就是设置上传路径
第二种写两个路径，用冒号隔开，冒号左边为下载路径，右边为上传路径
输入”关闭“关闭图床功能

默认下载路径为：bot根目录/downloads

设置后会自动保存，不用每次都设置
'''
        await client.send_message(chat_id=message.chat.id, text=text)


image_handlers = [
    MessageHandler(single_mode, (filters.photo | filters.document) & filters.private)
]

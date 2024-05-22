# -*- coding: UTF-8 -*-
import asyncio
import datetime
import os
import random
import time
from concurrent.futures import ThreadPoolExecutor

from pyrogram import filters, Client
from pyrogram.types import Message

from api.alist.alist_api import alist
from config.config import img_cfg, DOWNLOADS_PATH, bot_cfg
from tools.filters import is_admin

# 4线程
thread_pool = ThreadPoolExecutor(max_workers=4)


async def download_upload(message: Message):
    now = datetime.datetime.now()
    current_time = now.strftime("%Y_%m_%d_%H_%M_%S")  # 获取当前时间
    file_name = f"{current_time}_{random.randint(1, 1000)}"
    # 生成文件名
    if message.photo:  # 压缩发送的图片
        file_name = f"{file_name}.jpg"  # 压缩的图片默认为.jpg

    elif message.document.mime_type.startswith("image/"):  # 未压缩的图片文件
        ext = os.path.splitext(message.document.file_name)[1]  # 获取文件扩展名
        file_name = f"{file_name}{ext}"

    # 本地路径+文件名
    file_name_path = DOWNLOADS_PATH.joinpath(file_name)

    # 下载图片
    time.sleep(random.uniform(0.01, 0.2))
    msg = await message.reply_text(
        text="📥下载图片中...", quote=True, disable_web_page_preview=False
    )
    await message.download(file_name=file_name_path)
    # 上传到alist
    await msg.edit(text="📤上传图片中...", disable_web_page_preview=False)
    time.sleep(random.uniform(0.01, 0.2))
    await alist.upload(file_name_path, img_cfg.image_upload_path, file_name)

    # 删除图片
    os.remove(file_name_path)

    # 刷新列表
    await msg.edit(text="🔄刷新列表中...", disable_web_page_preview=False)
    time.sleep(random.uniform(0.01, 0.2))
    await alist.fs_list(img_cfg.image_upload_path, 1)
    # 获取文件信息
    await msg.edit(text="⏳获取链接中...", disable_web_page_preview=False)
    time.sleep(random.uniform(0.01, 0.2))
    get_url = await alist.fs_get(f"{img_cfg.image_upload_path}/{file_name}")
    image_url = get_url.data.raw_url  # 直链

    text = f"""
图片名称：<code>{file_name}</code>
图片链接：<a href="{bot_cfg.alist_web}/{img_cfg.image_upload_path}/{file_name}">打开图片</a>
图片直链：<a href="{image_url}">下载图片</a>
Markdown：
`![{file_name}]({image_url})`
"""
    # HTML：
    # <code>&lt;img src="{image_url}" alt="{file_name}" /&gt;</code>

    await msg.edit(text=text, disable_web_page_preview=True)


@Client.on_message((filters.photo | filters.document) & filters.private & is_admin)
async def single_mode(_, message: Message):
    # 检测是否添加了说明
    if caption := message.caption:
        img_cfg.image_upload_path = None if caption == "关闭" else str(caption)
    # 开始运行
    if img_cfg.image_upload_path:
        # 添加任务到线程池
        # await download_upload(message)
        thread_pool.submit(asyncio.run, download_upload(message))
    else:
        text = """
未开启图床功能，请设置上传路径来开启图床

先选择一张图片，然后在”添加说明“处填写上传路径
格式: `/图床/测试`
输入 `关闭` 关闭图床功能
设置后会自动保存，不用每次都设置
"""
        await message.reply(text=text)

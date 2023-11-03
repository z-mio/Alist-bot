# -*- coding: UTF-8 -*-
import json
import os
import random
import urllib.parse

from pyrogram import filters, Client
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, CallbackQuery

from api.alist_api import refresh_list
from config.config import chat_data, roll_disable, path, write_config, roll_cfg, alist_web
from tool.random_kaomoji import random_kaomoji
from tool.utils import is_admin
from tool.utils import pybyte

return_button = [
    InlineKeyboardButton('↩️返回菜单', callback_data='sr_return'),
    InlineKeyboardButton('❌关闭菜单', callback_data='sr_close')
]


def btn():
    return [
        [
            InlineKeyboardButton('🛠修改配置', callback_data='edit_roll'),
            InlineKeyboardButton(
                '✅随机推荐' if roll_disable() else '❎随机推荐',
                callback_data='roll_off' if roll_disable() else 'roll_on',
            ),
        ],
        [
            InlineKeyboardButton('❌关闭菜单', callback_data='sr_close')
        ]
    ]


# 随机推荐菜单
@Client.on_message(filters.command('sr') & filters.private & is_admin)
async def sr_menu(_, message: Message):
    chat_data['sr_menu'] = await message.reply(text=random_kaomoji(), reply_markup=InlineKeyboardMarkup(btn()))


# 随机推荐
@Client.on_message(filters.command('roll'))
async def roll(_, message: Message):
    if not roll_disable():
        return
    roll_str = ' '.join(message.command[1:])
    if roll_str.replace("？", "?") == '?':
        t = "\n".join(list(path().keys()))
        text = f'已添加的关键词：\n<code>{t}</code>'
        return await message.reply(text)
    if path():
        names, sizes, url = await generate(key=roll_str or '')
        text = f"""
{random_kaomoji()}：<a href="{url}">{names}</a>
{f'{random_kaomoji()}：{sizes}' if sizes != '0.0b' else ''}
"""
        await message.reply(text, disable_web_page_preview=True)
    else:
        await message.reply('请先添加路径')


# 监听普通消息
async def echo_roll(message: Message):
    if 'edit_roll' in chat_data and chat_data['edit_roll']:
        await change_setting(message)


# 菜单按钮回调
@Client.on_callback_query(filters.regex('^sr_'))
async def menu(query: CallbackQuery):
    data = query.data
    if data == 'sr_return':
        chat_data['edit_roll'] = False
        await chat_data['sr_menu'].edit(text=random_kaomoji(), reply_markup=InlineKeyboardMarkup(btn()))
    elif data == 'sr_close':
        chat_data['edit_roll'] = False
        await chat_data['sr_menu'].edit(text=random_kaomoji())


# 修改配置按钮回调
@Client.on_callback_query(filters.regex('edit_roll'))
async def edit_roll(_, query: CallbackQuery):
    j = json.dumps(path(), indent=4, ensure_ascii=False)
    text = f"""
<code>{j}</code>


修改后发送，格式为json
一个关键词可以包含多个路径，使用列表格式
""" if j != 'null' else """
<code>
{
    "关键词": "路径",
    "slg": "/slg",
    "gal": [
        "/gal",
        "/123"
    ]
}
</code>

修改后发送，格式为json
一个关键词可以包含多个路径，使用列表格式
"""
    await query.message.edit(text=text, reply_markup=InlineKeyboardMarkup([return_button]))
    chat_data['edit_roll'] = True


# 开关回调
@Client.on_callback_query(filters.regex('^roll_'))
async def roll_of(_, message):
    query = message.data
    roll_cfg['roll_disable'] = query != 'roll_off'
    write_config("config/roll_cfg.yaml", roll_cfg)
    await chat_data['sr_menu'].edit(text=random_kaomoji(), reply_markup=InlineKeyboardMarkup(btn()))


# 写入配置
async def change_setting(message: Message):
    msg = message.text
    try:
        roll_cfg['path'] = json.loads(msg)
    except Exception as e:
        await message.reply(text=f'错误：{str(e)}\n\n请修改后重新发送')
    else:
        await message.delete()
        chat_data['edit_roll'] = False
        write_config("config/roll_cfg.yaml", roll_cfg)
        await chat_data['sr_menu'].edit(text='修改成功', reply_markup=InlineKeyboardMarkup(btn()))


async def generate(key=''):
    # 使用os.urandom生成随机字节串作为种子
    random.seed(os.urandom(32))

    values_list = list(path().values()) if key == '' else path()[key]
    r_path = get_random_value(values_list)
    r = await refresh_list(r_path)
    data = r.json()
    content = data["data"]["content"]

    selected_item = random.choice(content)
    name = selected_item["name"]
    size = selected_item["size"]
    get_path = f'{r_path}/{name}'

    url = alist_web + get_path
    url = urllib.parse.quote(url, safe=':/')
    return name, pybyte(size), url


# 递归列表，返回随机值
def get_random_value(data):
    if not isinstance(data, list):
        return data
    random_value = random.choice(data)
    return (
        get_random_value(random_value)
        if isinstance(random_value, list)
        else random_value
    )

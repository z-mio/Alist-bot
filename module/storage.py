# -*- coding: UTF-8 -*-
import concurrent.futures
import datetime
import json
import logging
import re
from typing import Union

import requests
from pyrogram import filters, Client
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery, Message

from api.alist_api import (storage_update, storage_create, storage_list, storage_get, storage_delete, storage_disable,
                           storage_enable, get_driver)
from config.config import storage_cfg, write_config, chat_data
from tool.utils import is_admin
from tool.utils import translate_key

mount_path = []  # 存储路径
disabled = []  # 存储是否禁用
driver_id = []  # 存储id
ns_button_list = []  # 支持添加的存储的按钮
button_list = []
common_dict = {}  # 新建存储——新建存储的json模板

with open('config/cn_dict.json', 'r', encoding='utf-8') as c:
    text_dict = json.load(c)
thread_pool = concurrent.futures.ThreadPoolExecutor(max_workers=20)
#####################################################################################
#####################################################################################
# 返回菜单
return_button = [
    InlineKeyboardButton('↩️返回存储管理', callback_data='st_return'),
    InlineKeyboardButton('❌关闭菜单', callback_data='st_close'),
]

st_button = [
    [
        InlineKeyboardButton('⬆️自动排序', callback_data='auto_sorting')
    ],
    [
        InlineKeyboardButton('⏯开关存储', callback_data='st_vs'),
        InlineKeyboardButton('📋复制存储', callback_data='st_cs')
    ],
    [
        InlineKeyboardButton('🆕新建存储', callback_data='st_ns'),
        InlineKeyboardButton('🗑️删除存储', callback_data='st_ds')
    ],
    [
        InlineKeyboardButton('📋复制存储配置', callback_data='st_storage_copy_list'),
        InlineKeyboardButton('🛠️修改默认配置', callback_data='st_storage_amend')
    ],
    [
        InlineKeyboardButton('❌关闭菜单', callback_data='st_close')
    ]
]

vs_all_button = [
    InlineKeyboardButton('✅开启全部存储', callback_data='vs_onall'),
    InlineKeyboardButton('❌关闭全部存储', callback_data='vs_offall')

]


#####################################################################################
# 按钮回调
#####################################################################################
# 返回存储管理菜单
@Client.on_callback_query(filters.regex(r'^st_return$'))
async def st_return_callback(_, __):
    chat_data["st_storage_cfg_amend"] = False
    await st_return()


# 添加单个存储_返回存储管理菜单
@Client.on_callback_query(filters.regex('^ns_re_menu$'))
async def ns_re_menu_callback(client: Client, __):
    await ns_mode_a_delete(client)
    await st_return()


# 添加单个存储_返回存储管理菜单
@Client.on_callback_query(filters.regex('^ns_re_new_b_menu$'))
async def ns_re_new_b_menu_callback(client: Client, __):
    await ns_mode_b_delete(client)
    await st_return()


# 关闭存储管理菜单
@Client.on_callback_query(filters.regex(r'^st_close$'))
async def st_close(_, __):
    await storage_menu_button.edit('已退出『存储管理』')


# 发送 开关存储 按钮列表
@Client.on_callback_query(filters.regex(r'^st_vs$'))
async def vs(_, __):
    await get_storage(callback_data_pr='vs')
    button_list.insert(1, vs_all_button)
    button_list.insert(-1, vs_all_button)
    await storage_menu_button.edit(text='点击开启/关闭存储\n存储列表：', reply_markup=InlineKeyboardMarkup(button_list))


# 发送 复制存储 按钮列表
@Client.on_callback_query(filters.regex(r'^st_cs$'))
async def cs(_, __):
    await get_storage(callback_data_pr='cs')
    await storage_menu_button.edit(text='点击复制存储\n存储列表：', reply_markup=InlineKeyboardMarkup(button_list))


# 发送 删除存储 按钮列表
@Client.on_callback_query(filters.regex(r'^st_ds$'))
async def ds(_, __):
    await get_storage(callback_data_pr='ds')
    await storage_menu_button.edit(text='点击删除存储\n存储列表：', reply_markup=InlineKeyboardMarkup(button_list))


# 返回可添加存储列表
@Client.on_callback_query(filters.regex('^ns_re_list$'))
async def ns_re_list_callback(_, __):
    chat_data["ns_a"] = False
    await ns(_, __)


# 返回添加存储列表
@Client.on_callback_query(filters.regex('^ns_re_list_mode_b$'))
async def ns_re_list_mode_b_callback(client: Client, _):
    chat_data["ns_b"] = False
    await ns_re_list_mode_b(client)
    await ns(_, _)


# 发送 添加存储 按钮列表
@Client.on_callback_query(filters.regex(r'^st_ns$'))
async def ns(_, __):
    r = await get_driver()
    stj_key = list(r.json()['data'].keys())
    ns_storage_list = translate_key(stj_key, text_dict['driver'])  # 支持添加的存储列表
    ns_button_list.clear()

    for storage_list_js in range(len(ns_storage_list)):
        button_ns = [
            InlineKeyboardButton(
                ns_storage_list[storage_list_js],
                callback_data=f'ns{str(stj_key[storage_list_js])}',
            )
        ]
        ns_button_list.append(button_ns)

    ns_button_list.insert(0, return_button)  # 列表开头添加返回和关闭菜单按钮
    ns_button_list.append(return_button)  # 列表结尾添加返回和关闭菜单按钮

    await storage_menu_button.edit(text='支持添加的存储：', reply_markup=InlineKeyboardMarkup(ns_button_list))


# 发送 复制存储配置 按钮列表
@Client.on_callback_query(filters.regex(r'^st_storage_copy_list$'))
async def st_storage_copy_list(_, __):
    await get_storage(callback_data_pr='st_storage_copy_cfg')
    await storage_menu_button.edit(text='点击复制存储配置：', reply_markup=InlineKeyboardMarkup(button_list))


# 取消修改默认配置
@Client.on_callback_query(filters.regex(r'^st_storage_cfg_off$'))
async def sst_storage_cfg_off_callback(_, __):
    chat_data["st_storage_cfg_amend"] = False
    await st_storage_amend('', '')


#####################################################################################
#####################################################################################

# 检测普通消息
async def echo_storage(client: Client, message: Message):
    if "ns_a" in chat_data and chat_data["ns_a"]:
        chat_data["ns_a"] = False
        await ns_new_a(client, message)
        chat_data['chat_id'] = message.chat.id
        chat_data['message_id'] = message.id
    elif "ns_b" in chat_data and chat_data["ns_b"]:
        await ns_new_b(client, message)
        chat_data['chat_id'] = message.chat.id
        chat_data['message_id'] = message.id
    elif "st_storage_cfg_amend" in chat_data and chat_data["st_storage_cfg_amend"]:
        chat_data["st_storage_cfg_amend"] = False
        chat_data['chat_id'] = message.chat.id
        chat_data['message_id'] = message.id
        await st_storage_cfg_amend(client, message)
    return


async def st_aaa():
    try:
        sl = await storage_list()
    except requests.exceptions.ReadTimeout:
        logging.error('连接Alist超时，请检查网站状态')
    else:
        sl_json = sl.json()
        zcc = len(sl_json['data']['content'])
        content_list = sl_json["data"]["content"]
        jysl = sum(bool(item["disabled"])
                   for item in content_list)
        qysl = zcc - jysl
        return f'存储数量：{zcc}\n启用：{qysl}\n禁用：{jysl}'


# 存储管理菜单
@Client.on_message(filters.command('st') & filters.private & is_admin)
async def st(_, message: Message):
    global storage_menu_button
    storage_menu_button = await message.reply(text=await st_aaa(), reply_markup=InlineKeyboardMarkup(st_button))


# 返回存储管理菜单
async def st_return():
    await storage_menu_button.edit(text=await st_aaa(), reply_markup=InlineKeyboardMarkup(st_button))


# 修改存储默认配置
@Client.on_callback_query(filters.regex(r'^st_storage_amend$'))
async def st_storage_amend(_, __):
    t = translate_key(translate_key(storage_cfg()['storage'], text_dict['common']), text_dict['additional'])
    t = json.dumps(t, indent=4, ensure_ascii=False)

    button = [
        [
            InlineKeyboardButton('🔧修改配置', callback_data='st_storage_cfg_amend')
        ],
        [
            InlineKeyboardButton('↩️返回存储管理', callback_data='st_return')
        ]
    ]

    await storage_menu_button.edit(text=f'当前配置：\n<code>{t}</code>', reply_markup=InlineKeyboardMarkup(button))


# 修改存储默认配置_按钮回调
@Client.on_callback_query(filters.regex(r'^st_storage_cfg_amend$'))
async def st_storage_amend_callback(_, __):
    chat_data["st_storage_cfg_amend"] = True
    t = translate_key(translate_key(storage_cfg()['storage'], text_dict['common']), text_dict['additional'])
    t = json.dumps(t, indent=4, ensure_ascii=False)
    button = [
        [
            InlineKeyboardButton('❌取消修改', callback_data='st_storage_cfg_off')
        ],
        [
            InlineKeyboardButton('↩️返回存储管理', callback_data='st_return')
        ]
    ]
    text = f'''当前配置：
<code>{t}</code>

支持的选项：<a href="https://telegra.ph/驱动字典-03-20">点击查看</a>
先复制当前配置，修改后发送

格式（Json）：
1、每行前面要添加4个空格
2、除了最后一行，每行后面都要添加英文逗号“,”

'''
    await storage_menu_button.edit(text=text, reply_markup=InlineKeyboardMarkup(button),
                                   disable_web_page_preview=True)


#####################################################################################
# 运行
#####################################################################################


# 开启关闭存储
@Client.on_callback_query(filters.regex(r'^vs\d'))
async def vs_callback(_, query: CallbackQuery):
    bvj = int(query.data.strip("vs"))
    storage_id = driver_id[bvj]
    if disabled[bvj]:
        of_t = "✅已开启存储："
        await storage_enable(storage_id)
    else:
        of_t = "❌已关闭存储："
        await storage_disable(storage_id)
    await get_storage(callback_data_pr='vs')
    button_list.insert(1, vs_all_button)
    button_list.insert(-1, vs_all_button)
    await storage_menu_button.edit(text=of_t + mount_path[bvj], reply_markup=InlineKeyboardMarkup(button_list))


# 开启&关闭全部存储
@Client.on_callback_query(filters.regex(r'vs_offall|vs_onall'))
async def vs_on_off_all(_, query: CallbackQuery):
    bvj = query.data
    command = storage_enable if bvj == 'vs_onall' else storage_disable
    action = '开启中...' if bvj == 'vs_onall' else '关闭中...'
    await storage_menu_button.edit(text=action, reply_markup=InlineKeyboardMarkup(button_list))
    for i, is_disabled in enumerate(disabled):

        await command(driver_id[i])
        await get_storage(callback_data_pr='vs')
        button_list.insert(1, vs_all_button)
        button_list.insert(-1, vs_all_button)
        try:
            await storage_menu_button.edit(text=action, reply_markup=InlineKeyboardMarkup(button_list))
        except Exception as e:
            logging.info(e)
    await storage_menu_button.edit(text='完成！', reply_markup=InlineKeyboardMarkup(button_list))


# 复制存储
@Client.on_callback_query(filters.regex('^cs'))
async def cs_callback(_, query: CallbackQuery):
    bvj = int(query.data.strip("cs"))
    cs_storage = []
    cs_storage.clear()
    storage_id = str(driver_id[bvj])
    cs_alist_get = await storage_get(storage_id)  # 获取存储
    cs_json = cs_alist_get.json()
    cs_storage.append(cs_json['data'])  # 保存获取的存储
    del cs_storage[0]['id']  # 删除存储id
    now = datetime.datetime.now()
    current_time = now.strftime("%M%S")  # 获取当前时间

    cs_mount_path = cs_storage[0]['mount_path']
    cs_order = cs_storage[0]['order']
    if '.balance' not in cs_mount_path:  # 修改存储的mount_path
        cs_storage[0]['mount_path'] = f'{cs_mount_path}.balance{current_time}'
    else:
        cs_mount_path_text = re.sub('.balance.*', '', cs_mount_path)
        cs_storage[0]['mount_path'] = f'{cs_mount_path_text}.balance{current_time}'
    cs_storage[0]['order'] = cs_order + 1  # 基于当前配置的排序加1
    # cs_storage[0]['remark'] = f"{mount_path[bvj]} -> {cs_storage[0]['mount_path']}\n{cs_storage[0]['remark']}"

    body = cs_storage[0]
    await storage_create(body)  # 新建存储

    await get_storage(callback_data_pr='cs')
    await storage_menu_button.edit(text='已复制\n' + mount_path[bvj] + ' -> ' + cs_storage[0]['mount_path'], reply_markup=InlineKeyboardMarkup(button_list))


# 删除存储

@Client.on_callback_query(filters.regex('^ds'))
async def ds_callback(_, query: CallbackQuery):
    bvj = int(query.data.strip("ds"))
    await storage_delete(driver_id[bvj])
    st_id = mount_path[bvj]
    await get_storage(callback_data_pr='ds')
    await storage_menu_button.edit(text='🗑已删除存储：' + st_id, reply_markup=InlineKeyboardMarkup(button_list))


# 自动排序
@Client.on_callback_query(filters.regex(r'auto_sorting'))
async def auto_sorting(_, query: CallbackQuery):
    st = await storage_list()
    content: list = st.json()['data']['content']
    content.sort(key=lambda x: x['mount_path'])
    for i, v in enumerate(content):
        await query.message.edit_text(f'排序中|{i + 1}/{len(content)}')
        v['order'] = i
        thread_pool.submit(storage_update, v)
    await query.message.edit_text('排序完成！')


# 选择存储后，发送添加模式按钮
@Client.on_callback_query(filters.regex('^ns[^_]'))
async def ns_mode(_, query: CallbackQuery):  # 支持添加的存储列表
    bvj = str(query.data.lstrip("ns"))  # 发送选择模式菜单
    global name
    # stj_key = list(json.loads(get_driver().text)['data'].keys())
    name = bvj
    button = [
        [
            InlineKeyboardButton('☝️添加单个', callback_data=f'ns_a{str(bvj)}'),
            InlineKeyboardButton('🖐添加多个', callback_data=f'ns_b{str(bvj)}'),
        ],
        [InlineKeyboardButton('↩️返回存储列表', callback_data='ns_re_list')],
    ]
    await storage_menu_button.edit(text=f'<b>选择的存储：{name}</b>\n选择模式：', reply_markup=InlineKeyboardMarkup(button))


# 单个模式，发送模板后监听下一条消息
@Client.on_callback_query(filters.regex('ns_a'))
async def ns_mode_a(_, __):
    chat_data["ns_a"] = True
    text, common_dict_json = await storage_config(name)
    await storage_menu_button.edit(
        text=f'''<b>选择的存储：{name}</b>\n<code>{str(text)}</code>\n*为必填，如果有默认值则可不填\n请修改配置后发送''',
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('↩️返回存储列表', callback_data='ns_re_list')]])
    )


# 添加单个存储失败后重新添加
@Client.on_callback_query(filters.regex('^ns_re_ns_mode_a$'))
async def ns_re_ns_mode_a_callback(client: Client, __):
    chat_data["ns_a"] = True
    await ns_mode_a_delete(client)


# 删除用户和bot的信息
async def ns_mode_a_delete(client: Client):
    await client.delete_messages(chat_id=chat_data['chat_id_a'],
                                 message_ids=chat_data['message_id_a'])
    await client.delete_messages(chat_id=chat_data['chat_id'],
                                 message_ids=chat_data['message_id'])


# 多个模式，发送模板后监听下一条消息
@Client.on_callback_query(filters.regex('ns_b'))
async def ns_mode_b(_, query: CallbackQuery):
    ns_new_b_list.clear()
    message_text_list.clear()
    chat_data["ns_b"] = True
    text, common_dict_json = await storage_config(name)
    await storage_menu_button.edit(f'''<b>选择的存储：{name}</b>\n<code>{str(text)}</code>\n*为必填，如果有默认值则可不填\n请修改配置后发送''', )
    ns_mode_b_message_2 = await query.message.reply(text='请发送存储配置，注意挂载路径不要重复',
                                                    reply_markup=InlineKeyboardMarkup([
                                                        [
                                                            InlineKeyboardButton('↩️返回存储列表', callback_data='ns_re_list_mode_b')
                                                        ]
                                                    ]))

    chat_data['ns_mode_b_message_2_chat_id'] = ns_mode_b_message_2.chat.id
    chat_data['ns_mode_b_message_2_message_id'] = ns_mode_b_message_2.id


# 新建存储_单个模式
async def ns_new_a(_, message: Message):
    message_tj = await message.reply('新建存储中...')
    chat_data['chat_id_a'] = message_tj.chat.id
    chat_data['message_id_a'] = message_tj.id
    message_text = message.text
    st_cfg, user_cfg_code = await user_cfg(message_text)  # 解析用户发送的存储配置
    if user_cfg_code != 200:
        text = f'''添加失败！
——————————
请检查配置后重新发送：
<code>{message_text}</code>

错误Key：
<code>{str(user_cfg_code)}</code>
'''
        await message_tj.edit(text=text, reply_markup=InlineKeyboardMarkup(
            [
                [InlineKeyboardButton('🔄重新添加', callback_data='ns_re_ns_mode_a')],
                [InlineKeyboardButton('↩️︎返回存储管理', callback_data='ns_re_menu')]
            ]))
    else:
        ns_body = remove_quotes(st_cfg)
        ns_alist_post = await storage_create(ns_body)  # 新建存储
        ns_json = ns_alist_post.json()
        if ns_json['code'] == 200:
            await message_tj.edit(text=f'{name}添加成功！',
                                  reply_markup=InlineKeyboardMarkup([
                                      [InlineKeyboardButton('↩️返回存储管理', callback_data='ns_re_menu')]
                                  ]))
        elif ns_json['code'] == 500:
            storage_id = str(ns_json['data']['id'])
            ns_get_get = await storage_get(storage_id)  # 查询指定存储信息
            ns_get_json = ns_get_get.json()

            ns_update_json = ns_get_json['data']
            ns_update_post = await storage_update(ns_update_json)  # 更新存储
            ns_up_json = ns_update_post.json()

            if ns_up_json['code'] == 200:
                await message_tj.edit(text=f'{name}添加成功！',
                                      reply_markup=InlineKeyboardMarkup([
                                          [InlineKeyboardButton('↩️返回存储管理', callback_data='ns_re_menu')]
                                      ]))
            else:
                await message_tj.edit(text=name + '添加失败！\n——————————\n' + ns_update_post.text,
                                      reply_markup=InlineKeyboardMarkup([
                                          [InlineKeyboardButton('↩️返回存储管理', callback_data='ns_re_menu')]
                                      ]))
        else:
            await message_tj.edit(text=name + '添加失败！\n——————————\n' + ns_alist_post.text,
                                  reply_markup=InlineKeyboardMarkup([
                                      [InlineKeyboardButton('↩️返回存储管理', callback_data='ns_re_menu')]
                                  ]))


# 新建存储_批量模式_处理用户发送的配置
ns_new_b_list = []  # 解析后的配置
message_text_list = []  # 用户发送的配置
ns_new_b_message_id = {}  # 存储消息id和消息内容


async def ns_new_b(client: Client, message: Message):
    message_text = message.text
    await storage_config(name)
    st_cfg, user_cfg_code = await user_cfg(message_text)  # 解析用户发送的存储配置

    ns_new_b_message_id.clear()

    a = json.dumps(st_cfg)
    b = json.loads(a)

    if user_cfg_code == 200:
        ns_new_b_list.append(b)
        message_text_list.append(message_text)  # 添加用户发送的配置到列表

        # 删除用户发送的信息
        await message.delete()

        # 开始处理发送的配置
        await ns_r(client, message)
    else:
        message_text_list.append(
            f'添加失败！\n——————————\n请检查配置后重新发送：\n{message_text}\n\n错误Key：\n{str(user_cfg_code)}')
        text = ''
        for i in range(len(message_text_list)):
            textt = f'{i + 1}、\n<code>{str(message_text_list[i])}</code>\n\n'
            text += textt
        await message.delete()
        try:
            await client.edit_message_text(chat_id=message.chat.id,
                                           message_id=chat_data['ns_mode_b_message_2_message_id'],
                                           text=f'已添加的配置：\n{str(text)}',
                                           reply_markup=InlineKeyboardMarkup([
                                               [InlineKeyboardButton('↩️返回存储列表',
                                                                     callback_data='ns_re_list_mode_b')]
                                           ])
                                           )
        except Exception as e:
            logging.info(e)
        message_text_list.pop()
    return


# 撤销添加的配置
@Client.on_callback_query(filters.regex('^ns_re$'))
async def ns_remove(client: Client, query: CallbackQuery):
    message_text_list.pop()
    ns_new_b_list.pop()
    await ns_r(client, query)


# 新建存储_刷新已添加的存储
async def ns_r(client: Client, message: Union[Message, CallbackQuery]):
    text = ''
    for i in range(len(ns_new_b_list)):
        textt = f'{i + 1}、\n<code>{str(message_text_list[i])}</code>\n\n'
        text += textt
    button = [
        [
            InlineKeyboardButton('🔄撤销', callback_data='ns_re'),
            InlineKeyboardButton('↩️返回', callback_data='ns_re_list_mode_b'),
        ],
        [InlineKeyboardButton('🎉开始新建', callback_data='ns_sp')],
    ]
    ns_r_text = await client.edit_message_text(
        chat_id=message.chat.id if isinstance(message, Message) else message.message.chat.id,
        message_id=chat_data['ns_mode_b_message_2_message_id'],
        text='已添加的配置：\n' + str(text),
        reply_markup=InlineKeyboardMarkup(button))
    ns_new_b_message_id['text'] = ns_r_text.text


# 开始批量新建存储
@Client.on_callback_query(filters.regex('^ns_sp$'))
async def ns_new_b_start(client: Client, query: CallbackQuery):
    chat_data["ns_b"] = False
    message_b = []
    await client.edit_message_text(chat_id=query.message.chat.id,
                                   message_id=chat_data['ns_mode_b_message_2_message_id'],
                                   text=f'<code>{ns_new_b_message_id["text"]}</code>')
    ns_b_message_tj = await query.message.reply("开始添加存储")
    text = ''
    for i in range(len(ns_new_b_list)):
        st_cfg = ns_new_b_list[i]
        ns_body = remove_quotes(st_cfg)
        ns_alist_post = await storage_create(ns_body)  # 新建存储
        ns_json = ns_alist_post.json()
        mount_path = ns_new_b_list[i]["mount_path"]
        if ns_json['code'] == 200:
            message_b.append(f'{mount_path} 添加成功！')
        elif ns_json['code'] == 500 and 'but storage is already created' in ns_json['data']:  # 初始化存储失败，但存储已经创建
            storage_id = str(ns_json['data']['id'])
            ns_get_get = await storage_get(storage_id)  # 查询指定存储信息
            ns_get_json = ns_get_get.json()
            ns_update_json = ns_get_json['data']
            ns_update_post = await storage_update(ns_update_json)  # 更新存储
            ns_up_json = ns_update_post.json()
            if ns_up_json['code'] == 200:
                message_b.append(f'{mount_path} 添加成功！')
            else:
                message_b.append(f'{mount_path} 添加失败！\n——————————\n{ns_update_post.text}\n——————————')
        elif ns_json['code'] == 500 and '1062 (23000)' in ns_json['data']:  # 存储路径已存在
            message_b.append(f'{mount_path} 添加失败！\n——————————\n{ns_alist_post.text}\n——————————')
        else:
            message_b.append(f'{mount_path} 添加失败！\n——————————\n{ns_alist_post.text}\n——————————')
        textt = f'{str(message_b[i])}\n'
        text += textt
        ns_new_bb_start = await ns_b_message_tj.edit(text=text, reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton('↩️︎返回存储管理', callback_data='ns_re_new_b_menu')
            ]
        ]))
        chat_data['ns_new_b_start_chat_id'] = ns_new_bb_start.chat.id
        chat_data['ns_new_b_start_message_id'] = ns_new_bb_start.id

    ns_new_b_list.clear()
    message_text_list.clear()


# 删除用户和bot的信息
async def ns_mode_b_delete(client: Client):
    await client.delete_messages(chat_id=chat_data['ns_new_b_start_chat_id'],
                                 message_ids=chat_data['ns_new_b_start_message_id'])
    await client.delete_messages(chat_id=chat_data['ns_mode_b_message_2_chat_id'],
                                 message_ids=chat_data['ns_mode_b_message_2_message_id'])


# 删除用户和bot的信息
async def ns_re_list_mode_b(client: Client):
    await client.delete_messages(chat_id=chat_data['ns_mode_b_message_2_chat_id'],
                                 message_ids=chat_data['ns_mode_b_message_2_message_id'])


# 复制存储配置
@Client.on_callback_query(filters.regex(r'^st_storage_copy_cfg') & is_admin)
async def st_storage_copy_cfg(_, query: CallbackQuery):
    bvj = int(query.data.strip("st_storage_copy_cfg"))
    get = await storage_get(driver_id[bvj])
    get = get.json()
    get_a, get_b = get['data'], json.loads(get['data']['addition'])

    get_a = translate_key(translate_key(get_a, text_dict['common']), text_dict['additional'])
    get_b = translate_key(translate_key(get_b, text_dict['common']), text_dict['additional'])
    get_a.update(get_b)
    delete = ['额外信息', '状态', '修改时间', '禁用', 'id', '驱动', '是否Sharepoint', 'AccessToken']
    for i in delete:
        try:
            get_a.pop(i)
        except KeyError:
            ...
    get_a['备注'] = get_a['备注'].replace('\n', ' ')
    text_list = [f"{i} = {get_a[i]}\n" for i in get_a.keys()]
    text = "".join(text_list)
    await storage_menu_button.edit(text=f'<code>{text}</code>',
                                   reply_markup=InlineKeyboardMarkup(button_list),
                                   disable_web_page_preview=True
                                   )


# 修改默认存储配置
async def st_storage_cfg_amend(client: Client, message: Message):
    message_text = message.text
    await client.delete_messages(chat_id=chat_data['chat_id'],
                                 message_ids=chat_data['message_id'])
    button = [
        [
            InlineKeyboardButton('🔄重新修改', callback_data='st_storage_cfg_amend')
        ],
        [
            InlineKeyboardButton('↩️返回存储管理', callback_data='st_return')
        ]
    ]
    try:
        message_text = json.loads(message_text)
    except json.decoder.JSONDecodeError as z:
        await storage_menu_button.edit(text=f'配置错误\n——————————\n请检查配置:\n<code>{message_text}</code>\n{z}',
                                       reply_markup=InlineKeyboardMarkup(button))
    else:
        new_dict = {v: k for k, v in text_dict['common'].items()}  # 调换common键和值的位置
        new_add_dict = {v: k for k, v in text_dict['additional'].items()}  # 调换additional键和值的位置
        new_dict |= new_add_dict
        #         ekey = [key for key in message_text.keys() if key not in new_dict.keys()]
        #         if ekey_text := '\n'.join(ekey):
        #             text = f'''配置错误
        # ——————————
        # 请检查配置:
        # <code>{json.dumps(message_text, indent=4, ensure_ascii=False)}</code>
        # 错误Key：
        # <code>{ekey_text}</code>
        # '''
        #             await client.edit_message_text(chat_id=message.chat.id,
        #                                            message_id=storage_menu_button.id,
        #                                            text=text,
        #                                            reply_markup=InlineKeyboardMarkup(button))
        #         else:
        t = translate_key(message_text, new_dict)
        t_d = {'storage': t}
        write_config("config/storage_cfg.yaml", t_d)
        await st_storage_amend('', '')


#####################################################################################

#####################################################################################

# 解析用户发送的存储配置，返回解析后的配置和状态码
async def user_cfg(message_text):  # sourcery skip: dict-assign-update-to-union
    message_config = {'addition': {}}  # 解析用户发送的配置
    new_dict = {v: k for k, v in text_dict['common'].items()}  # 调换common键和值的位置
    new_add_dict = {v: k for k, v in text_dict['additional'].items()}  # 调换additional键和值的位置
    new_dict.update(new_add_dict)  # 合并调换位置后的common，additional
    try:
        user_cfg_code = 200
        for i in message_text.split('\n'):
            k = i.split('=')[0].strip(' * ')
            l_i = new_dict.get(k, k)
            r_i = i.split('=')[1].replace(" ", "")
            if r_i == 'True':
                r_i = 'true'
            elif r_i == 'False':
                r_i = 'false'
            if l_i in text_dict['common']:
                message_config[l_i] = r_i
            else:
                message_config['addition'][l_i] = r_i
    except KeyError as e:
        user_cfg_code = e
    else:
        common_dict['addition'].update(message_config['addition'])
        message_config['addition'].update(common_dict['addition'])
        common_dict.update(message_config)  # 将用户发送的配置更新到默认配置
        common_dict['addition'] = f'''{json.dumps(common_dict['addition'])}'''
    return common_dict, user_cfg_code


# 获取存储并写入列表
async def get_storage(callback_data_pr):
    mount_path.clear()
    disabled.clear()
    driver_id.clear()
    button_list.clear()

    vs_alist_post = await storage_list()  # 获取存储列表
    vs_data = vs_alist_post.json()

    for item in vs_data['data']['content']:
        mount_path.append(item['mount_path'])
        disabled.append(item['disabled'])
        driver_id.append(item['id'])

    for button_js in range(len(mount_path)):
        disabled_a = '❌' if disabled[button_js] else '✅'

        # 添加存储按钮
        storage_button = [InlineKeyboardButton(mount_path[button_js] + disabled_a,
                                               callback_data=callback_data_pr + str(button_js))]
        button_list.append(storage_button)
    button_list.insert(0, return_button)  # 列表开头添加返回和关闭菜单按钮
    button_list.append(return_button)  # 列表结尾添加返回和关闭菜单按钮
    return button_list


# 删除json中num和bool的值的引号
def remove_quotes(obj):
    if isinstance(obj, (int, float, bool)):
        return obj
    elif isinstance(obj, dict):
        return {k: remove_quotes(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [remove_quotes(elem) for elem in obj]
    elif isinstance(obj, str):
        try:
            return int(obj)
        except ValueError:
            try:
                return float(obj)
            except ValueError:
                if obj.lower() == 'true':
                    return True
                elif obj.lower() == 'false':
                    return False
                else:
                    return obj
    else:
        return obj


# 解析驱动配置模板并返回 新建存储的json模板，消息模板
async def storage_config(driver_name):
    storage_name = driver_name
    additional_dict = {}
    default_storage_config = []  # 默认存储配置
    default_storage_config_message = []  # 发给用户的模板
    common_dict['driver'] = driver_name  # 将驱动名称加入字典
    stj = await get_driver()
    stj = stj.json()['data']

    def common_c(vl):
        for i in range(len(stj[storage_name][vl])):
            stj_name = stj[storage_name][vl][int(i)]['name']  # 存储配置名称
            stj_bool = stj[storage_name][vl][int(i)]['type']
            stj_default = stj[storage_name][vl][int(i)]['default'] if stj_bool != 'bool' else 'false'  # 存储配置默认值
            stj_options = stj[storage_name][vl][int(i)]['options']  # 存储配置可选选项
            stj_required = stj[storage_name][vl][int(i)]['required']  # 是否必填
            cr = '*' if stj_required else ''
            co = '' if not stj_options else f'({stj_options})'
            if vl == 'common':
                common_dict[stj_name] = stj_default
            else:
                additional_dict[stj_name] = stj_default  # 将存储配置名称和默认值写入字典
            sn = text_dict[vl].get(stj_name, stj_name)
            default_storage_config.append(f'{sn} = {stj_default}')
            try:
                for k in storage_cfg()['storage'].keys():
                    if k in text_dict['common'].keys():
                        common_dict[k] = storage_cfg()['storage'][k]
                    else:
                        additional_dict[k] = storage_cfg()['storage'][k]
            except (AttributeError, KeyError):
                ...
            if vl == 'common':
                default_storage_config_message.append(
                    f'''{cr}{sn} = {common_dict[stj_name]} {co}''')  # 发给用户的模板
            else:
                default_storage_config_message.append(
                    f'''{cr}{sn} = {additional_dict[stj_name]} {co}''')  # 发给用户的模板

    common_c(vl='common')
    common_c(vl='additional')

    common_dict['addition'] = additional_dict  # 将additional添加到common
    common_dict_json = json.dumps(common_dict, ensure_ascii=False)
    default_storage_config_message = [f"{default_storage_config_message[i]}\n" for i in
                                      range(len(default_storage_config_message))]
    text = "".join(default_storage_config_message)
    return text, common_dict_json

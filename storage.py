# -*- coding: UTF-8 -*-
import datetime
import json
import re

import telegram
import yaml
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler, CommandHandler, filters, MessageHandler

from alist_api import storage_update, storage_create, storage_list, storage_get, storage_delete, storage_disable, \
    storage_enable
from bot import alist_host, alist_token, translate_key, admin_yz

mount_path = []  ## 存储路径
disabled = []  ## 存储是否禁用
id = []  ## 存储id
ns_button_list = []  ## 支持添加的存储的按钮
button_list = []
common_dict = {}  ## 新建存储——新建存储的json模板
## 返回菜单
return_button = [InlineKeyboardButton('↩️返回存储管理',
                                      callback_data=str('st_return')),
                 InlineKeyboardButton('❌关闭菜单',
                                      callback_data=str('st_close'))]

with open('config/cn_dict.json', 'r', encoding='utf-8') as c:
    text_dict = json.load(c)

with open("config/driver_list.json", 'r', encoding='utf-8') as d:
    stj = json.load(d)
    stj_key = stj.keys()
    stj_key = list(stj_key)

with open("config/storage_cfg.yaml", 'r', encoding='utf-8') as f:
    storage_cfg = yaml.safe_load(f)


#####################################################################################
## 按钮回调
#####################################################################################


## 存储管理菜单 按钮回调
@admin_yz
async def st_button_callback(update, context):
    query = update.callback_query
    bvj = query.data
    if bvj == 'st_vs':
        await vs(update, context)
    elif bvj == 'st_cs':
        await cs(update, context)
    elif bvj == 'st_ns':
        await ns(update, context)
    elif bvj == 'st_ds':
        await ds(update, context)
    elif bvj == 'st_return':
        context.chat_data["st_storage_cfg_amend"] = False
        await st_return(update, context)
    elif bvj == 'st_close':
        await st_close(update, context)
    elif bvj.startswith("st_storage"):
        if bvj.startswith("st_storage_copy"):
            if bvj == 'st_storage_copy_list':
                await st_storage_copy_list(update, context)
            elif bvj.startswith('st_storage_copy_cfg'):
                bvj = int(bvj.strip("st_storage_copy_cfg"))
                await st_storage_copy_cfg(bvj, query, update, context)
        elif bvj == 'st_storage_amend':
            await st_storage_amend(update, context)
        elif bvj == 'st_storage_cfg_amend':
            context.chat_data["st_storage_cfg_amend"] = True
            await st_storage_amend_callback(update, context)
        elif bvj == 'st_storage_cfg_off':
            context.chat_data["st_storage_cfg_amend"] = False
            await st_storage_amend(update, context)


## 开关存储 按钮回调
@admin_yz
async def vs_button_callback(update):
    query = update.callback_query
    bvj = query.data
    if bvj == 'vs_onall':
        await vs_on_off_all(bvj, query)
    elif bvj == 'vs_offall':
        await vs_on_off_all(bvj, query)
    else:
        bvj = int(bvj.strip("vs"))
        await vs_callback(bvj, query)


## 复制存储 按钮回调
@admin_yz
async def cs_button_callback(update):
    query = update.callback_query
    bvj = query.data
    bvj = int(bvj.strip("cs"))
    await cs_callback(bvj, query)


## 删除存储 按钮回调
@admin_yz
async def ds_button_callback(update):
    query = update.callback_query
    bvj = query.data
    bvj = int(bvj.strip("ds"))
    await ds_callback(bvj, query)


## 新建存储 按钮回调
@admin_yz
async def ns_button_callback(update, context):
    query = update.callback_query
    bvj = query.data
    if 'ns_a' in bvj:
        bvj_a = int(bvj.strip("ns_a"))
        await ns_mode_a(bvj_a, query)
    elif bvj.startswith("ns_re"):
        if bvj == 'ns_re':  ##撤销添加的配置
            message_text_list.pop()
            ns_new_b_list.pop()
            await ns_r(update, context)
        elif bvj == 'ns_re_list':  ## 返回可添加存储列表
            context.chat_data["ns_a"] = False
            await ns(update, context)
        elif bvj == 'ns_re_ns_mode_a':  ## 添加单个存储失败后重新添加
            context.chat_data["ns_a"] = True
            await ns_mode_a_delete(context)
        elif bvj == 'ns_re_menu':  ## 添加单个存储_返回存储管理菜单
            await ns_mode_a_delete(context)
            await st_return(update, context)
        elif bvj == 'ns_re_new_b_menu':  ## 添加单个存储_返回存储管理菜单
            await ns_mode_b_delete(context)
            await st_return(update, context)
        elif bvj == 'ns_re_list_mode_b':
            context.chat_data["ns_b"] = False
            await ns_re_list_mode_b(context)
            await ns(update, context)
    elif 'ns_b' in bvj:  ## 多个模式，发送模板后监听下一条消息
        bvj_b = int(bvj.strip("ns_b"))
        await ns_mode_b(bvj_b, query, update)
    elif bvj == 'ns_sp':  ##  开始批量新建存储
        context.chat_data["ns_b"] = False
        await ns_new_b_start(update, context)
    else:
        bvj_sn = int(bvj.strip("ns"))  ##  发送选择模式菜单
        await ns_mode(bvj_sn, query, update, context)


#####################################################################################
## 监听指令
#####################################################################################

ns_a_message = {}  ##保存 添加单个存储 的用户和bot消息id


## 检测普通消息
async def echo(update, context):
    if "ns_a" in context.chat_data and context.chat_data["ns_a"]:
        context.chat_data["ns_a"] = False
        await ns_new_a(update, context)
        ns_a_message['chat_id'] = update.effective_chat.id
        ns_a_message['message_id'] = update.message.message_id
    elif "ns_b" in context.chat_data and context.chat_data["ns_b"]:
        await ns_new_b(update, context)
        ns_a_message['chat_id'] = update.effective_chat.id
        ns_a_message['message_id'] = update.message.message_id
    elif "st_storage_cfg_amend" in context.chat_data and context.chat_data["st_storage_cfg_amend"]:
        context.chat_data["st_storage_cfg_amend"] = False
        ns_a_message['chat_id'] = update.effective_chat.id
        ns_a_message['message_id'] = update.message.message_id
        await st_storage_cfg_amend(update, context)
    return


## 存储管理菜单
@admin_yz
async def st(update, context):
    global st_button
    global storage_menu_button
    st_button = [
        [
            InlineKeyboardButton('⚙️存储管理', callback_data='st_set')
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
    sl = storage_list(alist_host, alist_token)
    sl_json = json.loads(sl.text)
    zcc = len(sl_json['data']['content'])
    content_list = sl_json["data"]["content"]
    jysl = 0
    for item in content_list:
        if item["disabled"] == True:
            jysl += 1
    qysl = zcc - jysl
    text = f'存储数量：{zcc}\n启用：{qysl}\n禁用：{jysl}'
    storage_menu_button = await context.bot.send_message(chat_id=update.effective_chat.id,
                                                         text=text,
                                                         reply_markup=InlineKeyboardMarkup(st_button),
                                                         parse_mode=telegram.constants.ParseMode.HTML
                                                         )


## 返回存储管理菜单
async def st_return(update, context):
    sl = storage_list(alist_host, alist_token)
    sl_json = json.loads(sl.text)
    zcc = len(sl_json['data']['content'])
    content_list = sl_json["data"]["content"]
    jysl = 0
    for item in content_list:
        if item["disabled"] == True:
            jysl += 1
    qysl = zcc - jysl
    text = f'存储数量：{zcc}\n启用：{qysl}\n禁用：{jysl}'
    await context.bot.edit_message_text(chat_id=update.effective_chat.id,
                                        message_id=storage_menu_button.message_id,
                                        text=text,
                                        reply_markup=InlineKeyboardMarkup(st_button))


## 关闭存储管理菜单
async def st_close(update, context):
    await context.bot.edit_message_text(chat_id=update.effective_chat.id,
                                        message_id=storage_menu_button.message_id,
                                        text='已退出『存储管理』')


## 发送 开关存储 按钮列表
async def vs(update, context):
    await get_storage(alist_host, alist_token, callback_data_pr='vs')
    global vs_all_button
    vs_all_button = [

        InlineKeyboardButton('✅开启全部', callback_data='vs_onall'),
        InlineKeyboardButton('❌关闭全部', callback_data='vs_offall')

    ]
    button_list.insert(1, vs_all_button)
    button_list.insert(-1, vs_all_button)
    await context.bot.edit_message_text(chat_id=update.effective_chat.id,
                                        message_id=storage_menu_button.message_id,
                                        text='点击开启/关闭存储\n存储列表：',
                                        reply_markup=InlineKeyboardMarkup(button_list))


## 发送 复制存储 按钮列表
async def cs(update, context):
    await get_storage(alist_host, alist_token, callback_data_pr='cs')
    await context.bot.edit_message_text(chat_id=update.effective_chat.id,
                                        message_id=storage_menu_button.message_id,
                                        text='点击复制存储\n存储列表：',
                                        reply_markup=InlineKeyboardMarkup(button_list))


## 发送 删除存储 按钮列表
async def ds(update, context):
    await get_storage(alist_host, alist_token, callback_data_pr='ds')
    await context.bot.edit_message_text(chat_id=update.effective_chat.id,
                                        message_id=storage_menu_button.message_id,
                                        text='点击删除存储\n存储列表：',
                                        reply_markup=InlineKeyboardMarkup(button_list))


## 发送 添加存储 按钮列表
async def ns(update, context):
    storage_list = stj_key  ## 支持添加的存储列表
    ns_button_list.clear()

    for storage_list_js in range(len(storage_list)):
        button_ns = [InlineKeyboardButton(storage_list[storage_list_js], callback_data='ns' + str(storage_list_js))]
        ns_button_list.append(button_ns)

    ns_button_list.insert(0, return_button)  ## 列表开头添加返回和关闭菜单按钮
    ns_button_list.append(return_button)  ## 列表结尾添加返回和关闭菜单按钮

    await context.bot.edit_message_text(chat_id=update.effective_chat.id,
                                        message_id=storage_menu_button.message_id,
                                        text='支持添加的存储：',
                                        reply_markup=InlineKeyboardMarkup(ns_button_list))


## 发送 复制存储配置 按钮列表
async def st_storage_copy_list(update, context):
    await get_storage(alist_host, alist_token, callback_data_pr='st_storage_copy_cfg')
    await context.bot.edit_message_text(chat_id=update.effective_chat.id,
                                        message_id=storage_menu_button.message_id,
                                        text='点击复制存储配置：',
                                        reply_markup=InlineKeyboardMarkup(button_list))


## 修改存储默认配置
async def st_storage_amend(update, context):
    t = translate_key(translate_key(storage_cfg['storage'], text_dict['common']), text_dict['additional'])
    t = json.dumps(t, indent=4, ensure_ascii=False)

    button = [
        [
            InlineKeyboardButton('🔧修改配置', callback_data='st_storage_cfg_amend')
        ],
        [
            InlineKeyboardButton('↩️返回存储管理', callback_data='st_return')
        ]
    ]

    await context.bot.edit_message_text(chat_id=update.effective_chat.id,
                                        message_id=storage_menu_button.message_id,
                                        text=f'当前配置：\n<code>{t}</code>',
                                        reply_markup=InlineKeyboardMarkup(button),
                                        parse_mode=telegram.constants.ParseMode.HTML)


## 修改存储默认配置_按钮回调
async def st_storage_amend_callback(update, context):
    t = translate_key(translate_key(storage_cfg['storage'], text_dict['common']), text_dict['additional'])
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

格式：
1、每行前面要添加4个空格
2、除了最后一行，每行后面都要添加英文逗号“,”
'''
    await context.bot.edit_message_text(chat_id=update.effective_chat.id,
                                        message_id=storage_menu_button.message_id,
                                        text=text,
                                        reply_markup=InlineKeyboardMarkup(button),
                                        parse_mode=telegram.constants.ParseMode.HTML,
                                        disable_web_page_preview=True)


#####################################################################################
## 运行
#####################################################################################


## 开启关闭存储
async def vs_callback(bvj, query):
    storage_id = id[int(bvj)]
    if disabled[bvj]:
        of_t = "✅已开启存储："
        storage_enable(storage_id, alist_host, alist_token)
    else:
        of_t = "❌已关闭存储："
        storage_disable(storage_id, alist_host, alist_token)
    await get_storage(alist_host, alist_token, callback_data_pr='vs')
    button_list.insert(1, vs_all_button)
    button_list.insert(-1, vs_all_button)
    await query.edit_message_text(
        text=of_t + mount_path[bvj],
        reply_markup=InlineKeyboardMarkup(button_list)
    )


## 开启&关闭全部存储
async def vs_on_off_all(bvj, query):
    command = storage_enable if bvj == 'vs_onall' else storage_disable
    action = '开启中...' if bvj == 'vs_onall' else '关闭中...'
    await query.edit_message_text(
        text=action,
        reply_markup=InlineKeyboardMarkup(button_list))
    for i, is_disabled in enumerate(disabled):
        if is_disabled:
            command(id[i], alist_host, alist_token)
            await get_storage(alist_host, alist_token, callback_data_pr='vs')
            button_list.insert(1, vs_all_button)
            button_list.insert(-1, vs_all_button)
            try:
                await query.edit_message_text(
                    text=action,
                    reply_markup=InlineKeyboardMarkup(button_list))
            except telegram.error.BadRequest:
                pass


## 复制存储
async def cs_callback(bvj, query):
    cs_storage = []
    cs_storage.clear()
    storage_id = str(id[int(bvj)])
    cs_alist_get = storage_get(storage_id, alist_host, alist_token)  ## 获取存储
    cs_json = json.loads(cs_alist_get.text)

    cs_storage.append(cs_json['data'])  ## 保存获取的存储
    del cs_storage[0]['id']  ## 删除存储id
    now = datetime.datetime.now()
    current_time = now.strftime("%M%S")  ## 获取当前时间

    cs_mount_path = cs_storage[0]['mount_path']
    cs_order = cs_storage[0]['order']
    if '.balance' not in cs_mount_path:  ## 修改存储的mount_path
        cs_storage[0]['mount_path'] = cs_mount_path + '.balance' + current_time
    else:
        cs_mount_path_text = re.sub('.balance.*', '', cs_mount_path)
        cs_storage[0]['mount_path'] = cs_mount_path_text + '.balance' + current_time
    cs_storage[0]['order'] = cs_order + 1  ## 基于当前配置的排序加1
    cs_storage[0]['remark'] = mount_path[bvj] + ' -> ' + cs_storage[0]['mount_path']  ##修改配置文件

    body = cs_storage[0]
    storage_create(body, alist_host, alist_token)  ## 新建存储

    await get_storage(alist_host, alist_token, callback_data_pr='cs')
    await query.edit_message_text(
        text='已复制\n' + mount_path[bvj] + ' -> ' + cs_storage[0]['mount_path'],
        reply_markup=InlineKeyboardMarkup(button_list)
    )


## 删除存储
async def ds_callback(bvj, query):
    storage_id = id[int(bvj)]
    storage_delete(storage_id, alist_host, alist_token)
    stid = mount_path[bvj]
    await get_storage(alist_host, alist_token, callback_data_pr='ds')
    await query.edit_message_text(
        text='🗑已删除存储：' + stid,
        reply_markup=InlineKeyboardMarkup(button_list)
    )


## 选择存储后，发送添加模式按钮
async def ns_mode(bvj, query, update, context):
    storage_list = stj_key  ## 支持添加的存储列表
    global name
    name = storage_list[bvj]
    button = [
        [
            InlineKeyboardButton('☝️添加单个', callback_data='ns_a' + str(bvj)),
            InlineKeyboardButton('🖐添加多个', callback_data='ns_b' + str(bvj))
        ],
        [
            InlineKeyboardButton('↩️返回存储列表', callback_data='ns_re_list')
        ]
    ]
    await query.edit_message_text(
        text=f'<b>选择的存储：{name}</b>\n选择模式：',
        reply_markup=InlineKeyboardMarkup(button),
        parse_mode=telegram.constants.ParseMode.HTML
    )


## 单个模式，发送模板后监听下一条消息
async def ns_mode_a(query, context):
    context.chat_data["ns_a"] = True
    text, common_dict_json = await storage_config(name)
    await query.edit_message_text(
        text=f'''<b>选择的存储：{name}</b>\n<code>{str(text)}</code>\n*为必填，如果有默认值则可不填\n请修改配置后发送''',
        parse_mode=telegram.constants.ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('↩️返回存储列表', callback_data='ns_re_list')]]))


## 删除用户和bot的信息
async def ns_mode_a_delete(context):
    await context.bot.delete_message(chat_id=ns_a_message['chat_id_a'],
                                     message_id=ns_a_message['message_id_a'])
    await context.bot.delete_message(chat_id=ns_a_message['chat_id'],
                                     message_id=ns_a_message['message_id'])


## 多个模式，发送模板后监听下一条消息
async def ns_mode_b(query, update, context):
    ns_new_b_list.clear()
    message_text_list.clear()
    context.chat_data["ns_b"] = True
    text, common_dict_json = await storage_config(name)
    await query.edit_message_text(
        text=f'''<b>选择的存储：{name}</b>\n<code>{str(text)}</code>\n*为必填，如果有默认值则可不填\n请修改配置后发送''',
        parse_mode=telegram.constants.ParseMode.HTML
    )
    global ns_mode_b_start
    ns_mode_b_message_2 = ns_mode_b_start = await context.bot.send_message(chat_id=update.effective_chat.id,
                                                                           text='请发送存储配置，注意挂载路径不要重复',
                                                                           reply_markup=InlineKeyboardMarkup([
                                                                               [InlineKeyboardButton('↩️返回存储列表',
                                                                                                     callback_data='ns_re_list_mode_b')]
                                                                           ]))
    ns_a_message['ns_mode_b_message_2_chat_id'] = ns_mode_b_message_2.chat_id
    ns_a_message['ns_mode_b_message_2_message_id'] = ns_mode_b_message_2.message_id


## 新建存储_单个模式
async def ns_new_a(update, context):
    message_tj = await update.message.reply_text(reply_to_message_id=update.message.message_id,
                                                 text='新建存储中...')
    ns_a_message['chat_id_a'] = message_tj.chat_id
    ns_a_message['message_id_a'] = message_tj.message_id
    message_text = update.message.text
    st_cfg, user_cfg_code = await user_cfg(update)  ## 解析用户发送的存储配置
    if user_cfg_code != 200:
        text = f'添加失败！\n——————————\n请检查配置后重新发送：\n<code>{message_text}</code>\n\n错误Key：\n<code>{str(user_cfg_code)}</code>'
        await context.bot.edit_message_text(chat_id=update.effective_chat.id,
                                            message_id=message_tj.message_id,
                                            text=text,
                                            reply_markup=InlineKeyboardMarkup([
                                                [InlineKeyboardButton('🔄重新添加', callback_data='ns_re_ns_mode_a')],
                                                [InlineKeyboardButton('↩️︎返回存储管理', callback_data='ns_re_menu')]
                                            ]))
    else:

        ns_body = remove_quotes(st_cfg)
        ns_alist_post = storage_create(ns_body, alist_host, alist_token)  ## 新建存储
        ns_json = json.loads(ns_alist_post.text)

        if ns_json['code'] == 200:
            await context.bot.edit_message_text(chat_id=update.effective_chat.id,
                                                message_id=message_tj.message_id,
                                                text=name + '添加成功！',
                                                reply_markup=InlineKeyboardMarkup([
                                                    [InlineKeyboardButton('↩️返回存储管理', callback_data='ns_re_menu')]
                                                ]))
        elif ns_json['code'] == 500:
            storage_id = str(ns_json['data']['id'])
            ns_get_get = storage_get(storage_id, alist_host, alist_token)  ## 查询指定存储信息
            ns_get_json = json.loads(ns_get_get.text)

            ns_update_json = ns_get_json['data']
            ns_update_post = storage_update(ns_update_json, alist_host, alist_token)  ## 更新存储
            ns_up_json = json.loads(ns_update_post.text)

            if ns_up_json['code'] == 200:
                await context.bot.edit_message_text(chat_id=update.effective_chat.id,
                                                    message_id=message_tj.message_id,
                                                    text=name + '添加成功！',
                                                    reply_markup=InlineKeyboardMarkup([
                                                        [InlineKeyboardButton('↩️返回存储管理',
                                                                              callback_data='ns_re_menu')]
                                                    ]))
            else:
                await context.bot.edit_message_text(chat_id=update.effective_chat.id,
                                                    message_id=message_tj.message_id,
                                                    text=name + '添加失败！\n——————————\n' + ns_update_post.text,
                                                    reply_markup=InlineKeyboardMarkup([
                                                        [InlineKeyboardButton('↩️返回存储管理',
                                                                              callback_data='ns_re_menu')]
                                                    ]))
        else:
            await context.bot.edit_message_text(chat_id=update.effective_chat.id,
                                                message_id=message_tj.message_id,
                                                text=name + '添加失败！\n——————————\n' + ns_alist_post.text,
                                                reply_markup=InlineKeyboardMarkup([
                                                    [InlineKeyboardButton('↩️返回存储管理', callback_data='ns_re_menu')]
                                                ]))


## 新建存储_批量模式_处理用户发送的配置
ns_new_b_list = []  ## 解析后的配置
message_text_list = []  ## 用户发送的配置
ns_new_b_message_id = {}  ## 存储消息id和消息内容


async def ns_new_b(update, context):
    message_text = update.message.text
    await storage_config(name)
    st_cfg, user_cfg_code = await user_cfg(update)  ## 解析用户发送的存储配置

    ns_new_b_message_id.clear()

    a = json.dumps(st_cfg)
    b = json.loads(a)

    if user_cfg_code == 200:
        ns_new_b_list.append(b)
        message_text_list.append(message_text)  ## 添加用户发送的配置到列表

        ## 删除用户发送的信息
        await context.bot.delete_message(chat_id=update.effective_chat.id,
                                         message_id=update.message.message_id)

        ## 开始处理发送的配置
        await ns_r(update, context)
    else:
        message_text_list.append(
            f'添加失败！\n——————————\n请检查配置后重新发送：\n{message_text}\n\n错误Key：\n{str(user_cfg_code)}')
        text = ''
        for i in range(len(message_text_list)):
            textt = f'{i + 1}、\n<code>{str(message_text_list[i])}</code>\n\n'
            text += textt
        await context.bot.delete_message(chat_id=update.effective_chat.id,
                                         message_id=update.message.message_id)
        try:
            await context.bot.edit_message_text(chat_id=update.effective_chat.id,
                                                message_id=ns_mode_b_start.message_id,
                                                text=f'已添加的配置：\n{str(text)}',
                                                parse_mode=telegram.constants.ParseMode.HTML,
                                                reply_markup=InlineKeyboardMarkup([
                                                    [InlineKeyboardButton('↩️返回存储列表',
                                                                          callback_data='ns_re_list_mode_b')]
                                                ])
                                                )
        except telegram.error.BadRequest as e:
            pass
        message_text_list.pop()
    return


## 新建存储_刷新已添加的存储
async def ns_r(update, context):
    text = ''
    for i in range(len(ns_new_b_list)):
        nlj = json.dumps(ns_new_b_list[i], indent=4, ensure_ascii=False)
        textt = f'{i + 1}、\n<code>{str(message_text_list[i])}</code>\n\n'
        text += textt
    button = [
        [
            InlineKeyboardButton('🔄撤销', callback_data=str('ns_re')),
            InlineKeyboardButton('↩️返回', callback_data='ns_re_list_mode_b')

        ],
        [
            InlineKeyboardButton('🎉开始新建', callback_data=str('ns_sp'))
        ]
    ]

    ns_r_text = await context.bot.edit_message_text(chat_id=update.effective_chat.id,
                                                    message_id=ns_mode_b_start.message_id,
                                                    text='已添加的配置：\n' + str(text),
                                                    reply_markup=InlineKeyboardMarkup(button),
                                                    parse_mode=telegram.constants.ParseMode.HTML)
    ns_new_b_message_id['text'] = ns_r_text.text


## 开始批量新建存储
async def ns_new_b_start(update, context):
    message_b = []
    await context.bot.edit_message_text(chat_id=update.effective_chat.id,
                                        message_id=ns_mode_b_start.message_id,
                                        text=f'<code>{ns_new_b_message_id["text"]}</code>',
                                        parse_mode=telegram.constants.ParseMode.HTML)
    ns_b_message_tj = await context.bot.send_message(chat_id=update.effective_chat.id, text="开始添加存储")
    text = ''
    for i in range(len(ns_new_b_list)):
        st_cfg = ns_new_b_list[i]
        ns_body = remove_quotes(st_cfg)
        ns_alist_post = storage_create(ns_body, alist_host, alist_token)  ## 新建存储
        ns_json = json.loads(ns_alist_post.text)
        mount_path = ns_new_b_list[i]["mount_path"]
        if ns_json['code'] == 200:
            message_b.append(f'{mount_path} 添加成功！')
        elif ns_json['code'] == 500 and 'failed init storage but storage is already created' in ns_json[
            'data']:  ## 初始化存储失败，但存储已经创建
            storage_id = str(ns_json['data']['id'])
            ns_get_get = storage_get(storage_id, alist_host, alist_token)  ## 查询指定存储信息
            ns_get_json = json.loads(ns_get_get.text)
            ns_update_json = ns_get_json['data']
            ns_update_post = storage_update(ns_update_json, alist_host, alist_token)  ## 更新存储
            ns_up_json = json.loads(ns_update_post.text)
            if ns_up_json['code'] == 200:
                message_b.append(f'{mount_path} 添加成功！')
            else:
                message_b.append(f'{mount_path} 添加失败！\n——————————\n{ns_update_post.text}\n——————————')
        elif ns_json['code'] == 500 and '1062 (23000)' in ns_json['data']:  ## 存储路径已存在
            message_b.append(f'{mount_path} 添加失败！\n——————————\n{ns_alist_post.text}\n——————————')
        else:
            message_b.append(f'{mount_path} 添加失败！\n——————————\n{ns_alist_post.text}\n——————————')
        textt = f'{str(message_b[i])}\n'
        text += textt
        ns_new_b_start = await context.bot.edit_message_text(chat_id=update.effective_chat.id,
                                                             message_id=ns_b_message_tj.message_id,
                                                             text=text,
                                                             reply_markup=InlineKeyboardMarkup([
                                                                 [InlineKeyboardButton('↩️︎返回存储管理',
                                                                                       callback_data='ns_re_new_b_menu')]
                                                             ]))
        ns_a_message['ns_new_b_start_chat_id'] = ns_new_b_start.chat_id
        ns_a_message['ns_new_b_start_message_id'] = ns_new_b_start.message_id

    ns_new_b_list.clear()
    message_text_list.clear()


## 删除用户和bot的信息
async def ns_mode_b_delete(context):
    await context.bot.delete_message(chat_id=ns_a_message['ns_new_b_start_chat_id'],
                                     message_id=ns_a_message['ns_new_b_start_message_id'])
    await context.bot.delete_message(chat_id=ns_a_message['ns_mode_b_message_2_chat_id'],
                                     message_id=ns_a_message['ns_mode_b_message_2_message_id'])


## 删除用户和bot的信息
async def ns_re_list_mode_b(context):
    await context.bot.delete_message(chat_id=ns_a_message['ns_mode_b_message_2_chat_id'],
                                     message_id=ns_a_message['ns_mode_b_message_2_message_id'])


## 复制存储配置
async def st_storage_copy_cfg(bvj, query, update, context):
    get = json.loads(storage_get(id[int(bvj)], alist_host, alist_token).text)
    get_a, get_b = get['data'], json.loads(get['data']['addition'])

    get_a = translate_key(translate_key(get_a, text_dict['common']), text_dict['additional'])
    get_b = translate_key(translate_key(get_b, text_dict['common']), text_dict['additional'])
    get_a.update(get_b)
    get_a.pop('额外信息')
    text_list = [f"{i} = {get_a[i]}\n" for i in get_a.keys()]
    text = "".join(text_list)
    await query.edit_message_text(text=f'<code>{text}</code>',
                                  reply_markup=InlineKeyboardMarkup(button_list),
                                  disable_web_page_preview=True,
                                  parse_mode=telegram.constants.ParseMode.HTML
                                  )


## 修改默认存储配置
async def st_storage_cfg_amend(update, context):
    message_text = update.message.text
    await context.bot.delete_message(chat_id=ns_a_message['chat_id'],
                                     message_id=ns_a_message['message_id'])
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
        await context.bot.edit_message_text(chat_id=update.effective_chat.id,
                                            message_id=storage_menu_button.message_id,
                                            text=f'配置错误\n——————————\n请检查配置:\n<code>{message_text}</code>\n{z}',
                                            reply_markup=InlineKeyboardMarkup(button),
                                            parse_mode=telegram.constants.ParseMode.HTML)
    else:
        new_dict = {v: k for k, v in text_dict['common'].items()}  ## 调换common键和值的位置
        new_add_dict = {v: k for k, v in text_dict['additional'].items()}  ## 调换additional键和值的位置
        new_dict.update(new_add_dict)  ## 合并调换位置后的common，additional
        ekey = []
        for key in message_text.keys():
            if key not in new_dict.keys():
                ekey.append(key)
        ekey_text = '\n'.join(ekey)
        if ekey_text:
            text = f'''配置错误
——————————
请检查配置:
<code>{json.dumps(message_text, indent=4, ensure_ascii=False)}</code>
错误Key：
<code>{ekey_text}</code>
'''
            await context.bot.edit_message_text(chat_id=update.effective_chat.id,
                                                message_id=storage_menu_button.message_id,
                                                text=text,
                                                reply_markup=InlineKeyboardMarkup(button),
                                                parse_mode=telegram.constants.ParseMode.HTML)
        else:
            t = translate_key(message_text, new_dict)
            t_d = {'storage': t}
            with open('config/storage_cfg.yaml', 'w') as f:
                yaml.dump(t_d, f)
            with open("config/storage_cfg.yaml", 'r', encoding='utf-8') as f:
                global storage_cfg
                storage_cfg = yaml.safe_load(f)
            await st_storage_amend(update, context)


#####################################################################################
## 函数
#####################################################################################

## 解析用户发送的存储配置，返回解析后的配置和状态码
async def user_cfg(message_text):
    message_config = {'addition': {}}  ## 解析用户发送的配置
    new_dict = {v: k for k, v in text_dict['common'].items()}  ## 调换common键和值的位置
    new_add_dict = {v: k for k, v in text_dict['additional'].items()}  ## 调换additional键和值的位置
    new_dict.update(new_add_dict)  ## 合并调换位置后的common，additional
    try:
        user_cfg_code = 200
        for i in message_text.split('\n'):
            l_i = new_dict[i.split('=')[0].strip(' * ')]
            r_i = i.split('=')[1].replace(" ", "")
            if l_i in text_dict['common']:
                message_config[l_i] = r_i
            else:
                message_config['addition'][l_i] = r_i
    except KeyError as e:
        user_cfg_code = e
    else:
        common_dict['addition'].update(message_config['addition'])
        message_config['addition'].update(common_dict['addition'])
        common_dict.update(message_config)  ## 将用户发送的配置更新到默认配置
        common_dict['addition'] = f'''{json.dumps(common_dict['addition'])}'''
    return common_dict, user_cfg_code


## 获取存储并写入列表
async def get_storage(alist_host, alist_token, callback_data_pr):
    mount_path.clear()
    disabled.clear()
    id.clear()
    button_list.clear()

    vs_alist_post = storage_list(alist_host, alist_token)  ## 获取存储列表
    vs_data = json.loads(vs_alist_post.text)

    for item in vs_data['data']['content']:
        mount_path.append(item['mount_path'])
        disabled.append(item['disabled'])
        id.append(item['id'])

    for button_js in range(len(mount_path)):
        disabled_a = '❌' if disabled[button_js] else '✅'

        ## 添加存储按钮
        storage_button = [InlineKeyboardButton(mount_path[button_js] + disabled_a,
                                               callback_data=callback_data_pr + str(button_js))]
        button_list.append(storage_button)
    button_list.insert(0, return_button)  ## 列表开头添加返回和关闭菜单按钮
    button_list.append(return_button)  ## 列表结尾添加返回和关闭菜单按钮
    return button_list


## 删除json中num和bool的值的引号
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


## 解析驱动配置模板并返回 新建存储的json模板，消息模板
async def storage_config(name):
    storage_name = name
    additional_dict = {}
    default_storage_config = []  ## 默认存储配置
    default_storage_config_message = []  ## 发给用户的模板
    common_dict['driver'] = name  ##  将驱动名称加入字典

    def common_c(vl):
        for i in range(len(stj[storage_name][vl])):
            stj_name = stj[storage_name][vl][int(i)]['name']  ## 存储配置名称
            stj_bool = stj[storage_name][vl][int(i)]['type']
            stj_default = stj[storage_name][vl][int(i)][
                'default'] if stj_bool != 'bool' else 'false'  ##  存储配置默认值
            stj_options = stj[storage_name][vl][int(i)]['options']  ##  存储配置可选选项
            stj_required = stj[storage_name][vl][int(i)]['required']  ## 是否必填
            cr = '*' if stj_required else ''
            co = '' if not stj_options else f'({stj_options})'
            if vl == 'common':
                common_dict[stj_name] = stj_default
            else:
                additional_dict[stj_name] = stj_default  ##  将存储配置名称和默认值写入字典
            default_storage_config.append(text_dict[vl][stj_name] + ' = ' + stj_default)  ## 默认存储配置
            try:
                for k in storage_cfg['storage'].keys():
                    common_dict[k] = storage_cfg['storage'][k]
                    additional_dict[k] = storage_cfg['storage'][k]
            except AttributeError:
                pass
            except KeyError:
                pass

            if vl == 'common':
                default_storage_config_message.append(
                    f'''{cr}{text_dict[vl][stj_name]} = {common_dict[stj_name]} {co}''')  ## 发给用户的模板
            else:
                default_storage_config_message.append(
                    f'''{cr}{text_dict[vl][stj_name]} = {additional_dict[stj_name]} {co}''')  ## 发给用户的模板

    common_c(vl='common')
    common_c(vl='additional')

    common_dict['addition'] = additional_dict  ## 将additional添加到common
    common_dict_json = json.dumps(common_dict, ensure_ascii=False)
    default_storage_config_message = [f"{default_storage_config_message[i]}\n" for i in
                                      range(len(default_storage_config_message))]
    text = "".join(default_storage_config_message)

    return text, common_dict_json


#####################################################################################
#####################################################################################

st_handler = CommandHandler('st', st)

##  监听按钮
st_button_callback_handler = CallbackQueryHandler(st_button_callback, pattern=r'^st')  ## 存储设置菜单按钮
vs_button_callback_handler = CallbackQueryHandler(vs_button_callback, pattern=r'^vs')  ##  开关存储按钮
cs_button_callback_handler = CallbackQueryHandler(cs_button_callback, pattern=r'^cs')  ##  复制存储按钮
ds_button_callback_handler = CallbackQueryHandler(ds_button_callback, pattern=r'^ds')  ##  删除存储按钮
ns_button_callback_handler = CallbackQueryHandler(ns_button_callback, pattern=r'^ns')  ##  新建存储按钮

echo_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), echo)  ##  处理普通消息

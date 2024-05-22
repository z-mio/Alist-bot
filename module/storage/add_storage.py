import json
from typing import Union

from loguru import logger
from pyrogram import filters, Client
from pyrogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    CallbackQuery,
    Message,
)

from api.alist.alist_api import alist
from config.config import chat_data
from module.storage.storage import (
    st_return,
    ns_button_list,
    text_dict,
    return_button,
    ns_mode_b_delete,
    ns_re_list_mode_b,
    remove_quotes,
    storage_config,
    user_cfg,
)
from tools.filters import is_admin
from tools.utils import translate_key


def _ns_a_filter(_, __, ___):
    return bool("ns_a" in chat_data and chat_data["ns_a"])


ns_a_filter = filters.create(_ns_a_filter)


def _ns_b_filter(_, __, ___):
    return bool("ns_b" in chat_data and chat_data["ns_b"])


ns_b_filter = filters.create(_ns_b_filter)


# 添加单个存储_返回存储管理菜单
@Client.on_callback_query(filters.regex("^ns_re_menu$"))
async def ns_re_menu_callback(client: Client, __):
    await ns_mode_a_delete(client)
    await st_return()


# 添加单个存储_返回存储管理菜单
@Client.on_callback_query(filters.regex("^ns_re_new_b_menu$"))
async def ns_re_new_b_menu_callback(client: Client, __):
    await ns_mode_b_delete(client)
    await st_return()


# 返回可添加存储列表
@Client.on_callback_query(filters.regex("^ns_re_list$"))
async def ns_re_list_callback(_, __):
    chat_data["ns_a"] = False
    await ns(_, __)


# 返回添加存储列表
@Client.on_callback_query(filters.regex("^ns_re_list_mode_b$"))
async def ns_re_list_mode_b_callback(client: Client, _):
    chat_data["ns_b"] = False
    await ns_re_list_mode_b(client)
    await ns(_, _)


# 发送 添加存储 按钮列表
@Client.on_callback_query(filters.regex(r"^st_ns$"))
async def ns(_, __):
    r = await alist.driver_list()
    stj_key = list(r.data.keys())
    ns_storage_list = translate_key(stj_key, text_dict["driver"])  # 支持添加的存储列表
    ns_button_list.clear()

    for storage_list_js in range(len(ns_storage_list)):
        button_ns = [
            InlineKeyboardButton(
                ns_storage_list[storage_list_js],
                callback_data=f"ns{str(stj_key[storage_list_js])}",
            )
        ]
        ns_button_list.append(button_ns)

    ns_button_list.insert(0, return_button)  # 列表开头添加返回和关闭菜单按钮
    ns_button_list.append(return_button)  # 列表结尾添加返回和关闭菜单按钮

    await chat_data["storage_menu_button"].edit(
        text="支持添加的存储：", reply_markup=InlineKeyboardMarkup(ns_button_list)
    )


# 选择存储后，发送添加模式按钮
@Client.on_callback_query(filters.regex("^ns[^_]"))
async def ns_mode(_, query: CallbackQuery):  # 支持添加的存储列表
    bvj = str(query.data.lstrip("ns"))  # 发送选择模式菜单
    global name
    # stj_key = list(json.loads(get_driver().text)['data'].keys())
    name = bvj
    button = [
        [
            InlineKeyboardButton("☝️添加单个", callback_data=f"ns_a{bvj}"),
            InlineKeyboardButton("🖐添加多个", callback_data=f"ns_b{bvj}"),
        ],
        [InlineKeyboardButton("↩️返回存储列表", callback_data="ns_re_list")],
    ]
    await chat_data["storage_menu_button"].edit(
        text=f"<b>选择的存储：{name}</b>\n选择模式：",
        reply_markup=InlineKeyboardMarkup(button),
    )


# 单个模式，发送模板后监听下一条消息
@Client.on_callback_query(filters.regex("ns_a"))
async def ns_mode_a(_, __):
    chat_data["ns_a"] = True
    text, common_dict_json = await storage_config(name)
    await chat_data["storage_menu_button"].edit(
        text=f"""<b>选择的存储：{name}</b>\n```存储配置\n{text}```\n*为必填，如果有默认值则可不填\n请修改配置后发送""",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("↩️返回存储列表", callback_data="ns_re_list")]]
        ),
    )


# 添加单个存储失败后重新添加
@Client.on_callback_query(filters.regex("^ns_re_ns_mode_a$"))
async def ns_re_ns_mode_a_callback(client: Client, __):
    chat_data["ns_a"] = True
    await ns_mode_a_delete(client)


# 删除用户和bot的信息
async def ns_mode_a_delete(client: Client):
    await client.delete_messages(
        chat_id=chat_data["chat_id_a"], message_ids=chat_data["message_id_a"]
    )
    await client.delete_messages(
        chat_id=chat_data["chat_id"], message_ids=chat_data["message_id"]
    )


# 多个模式，发送模板后监听下一条消息
@Client.on_callback_query(filters.regex("ns_b"))
async def ns_mode_b(_, query: CallbackQuery):
    ns_new_b_list.clear()
    message_text_list.clear()
    chat_data["ns_b"] = True
    text = (await storage_config(name))[0]
    await chat_data["storage_menu_button"].edit(
        f"<b>选择的存储：{name}</b>\n```存储配置\n{text}```\n*为必填，如果有默认值则可不填\n请修改配置后发送",
    )
    ns_mode_b_message_2 = await query.message.reply(
        text="请发送存储配置，注意挂载路径不要重复",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("↩️返回存储列表", callback_data="ns_re_list_mode_b")]]
        ),
    )

    chat_data["ns_mode_b_message_2_chat_id"] = ns_mode_b_message_2.chat.id
    chat_data["ns_mode_b_message_2_message_id"] = ns_mode_b_message_2.id


# 新建存储_单个模式
@Client.on_message(filters.text & filters.private & ns_a_filter & is_admin)
async def ns_new_a(_, message: Message):
    message_tj = await message.reply("新建存储中...")
    chat_data["chat_id_a"] = message_tj.chat.id
    chat_data["message_id_a"] = message_tj.id
    message_text = message.text
    st_cfg, user_cfg_code = await user_cfg(message_text)  # 解析用户发送的存储配置
    if user_cfg_code != 200:
        text = f"""添加失败！
——————————
请检查配置后重新发送：
<code>{message_text}</code>

错误Key：
<code>{str(user_cfg_code)}</code>
"""
        await message_tj.edit(
            text=text,
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "🔄重新添加", callback_data="ns_re_ns_mode_a"
                        )
                    ],
                    [InlineKeyboardButton("↩️︎返回存储管理", callback_data="ns_re_menu")],
                ]
            ),
        )
    else:
        ns_json = await alist.storage_create(remove_quotes(st_cfg))  # 新建存储
        if ns_json.code == 200:
            await message_tj.edit(
                text=f"{name}添加成功！",
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                "↩️返回存储管理", callback_data="ns_re_menu"
                            )
                        ]
                    ]
                ),
            )
        elif ns_json.code == 500:
            storage_id = str(ns_json.data["id"])
            st_info = await alist.storage_get(storage_id)  # 查询指定存储信息
            ns_up_json = await alist.storage_update(st_info.data)  # 更新存储

            if ns_up_json.code == 200:
                await message_tj.edit(
                    text=f"{name}添加成功！",
                    reply_markup=InlineKeyboardMarkup(
                        [
                            [
                                InlineKeyboardButton(
                                    "↩️返回存储管理", callback_data="ns_re_menu"
                                )
                            ]
                        ]
                    ),
                )
            else:
                await message_tj.edit(
                    text=name + "添加失败！\n——————————\n" + ns_up_json["message"],
                    reply_markup=InlineKeyboardMarkup(
                        [
                            [
                                InlineKeyboardButton(
                                    "↩️返回存储管理", callback_data="ns_re_menu"
                                )
                            ]
                        ]
                    ),
                )
        else:
            await message_tj.edit(
                text=name + "添加失败！\n——————————\n" + ns_json["message"],
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                "↩️返回存储管理", callback_data="ns_re_menu"
                            )
                        ]
                    ]
                ),
            )

    chat_data["ns_a"] = False
    chat_data["chat_id"] = message.chat.id
    chat_data["message_id"] = message.id


# 新建存储_批量模式_处理用户发送的配置
ns_new_b_list = []  # 解析后的配置
message_text_list = []  # 用户发送的配置
ns_new_b_message_id = {}  # 存储消息id和消息内容


@Client.on_message(filters.text & filters.private & ns_b_filter & is_admin)
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
            f"添加失败！\n——————————\n请检查配置后重新发送：\n{message_text}\n\n错误Key：\n{str(user_cfg_code)}"
        )
        text = ""
        for i in range(len(message_text_list)):
            textt = f"{i + 1}、\n<code>{str(message_text_list[i])}</code>\n\n"
            text += textt
        await message.delete()
        try:
            await client.edit_message_text(
                chat_id=message.chat.id,
                message_id=chat_data["ns_mode_b_message_2_message_id"],
                text=f"已添加的配置：\n{str(text)}",
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                "↩️返回存储列表", callback_data="ns_re_list_mode_b"
                            )
                        ]
                    ]
                ),
            )
        except Exception as e:
            logger.info(e)
        message_text_list.pop()

    chat_data["chat_id"] = message.chat.id
    chat_data["message_id"] = message.id

    return


# 撤销添加的配置
@Client.on_callback_query(filters.regex("^ns_re$"))
async def ns_remove(client: Client, query: CallbackQuery):
    message_text_list.pop()
    ns_new_b_list.pop()
    await ns_r(client, query)


# 新建存储_刷新已添加的存储
async def ns_r(client: Client, message: Union[Message, CallbackQuery]):
    text = ""
    for i in range(len(ns_new_b_list)):
        textt = f"{i + 1}、\n<code>{str(message_text_list[i])}</code>\n\n"
        text += textt
    button = [
        [
            InlineKeyboardButton("🔄撤销", callback_data="ns_re"),
            InlineKeyboardButton("↩️返回", callback_data="ns_re_list_mode_b"),
        ],
        [InlineKeyboardButton("🎉开始新建", callback_data="ns_sp")],
    ]
    ns_r_text = await client.edit_message_text(
        chat_id=(
            message.chat.id if isinstance(message, Message) else message.message.chat.id
        ),
        message_id=chat_data["ns_mode_b_message_2_message_id"],
        text="已添加的配置：\n" + str(text),
        reply_markup=InlineKeyboardMarkup(button),
    )
    ns_new_b_message_id["text"] = ns_r_text.text


# 开始批量新建存储
@Client.on_callback_query(filters.regex("^ns_sp$"))
async def ns_new_b_start(client: Client, query: CallbackQuery):
    chat_data["ns_b"] = False
    message_b = []
    await client.edit_message_text(
        chat_id=query.message.chat.id,
        message_id=chat_data["ns_mode_b_message_2_message_id"],
        text=f'<code>{ns_new_b_message_id["text"]}</code>',
    )
    ns_b_message_tj = await query.message.reply("开始添加存储")
    text = ""
    for i in range(len(ns_new_b_list)):
        st_cfg = ns_new_b_list[i]
        ns_body = remove_quotes(st_cfg)
        ns_json = await alist.storage_create(ns_body)  # 新建存储
        mount_path = ns_new_b_list[i]["mount_path"]
        if ns_json.code == 200:
            message_b.append(f"`{mount_path}` | 添加成功！")
        elif (
            ns_json.code == 500 and "but storage is already created" in ns_json.message
        ):  # 初始化存储失败，但存储已经创建
            storage_id = str(ns_json.data["id"])
            st_info = await alist.storage_get(storage_id)  # 查询指定存储信息
            ns_up_json = await alist.storage_update(st_info.data)  # 更新存储
            if ns_up_json.code == 200:
                message_b.append(f"`{mount_path}` | 添加成功！")
            else:
                message_b.append(
                    f"{mount_path} 添加失败！\n——————————\n{ns_up_json}\n——————————"
                )
        elif (
            ns_json.code == 500 and "1062 (23000)" in ns_json.message
        ):  # 存储路径已存在
            message_b.append(
                f"{mount_path} 添加失败！\n——————————\n{ns_json.message}\n——————————"
            )
        else:
            message_b.append(
                f"{mount_path} 添加失败！\n——————————\n{ns_json.message}\n——————————"
            )
        textt = f"{message_b[i]}\n"
        text += textt
        ns_new_bb_start = await ns_b_message_tj.edit(
            text=text,
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "↩️︎返回存储管理", callback_data="ns_re_new_b_menu"
                        )
                    ]
                ]
            ),
        )
        chat_data["ns_new_b_start_chat_id"] = ns_new_bb_start.chat.id
        chat_data["ns_new_b_start_message_id"] = ns_new_bb_start.id

    ns_new_b_list.clear()
    message_text_list.clear()

# -*- coding: UTF-8 -*-
import asyncio
import json

from loguru import logger
from pyrogram import filters, Client
from pyrogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    CallbackQuery,
    Message,
)

from api.alist.alist_api import alist
from config.config import st_cfg, chat_data
from tools.filters import is_admin
from tools.utils import translate_key

mount_path = []  # 存储路径
disabled = []  # 存储是否禁用
driver_id = []  # 存储id
ns_button_list = []  # 支持添加的存储的按钮
button_list = []
common_dict = {}  # 新建存储——新建存储的json模板

with open("module/storage/cn_dict.json", "r", encoding="utf-8") as c:
    text_dict = json.load(c)

#####################################################################################
#####################################################################################
# 返回菜单
return_button = [
    InlineKeyboardButton("↩️返回存储管理", callback_data="re_st_menu"),
    InlineKeyboardButton("❌关闭菜单", callback_data="st_close"),
]

st_button = [
    [InlineKeyboardButton("⬆️自动排序", callback_data="auto_sorting")],
    [
        InlineKeyboardButton("⏯开关存储", callback_data="st_vs"),
        InlineKeyboardButton("📋复制存储", callback_data="st_cs"),
    ],
    [
        InlineKeyboardButton("🆕新建存储", callback_data="st_ns"),
        InlineKeyboardButton("🗑️删除存储", callback_data="st_ds"),
    ],
    [
        InlineKeyboardButton("📋复制存储配置", callback_data="st_storage_copy_list"),
        InlineKeyboardButton("🛠️修改默认配置", callback_data="st_storage_amend"),
    ],
    [InlineKeyboardButton("❌关闭菜单", callback_data="st_close")],
]

vs_all_button = [
    InlineKeyboardButton("✅开启全部存储", callback_data="vs_onall"),
    InlineKeyboardButton("❌关闭全部存储", callback_data="vs_offall"),
]


#####################################################################################
# 按钮回调
#####################################################################################
# 返回存储管理菜单
@Client.on_callback_query(filters.regex(r"^re_st_menu$"))
async def st_return_callback(_, __):
    chat_data["st_storage_cfg_amend"] = False
    await st_return()


# 关闭存储管理菜单
@Client.on_callback_query(filters.regex(r"^st_close$"))
async def st_close(_, __):
    await chat_data["storage_menu_button"].edit("已退出『存储管理』")


#####################################################################################
#####################################################################################


async def st_aaa():
    try:
        st_info_list = (await alist.storage_list()).data
    except Exception:
        text = "连接Alist超时，请检查网站状态"
        logger.error(text)
        return text
    else:
        zcc = len(st_info_list)
        jysl = sum(bool(item.disabled) for item in st_info_list)
        qysl = zcc - jysl
        return f"存储数量：{zcc}\n启用：{qysl}\n禁用：{jysl}"


# 存储管理菜单
@Client.on_message(filters.command("st") & filters.private & is_admin)
async def st(_, message: Message):
    storage_menu_button = await message.reply(
        text=await st_aaa(), reply_markup=InlineKeyboardMarkup(st_button)
    )
    chat_data["storage_menu_button"]: Message = storage_menu_button


# 返回存储管理菜单
async def st_return():
    await chat_data["storage_menu_button"].edit(
        text=await st_aaa(), reply_markup=InlineKeyboardMarkup(st_button)
    )


# 修改存储默认配置
@Client.on_callback_query(filters.regex(r"^st_storage_amend$"))
async def st_storage_amend(_, __):
    t = translate_key(
        translate_key(st_cfg.storage, text_dict["common"]),
        text_dict["additional"],
    )
    t = json.dumps(t, indent=4, ensure_ascii=False)

    button = [
        [InlineKeyboardButton("🔧修改配置", callback_data="st_storage_cfg_amend")],
        [InlineKeyboardButton("↩️返回存储管理", callback_data="re_st_menu")],
    ]

    await chat_data["storage_menu_button"].edit(
        text=f"当前配置：\n<code>{t}</code>", reply_markup=InlineKeyboardMarkup(button)
    )


#####################################################################################
#####################################################################################


# 自动排序
@Client.on_callback_query(filters.regex(r"auto_sorting"))
async def auto_sorting(_, query: CallbackQuery):
    st_list = (await alist.storage_list()).data
    st_list.sort(key=lambda x: x.mount_path)
    await query.message.edit_text("排序中...")

    task = []
    for i, v in enumerate(st_list):
        v.order = i
        task.append(alist.storage_update(v))
    results = await asyncio.gather(*task, return_exceptions=True)
    for result in results:
        if isinstance(result, Exception):
            logger.error(f"排序失败：{result}")
    return await st_return()


# 删除用户和bot的信息
async def ns_mode_b_delete(client: Client):
    await client.delete_messages(
        chat_id=chat_data["ns_new_b_start_chat_id"],
        message_ids=chat_data["ns_new_b_start_message_id"],
    )
    await client.delete_messages(
        chat_id=chat_data["ns_mode_b_message_2_chat_id"],
        message_ids=chat_data["ns_mode_b_message_2_message_id"],
    )


# 删除用户和bot的信息
async def ns_re_list_mode_b(client: Client):
    await client.delete_messages(
        chat_id=chat_data["ns_mode_b_message_2_chat_id"],
        message_ids=chat_data["ns_mode_b_message_2_message_id"],
    )


#####################################################################################
#####################################################################################


# 解析用户发送的存储配置，返回解析后的配置和状态码
async def user_cfg(message_text):  # sourcery skip: dict-assign-update-to-union
    message_config = {"addition": {}}  # 解析用户发送的配置
    new_dict = {v: k for k, v in text_dict["common"].items()}  # 调换common键和值的位置
    new_add_dict = {
        v: k for k, v in text_dict["additional"].items()
    }  # 调换additional键和值的位置
    new_dict.update(new_add_dict)  # 合并调换位置后的common，additional
    try:
        user_cfg_code = 200
        for i in message_text.split("\n"):
            k = i.split("=")[0].strip(" * ")
            l_i = new_dict.get(k, k)
            r_i = i.split("=")[1].replace(" ", "")
            if r_i == "True":
                r_i = "true"
            elif r_i == "False":
                r_i = "false"
            if l_i in text_dict["common"]:
                message_config[l_i] = r_i
            else:
                message_config["addition"][l_i] = r_i
    except (KeyError, IndexError) as e:
        user_cfg_code = e
    else:
        common_dict["addition"].update(message_config["addition"])
        message_config["addition"].update(common_dict["addition"])
        common_dict.update(message_config)  # 将用户发送的配置更新到默认配置
        common_dict["addition"] = f"""{json.dumps(common_dict['addition'])}"""
    return common_dict, user_cfg_code


# 获取存储并写入列表
async def get_storage(callback_data_pr):
    mount_path.clear()
    disabled.clear()
    driver_id.clear()
    button_list.clear()

    vs_data = (await alist.storage_list()).data  # 获取存储列表

    for item in vs_data:
        mount_path.append(item.mount_path)
        disabled.append(item.disabled)
        driver_id.append(item.id)

    for button_js in range(len(mount_path)):
        disabled_a = "❌" if disabled[button_js] else "✅"

        # 添加存储按钮
        storage_button = [
            InlineKeyboardButton(
                disabled_a + mount_path[button_js],
                callback_data=callback_data_pr + str(button_js),
            )
        ]
        button_list.append(storage_button)

    if driver_id[7:]:
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
                if obj.lower() == "true":
                    return True
                elif obj.lower() == "false":
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
    common_dict["driver"] = driver_name  # 将驱动名称加入字典
    stj = (await alist.driver_list()).data

    def common_c(vl):
        for i in range(len(stj[storage_name][vl])):
            stj_name = stj[storage_name][vl][int(i)]["name"]  # 存储配置名称
            stj_bool = stj[storage_name][vl][int(i)]["type"]
            stj_default = (
                stj[storage_name][vl][int(i)]["default"]
                if stj_bool != "bool"
                else "false"
            )  # 存储配置默认值
            stj_options = stj[storage_name][vl][int(i)]["options"]  # 存储配置可选选项
            stj_required = stj[storage_name][vl][int(i)]["required"]  # 是否必填
            cr = "*" if stj_required else ""
            co = f"({stj_options})" if stj_options else ""
            if vl == "common":
                common_dict[stj_name] = stj_default
            else:
                additional_dict[stj_name] = (
                    stj_default  # 将存储配置名称和默认值写入字典
                )
            sn = text_dict[vl].get(stj_name, stj_name)
            default_storage_config.append(f"{sn} = {stj_default}")
            storage = st_cfg.storage
            try:
                for k in storage.keys():
                    if k in text_dict["common"].keys():
                        common_dict[k] = storage[k]
                    else:
                        additional_dict[k] = storage[k]
            except (AttributeError, KeyError):
                ...
            if vl == "common":
                default_storage_config_message.append(
                    f"""{cr}{sn} = {common_dict[stj_name]} {co}"""
                )  # 发给用户的模板
            else:
                default_storage_config_message.append(
                    f"""{cr}{sn} = {additional_dict[stj_name]} {co}"""
                )  # 发给用户的模板

    common_c(vl="common")
    common_c(vl="additional")

    common_dict["addition"] = additional_dict  # 将additional添加到common
    common_dict_json = json.dumps(common_dict, ensure_ascii=False)
    default_storage_config_message = [
        f"{default_storage_config_message[i]}\n"
        for i in range(len(default_storage_config_message))
    ]
    text = "".join(default_storage_config_message)
    return text, common_dict_json

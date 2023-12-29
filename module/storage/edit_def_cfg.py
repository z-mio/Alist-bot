import json

from pyrogram import filters, Client
from pyrogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from config.config import write_config, chat_data, storage_cfg
from module.storage.storage import (
    st_storage_amend,
    text_dict,
)
from tool.utils import is_admin
from tool.utils import translate_key


# 取消修改默认配置
@Client.on_callback_query(filters.regex(r"^st_storage_cfg_off$"))
async def sst_storage_cfg_off_callback(_, __):
    chat_data["st_storage_cfg_amend"] = False
    await st_storage_amend("", "")


def _st_storage_cfg_amend_filter(_, __, ___):
    return bool(
        "st_storage_cfg_amend" in chat_data and chat_data["st_storage_cfg_amend"]
    )


st_storage_cfg_amend_filter = filters.create(_st_storage_cfg_amend_filter)


# 修改存储默认配置_按钮回调
@Client.on_callback_query(filters.regex(r"^st_storage_cfg_amend$"))
async def st_storage_amend_callback(_, __):
    chat_data["st_storage_cfg_amend"] = True
    t = translate_key(
        translate_key(storage_cfg()["storage"], text_dict["common"]),
        text_dict["additional"],
    )
    t = json.dumps(t, indent=4, ensure_ascii=False)
    button = [
        [InlineKeyboardButton("❌取消修改", callback_data="st_storage_cfg_off")],
        [InlineKeyboardButton("↩️返回存储管理", callback_data="st_return")],
    ]
    text = f"""当前配置：
<code>{t}</code>

支持的选项：<a href="https://telegra.ph/驱动字典-03-20">点击查看</a>
先复制当前配置，修改后发送

格式（Json）：
1、每行前面要添加4个空格
2、除了最后一行，每行后面都要添加英文逗号“,”

"""
    await chat_data["storage_menu_button"].edit(
        text=text,
        reply_markup=InlineKeyboardMarkup(button),
        disable_web_page_preview=True,
    )


# 修改默认存储配置
@Client.on_message(
    filters.text & filters.private & st_storage_cfg_amend_filter & is_admin
)
async def st_storage_cfg_amend(client: Client, message: Message):
    message_text = message.text
    await client.delete_messages(
        chat_id=chat_data["chat_id"], message_ids=chat_data["message_id"]
    )
    button = [
        [InlineKeyboardButton("🔄重新修改", callback_data="st_storage_cfg_amend")],
        [InlineKeyboardButton("↩️返回存储管理", callback_data="st_return")],
    ]
    try:
        message_text = json.loads(message_text)
    except json.decoder.JSONDecodeError as z:
        await chat_data["storage_menu_button"].edit(
            text=f"配置错误\n——————————\n请检查配置:\n<code>{message_text}</code>\n{z}",
            reply_markup=InlineKeyboardMarkup(button),
        )
    else:
        new_dict = {v: k for k, v in text_dict["common"].items()}  # 调换common键和值的位置
        new_add_dict = {
            v: k for k, v in text_dict["additional"].items()
        }  # 调换additional键和值的位置
        new_dict |= new_add_dict
        t = translate_key(message_text, new_dict)
        t_d = {"storage": t}
        write_config("config/storage_cfg.yaml", t_d)
        await st_storage_amend("", "")

    chat_data["st_storage_cfg_amend"] = False
    chat_data["chat_id"] = message.chat.id
    chat_data["message_id"] = message.id

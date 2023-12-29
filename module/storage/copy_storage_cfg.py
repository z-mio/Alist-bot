import json

from pyrogram import filters, Client
from pyrogram.types import (
    InlineKeyboardMarkup,
    CallbackQuery,
)

from api.alist_api import AListAPI
from config.config import chat_data
from module.storage.storage import (
    get_storage,
    button_list,
    driver_id,
    text_dict,
)
from tool.utils import is_admin
from tool.utils import translate_key


# 发送 复制存储配置 按钮列表
@Client.on_callback_query(filters.regex(r"^st_storage_copy_list$"))
async def st_storage_copy_list(_, __):
    await get_storage(callback_data_pr="st_storage_copy_cfg")
    await chat_data["storage_menu_button"].edit(
        text="点击复制存储配置：", reply_markup=InlineKeyboardMarkup(button_list)
    )


# 复制存储配置
@Client.on_callback_query(filters.regex(r"^st_storage_copy_cfg") & is_admin)
async def st_storage_copy_cfg(_, query: CallbackQuery):
    bvj = int(query.data.strip("st_storage_copy_cfg"))
    get = await AListAPI.storage_get(driver_id[bvj])
    get_a, get_b = get["data"], json.loads(get["data"]["addition"])

    get_a = translate_key(
        translate_key(get_a, text_dict["common"]), text_dict["additional"]
    )
    get_b = translate_key(
        translate_key(get_b, text_dict["common"]), text_dict["additional"]
    )
    get_a.update(get_b)
    delete = ["额外信息", "状态", "修改时间", "禁用", "id", "驱动", "是否Sharepoint", "AccessToken"]
    for i in delete:
        try:
            get_a.pop(i)
        except KeyError:
            ...
    get_a["备注"] = get_a["备注"].replace("\n", " ")
    text_list = [f"{i} = {get_a[i]}\n" for i in get_a.keys()]
    text = "".join(text_list)
    await chat_data["storage_menu_button"].edit(
        text=f"<code>{text}</code>",
        reply_markup=InlineKeyboardMarkup(button_list),
        disable_web_page_preview=True,
    )

from pyrogram import filters, Client
from pyrogram.types import (
    InlineKeyboardMarkup,
    CallbackQuery,
)

from api.alist_api import AListAPI
from config.config import chat_data
from module.storage.storage import get_storage, mount_path, driver_id, button_list


# 发送 删除存储 按钮列表
@Client.on_callback_query(filters.regex(r"^st_ds$"))
async def ds(_, __):
    await get_storage(callback_data_pr="ds")
    await chat_data["storage_menu_button"].edit(
        text="点击删除存储\n存储列表：", reply_markup=InlineKeyboardMarkup(button_list)
    )


# 删除存储
@Client.on_callback_query(filters.regex("^ds"))
async def ds_callback(_, query: CallbackQuery):
    bvj = int(query.data.strip("ds"))
    await AListAPI.storage_delete(driver_id[bvj])
    st_id = mount_path[bvj]
    await get_storage(callback_data_pr="ds")
    await chat_data["storage_menu_button"].edit(
        text=f"🗑已删除存储：`{st_id}`", reply_markup=InlineKeyboardMarkup(button_list)
    )

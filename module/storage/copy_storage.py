import datetime
import re

from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, CallbackQuery

from api.alist.alist_api import alist
from config.config import chat_data
from module.storage.storage import (
    get_storage,
    button_list,
    driver_id,
    mount_path,
)


# 发送 复制存储 按钮列表
@Client.on_callback_query(filters.regex(r"^st_cs$"))
async def cs(_, __):
    await get_storage(callback_data_pr="cs")
    await chat_data["storage_menu_button"].edit(
        text="点击复制存储\n存储列表：", reply_markup=InlineKeyboardMarkup(button_list)
    )


# 复制存储
@Client.on_callback_query(filters.regex("^cs"))
async def cs_callback(_, query: CallbackQuery):
    bvj = int(query.data.strip("cs"))
    storage_id = str(driver_id[bvj])
    st = (await alist.storage_get(storage_id)).data  # 获取存储
    del st.id  # 删除存储id
    now = datetime.datetime.now()
    current_time = now.strftime("%M%S")  # 获取当前时间

    cs_mount_path = st.mount_path
    cs_order = st.order
    if ".balance" not in cs_mount_path:  # 修改存储的mount_path
        st.mount_path = f"{cs_mount_path}.balance{current_time}"
    else:
        cs_mount_path_text = re.sub(".balance.*", "", cs_mount_path)
        st.mount_path = f"{cs_mount_path_text}.balance{current_time}"
    st.order = cs_order + 1  # 基于当前配置的排序加1

    await alist.storage_create(st)  # 新建存储

    await get_storage(callback_data_pr="cs")
    await chat_data["storage_menu_button"].edit(
        text=f"已复制\n`{mount_path[bvj]}` -> `{st.mount_path}`",
        reply_markup=InlineKeyboardMarkup(button_list),
    )

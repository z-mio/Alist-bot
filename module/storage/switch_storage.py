import asyncio

from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, CallbackQuery

from api.alist_api import AListAPI
from config.config import chat_data
from module.storage.storage import (
    get_storage,
    button_list,
    vs_all_button,
    driver_id,
    disabled,
    mount_path,
)


def insert_button():
    if button_list[5:]:
        if button_list[8:]:
            button_list.insert(1, vs_all_button)
        button_list.insert(-1, vs_all_button)


# 发送 开关存储 按钮列表
@Client.on_callback_query(filters.regex(r"^st_vs$"))
async def vs(_, __):
    await get_storage(callback_data_pr="vs")
    insert_button()
    await chat_data["storage_menu_button"].edit(
        text="点击开启/关闭存储\n存储列表：", reply_markup=InlineKeyboardMarkup(button_list)
    )


# 开启关闭存储
@Client.on_callback_query(filters.regex(r"^vs\d"))
async def vs_callback(_, query: CallbackQuery):
    bvj = int(query.data.strip("vs"))
    storage_id = driver_id[bvj]
    if disabled[bvj]:
        of_t = "✅已开启存储："
        await AListAPI.storage_enable(storage_id)
    else:
        of_t = "❌已关闭存储："
        await AListAPI.storage_disable(storage_id)
    await get_storage(callback_data_pr="vs")
    insert_button()
    await chat_data["storage_menu_button"].edit(
        text=f"{of_t}`{mount_path[bvj]}`", reply_markup=InlineKeyboardMarkup(button_list)
    )


# 开启&关闭全部存储
@Client.on_callback_query(filters.regex(r"vs_offall|vs_onall"))
async def vs_on_off_all(_, query: CallbackQuery):
    bvj = query.data
    command = AListAPI.storage_enable if bvj == "vs_onall" else AListAPI.storage_disable
    action = "开启中..." if bvj == "vs_onall" else "关闭中..."
    await chat_data["storage_menu_button"].edit(
        text=action, reply_markup=InlineKeyboardMarkup(button_list)
    )

    task = [command(driver_id[i]) for i, is_disabled in enumerate(disabled)]
    await asyncio.gather(*task, return_exceptions=True)
    await get_storage(callback_data_pr="vs")
    insert_button()
    await chat_data["storage_menu_button"].edit(
        text="完成！", reply_markup=InlineKeyboardMarkup(button_list)
    )

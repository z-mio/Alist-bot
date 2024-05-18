# -*- coding: UTF-8 -*-
import os
from typing import Literal
from urllib import parse

import httpx

from config.config import alist_host, alist_token

useragent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36"


class AListAPI:
    @staticmethod
    async def _send_request(
        method: Literal["GET", "POST", "PUT"],
        url,
        headers=None,
        json=None,
        params=None,
        data=None,
        timeout=10,
    ):
        async with httpx.AsyncClient() as client:
            if method == "GET":
                response = await client.get(
                    url, headers=headers, params=params, timeout=timeout
                )
            elif method == "POST":
                response = await client.post(
                    url, headers=headers, json=json, timeout=timeout
                )
            elif method == "PUT":
                response = await client.put(
                    url, headers=headers, data=data, timeout=timeout
                )
            return response.json()

    # 搜索文件
    @staticmethod
    async def search(file_name, page: int = 1, per_page: int = 100):
        url = f"{alist_host}/api/fs/search"
        header = {
            "Authorization": alist_token,
        }
        body = {
            "parent": "/",
            "keywords": file_name,
            "page": page,
            "per_page": per_page,
        }
        return await AListAPI._send_request("POST", url, headers=header, json=body)

    # 获取下载信息
    @staticmethod
    async def fs_get(path):
        url = f"{alist_host}/api/fs/get"
        header = {"Authorization": alist_token, "Cache-Control": "no-cache"}
        body = {"path": path}
        return await AListAPI._send_request("POST", url, headers=header, json=body)

    # 查询指定存储信息
    @staticmethod
    async def storage_get(storage_id):
        url = f"{alist_host}/api/admin/storage/get?id={str(storage_id)}"
        header = {"Authorization": alist_token}
        return await AListAPI._send_request("GET", url, headers=header)

    # 新建存储
    @staticmethod
    async def storage_create(body):
        url = f"{alist_host}/api/admin/storage/create"
        header = {
            "UserAgent": useragent,
            "Content-Type": "application/json",
            "Authorization": alist_token,
        }
        return await AListAPI._send_request("POST", url, headers=header, json=body)

    # 更新存储
    @staticmethod
    async def storage_update(body):
        url = f"{alist_host}/api/admin/storage/update"
        header = {"Authorization": alist_token}
        return await AListAPI._send_request("POST", url, headers=header, json=body)

    # 获取存储列表
    @staticmethod
    async def storage_list():
        url = f"{alist_host}/api/admin/storage/list"
        header = {
            "Authorization": alist_token,
        }
        return await AListAPI._send_request("GET", url, headers=header)

    # 获取存储列表
    @staticmethod
    def storage_list_():
        url = f"{alist_host}/api/admin/storage/list"
        header = {
            "Authorization": alist_token,
        }
        result = httpx.get(url, headers=header, timeout=10)
        return result.json()

    # 删除指定存储
    @staticmethod
    async def storage_delete(storage_id):
        url = f"{alist_host}/api/admin/storage/delete?id={str(storage_id)}"
        header = {"Authorization": alist_token}
        return await AListAPI._send_request("POST", url, headers=header)

    # 开启存储
    @staticmethod
    async def storage_enable(storage_id):
        url = f"{alist_host}/api/admin/storage/enable?id={str(storage_id)}"
        header = {"Authorization": alist_token}
        return await AListAPI._send_request("POST", url, headers=header)

    # 关闭存储
    @staticmethod
    async def storage_disable(storage_id):
        url = f"{alist_host}/api/admin/storage/disable?id={str(storage_id)}"
        header = {"Authorization": alist_token}
        return await AListAPI._send_request("POST", url, headers=header)

    # 上传文件
    @staticmethod
    async def upload(local_path, remote_path, file_name, as_task: bool = "false"):
        url = f"{alist_host}/api/fs/put"
        header = {
            "UserAgent": useragent,
            "As-Task": as_task,
            "Authorization": alist_token,
            "File-Path": parse.quote(f"{remote_path}/{file_name}"),
            "Content-Length": f"{os.path.getsize(local_path)}",
        }
        return await AListAPI._send_request(
            "PUT", url, headers=header, data=open(local_path, "rb").read()
        )

    # 获取列表，强制刷新列表
    @staticmethod
    async def refresh_list(path, per_page: int = 0):
        url = f"{alist_host}/api/fs/list"
        header = {"Authorization": alist_token}
        body = {"path": path, "page": 1, "per_page": per_page, "refresh": True}
        return await AListAPI._send_request("POST", url, headers=header, json=body)

    # 获取驱动列表
    @staticmethod
    async def get_driver():
        url = f"{alist_host}/api/admin/driver/list"
        header = {"Authorization": alist_token}
        return await AListAPI._send_request("GET", url, headers=header)

    # 获取离线下载工具
    @staticmethod
    async def get_offline_download_tools():
        url = f"{alist_host}/api/public/offline_download_tools"
        header = {"Authorization": alist_token}
        return await AListAPI._send_request("GET", url, headers=header)

    # 离线下载
    @staticmethod
    async def offline_download(urls, tool, path, delete_policy):
        url = f"{alist_host}/api/fs/add_offline_download"
        header = {"Authorization": alist_token}
        body = {"delete_policy": delete_policy, "path": path, "tool": tool, "urls": urls}
        return await AListAPI._send_request("POST", url, headers=header, json=body)

    # 获取离线下载未完成任务
    @staticmethod
    async def get_offline_download_undone_task():
        url = f"{alist_host}/api/admin/task/offline_download/undone"
        header = {"Authorization": alist_token}
        return await AListAPI._send_request("GET", url, headers=header)

    # 获取离线下载已完成任务
    @staticmethod
    async def get_offline_download_done_task():
        url = f"{alist_host}/api/admin/task/offline_download/done"
        header = {"Authorization": alist_token}
        return await AListAPI._send_request("GET", url, headers=header)

    # 清空离线下载已完成任务（包含成功/失败）
    @staticmethod
    async def clear_offline_download_done_task():
        url = f"{alist_host}/api/admin/task/offline_download/clear_done"
        header = {"Authorization": alist_token}
        return await AListAPI._send_request("POST", url, headers=header)

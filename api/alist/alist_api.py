# -*- coding: UTF-8 -*-
import base64
import hashlib
import hmac
import os
from typing import Literal, Type, Dict, Any
from urllib import parse
from urllib.parse import urljoin

import httpx

from api.alist.base import *
from api.alist.base.base import AListAPIResponse, T
from config.config import bot_cfg

useragent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36"


class AListAPI:
    def __init__(self, host, token):
        self.host = host
        self.token = token

        self.headers = {
            "UserAgent": useragent,
            "Content-Type": "application/json",
            "Authorization": self.token,
        }

    async def _request(
        self,
        method: Literal["GET", "POST", "PUT"],
        url,
        *,
        data_class: Type[T] = None,
        headers: Dict[str, str] = None,
        json: Dict[str, Any] = None,
        params: Dict[str, Any] = None,
        data: Any = None,
        timeout: int = 10,
    ) -> AListAPIResponse[T]:
        url = urljoin(self.host, url)
        headers = self.headers if headers is None else headers

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
        response.raise_for_status()
        result = response.json()
        return AListAPIResponse.from_dict(result, data_class)

    async def search(
        self,
        keywords,
        page: int = 1,
        per_page: int = 100,
        parent: str = "/",
        scope: int = 0,
        password: str = "",
    ):
        """搜索文件"""
        body = {
            "parent": parent,
            "keywords": keywords,
            "scope": scope,
            "page": page,
            "per_page": per_page,
            "password": password,
        }
        return await self._request(
            "POST", "/api/fs/search", data_class=SearchResultData, json=body
        )

    async def fs_get(self, path):
        """获取下载信息"""
        return await self._request(
            "POST", "/api/fs/get", data_class=FileInfo, json={"path": path}
        )

    async def storage_get(self, storage_id):
        """查询指定存储信息"""
        url = f"/api/admin/storage/get?id={storage_id}"
        return await self._request("GET", url, data_class=StorageInfo)

    async def storage_create(self, body: StorageInfo | dict):
        """新建存储"""
        url = "/api/admin/storage/create"
        if isinstance(body, dict):
            body = StorageInfo.from_dict(body)
        return await self._request("POST", url, json=body.to_dict())

    async def storage_update(self, body: StorageInfo):
        """更新存储"""
        url = "/api/admin/storage/update"
        if isinstance(body, dict):
            body = StorageInfo.from_dict(body)
        return await self._request("POST", url, json=body.to_dict())

    async def storage_list(self):
        """获取存储列表"""
        url = "/api/admin/storage/list"
        return await self._request("GET", url, data_class=StorageInfo)

    async def storage_delete(self, storage_id) -> AListAPIResponse:
        """删除指定存储"""
        url = f"/api/admin/storage/delete?id={str(storage_id)}"
        return await self._request("POST", url)

    async def storage_enable(self, storage_id) -> AListAPIResponse:
        """开启存储"""
        url = f"/api/admin/storage/enable?id={str(storage_id)}"
        return await self._request("POST", url)

    async def storage_disable(self, storage_id) -> AListAPIResponse:
        """关闭存储"""
        url = f"/api/admin/storage/disable?id={str(storage_id)}"
        return await self._request("POST", url)

    async def upload(
        self,
        local_path,
        remote_path,
        file_name,
        as_task: Literal["true", "false"] = "false",
    ):
        """上传文件"""
        url = "/api/fs/put"
        header = {
            "UserAgent": useragent,
            "As-Task": as_task,
            "Authorization": self.token,
            "File-Path": parse.quote(f"{remote_path}/{file_name}"),
            "Content-Length": f"{os.path.getsize(local_path)}",
        }
        return await self._request(
            "PUT",
            url,
            # data_class=UploadTaskResult,
            headers=header,
            data=open(local_path, "rb").read(),
        )

    async def fs_list(self, path, per_page: int = 0):
        """获取列表，强制刷新列表"""
        url = "/api/fs/list"
        body = {"path": path, "page": 1, "per_page": per_page, "refresh": True}
        return await self._request("POST", url, json=body)

    async def driver_list(self):
        """获取驱动列表"""
        url = "/api/admin/driver/list"
        return await self._request("GET", url)

    async def setting_list(self):
        """获取设置列表"""
        url = "/api/admin/setting/list"
        return await self._request("GET", url, data_class=SettingInfo)

    async def user_list(self):
        """获取用户列表"""
        url = "/api/admin/user/list"
        return await self._request("GET", url, data_class=UserInfo)

    async def meta_list(self):
        """获取元信息列表"""
        url = "/api/admin/meta/list"
        return await self._request("GET", url, data_class=MetaInfo)

    async def setting_get(self, key):
        """获取某项设置"""
        url = "/api/admin/setting/get"
        params = {"key": key}
        return await self._request("GET", url, data_class=SettingInfo, params=params)

    async def get_offline_download_tools(self):
        """获取离线下载工具"""
        url = "/api/public/offline_download_tools"
        return await self._request("GET", url)

    async def add_offline_download(self, urls, tool, path, delete_policy):
        """离线下载"""
        url = "/api/fs/add_offline_download"
        body = {
            "delete_policy": delete_policy,
            "path": path,
            "tool": tool,
            "urls": urls,
        }
        return await self._request("POST", url, json=body)

    async def get_offline_download_undone_task(self):
        """获取离线下载未完成任务"""
        url = "/api/admin/task/offline_download/undone"
        return await self._request("GET", url)

    async def get_offline_download_done_task(self):
        """获取离线下载已完成任务"""
        url = "/api/admin/task/offline_download/done"
        return await self._request("GET", url)

    async def clear_offline_download_done_task(self):
        """清空离线下载已完成任务（包含成功/失败）"""
        url = "/api/admin/task/offline_download/clear_done"
        return await self._request("POST", url)

    @staticmethod
    def sign(path) -> str:
        """计算签名"""
        expire_time_stamp = "0"
        to_sign = f"{path}:{expire_time_stamp}"
        signature = hmac.new(
            bot_cfg.alist_token.encode(), to_sign.encode(), hashlib.sha256
        ).digest()
        _safe_base64 = base64.urlsafe_b64encode(signature).decode()
        return f"{_safe_base64}:{expire_time_stamp}"


alist = AListAPI(bot_cfg.alist_host, bot_cfg.alist_token)

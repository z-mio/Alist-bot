# -*- coding: UTF-8 -*-
import json
import os
from urllib import parse

import requests

from config.config import alist_host, alist_token


# 搜索文件
def search(file_name, per_page):
    url = f'{alist_host}/api/fs/search'
    header = {"Authorization": alist_token, }
    body = {"parent": "/",
            "keywords": file_name,
            "page": 1,
            "per_page": per_page
            }

    return requests.post(url, json=body, headers=header, timeout=10)


# 获取下载信息
def fs_get(path):
    url = f'{alist_host}/api/fs/get'
    header = {"Authorization": alist_token,
              'Cache-Control': 'no-cache'
              }
    body = {"path": path}
    return requests.post(url, json=body, headers=header, timeout=10)


# 查询指定存储信息
def storage_get(storage_id):
    url = f'{alist_host}/api/admin/storage/get?id={str(storage_id)}'
    header = {"Authorization": alist_token}

    return requests.get(url, headers=header, timeout=10)


# 新建存储
def storage_create(body):
    url = f'{alist_host}/api/admin/storage/create'
    header = {'Authorization': alist_token}

    return requests.post(url, json=body, headers=header, timeout=10)


# 更新存储
def storage_update(body):
    url = f'{alist_host}/api/admin/storage/update'
    header = {"Authorization": alist_token}

    return requests.post(url, json=body, headers=header, timeout=10)


# 获取存储列表
def storage_list():
    url = f'{alist_host}/api/admin/storage/list'
    header = {"Authorization": alist_token, }

    return requests.get(url, headers=header, timeout=10)


# 删除指定存储
def storage_delete(storage_id):
    url = f'{alist_host}/api/admin/storage/delete?id={str(storage_id)}'
    header = {"Authorization": alist_token}

    return requests.post(url, headers=header, timeout=10)


# 开启存储
def storage_enable(storage_id):
    url = f'{alist_host}/api/admin/storage/enable?id={str(storage_id)}'
    header = {"Authorization": alist_token}

    return requests.post(url, headers=header, timeout=10)


# 关闭存储
def storage_disable(storage_id):
    url = f'{alist_host}/api/admin/storage/disable?id={str(storage_id)}'
    header = {"Authorization": alist_token}

    return requests.post(url, headers=header, timeout=10)


# 上传文件
# https://github.com/lym12321/Alist-SDK/blob/dde4bcc74893f9e62281482a2395abe9a1dd8d15/alist.py#L67

def upload(local_path, remote_path, file_name):
    useragent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36'
    url = f'{alist_host}/api/fs/put'
    header = {
        'UserAgent': useragent,
        'Authorization': alist_token,
        'File-Path': parse.quote(f'{remote_path}/{file_name}'),
        'Content-Length': f'{os.path.getsize(local_path)}'
    }

    return json.loads(
        requests.put(url, headers=header, data=open(local_path, 'rb').read()).text)


# 获取目录列表，强制刷新

def refresh_list(path):
    url = f'{alist_host}/api/fs/list'
    header = {"Authorization": alist_token}
    body = {"path": path, "page": 1, "per_page": 0, "refresh": True}

    return requests.post(url, json=body, headers=header, timeout=10)

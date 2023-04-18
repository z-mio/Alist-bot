# -*- coding: UTF-8 -*-
import requests


# 搜索文件
def search(file_name, per_page, alist_host, alist_token):
    url = f'{alist_host}/api/fs/search'
    header = {"Authorization": alist_token, }
    body = {"parent": "/",
            "keywords": file_name,
            "page": 1,
            "per_page": per_page
            }
    return requests.post(url, json=body, headers=header)


# 获取下载信息
def fs_get(path, alist_host, alist_token):
    url = f'{alist_host}/api/fs/get'
    header = {"Authorization": alist_token,
              'Cache-Control': 'no-cache'
              }
    return requests.post(url, json=path, headers=header)


# 查询指定存储信息
def storage_get(storage_id, alist_host, alist_token):
    url = f'{alist_host}/api/admin/storage/get?id={str(storage_id)}'
    header = {"Authorization": alist_token}
    return requests.get(url, headers=header)


# 新建存储
def storage_create(body, alist_host, alist_token):
    url = f'{alist_host}/api/admin/storage/create'
    header = {'Authorization': alist_token}
    return requests.post(url, json=body, headers=header)


# 更新存储
def storage_update(body, alist_host, alist_token):
    url = f'{alist_host}/api/admin/storage/update'
    header = {"Authorization": alist_token}
    return requests.post(url, json=body, headers=header)


# 获取存储列表
def storage_list(alist_host, alist_token):
    url = f'{alist_host}/api/admin/storage/list'
    header = {"Authorization": alist_token, }
    return requests.get(url, headers=header)


# 删除指定存储
def storage_delete(storage_id, alist_host, alist_token):
    url = f'{alist_host}/api/admin/storage/delete?id={str(storage_id)}'
    header = {"Authorization": alist_token}
    return requests.post(url, headers=header)


# 开启存储
def storage_enable(storage_id, alist_host, alist_token):
    url = f'{alist_host}/api/admin/storage/enable?id={str(storage_id)}'
    header = {"Authorization": alist_token}
    return requests.post(url, headers=header)


# 关闭存储
def storage_disable(storage_id, alist_host, alist_token):
    url = f'{alist_host}/api/admin/storage/disable?id={str(storage_id)}'
    header = {"Authorization": alist_token}
    return requests.post(url, headers=header)

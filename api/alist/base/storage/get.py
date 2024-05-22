from typing import Union

from api.alist.base.base import AListAPIData


class StorageInfo(AListAPIData):
    def __init__(
        self,
        id: int,
        mount_path: str,
        order: int,
        driver: str,
        cache_expiration: int,
        status: str,
        addition: str,
        remark: str,
        modified: str,
        disabled: bool,
        order_by: str,
        order_direction: str,
        extract_folder: str,
        web_proxy: bool,
        webdav_policy: str,
        down_proxy_url: str,
    ):
        self.id = id
        self.mount_path = mount_path
        self.order = order
        self.driver = driver
        self.cache_expiration = cache_expiration
        self.status = status
        self.addition = addition
        self.remark = remark
        self.modified = modified
        self.disabled = disabled
        self.order_by = order_by
        self.order_direction = order_direction
        self.extract_folder = extract_folder
        self.web_proxy = web_proxy
        self.webdav_policy = webdav_policy
        self.down_proxy_url = down_proxy_url

    @classmethod
    def from_dict(cls, data: dict) -> Union["StorageInfo", list["StorageInfo"]]:
        return [cls.__b(i) for i in c] if (c := data.get("content")) else cls.__b(data)

    @classmethod
    def __b(cls, data: dict):
        return cls(
            id=data.get("id"),
            mount_path=data.get("mount_path"),
            order=data.get("order"),
            driver=data.get("driver"),
            cache_expiration=data.get("cache_expiration"),
            status=data.get("status"),
            addition=data.get("addition"),
            remark=data.get("remark"),
            modified=data.get("modified"),
            disabled=data.get("disabled"),
            order_by=data.get("order_by"),
            order_direction=data.get("order_direction"),
            extract_folder=data.get("extract_folder"),
            web_proxy=data.get("web_proxy"),
            webdav_policy=data.get("webdav_policy"),
            down_proxy_url=data.get("down_proxy_url"),
        )

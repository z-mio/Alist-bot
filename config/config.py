# -*- coding: UTF-8 -*-
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Any

import yaml

# 存储和检索与特定聊天相关联的数据
chat_data = {}
DOWNLOADS_PATH = Path("data/downloads")
DOWNLOADS_PATH.mkdir(parents=True, exist_ok=True)


class BaseConfig:
    def __init__(self, cfg_path):
        self.cfg_path = cfg_path
        self.config = self.load_config()
        self._key_map = {}

    def load_config(self):
        with open(self.cfg_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def save_config(self):
        with open(self.cfg_path, "w", encoding="utf-8") as f:
            yaml.dump(self.config, f, allow_unicode=True)

    def retrieve(self, key: str, default: Optional[Any] = None) -> Any:
        keys = key.split(".")
        result = self.config
        for k in keys:
            if isinstance(result, dict):
                result = result.get(k, default)
            else:
                return default
        self._key_map[keys[-1]] = key  # 保存属性名到配置路径的映射
        return result

    def modify(self, key, value):
        # 根据key和value实现修改逻辑
        keys = key.split(".")
        temp = self.config
        for k in keys[:-1]:
            temp = temp.setdefault(k, {})
        temp[keys[-1]] = value
        self.save_config()


class Config(BaseConfig):
    def __setattr__(self, key, value):
        if key in self.__dict__ and key in self._key_map:
            self.modify(self._key_map[key], value)
        super().__setattr__(key, value)


class BotConfig(Config):
    def __init__(self, cfg_path):
        super().__init__(cfg_path)
        self.admin: int = self.retrieve("user.admin")
        self.member: list = self.retrieve("user.member")
        self.bot_token = self.retrieve("user.bot_token")
        self.api_id = self.retrieve("user.api_id")
        self.api_hash = self.retrieve("user.api_hash")

        self.alist_host = self.retrieve("alist.alist_host")
        self.alist_web = self.retrieve("alist.alist_web")
        self.alist_token = self.retrieve("alist.alist_token")

        self.hostname = self.retrieve("proxy.hostname")
        self.port = self.retrieve("proxy.port")
        self.scheme = self.retrieve("proxy.scheme")

        self.backup_time = self.retrieve("backup_time")


@dataclass
class DT:
    chat: int
    time: int


class SearchConfig(Config):
    def __init__(self, cfg_path):
        super().__init__(cfg_path)
        self.per_page: int = self.retrieve("per_page")
        self.z_url: bool = self.retrieve("z_url")

    @property
    def timed_del(self) -> "DT":
        if timed_del := self.retrieve("timed_del"):
            return DT(timed_del["chat"], timed_del["time"])

    @timed_del.setter
    def timed_del(self, value: "DT"):
        self.modify("timed_del", vars(value))


class StorageConfig(Config):
    def __init__(self, cfg_path):
        super().__init__(cfg_path)
        self.storage: dict = self.retrieve("storage")


class ImageConfig(Config):
    def __init__(self, cfg_path):
        super().__init__(cfg_path)
        self.image_upload_path: str = self.retrieve("image_upload_path")
        if p := self.image_upload_path:
            self.image_upload_path = p.removeprefix("/")


@dataclass
class CloudFlareInfo:
    account_id: str
    email: str
    global_api_key: str
    url: str
    zone_id: str
    worker_name: str


class CloudflareConfig(Config):
    def __init__(self, cfg_path):
        super().__init__(cfg_path)
        self.auto_switch_nodes: bool = self.retrieve("cronjob.auto_switch_nodes")
        self.bandwidth_push: bool = self.retrieve("cronjob.bandwidth_push")
        self.chat_id: list = self.retrieve("cronjob.chat_id")
        self.status_push: bool = self.retrieve("cronjob.status_push")
        self.storage_mgmt: bool = self.retrieve("cronjob.storage_mgmt")
        self.time: str = self.retrieve("cronjob.time")

    @property
    def nodes(self) -> list[CloudFlareInfo]:
        info = self.retrieve("nodes")
        return [
            CloudFlareInfo(
                i["account_id"],
                i["email"],
                i["global_api_key"],
                i["url"],
                i["zone_id"],
                i["worker_name"],
            )
            for i in info
        ]

    def add_node(self, node_info: CloudFlareInfo):
        nodes: list = self.retrieve("nodes")
        nodes.append(vars(node_info))
        self.modify("nodes", nodes)

    def del_node(self, node_info: CloudFlareInfo):
        nodes: list = self.retrieve("nodes")
        nodes.remove(vars(node_info))
        self.modify("nodes", nodes)


class RollConfig(Config):
    def __init__(self, cfg_path):
        super().__init__(cfg_path)
        self.path = self.retrieve("path")
        self.roll_disable = self.retrieve("roll_disable")


class ProxyLoadBalance(Config):
    def __init__(self, cfg_path):
        super().__init__(cfg_path)
        self.enable = self.retrieve("enable")
        self.port = self.retrieve("port")


class OfflineDownload(Config):
    def __init__(self, cfg_path):
        super().__init__(cfg_path)
        self.download_tool = self.retrieve("download_tool")
        self.download_path = self.retrieve("download_path")
        self.download_strategy = self.retrieve("download_strategy")
        self.download_url = self.retrieve("download_url")


bot_cfg = BotConfig("config.yaml")
search_cfg = SearchConfig("config/cfg/search_cfg.yaml")
cf_cfg = CloudflareConfig("config/cfg/cloudflare_cfg.yaml")
st_cfg = StorageConfig("config/cfg/storage_cfg.yaml")
img_cfg = ImageConfig("config/cfg/image_cfg.yaml")
roll_cfg = RollConfig("config/cfg/roll_cfg.yaml")
plb_cfg = ProxyLoadBalance("config/cfg/proxy_load_balance_cfg.yaml")
od_cfg = OfflineDownload("config/cfg/offline_download_cfg.yaml")

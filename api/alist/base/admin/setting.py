from typing import Union

from api.alist.base.base import AListAPIData


class SettingInfo(AListAPIData):
    """/api/admin/setting/list"""

    def __init__(self, key, value, help, type, options, group, flag):
        self.key = key
        self.value = value
        self.help = help
        self.type = type
        self.options = options
        self.group = group
        self.flag = flag

    @classmethod
    def from_dict(cls, data: dict | list) -> Union["SettingInfo", list["SettingInfo"]]:
        return cls.__b(data) if isinstance(data, dict) else [cls.__b(i) for i in data]

    @classmethod
    def __b(cls, data: dict):
        return cls(
            key=data.get("key"),
            value=data.get("value"),
            help=data.get("help"),
            type=data.get("type"),
            options=data.get("options"),
            group=data.get("group"),
            flag=data.get("flag"),
        )

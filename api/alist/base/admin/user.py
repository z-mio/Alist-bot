from typing import Union

from api.alist.base.base import AListAPIData


class UserInfo(AListAPIData):
    """/api/admin/user/list"""

    def __init__(
        self, id, username, password, base_path, role, disabled, permission, sso_id
    ):
        self.id = id
        self.username = username
        self.password = password
        self.base_path = base_path
        self.role = role
        self.disabled = disabled
        self.permission = permission
        self.sso_id = sso_id

    @classmethod
    def from_dict(cls, data: dict) -> Union["UserInfo", list["UserInfo"]]:
        return [cls.__b(i) for i in c] if (c := data.get("content")) else cls.__b(data)

    @classmethod
    def __b(cls, data: dict):
        return cls(
            id=data.get("id"),
            username=data.get("username"),
            password=data.get("password"),
            base_path=data.get("base_path"),
            role=data.get("role"),
            disabled=data.get("disabled"),
            permission=data.get("permission"),
            sso_id=data.get("sso_id"),
        )

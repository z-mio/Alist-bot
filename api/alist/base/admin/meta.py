from typing import Union

from api.alist.base.base import AListAPIData


class MetaInfo(AListAPIData):
    """/api/admin/meta/list"""

    def __init__(
        self,
        id,
        path,
        password,
        p_sub,
        write,
        w_sub,
        hide,
        h_sub,
        readme,
        r_sub,
        header,
        header_sub,
    ):
        self.id = id
        self.path = path
        self.password = password
        self.p_sub = p_sub
        self.write = write
        self.w_sub = w_sub
        self.hide = hide
        self.h_sub = h_sub
        self.readme = readme
        self.r_sub = r_sub
        self.header = header
        self.header_sub = header_sub

    @classmethod
    def from_dict(cls, data: dict) -> Union["MetaInfo", list["MetaInfo"]]:
        return [cls.__b(i) for i in c] if (c := data.get("content")) else cls.__b(data)

    @classmethod
    def __b(cls, data: dict):
        return cls(
            id=data.get("id"),
            path=data.get("path"),
            password=data.get("password"),
            p_sub=data.get("p_sub"),
            write=data.get("write"),
            w_sub=data.get("w_sub"),
            hide=data.get("hide"),
            h_sub=data.get("h_sub"),
            readme=data.get("readme"),
            r_sub=data.get("r_sub"),
            header=data.get("header"),
            header_sub=data.get("header_sub"),
        )

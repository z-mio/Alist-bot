from dataclasses import dataclass
from typing import TypeVar, Generic, Type, Union

T = TypeVar("T")


class AListAPIData:
    @classmethod
    def from_dict(cls, data: dict) -> Union["AListAPIData", list["AListAPIData"]]:
        raise NotImplementedError

    def to_dict(self) -> dict:
        return vars(self)


@dataclass
class AListAPIResponse(Generic[T]):
    def __init__(self, code: int, message: str, data: T | list[T] | dict | None = None):
        self.code = code
        self.message = message
        self.data = data
        self.raw_data: dict | list | None = None

    @classmethod
    def from_dict(
        cls, result: dict, data_class: Type[T] | None
    ) -> "AListAPIResponse[T]":
        response = cls(code=result.get("code"), message=result.get("message"))
        response._check_code()
        data = result.get("data")
        response.raw_data = data
        response.data = data_class.from_dict(data) if data_class else data
        return response

    def _check_code(self):
        if self.code == 401 and self.message == "that's not even a token":
            raise AListTokenError()

    def __repr__(self):
        return (
            f"APIResponse(code={self.code}, message={self.message}, data={self.data})"
        )


class AListError(Exception):
    def __init__(self, message: str):
        self.message = message

    def __str__(self):
        return self.message


class AListTokenError(AListError):
    def __init__(self):
        super().__init__("AList Token错误")

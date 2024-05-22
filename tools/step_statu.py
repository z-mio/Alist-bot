from dataclasses import dataclass
from typing import Union, Any, List

_step_dict = {}
_par = {}


@dataclass
class StepStatu:
    def set_step(self, uid: int, step: str, statu: bool = True):
        self.init(uid)
        if not _step_dict.get(uid):
            _step_dict[uid] = {}
        _step_dict[uid][step] = statu

    @staticmethod
    def insert(uid: int, **kwargs):
        if not _par.get(uid):
            _par[uid] = {}
        for k, v in kwargs.items():
            _par[uid][k] = v

    @staticmethod
    def get(uid: int, key: str | list) -> Union[Any, List[Any]]:
        if d := _par.get(uid):
            return (
                (d.get(k) for k in key) if isinstance(key, list) else d.get(key, None)
            )

    @staticmethod
    def clear(uid: int):
        _par.pop(uid, None)

    @staticmethod
    def step_statu(uid: int, step: str):
        return c.get(step) if (c := _step_dict.get(uid)) else False

    @staticmethod
    def init(uid: int):
        return _step_dict.pop(uid, None)


step = StepStatu()

from api.alist.base.base import AListAPIData


class SearchResultData(AListAPIData):
    """/api/fs/search"""

    def __init__(self, content, total):
        self.content = [Content.from_dict(item) for item in content]
        self.total = total

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            content=data.get("content"),
            total=data.get("total"),
        )

    def __repr__(self):
        return f"SearchResult(content={self.content}, total={self.total})"


class Content(AListAPIData):
    def __init__(self, parent, name, is_dir, size, type):
        self.parent = parent
        self.name = name
        self.is_dir = is_dir
        self.size = size
        self.type = type

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            parent=data.get("parent"),
            name=data.get("name"),
            is_dir=data.get("is_dir"),
            size=data.get("size"),
            type=data.get("type"),
        )

    def __repr__(self):
        return f"Content(parent={self.parent}, name={self.name}, is_dir={self.is_dir}, size={self.size}, type={self.type})"

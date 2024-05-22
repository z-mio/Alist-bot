from api.alist.base.base import AListAPIData


class FileInfo(AListAPIData):
    """/api/fs/get"""

    def __init__(
        self,
        name,
        size,
        is_dir,
        modified,
        sign,
        thumb,
        type,
        raw_url,
        readme,
        provider,
        related,
    ):
        self.name = name
        self.size = size
        self.is_dir = is_dir
        self.modified = modified
        self.sign = sign
        self.thumb = thumb
        self.type = type
        self.raw_url = raw_url
        self.readme = readme
        self.provider = provider
        self.related = related

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            name=data.get("name"),
            size=data.get("size"),
            is_dir=data.get("is_dir"),
            modified=data.get("modified"),
            sign=data.get("sign"),
            thumb=data.get("thumb"),
            type=data.get("type"),
            raw_url=data.get("raw_url"),
            readme=data.get("readme"),
            provider=data.get("provider"),
            related=data.get("related"),
        )

    def __repr__(self):
        return f"FileInfo(name={self.name}, size={self.size}, is_dir={self.is_dir}, modified={self.modified}, sign={self.sign}, thumb={self.thumb}, type={self.type}, raw_url={self.raw_url}, readme={self.readme}, provider={self.provider}, related={self.related})"

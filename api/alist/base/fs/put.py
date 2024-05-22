from api.alist.base.base import AListAPIData


class UploadTaskResult(AListAPIData):
    def __init__(self, id, name, state, status, progress, error):
        self.id = id
        self.name = name
        self.state = state
        self.status = status
        self.progress = progress
        self.error = error

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            id=data.get("id"),
            name=data.get("name"),
            state=data.get("state"),
            status=data.get("status"),
            progress=data.get("progress"),
            error=data.get("error"),
        )

    def __repr__(self):
        return f"Task(id={self.id}, name={self.name}, state={self.state}, status={self.status}, progress={self.progress}, error={self.error})"

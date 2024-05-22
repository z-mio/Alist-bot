class CloudflareAPIResponse:
    @classmethod
    def from_dict(cls, result: dict):
        raise NotImplementedError

    def to_dict(self) -> dict:
        return vars(self)


class WorkerInfo(CloudflareAPIResponse):
    def __init__(self, duration, errors, requests, response_body_size, subrequests):
        """
        :param duration:
        :param errors: 错误请求数
        :param requests: 今天的请求总数 免费版最多10万次/天 北京时间早上8点重置
        :param response_body_size: 已用流量
        :param subrequests: 子请求数
        """
        self.duration = duration
        self.errors = errors
        self.requests = requests
        self.response_body_size = response_body_size
        self.subrequests = subrequests

    @classmethod
    def from_dict(cls, result: dict):
        if data := result.get("data"):
            sum = data["viewer"]["accounts"][0]["workersInvocationsAdaptive"][0]["sum"]
            return cls(
                duration=sum["requests"],
                errors=sum["errors"],
                requests=sum["requests"],
                response_body_size=sum["responseBodySize"],
                subrequests=sum["subrequests"],
            )
        else:
            raise ValueError("Invalid data")

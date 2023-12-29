from apscheduler.schedulers.asyncio import AsyncIOScheduler


# 定义一个单例类
class Singleton:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls, *args, **kwargs)
        return cls._instance


# 定义一个类用于 APScheduler，并继承单例类
class APS(Singleton):
    # 用指定的设置初始化调度器
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        # 启动调度器
        self.scheduler.start()

    # 向调度器添加一个任务
    def add_job(
        self,
        job_id,
        func,
        trigger="cron",
        args=None,
        kwargs=None,
        name=None,
        **trigger_args
    ):
        """
        添加任务

        :param job_id: 任务id，用于唯一标识任务，必须
        :param func: 任务执行函数，必须
        :param trigger: 触发器类型，可选，默认为cron表达式
        :param args: 任务执行函数的参数，为列表类型，可选
        :param kwargs: 任务执行函数的参数，为字典类型，可选
        :param name: 任务名称，可选
        :param trigger_args: 触发器参数，可选
        :return: 返回True表示添加成功，返回False表示添加失败
        """
        # 检查任务id是否已存在，如果不存在则添加任务，否则返回False
        return not self.job_exists(job_id) and self.scheduler.add_job(
            id=job_id,
            func=func,
            trigger=trigger,
            args=args,
            kwargs=kwargs,
            name=name,
            **trigger_args,
        )

    # 修改调度器中已有的任务
    def modify_job(
        self,
        job_id,
        func=None,
        trigger=None,
        args=None,
        kwargs=None,
        name=None,
        **trigger_args
    ):
        """
        修改任务

        :param job_id: 任务id，必须
        :param func: 新的任务执行函数，可选
        :param trigger: 新的触发器类型，可选
        :param args: 新的任务执行函数的参数，为列表类型，可选
        :param kwargs: 新的任务执行函数的参数，为字典类型，可选
        :param name: 新的任务名称，可选
        :param trigger_args: 新的触发器参数，可选
        :return: 返回True表示修改成功，返回False表示修改失败
        """
        # 检查任务id是否存在，如果存在则修改任务，否则返回False
        return self.job_exists(job_id) and self.scheduler.reschedule_job(
            job_id=job_id,
            func=func,
            trigger=trigger,
            args=args,
            kwargs=kwargs,
            name=name,
            **trigger_args,
        )

    # 暂停调度器中的一个任务
    def pause_job(self, job_id):
        """
        暂停任务

        :param job_id: 任务id，必须
        :return: 返回True表示暂停成功，返回False表示暂停失败
        """
        # 检查任务id是否存在，如果存在则暂停任务，否则返回False
        return self.job_exists(job_id) and self.scheduler.pause_job(job_id)

    # 恢复调度器中暂停的一个任务
    def resume_job(self, job_id):
        """
        恢复任务

        :param job_id: 任务id，必须
        :return: 返回True表示恢复成功，返回False表示恢复失败
        """
        # 检查任务id是否存在，如果存在则恢复任务，否则返回False
        return self.job_exists(job_id) and self.scheduler.resume_job(job_id)

    # 从调度器中移除一个任务
    def remove_job(self, job_id):
        """
        删除任务

        :param job_id: 任务id，必须
        :return: 返回True表示删除成功，返回False表示删除失败
        """
        # 检查任务id是否存在，如果存在则删除任务，否则返回False
        return self.job_exists(job_id) and self.scheduler.remove_job(job_id)

    def job_exists(self, job_id):
        # 检测任务是否存在，并返回布尔值
        return bool(self.scheduler.get_job(job_id))


aps = APS()

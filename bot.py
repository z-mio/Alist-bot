# -*- coding: UTF-8 -*-

import datetime
import json
import logging
import os

import croniter
import requests
import telegram
import yaml
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from telegram import Update, BotCommand
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, filters, MessageHandler

from alist_api import storage_list
from config.config import config, admin, bot_token, alist_host, alist_token, backup_time, write_config, proxy_url

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s: %(message)s',
    level=logging.INFO
)

scheduler = AsyncIOScheduler()


# 管理员验证
def admin_yz(func):  # sourcery skip: remove-unnecessary-else
    async def wrapper(update, context, *args, **kwargs):
        user_id = update.effective_user.id
        try:
            query = update.callback_query
            query_user_id = query.from_user.id
        except AttributeError:
            query_user_id = 2023

        if user_id == admin:
            return await func(update, context, *args, **kwargs)
        else:
            if query_user_id == admin:
                return await func(update, context, *args, **kwargs)
            else:
                await context.bot.send_message(chat_id=update.effective_chat.id, text="该命令仅管理员可用")

    return wrapper


# 开始
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="发送 /s+文件名 进行搜索")


# 设置菜单
@admin_yz
async def menu(update, context):
    # 管理员私聊可见
    a_bot_menu = [BotCommand(command="start", description="开始"),
                  BotCommand(command="s", description="搜索文件"),
                  BotCommand(command="sl", description="设置搜索结果数量"),
                  BotCommand(command="zl", description="开启/关闭 直链"),
                  BotCommand(command="st", description="存储管理"),
                  BotCommand(command="cf", description="查看当前配置"),
                  BotCommand(command="bc", description="备份Alist配置"),
                  BotCommand(command="sbt", description="设置定时备份"),
                  ]
    # 全部可见
    b_bot_menu = [BotCommand(command="start", description="开始"),
                  BotCommand(command="s", description="搜索文件"),
                  ]

    await context.bot.delete_my_commands()  # 删除菜单
    await context.bot.set_my_commands(a_bot_menu, scope=telegram.BotCommandScopeChat(chat_id=admin))  # 管理员私聊可见
    await context.bot.set_my_commands(b_bot_menu)  # 全部可见
    await context.bot.send_message(chat_id=update.effective_chat.id,
                                   text="菜单设置成功，请退出聊天界面重新进入来刷新菜单")


# 查看当前配置
@admin_yz
async def cf(update, context):
    with open("config/config.yaml", 'r', encoding='utf-8') as f:
        cf_config = yaml.safe_load(f)
    with open("config/cn_dict.json", 'r', encoding='utf-8') as ff:
        cn_dict = json.load(ff)
    b = translate_key(translate_key(cf_config, cn_dict["config_cn"]), cn_dict["common"])
    text = json.dumps(b, indent=4, ensure_ascii=False)
    await context.bot.send_message(chat_id=update.effective_chat.id,
                                   text=f'<code>{text}</code>',
                                   parse_mode=telegram.constants.ParseMode.HTML)


# 监听普通消息

async def echo_bot(update, context):
    if "bc" in context.chat_data and context.chat_data["bc"]:
        message = update.message
        if message.reply_to_message:
            bc_message_id = context.chat_data.get("bc_message_id")
            if message.reply_to_message.message_id == bc_message_id.message_id:
                note_message_text = message.text
                await context.bot.delete_message(chat_id=message.chat.id,
                                                 message_id=message.message_id)
                await context.bot.edit_message_caption(chat_id=bc_message_id.chat.id,
                                                       message_id=bc_message_id.message_id,
                                                       caption=f'#Alist配置备份\n{note_message_text}')
        else:
            context.chat_data["bc"] = False
            context.chat_data.pop("bc_message_id", None)


# 备份alist配置

def backup_config():
    bc_list = ['setting', 'user', 'storage', 'meta']
    bc_dic = {'settings': '', 'users': 'users', 'storages': '', 'metas': ''}
    for i in range(len(bc_list)):
        bc_url = f'{alist_host}/api/admin/{bc_list[i]}/list'
        bc_header = {"Authorization": alist_token, 'accept': 'application/json'}
        bc_post = requests.get(bc_url, headers=bc_header)
        data = json.loads(bc_post.text)
        bc_dic[f'{bc_list[i]}s'] = data['data'] if i == 0 else data['data']['content']
    data = json.dumps(bc_dic, indent=4, ensure_ascii=False)  # 格式化json
    now = datetime.datetime.now()
    current_time = now.strftime("%Y_%m_%d_%H_%M_%S")  # 获取当前时间
    bc_file_name = f'alist_bot_backup_{current_time}.json'
    with open(bc_file_name, 'w', encoding='utf-8') as b:
        b.write(data)
    return bc_file_name


# 发送备份文件
@admin_yz
async def send_backup_file(update, context):
    bc_file_name = backup_config()
    context.chat_data["bc_message_id"] = await context.bot.send_document(chat_id=update.effective_chat.id,
                                                                         document=bc_file_name,
                                                                         caption='#Alist配置备份')
    context.chat_data["bc"] = True
    os.remove(bc_file_name)


# 定时任务——发送备份文件
async def recovery_send_backup_file(_, context):
    bc_file_name = backup_config()
    await context.bot.send_document(
        chat_id=admin, document=bc_file_name, caption='#Alist配置定时备份'
    )
    os.remove(bc_file_name)


# 设置备份时间&开启定时备份
@admin_yz
async def set_backup_time(update, context):
    time = update.message.text.strip("/sbt ")
    if len(time.split()) == 5:
        config['bot']['backup_time'] = time
        write_config('config/config.yaml', config)

        cron = croniter.croniter(backup_time(), datetime.datetime.now())
        next_run_time = cron.get_next(datetime.datetime)  # 下一次备份时间

        if not scheduler.get_jobs():  # 新建
            RegularBackup().new_scheduled_backup_task(context)
            text = f'已开启定时备份！\n下一次备份时间：{next_run_time}'
        else:  # 修改
            RegularBackup().modify_scheduled_backup_task()
            text = f'修改成功！\n下一次备份时间：{next_run_time}'
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text=text)

    elif time == '0':
        config['bot']['backup_time'] = time
        write_config('config/config.yaml', config)
        if scheduler.get_jobs():
            RegularBackup().disable_scheduled_backup_task()
        await context.bot.send_message(chat_id=update.effective_chat.id, text='已关闭定时备份')
    elif not time:
        text = '''格式：/sbt + 5位cron表达式，0为关闭

例：
<code>/sbt 0</code> 关闭定时备份
<code>/sbt 0 8 * * *</code> 每天上午8点运行
<code>/sbt 30 20 */3 * *</code> 每3天晚上8点30运行

 5位cron表达式格式说明
  ——分钟（0 - 59）
 |  ——小时（0 - 23）
 | |  ——日（1 - 31）
 | | |  ——月（1 - 12）
 | | | |  ——星期（0 - 7，星期日=0或7）
 | | | | |
 * * * * *
 
注：bot重启后需要重新设置
'''
        await context.bot.send_message(chat_id=update.effective_chat.id, text=text,
                                       parse_mode=telegram.constants.ParseMode.HTML)
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text='格式错误')


# 定时备份
class RegularBackup:

    # 新建定时备份任务
    @staticmethod
    def new_scheduled_backup_task(context):
        scheduler.add_job(recovery_send_backup_file, trigger=CronTrigger.from_crontab(backup_time()),
                          args=(admin, context),
                          id='send_backup_messages_regularly_id')
        scheduler.start()

    # 修改定时备份任务
    @staticmethod
    def modify_scheduled_backup_task():
        scheduler.reschedule_job('send_backup_messages_regularly_id',
                                 trigger=CronTrigger.from_crontab(backup_time()))

    # 暂停定时备份任务
    @staticmethod
    def disable_scheduled_backup_task():
        scheduler.pause_job('send_backup_messages_regularly_id')


#####################################################################################

#####################################################################################


# 列表/字典key翻译，输入：待翻译列表/字典，翻译字典 输出：翻译后的列表/字典
def translate_key(list_or_dict, translation_dict):  # sourcery skip: assign-if-exp
    if isinstance(list_or_dict, dict):
        def translate_zh(_key):
            translate_dict = translation_dict
            # 如果翻译字典里有当前的key，就返回对应的中文字符串
            if _key in translate_dict:
                return translate_dict[_key]
            # 如果翻译字典里没有当前的key，就返回原字符串
            else:
                return _key

        new_dict_or_list = {}  # 存放翻译后key的字典
        # 遍历原字典里所有的键值对
        for key, value in list_or_dict.items():
            # 如果当前的值还是字典，就递归调用自身
            if isinstance(value, dict):
                new_dict_or_list[translate_zh(key)] = translate_key(value, translation_dict)
            # 如果当前的值不是字典，就把当前的key翻译成中文，然后存到新的字典里
            else:
                new_dict_or_list[translate_zh(key)] = value
    else:
        new_dict_or_list = []
        for index, value in enumerate(list_or_dict):
            if value in translation_dict.keys():
                new_dict_or_list.append(translation_dict[value])
            else:
                new_dict_or_list.append(value)
    return new_dict_or_list


#####################################################################################
#####################################################################################

# bot重启后要恢复的任务
async def recovery_task(context):
    # Alist配置定时备份
    async def alist_config_timed_backup():
        if backup_time() != '0':
            logging.info('恢复定时任务')
            RegularBackup().new_scheduled_backup_task(context)

    ###
    await alist_config_timed_backup()


# bot启动时验证
def examine():
    try:
        a = storage_list(alist_host, alist_token)
        code = json.loads(a.text)
    except json.decoder.JSONDecodeError:
        logging.error('连接Alist失败，请检查配置alist_host是否填写正确')
        exit()
    except requests.exceptions.ReadTimeout:
        logging.error('连接Alist超时，请检查网站状态')
        exit()
    else:
        if code['code'] == 200:
            ...
        elif code['code'] == 401 and code['message'] == "that's not even a token":
            logging.error('Alist token错误')
            exit()


def main():
    from search import search_handlers
    from storage import storage_handlers, echo_storage
    application = (
        ApplicationBuilder()
        .token(bot_token)
        .proxy_url(proxy_url)
        .get_updates_proxy_url(proxy_url)
        .build()
        if proxy_url
        else ApplicationBuilder().token(bot_token).build()
    )

    job_queue = application.job_queue
    job_queue.run_once(recovery_task, 5)  # 定时任务，bot启动时等待5秒运行，只运行一次

    bot_handlers = [
        CommandHandler('start', start),
        CommandHandler('bc', send_backup_file),
        CommandHandler('cf', cf),
        CommandHandler('menu', menu),
        CommandHandler('sbt', set_backup_time),

    ]

    # bot
    application.add_handlers(bot_handlers)

    # 监听普通消息
    async def e(update, context):
        await echo_storage(update, context)
        await echo_bot(update, context)

    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), e))

    # search
    application.add_handlers(search_handlers)

    # storage
    application.add_handlers(storage_handlers)

    # 启动
    try:
        application.run_polling()
    except telegram.error.InvalidToken:
        logging.error('token被服务器拒绝，请检查配置bot token')
    except telegram.error.NetworkError:
        logging.error('所有连接尝试都失败，请检查配置proxy_url')


if __name__ == '__main__':
    examine()
    main()

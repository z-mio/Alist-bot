# -*- coding: UTF-8 -*-

import datetime
import json
import logging
import os

import croniter
import pyrogram
import requests
import yaml
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from pyrogram import Client, filters, enums
from pyrogram.types import BotCommand

from api.alist_api import storage_list
from config.config import (config, admin, alist_host, alist_token, backup_time, write_config, api_id, api_hash,
                           bot_token, scheme, hostname, port)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s: %(message)s',
    level=logging.INFO
)

scheduler = AsyncIOScheduler()

proxy = {
    "scheme": scheme,  # 支持“socks4”、“socks5”和“http”
    "hostname": hostname,
    "port": port
}

if os.path.exists('my_bot.session'):
    app = (
        Client("my_bot", proxy=proxy)
        if scheme and hostname and port
        else Client("my_bot")
    )
elif scheme and hostname and port:
    app = Client(
        "my_bot", proxy=proxy,
        api_id=api_id, api_hash=api_hash,
        bot_token=bot_token)
else:
    app = Client(
        "my_bot",
        api_id=api_id, api_hash=api_hash,
        bot_token=bot_token)
app.set_parse_mode(enums.ParseMode.HTML)


# 管理员验证
def admin_yz(func):
    async def wrapper(client, message, *args, **kwargs):
        user_id = message.from_user.id
        query_user_id = getattr(message, "from_user", None)
        query_user_id = query_user_id.id if query_user_id else 2023

        if user_id == admin or query_user_id == admin:
            return await func(client, message, *args, **kwargs)
        else:
            await client.send_message(chat_id=message.chat.id, text="该命令仅管理员可用")

    return wrapper


# 开始
@app.on_message(filters.command('start'))
async def start(_, message):
    await app.send_message(chat_id=message.chat.id, text="发送 /s+文件名 进行搜索")


# 帮助
@app.on_message(filters.command('help') & filters.private)
@admin_yz
async def _help(_, message):
    text = '''
发送图片查看图床功能
'''
    await app.send_message(chat_id=message.chat.id, text=text)


# 设置菜单
@app.on_message(filters.command('menu') & filters.private)
@admin_yz
async def menu(_, message):
    # 管理员私聊可见
    a_bot_menu = [BotCommand(command="start", description="开始"),
                  BotCommand(command="s", description="搜索文件"),
                  BotCommand(command="sl", description="设置搜索结果数量"),
                  BotCommand(command="zl", description="开启/关闭 直链"),
                  BotCommand(command="st", description="存储管理"),
                  BotCommand(command="cf", description="查看当前配置"),
                  BotCommand(command="bc", description="备份Alist配置"),
                  BotCommand(command="sbt", description="设置定时备份"),
                  BotCommand(command="help", description="查看帮助"),
                  ]

    # 全部可见
    b_bot_menu = [BotCommand(command="start", description="开始"),
                  BotCommand(command="s", description="搜索文件"),
                  ]

    await app.delete_bot_commands()
    await app.set_bot_commands(a_bot_menu, scope=pyrogram.types.BotCommandScopeChat(chat_id=admin))
    await app.set_bot_commands(b_bot_menu)
    await app.send_message(chat_id=message.chat.id, text="菜单设置成功，请退出聊天界面重新进入来刷新菜单")


# 查看当前配置

@app.on_message(filters.command('cf') & filters.private)
@admin_yz
async def view_current_config(_, message):
    with open("config/config.yaml", 'r', encoding='utf-8') as f:
        cf_config = yaml.safe_load(f)
    with open("config/cn_dict.json", 'r', encoding='utf-8') as ff:
        cn_dict = json.load(ff)
    b = translate_key(translate_key(cf_config, cn_dict["config_cn"]), cn_dict["common"])
    text = json.dumps(b, indent=4, ensure_ascii=False)
    await app.send_message(chat_id=message.chat.id,
                           text=f'<code>{text}</code>')


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


# 监听回复消息的消息
@app.on_message(filters.text & filters.reply & filters.private)
@admin_yz
async def echo_bot(_, message):
    if message.reply_to_message.document:  # 判断回复的消息是否包含文件
        await app.delete_messages(chat_id=message.chat.id,
                                  message_ids=message.id)
        await app.edit_message_caption(chat_id=message.chat.id,
                                       message_id=message.reply_to_message_id,
                                       caption=f'#Alist配置备份\n{message.text}')


# 发送备份文件
@app.on_message(filters.command('bc') & filters.private)
@admin_yz
async def send_backup_file(_, message):
    bc_file_name = backup_config()
    await app.send_document(chat_id=message.chat.id,
                            document=bc_file_name,
                            caption='#Alist配置备份')
    os.remove(bc_file_name)


# 定时任务——发送备份文件
async def recovery_send_backup_file():
    bc_file_name = backup_config()
    await app.send_document(
        chat_id=admin, document=bc_file_name, caption='#Alist配置定时备份'
    )
    os.remove(bc_file_name)
    logging.info('定时备份成功')


# 设置备份时间&开启定时备份
@app.on_message(filters.command('sbt') & filters.private)
@admin_yz
async def set_backup_time(_, message):
    time = ' '.join(message.command[1:])
    if len(time.split()) == 5:
        config['bot']['backup_time'] = time
        write_config('config/config.yaml', config)

        cron = croniter.croniter(backup_time(), datetime.datetime.now())
        next_run_time = cron.get_next(datetime.datetime)  # 下一次备份时间

        if not scheduler.get_jobs():  # 新建
            RegularBackup().new_scheduled_backup_task()
            text = f'已开启定时备份！\n下一次备份时间：{next_run_time}'
        else:  # 修改
            RegularBackup().modify_scheduled_backup_task()
            text = f'修改成功！\n下一次备份时间：{next_run_time}'
        await app.send_message(chat_id=message.chat.id,
                               text=text)

    elif time == '0':
        config['bot']['backup_time'] = time
        write_config('config/config.yaml', config)
        if scheduler.get_jobs():
            RegularBackup().disable_scheduled_backup_task()
        await app.send_message(chat_id=message.chat.id, text='已关闭定时备份')
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

'''
        await app.send_message(chat_id=message.chat.id, text=text)
    else:
        await app.send_message(chat_id=message.chat.id, text='格式错误')


# 定时备份
class RegularBackup:

    # 新建定时备份任务
    @staticmethod
    def new_scheduled_backup_task():
        scheduler.add_job(recovery_send_backup_file, trigger=CronTrigger.from_crontab(backup_time()),
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
def recovery_task():
    # Alist配置定时备份
    def alist_config_timed_backup():
        if backup_time() != '0':
            logging.info('定时备份已启动')
            RegularBackup().new_scheduled_backup_task()

    # 运行
    alist_config_timed_backup()


# bot启动时验证
def examine():
    try:
        a = storage_list()
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


def start_bot():
    from module.search import search_handlers
    from module.storage import storage_handlers
    from module.image import image_handlers
    [app.add_handler(handler) for handler in
     search_handlers + storage_handlers + image_handlers]

    app.run()


if __name__ == '__main__':
    examine()
    recovery_task()
    start_bot()

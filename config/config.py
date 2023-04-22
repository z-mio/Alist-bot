# -*- coding: UTF-8 -*-
import yaml

# 存储和检索与特定聊天相关联的数据
chat_data = {}


def get_config(path):
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def write_config(path, modified_config):
    with open(path, 'w', encoding='utf-8') as f:
        yaml.dump(modified_config, f, allow_unicode=True)


config = get_config("config/config.yaml")


# bot
def backup_time():
    return config['bot']['backup_time']


def per_page():
    return config['bot']['search']['per_page']


def z_url():
    return config['bot']['search']['z_url']


# user
admin = config['user']['admin']
alist_host = config['user']['alist_host'].removesuffix('/')
alist_web = config['user']['alist_web'].removesuffix('/')
alist_token = config['user']['alist_token']
bot_token = config['user']['bot_token']
api_id = config['user']['api_id']
api_hash = config['user']['api_hash']
# proxy
scheme = config['proxy']['scheme']
hostname = config['proxy']['hostname']
port = config['proxy']['port']


# storage_cfg
def storage_cfg():
    return get_config("config/storage_cfg.yaml")


# image_cfg
image_config = get_config("config/image_cfg.yaml")


def image_save_path():
    return image_config['image_save_path'].lstrip('/')


def image_upload_path():
    return image_config['image_upload_path'].lstrip('/')

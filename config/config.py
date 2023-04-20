# -*- coding: UTF-8 -*-
import yaml


def get_config(path):
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def write_config(path, modified_config):
    with open(path, 'w') as f:
        yaml.dump(modified_config, f)


# config

config = get_config("config/config.yaml")

alist_host = config['user']['alist_host'].removesuffix('/')

alist_token = config['user']['alist_token']

bot_token = config['user']['bot_token']

alist_web = config['search']['alist_web'].removesuffix('/')

proxy_url = config['bot']['proxy_url']


def admin():
    return config['user']['admin']


def per_page():
    return config['search']['per_page']


def z_url():
    return config['search']['z_url']


def backup_time():
    return config['bot']['backup_time']


# storage_cfg

def storage_cfg():
    return get_config("config/storage_cfg.yaml")

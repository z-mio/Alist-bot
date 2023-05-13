# -*- coding: UTF-8 -*-
# try
import logging


def handle_exception(func):
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            logging.error(e)

    return wrapper

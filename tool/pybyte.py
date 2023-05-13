# -*- coding: UTF-8 -*-
# 字节数转文件大小
import math


def pybyte(size, dot=2):
    size = float(size)
    # 位 比特 bit
    if 0 <= size < 1:
        human_size = f'{str(round(size / 0.125, dot))}b'
    elif 1 <= size < 1024:
        human_size = f'{str(round(size, dot))}B'
    elif math.pow(1024, 1) <= size < math.pow(1024, 2):
        human_size = f'{str(round(size / math.pow(1024, 1), dot))}KB'
    elif math.pow(1024, 2) <= size < math.pow(1024, 3):
        human_size = f'{str(round(size / math.pow(1024, 2), dot))}MB'
    elif math.pow(1024, 3) <= size < math.pow(1024, 4):
        human_size = f'{str(round(size / math.pow(1024, 3), dot))}GB'
    elif math.pow(1024, 4) <= size < math.pow(1024, 5):
        human_size = f'{str(round(size / math.pow(1024, 4), dot))}TB'
    else:
        raise ValueError(
            f'{pybyte.__name__}() takes number than or equal to 0, but less than 0 given.'
        )
    return human_size

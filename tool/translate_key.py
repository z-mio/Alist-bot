# -*- coding: UTF-8 -*-
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

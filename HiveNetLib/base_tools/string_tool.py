#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
#
# Copyright 2018 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
字符串处理模块

@module string_tool
@file string_tool.py

"""

import copy
import json
from random import Random


__MOUDLE__ = 'string_tool'  # 模块名
__DESCRIPT__ = u'字符串处理模块'  # 模块描述
__VERSION__ = '0.1.0'  # 版本
__AUTHOR__ = u'黎慧剑'  # 作者
__PUBLISH__ = '2018.08.29'  # 发布日期


class StringTool(object):
    """
    字符串处理通用类
    提供各类字符串处理相关的常用工具函数（静态方法）

    """
    #############################
    # 哈希转换
    #############################
    @staticmethod
    def bytes_to_hex(byte_array):
        """
        将byte串转换为哈希字符串

        @param {byte[]} byte_array - 需要转换的byte数组

        @returns {string} - 转换后的hex字符串

        @example
            StringTool.bytes_to_hex(bytes("test string", encoding='utf-8'))

        """
        return ''.join(["%02X" % x for x in byte_array]).strip()

    @staticmethod
    def hex_to_bytes(hex_str):
        """
        将哈希字符串转换为byte数组

        @param {string} hex_str - 需要转换的Hex样式的字符串

        @returns {byte[]} - byte数组

        @example
            StringTool.hex_to_bytes("A3D3F33433")

        """
        return bytes.fromhex(hex_str)

    #############################
    # 字符处理
    #############################
    @staticmethod
    def fill_fix_string(deal_str, fix_len, fill_char, left=True):
        """
        用指定字符填充字符串达到固定长度

        @param {string} deal_str - 要处理的字符串
        @param {int} fix_len - 返回字符串的固定长度
        @param {string} fill_char - 填充字符(单字符)
        @param {bool} left=True - 填充方向，True-左填充，False-右填充

        @returns {string} - 如果原字符串长度已超过指定长度，则直接返回原字符串；否则返回处理后的字符串

        @example
            fix_str = StringTool.fill_fix_string('My job is', 50, ' ', False)

        """
        _str = str(deal_str)
        # 生成填充串
        _mixstr = ""
        _i = 0
        while _i < fix_len - len(_str):
            _mixstr = _mixstr + fill_char
            _i = _i + 1
        # 按方向填充
        if left:
            return _mixstr + _str
        else:
            return _str + _mixstr

    @staticmethod
    def get_list_from_str(deal_str):
        """
        从字符串中提炼出数组
        按照python的模式提炼出数组，说明如下：
            1、数组内的对象根据字符的形式取得实际类型，例如：
                'text' - 字符串
                10 - 数字
                True - bool类型
            2、如果数组有嵌套，可以支持嵌套的模式

        @param {string} deal_str - 要提炼的字符串，内部要含有[a,b,c,d,'d']这类的字符串，例如'dfdfdfd[ddd,aa,dd]'

        @returns {list} - 抽离出来的数组

        @example
            mylist = StringTool.get_list_from_str('aaa["a", 10, [39, 4], True, 21.4]bbb')

        """
        _array = []
        _index1 = deal_str.find("[")
        _index2 = deal_str.rfind("]")  # 从后往前找
        if _index2 <= _index1:
            return _array
        _str = deal_str[_index1:_index2 + 1]
        _array = eval(_str)
        return _array

    @staticmethod
    def get_random_str(random_length=8, chars="AaBbCcDdEeFfGgHhIiJjKkLlMmNnOoPpQqRrSsTtUuVvWwXxYyZz0123456789"):
        """
        随机生成固定长度的字符串

        @param {int} random_length=8 - 需生成的字符串长度
        @param {string} chars="AaBbCcDdEeFfGgHhIiJjKkLlMmNnOoPpQqRrSsTtUuVvWwXxYyZz0123456789" - 随机抽取的字符串内容

        @returns {string} - 返回的字符串

        @example
            randomstr = StringTool.get_random_str(10)

        """
        _str = ''
        length = len(chars) - 1
        random = Random()
        for i in range(random_length):
            _str += chars[random.randint(0, length)]
        return _str

    @staticmethod
    def get_n_index(src, sub, n=1, start=0):
        """
        查找第n次出现子字符串的位置

        @param {string} src - 要处理的字符串
        @param {string} sub - 要查找的子字符串

        @param {int} [n=1] - 要查找的字符串出现次数
        @param {int} [start=0] - 查找开始位置

        @returns {int} - 返回找到的位置，如果找不到返回-1

        """
        if n < 1:
            # 已找不到了
            return -1
        index = src.find(sub, start)
        if index != -1 and n > 1:
            return StringTool.get_n_index(src, sub, n - 1, index + len(sub))
        return index

    #############################
    # 对象与字符串转换
    #############################
    @staticmethod
    def format_obj_property_str(deal_obj, is_deal_subobj=False, c_level=0, max_level=10, is_same_line=False):
        """
        将对象属性格式化为可打印字符串

        @param {[type]} deal_obj - 要格式化的对象
        @param {bool} is_deal_subobj=False - 是否要打印属性对象的子属性
        @param {int} c_level=0 - 打印级别（根据级别调整缩进位数，每一级缩进2个空格）
        @param {int} max_level=10 - 最大检索级别，<=0代表不进行限制
        @param {bool} is_same_line=False - 输出内容是否不换行，内部使用，如果不换行则忽略缩进

        @returns {string} - 返回格式化后的字符串

        @example
            obj = NullObj()
            obj.aa = 1
            obj.cb = 'fdfd'
            obj.kk = NullObj()
            obj.kk.abc = 3
            obj.kk.bcd = 'dfdfd'
            print(StringTools.format_obj_property_str(obj=obj,is_deal_subobj=True))

        """
        # 先打印对象自身
        _indent_str = ''
        if not is_same_line:
            _indent_str = StringTool.fill_fix_string(
                deal_str='', fix_len=c_level * 2, fill_char=' ', left=True)
        _retstr = '%stype(%s) ' % (
            _indent_str,
            type(deal_obj)
        )
        if is_deal_subobj and (max_level <= 0 or (max_level > c_level)):
            # print("c_level:" + str(c_level))
            _indent_str = StringTool.fill_fix_string(
                deal_str='', fix_len=(c_level + 1) * 2, fill_char=' ', left=True)
            # 要打印子对象,区分类型进行处理
            if type(deal_obj) in (list, tuple):
                # 数组和列表
                _index = 0
                while _index < len(deal_obj):
                    _retstr = (
                        _retstr + '\n' + _indent_str
                        + '[index:' + str(_index) + '] '
                        + StringTool.format_obj_property_str(
                            deal_obj[_index], is_deal_subobj=is_deal_subobj,
                            c_level=c_level + 1, max_level=max_level, is_same_line=True
                        )
                    )
                    _index = _index + 1
            elif type(deal_obj) == dict:
                # 字典
                for _key in deal_obj.keys():
                    _retstr = (
                        _retstr + '\n' + _indent_str
                        + 'key: ' + str(_key) + '  value: '
                        + StringTool.format_obj_property_str(
                            deal_obj[_key], is_deal_subobj=is_deal_subobj,
                            c_level=c_level + 2, max_level=max_level, is_same_line=True
                        )
                    )
            else:
                # 一般对象，直接类的属性，通过dir获取，且非内置属性
                _attr_print = False
                _attr_dir = list()
                if str(deal_obj).find(' object at 0x') > 0:  # 通过str判断是否有重载处理
                    _attr_print = True
                    _attr_dir = dir(deal_obj)
                    for _item in _attr_dir:
                        if _item[0: 2] != '__' and not callable(getattr(deal_obj, _item)):
                            _retstr = (
                                _retstr + "\n" + _indent_str
                                + _item + '(attr): '
                                + StringTool.format_obj_property_str(
                                    getattr(deal_obj, _item), is_deal_subobj=is_deal_subobj,
                                    c_level=c_level + 2, max_level=max_level, is_same_line=True
                                )
                            )

                # 一般对象,object上补充的属性
                try:
                    for _item in deal_obj.__dict__.items():
                        if _attr_print and _item[0] not in _attr_dir:
                            _retstr = (
                                _retstr + "\n" + _indent_str
                                + _item[0] + '(__dict__): '
                                + StringTool.format_obj_property_str(
                                    _item[1], is_deal_subobj=is_deal_subobj,
                                    c_level=c_level + 2, max_level=max_level, is_same_line=True
                                )
                            )
                except:
                    # 可能对象没有__dict__属性
                    _retstr = _retstr + str(deal_obj)
        else:
            # 不打印子对象
            _retstr = _retstr + str(deal_obj)

        return _retstr

    #############################
    # JSON相关
    #############################
    @staticmethod
    def object_to_json(obj):
        """
        将python对象转换为json字符串（支持所有对象的通用转换）

        @param {object} obj - 要转换的json

        @return {string} - 转换后的json字符串，如果是None返回''

        @see 处理方式：
            1、如果对象包含__json__方法，则直接调用对象的该方法进行转换
            2、尝试通过json库标准方法进行转换
            3、如果对象不支持序列化，转换会出现异常；如果对象包含__dict__，则将__dict__转换为json
            4、如果都失败，则抛出异常
        """
        _json_str = None
        if obj is None:
            _json_str = ''
        elif hasattr(obj, '__json__'):
            _json_str = obj.__json__()
        else:
            try:
                _json_str = json.dumps(obj)
            except Exception as e:
                if hasattr(obj, '__dict__'):
                    _json_str = json.dumps(obj.__dict__)
                raise e
        return _json_str

    @staticmethod
    def json_to_object(json_str, class_ref=None, object_hook=None):
        """
        将json字符串转换为python对象（支持自定义转换）

        @param {string} json_str - 要转换的json字符串
        @param {class} class_ref=None - 类定义引用，例如generic.NullObj
            引用的类必须实现__fromjson__的静态函数，传入json字符串，返回对象实例
        @param {function} object_hook=None - 将json对象转换为所需实例类的函数
            函数入参为通过json标准库转换后的json对象，出参为转换后的对象实例

        @return {object} - 转换后的对象

        @see 处理方式：
            1、如果json_str为''，直接返回None
            2、如果object_hook不为空，则通过json库标准方法进行转换，并使用object_hook将对象转换为所需的类型
            3、如果class_ref不为None并且有__fromjson__的静态函数，则通过该函数获取对象，如果没有该函数抛出异常
        """
        _obj = None
        if json_str == '':
            pass
        elif object_hook is not None:
            _obj = json.loads(json_str, object_hook=object_hook)
        elif class_ref is not None:
            _obj = class_ref.__fromjson__(json_str)
        else:
            _obj = json.loads(json_str)

        return _obj


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    # 打印版本信息
    print(('模块名：%s  -  %s\n'
           '作者：%s\n'
           '发布日期：%s\n'
           '版本：%s' % (__MOUDLE__, __DESCRIPT__, __AUTHOR__, __PUBLISH__, __VERSION__)))
    print(StringTool.object_to_json(10))
    print(type(StringTool.json_to_object('10')))

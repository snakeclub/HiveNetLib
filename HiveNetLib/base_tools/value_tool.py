#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
#
# Copyright 2018 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
值处理通用工具

@module value_tool
@file value_tool.py

"""

import sys
import os


__MOUDLE__ = 'value_tool'  # 模块名
__DESCRIPT__ = u'值处理通用工具'  # 模块描述
__VERSION__ = '0.1.0'  # 版本
__AUTHOR__ = u'黎慧剑'  # 作者
__PUBLISH__ = '2018.09.30'  # 发布日期


class ValueTool(object):
    """
    值处理通用工具

    """

    @staticmethod
    def get_dict_value(key, dict_obj, default_value=None):
        """
        获取字典指定值

        @param {object} key - 字典key值
        @param {object} dict_obj - 要查的字典
        @param {object} default_value=None - 如果取不到的默认值

        @returns {object} - 去到值

        """
        _value = default_value
        if key in dict_obj.keys():
            _value = dict_obj[key]
        return _value


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    # 打印版本信息
    print(('模块名：%s  -  %s\n'
           '作者：%s\n'
           '发布日期：%s\n'
           '版本：%s' % (__MOUDLE__, __DESCRIPT__, __AUTHOR__, __PUBLISH__, __VERSION__)))

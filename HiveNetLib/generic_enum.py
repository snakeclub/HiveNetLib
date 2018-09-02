#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
# Filename : generic_enum.py
#
# Copyright 2018 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
通用枚举值定义模块
@module generic_enum
@file generic_enum.py
"""

import logging
from enum import Enum


__MOUDLE__ = 'generic_enum'  # 模块名
__DESCRIPT__ = '通用枚举值定义'  # 模块描述
__VERSION__ = '0.1.0'  # 版本
__AUTHOR__ = '黎慧剑'  # 作者
__PUBLISH__ = '2018.08.29'  # 发布日期


class EnumLogLevel(Enum):
    """
    日志级别
    @enum {int}
    """
    DEBUG = logging.DEBUG  # 调试
    INFO = logging.INFO  # 一般
    WARNING = logging.WARNING  # 告警
    ERROR = logging.ERROR  # 错误
    CRITICAL = logging.CRITICAL  # 严重


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    # 打印版本信息
    print(('模块名：%s  -  %s\n'
           '作者：%s\n'
           '发布日期：%s\n'
           '版本：%s' % (__MOUDLE__, __DESCRIPT__, __AUTHOR__, __PUBLISH__, __VERSION__)))

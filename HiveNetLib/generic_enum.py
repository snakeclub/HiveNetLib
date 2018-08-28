#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
# Filename : generic_enum.py
#
# Copyright 2018 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import logging
from enum import Enum


__MoudleName__ = 'generic_enum'
__MoudleDesc__ = '通用枚举值定义'
__Version__ = '1.0.0'
__Author__ = '黎慧剑'
__Time__ = '2018/1/13'


class EnumLogLevel(Enum):
    """
    @enum 日志级别
    @enumName EnumLogLevel
    @enumDescription 日志级别枚举值定义

    """
    DEBUG = logging.DEBUG  # 调试
    INFO = logging.INFO  # 一般
    WARNING = logging.WARNING  # 告警
    ERROR = logging.ERROR  # 错误
    CRITICAL = logging.CRITICAL  # 严重


if __name__ == "__main__":
    """
    # 当程序自己独立运行时执行的操作
    """
    # 打印版本信息
    print('''模块名：%s  -  %s
    作者：%s
    更新日期：%s
    版本：%s''' % (__MoudleName__, __MoudleDesc__, __Author__, __Time__, __Version__))

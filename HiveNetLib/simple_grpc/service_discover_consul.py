#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
#
# Copyright 2018 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
consul服务发现适配器
@module service_discover_consul
@file service_discover_consul.py
@see consul https://www.cnblogs.com/yuzhenjie/p/9398569.html
@requires python-consul
    pip install python-consul
"""

import os
import sys
# 根据当前文件路径将包路径纳入，在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir, os.path.pardir)))
from HiveNetLib.simple_grpc.service_discover_fw import BaseServiceDiscover


__MOUDLE__ = 'service_discover_consul'  # 模块名
__DESCRIPT__ = u'consul服务发现适配器'  # 模块描述
__VERSION__ = '0.1.0'  # 版本
__AUTHOR__ = u'黎慧剑'  # 作者
__PUBLISH__ = '2019.06.10'  # 发布日期


class ConsulServiceDiscover(BaseServiceDiscover):
    """
    consul服务发现适配器
    """


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    # 打印版本信息
    print(('模块名：%s  -  %s\n'
           '作者：%s\n'
           '发布日期：%s\n'
           '版本：%s' % (__MOUDLE__, __DESCRIPT__, __AUTHOR__, __PUBLISH__, __VERSION__)))


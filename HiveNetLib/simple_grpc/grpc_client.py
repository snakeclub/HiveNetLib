#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
#
# Copyright 2018 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
gRPC客户端应用

@module grpc_client
@file grpc_client.py
"""

import os
import sys
# 根据当前文件路径将包路径纳入，在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir, os.path.pardir)))

__MOUDLE__ = 'grpc_client'  # 模块名
__DESCRIPT__ = u'gRPC客户端应用'  # 模块描述
__VERSION__ = '0.1.0'  # 版本
__AUTHOR__ = u'黎慧剑'  # 作者
__PUBLISH__ = '2019.06.30'  # 发布日期


class SimpleGRpcClient(object):
    """
    封装SimpleGRpc的客户端方法
    """
    #############################
    # 内部变量
    #############################
    _connect_para = None  # 客户端的连接参数

    #############################
    # 静态函数
    #############################

    #############################
    # 公共函数
    #############################


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    # 打印版本信息
    print(('模块名：%s  -  %s\n'
           '作者：%s\n'
           '发布日期：%s\n'
           '版本：%s' % (__MOUDLE__, __DESCRIPT__, __AUTHOR__, __PUBLISH__, __VERSION__)))

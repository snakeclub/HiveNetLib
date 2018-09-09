#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
#
# Copyright 2018 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
<description>
@module call_chain_tool
@file call_chain_tool.py
"""

import datetime

__MOUDLE__ = 'call_chain_tool'  # 模块名
__DESCRIPT__ = u''  # 模块描述
__VERSION__ = '0.1.0'  # 版本
__AUTHOR__ = u'黎慧剑'  # 作者
__PUBLISH__ = '2018.09.06'  # 发布日期


class CallChainTool(object):
    """
    调用链工具类

    """

    @staticmethod
    def methon_call_chain(f):
        """
        模块方法调用链修饰符
        """
        # 记录启动的信息
        _start_time = datetime.datetime.now()
        f()
        _end_time = datetime.datetime.now()
        print('use:' + str(_end_time - _start_time))

    @staticmethod
    def api_call_chain(f):
        """
        api接口调用链修饰符
        """
        pass


@CallChainTool.methon_call_chain
def test_fun():
    print('test_fun:' + str(a) + b)


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    # 打印版本信息
    print(('模块名：%s  -  %s\n'
           '作者：%s\n'
           '发布日期：%s\n'
           '版本：%s' % (__MOUDLE__, __DESCRIPT__, __AUTHOR__, __PUBLISH__, __VERSION__)))

    test_fun(20, 'B3333')

#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
#
# Copyright 2018 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
并行任务模块测试
@module test_simple_parallel
@file test_simple_parallel.py
"""

import os
import sys
import unittest
# 根据当前文件路径将包路径纳入，在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir)))
from HiveNetLib.simple_i18n import SimpleI18N, _, set_global_i18n
from HiveNetLib.base_tools.test_tool import TestTool
from HiveNetLib.simple_parallel import ThreadParallelShareDict, ProcessParallelShareDict


__MOUDLE__ = 'test_simple_parallel'  # 模块名
__DESCRIPT__ = u'并行任务模块测试'  # 模块描述
__VERSION__ = '0.1.0'  # 版本
__AUTHOR__ = u'黎慧剑'  # 作者
__PUBLISH__ = '2018.10.04'  # 发布日期


class TestSimpleParallel(unittest.TestCase):
    """
    测试simple_parallel模块
    """

    def setUp(self):
        """
        启动测试案例执行的初始化（注意如果多个案例会执行多次）
        """
        pass

    def tearDown(self):
        """
        结束测试案例执行的销毁（注意如果多个案例会执行多次）
        """
        pass

    def test_parallel_share_dict(self):
        """
        测试并行共享字典
        """
        d1 = ThreadParallelShareDict('d1')
        d2 = ThreadParallelShareDict('d2')
        d1['key1'] = 'd1-key1'
        d2['key1'] = 'd2-key1'
        self.assertTrue(d1['key1'] == 'd1-key1', 'ThreadParallelShareDict data error')
        self.assertTrue(d2['key1'] == 'd2-key1', 'ThreadParallelShareDict data error')

        d1 = ProcessParallelShareDict('d1')
        d2 = ProcessParallelShareDict('d2')
        d1['key1'] = 'd1-key1'
        d2['key1'] = 'd2-key1'
        self.assertTrue(d1['key1'] == 'd1-key1', 'ProcessParallelShareDict data error')
        self.assertTrue(d2['key1'] == 'd2-key1', 'ProcessParallelShareDict data error')

        class c1(object):
            def __init__(self, tag=''):
                self.d = ProcessParallelShareDict('d')
                self.d['key1'] = 'd-key1-' + tag

        d1 = c1('d1')
        d2 = c1('d2')
        self.assertTrue(d1.d['key1'] == 'd-key1-d1',
                        'ProcessParallelShareDict class1 data error: %s' % (d1.d['key1']))
        self.assertTrue(d2.d['key1'] == 'd-key1-d2', 'ProcessParallelShareDict class2 data error')


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    unittest.main()

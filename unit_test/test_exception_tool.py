#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
#

"""
<description>
@module test_exception_tool
@file test_exception_tool.py
"""

import unittest
import time
import sys
import os
# 根据当前文件路径将包路径纳入，在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir)))
from contextlib import contextmanager
import HiveNetLib.simple_log as simple_log
from HiveNetLib.base_tools.file_tool import FileTool
from HiveNetLib.generic import CResult
from HiveNetLib.base_tools.exception_tool import ExceptionTool


class TestExcepitonTool(unittest.TestCase):
    """
    测试ExcepitonTool类
    """

    def setUp(self):
        """
        启动测试执行的初始化
        """
        pass

    def tearDown(self):
        """
        结束测试执行的销毁
        """
        pass

    def test_methon(self):
        """
        测试静态方法
        """
        _result = CResult('00000')
        _result.net_info = None
        with ExceptionTool.ignored_cresult(
            _result,
            logger=None,
            expect=(),
            error_map={ImportError: ('20401', None), BlockingIOError: ('20407', None)},
            self_log_msg='test:',
            force_log_level=None
        ):
            _result.test = 'test'

        self.assertTrue(_result.code ==
                        '00000' and _result.test == 'test', 'ok result error')

        _result = CResult('00000')
        with ExceptionTool.ignored_cresult(
            _result,
            logger=None,
            expect=(),
            error_map={ImportError: ('20401', None), BlockingIOError: ('20407', None)},
            self_log_msg='test:',
            force_log_level=None
        ):
            raise ImportError

        self.assertTrue(_result.code == '20401',
                        '20401 result error, code:' + _result.code)

        _result = CResult('00000')
        with ExceptionTool.ignored_cresult(
            _result,
            logger=None,
            expect=(),
            error_map={ImportError: ('20401', None), BlockingIOError: ('20407', None)},
            self_log_msg='test:',
            force_log_level=None
        ):
            raise BlockingIOError

        self.assertTrue(_result.code == '20407', '20407 result error, code:' + _result.code)


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    unittest.main()

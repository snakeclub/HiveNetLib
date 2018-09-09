#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""
测试调用链工具模块
@module test_call_chain_tool
@file test_call_chain_tool.py
"""

import os
import sys
import time
import unittest
sys.path.append(os.path.abspath(os.path.dirname(__file__)+'/'+'../..'))
from HiveNetLib.base_tools.call_chain_tool import CallChainTool
from HiveNetLib.generic_enum import EnumLogLevel
from HiveNetLib.simple_log import Logger, EnumLoggerName, EnumLoggerConfigType
from HiveNetLib.base_tools.file_tool import FileTool

__MOUDLE__ = 'test_call_chain_tool'  # 模块名
__DESCRIPT__ = u'测试调用链工具模块'  # 模块描述
__VERSION__ = '0.1.0'  # 版本
__AUTHOR__ = u'黎慧剑'  # 作者
__PUBLISH__ = '2018.09.09'  # 发布日期


_TEMP_DIR = os.path.abspath(os.path.dirname(__file__) + '/' +
                            '../../test_data/temp/call_chain_log/').replace('\\', '/')


# 不带任何入参，没有返回出参的函数
@CallChainTool.methon_call_chain(is_use_global_logger=True)
def func_case1_no_para(a):
    CallChainTool.get_global_logger().write_log('runing func_case1_no_para')
    time.sleep(0.01)
    return


class TestCallChainTool(unittest.TestCase):
    """
    测试CallChainTool类
    """

    def setUp(self):
        """
        启动测试执行的初始化
        """
        # 初始化日志类
        try:
            # 删除临时日志
            FileTool.remove_files(path=_TEMP_DIR + '/log/', regex_str='test_case1*')
        except Exception as e:
            pass

        # 初始化
        _logger = Logger(
            conf_file_name=_TEMP_DIR + '/test_call_chain.json',
            logger_name=EnumLoggerName.ConsoleAndFile.value,
            logfile_path=_TEMP_DIR + '/log/test_case1.log',
            is_create_logfile_by_day=True,
            is_print_file_name=True,
            is_print_fun_name=True
        )
        CallChainTool.set_global_logger(_logger)

    def tearDown(self):
        """
        结束测试执行的销毁
        """
        pass

    def test_search(self):
        """
        测试静态方法search
        """
        # 不带任何入参的对象
        func_case1_no_para('44')


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    unittest.main()

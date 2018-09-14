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
from HiveNetLib.generic import CResult

__MOUDLE__ = 'test_call_chain_tool'  # 模块名
__DESCRIPT__ = u'测试调用链工具模块'  # 模块描述
__VERSION__ = '0.1.0'  # 版本
__AUTHOR__ = u'黎慧剑'  # 作者
__PUBLISH__ = '2018.09.09'  # 发布日期


_TEMP_DIR = os.path.abspath(os.path.dirname(__file__) + '/' +
                            '../../test_data/temp/call_chain_log/').replace('\\', '/')


# 不带任何入参，没有返回出参的函数
@CallChainTool.methon_call_chain(is_use_global_logger=True)
def func_case1_no_para():
    CallChainTool.get_global_logger().write_log('runing func_case1_no_para')
    time.sleep(0.001)
    return


# 不带任何入参，返回CResult出参的函数
@CallChainTool.methon_call_chain(is_use_global_logger=True, is_print_back=True)
def func_case1_no_para_with_cresult():
    CallChainTool.get_global_logger().write_log('runing func_case1_no_para_with_cresult')
    time.sleep(0.001)
    _ret = CResult()
    _ret.self_para = [3, 'str']
    return _ret


# 带固定入参的函数
@CallChainTool.methon_call_chain(is_use_global_logger=True, key_para=(0, 1,), print_in_para=(2,), print_out_para=(1,), is_print_back=True)
def func_case1_fix_para(a, b, c):
    CallChainTool.get_global_logger().write_log('runing func_case1_fix_para(a=%s, b=%s, c=%s)' % (a, b, c))
    time.sleep(0.001)
    return


# 标准输入模式
@CallChainTool.methon_call_chain(is_use_global_logger=True, is_standard_def=True, key_para=(0, 1, 'k1'))
def func_case1_standard(*args, **kwargs):
    CallChainTool.get_global_logger().write_log(
        'runing func_case1_standard : %s : %s' % (str(args), str(kwargs)))
    time.sleep(0.001)
    return


# 半标准输入模式
@CallChainTool.methon_call_chain(is_use_global_logger=True, key_para=(0, 1, 'k1'))
def func_case1_half_standard(a, b, **kwargs):
    CallChainTool.get_global_logger().write_log(
        'runing func_case1_half_standard : a=%s, b=%s : %s' % (str(a), str(b), str(kwargs)))
    time.sleep(0.001)
    return


# 嵌套调用，产生调用链
@CallChainTool.methon_call_chain(is_use_global_logger=True, key_para=('k1'))
def func_case1_call_1(a, b, **kwargs):
    CallChainTool.get_global_logger().write_log(
        'runing func_case1_call_1 : a=%s, b=%s : %s' % (str(a), str(b), str(kwargs)))
    time.sleep(0.001)
    # 执行2
    func_case1_call_2('2a', '2b', '2c', k1=kwargs['k1'])
    # 执行3
    func_case1_call_3(k1=kwargs['k1'])
    return


@CallChainTool.methon_call_chain(is_use_global_logger=True, key_para=('k1'))
def func_case1_call_2(a, b, c, **kwargs):
    CallChainTool.get_global_logger().write_log(
        'runing func_case1_call_2 : a=%s, b=%s, c=%s: %s' % (str(a), str(b), str(c), str(kwargs)))
    time.sleep(0.001)
    # 执行4
    func_case1_call_4('4a', '4b', '4c', k1=kwargs['k1'])
    return


@CallChainTool.methon_call_chain(is_use_global_logger=True, key_para=('k1'))
def func_case1_call_3(**kwargs):
    CallChainTool.get_global_logger().write_log(
        'runing func_case1_call_3 : %s' % (str(kwargs)))
    time.sleep(0.001)
    return


@CallChainTool.methon_call_chain(is_use_global_logger=True, key_para=('k1'))
def func_case1_call_4(a, b, c, **kwargs):
    CallChainTool.get_global_logger().write_log(
        'runing func_case1_call_4 : a=%s, b=%s, c=%s: %s' % (str(a), str(b), str(c), str(kwargs)))
    time.sleep(0.001)
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

        # 初始化日志类
        _logger = Logger(
            conf_file_name=_TEMP_DIR + '/../../call_chain_tool/test_call_chain.json',
            logger_name=EnumLoggerName.ConsoleAndFile.value,
            logfile_path=_TEMP_DIR + '/log/test_case1.log',
            is_create_logfile_by_day=True,
            is_print_file_name=True,
            is_print_fun_name=True
        )
        # 设置为全局使用
        CallChainTool.set_global_logger(_logger)

    def tearDown(self):
        """
        结束测试执行的销毁
        """
        pass

    def test_methon(self):
        """
        测试静态方法方法
        """
        # 不带任何入参的对象
        print('\n不带参数调用')
        func_case1_no_para()
        print('\n\n不带参数有返回结果')
        func_case1_no_para_with_cresult()
        print('\n\n带固定个数输入参数')
        func_case1_fix_para('a-str', 'b-str', 'c-str')
        print('\n\n标准模式')
        func_case1_standard('arg1', 'arg2', k1='kw1', k2='kw2')
        print('\n\n半标准模式')
        func_case1_half_standard('arg1', 'arg2', k1='kw1', k2='kw2')
        print('\n\n调用链执行')
        func_case1_call_1('1a', '1b', k1='testk1')


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    unittest.main()

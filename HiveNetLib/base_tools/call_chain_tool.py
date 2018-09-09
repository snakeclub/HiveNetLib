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

import os
import sys
import uuid
import datetime
sys.path.append(os.path.abspath(os.path.dirname(__file__)+'/'+'../..'))
from HiveNetLib.generic_enum import EnumLogLevel
from HiveNetLib.base_tools.run_tool import RunTool

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
    def set_global_logger(logger):
        """
        设置全局使用的logger对象

        @param {object} logger - logger对象,传入对象需满足:
            1、标准logging的logger对象
            2、自定义的日志类对象，但应实现info、warning、error等标准方法

        """
        RunTool.set_global_var('CALL_CHAIN_TOOL_LOGGER', logger)

    @staticmethod
    def get_global_logger():
        """
        获取全局使用的logger对象

        @returns {object} - 全局使用的logger对象

        """
        return RunTool.get_global_var('CALL_CHAIN_TOOL_LOGGER')

    @staticmethod
    def generate_trace_id():
        """
        生成全局唯一的trace_id
        注：目前使用uuid1的方法

        @returns {string} - trace_id

        """
        return str(uuid.uuid1())

    @staticmethod
    def methon_call_chain(logger=None, trace_id=None, key_para=(), print_in_para=(), is_print_back=False,
                          is_use_global_logger=False, log_level=EnumLogLevel.INFO):
        """
        模块方法调用链修饰符

        @param {object} logger=None - 日志对象，如果为None代表不需要输出日志，传入对象需满足:
            1、标准logging的logger对象
            2、自定义的日志类对象，但应实现info、warning、error等标准方法
        @param {string} trace_id=None - 调用链追踪ID，None代表沿用上一调用函数传递的ID；传入值则以该值向下传递
            注：如果找不到上一调用函数传递的ID，并且修饰符也没有传入值，则自动生成一个唯一的trace_id
        @param {tuple} key_para=() - 定义业务层面唯一标识业务的入参参数名列表，从所修饰函数中获取对应的参数值进行打印
        @param {tuple} print_in_para=() - 定义需要打印的入参参数值
        @param {bool} is_print_back=False - 是否打印返回值信息，直接调用返回值的__str__方法
        @param {bool} is_use_global_logger=False - 当logger=None时，是否使用全局logger对象
            注：通过CallChainTool.set_global_logger进行设置
        @param {EnumLogLevel} log_level=EnumLogLevel.INFO - 打印日志的级别

        @returns {object} - 返回所修饰函数的返回值

        @example

        """
        def wrapper1(func):
            """
            第一层修饰函数，设置两层的目的是支持参数传入

            @param {function} func - 所修饰的函数

            """
            def wrapper2(*args, **kwargs):
                """
                第二层修饰函数，用于向所修饰函数传入参数
                """
                # 处理日志对象和trace_id
                _logger = logger
                if _logger is None and is_use_global_logger:
                    # 使用全局logger
                    _logger = CallChainTool.get_global_logger()

                if _logger is None:
                    # 没有配置日志类，不做任何封装处理，直接调用和返回
                    return func(args, kwargs)
                else:
                    _start_time = datetime.datetime.now()
                    try:
                        _back = func(args, kwargs)
                    except Exception as e:
                        # 记录异常日志
                        _end_time = datetime.datetime.now()
                        raise e
                    _end_time = datetime.datetime.now()
                    print('use:' + str((_end_time - _start_time).total_seconds()))
                    return _back
            return wrapper2
        return wrapper1

    @staticmethod
    def api_call_chain(f):
        """
        api接口调用链修饰符
        """
        pass


@CallChainTool.methon_call_chain()
def test_fun(a=10, b='33'):
    print('test_fun:' + str(a) + ":" + str(b))


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    # 打印版本信息
    print(('模块名：%s  -  %s\n'
           '作者：%s\n'
           '发布日期：%s\n'
           '版本：%s' % (__MOUDLE__, __DESCRIPT__, __AUTHOR__, __PUBLISH__, __VERSION__)))

    test_fun(a=33, b='3343')

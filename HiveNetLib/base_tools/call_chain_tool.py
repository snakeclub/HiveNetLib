#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
#
# Copyright 2018 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
调用链日志处理工具
@module call_chain_tool
@file call_chain_tool.py
"""

import os
import sys
import uuid
import datetime
import traceback
sys.path.append(os.path.abspath(os.path.dirname(__file__)+'/'+'../..'))
from HiveNetLib.simple_log import EnumLogLevel
from HiveNetLib.base_tools.run_tool import RunTool
from HiveNetLib.base_tools.string_tool import StringTool


__MOUDLE__ = 'call_chain_tool'  # 模块名
__DESCRIPT__ = u'调用链日志处理工具'  # 模块描述
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
        return str(uuid.uuid1()).replace('-', '')  # 不带-更容易查找日志

    @staticmethod
    def methon_call_chain(logger=None, trace_id=None, trace_level=None, call_id=None,
                          parent_id=None, key_para=(), print_in_para=(),
                          print_out_para=(), is_print_back=False,
                          is_use_global_logger=True, log_level=EnumLogLevel.INFO,
                          is_standard_def=False):
        """
        模块方法调用链修饰符

        @param {object} logger=None - 日志对象，如果为None代表不需要输出日志，传入对象需满足:
            1、标准logging的logger对象
            2、自定义的日志类对象，但应实现info、warning、error等标准方法
        @param {string} trace_id=None - 调用链追踪ID，None代表沿用上一调用函数传递的ID；传入值则以该值向下传递
            注：如果找不到上一调用函数传递的ID，并且修饰符也没有传入值，则自动生成一个唯一的trace_id
        @param {int[]} trace_level=None - 函数调用层级，是一个只有一个int变量的数组，trace_level[0]为当前的执行层级
            注：该变量每执行一次函数应该+1
        @param {string} call_id=None - 当前函数的执行ID，如果未传入，则自动生成一个执行ID
        @param {string} parent_id=None - 上一函数的执行ID，由上一函数传入，或自动获取
        @param {tuple} key_para=() - 定义业务层面唯一标识业务的入参参数名列表，从所修饰函数中获取对应的参数值进行打印
            注意：如果列表中的对象是string，则从函数入参的kwargs参数中获取；如果对象是int，则从args中取指定位置的值
        @param {tuple} print_in_para=() - 定义需要打印的入参参数值
            注意：如果列表中的对象是string，则从函数入参的kwargs参数中获取；如果对象是int，则从args中取指定位置的值
        @param {tuple} print_out_para=() - 定义需要打印的出参参数值（改写入参的情况）
            注意：如果列表中的对象是string，则从函数入参的kwargs参数中获取；如果对象是int，则从args中取指定位置的值
        @param {bool} is_print_back=False - 是否打印返回值信息，直接调用返回值的__str__方法
        @param {bool} is_use_global_logger=True - 当logger=None时，是否使用全局logger对象
            注：通过CallChainTool.set_global_logger进行设置
        @param {EnumLogLevel} log_level=EnumLogLevel.INFO - 打印日志的级别
        @param {bool} is_standard_def=False - 所修饰是否标准定义格式
            注：标准定义格式指入参固定为 func(*args, **kwargs)，这样修饰函数处理过程中无需判断入参格式，提升处理效率

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
                    return CallChainTool.__call_func(func, args, kwargs, is_standard_def)
                else:
                    # 获取各类信息
                    _start_time = datetime.datetime.now()
                    _call_id = call_id
                    if _call_id is None:
                        _call_id = CallChainTool.generate_trace_id()  # 生成执行ID
                    _file_path, _file_name = os.path.split(sys._getframe().f_code.co_filename)
                    _fun_name = str(func.__name__)
                    _trace_id = trace_id

                    # 处理trace_id，优先获取当前函数参数，没有则找修饰函数传参，没有再找父函数的参数，再没有则自己创建
                    _parent_fun = sys._getframe().f_back
                    _parent_fun_name = str(_parent_fun.f_code.co_name)
                    if 'trace_id' in kwargs.keys():
                        _trace_id = kwargs['trace_id']  # 从上一个函数调用传入了追踪ID，优先使用这个

                    if _trace_id == '' or _trace_id is None and _parent_fun_name != '<module>':
                        # 尝试获取上一个调用函数参数中的trace_id
                        _trace_id = CallChainTool.__get_parent_fun_para_value(
                            _parent_fun, 'trace_id')

                    if _trace_id == '' or _trace_id is None:
                        # 都没有找到，只能当作自己是第1个调用的函数
                        _trace_id = _call_id

                    # 处理trace_level
                    _trace_level = trace_level
                    if 'trace_level' in kwargs.keys():
                        _trace_level = kwargs['trace_level']  # 从上一个函数调用传入了追踪层级，优先使用这个

                    if _trace_level is None and _parent_fun_name != '<module>':
                        # 尝试获取上一个调用函数参数中的trace_level
                        _trace_level = CallChainTool.__get_parent_fun_para_value(
                            _parent_fun, 'trace_level')

                    if _trace_level is None:
                        # 都没有找到，只能当作自己是第1个调用的函数
                        _trace_level = [0]
                    # 自加1
                    _trace_level[0] = _trace_level[0] + 1

                    # 处理parent_call_id
                    _parent_call_id = parent_id
                    if 'parent_id' in kwargs.keys():
                        _parent_call_id = kwargs['parent_id']  # 从上一个函数调用传入了追踪层级，优先使用这个
                    if _parent_call_id is None and _parent_fun_name != '<module>':
                        _parent_call_id = CallChainTool.__get_parent_fun_para_value(
                            _parent_fun, 'call_id')
                    if _parent_call_id is None:
                        _parent_call_id = ''

                    # 生成trace日志信息项
                    _trace_item = '%s:%s:%s:%s:%s:%s' % (
                        _trace_id, _call_id, _parent_call_id, str(_trace_level[0]), _file_name, _fun_name)

                    # 生成日志信息
                    _log_obj = {'key': {}, 'para': {}}
                    for _key in key_para:
                        _log_obj['key'][_key] = str(
                            CallChainTool.__get_value_from_para(_key, args, kwargs))
                    for _key in print_in_para:
                        _log_obj['para'][_key] = str(
                            CallChainTool.__get_value_from_para(_key, args, kwargs))

                    # 打印调用信息
                    _log_str = '[TRACE:%s]%s' % (_trace_item, str(_log_obj))
                    # 日志函数处理, 简化处理代码
                    _log_fun = {
                        EnumLogLevel.INFO: _logger.info,
                        EnumLogLevel.DEBUG: _logger.debug,
                        EnumLogLevel.WARNING: _logger.warning,
                        EnumLogLevel.ERROR: _logger.error,
                        EnumLogLevel.CRITICAL: _logger.critical
                    }
                    _log_fun[log_level](_log_str)

                    # 执行函数，把trace_id和trace_level放入参数中
                    kwargs['trace_id'] = _trace_id
                    kwargs['trace_level'] = _trace_level
                    kwargs['call_id'] = _call_id
                    kwargs['parent_id'] = _parent_call_id
                    try:
                        _back = CallChainTool.__call_func(func, args, kwargs, is_standard_def)
                    except Exception as e:
                        # 记录异常日志
                        _end_time = datetime.datetime.now()
                        _use = (_end_time - _start_time).total_seconds()
                        _log_str = '[TRACE:%s][USE:%ss][EX:%s]%s' % (
                            _trace_item, str(_use), str(type(e)), traceback.format_exc())
                        _log_fun[log_level](_log_str)
                        raise e

                    # 执行完成
                    _end_time = datetime.datetime.now()
                    _use = (_end_time - _start_time).total_seconds()
                    _log_back = ''
                    if is_print_back:
                        _log_obj = {'return': str(_back), 'out_para': {}}
                        for _key in print_out_para:
                            _log_obj['out_para'][_key] = str(
                                CallChainTool.__get_value_from_para(_key, args, kwargs))
                        _log_back = str(_log_obj)
                    # 打印调用信息
                    _log_str = '[TRACE:%s][USE:%ss]%s' % (_trace_item, str(_use), _log_back)
                    _log_fun[log_level](_log_str)
                    return _back
            return wrapper2
        return wrapper1

    @staticmethod
    def api_get_trace_info(msg, proto_msg=None):
        """
        从接口报文对象中获取调用链的信息
        TRACE_ID（追踪ID）、CALL_ID（执行ID）、PARENT_CALL_ID（父调用函数的执行ID）、
        TRACE_LEVEL（调用层级，每CALL一个下级函数+1）

        @returns {dict} - 返回对应的字典，如果值不存在，对应的参数值为None
        """
        pass

    @staticmethod
    def __call_func(func, args, kwargs, is_standard_def):
        """
        内部函数，根据传入参数处理实际的函数调用

        @param {function} func - 要执行的函数
        @param {tuple} args - 不带参数名的参数列表
        @param {dict} kwargs - 带参数名的参数列表
        @param {bool} is_standard_def - 是否标准定义的修饰符函数

        @returns {object} - 返回函数的执行结果

        """
        if is_standard_def:
            # 标准修饰符函数，直接调用无需特殊处理
            return func(*args, **kwargs)
        else:
            # 非标准修饰符函数，通过动态参数传入执行
            _exec_str = 'func('
            # 拼接
            _i = 0
            while _i < len(args):
                _exec_str = _exec_str + ('args[%s],' % (str(_i)))
                _i = _i + 1
            _exec_str_2 = _exec_str.rstrip(',') + ')'  # 这个脚本用于在参数传入执行出错的情况下重新执行
            for _key in kwargs.keys():
                _exec_str = _exec_str + ('%s=kwargs[\'%s\'],' % (_key, _key))
            # 去掉最后一个逗号
            _exec_str = _exec_str.rstrip(',') + ')'
            # 执行并返回
            try:
                return eval(_exec_str)
            except TypeError:
                return eval(_exec_str_2)

    @staticmethod
    def __get_value_from_para(index, args, kwargs):
        """
        从函数入参值中获取指定的值

        @param {string/int} index - key值或位置索引
        @param {tuple} args - 动态位置入参
        @param {dict} kwargs - 动态key-value入参

        @returns {object} - 取到的值，如果取不到则返回None

        """
        try:
            if type(index) == int:
                return args[index]
            else:
                return kwargs[index]
        except Exception:
            return None

    @staticmethod
    def __get_parent_fun_para_value(parent_fun_frame, para_name):
        """
        从父函数堆栈获取参数值

        @param {object} parent_fun_frame - 父函数堆栈（sys._getframe().f_back）
        @param {string} para_name - 参数名

        @returns {object} - 获取到的参数值，如果找不到返回None

        """
        _para_value = None
        if hasattr(parent_fun_frame, 'f_locals'):
            if para_name in parent_fun_frame.f_locals.keys():
                _para_value = parent_fun_frame.f_locals[para_name]
            elif 'kwargs' in parent_fun_frame.f_locals.keys() and para_name in parent_fun_frame.f_locals['kwargs']:
                _para_value = parent_fun_frame.f_locals['kwargs'][para_name]
        return _para_value


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    # 打印版本信息
    print(('模块名：%s  -  %s\n'
           '作者：%s\n'
           '发布日期：%s\n'
           '版本：%s' % (__MOUDLE__, __DESCRIPT__, __AUTHOR__, __PUBLISH__, __VERSION__)))

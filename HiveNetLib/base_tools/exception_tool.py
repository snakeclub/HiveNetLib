#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
#
# Copyright 2018 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
异常处理工具

@module exception_tool
@file exception_tool.py

"""

import os
import sys
import copy
import traceback
from contextlib import contextmanager
sys.path.append(os.path.abspath(os.path.dirname(__file__)+'/'+'../..'))
from HiveNetLib.simple_log import EnumLogLevel
from HiveNetLib.generic import CResult
from HiveNetLib.base_tools.run_tool import RunTool


__MOUDLE__ = 'exception_tool'  # 模块名
__DESCRIPT__ = u'异常处理工具'  # 模块描述
__VERSION__ = '0.1.0'  # 版本
__AUTHOR__ = u'黎慧剑'  # 作者
__PUBLISH__ = '2018.08.29'  # 发布日期


class ExceptionTool(object):
    """
    异常处理工具,提供便捷的异常处理模式

    """

    @staticmethod
    @contextmanager
    def ignored(expect=(), logger=None, self_log_msg='', force_log_level=None):
        """
        忽略指定异常，简化异常捕获代码，利用该函数忽略指定的异常，详细说明如下：
            1、对于指定忽略的异常，忽略不处理（如果指定logger则会进行日志输出，使用WARNING级别）
            2、对于非指定的异常，仍抛出异常（如果指定logger则会进行日志输出，使用ERROR级别）
            3、输出的日志为self_log_msg+'\n'+trace_str


        @param {tuple} expect=() - 需要忽略的异常列表，例如(ZeroDivisionError, ValueError)
        @param {object} logger=None - 日志对象，如果为None代表不需要输出日志，传入对象需满足:
            1、标准logging的logger对象
            2、自定义的日志类对象，但应实现warning、error的标准方法
        @param {string} self_log_msg='' - 需要输出的自定义日志信息
        @param {EnumLogLevel} force_log_level=None - 强制遇到所有异常统一按指定的日志级别输出

        @example
            with ignored((ZeroDivisionError, ValueError), logger, '执行XX出现异常'):
                count = 1 / 0
                count = count + 10000

        """
        try:
            yield
        except expect as ex:
            # 匹配到指定异常，输出日志
            _log_level = EnumLogLevel.WARNING
            if force_log_level is not None:
                _log_level = force_log_level
            ExceptionTool.__print_log(logger=logger, self_log_msg='[EX:%s]%s' % (str(type(ex)), self_log_msg),
                                      trace_str=traceback.format_exc(), log_level=_log_level)
            pass
        except Exception as e:
            # 其他异常，输出日志并抛出异常
            _log_level = EnumLogLevel.ERROR
            if force_log_level is not None:
                _log_level = force_log_level
            ExceptionTool.__print_log(logger=logger, self_log_msg='[EX:%s]%s' % (str(type(e)), self_log_msg),
                                      trace_str=traceback.format_exc(), log_level=_log_level)
            raise sys.exc_info()[1]

    @staticmethod
    @contextmanager
    def ignored_all(unexpect=(), logger=None, self_log_msg='', force_log_level=None):
        """
        忽略除指定以外的所有异常,简化异常捕获代码，利用该函数忽略指定以外的所有异常，详细说明如下：
            1、对于指定以外的异常，忽略不处理（如果指定logger则会进行日志输出，使用WARNING级别）
            2、对于指定的异常，仍抛出异常（如果指定logger则会进行日志输出，使用ERROR级别）
            3、输出的日志为self_log_msg+'\n'+trace_str

        @param {tuple} unexpect=() - 指定不能忽略的异常列表，例如(ZeroDivisionError, ValueError)
        @param {object} logger=None - 日志对象，如果为None代表不需要输出日志，传入对象需满足:
            1、标准logging的logger对象
            2、自定义的日志类对象，但应实现warning、error的标准方法
        @param {string} self_log_msg='' - 需要输出的自定义日志信息
        @param {EnumLogLevel} force_log_level=None - 强制遇到所有异常统一按指定的日志级别输出

        @example
            with ignored_all((ZeroDivisionError, ValueError), logger, '执行XX出现异常'):
                count = 1 / 0
                count = count + 10000

        """
        try:
            yield
        except unexpect as ue:
            # 匹配到指定异常，输出日志并抛出异常
            _log_level = EnumLogLevel.ERROR
            if force_log_level is not None:
                _log_level = force_log_level
            ExceptionTool.__print_log(logger=logger, self_log_msg='[EX:%s]%s' % (str(type(ue)), self_log_msg),
                                      trace_str=traceback.format_exc(), log_level=_log_level)
            raise sys.exc_info()[1]
        except Exception as e:
            # 其他异常，输出日志并忽略
            _log_level = EnumLogLevel.WARNING
            if force_log_level is not None:
                _log_level = force_log_level
            ExceptionTool.__print_log(logger=logger, self_log_msg='[EX:%s]%s' % (str(type(e)), self_log_msg),
                                      trace_str=traceback.format_exc(), log_level=_log_level)
            pass

    @staticmethod
    @contextmanager
    def ignored_cresult(result_obj=None, error_map={}, expect=(), expect_no_log=False, expect_use_error_map=True,
                        logger=None, self_log_msg='', force_log_level=None, i18n_obj=None):
        """
        忽略异常并设置CResult对象,简化异常捕获代码，利用该函数忽略指定的异常，并设置传入的通用结果对象，详细说明如下：
            1、对于指定忽略的异常，忽略不处理，结果为成功（如果指定logger则会进行日志输出，使用WARNING级别）
            2、对于非指定的异常，不抛出异常，结果为失败（如果指定logger则会进行日志输出，使用ERROR级别）
            3、输出的日志为self_log_msg+'\n'+trace_str
            4、根据error_map的映射关系设置错误码和错误信息

        @param {CResult} result_obj=None - 需要设置的错误类对象(对象值会被修改)
        @param {dict} error_map={} - 用来设置错误类对象的映射表，具体说明如下：
            1、key为异常类，value为(code, msg)的错误码、错误描述二元组，如果msg=None代表使用标准错误码
            2、应有一个'DEFAULT'的key，代表没有匹配上的异常映射，默认value为('29999', None)
            3、应有一个'SUCESS'的key，代表成功的映射，默认value为('00000', None)
        @param {tuple} expect=() - 需要忽略的异常列表，例如(ZeroDivisionError, ValueError)
        @param {bool} expect_no_log=False - 忽略异常列表是否不打印日志
        @param {bool} expect_use_error_map=True - 忽略异常列表所匹配到的异常，所返回错误码是否使用错误码映射表:
            如果在映射表中匹配上则返回映射表的错误码；匹配不上则返回成功
        @param {object} logger=None - 日志对象，如果为None代表不需要输出日志，传入对象需满足:
            1、标准logging的logger对象
            2、自定义的日志类对象，但应实现warning、error的标准方法
        @param {string} self_log_msg='' - 需要输出的自定义日志信息
        @param {EnumLogLevel} force_log_level=None - 强制遇到所有异常统一按指定的日志级别输出
        @param {object} i18n_obj=None - 国际化类的实例对象，该对象需实现translate方法

        @example
            result = CResult()
            with ExceptionTools.ignored_CResult(result_obj=result, error_map={},expect=(),logger=None,self_log_msg=''):
                i = 1/0
                i = i + 1000
            print(str(result))

        """
        _error_map = copy.deepcopy(error_map)
        try:
            # 初始化对象
            if result_obj is None:
                result_obj = CResult(code='00000', msg=None, i18n_obj=i18n_obj)

            # 确保映射表中有默认值
            if 'SUCESS' not in _error_map.keys():
                _error_map['SUCESS'] = ('00000', None)
            if 'DEFAULT' not in _error_map.keys():
                _error_map['DEFAULT'] = ('29999', None)
            # 执行with对应的脚本
            yield
        except expect as ex:
            # 匹配到指定异常，输出日志
            if not expect_no_log:
                _log_level = EnumLogLevel.WARNING
                if force_log_level is not None:
                    _log_level = force_log_level
                ExceptionTool.__print_log(logger=logger, self_log_msg='[EX:%s]%s' % (str(type(ex)), self_log_msg),
                                          trace_str=traceback.format_exc(), log_level=_log_level)
            # 按成功处理
            _error = sys.exc_info()
            _trace_str = traceback.format_exc()
            if expect_use_error_map and _error[0] in _error_map.keys():
                result_obj.change_code(code=_error_map[_error[0]][0], msg=_error_map[_error[0]][1])
                result_obj.error = _error
                result_obj.trace_str = _trace_str
            else:
                # 按成功处理
                pass
        except Exception as e:
            # 其他异常，输出日志，获取失败信息
            _error = sys.exc_info()
            _trace_str = traceback.format_exc()
            if _error[0] in _error_map.keys():
                result_obj.change_code(code=_error_map[_error[0]][0], msg=_error_map[_error[0]][1])
                result_obj.error = _error
                result_obj.trace_str = _trace_str
            else:
                # 其他失败
                result_obj.change_code(code=_error_map['DEFAULT'][0], msg=_error_map['DEFAULT'][1])
                result_obj.error = _error
                result_obj.trace_str = _trace_str

            _log_level = EnumLogLevel.ERROR
            if force_log_level is not None:
                _log_level = force_log_level
            ExceptionTool.__print_log(logger=logger, self_log_msg='[EX:%s]%s' % (str(type(e)), self_log_msg),
                                      trace_str=result_obj.trace_str, log_level=_log_level)

    # 内部函数定义
    @staticmethod
    def __print_log(logger=None, self_log_msg='', trace_str='', log_level=EnumLogLevel.WARNING):
        """
        内部进行日志输出处理， 调用日志对象进行日志输出处理

        @param {object} logger=None - 日志对象，如果为None代表不需要输出日志，传入对象需满足:
            1、标准logging的logger对象
            2、自定义的日志类对象，但应实现warning、error等的标准方法
        @param {string} self_log_msg='' - 需要输出的自定义日志信息
        @param {string} trace_str='' - 错误追踪堆栈日志，异常时的traceback.format_exc()
        @param {EnumLogLevel} log_level=EnumLogLevel.WARNING - 需要输出的自定义日志级别

        """
        if logger is not None:
            # 要输出的日志内容
            _log_str = ''
            if len(self_log_msg) > 0:
                _log_str = self_log_msg + '\n' + trace_str
            else:
                _log_str = trace_str
            # 输出日志
            RunTool.writelog_by_level(logger=logger, log_str=_log_str, log_level=log_level)


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    # 打印版本信息
    print(('模块名：%s  -  %s\n'
           '作者：%s\n'
           '发布日期：%s\n'
           '版本：%s' % (__MOUDLE__, __DESCRIPT__, __AUTHOR__, __PUBLISH__, __VERSION__)))

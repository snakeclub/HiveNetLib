#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
#
# Copyright 2018 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
运行参数处理通用工具
@module run_tool
@file run_tool.py
"""

import sys
import os
import traceback
from contextlib import contextmanager
sys.path.append(os.path.abspath(os.path.dirname(__file__)+'/'+'../..'))
from HiveNetLib.simple_log import EnumLogLevel
from HiveNetLib.base_tools.file_tool import FileTool


__MOUDLE__ = 'run_tool'  # 模块名
__DESCRIPT__ = u'运行参数处理通用工具'  # 模块描述
__VERSION__ = '0.1.0'  # 版本
__AUTHOR__ = u'黎慧剑'  # 作者
__PUBLISH__ = '2018.08.29'  # 发布日期


# 全局变量
# 用于存储打开的单进程控制文件句柄的字典（dict）
# key为文件路径，value为句柄变量
# 该变量为全局变量，以支持在不同线程间访问
SINGLE_PROCESS_PID_FILE_LIST = dict()


# 全局变量
# 用于存储全局变量的值
# key为全局变量名（string），value为全局变量的值
RUNTOOL_GLOBAL_VAR_LIST = dict()


class RunTool(object):
    """
    运行参数处理通用类
    提供各类运行环境处理相关的常用工具函数（静态方法）
    """

    @staticmethod
    def get_kv_opts():
        """
        获取Key=Value格式的命令行输入参数

        @returns {dict} - 命令行参数字典：key为参数名，value为参数值

        @example
            命令行# python ggeneric.py key1=value1 key2=value2 key3="value 3" "key 4"=value4 "key 5"="value 5"
            input_para = RunTools.get_kv_opts()
        """
        # 建立要返回的字典
        _dict = {}
        # 遍历参数
        i = 1
        _argv_count = len(sys.argv)
        while i < _argv_count:
            _pair = str(sys.argv[i]).split("=")
            _key = _pair[0]
            _value = ""
            if len(_pair) > 1:
                _value = sys.argv[i][len(_key) + 1:]
            _dict[_key] = _value
            i = i + 1
        return _dict

    @staticmethod
    def var_defined(name_str):
        """
        判断变量是否已定义

        @param {string} name_str - 变量名（注意是名字字符串，不是传入变量）

        @returns {bool} - 是否已定义，True-已定义，False-未定义
        """
        try:
            type(eval(name_str))
        except Exception as e:
            return False
        else:
            return True

    @staticmethod
    def writelog_by_level(logger, log_str, log_level=EnumLogLevel.INFO):
        """
        根据日志级别调用日志输出,根据日志级别调用日志类的不同方法，简化日志级别的判断处理

        @param {object} logger - 日志对象，如果为None代表不需要输出日志，传入对象需满足:
            1、标准logging的logger对象
            2、自定义的日志类对象，但应实现warning、error的标准方法
        @param {string} log_str - 需输出的日志内容
        @param {EnumLogLevel} log_level=EnumLogLevel.INFO - 输出日志级别

        """
        if log_level == EnumLogLevel.DEBUG:
            logger.debug(log_str)
        elif log_level == EnumLogLevel.WARNING:
            logger.warning(log_str)
        elif log_level == EnumLogLevel.ERROR:
            logger.error(log_str)
        elif log_level == EnumLogLevel.CRITICAL:
            logger.critical(log_str)
        else:
            logger.info(log_str)

    @staticmethod
    def set_global_var(key, value):
        """
        设置全局变量的值，后续可以通过Key获取到指定的值，如果如果key存在将覆盖

        @param {string} key - 要设置的全局变量key值
        @param {object} value - 要设置的全局变量值
        """
        global RUNTOOL_GLOBAL_VAR_LIST
        RUNTOOL_GLOBAL_VAR_LIST[key] = value

    @staticmethod
    def get_global_var(key):
        """
        根据key获取全局变量的值，如果找不到key则返回None

        @param {string} key - 要获取的全局变量key值

        @returns {object} - 全局变量的值，如果找不到key则返回None
        """
        global RUNTOOL_GLOBAL_VAR_LIST
        if key in RUNTOOL_GLOBAL_VAR_LIST.keys():
            return RUNTOOL_GLOBAL_VAR_LIST[key]

        return None

    @staticmethod
    def del_global_var(key):
        """
        删除key值对应的全局变量

        @param {string} key - 要删除的全局变量key值

        """
        global RUNTOOL_GLOBAL_VAR_LIST
        if key in RUNTOOL_GLOBAL_VAR_LIST.keys():
            del RUNTOOL_GLOBAL_VAR_LIST[key]

    @staticmethod
    def del_all_global_var():
        """
        清空所有全局变量
        """
        global RUNTOOL_GLOBAL_VAR_LIST
        RUNTOOL_GLOBAL_VAR_LIST.clear()

    @staticmethod
    def single_process_get_lockfile(process_name='', base_path=''):
        """
        获取进程锁处理锁文件路径
        进程锁处理的辅助函数，获取指定进程的锁文件名（含路径）

        @param {string} process_name='' - 进程锁的进程名，默认值为''；如果为''代表获取执行程序的模块名
        @param {string} base_path='' - 进程锁文件指定的路径，默认值为''；如果为''代表获取执行程序的模块文件目录

        @returns {string} - 锁文件名（含路径）

        """
        _process_name = process_name
        _base_path = base_path
        if not len(_process_name) > 0:
            # 默认取运行的程序名
            _process_name = FileTool.get_exefile_name_no_ext()
        if not len(_base_path) > 0:
            # 默认取运行程序目录
            _base_path = FileTool.get_exefile_path() + os.sep
        else:
            _base_path = os.path.realpath(_base_path)
            if not os.path.isdir(_base_path):
                # 如果是文件的情况下，拿文件对应的目录
                _base_path = os.path.split(os.path.realpath(_base_path))[0]
            _base_path = _base_path + os.sep
        return _base_path + _process_name + ".lock"  # 要建立锁的文件名

    @staticmethod
    def single_process_del_lockfile(process_name='', base_path=''):
        """
        强制删除进程锁文件
        进程锁处理的辅助函数，强制删除进程锁文件

        @param {string} process_name='' - 进程锁的进程名，默认值为''；如果为''代表获取执行程序的模块名
        @param {string} base_path='' - 进程锁文件指定的路径，默认值为''；如果为''代表获取执行程序的模块文件目录
        """
        try:
            _lock_file = RunTool.single_process_get_lockfile(
                process_name=process_name, base_path=base_path)
            if os.path.exists(_lock_file) and os.path.isfile(_lock_file):
                os.remove(_lock_file)
        except Exception as e:
            return

    @staticmethod
    def single_process_enter(process_name='', base_path='', is_try_del_lockfile=False):
        """
        获取进程锁：如果获取失败代表锁已被其他进程占有，可选择结束进程以控制同一时间只有一个进程执行

        @param {string} process_name='' - 进程锁的进程名，默认值为''；如果为''代表获取执行程序的模块名
        @param {string} base_path='' - 进程锁文件指定的路径，默认值为''；如果为''代表获取执行程序的模块文件目录
        @param {bool} is_try_del_lockfile=False - 是否尝试先删除锁文件（可以应对强制关闭进程未自动删除锁文件的情况）

        @returns {bool} - 是否获取进程锁成功：True - 获取成功并占用锁；False - 获取失败，应选择关闭进程

        @example
            get_process_lock = RunTool.single_process_enter("CFuntion","c:/test/")
            if not get_process_lock:
                print("已有一个进程在执行状态，结束本进程")
                exit(1)

            try:
                do something ...
            finally:
                RunTool.single_process_exit("CFuntion","c:/test/")

        """
        global SINGLE_PROCESS_PID_FILE_LIST
        if not RunTool.var_defined("SINGLE_PROCESS_PID_FILE_LIST"):
            SINGLE_PROCESS_PID_FILE_LIST = {}
        # 要建立锁的文件名
        _lock_file = RunTool.single_process_get_lockfile(
            process_name=process_name, base_path=base_path)
        # 尝试自动先删除锁文件
        if is_try_del_lockfile:
            RunTool.single_process_del_lockfile(process_name=process_name, base_path=base_path)
        # 尝试创建锁文件
        try:
            _pid = os.open(_lock_file, os.O_CREAT | os.O_EXCL | os.O_RDWR)
            SINGLE_PROCESS_PID_FILE_LIST[_lock_file] = _pid
        except OSError:
            return False
        else:
            return True

    @staticmethod
    def single_process_exit(process_name='', base_path=''):
        """
        结束进程锁控制:
            1、结束单进程控制，删除锁文件；
            2、注意必须在程序执行完后一定要调用这个函数，否则会导致一直锁住

        @param {string} process_name='' - 进程锁的进程名，默认值为''；如果为''代表获取执行程序的模块名
        @param {string} base_path='' - 进程锁文件指定的路径，默认值为''；如果为''代表获取执行程序的模块文件目录

        """
        global SINGLE_PROCESS_PID_FILE_LIST
        if not RunTool.var_defined("SINGLE_PROCESS_PID_FILE_LIST"):
            SINGLE_PROCESS_PID_FILE_LIST = {}
        # 要建立锁的文件名
        _lock_file = RunTool.single_process_get_lockfile(
            process_name=process_name, base_path=base_path)
        try:
            os.close(SINGLE_PROCESS_PID_FILE_LIST[_lock_file])
            os.remove(_lock_file)
            return
        except Exception as e:
            raise sys.exc_info()[1]

    @staticmethod
    @contextmanager
    def single_process_with(process_name='', base_path='', is_try_del_lockfile=False,
                            logger=None, log_level=EnumLogLevel.WARNING, exit_code=1):
        """
        单进程控制的with简单模式,封装with模式的调用方式来实现单进程控制

        @param {string} process_name='' - 进程锁的进程名，默认值为''；如果为''代表获取执行程序的模块名
        @param {string} base_path='' - 进程锁文件指定的路径，默认值为''；如果为''代表获取执行程序的模块文件目录
        @param {bool} is_try_del_lockfile=False - 是否尝试先删除锁文件（可以应对强制关闭进程未自动删除锁文件的情况）
        @param {object} logger=None - 日志对象，如果为None代表不需要输出日志，传入对象需满足:
            1、标准logging的logger对象
            2、自定义的日志类对象，但应实现warning、error等的标准方法
        @param {EnumLogLevel} log_level=EnumLogLevel.WARNING - 需要输出的自定义日志级别
        @param {int} exit_code=1 - 控制获取进程锁失败退出的错误码定义

        @example
            with RunTools.single_process_with():
                # 以下为需要执行的程序逻辑
        """
        _get_process_lock = RunTool.single_process_enter(process_name=process_name,
                                                         base_path=base_path, is_try_del_lockfile=is_try_del_lockfile)
        if not _get_process_lock:
            if logger is not None:
                # 打印日志
                _log_str = u'已存在一个"%s"进程在执行中，结束本进程' % process_name
                RunTool.writelog_by_level(logger=logger, log_str=_log_str, log_level=log_level)
            # 退出进程
            exit(exit_code)
        try:
            yield  # 处理程序逻辑
        finally:
            # 退出进程，打印日志
            if logger is not None:
                _log_str = u'进程"%s"结束退出，释放进程锁' % process_name
                RunTool.writelog_by_level(logger=logger, log_str=_log_str, log_level=log_level)
            try:
                RunTool.single_process_exit(process_name=process_name, base_path=base_path)
            except Exception as e:
                # 出现异常，写日志，同时抛出异常
                if logger is not None:
                    _log_str = u'进程"%s"结束时释放进程锁发生异常：%s' % (process_name, traceback.format_exc())
                    RunTool.writelog_by_level(logger=logger, log_str=_log_str, log_level=log_level)
                raise sys.exc_info()[1]


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    # 打印版本信息
    print(('模块名：%s  -  %s\n'
           '作者：%s\n'
           '发布日期：%s\n'
           '版本：%s' % (__MOUDLE__, __DESCRIPT__, __AUTHOR__, __PUBLISH__, __VERSION__)))

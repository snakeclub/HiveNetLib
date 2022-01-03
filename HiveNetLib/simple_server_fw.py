#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
#
# Copyright 2019 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
简单服务启停类框架

@module simple_server_fw
@file simple_server_fw.py
"""

import os
import sys
import time
import datetime
import threading
import logging
from enum import Enum
from abc import ABC, abstractmethod  # 利用abc模块实现抽象类
# 根据当前文件路径将包路径纳入，在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir)))
from HiveNetLib.generic import CResult, NullObj
from HiveNetLib.simple_i18n import _, get_global_i18n, init_global_i18n
from HiveNetLib.base_tools.exception_tool import ExceptionTool
from HiveNetLib.base_tools.run_tool import RunTool


__MOUDLE__ = 'simple_server_fw'  # 模块名
__DESCRIPT__ = u'简单服务启停类框架'  # 模块描述
__VERSION__ = '0.1.0'  # 版本
__AUTHOR__ = u'黎慧剑'  # 作者
__PUBLISH__ = '2019.05.27'  # 发布日期


class EnumServerRunStatus(Enum):
    """
    服务器运行状态

    @enum {string}

    """
    Stop = 'Stop'  # 停止
    Running = 'Running'  # 正在运行
    WaitStop = 'WaitStop'  # 等待停止
    WaitStart = 'WaitStart'  # 等待启动
    ForceStop = 'ForceStop'  # 强制停止


class SimpleServerFW(ABC):
    """
    简单服务启停类框架
    抽象服务启停的公共方法形成框架，并提供基本的处理功能，简化涉及服务启停功能编程的难度

    @example
        1、实现类应集成该类，例如 class XSever(SimpleServerFW):
        2、实现类根据所需重载以下几个函数：
            _start_server_self : 自定义服务启动函数
            _stop_server_predeal_self : 自定义服务停止前处理函数
            _stop_server_end_self : 自定义服务停止后处理函数
            _server_run_self : 自定义服务处理函数
    """

    #############################
    # 私有变量 - 子类可访问的变量
    #############################

    _logLevel = logging.INFO  # 外围传入的日志级别，根据该级别打印日志，例如传DEBUG可减少日志的输出
    _server_name = 'Service'  # 服务名，记录日志使用
    _server_log_prefix = 'SER'  # 服务日志记录前缀，记录日志使用，例如[SER-STARTING]...
    _trans_file_path = ''  # 国际化翻译文件路径
    _trans_file_prefix = ''  # 国际化翻译文件的前缀
    _trans_file_encoding = 'utf-8'  # 国际化翻译文件的编码

    #############################
    # 私有变量 - 只用于框架内部处理的变量
    #############################

    # 外围传入的日志对象，服务过程中通过该函数写日志
    _logger = None

    # 外围传入的服务状态变更通知函数，函数实现的第1个参数为当前状态，第2个参数为错误信息result对象，含code和msg
    __server_status_info_fun = None

    __self_tag = ''  # 自定义标识，用于发起端传入自身的识别标识
    __server_run_status = EnumServerRunStatus.Stop  # 服务端服务运行情况
    __server_run_status_lock = None  # 服务端状态变更的同步锁

    __server_begin_time = None  # 执行启动函数的开始时间
    __server_stop_time = None  # 执行关闭函数的开始时间

    __last_start_result = None  # 登记最后一次启动状态

    #############################
    # 私有函数 - 子类可直接使用的函数
    #############################

    def _server_status_change(self, server_status, result):
        """
        通用的服务器状态修改函数
        进行服务器的状态变更，并调用server_status_info_fun通知调用者

        @param {EnumServerRunStatus} server_status - 要修改的服务器状态
        @param {CResult} result - 通用执行结果对象，其中自定义属性self_tag为发起方识别标识

        """
        self.__server_run_status = server_status
        if self.__server_status_info_fun is None:
            return
        else:
            result.self_tag = self.__self_tag
            self.__server_status_info_fun(server_status, result)

    def _load_i18n_dict(self):
        """
        装载多国语言字典

        """
        _i18n_obj = get_global_i18n()
        if _i18n_obj is None:
            # 创建对象并加入到全局中
            init_global_i18n()
            _i18n_obj = get_global_i18n()

        # 装载多国语言
        if self._trans_file_prefix != '':
            _i18n_obj.load_trans_from_dir(
                trans_file_path=self._trans_file_path,
                trans_file_prefix=self._trans_file_prefix,
                encoding=self._trans_file_encoding,
                append=True
            )

    #############################
    # 公共属性
    # __slots__ = ('_server_opts', '__self_tag','__server_run_status') #可以通过该函数限定实例不可以动态绑定其他属性，这里不做限制
    #############################

    @property
    def log_level(self):
        """
        获取正常日志输出级别

        @property {int}

        """
        return self._log_level

    @log_level.setter
    def log_level(self, value):
        """
        设置正常日志输出级别

        @property {int} value - 输出日志级别

        """
        self._log_level = value

    @property
    def self_tag(self):
        """
        获取调用方自定义标识
        @property {string}

        """
        return self.__self_tag

    @property
    def server_run_status(self):
        """
        获取服务端服务当前状态

        @property {EnumServerRunStatus}

        """
        return self.__server_run_status

    @property
    def server_run_status_desc(self):
        """
        获取服务端服务当前状态的描述

        @property {string}

        """
        if self.__server_run_status == EnumServerRunStatus.Stop:
            return _("stop")
        elif self.__server_run_status == EnumServerRunStatus.WaitStop:
            return _("waiting stop")
        elif self.__server_run_status == EnumServerRunStatus.WaitStart:
            return _("waiting start")
        elif self.__server_run_status == EnumServerRunStatus.ForceStop:
            return _("force stop")
        else:
            return _("running")

    #############################
    # 公共函数
    #############################

    def __init__(self, logger=None, server_status_info_fun=None, self_tag='',
                 log_level=logging.INFO, server_log_prefix='SER', server_name='Service',
                 is_auto_load_i18n=True, trans_file_path='', trans_file_prefix='', trans_file_encoding='utf-8'):
        """
        构造函数

        @param {Logger} logger=None - 日志对象，服务过程中通过该函数写日志:
            可以为标准的logging日志库对象，也可以为simple_log对象，但要求对象实现:
            标准的info、debug、warning、error、critical五个日志方法
        @param {function} server_status_info_fun=None - 外围传入的服务状态变更通知函数对象，当服务状态发生变更时通过:
            该函数通知调用方；形式为fun(server_status, result):
            其中server_status为服务器状态EnumServerRunStatus，
            result为CResult通用执行结果对象，自定义属性self_tag为发起方识别标识
        @param {string} self_tag='' - 自定义标识
        @param {int} log_level=logging.INFO - 处理中正常日志的输出登记级别，默认为INFO，如果不想输出过:
            多日志可以设置为DEBUG
        @param {string} server_log_prefix='SER' - 服务日志记录前缀，记录日志使用，例如[SER-STARTING]...
        @param {string} server_name='Service' - 服务名，记录日志使用
        @param {bool} is_auto_load_i18n=True - 是否自动加载i18n字典，如果继承类有自己的字典，可以重载__init__函数实现装载
        @param {string} trans_file_path='' - 要加载的i18n字典文件路径，如果填空代表程序运行的当前路径
        @param {string} trans_file_prefix='' - 要加载的i18n字典文件前缀
        @param {string} trans_file_encoding='utf-8' - 要加载的i18n字典文件的字符编码

        """
        self.__server_run_status_lock = threading.RLock()
        self._logger = logger
        self.__server_status_info_fun = server_status_info_fun
        self.__self_tag = self_tag
        self._log_level = log_level
        self._server_log_prefix = server_log_prefix
        self._server_name = server_name
        self._trans_file_path = trans_file_path
        self._trans_file_prefix = trans_file_prefix
        self._trans_file_encoding = trans_file_encoding
        if is_auto_load_i18n:
            self._load_i18n_dict()

    def start_server(self, is_wait=False):
        """
        启动服务
        注意服务必须处于停止状态才能启动

        @param {bool} is_wait=False - 是否等待服务启动完成后再退出

        @returns {CResult} - 启动结果，result.code：'00000'-成功，'21401'-服务不属于停止状态，不能启动，其他-异常

        """
        _result = CResult(code='00000')  # 成功
        with ExceptionTool.ignored_cresult(
            _result,
            logger=self._logger,
            self_log_msg='[%s-STARTING][NAME:%s]%s: ' % (
                self._server_log_prefix, self._server_name,
                _('start service error')),
            force_log_level=logging.ERROR
        ):
            # 先获取锁，拿到最准确的服务状态
            self.__server_run_status_lock.acquire()
            try:
                if self.__server_run_status != EnumServerRunStatus.Stop:
                    # 不属于停止状态，不能启动
                    _temp_result = CResult(code='21401')  # 服务启动失败-服务已启动
                    self._logger.log(
                        self._log_level,
                        '[%s-STARTING][NAME:%s]%s' % (self._server_log_prefix, self._server_name, _temp_result.msg))
                    return _temp_result

                # 执行启动服务的动作，通过线程方式启动，避免调用方等待
                self.__server_begin_time = datetime.datetime.now()
                self._logger.log(
                    self._log_level,
                    '[%s-STARTING][NAME:%s]%s' % (self._server_log_prefix, self._server_name, _('service starting')))
                self._server_status_change(EnumServerRunStatus.WaitStart, _result)
                _server_thread = threading.Thread(
                    target=self.__start_server_thread_fun,
                    args=(1,),
                    name='Thread-Server-Main'
                )
                _server_thread.setDaemon(True)
                _server_thread.start()
            finally:
                # 释放锁
                self.__server_run_status_lock.release()

        # 返回结果,循环等待
        while is_wait and self.__server_run_status == EnumServerRunStatus.WaitStart:
            RunTool.sleep(0.01)

        # 如果是等待模式，检查一次结果，如果没有正常运行返回最后一次启动结果
        if is_wait:
            if self.__server_run_status != EnumServerRunStatus.Running:
                _result = self.__last_start_result

        return _result

    def stop_server(self, is_wait=True, overtime=0):
        """
        关闭服务，设置服务为WaitStop-等待停止状态或ForceStop-强制停止状态

        @param {bool} is_wait=True - 是否等待服务器所有线程都处理完成后再关闭，True-等待所有线程完成处理，False-强制关闭
        @param {float} overtime=0 - 等待超时时间，单位为秒，0代表一直等待

        @returns {CResult} - 停止结果，result.code：'00000'-成功，'21402'-服务停止失败-服务已关闭，
            '31005'-执行超时，29999'-其他系统失败

        """
        _result = CResult(code='00000')  # 成功
        with ExceptionTool.ignored_cresult(
            _result,
            logger=self._logger,
            self_log_msg='[%s-STOPING][NAME:%s]%s: ' % (
                self._server_log_prefix, self._server_name, _('stop service error')),
            force_log_level=logging.ERROR
        ):
            self.__server_run_status_lock.acquire()
            try:
                _status = EnumServerRunStatus.WaitStop
                if not is_wait:
                    _status = EnumServerRunStatus.ForceStop

                self.__server_stop_time = datetime.datetime.now()
                if self.__server_run_status == EnumServerRunStatus.Running:
                    # 运行状态，处理设置等待关闭状态
                    self._logger.log(
                        self._log_level,
                        '[%s-STOPING][NAME:%s]%s' % (self._server_log_prefix, self._server_name, _('service stoping')))
                    self._server_status_change(_status, _result)
                elif self.__server_run_status == EnumServerRunStatus.WaitStop \
                        and _status == EnumServerRunStatus.ForceStop:
                    self._logger.log(
                        self._log_level,
                        '[%s-STOPING][NAME:%s]%s' % (self._server_log_prefix, self._server_name, _('service force stoping')))
                    self._server_status_change(_status, _result)
                else:
                    # 不属于运行状态，不能处理
                    _temp_result = CResult(code='21402')  # 服务停止失败-服务已关闭
                    self._logger.log(
                        self._log_level,
                        '[%s-STOPING][NAME:%s]%s' % (self._server_log_prefix, self._server_name, _temp_result.msg))
                    return _temp_result
            finally:
                self.__server_run_status_lock.release()

        # 等待服务关闭
        _begin_time = datetime.datetime.now()  # 记录等待开始时间
        while is_wait:
            if self.__server_run_status == EnumServerRunStatus.Stop:
                break
            if overtime > 0 and (datetime.datetime.now() - _begin_time).total_seconds() > overtime:
                _result = CResult(code='31005')  # 执行超时
                break
            RunTool.sleep(0.1)

        # 返回结果
        return _result

    #############################
    # 私有函数 -  框架内部处理函数
    #############################

    def __start_server_thread_fun(self, tid):
        """
        启动服务处理主线程，本线程结束就代表服务停止

        @param {int} tid - 线程id

        """
        _result = CResult(code='00000')  # 成功
        with ExceptionTool.ignored_cresult(
            result_obj=_result,
            logger=self._logger,
            self_log_msg='[%s-STARTING][NAME:%s]%s: ' % (
                self._server_log_prefix, self._server_name,
                _('start service error'))
        ):
            # 统一的异常处理
            self._logger.log(
                self._log_level,
                '[%s-STARTING][NAME:%s]%s' % (self._server_log_prefix, self._server_name, _('service starting')))

            # 执行服务启动处理，执行通过则代表启动成功tid
            start_result = self._start_server_self(tid)
            self.__last_start_result = start_result

            if start_result.code != '00000':
                # 启动失败，登记了日志，修改状态为未启动，退出
                self._logger.log(
                    logging.ERROR,
                    ('[%s-STARTING][NAME:%s][USE:%ss]%s: %s - %s' % (
                        self._server_log_prefix,
                        self._server_name, str(
                            (datetime.datetime.now() - self.__server_begin_time).total_seconds()),
                        _('start service error'), start_result.code, start_result.msg))
                )

                self._server_status_change(EnumServerRunStatus.Stop, start_result)
                return

            # 启动成功，更新状态
            self._logger.log(
                self._log_level,
                '[%s-STARTED][NAME:%s][USE:%ss]%s' % (
                    self._server_log_prefix,
                    self._server_name,
                    str((datetime.datetime.now() - self.__server_begin_time).total_seconds()),
                    _('start service sucess')
                ))
            self._server_status_change(EnumServerRunStatus.Running, _result)

            # 开始进入循环处理
            while True:
                if self.__server_run_status == EnumServerRunStatus.WaitStop:
                    # 收到指令等待停止
                    while True:
                        if self.__server_run_status == EnumServerRunStatus.ForceStop:
                            # 过程中又被要求强制退出
                            break

                        # 执行预停止处理函数，例如关闭已打开的子线程
                        stop_predeal_result = self._stop_server_predeal_self(
                            tid, start_result.server_info)
                        if stop_predeal_result.code == '00000' and not stop_predeal_result.is_finished:
                            # 预处理未完成，需要循环处理
                            RunTool.sleep(0.1)
                            continue
                        else:
                            # 预处理已完成，退出
                            break
                    break
                elif self.__server_run_status == EnumServerRunStatus.ForceStop:
                    # 收到指令马上停止
                    break
                else:
                    # 正常执行一次服务处理函数
                    run_result = self._server_run_self(tid, start_result.server_info)

                    # 继续下一个循环处理
                    if not run_result.is_finished:
                        continue

        # 线程结束就代表服务已关闭，执行结束处理函数
        self._stop_server_end_self(tid)
        self._server_status_change(EnumServerRunStatus.Stop, _result)
        self._logger.log(
            self._log_level,
            '[%s-STOPED][NAME:%s][USE:%ss]%s' % (
                self._server_log_prefix,
                self._server_name,
                str((datetime.datetime.now() - self.__server_stop_time).total_seconds()),
                _('service stoped')
            ))

    #############################
    # 外部系统应实现的接口对象（内部处理函数）
    #############################

    def _start_server_self(self, tid):
        """
        自定义服务启动函数，实现类可重载该函数加入自己的处理逻辑

        @param {int} tid - 线程id

        @returns {CResult} - 启动结果:
            result.code ：'00000'-成功，其他值为失败
            result.server_info ：启动成功后的服务对象，用于传递到后续的服务处理函数

        """
        _result = CResult(code='00000')  # 成功
        _result.server_info = NullObj()
        with ExceptionTool.ignored_cresult(_result):
            # 可在该部分实现自定义逻辑
            pass
        # 返回处理结果
        return _result

    def _stop_server_predeal_self(self, tid, server_info):
        """
        自定义服务停止前处理函数，实现类可重载该函数加入自己的处理逻辑（例如结束子线程）

        @param {int} tid - 线程id
        @param {object} server_info - _start_server_self函数生成的server_info信息

        @returns {CResult} - 处理结果:
            result.code ：'00000'-成功，其他值为失败
            result.is_finished ：处理是否已完成，True - 已处理完成，False - 未完成，需循环再处理

        """
        _result = CResult(code='00000')  # 成功
        _result.is_finished = True
        with ExceptionTool.ignored_cresult(
            _result,
            logger=self._logger,
            self_log_msg='[%s-STOPING][NAME:%s]%s: ' % (
                self._server_log_prefix, self._server_name, _('stop service predeal error')),
            force_log_level=logging.ERROR
        ):
            # 可在该部分实现自定义逻辑
            pass
        # 返回处理结果
        return _result

    def _stop_server_end_self(self, tid):
        """
        自定义服务停止后处理函数，实现类可重载该函数加入自己的处理逻辑
            注意：函数应屏蔽异常

        @param {int} tid - 线程id

        """
        _result = CResult(code='00000')  # 成功
        with ExceptionTool.ignored_cresult(
            _result,
            logger=self._logger,
            self_log_msg='[%s-STOPING][NAME:%s]%s: ' % (
                self._server_log_prefix, self._server_name, _('stop service end fun error')),
            force_log_level=logging.ERROR
        ):
            # 可在该部分实现自定义逻辑
            pass
        # 返回处理结果
        return

    def _server_run_self(self, tid, server_info):
        """
        自定义服务处理函数，实现类可重载该函数加入自己的处理逻辑（例如进行实际业务处理）
            注意：该函数每次只处理一次就应该返回，且应该实现异常处理

        @param {int} tid - 线程id
        @param {object} server_info - _start_server_self函数生成的server_info信息

        @returns {CResult} - 处理结果:
            result.code ：'00000'-成功，其他值为失败
            result.is_finished ：处理是否已完成，True - 已处理完成，False - 未完成，需循环再处理

        """
        _result = CResult(code='00000')  # 成功
        _result.is_finished = False
        with ExceptionTool.ignored_cresult(
            _result,
            logger=self._logger,
            self_log_msg='[%s][NAME:%s]%s: ' % (
                self._server_log_prefix, self._server_name, _('service run error')),
            force_log_level=logging.ERROR
        ):
            # 可在该部分实现自定义逻辑
            pass
        # 返回处理结果
        return _result


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    # 打印版本信息
    print(('模块名：%s  -  %s\n'
           '作者：%s\n'
           '发布日期：%s\n'
           '版本：%s' % (__MOUDLE__, __DESCRIPT__, __AUTHOR__, __PUBLISH__, __VERSION__)))

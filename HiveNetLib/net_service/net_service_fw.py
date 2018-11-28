#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
#
# Copyright 2018 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
网络服务框架

@module net_service_fw
@file net_service_fw.py

"""

import os
import sys
import copy
import time
import datetime
import threading
from enum import Enum
from abc import ABC, abstractmethod  # 利用abc模块实现抽象类
sys.path.append(os.path.abspath(os.path.dirname(__file__)+'/'+'../..'))
from HiveNetLib.simple_log import EnumLogLevel
from HiveNetLib.generic import CResult
from HiveNetLib.simple_i18n import _, SimpleI18N, get_global_i18n, init_global_i18n
from HiveNetLib.base_tools.exception_tool import ExceptionTool
from HiveNetLib.base_tools.string_tool import StringTool
from HiveNetLib.base_tools.debug_tool import DebugTool


__MOUDLE__ = 'base_service_fw'  # 模块名
__DESCRIPT__ = u'网络服务框架'  # 模块描述
__VERSION__ = '0.1.0'  # 版本
__AUTHOR__ = u'黎慧剑'  # 作者
__PUBLISH__ = '2018.09.04'  # 发布日期


class EnumNetServerRunStatus(Enum):
    """
    服务器运行状态

    @enum {string}

    """
    Stop = 'S'  # 停止
    Running = 'R'  # 正在运行
    WaitStop = 'WS'  # 等待停止
    WaitStart = 'WR'  # 等待启动
    ForceStop = 'FS'  # 强制停止


class NetServiceFW(ABC):
    """
    网络服务框架类
    抽象网络编程的公共方法形成框架，并提供基本的处理功能，简化网络协议编程的难度

    @param {Logger} logger=None - 日志对象，服务过程中通过该函数写日志:
        可以为标准的logging日志库对象，也可以为simple_log对象，但要求对象实现:
        标准的info、debug、warning、error、critical五个日志方法
    @param {function} server_status_info_fun=None - 外围传入的网络服务状态变更通知函数对象，当网络服务状态发生变更时通过:
        该函数通知调用方；形式为fun(server_status, result):
        其中server_status为服务器状态EnumNetServerRunStatus，
        result为CResult通用执行结果对象，自定义属性self_tag为发起方识别标识
    @param {function} server_connect_deal_fun=None - 外围传入的网络服务与客户端连接后对连接的处理线程函数对象，在该函数中:
        实现服务器端具体的通讯处理（如循环收报文、返回报文等）；
        形式为fun(thread_id, server_opts, net_info, self_tag):
            thread_id - 线程ID
            server_opts -服务的启动参数
            net_info - 具体实现的连接信息（例如Socket对象）
            self_tag - 用于发起端传入自身的识别标识
        需注意实现上应在每次循环时查询服务器关闭状态，如果判断到服务器已关闭，应结束处理.
    @param {string} self_tag='' - 自定义标识
    @param {EnumLogLevel} log_level=EnumLogLevel.INFO - 处理中正常日志的输出登记级别，默认为INFO，如果不想输出过多日志可以设置为DEBUG
    @param {string} server_name='NetService' - 服务名，记录日志使用
    @param {bool} is_auto_load_i18n=True - 是否自动加载i18n字典，如果继承类有自己的字典，可以重载__init__函数实现装载

    @example
        1、服务器端的使用方法，假设实现类为XService
        def server_status_info_fun(server_status, result):
            ...根据通知的服务器状态变更执行自定义处理
            return

        def server_connect_deal_fun(thread_id, server_opts, net_info, self_tag)
            ...循环通过recv_data和send_data进行连接收发处理
            return

        # 初始化服务对象
        _logger = logging.Logger()
        server = Xservice(logger=_logger, server_status_info_fun=server_status_info_fun,
            server_connect_deal_fun=server_connect_deal_fun, self_tag="TestTag")

        # 启动网络服务
        server_opts = ...
        server.start_server(server_opts=server_opts)

        # 关闭服务
        server.stop_server(is_wait=True)

        2、客户端的使用方法，假设实现类为XService
        connect_para=...
        connect_result = XService.connect_server(connect_para=connect_para)
        if connect_result.code == 0:
            # 连接成功
            send_para = ...
            data = ...
            send_result = XService.send.data(connect_result.net_info, send_para, data)
            if send_result.code == 0:
                # 获取返回结果
                recv_para = ...
                read_result = XService.recv_data(connect_result.net_info, recv_para)
                print(read_result.data)

    """

    #############################
    # 私有变量 - 子类可访问的变量
    #############################

    _server_opts = None  # 外围传入的网络服务启动参数，应为一个object对象，通过_serverOpts.xxx 获取对应的属性xxx值
    _logLevel = EnumLogLevel.INFO  # 外围传入的日志级别，根据该级别打印日志，例如传DEBUG可减少日志的输出
    _server_name = 'NetService'  # 服务名，记录日志使用

    #############################
    # 私有变量 - 只用于框架内部处理的变量
    #############################

    # 外围传入的日志对象，服务过程中通过该函数写日志
    _logger = None
    _logger_fun = dict()  # 记载debug、warning等方法的数组，简化日志输出代码

    # 外围传入的网络服务状态变更通知函数，函数实现的第1个参数为当前状态，第2个参数为错误信息result对象，含code和msg
    __server_status_info_fun = None

    # 外围传入的网络服务与客户端连接后对连接的处理线程函数:
    # 函数实现的第1个参数为线程ID，第2个参数为服务启动参数，第3个为连接信息
    # 需注意实现上应在每次循环时查询服务器关闭状态，如果遇到则结束处理
    __server_connect_deal_fun = None

    __self_tag = ''  # 自定义标识，用于发起端传入自身的识别标识
    __server_run_status = EnumNetServerRunStatus.Stop  # 服务端服务运行情况
    __server_run_status_lock = threading.RLock()  # 服务端状态变更的同步锁
    __server_connect_thread_id = 1  # 服务端的链接线程ID序列
    __server_connect_thread_list = {}  # 服务端正在运行的连接线程列表
    __server_connect_thread_list_lock = threading.RLock()  # 连接线程列表变更的同步锁

    __server_begin_time = None  # 执行启动函数的开始时间
    __server_stop_time = None  # 执行关闭函数的开始时间

    #############################
    # 私有函数 - 子类可直接使用的函数
    #############################

    def _server_status_change(self, server_status, result):
        """
        通用的服务器状态修改函数
        进行服务器的状态变更，并调用server_status_info_fun通知调用者

        @param {EnumNetServerRunStatus} server_status - 要修改的服务器状态
        @param {CResult} result - 通用执行结果对象，其中自定义属性self_tag为发起方识别标识

        """
        self.__server_run_status = server_status
        if self.__server_status_info_fun is None:
            return
        else:
            result.self_tag = self.__self_tag
            self.__server_status_info_fun(server_status, result)

    def _get_server_opts(self, para_name, default_value=''):
        """
        获取服务启动参数

        @param {string} para_name - 参数名
        @param {string} default_value='' - 默认值

        @returns {object} - 参数值

        """
        try:
            _obj = eval('self._server_opts.' + para_name)
            return _obj
        except Exception:
            return default_value

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
        _i18n_obj.load_trans_from_dir(
            trans_file_path=os.path.abspath(os.path.dirname(__file__)),
            trans_file_prefix='netservicefw',
            encoding='utf-8',
            append=True
        )

    #############################
    # 私有函数 -  框架内部处理函数
    #############################

    def __server_connect_thread_end(self, thread_id):
        """
        服务端连接线程结束清除线程池记录
        在服务端连接线程处理结束时调用，将线程ID从线程池记录中删除

        @param {int} thread_id - 线程ID

        """
        self.__server_connect_thread_list_lock.acquire()
        with ExceptionTool.ignored_all(logger=self._logger, self_log_msg='__server_connect_thread_end exception:'):
            del self.__server_connect_thread_list[thread_id]
        self.__server_connect_thread_list_lock.release()

    def __server_connect_thread_clear(self):
        """
        删除服务端连接线程池记录

        """
        self.__server_connect_thread_list_lock.acquire()
        with ExceptionTool.ignored_all(logger=self._logger, self_log_msg='__server_connect_thread_clear exception:'):
            self.__server_connect_thread_list.clear()
        self.__server_connect_thread_list_lock.release()

    def __server_connect_thread_add(self, thread_id, thread_obj):
        """
        服务端连接线程池增加线程记录
        服务端启动一个新连接线程时，通过该函数新增线程池记录

        @param {int} thread_id - 线程ID
        @param {object} thread_obj -线程对象

        """
        self.__server_connect_thread_list_lock.acquire()
        with ExceptionTool.ignored_all(logger=self._logger, self_log_msg='__server_connect_thread_add exception:'):
            self.__server_connect_thread_list[thread_id] = thread_obj
        self.__server_connect_thread_list_lock.release()

    def __start_server_thread_fun(self, tid, server_opts):
        """
        启动网络服务的监听线程，步骤如下:
            1、启动监听服务_start_server_without_accept
            2、循环获取连接_accept_one
            3、每一个连接启动一个处理线程__server_connect_thread_fun
            4、本线程结束就代表网络服务停止

        @param {int} tid - 线程id
        @param {object} server_opts - 服务启动参数

        """
        DebugTool.debug_print(u'服务监听线程进入')
        _result = CResult(code='00000')  # 成功
        with ExceptionTool.ignored_cresult(
            result_obj=_result,
            logger=self._logger,
            self_log_msg='[LIS-STARTING][NAME:%s]%s: ' % (self._server_name,
                                                          _('start net service error'))
        ):
            # 统一的异常处理
            self._logger_fun[self._log_level](
                '[LIS-STARTING][NAME:%s]%s' % (self._server_name, _('net service starting')))
            self._logger_fun[self._log_level]('[LIS-STARTING][NAME:%s]%s:\n%s' % (
                self._server_name,
                _('net start parameter'), StringTool.format_obj_property_str(server_opts, is_deal_subobj=True))
            )

            # 启动服务，但不接受连接
            _result = self._start_server_without_accept(server_opts)
            _server_info = _result.net_info
            if not _result.is_success():
                # 启动失败
                self._logger_fun[EnumLogLevel.ERROR]('[LIS-STARTING][NAME:%s][USE:%ss]%s: %s - %s' % (
                    self._server_name, str(
                        (datetime.datetime.now() - self.__server_begin_time).total_seconds()),
                    _('start net service error'), _result.code, _result.msg))
                return
            # 启动成功，更新状态
            self._logger_fun[self._log_level](
                '[LIS-STARTED][NAME:%s][USE:%ss][IP:%s][PORT:%s]%s' % (
                    self._server_name,
                    str((datetime.datetime.now() - self.__server_begin_time).total_seconds()),
                    str(self._get_server_opts('ip', '')),
                    str(self._get_server_opts('port', '')),
                    _('start net service sucess')
                ))
            self._server_status_change(EnumNetServerRunStatus.Running, _result)

            # 开始进入监听进程
            DebugTool.debug_print(u'服务监听线程循环处理')
            while True:
                if self.__server_run_status == EnumNetServerRunStatus.WaitStop:
                    # 收到指令等待停止
                    DebugTool.debug_print(u'服务监听线程收到指令等待停止')
                    while True:
                        if self.__server_run_status == EnumNetServerRunStatus.ForceStop:
                            # 过程中又被要求强制退出
                            break
                        if len(self.__server_connect_thread_list.keys()) > 0:
                            time.sleep(0.1)
                            continue
                        else:
                            # 线程已全部停止
                            break
                    break
                elif self.__server_run_status == EnumNetServerRunStatus.ForceStop:
                    # 收到指令马上停止
                    DebugTool.debug_print(u'服务监听线程收到指令马上停止')
                    break
                else:
                    # 正常监听下一个请求
                    DebugTool.debug_print(u'服务监听线程正常监听下一请求')
                    _accept_result = self._accept_one(server_opts, _server_info)
                    if _accept_result.is_success():
                        # 获取到一个连接，创建线程
                        self.__server_connect_thread_id = self.__server_connect_thread_id + 1
                        _thread_id = self.__server_connect_thread_id
                        _new_thread = threading.Thread(
                            target=self.__server_connect_thread_fun,
                            args=(_thread_id, server_opts, _accept_result.net_info),
                            name='Thread-ConnectDeal' + str(_thread_id)
                        )
                        self.__server_connect_thread_add(_thread_id, _new_thread)
                        _new_thread.setDaemon(True)
                        _new_thread.start()
                    elif _accept_result.code != '20407':
                        # 不是超时的其他获取错误，打印信息
                        self._logger_fun[EnumLogLevel.ERROR](
                            "[LIS][NAME:%s][EX:%s]%s: %s\n%s" % (
                                self._server_name, str(type(_accept_result.error)),
                                _('accept net connection error'), _accept_result.msg,
                                _accept_result.trace_str
                            )
                        )
                    else:
                        DebugTool.debug_print(u'服务监听线程获取客户端连接超时')

                    # 继续下一个请求
                    continue

        # 线程结束就代表服务已关闭
        self.__server_connect_thread_clear()
        self._server_status_change(EnumNetServerRunStatus.Stop, _result)
        self._logger_fun[self._log_level](
            '[LIS-STOPED][NAME:%s][USE:%ss][IP:%s][PORT:%s]%s' % (
                self._server_name,
                str((datetime.datetime.now() - self.__server_stop_time).total_seconds()),
                str(self._get_server_opts('ip', '')),
                str(self._get_server_opts('port', '')),
                _('net service stoped')
            ))
        DebugTool.debug_print(u'服务监听线程结束')

    def __server_connect_thread_fun(self, thread_id, server_opts, net_info):
        """
        调用外围传入的网络连接处理线程的封装函数
        该函数的主要目的是屏蔽调用程序的网络连接处理函数的异常

        @param {int} thread_id - 线程ID
        @param {object} server_opts - 网络服务的启动参数
        @param {object} net_info - 网络的接入参数（例如socket对象）

        """
        with ExceptionTool.ignored_all(
            logger=self._logger,
            self_log_msg='[LIS][NAME:%s]%s: ' % (self._server_name, _(
                'net service connect deal threading error')),
            force_log_level=EnumLogLevel.ERROR
        ):
            self.__server_connect_deal_fun(thread_id, server_opts, net_info, self.__self_tag)
        # 结束处理
        self.__server_connect_thread_end(thread_id)

    #############################
    # 公共属性
    # __slots__ = ('_server_opts', '__self_tag','__server_run_status') #可以通过该函数限定实例不可以动态绑定其他属性，这里不做限制
    #############################

    @property
    def log_level(self):
        """
        获取正常日志输出级别

        @property {EnumLogLevel}

        """
        return self._log_level

    @log_level.setter
    def log_level(self, value):
        """
        设置正常日志输出级别

        @property {EnumLogLevel} value - 输出日志级别

        """
        self._log_level = value

    @property
    def server_opts(self):
        """
        获取服务器启动参数

        @property {object}

        @example
            opts = serverobj.server_opts

        """
        return copy.deepcopy(self._server_opts)

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

        @property {EnumNetServerRunStatus}

        """
        return self.__server_run_status

    @property
    def server_run_status_desc(self):
        """
        获取服务端服务当前状态的描述

        @property {string}

        """
        if self.__server_run_status == EnumNetServerRunStatus.Stop:
            return _("stop")
        elif self.__server_run_status == EnumNetServerRunStatus.WaitStop:
            return _("waiting stop")
        elif self.__server_run_status == EnumNetServerRunStatus.WaitStart:
            return _("waiting start")
        elif self.__server_run_status == EnumNetServerRunStatus.ForceStop:
            return _("force stop")
        else:
            return _("running")

    #############################
    # 公共函数
    #############################

    def __init__(self, logger=None, server_status_info_fun=None, server_connect_deal_fun=None, self_tag='',
                 log_level=EnumLogLevel.INFO, server_name='NetService', is_auto_load_i18n=True):
        """
        构造函数

        @param {Logger} logger=None - 日志对象，服务过程中通过该函数写日志:
            可以为标准的logging日志库对象，也可以为simple_log对象，但要求对象实现:
            标准的info、debug、warning、error、critical五个日志方法
        @param {function} server_status_info_fun=None - 外围传入的网络服务状态变更通知函数对象，当网络服务状态发生变更时通过:
            该函数通知调用方；形式为fun(server_status, result):
            其中server_status为服务器状态EnumNetServerRunStatus，
            result为CResult通用执行结果对象，自定义属性self_tag为发起方识别标识
        @param {function} server_connect_deal_fun=None - 外围传入的网络服务与客户端连接后对连接的处理线程函数对象，在该函数中:
            实现服务器端具体的通讯处理（如循环收报文、返回报文等）；
            形式为fun(thread_id, server_opts, net_info, self_tag):
                thread_id - 线程ID
                server_opts -服务的启动参数
                net_info - 具体实现的连接信息（例如Socket对象）
                self_tag - 用于发起端传入自身的识别标识
            需注意实现上应在每次循环时查询服务器关闭状态，如果判断到服务器已关闭，应结束处理.
        @param {string} self_tag='' - 自定义标识
        @param {EnumLogLevel} log_level=EnumLogLevel.INFO - 处理中正常日志的输出登记级别，默认为INFO，如果不想输出过多日志可以设置为DEBUG
        @param {string} server_name='NetService' - 服务名，记录日志使用
        @param {bool} is_auto_load_i18n=True - 是否自动加载i18n字典，如果继承类有自己的字典，可以重载__init__函数实现装载

        """
        self._logger = logger
        if self._logger is not None:
            # 直接通过字典调用写日志方法
            self._logger_fun[EnumLogLevel.DEBUG] = self._logger.debug
            self._logger_fun[EnumLogLevel.WARNING] = self._logger.warning
            self._logger_fun[EnumLogLevel.ERROR] = self._logger.error
            self._logger_fun[EnumLogLevel.CRITICAL] = self._logger.critical
            self._logger_fun[EnumLogLevel.INFO] = self._logger.info
        self.__server_status_info_fun = server_status_info_fun
        self.__server_connect_deal_fun = server_connect_deal_fun
        self.__self_tag = self_tag
        self._log_level = log_level
        self._server_name = server_name
        if is_auto_load_i18n:
            self._load_i18n_dict()

    def start_server(self, server_opts, is_wait=False):
        """
        启动网络服务
        根据传入的服务器参数，启动网络服务监听线程，注意服务必须处于停止状态才能启动

        @param {object} server_opts - 启动服务器参数，由框架的实际实现类进行定义:
            子类通过_serverOpts.xxx获取具体的属性值
        @param {bool} is_wait=False - 是否等待服务启动完成后再退出

        @returns {CResult} - 启动结果，result.code：'00000'-成功，'21401'-服务不属于停止状态，不能启动，其他-异常

        """
        _result = CResult(code='00000')  # 成功
        with ExceptionTool.ignored_cresult(
            _result,
            logger=self._logger,
            self_log_msg='[LIS-STARTING][NAME:%s]%s: ' % (self._server_name,
                                                          _('start net service error')),
            force_log_level=EnumLogLevel.ERROR
        ):
            self._server_opts = server_opts
            # 先获取锁，拿到最准确的服务状态
            self.__server_run_status_lock.acquire()
            try:
                if self.__server_run_status != EnumNetServerRunStatus.Stop:
                    # 不属于停止状态，不能启动
                    _result = CResult(code='21401')  # 服务启动失败-服务已启动
                    self._logger_fun[self._log_level](
                        '[LIS-STARTING][NAME:%s]%s' % (self._server_name, _result.msg))
                    return _result

                # 执行启动服务的动作，通过线程方式启动，避免调用方等待
                self.__server_begin_time = datetime.datetime.now()
                self._logger_fun[self._log_level](
                    '[LIS-STARTING][NAME:%s]%s' % (self._server_name, _('net service starting')))
                self._server_status_change(EnumNetServerRunStatus.WaitStart, _result)
                _listen_thread = threading.Thread(
                    target=self.__start_server_thread_fun,
                    args=(1, server_opts),
                    name='Thread-ServerListen'
                )
                _listen_thread.setDaemon(True)
                _listen_thread.start()
            finally:
                # 释放锁
                self.__server_run_status_lock.release()
        # 返回结果,循环等待
        while is_wait and self.__server_run_status == EnumNetServerRunStatus.WaitStart:
            time.sleep(0.01)

        return _result

    def stop_server(self, is_wait=True):
        """
        关闭网络服务，设置网络服务为WaitStop-等待停止状态或ForceStop-强制停止状态，:
            由监听和处理线程内部执行关闭处理

        @param {bool} is_wait=True - 是否等待服务器所有线程都处理完成后再关闭，True-等待所有线程完成处理，False-强制关闭

        @returns {CResult} - 停止结果，result.code：'00000'-成功，'21402'-服务停止失败-服务已关闭，'29999'-其他系统失败

        """
        _result = CResult(code='00000')  # 成功
        with ExceptionTool.ignored_cresult(
            _result,
            logger=self._logger,
            self_log_msg='[LIS-STOPING][NAME:%s]%s: ' % (
                self._server_name, _('stop net service error')),
            force_log_level=EnumLogLevel.ERROR
        ):
            self.__server_run_status_lock.acquire()
            try:
                _status = EnumNetServerRunStatus.WaitStop
                if not is_wait:
                    _status = EnumNetServerRunStatus.ForceStop

                self.__server_stop_time = datetime.datetime.now()
                if self.__server_run_status == EnumNetServerRunStatus.Running:
                    # 运行状态，处理设置等待关闭状态
                    self._logger_fun[self._log_level](
                        '[LIS-STOPING][NAME:%s]%s' % (self._server_name, _('net service stoping')))
                    self._server_status_change(_status, _result)
                elif self.__server_run_status == EnumNetServerRunStatus.WaitStop \
                        and _status == EnumNetServerRunStatus.ForceStop:
                    self._logger_fun[self._log_level](
                        '[LIS-STOPING][NAME:%s]%s' % (self._server_name, _('net service force stoping')))
                    self._server_status_change(_status, _result)
                else:
                    # 不属于运行状态，不能处理
                    _result = CResult(code='21402')  # 服务停止失败-服务已关闭
                    self._logger_fun[self._log_level](
                        '[LIS-STOPING][NAME:%s]%s' % (self._server_name, _result.msg))
                    return _result
            finally:
                self.__server_run_status_lock.release()
        # 等待服务关闭
        while True:
            if self.__server_run_status == EnumNetServerRunStatus.Stop:
                break
            time.sleep(0.1)
        # 返回结果
        return _result

    #############################
    # 外部系统必须实现的接口对象（内部处理函数）
    #############################

    @abstractmethod  # 定义抽象方法，无需实现功能
    def _start_server_without_accept(self, server_opts):
        """
        启动服务但不接受请求服务，该方法只做到启动端口层面，轮询监听不在该方法中实现:
            注意该该函数必须捕获并处理异常

        @param {object} server_opts - 参数说明

        @returns {CResult} - 启动结果:
            result.code ：'00000'-成功，其他值为失败
            result.net_info ：启动后的服务端网络连接信息对象，该对象将传给后续的监听线程（_AcceptOne）

        """
        # 子类必须定义该功能
        pass

    @abstractmethod  # 定义抽象方法，无需实现功能
    def _accept_one(self, server_opts, net_info):
        """
        监听接受一个请求并返回
        提供监听并获取到请求连接返回的方法；注意该该函数必须捕获并处理异常

        @param {objcet} server_opts - 网络服务启动参数
        @param {objcet} net_info - 网络连接信息对象，_start_server_without_accept中获取到的结果

        @returns {CResult} - 获取网络连接结果:
            result.code ：'00000'-成功，'20407'-获取客户端连接请求超时
            result.net_info ：客户端连接信息对象，该对象将传给后续单个连接处理的线程

        """
        # 子类必须定义该功能
        pass

    # 外部系统必须实现的接口对象（公共函数）

    @classmethod
    @abstractmethod  # 定义抽象方法，无需实现功能
    def recv_data(cls, net_info, recv_para={}):
        """
        从指定的网络连接中读取数据

        @param {object} net_info - 要读取数据的网络信息对象（例如socket对象）
        @param {dict} recv_para={} - 读取数据的参数（例如长度、超时时间等，由实现类自定义）

        @returns {CResult} - 数据获取结果:
            result.code ：'00000'-成功，'20403'-获取数据超时，其他为获取失败
            result.data ：获取到的数据对象（具体类型和定义，由实现类自定义）
            result.recv_time : datetime 实际开始接受数据时间

        """
        # 子类必须定义该功能
        pass

    @classmethod
    @abstractmethod  # 定义抽象方法，无需实现功能
    def send_data(cls, net_info, data, send_para={}):
        """
        向指定的网络连接发送数据

        @param {object} net_info - 要写入数据的网络信息对象（例如socket对象）
        @param {object} data - 要写入的数据对象（具体类型和定义，由实现类自定义）
        @param {dict} send_para={} - 写入数据的参数（例如长度、超时时间等，由实现类自定义）

        @returns {CResult} - 发送结果:
            result.code ：'00000'-成功，'20404'-写入数据超时，其他为写入失败
            result.send_time : datetime 实际发送完成时间

        """
        # 子类必须定义该功能
        pass

    @classmethod
    @abstractmethod  # 定义抽象方法，无需实现功能
    def close_connect(cls, net_info):
        """
        关闭指定的网络连接，注意该该函数必须捕获并处理异常

        @param {object} net_info - 需要关闭的网络连接信息对象

        @returns {CResult} - 关闭结果
            result.code ：'00000'-成功，其他值为失败

        """
        # 子类必须定义该功能
        pass

    @classmethod
    @abstractmethod  # 定义抽象方法，无需实现功能
    def connect_server(cls, connect_para):
        """
        客户端通过该函数连接服务器端

        @param {object} connect_para - 需要连接服务器的参数（例如IP、端口、超时时间等，由实现类自定义）

        @returns {CResult} - 连接结果:
            result.code ：'00000'-成功，其他值为失败
            result.net_info ： 连接后的网络信息对象

        """
        # 子类必须定义该功能
        pass

    @abstractmethod
    def get_server_info(self, para_name, default_value=None):
        """
        获取服务器信息

        @param {string} para_name - 参数名

        @returns {object} - 返回具体的参数值对象（实现类自定义）

        """
        pass

    @classmethod
    @abstractmethod
    def get_client_info(cls, net_info, para_name, default_value=None):
        """
        获取指定客户端连接的信息，根据传入的参数获取参数值（具体可以获取什么参数由实现类自定义）

        @param {object} net_info - 客户端网络连接信息对象
        @param {string} para_name - 参数名

        @returns {object} - 返回具体的参数值对象（实现类自定义）

        """
        pass


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    # 打印版本信息
    print(('模块名：%s  -  %s\n'
           '作者：%s\n'
           '发布日期：%s\n'
           '版本：%s' % (__MOUDLE__, __DESCRIPT__, __AUTHOR__, __PUBLISH__, __VERSION__)))

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
import threading
import logging
from abc import abstractmethod  # 利用abc模块实现抽象类
# 根据当前文件路径将包路径纳入，在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir, os.path.pardir)))
from HiveNetLib.generic import CResult, NullObj
from HiveNetLib.simple_server_fw import EnumServerRunStatus, SimpleServerFW
from HiveNetLib.simple_i18n import _, SimpleI18N, get_global_i18n, init_global_i18n
from HiveNetLib.base_tools.exception_tool import ExceptionTool
from HiveNetLib.base_tools.string_tool import StringTool
from HiveNetLib.base_tools.debug_tool import DebugTool


__MOUDLE__ = 'base_service_fw'  # 模块名
__DESCRIPT__ = u'网络服务框架'  # 模块描述
__VERSION__ = '0.1.0'  # 版本
__AUTHOR__ = u'黎慧剑'  # 作者
__PUBLISH__ = '2018.09.04'  # 发布日期


class NetServiceFW(SimpleServerFW):
    """
    网络服务框架类
    抽象网络编程的公共方法形成框架，并提供基本的处理功能，简化网络协议编程的难度

    @param {Logger} logger=None - 日志对象，服务过程中通过该函数写日志:
        可以为标准的logging日志库对象，也可以为simple_log对象，但要求对象实现:
        标准的info、debug、warning、error、critical五个日志方法
    @param {function} server_status_info_fun=None - 外围传入的网络服务状态变更通知函数对象，当网络服务状态发生变更时通过:
        该函数通知调用方；形式为fun(server_status, result):
        其中server_status为服务器状态EnumServerRunStatus，
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
    @param {int} log_level=logging.INFO - 处理中正常日志的输出登记级别，默认为INFO，如果不想输出过多日志可以设置为DEBUG
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

    #############################
    # 私有函数 - 子类可直接使用的函数
    #############################

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
            self_log_msg='[%s][NAME:%s]%s: ' % (self._server_log_prefix, self._server_name, _(
                'net service connect deal threading error')),
            force_log_level=logging.ERROR
        ):
            self.__server_connect_deal_fun(thread_id, server_opts, net_info, self.self_tag)
        # 结束处理
        self.__server_connect_thread_end(thread_id)

    #############################
    # 公共属性
    # __slots__ = ('_server_opts', '__self_tag','__server_run_status') #可以通过该函数限定实例不可以动态绑定其他属性，这里不做限制
    #############################

    @property
    def server_opts(self):
        """
        获取服务器启动参数

        @property {object}

        @example
            opts = serverobj.server_opts

        """
        return copy.deepcopy(self._server_opts)

    #############################
    # 公共函数
    #############################

    def __init__(self, logger=None, server_status_info_fun=None, server_connect_deal_fun=None, self_tag='',
                 log_level=logging.INFO, server_name='NetService',
                 is_auto_load_i18n=True, trans_file_path='', trans_file_prefix='', trans_file_encoding='utf-8'):
        """
        构造函数

        @param {Logger} logger=None - 日志对象，服务过程中通过该函数写日志:
            可以为标准的logging日志库对象，也可以为simple_log对象，但要求对象实现:
            标准的info、debug、warning、error、critical五个日志方法
        @param {function} server_status_info_fun=None - 外围传入的网络服务状态变更通知函数对象，当网络服务状态发生变更时通过:
            该函数通知调用方；形式为fun(server_status, result):
            其中server_status为服务器状态EnumServerRunStatus，
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
        @param {int} log_level=logging.INFO - 处理中正常日志的输出登记级别，默认为INFO，如果不想输出过多日志可以设置为DEBUG
        @param {string} server_name='NetService' - 服务名，记录日志使用
        @param {bool} is_auto_load_i18n=True - 是否自动加载i18n字典，如果继承类有自己的字典，可以重载__init__函数实现装载
        @param {string} trans_file_path='' - 要加载的i18n字典文件路径，如果填空代表程序运行的当前路径
        @param {string} trans_file_prefix='' - 要加载的i18n字典文件前缀
        @param {string} trans_file_encoding='utf-8' - 要加载的i18n字典文件的字符编

        """
        #############################
        # 私有变量 - 只用于框架内部处理的变量
        #############################

        # 外围传入的网络服务与客户端连接后对连接的处理线程函数:
        # 函数实现的第1个参数为线程ID，第2个参数为服务启动参数，第3个为连接信息
        # 需注意实现上应在每次循环时查询服务器关闭状态，如果遇到则结束处理
        self.__server_connect_deal_fun = None
        self.__server_connect_thread_id = 1  # 服务端的链接线程ID序列
        self.__server_connect_thread_list = {}  # 服务端正在运行的连接线程列表
        self.__server_connect_thread_list_lock = threading.RLock()  # 连接线程列表变更的同步锁

        # 赋值
        __trans_file_path = trans_file_path
        __trans_file_prefix = trans_file_prefix
        if trans_file_prefix == '':
            __trans_file_path = os.path.abspath(os.path.dirname(__file__))
            __trans_file_prefix = 'netservicefw'

        SimpleServerFW.__init__(self, logger=logger, server_status_info_fun=server_status_info_fun,
                                self_tag=self_tag, log_level=log_level, server_log_prefix='LIS',
                                server_name=server_name, is_auto_load_i18n=is_auto_load_i18n,
                                trans_file_path=__trans_file_path, trans_file_prefix=__trans_file_prefix,
                                trans_file_encoding=trans_file_encoding)
        self.__server_connect_deal_fun = server_connect_deal_fun

    def start_server(self, server_opts, is_wait=False):
        """
        启动网络服务(重载start_server函数)
        根据传入的服务器参数，启动网络服务监听线程，注意服务必须处于停止状态才能启动

        @param {object} server_opts - 启动服务器参数，由框架的实际实现类进行定义:
            子类通过_serverOpts.xxx获取具体的属性值
        @param {bool} is_wait=False - 是否等待服务启动完成后再退出

        @returns {CResult} - 启动结果，result.code：'00000'-成功，'21401'-服务不属于停止状态，不能启动，其他-异常

        """
        self._server_opts = server_opts
        return SimpleServerFW.start_server(self, is_wait=is_wait)

    #############################
    # 重载SimpleServerFW的处理函数
    #############################

    def _start_server_self(self, tid):
        """
        自定义服务启动函数，实现类可重载该函数加入自己的处理逻辑
        重载该函数，实现网络监听服务的启动，但不接收连接

        @param {int} tid - 线程id

        @returns {CResult} - 启动结果:
            result.code ：'00000'-成功，其他值为失败
            result.server_info ：启动成功后的服务对象，用于传递到后续的服务处理函数

        """
        _result = CResult(code='00000')  # 成功
        _result.server_info = NullObj()
        with ExceptionTool.ignored_cresult(_result):
            # 可在该部分实现自定义逻辑
            self._logger.log(
                self._log_level,
                '[%s-STARTING][NAME:%s]%s:\n%s' % (
                    self._server_log_prefix,
                    self._server_name,
                    _('net start parameter'),
                    StringTool.format_obj_property_str(self._server_opts, is_deal_subobj=True)
                )
            )

            # 启动服务，但不接受连接
            _result = self._start_server_without_accept(self._server_opts)
            _result.server_info = _result.net_info

        # 返回处理结果
        return _result

    def _stop_server_predeal_self(self, tid, server_info):
        """
        自定义服务停止前处理函数，实现类可重载该函数加入自己的处理逻辑（例如结束子线程）
        重载该函数，检查连接子线程是否均已结束，否则返回未完成，继续等待下一次检查

        @param {int} tid - 线程id
        @param {object} server_info - _start_server_self函数生成的server_info信息

        @returns {CResult} - 处理结果:
            result.code ：'00000'-成功，其他值为失败
            result.is_finished ：处理是否已完成，True - 已处理完成，False - 未完成，需循环再处理

        """
        _result = CResult(code='00000')  # 成功
        _result.is_finished = True
        if len(self.__server_connect_thread_list.keys()) > 0:
            _result.is_finished = False
        return _result

    def _stop_server_end_self(self, tid):
        """
        自定义服务停止后处理函数，实现类可重载该函数加入自己的处理逻辑
        重载该函数，执行连接线程的清理

        @param {int} tid - 线程id

        """
        # 清除连接线程
        self.__server_connect_thread_clear()
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
            # 监听下一个连接请求
            _accept_result = self._accept_one(self._server_opts, server_info)
            if _accept_result.is_success():
                # 获取到一个连接，创建线程
                self.__server_connect_thread_id = self.__server_connect_thread_id + 1
                _thread_id = self.__server_connect_thread_id
                _new_thread = threading.Thread(
                    target=self.__server_connect_thread_fun,
                    args=(_thread_id, self._server_opts, _accept_result.net_info),
                    name='Thread-ConnectDeal' + str(_thread_id)
                )
                self.__server_connect_thread_add(_thread_id, _new_thread)
                _new_thread.setDaemon(True)
                _new_thread.start()
            elif _accept_result.code != '20407':
                # 不是超时的其他获取错误，打印信息
                self._logger.log(
                    logging.ERROR,
                    "[%s][NAME:%s][EX:%s]%s: %s\n%s" % (
                        self._server_log_prefix,
                        self._server_name, str(type(_accept_result.error)),
                        _('accept net connection error'), _accept_result.msg,
                        _accept_result.trace_str
                    )
                )
            else:
                # 监听超时
                pass
        # 返回处理结果
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

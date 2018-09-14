#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
#
# Copyright 2018 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
TcpIp协议服务
@module tcpip_service
@file tcpip_service.py
"""

import os
import sys
import platform
import datetime
import socket
sys.path.append(os.path.abspath(os.path.dirname(__file__)+'/'+'../..'))
from HiveNetLib.simple_i18n import _, SimpleI18N
from HiveNetLib.net_service.net_service_fw import NetServiceFW
from HiveNetLib.generic import NullObj, CResult
from HiveNetLib.generic_enum import EnumLogLevel
from HiveNetLib.base_tools.exception_tool import ExceptionTool

__MOUDLE__ = 'tcpip_service'  # 模块名
__DESCRIPT__ = u'TcpIp协议服务'  # 模块描述
__VERSION__ = '0.1.0'  # 版本
__AUTHOR__ = u'黎慧剑'  # 作者
__PUBLISH__ = '2018.09.14'  # 发布日期


class TcpIpService(NetServiceFW):
    """
    TcpIp协议服务
    基于NetServiceFW框架

    """

    @staticmethod
    def generate_server_opts(ip='', port=8080, max_connect=20, recv_timeout=10000, send_timeout=10000):
        """
        生成默认服务启动参数

        @param {string} ip='' - 主机名或IP地址
        @param {int} port=8080 - 监听端口
        @param {int} max_connect=20 - 允许最大连接数
        @param {int} recv_timeout=10000 - 数据接收的超时时间，单位为毫秒
        @param {int} send_timeout=10000 - 数据发送的超时时间，单位为毫秒

        @returns {object} - 返回带参数属性的对象，例如对象为ret：
            ret.ip = ''
            ...

        """
        _server_opts = NullObj()
        _server_opts.ip = ip  # 主机名或IP地址
        _server_opts.port = 8080  # 监听端口
        _server_opts.max_connect = 20  # 允许最大连接数
        _server_opts.recv_timeout = 10000  # 数据接收的超时时间，单位为毫秒
        _server_opts.send_timeout = 10000  # 数据发送的超时时间，单位为毫秒
        return _server_opts

    def _start_server_without_accept(self, server_opts):
        """
        启动服务但不接受请求服务，该方法只做到启动端口层面，轮询监听不在该方法中实现:

        @param {object} server_opts - 服务参数

        @returns {CResult} - 启动结果:
            result.code ：'00000'-成功，其他值为失败
            result.net_info ：启动后的服务端网络连接信息对象，该对象将传给后续的监听线程（_AcceptOne），定义为：
                result.net_info.csocket - socket对象
                result.net_info.addr 地址对象，("IP地址",打开端口)

        """
        # 子类必须定义该功能
        _result = CResult('00000')
        _result.net_info = None
        with ExceptionTool.ignored_cresult(
            _result,
            logger=self._logger,
            self_log_msg='[LIS-STARTING][NAME:%s]%s - %s error: ' % (
                self._server_name, _('net service starting'), _('listen without accept')),
            force_log_level=EnumLogLevel.ERROR
        ):
            _sys_str = platform.system()
            _server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            _server_socket.bind((server_opts.ip, server_opts.port))
            _server_socket.listen(server_opts.max_connect)
            if (_sys_str == "Windows"):
                _server_socket.setsockopt(
                    socket.SOL_SOCKET, socket.SO_RCVTIMEO, server_opts.recv_timeout)
                _server_socket.setsockopt(
                    socket.SOL_SOCKET, socket.SO_SNDTIMEO, server_opts.send_timeout)
            else:
                # linux 设置超时时间不同，需重新测试
                _server_socket.settimeout(server_opts.recv_timeout/1000)
            _result.net_info = NullObj()
            _result.net_info.addr = (server_opts.ip, server_opts.port)
            _result.net_info.csocket = _server_socket
        return _result

    def _accept_one(self, server_opts, net_info):
        """
        监听接受一个请求并返回
        提供监听并获取到请求连接返回的方法；注意该该函数必须捕获并处理异常

        @param {objcet} server_opts - 网络服务启动参数
        @param {objcet} net_info - 网络连接信息对象，_start_server_without_accept中获取到的结果

        @returns {CResult} - 获取网络连接结果:
            result.code ：'00000'-成功，'20007'-获取客户端连接请求超时
            result.net_info ：客户端连接信息对象，该对象将传给后续单个连接处理的线程

        """
        # 子类必须定义该功能
        _result = CResult('00000')
        _result.net_info = None
        with ExceptionTool.ignored_cresult(
            _result,
            logger=self._logger,
            expect=(socket.timeout),
            error_map={socket.timeout: ('20007', None)},
            self_log_msg='[LIS][NAME:%s]%s error: ' % (
                self._server_name, _('accept client connect')),
            force_log_level=None
        ):
            _sys_str = platform.system()
            _csocket, _addr = net_info.csocket.accept()  # 接收客户端连接，返回客户端和地址
            _result.net_info = NullObj()
            _result.net_info.csocket = _csocket
            _result.net_info.addr = _addr
            if (_sys_str == "Windows"):
                _csocket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVTIMEO, server_opts.recv_timeout)
                _csocket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDTIMEO, server_opts.send_timeout)
            else:
                # linux 设置超时时间不同，需重新测试
                _csocket.settimeout(server_opts.recv_timeout / 1000)
            self._logger_fun[self._log_level](
                '[LIS][NAME:%s]%s: %s - %s' % (
                    self._server_name, _('accept one client connection'), str(_addr), str(_csocket)
                )
            )
        return _result

    @classmethod
    def recv_data(cls, net_info, recv_para):
        """
        从指定的网络连接中读取数据

        @param {object} net_info - 要读取数据的网络信息对象（例如socket对象）
        @param {dict} recv_para - 读取数据的参数, 包括：
            recv_len {int} - 要获取的数据长度

        @returns {CResult} - 数据获取结果:
            result.code ：'00000'-成功，'20003'-获取数据超时，其他为获取失败
            result.data ：获取到的数据对象（具体类型和定义，由实现类自定义）
            result.recv_time : datetime 实际开始接受数据时间

        """
        # 子类必须定义该功能
        _result = CResult('00000')
        _result.data = None
        _result.recv_time = datetime.datetime.now()
        with ExceptionTool.ignored_cresult(
            _result,
            logger=None,
            expect=(socket.timeout),
            error_map={socket.timeout: ('20003', None)}
        ):
            _result.data = net_info.csocket.recv(recv_para['recv_len'])
            if len(_result.data) < recv_para['recv_len']:
                # 获取数据数量不足，认为超时
                _result.change_code(code='20003')
        return _result

    @classmethod
    def send_data(cls, net_info, send_para, data):
        """
        向指定的网络连接发送数据

        @param {object} net_info - 要写入数据的网络信息对象（例如socket对象）
        @param {dict} send_para - 写入数据的参数，包括
            data {bytes} - 要发送的二进制数据
        @param {object} data - 要写入的数据对象（具体类型和定义，由实现类自定义）

        @returns {CResult} - 发送结果:
            result.code ：'00000'-成功，'20004'-写入数据超时，其他为写入失败
            result.send_time : datetime 实际发送完成时间

        """
        # 子类必须定义该功能
        _result = CResult('00000')
        _result.send_time = None
        with ExceptionTool.ignored_cresult(
            _result,
            logger=None,
            expect=(socket.timeout),
            error_map={socket.timeout: ('20004', None)}
        ):
            net_info.csocket.send(data)
            _result.send_time = datetime.datetime.now()
        return _result

    @classmethod
    def close_connect(cls, net_info):
        """
        关闭指定的网络连接，注意该该函数必须捕获并处理异常

        @param {object} net_info - 需要关闭的网络连接信息对象

        @returns {CResult} - 关闭结果
            result.code ：'00000'-成功，其他值为失败

        """
        # 子类必须定义该功能
        _result = CResult('00000')
        with ExceptionTool.ignored_cresult(
            _result,
            logger=None
        ):
            net_info.csocket.close()
        return _result

    @classmethod
    def connect_server(cls, connect_para):
        """
        客户端通过该函数连接服务器端

        @param {object} connect_para - 需要连接服务器的参数，与server_opts一致

        @returns {CResult} - 连接结果:
            result.code ：'00000'-成功，其他值为失败
            result.net_info ： 连接后的网络信息对象

        """
        # 子类必须定义该功能
        _result = CResult('00000')
        _result.net_info = None
        with ExceptionTool.ignored_cresult(
            _result,
            logger=None
        ):
            _sys_str = platform.system()
            _tcp_cli_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # 分配 TCP 客户端套接字
            _tcp_cli_sock.connect((connect_para.ip, connect_para.port))  # 主动连接
            if (_sys_str == "Windows"):
                _tcp_cli_sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVTIMEO,
                                         connect_para.recv_timeout)
                _tcp_cli_sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDTIMEO,
                                         connect_para.send_timeout)
            else:
                # linux 设置超时时间不同，需重新测试
                _tcp_cli_sock.settimeout(connect_para.recv_timeout / 1000)
            _result.net_info = NullObj()
            _result.net_info.csocket = _tcp_cli_sock
            _result.net_info.addr = (connect_para.ip, connect_para.port)
        return _result

    def get_server_info(self, para_name, default_value=None):
        """
        获取服务器信息

        @param {string} para_name - 参数名
        @param {object} default_value=None - 参数值

        @returns {object} - 返回具体的参数值对象（实现类自定义）

        """
        return self._get_server_opts(para_name, default_value=default_value)

    @classmethod
    def get_client_info(cls, net_info, para_name, default_value=None):
        """
        获取指定客户端连接的信息，根据传入的参数获取参数值（具体可以获取什么参数由实现类自定义）

        @param {object} net_info - 客户端网络连接信息对象
        @param {string} para_name - 参数名

        @returns {object} - 返回具体的参数值对象（实现类自定义）

        """
        if para_name == "ip":
            return net_info.addr[0]
        elif para_name == "port":
            return net_info.addr[1]
        elif para_name == "socket":
            return net_info.csocket
        else:
            return default_value


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    # 打印版本信息
    print(('模块名：%s  -  %s\n'
           '作者：%s\n'
           '发布日期：%s\n'
           '版本：%s' % (__MOUDLE__, __DESCRIPT__, __AUTHOR__, __PUBLISH__, __VERSION__)))

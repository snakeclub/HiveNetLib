#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
#
# Copyright 2018 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
gRPC客户端应用

@module grpc_client
@file grpc_client.py
"""

import os
import sys
import logging
# 根据当前文件路径将包路径纳入，在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir, os.path.pardir)))
from HiveNetLib.generic import NullObj, CResult
from HiveNetLib.simple_grpc.grpc_tool import SimpleGRpcTools, EnumCallMode
import HiveNetLib.simple_grpc.msg_pb2 as msg_pb2
from HiveNetLib.base_tools.call_chain_tool import CallChainTool


__MOUDLE__ = 'grpc_client'  # 模块名
__DESCRIPT__ = u'gRPC客户端应用'  # 模块描述
__VERSION__ = '0.1.0'  # 版本
__AUTHOR__ = u'黎慧剑'  # 作者
__PUBLISH__ = '2019.06.30'  # 发布日期


class SimpleGRpcConnection(object):
    """
    封装SimpleGRpc的客户端连接方法
    """
    #############################
    # 内部变量
    #############################
    _connect_para = None  # 客户端的连接参数
    _channel = None  # grpc连接
    _stub = None  # grpc的stub
    _health_stub = None  # 健康检查的stub

    # 部分连接参数直接增加一个引用，便于代码处理
    _logger = None
    _log_level = logging.INFO
    _test_on_connect = True
    _test_use_health_check = False
    _servicer_name = ''
    _timeout = None

    # 用于临时缓存trace_id的对象，key为当次callid，value为当前的trace_info(NullObj)
    _trace_info_dict = dict()

    #############################
    # 静态函数
    #############################
    @staticmethod
    def generate_connect_para(
        ip='', port=50051, conn_str=None, timeout=None,
        is_use_ssl=False, root_certificates=None,
        private_key=None, certificate_chain=None,
        options=None, compression=None,
        test_on_connect=True, test_use_health_check=False, servicer_name='',
        logger=None, log_level=logging.INFO
    ):
        """
        生成客户端连接参数

        @param {string} ip='' - 要连接的服务器IP
            注意：TSLSSL模式下，客户端是通过"服务名称:port"来获取服务的凭据，而不是"ip:port"，
            如果使用TSL/SSL的情况客户端连接失败，可从这个角度排查解决问题
        @param {int} port=50051 - 要连接的服务器端口
        @param {conn_str} conn_str=None - 连接字符串，如果传入该字符串则不再使用ip和端口方式连接
            连接字符串的格式如下：'ip协议(ipv4|ipv6):///ip1:port1,ip2:port2,...'
            例如"ipv4:///1.2.3.4:9999,1.2.3.5:9999,1.2.3.6:9999"
                "ipv6:///[1::2]:9999,[1::3]:9999,[1::4]:9999"
        @param {number} timeout=None - 超时时间，单位为秒
        @param {bool} is_use_ssl=False - 是否使用SSL/TLS
        @param {bytes} root_certificates=None - 用于验证服务器证书的根证书，即服务器端的公钥证书
            The PEM-encoded root certificates as a byte string
            with open('ca.crt', 'rb') as f:
                root_certificates = f.read()
        @param {bytes} private_key=None - 当反向认证时（服务器验证客户端证书），客户端的私钥文件
            The PEM-encoded private key as a byte string
            with open('server.pem', 'rb') as f:
                private_key = f.read()
        @param {bytes} certificate_chain=None - 当反向认证时（服务器验证客户端证书），客户端的公钥证书文件
            The PEM-encoded certificate chain as a byte string
            with open('server.crt', 'rb') as f:
                certificate_chain = f.read()
        @param {?} options=None - An optional list of key-value pairs (channel args in gRPC Core runtime) to configure the channel
        @param {?} compression=None - An optional value indicating the compression method to be used over the lifetime of the channel
        @param {bool} test_on_connect=True - 连接时进行有效性测试
        @param {bool} test_use_health_check=False - 使用标准的health_check进行测试
        @param {string} servicer_name='' - 使用health_check进行测试的对应服务名（由服务端定义）
        @param {Logger} logger=None - 日志对象，服务过程中通过该函数写日志:
            可以为标准的logging日志库对象，也可以为simple_log对象，但要求对象实现:
            标准的info、debug、warning、error、critical五个日志方法
        @param {int} log_level=logging.INFO - 处理中正常日志的输出登记级别，默认为INFO，如果不想输出
            过多日志可以设置为DEBUG

        @returns {object} - 返回带参数属性的对象，例如对象为ret：
            ret.ip = ''
            ...

        """
        _connect_para = NullObj()
        _connect_para.ip = ip
        _connect_para.port = port
        _connect_para.conn_str = conn_str
        _connect_para.timeout = timeout
        _connect_para.is_use_ssl = is_use_ssl  # 是否使用SSL/TLS
        _connect_para.private_key = private_key
        _connect_para.certificate_chain = certificate_chain
        _connect_para.root_certificates = root_certificates
        _connect_para.options = options
        _connect_para.compression = compression
        _connect_para.test_on_connect = test_on_connect
        _connect_para.test_use_health_check = test_use_health_check
        _connect_para.servicer_name = servicer_name
        _connect_para.logger = logger
        _connect_para.log_level = log_level
        return _connect_para

    #############################
    # 公共函数
    #############################
    def __init__(self, connect_para):
        """
        构造函数

        @param {NullObj} connect_para - 具体参数见SimpleGRpcConnection.generate_connect_para函数的定义

        @throws {ConnectionError} - 如果连接时需要检查有效性，当检查失败时抛出该异常
        """
        # 初始化参数
        self._connect_para = connect_para
        if hasattr(connect_para, 'test_on_connect'):
            self._test_on_connect = connect_para.test_on_connect
        if hasattr(connect_para, 'test_use_health_check'):
            self._test_use_health_check = connect_para.test_use_health_check
        if hasattr(connect_para, 'servicer_name'):
            self._servicer_name = connect_para.servicer_name
        if hasattr(connect_para, 'logger'):
            self._logger = connect_para.logger
        if hasattr(connect_para, 'log_level'):
            self._log_level = connect_para.log_level
        if hasattr(connect_para, 'timeout'):
            self._timeout = connect_para.timeout

        # 进行连接
        self._channel = SimpleGRpcTools.generate_channel(self._connect_para)
        self._stub = SimpleGRpcTools.generate_call_stub(self._channel)

        # 检查连接有效性
        if self._test_on_connect:
            _check_result = self.test()
            if _check_result.status != msg_pb2.HealthResponse.SERVING:
                # 连接失败，打印日志后抛出异常
                if self._logger is not None:
                    self._logger.log(
                        self._log_level,
                        '[EX:%s]%s%s\n%s' % (
                            _check_result.error,
                            'SimpleGRpcConnection init error: ',
                            _check_result.msg,
                            _check_result.trace_str
                        )
                    )
                raise ConnectionError(_check_result.msg)

    def test(self):
        """
        检测连接是否有效

        @returns {CResult} - 响应对象，判断成功的方法：
            ret.status == msg_pb2.HealthResponse.SERVING
            总共有以下几种状态
            health_pb2.HealthResponse.UNKNOWN
            health_pb2.HealthResponse.SERVICE_UNKNOWN
            health_pb2.HealthResponse.NOT_SERVING
            health_pb2.HealthResponse.SERVING
        """
        _check_result = None
        if self._test_use_health_check:
            # 使用标准健康检查
            self._health_stub = SimpleGRpcTools.generate_health_check_stub(self._channel)
            _check_result = SimpleGRpcTools.health_check_by_stub(
                self._health_stub, self._servicer_name, timeout=self._timeout)
        else:
            # 使用自定义的健康检查
            _check_result = SimpleGRpcTools.simple_grpc_health_check_by_stub(
                self._stub, timeout=self._timeout
            )
        # 返回结果
        return _check_result

    def close(self):
        """
        关闭连接
        """
        if self._channel is not None:
            self._channel.close()
            self._channel = None
            self._stub = None
            self._health_stub = None

    def reconnect(self):
        """
        重新连接

        @returns {CResult} - 响应对象，判断成功的方法：
            ret.status == msg_pb2.HealthResponse.SERVING
            总共有以下几种状态
            health_pb2.HealthResponse.UNKNOWN
            health_pb2.HealthResponse.SERVICE_UNKNOWN
            health_pb2.HealthResponse.NOT_SERVING
            health_pb2.HealthResponse.SERVING
        """
        # 先关闭连接
        self.close()

        # 进行连接
        self._channel = SimpleGRpcTools.generate_channel(self._connect_para)
        self._stub = SimpleGRpcTools.generate_call_stub(self._channel)

        # 检查连接有效性
        if self._test_on_connect:
            _check_result = self.test()
            if _check_result.status != msg_pb2.HealthResponse.SERVING:
                # 连接失败，打印日志后抛出异常
                if self._logger is not None:
                    self._logger.log(
                        self._log_level,
                        '[EX:%s]%s%s\n%s' % (
                            _check_result.error,
                            'SimpleGRpcConnection reconnect error: ',
                            _check_result.msg,
                            _check_result.trace_str
                        )
                    )
            return _check_result
        else:
            # 不检查的情况，直接返回成功，但注意连接状态为UNKNOWN
            _check_result = CResult('00000')
            _check_result.status = msg_pb2.HealthResponse.UNKNOWN
            return _check_result

    def call(self, rpc_request, call_mode=EnumCallMode.Simple,
             timeout=None, metadata=None, credentials=None,
             wait_for_ready=None, compression=None):
        """
        执行gRPC远程调用

        @param {msg_pb2.RpcRequest|request_iterator} rpc_request - 请求对象或产生请求对象的迭代器（iterator），应与call_mode匹配
        @param {EnumCallMode} call_mode=EnumCallMode.Simple - 调用服务端的模式
        @param {number} timeout=None - 超时时间，单位为秒
        @param {object} metadata=None - Optional :term:`metadata` to be transmitted to the
            service-side of the RPC.
        @param {object} credentials=None - An optional CallCredentials for the RPC. Only valid for
            secure Channel.
        @param {object} wait_for_ready=None - This is an EXPERIMENTAL argument. An optional
            flag to enable wait for ready mechanism
        @param {object} compression=None - An element of grpc.compression, e.g.
            grpc.compression.Gzip. This is an EXPERIMENTAL option.

        @returns {CResult|iterator} - 执行结果CResult或执行结果的迭代器（iterator），与call_mode匹配
            CResult对象有以下3个属性：
            return_json - 返回值的json字符串
            has_return_bytes - 是否有返回字节数组
            return_bytes - 返回的字节数组
        """
        _call_id = CallChainTool.generate_trace_id()  # 获取一个统一的ID，用于在对象中传递打印的trace信息
        _request = rpc_request
        # 发送之前记录日志
        if self._logger is not None:
            if call_mode in [EnumCallMode.Simple, EnumCallMode.ServerSideStream]:
                _request = self._call_before_write_log(
                    rpc_request=_request, call_mode=call_mode,
                    timeout=timeout, call_id=_call_id
                )
            else:
                _request = self._call_before_write_log_iterator(
                    rpc_request=_request, call_mode=call_mode,
                    timeout=timeout, call_id=_call_id
                )

        # 执行调用
        _cresult = SimpleGRpcTools.grpc_call_by_stub(
            self._stub, rpc_request=_request, call_mode=call_mode,
            timeout=timeout, metadata=metadata, credentials=credentials,
            wait_for_ready=wait_for_ready, compression=compression
        )

        # 接收响应后记录日志
        if self._logger is not None:
            pass

        # 返回结果
        return _cresult

    #############################
    # 私有函数
    #############################
    def __del__(self):
        """
        销毁函数，需要关闭连接
        """
        self.close()

    def _call_before_write_log(self, rpc_request, call_mode=EnumCallMode.Simple,
                               timeout=None, call_id=''):
        """
        远程调用前写日志，并返回要调用的参数
        """
        # 登记调用日志

        return rpc_request

    def _call_before_write_log_iterator(self, rpc_request, call_mode=EnumCallMode.Simple,
                                        timeout=None, call_id=''):
        """
        远程调用前写日志，并返回要调用的iterator对象
        """
        for _request in rpc_request:
            # 逐个登记调用日志

            # 返回调用对象
            yield _request

    def _call_after_write_log(self, cresult, call_mode=EnumCallMode.Simple, call_id=''):
        """
        登记返回结果日志
        """
        # 登记返回结果日志

        return cresult

    def _call_after_write_log_iterator(self, cresult_iterator, call_mode=EnumCallMode.Simple, call_id=''):
        for _cresult in cresult_iterator:
            # 逐个登记返回结果日志

            # 返回结果对象
            yield _cresult


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    # 打印版本信息
    print(('模块名：%s  -  %s\n'
           '作者：%s\n'
           '发布日期：%s\n'
           '版本：%s' % (__MOUDLE__, __DESCRIPT__, __AUTHOR__, __PUBLISH__, __VERSION__)))

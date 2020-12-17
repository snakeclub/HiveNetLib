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
import copy
import datetime
# 根据当前文件路径将包路径纳入，在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir, os.path.pardir)))
# 自有包引用
from HiveNetLib.generic import NullObj, CResult
from HiveNetLib.simple_grpc.grpc_tool import SimpleGRpcTools, EnumCallMode
import HiveNetLib.simple_grpc.msg_pb2 as msg_pb2
from HiveNetLib.base_tools.call_chain_tool import CallChainTool
from HiveNetLib.base_tools.run_tool import RunTool
from HiveNetLib.interface_tool.msg_json import MsgJSON
from HiveNetLib.connection_pool.pool_fw import ConnectionPoolFw


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
    _trace_info_dict = None

    #############################
    # 静态函数
    #############################
    @staticmethod
    def generate_connect_para(
        ip='', port=50051, conn_str=None, timeout=None,
        is_use_ssl=False, root_certificates=None,
        private_key=None, certificate_chain=None,
        options=None, compression=None,
        test_on_connect=False, test_use_health_check=False, servicer_name='',
        logger=None, log_level=logging.INFO, is_use_global_logger=True,
        idpool=None, get_id_overtime=0,
        send_logging_para={}, back_logging_para={},
        **kwargs
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
        @param {bool} test_on_connect=False - 连接时进行有效性测试
        @param {bool} test_use_health_check=False - 使用标准的health_check进行测试
        @param {string} servicer_name='' - 使用health_check进行测试的对应服务名（由服务端定义）
        @param {Logger} logger=None - 日志对象，服务过程中通过该函数写日志:
            可以为标准的logging日志库对象，也可以为simple_log对象，但要求对象实现:
            标准的info、debug、warning、error、critical五个日志方法
        @param {int} log_level=logging.INFO - 处理中正常日志的输出登记级别，默认为INFO，如果不想输出
            过多日志可以设置为DEBUG
        @param {bool} is_use_global_logger=True - 当logger=None时，是否使用全局logger对象
            注：通过RunTool.set_global_logger进行设置
        @param {HiveNetLib.IdPool} idpool=None - 获取id的资源池，如果传入None代表直接通过uuid生成id
        @param {number} get_id_overtime=0 - 超时时间，单位为秒，如果需要一直不超时送入0
        @param {dict} send_logging_para={} - 接收报文打印参数
        @param {dict} back_logging_para={} - 返回报文打印参数
            send_logging_para的参数格式一致，定义如下：
            'msg_class' {class} - 继承MsgFW框架的报文解析类对象，如果为None代表不处理信息
            'logging_head' {dict}- 定义打印的日志规范头信息
                key {string} - 日志头信息项名，例如'IP'
                value {string} - 日志头信息值，None代表从报文对象msg或proto_msg中获取(从api_mapping获取定义)
                跟当前服务相关的可选信息项包括：
                C-IP : 客户端的IP地址
                C-PORT : 客户端的连接端口
                S-IP : 服务端绑定服务
                S-PORT : 服务端监听端口
                SERVICE_NAME : 访问的服务名
                PARA_BYTES : 转换为字符串显示的参数字节数组信息
                PARA_BYTES_LEN : 字节数组长度
                RETURN_BYTES : 转换为字符串显示的响应字节数组信息
                RETURN_BYTES_LEN ： 响应报文字节数组长度

            'api_mapping' {dict}- 定义从报文中获取logging_head所需的信息
            'key_para' {dict} - 要打印的关键业务参数
            'print_in_para' {dict} - 要打印的指定接口字段
                以上三项的定义都是一样
                key {string} - 打印信息项名
                value {list}- 映射信息，为三项的数组:
                    value[0] {string} - 获取api对象类型，'msg'或'proto_msg'
                    value[1] {string} - 搜索路径，具体规则参考对应的MsgFW实例
                    value[2] {dict} - 获取参数,具体规则参考对应的MsgFW实例

            'is_print_msg' {bool} - 是否打印报文内容
            'msg_print_kwargs' {dict} - MsgFW对象（例如MsgJSON）的msg.to_str()函数的传入参数
        @param {kwargs}  - 动态参数，已定义的参数如下：
            id的资源池的get_id传入参数

        @returns {object} - 返回带参数属性的对象，例如对象为ret：
            ret.ip = ''
            ...

        """
        _connect_para = NullObj()
        _connect_para.ip = ip
        _connect_para.port = port
        _connect_para.conn_str = conn_str
        if conn_str == '':
            _connect_para.conn_str = None
        _connect_para.timeout = timeout
        if timeout is not None and timeout <= 0:
            _connect_para.timeout = None
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
        _connect_para.is_use_global_logger = is_use_global_logger
        _connect_para.idpool = idpool
        _connect_para.get_id_overtime = get_id_overtime
        _connect_para.send_logging_para = send_logging_para
        _connect_para.back_logging_para = back_logging_para
        _connect_para.kwargs = kwargs
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
        # 内部变量初始化
        self._trace_info_dict = dict()

        # 初始化参数
        self._connect_para = connect_para
        self._fill_connect_para(self._connect_para)
        self._test_on_connect = connect_para.test_on_connect
        self._test_use_health_check = connect_para.test_use_health_check
        self._servicer_name = connect_para.servicer_name
        self._logger = connect_para.logger
        self._log_level = connect_para.log_level
        self._timeout = connect_para.timeout

        # 日志处理
        if self._logger is None and connect_para.is_use_global_logger:
            # 使用全局logger
            self._logger = RunTool.get_global_logger()

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
        _check_result = CResult()
        if self._channel is None:
            # 没有连接
            _check_result.status = msg_pb2.HealthResponse.UNKNOWN
        elif self._test_use_health_check:
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
            if not _check_result.is_success() or _check_result.status != msg_pb2.HealthResponse.SERVING:
                # 连接失败，打印日志后抛出异常
                if self._logger is not None:
                    self._logger.log(
                        self._log_level,
                        '[EX:%s]%s%s, service status:%s\n%s' % (
                            _check_result.error,
                            'SimpleGRpcConnection reconnect error: ',
                            _check_result.msg,
                            _check_result.status,
                            _check_result.trace_str
                        )
                    )
            return _check_result
        else:
            # 不检查的情况，直接返回成功，连接状态为SERVING
            _check_result = CResult('00000')
            _check_result.status = msg_pb2.HealthResponse.SERVING
            return _check_result

    def call(self, rpc_request, call_mode=EnumCallMode.Simple,
             timeout=None, metadata=None, credentials=None,
             wait_for_ready=None, compression=None, **kwargs):
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
        @param {**kwargs} kwargs - 动态参数，用于支持调用链信息

        @returns {CResult|iterator} - 执行结果CResult或执行结果的迭代器（iterator），与call_mode匹配
            CResult对象有以下3个属性：
            return_json - 返回值的json字符串
            has_return_bytes - 是否有返回字节数组
            return_bytes - 返回的字节数组
        """
        _start_time = datetime.datetime.now()  # 开始处理时间
        _trace_info = self._get_trace_info(**kwargs)  # 获取调用链信息
        _request = None
        _timeout = timeout
        if timeout is None or timeout <= 0:
            _timeout = self._connect_para.timeout

        # 发送之前记录日
        if call_mode in [EnumCallMode.Simple, EnumCallMode.ServerSideStream]:
            _request = self._call_before_write_log(
                rpc_request=rpc_request, call_mode=call_mode,
                timeout=_timeout, trace_info=_trace_info
            )
        else:
            _request = self._call_before_write_log_iterator(
                rpc_request=rpc_request, call_mode=call_mode,
                timeout=_timeout, trace_info=_trace_info
            )

        # 执行调用
        _cresult_call = SimpleGRpcTools.grpc_call_by_stub(
            self._stub, rpc_request=_request, call_mode=call_mode,
            timeout=_timeout, metadata=metadata, credentials=credentials,
            wait_for_ready=wait_for_ready, compression=compression
        )

        # 接收响应后记录日志
        if call_mode in [EnumCallMode.Simple, EnumCallMode.ClientSideStream]:
            _cresult = self._call_after_write_log(
                _cresult_call, _start_time, call_mode=call_mode,
                timeout=_timeout, trace_info=_trace_info
            )
        else:
            _cresult = self._call_after_write_log_iterator(
                _cresult_call, _start_time, call_mode=call_mode,
                timeout=_timeout, trace_info=_trace_info
            )

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

    def _fill_connect_para(self, connect_para):
        """
        补充完整connect_para的基本属性

        @param {NullObj} connect_para - 要补充的连接参数对象
        """
        # 设置默认值
        if not hasattr(connect_para, 'ip'):
            connect_para.ip = ''
        if not hasattr(connect_para, 'port'):
            connect_para.port = 50051
        if not hasattr(connect_para, 'conn_str'):
            connect_para.conn_str = None
        if not hasattr(connect_para, 'timeout'):
            connect_para.timeout = None
        if not hasattr(connect_para, 'is_use_ssl'):
            connect_para.is_use_ssl = False
        if not hasattr(connect_para, 'root_certificates'):
            connect_para.root_certificates = None
        if not hasattr(connect_para, 'private_key'):
            connect_para.private_key = None
        if not hasattr(connect_para, 'certificate_chain'):
            connect_para.certificate_chain = None
        if not hasattr(connect_para, 'options'):
            connect_para.options = None
        if not hasattr(connect_para, 'compression'):
            connect_para.compression = None
        if not hasattr(connect_para, 'test_on_connect'):
            connect_para.test_on_connect = True
        if not hasattr(connect_para, 'test_use_health_check'):
            connect_para.test_use_health_check = False
        if not hasattr(connect_para, 'servicer_name'):
            connect_para.servicer_name = ''
        if not hasattr(connect_para, 'logger'):
            connect_para.logger = None
        if not hasattr(connect_para, 'log_level'):
            connect_para.log_level = logging.INFO
        if not hasattr(connect_para, 'is_use_global_logger'):
            connect_para.is_use_global_logger = True
        if not hasattr(connect_para, 'idpool'):
            connect_para.idpool = None
        if not hasattr(connect_para, 'get_id_overtime'):
            connect_para.get_id_overtime = 0
        if not hasattr(connect_para, 'send_logging_para'):
            connect_para.send_logging_para = {}
        if not hasattr(connect_para, 'back_logging_para'):
            connect_para.back_logging_para = {}
        if not hasattr(connect_para, 'kwargs'):
            connect_para.kwargs = {}

        # 日志打印参数处理
        _default_logging_para = {
            'msg_class': MsgJSON,
            'api_mapping': {},
            'logging_head': {
                'CALL_MODE': '',
                'SERVICE_NAME': '',
                'PARA_BYTES_LEN': '',
            },
            'is_print_msg': True,
            'msg_print_kwargs': {},
            'key_para': {},
            'print_in_para': {}
        }
        _send_logging_para = copy.deepcopy(_default_logging_para)
        _send_logging_para.update(connect_para.send_logging_para)
        connect_para.send_logging_para = _send_logging_para
        _back_logging_para = copy.deepcopy(_default_logging_para)
        _back_logging_para.update(connect_para.back_logging_para)
        connect_para.back_logging_para = _back_logging_para

    def _call_before_write_log(self, rpc_request, call_mode=EnumCallMode.Simple,
                               timeout=None, trace_info=None):
        """
        远程调用前写日志，并返回要调用的参数
        """
        # 增加调用链信息
        rpc_request.trace_id = trace_info.trace_id
        rpc_request.parent_id = trace_info.call_id
        rpc_request.trace_level = trace_info.trace_level

        if self._logger is not None:
            # 登记调用日志
            _info_dict = self._get_request_info_dict(
                rpc_request, call_mode=call_mode, timeout=timeout, trace_info=trace_info
            )
            _info_dict['err_log_msg'] = 'api call chain send log error'
            SimpleGRpcTools.write_api_call_chain_log(self._logger, _info_dict)

        return rpc_request

    def _call_before_write_log_iterator(self, rpc_request, call_mode=EnumCallMode.Simple,
                                        timeout=None, trace_info=None):
        """
        远程调用前写日志，并返回要调用的iterator对象
        """
        for _request in rpc_request:
            # 增加调用链信息
            _request.trace_id = trace_info.trace_id
            _request.parent_id = trace_info.call_id
            _request.trace_level = trace_info.trace_level

            if self._logger is not None:
                # 逐个登记调用日志
                _info_dict = self._get_request_info_dict(
                    _request, call_mode=call_mode, timeout=timeout, trace_info=trace_info
                )
                _info_dict['api_info_type'] = 'STREAM-SEND'
                _info_dict['err_log_msg'] = 'api call chain send log error'
                SimpleGRpcTools.write_api_call_chain_log(self._logger, _info_dict)

            # 返回调用对象
            yield _request

    def _call_after_write_log(self, cresult, start_time, call_mode=EnumCallMode.Simple,
                              timeout=None, trace_info=None):
        """
        登记返回结果日志
        """
        if self._logger is not None:
            # 登记返回结果日志
            _info_dict = self._get_cresult_info_dict(
                cresult, start_time, call_mode=call_mode, timeout=timeout, trace_info=trace_info
            )
            _info_dict['err_log_msg'] = 'api call chain back log error'
            SimpleGRpcTools.write_api_call_chain_log(self._logger, _info_dict)

        return cresult

    def _call_after_write_log_iterator(self, cresult_iterator, start_time, call_mode=EnumCallMode.Simple,
                                       timeout=None, trace_info=None):
        for _cresult in cresult_iterator:
            if self._logger is not None:
                # 逐个登记返回结果日志
                _info_dict = self._get_cresult_info_dict(
                    _cresult, start_time, call_mode=call_mode, timeout=timeout, trace_info=trace_info
                )
                _info_dict['err_log_msg'] = 'api call chain back log error'
                SimpleGRpcTools.write_api_call_chain_log(self._logger, _info_dict)

            # 返回结果对象
            yield _cresult

    def _get_trace_info(self, **kwargs):
        """
        获取调用链信息

        @param {**kwargs} kwargs - 动态参数，用于支持调用链信息

        @return {NullObj} - 从kwargs获取信息处理后的调用链信息
        """
        _trace_info = NullObj()
        _trace_info.trace_id = ''
        _trace_info.parent_id = ''
        _trace_info.trace_level = 0
        _trace_info.call_id = CallChainTool.generate_trace_id(
            idpool=self._connect_para.idpool,
            get_id_overtime=self._connect_para.get_id_overtime,
            **self._connect_para.kwargs
        )  # 当前函数的执行id

        if 'trace_id' in kwargs.keys():
            _trace_info.trace_id = kwargs['trace_id']
        if 'parent_id' in kwargs.keys():
            _trace_info.parent_id = kwargs['parent_id']
        if 'trace_level' in kwargs.keys():
            _trace_info.trace_level = kwargs['trace_level']

        if _trace_info.trace_id == '':
            # 上送请求没有调用链，则链从自己开始
            _trace_info.trace_id = _trace_info.call_id
            _trace_info.trace_level = 0
        else:
            _trace_info.trace_level = _trace_info.trace_level + 1
        # 返回信息
        return _trace_info

    def _get_request_info_dict(self, request, call_mode=EnumCallMode.Simple, timeout=None, trace_info=None):
        """
        生成请求日志信息字典

        @param {msg_pb2.RpcRequest} rpc_request - 请求对象
        @param {EnumCallMode} call_mode=EnumCallMode.Simple - 调用服务端的模式
        @param {number} timeout=None - 超时时间，单位为秒
        @param {NullObj} trace_info=None - 调用链信息
            注：在这里也会借助trace_info传递一些请求参数给返回值填入, 包括
                trace_info.service_name

        @return {dict} - 日志结果信息
        """
        _dict = dict()
        # 默认信息
        _dict['use'] = 0
        _dict['error'] = None
        _dict['trace_str'] = ''
        _dict['log_level'] = self._log_level
        _dict['call_fun_level'] = 2
        # 基本信息
        _dict['trace_id'] = trace_info.trace_id
        _dict['parent_id'] = trace_info.parent_id
        _dict['trace_level'] = trace_info.trace_level
        _dict['call_id'] = trace_info.call_id
        _dict['api_call_type'] = 'SEND'
        _dict['api_info_type'] = 'SEND'
        # 基本信息
        _dict['call_mode'] = call_mode
        _dict['para_json'] = request.para_json
        # IP信息
        _dict['c-ip'] = ''
        _dict['c-port'] = ''
        _dict['s-ip'] = ''
        _dict['s-port'] = ''
        # 请求报文信息
        _dict['service_name'] = request.service_name
        trace_info.service_name = request.service_name
        # 获取日志打印参数
        _dict['logging_para'] = copy.deepcopy(self._connect_para.send_logging_para)
        # 请求信息的bytes数组
        if request.para_bytes is None:
            _dict['para_bytes_len'] = 'None'
            _dict['para_bytes'] = 'None'
        else:
            _dict['para_bytes_len'] = str(len(request.para_bytes))
            if 'PARA_BYTES' in _dict['logging_para']['logging_head'].keys():
                _dict['para_bytes'] = str(request.para_bytes)
            else:
                _dict['para_bytes'] = 'None'

        # 返回字典
        return _dict

    def _get_cresult_info_dict(self, cresult, start_time, call_mode=EnumCallMode.Simple, timeout=None, trace_info=None):
        """
        生成结果日志信息字典

        @param {CResult} cresult - 请求结果
        @param {datetime} start_time - 请求开始时间
        @param {EnumCallMode} call_mode=EnumCallMode.Simple - 调用服务端的模式
        @param {number} timeout=None - 超时时间，单位为秒
        @param {NullObj} trace_info=None - 调用链信息

        @return {dict} - 日志结果信息
        return_json - 返回值的json字符串
            has_return_bytes - 是否有返回字节数组
            return_bytes - 返回的字节数组
        """
        _dict = dict()
        # 默认信息
        _dict['error'] = None
        _dict['trace_str'] = ''
        _dict['log_level'] = self._log_level
        _dict['call_fun_level'] = 2
        # 基本信息
        _dict['trace_id'] = trace_info.trace_id
        _dict['parent_id'] = trace_info.parent_id
        _dict['trace_level'] = trace_info.trace_level
        _dict['call_id'] = trace_info.call_id
        _dict['api_call_type'] = 'SEND'
        _dict['api_info_type'] = 'BACK'
        if call_mode in (EnumCallMode.BidirectionalStream, EnumCallMode.ServerSideStream):
            _dict['api_info_type'] = 'STREAM-BACK'
        # 基本信息
        _dict['call_mode'] = call_mode
        _dict['para_json'] = cresult.return_json
        # IP信息
        _dict['c-ip'] = ''
        _dict['c-port'] = ''
        _dict['s-ip'] = ''
        _dict['s-port'] = ''
        # 请求报文信息，service_name不能正常显示
        _dict['service_name'] = trace_info.service_name
        # 获取日志打印参数
        _dict['logging_para'] = copy.deepcopy(self._connect_para.back_logging_para)
        # 请求信息的bytes数组
        if cresult.return_bytes is None:
            _dict['para_bytes_len'] = 'None'
            _dict['para_bytes'] = 'None'
        else:
            _dict['para_bytes_len'] = str(len(cresult.return_bytes))
            if 'PARA_BYTES' in _dict['logging_para']['logging_head'].keys():
                _dict['para_bytes'] = str(cresult.return_bytes)
            else:
                _dict['para_bytes'] = 'None'

        # 异常情况
        if not cresult.is_success():
            _dict['error'] = cresult.error
            _dict['trace_str'] = cresult.trace_str
            if cresult.code == '30403':
                _dict['api_info_type'] = 'OT'
            else:
                _dict['api_info_type'] = 'EX'

        _end_time = datetime.datetime.now()
        _dict['use'] = (_end_time - start_time).total_seconds()

        # 返回字典
        return _dict


class SimpleGRpcConnectionPool(ConnectionPoolFw):
    """
    Grpc客户端连接池
    """
    #############################
    # 需要具体类实现的函数
    #############################

    def _create_connection_self(self):
        """
        创建一个连接对象（具体类实现）

        @return {object} - 返回有效的连接对象

        @throws {Exception} - 当创建失败或连接无效时应直接抛出异常
        """
        return SimpleGRpcConnection(self.connect_para)

    def _close_connection_self(self, connection):
        """
        关闭指定的连接对象（具体类实现）

        @param {object} connection - 要关闭的连接对象

        @throws {Exception} - 当关闭失败时应直接抛出异常
        """
        connection.close()

    def _test_connection_self(self, connection):
        """
        测试指定的连接对象是否有效（具体类实现）

        @param {object} connection - 要测试的连接对象

        @throws {Exception} - 当测试失败时应抛出异常
        """
        _cresult = connection.test()
        if not _cresult.is_success():
            # 执行测试失败
            raise ConnectionError('Execute Error, code:%s, msg:%s, error:%s, trace_str:%s' % (
                _cresult.code, _cresult.msg, _cresult.error, _cresult.trace_str
            ))
        elif _cresult.status != msg_pb2.HealthResponse.SERVING:
            # 服务状态不为可用
            raise RuntimeError('GRPC Server Status Error: %s' % (_cresult.status))

    def _reconnect_self(self, connection):
        """
        对指定对象重新进行连接（具体类实现）

        @param {object} connection - 要重新连接的对象

        @return {object} - 返回有效的连接对象

        @throws {Exception} - 当重连失败时应抛出异常
        """
        _cresult = connection.reconnect()
        if not _cresult.is_success():
            # 执行测试失败
            raise ConnectionError('Connect Error, code:%s, msg:%s, error:%s, trace_str:%s' % (
                _cresult.code, _cresult.msg, _cresult.error, _cresult.trace_str
            ))
        elif _cresult.status != msg_pb2.HealthResponse.SERVING:
            # 服务状态不为可用
            raise RuntimeError('GRPC Server Status Error: %s' % (_cresult.status))


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    # 打印版本信息
    print(('模块名：%s  -  %s\n'
           '作者：%s\n'
           '发布日期：%s\n'
           '版本：%s' % (__MOUDLE__, __DESCRIPT__, __AUTHOR__, __PUBLISH__, __VERSION__)))

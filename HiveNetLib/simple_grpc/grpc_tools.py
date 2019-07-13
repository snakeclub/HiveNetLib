#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
#
# Copyright 2018 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
简单GRPC调用工具库

@module grpc_tools
@file grpc_tools.py
"""

import os
import sys
import grpc
from grpc_health.v1.health import HealthServicer
from grpc_health.v1 import health_pb2
from grpc_health.v1 import health_pb2_grpc
from concurrent import futures
import time
import json
import copy
import traceback
import datetime
import inspect
from enum import Enum
# 根据当前文件路径将包路径纳入，在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir, os.path.pardir)))
import HiveNetLib.simple_grpc.msg_pb2 as msg_pb2
import HiveNetLib.simple_grpc.msg_pb2_grpc as msg_pb2_grpc
from HiveNetLib.simple_log import EnumLogLevel
from HiveNetLib.generic import CResult, NullObj
from HiveNetLib.simple_server_fw import EnumServerRunStatus, SimpleServerFW
from HiveNetLib.base_tools.exception_tool import ExceptionTool
from HiveNetLib.base_tools.run_tool import RunTool
from HiveNetLib.simple_i18n import _
from HiveNetLib.base_tools.call_chain_tool import CallChainTool
from HiveNetLib.interface_tool.msg_json import MsgJSON
from HiveNetLib.base_tools.string_tool import StringTool

__MOUDLE__ = 'grpc_tools'  # 模块名
__DESCRIPT__ = u'简单GRPC调用工具库'  # 模块描述
__VERSION__ = '0.1.0'  # 版本
__AUTHOR__ = u'黎慧剑'  # 作者
__PUBLISH__ = '2019.06.30'  # 发布日期


class EnumCallMode(Enum):
    """
    调用模式
    @enum {string}
    """
    Simple = 'Simple'  # 简单模式
    ClientSideStream = 'ClientSideStream'  # 客户端流式
    ServerSideStream = 'ServerSideStream'  # 服务端流式
    BidirectionalStream = 'BidirectionalStream'  # 双向数据流模式


class EnumStreamEndTagType(Enum):
    """
    流结束标识类型
    @enum {string}
    """
    Count = 'Count'  # 采用计数方式判断结束（当total=current时结束）
    EndTag = 'EndTag'  # 判断结束标记


class SimpleGRpcTools(object):
    """
    SimpleGRpc的工具类，封装了一些公共工具函数
    """
    #############################
    # 公共函数
    #############################
    @staticmethod
    def generate_request_obj(
        service_name, para_json='', has_para_bytes=False, para_bytes=None,
        trace_id='', parent_id='', trace_level=1
    ):
        """
        创建rpc调用请求参数对象(Simple简单模式)

        @param {string} service_name - 要调用的服务名
        @param {string} para_json='' - 调用服务的参数JSON对象
        @param {bool} has_para_bytes=Fasle - 传入的参数是否有字节数组，当有字节数组时，
            参数值为字符格式且内容为占位字符'{$SIMPLEGRPC_BYTES$}'
        @param {bytes} para_bytes=None - 当传入参数有字节数组时，通过该字段传入数组信息
        @param {string} trace_id='' - 调用链追踪ID
        @param {string} parent_id='' - 调用链父调用函数的执行ID
        @param {int} trace_level=1 - 调用链调用层级，每CALL一个下级函数+1

        @returns {msg_pb2.RpcRequest} - 请求对象
        """
        return msg_pb2.RpcRequest(
            trace_id=trace_id, parent_id=parent_id, trace_level=trace_level,
            service_name=service_name, para_json=para_json,
            has_para_bytes=has_para_bytes, para_bytes=para_bytes
        )

    @staticmethod
    def generate_response_obj(
        return_json='', has_return_bytes=False, return_bytes=None,
        call_code='', call_msg='', call_error='', call_msg_para=()
    ):
        """
        创建rpc调用响应对象(Simple简单模式)

        @param {string} return_json='' - 函数执行返回的信息，JSON格式
        @param {bool} has_return_bytes=False - 用于判断返回值是否有字节数组，当有字节数组时，
            参数值为字符格式且内容为占位字符'{$SIMPLEGRPC_BYTES$}'
        @param {bytes} return_bytes=None - 当返回值有字节数组时，通过该字段传入数组信息
        @param {bool} call_code='' - 执行错误码:'00000'-成功,'11403'-服务名不存在,'21007'-执行抛出异常
        @param {string} call_msg='' - 执行错误信息
        @param {string} call_error='' - 执行抛出异常时，异常对象的类型
        @param {tuple} call_msg_para=() - 执行错误信息对应的参数，JSON格式，数组()

        @returns {msg_pb2.RpcResponse} - 响应对象
        """
        return msg_pb2.RpcResponse(
            return_json=return_json, has_return_bytes=has_return_bytes, return_bytes=return_bytes,
            call_code=call_code, call_msg=call_msg, call_error=call_error,
            call_msg_para=json.dumps(call_msg_para)
        )

    @staticmethod
    def response_obj_to_cresult(resp_obj, json_para_mapping_key=None, i18n_obj=None):
        """
        将RpcResponse对象转换为CResult对象(仅Simple简单模式)

        @param {msg_pb2.RpcResponse} resp_obj - 响应对象
        @param {string} json_para_mapping_key=None - json转换为object的参数映射关键字
        @param {<type>} i18n_obj=None - 国际化类的实例对象，该对象需实现translate方法

        @return {CResult} - 返回的CResult对象，带有函数调用返回值属性：
            return_json - 返回值的json字符串
            return_obj - 返回值对象
        """
        _result = CResult(
            code=resp_obj.call_code,
            msg=resp_obj.call_msg,
            error=resp_obj.call_error,
            i18n_obj=i18n_obj,
            i18n_msg_paras=StringTool.json_to_object(resp_obj.call_msg_para)
        )
        _result.return_json = resp_obj.return_json
        _result.has_return_bytes = resp_obj.has_return_bytes
        _result.return_bytes = resp_obj.return_bytes
        _json_para = (None, None)
        if json_para_mapping_key is not None:
            _json_para = SimpleGRpcTools.get_json_to_object_para_mapping(json_para_mapping_key)
        _result.return_obj = StringTool.json_to_object(
            _result.return_json,
            class_ref=_json_para[0],
            object_hook=_json_para[1]
        )
        return _result

    @staticmethod
    def parameters_to_json(para_list, is_support_bytes=False):
        """
        将参数列表转换为json字符串

        @param {list} para_list - 要转换的参数列表，list的每一项为一个参数项，每个参数项如下：
            [para_name, call_value] : para_name可以为''
        @param {bool} is_support_bytes=False - 是否支持参数中的字节数组传递（只支持最后一个参数）

        @returns {object} - 返回对象，格式如下：
            object.para_json : 返回的json字符串
            object.has_para_bytes : 传入的参数是否有字节数组
            object.para_bytes : 当传入参数有字节数组时，通过该字段传入数组信息
        """
        para_obj = NullObj()
        para_obj.para_json = ''
        para_obj.has_para_bytes = False
        para_obj.para_bytes = None
        # 遍历处理
        _pos = len(para_list) - 1
        _is_no_name = False
        _has_deal_bytes = False
        while _pos >= 0:
            # 从后向前遍历参数数组，将倒数第一个不指定参数名的参数前面的参数项的参数名都去掉
            # 避免调用函数出现问题
            if _is_no_name:
                para_list[_pos][0] = ''
            elif para_list[_pos][0] == '':
                _is_no_name = True
            # 处理bytes数组
            if is_support_bytes and not _has_deal_bytes and type(para_list[_pos][1]) == bytes:
                para_obj.has_para_bytes = True
                para_obj.para_bytes = para_list[_pos][1]
                para_list[_pos][1] = '{$SIMPLEGRPC_BYTES$}'
                _has_deal_bytes = True
            # 继续下一个
            _pos = _pos - 1
        # 处理返回值
        para_obj.para_json = json.dumps(para_list)
        return para_obj

    @staticmethod
    def object_to_json_support_bytes(obj, is_support_bytes=False):
        """
        对象转换为json（支持bytes的情况）
        注意：如果为存在对象属性是bytes的情况，只支持一个；此外只支持第一级属性的情况；
            如果对象为bytes格式，则json串为'{$SIMPLEGRPC_BYTES$}'转换的json串

        @param {object} obj - 要处理的对象
        @param {bool} is_support_bytes=False - 是否支持有bytes的情况

        @return {NullObj} - 返回的对象，属性如下：
            obj.return_json : 转换后的JSON格式字符串
            obj.has_return_bytes : 返回值是否有字节数组
            obj.return_bytes : 有字节数组时，通过该字段传入数组信息
        """
        _ret_obj = NullObj()
        _ret_obj.return_json = ''
        _ret_obj.has_return_bytes = False
        _ret_obj.return_bytes = None
        if is_support_bytes:
            # 支持字节形式，进行判断和处理
            _has_deal_bytes = False
            if type(obj) == bytes:
                _ret_obj.has_return_bytes = True
                _ret_obj.return_bytes = obj
                _ret_obj.return_json = StringTool.object_to_json('{$SIMPLEGRPC_BYTES$}')
                _has_deal_bytes = True
            elif type(obj) not in (
                int, float, bool, complex,
                str, list, tuple, dict, set
            ):
                # 不是基础类型，查找第一层的属性并进行转换
                _attr_dir = dir(obj)
                for _item in _attr_dir:
                    if _item[0: 2] != '__' and not callable(getattr(obj, _item)):
                        if type(getattr(obj, _item)) == bytes:
                            _ret_obj.has_return_bytes = True
                            _ret_obj.return_bytes = getattr(obj, _item)
                            _has_deal_bytes = True
                            _copyobj = copy.deepcopy(obj)
                            exec('_copyobj.%s = "{$SIMPLEGRPC_BYTES$}"' % (_item))
                            _ret_obj.return_json = StringTool.object_to_json(_copyobj)
                            break

        # 不支持字节形式，直接转换；或前面没有进行过处理
        if not _has_deal_bytes:
            _ret_obj.return_json = StringTool.object_to_json(obj)
        return _ret_obj

    @staticmethod
    def get_json_to_object_para_mapping(key):
        """
        获取json转换为对象的映射参数
        通过全局公共参数“SIMPLEGRPC_JSON_TO_OBJECT_PARA”获取

        @param {string} key - 关键字（建议直接使用函数名）

        @return {tuple} (class_ref, object_hook) - 转换参数
            调用StringTool.json_to_object的参数，如果找不到配置都是返回None
        """
        _json_to_object_para = RunTool.get_global_var('SIMPLEGRPC_JSON_TO_OBJECT_PARA')
        if _json_to_object_para is None or key not in _json_to_object_para.keys():
            return (None, None)
        else:
            _para = _json_to_object_para[key]
            return (_para[0], _para[1])

    @staticmethod
    def set_json_to_object_para_mapping(key, class_ref=None, object_hook=None):
        """
        设置json转换为对象的映射参数

        @param {string} key - 名称关键字（建议直接使用函数名）
        @param {class} class_ref=None - 类定义引用，例如generic.NullObj
            引用的类必须实现__fromjson__的静态函数，传入json字符串，返回对象实例
        @param {function} object_hook=None - 将json对象转换为所需实例类的函数
            函数入参为通过json标准库转换后的json对象，出参为转换后的对象实例
        """
        _json_to_object_para = RunTool.get_global_var('SIMPLEGRPC_JSON_TO_OBJECT_PARA')
        if _json_to_object_para is None:
            _json_to_object_para = dict()
            RunTool.set_global_var('SIMPLEGRPC_JSON_TO_OBJECT_PARA', _json_to_object_para)
        # 设置值
        _json_to_object_para[key] = (class_ref, object_hook)
        return

    #############################
    # 服务端工具
    #############################
    @staticmethod
    def generate_server_opts(
        ip='', port=50051, max_workers=1, max_connect=20,
        is_health_check=False, auto_service_when_started=True,
        is_use_ssl=False, private_key_certificate_chain_pairs=None, root_certificates=None,
        options=None, compression=None,
        handlers=None, interceptors=None
    ):
        """
        生成服务启动参数

        @param {string} ip='' - 监听的服务器ip
        @param {int} port=50051 - 监听的服务端口
        @param {int} max_workers=1 - 最大工作处理线程数
        @param {int} max_connect=20 - 允许最大连接数
        @param {bool} is_health_check=False - 是否启用健康检查服务
        @param {bool} auto_service_when_started=True - 是否启动后自动向外服务（健康检查为服务中状态）
        @param {bool} is_use_ssl=False - 是否使用SSL/TLS
        @param {list} private_key_certificate_chain_pairs=None - 证书私钥及证书链组合列表，使用SSL时必填
            ((private_key, certificate_chain),)  :  [PEM-encoded private key, PEM-encoded certificate chain]
             with open('server.pem', 'rb') as f:
                private_key = f.read()  # 服务器端的私钥文件
            with open('server.crt', 'rb') as f:
                certificate_chain = f.read()  # 服务器端的公钥证书文件
        @param {list} root_certificates=None - 客户端反向认证时（验证客户端证书）的客户端根证书，即客户端的公钥证书文件
            with open('ca.crt', 'rb') as f:
                root_certificates = f.read()
        @param {type?} options=None - An optional list of key-value pairs (channel args in gRPC runtime) to configure the channel
        @param {type?} compression=None - An element of grpc.compression, e.g. grpc.compression.Gzip. This compression algorithm will be used for the lifetime of the server unless overridden
        @param {type?} handlers=None - An optional list of GenericRpcHandlers used for executing RPCs. More handlers may be added by calling add_generic_rpc_handlers any time before the server is started
        @param {type?} interceptors=None - An optional list of ServerInterceptor objects that observe and optionally manipulate the incoming RPCs before handing them over to handlers. The interceptors are given control in the order they are specified

        @returns {object} - 返回带参数属性的对象，例如对象为ret：
           ret.ip = ''
           ...
        """
        _server_opts = NullObj()
        _server_opts.ip = ip  # 主机名或IP地址
        _server_opts.port = port  # 监听端口
        _server_opts.max_workers = max_workers  # 最大工作处理线程数
        _server_opts.max_connect = max_connect
        _server_opts.is_health_check = is_health_check
        _server_opts.auto_service_when_started = auto_service_when_started
        _server_opts.is_use_ssl = is_use_ssl  # 是否使用SSL/TLS
        _server_opts.private_key_certificate_chain_pairs = private_key_certificate_chain_pairs
        _server_opts.root_certificates = root_certificates
        _server_opts.options = options
        _server_opts.compression = compression
        _server_opts.handlers = handlers
        _server_opts.interceptors = interceptors
        return _server_opts

    @staticmethod
    def get_private_key_certificate_chain_pair(key_file, crt_file):
        """
        根据.key和.crt文件生成private_key_certificate_chain_pair

        @param {string} key_file - .key文件的路径(含文件名)，服务器端的私钥文件
        @param {string} crt_file - .crt文件的路径(含文件名)，服务器端的公钥证书文件，提供给客户端使用

        @return {(bytes, bytes)} - 对应签名证书的(private_key, certificate_chain)

        @example
            利用openssl创建自签名证书:
            1、命令行：openssl genrsa -out server.key 2048
               执行过程中输入各类证书信息
            2、生成了server.key和server.crt两个文件，服务端两个文件都需要，客户端只需要crt文件
            3、对于服务器端，server.key对应private_key，server.crt对应certificate_chain
            4、对于客户端，server.crt对应root_certificates
        """
        with open(key_file, 'rb') as f:
            _private_key = f.read()
        with open(crt_file, 'rb') as f:
            _certificate_chain = f.read()
        return _private_key, _certificate_chain

    #############################
    # 客户端工具
    #############################
    @staticmethod
    def generate_connect_para(
        ip='', port=50051, conn_str=None,
        is_use_ssl=False, root_certificates=None,
        private_key=None, certificate_chain=None,
        options=None, compression=None
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

        @returns {object} - 返回带参数属性的对象，例如对象为ret：
            ret.ip = ''
            ...

        """
        _connect_para = NullObj()
        _connect_para.ip = ip
        _connect_para.port = port
        _connect_para.conn_str = conn_str
        _connect_para.is_use_ssl = is_use_ssl  # 是否使用SSL/TLS
        _connect_para.private_key = private_key
        _connect_para.certificate_chain = certificate_chain
        _connect_para.root_certificates = root_certificates
        _connect_para.options = options
        _connect_para.compression = compression
        return _connect_para

    @staticmethod
    def generate_channel(connect_para):
        """
        生成gRPC通道，注意该通道需要后端主动关闭

        @param {object} connect_para - 客户端连接参数

        @return {grpc.Channel} - gRPC连接通道
        """
        _channel = None
        _server_host_str = None
        if connect_para.conn_str is None:
            _server_host_str = ('%s:%s' % (connect_para.ip, connect_para.port))
        else:
            _server_host_str = connect_para.conn_str
        if connect_para.is_use_ssl:
            # 使用SSL验证
            _credentials = grpc.ssl_channel_credentials(
                root_certificates=connect_para.root_certificates,
                private_key=connect_para.private_key,
                certificate_chain=connect_para.certificate_chain
            )
            _channel = grpc.secure_channel(
                _server_host_str, _credentials, options=connect_para.options,
                compression=connect_para.compression
            )
        else:
            # 不使用SSL验证
            _channel = grpc.insecure_channel(
                _server_host_str,
                options=connect_para.options, compression=connect_para.compression
            )
        return _channel

    @staticmethod
    def generate_call_stub(channel):
        """
        生成gRPC桩代码对象(stub code，可以理解为映射服务端的占坑代码)，

        @param {grpc.Channel} channel - gRPC连接通道

        @return {msg_pb2_grpc.SimpleGRpcServiceStub} - SimpleGRpc的桩代码对象
        """
        return msg_pb2_grpc.SimpleGRpcServiceStub(channel)

    @staticmethod
    def grpc_call_by_stub(stub, rpc_request, call_mode=EnumCallMode.Simple):
        """
        基于stub对象执行远程调用

        @param {msg_pb2_grpc.SimpleGRpcServiceStub} stub - 已连接的stub对象
        @param {msg_pb2.RpcRequest|request_iterator} rpc_request - 请求对象或产生请求对象的迭代器（iterator），应与call_mode匹配
        @param {EnumCallMode} call_mode=EnumCallMode.Simple - 调用服务端的模式

        @returns {msg_pb2.RpcResponse|response_iterator} - 响应对象或产生响应对象的迭代器（iterator），与call_mode匹配
            注意：如果执行出现远程调用异常，则返回对象的call_code为20408，
                且call_msg_para的第一个参数为grpc.StatusCode的name属性值
        """
        try:
            if call_mode == EnumCallMode.ServerSideStream:
                return stub.GRpcCallServerSideStream(rpc_request)
            elif call_mode == EnumCallMode.ClientSideStream:
                return stub.GRpcCallClientSideStream(rpc_request)
            elif call_mode == EnumCallMode.BidirectionalStream:
                return stub.GRpcCallBidirectionalStream(rpc_request)
            else:
                # 简单模式
                return stub.GRpcCallSimple(rpc_request)
        except grpc._channel._Rendezvous as grpc_err:
            # 执行远程调用出现异常
            _error_return_obj = SimpleGRpcTools.generate_response_obj(
                call_code='20408',
                call_msg=None,
                call_error=str(type(grpc_err)),
                call_msg_para=(grpc_err._state.code.name, grpc_err._state.details)
            )
            if call_mode in (EnumCallMode.Simple, EnumCallMode.ClientSideStream):
                return _error_return_obj
            else:
                # 返回流
                return SimpleGRpcTools._generate_iterator_object(_error_return_obj)

    @staticmethod
    def grpc_call_by_channel(channel, rpc_request, call_mode=EnumCallMode.Simple):
        """
        基于channel对象执行远程调用

        @param {grpc.Channel} channel - gRPC连接通道
        @param {msg_pb2.RpcRequest|request_iterator} rpc_request - 请求对象或产生请求对象的迭代器（iterator），应与call_mode匹配
        @param {EnumCallMode} call_mode=EnumCallMode.Simple - 调用服务端的模式

        @returns {msg_pb2.RpcResponse|response_iterator} - 响应对象或产生响应对象的迭代器（iterator），与call_mode匹配
        """
        return SimpleGRpcTools.grpc_call_by_stub(
            SimpleGRpcTools.generate_call_stub(channel),
            rpc_request,
            call_mode=call_mode
        )

    @staticmethod
    def grpc_call(connect_para, rpc_request, call_mode=EnumCallMode.Simple):
        """
        执行gRPC远程调用（自动创建channel并在完成后关闭）
        注意：该调用方式不适合ServerSideStream、BidirectionalStream两种模式（自动关闭channel会导致处理失败）

        @param {object} connect_para - 客户端连接参数
        @param {msg_pb2.RpcRequest|request_iterator} rpc_request - 请求对象或产生请求对象的迭代器（iterator），应与call_mode匹配
        @param {EnumCallMode} call_mode=EnumCallMode.Simple - 调用服务端的模式

        @returns {msg_pb2.RpcResponse} - 响应对象

        @throws {ValueError} - 当call_mode为ServerSideStream、BidirectionalStream时抛出
        """
        if call_mode in (EnumCallMode.ServerSideStream, EnumCallMode.BidirectionalStream):
            raise ValueError('unsupport call_mode')

        with SimpleGRpcTools.generate_channel(connect_para) as channel:
            return SimpleGRpcTools.grpc_call_by_channel(
                channel,
                rpc_request,
                call_mode=call_mode
            )

    @staticmethod
    def generate_health_check_stub(channel):
        """
        生成健康检查桩代码对象(stub code，可以理解为映射服务端的占坑代码)，

        @param {grpc.Channel} channel - gRPC连接通道

        @return {health_pb2_grpc.HealthStub} - 标准健康检查的桩代码对象
        """
        return health_pb2_grpc.HealthStub(channel)

    @staticmethod
    def health_check_by_stub(stub, servicer_name):
        """
        基于stub对象执行远程调用

        @param {health_pb2_grpc.HealthStub} stub - 已连接的stub对象
        @param {string} servicer_name - 要检查的服务名

        @returns {health_pb2.HealthCheckResponse.ServingStatus} - 检查结果，有以下几种状态
            health_pb2.HealthCheckResponse.UNKNOWN
            health_pb2.HealthCheckResponse.SERVICE_UNKNOWN
            health_pb2.HealthCheckResponse.NOT_SERVING
            health_pb2.HealthCheckResponse.SERVING
        """
        try:
            _request = health_pb2.HealthCheckRequest(service=servicer_name)
            _resp = stub.Check(_request)
            return _resp.status
        except:
            # 出现异常
            return health_pb2.HealthCheckResponse.UNKNOWN

    @staticmethod
    def health_check(connect_para, servicer_name):
        """
        执行健康检查

        @param {object} connect_para - 客户端连接参数
        @param {string} servicer_name - 要检查的服务名

        @returns {health_pb2.HealthCheckResponse.ServingStatus} - 检查结果，有以下几种状态
            health_pb2.HealthCheckResponse.UNKNOWN
            health_pb2.HealthCheckResponse.SERVICE_UNKNOWN
            health_pb2.HealthCheckResponse.NOT_SERVING
            health_pb2.HealthCheckResponse.SERVING
        """
        with SimpleGRpcTools.generate_channel(connect_para) as channel:
            return SimpleGRpcTools.health_check_by_stub(
                SimpleGRpcTools.generate_health_check_stub(channel),
                servicer_name
            )

    #############################
    # 内部函数
    #############################
    @staticmethod
    def _generate_iterator_object(obj):
        """
        生成迭代器对象

        @param {object} obj - 要转换为迭代器的对象

        @return {iterator} - 生成的迭代器对象
        """
        yield obj


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    # 打印版本信息
    print(('模块名：%s  -  %s\n'
           '作者：%s\n'
           '发布日期：%s\n'
           '版本：%s' % (__MOUDLE__, __DESCRIPT__, __AUTHOR__, __PUBLISH__, __VERSION__)))

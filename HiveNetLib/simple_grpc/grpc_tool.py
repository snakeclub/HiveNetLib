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
import json
import copy
import traceback
import logging
from enum import Enum
# 根据当前文件路径将包路径纳入，在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir, os.path.pardir)))
import HiveNetLib.deps_tool as deps_tool
process_install_grpc = False
while True:
    try:
        import grpc
        from grpc_health.v1 import health_pb2
        from grpc_health.v1 import health_pb2_grpc
        break
    except ImportError:
        if not process_install_grpc:
            deps_tool.install_package('grpcio')
            deps_tool.install_package('grpcio-health')
            process_install_grpc = True
            continue
        raise
# 自有模块引用
import HiveNetLib.simple_grpc.msg_pb2 as msg_pb2
import HiveNetLib.simple_grpc.msg_pb2_grpc as msg_pb2_grpc
from HiveNetLib.generic import CResult, NullObj
from HiveNetLib.base_tools.run_tool import RunTool
from HiveNetLib.base_tools.string_tool import StringTool
from HiveNetLib.base_tools.exception_tool import ExceptionTool
from HiveNetLib.base_tools.call_chain_tool import CallChainTool
from HiveNetLib.simple_log import QueueHandler, Logger


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


class SimpleGRpcTools(object):
    """
    SimpleGRpc的工具类，封装了一些公共工具函数
    """
    #############################
    # 公共函数
    #############################
    @staticmethod
    def generate_request_obj(
        service_name, para_json='[]', has_para_bytes=False, para_bytes=None,
        trace_id='', parent_id='', trace_level=1
    ):
        """
        创建rpc调用请求参数对象

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

    #############################
    # 响应对象格式转换
    #############################

    @staticmethod
    def generate_response_obj(
        return_json='', has_return_bytes=False, return_bytes=None,
        call_code='', call_msg='', call_error='', call_msg_para=()
    ):
        """
        创建rpc调用响应对象

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
            call_msg_para=json.dumps(call_msg_para, ensure_ascii=False)
        )

    @staticmethod
    def response_obj_to_cresult(resp_obj):
        """
        将RpcResponse对象转换为CResult对象

        @param {msg_pb2.RpcResponse} resp_obj - 响应对象

        @return {CResult} - 返回的CResult对象，带有函数调用返回值属性：
            return_json - 返回值的json字符串
            has_return_bytes - 是否有返回字节数组
            return_bytes - 返回的字节数组
        """
        _result = CResult(
            code=resp_obj.call_code,
            msg=resp_obj.call_msg,
            error=resp_obj.call_error,
            i18n_obj=None,
            i18n_msg_paras=StringTool.json_to_object(resp_obj.call_msg_para)
        )
        _result.return_json = resp_obj.return_json
        _result.has_return_bytes = resp_obj.has_return_bytes
        _result.return_bytes = resp_obj.return_bytes
        return _result

    @staticmethod
    def response_iterator_to_cresults(resp_iterator):
        """
        将RpcResponsed的iterator对象转换为CResult的iterator对象

        @param {iterator} resp_iterator - 响应报文RpcResponse的iterator对象

        @return {iterator} - CResult的iterator对象
        """
        for resp_obj in resp_iterator:
            yield SimpleGRpcTools.response_obj_to_cresult(resp_obj)

    @classmethod
    def return_json_to_obj(cls, cresult: CResult, json_para_mapping_key: str = None,
                           deal_return_bytes: bool = False, bytes_location: list = None):
        """
        将CResult中的return_json转换为return_obj

        @param {CResult} cresult - gRPC返回的CResult对象
        @param {string} json_para_mapping_key - 通过 set_json_to_object_para_mapping 设置的特定python对象转换方法的key
        @param {bool} deal_return_bytes=False - 是否处理字节对象
        @param {list} bytes_location=None - 根据传入的数组查找bytes位置并替换，根据数组传入的值区分查找路径：
            str - 当前位置为字典，传入的是key值
            int - 当前位置为数组，传入的是所在数组的位置（0开始）
            如果不指定，则根据list和key遍历方式查找替换（只处理第1层）

        @return {CResult} - 包含转换后return_obj的CResult对象
        """
        # json转换为obj
        _cresult = cresult
        _cresult.return_obj = cls.json_to_object_by_para_mapping(
            _cresult.return_json, json_para_mapping_key
        )

        # 字节对象处理
        if deal_return_bytes and _cresult.has_return_bytes:
            _match_str = '{$SIMPLEGRPC_BYTES$}'
            _is_ok = False
            if bytes_location is None:
                # 遍历方式查找
                if type(_cresult.return_obj) == list:
                    for _i in range(len(_cresult.return_obj)):
                        if _cresult.return_obj[_i] == _match_str:
                            _cresult.return_obj[_i] = _cresult.return_bytes
                            _is_ok = True
                            break
                elif type(_cresult.return_obj) == dict:
                    for _key in _cresult.return_obj.keys():
                        if _cresult.return_obj[_key] == _match_str:
                            _cresult.return_obj[_key] = _cresult.return_bytes
                            _is_ok = True
                            break
            else:
                # 通过指定位置查找
                _current = _cresult.return_obj
                for _location in bytes_location:
                    _current = _cresult.return_obj[_location]

                if _current == _match_str:
                    _current = _cresult.return_bytes
                    _is_ok = True

            # 检查是否找到
            if not _is_ok:
                raise AttributeError('var with bytes not found in return obj')

        return cresult

    #############################
    # JSON转换
    #############################

    @staticmethod
    def parameters_to_json(para_list, is_support_bytes=False):
        """
        将参数列表转换为json字符串对象

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
        para_obj.para_json = json.dumps(para_list, ensure_ascii=False)
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
        _obj_type = type(obj)  # 对象类型
        if is_support_bytes:
            # 支持字节形式，进行判断和处理
            _has_deal_bytes = False
            if type(obj) == bytes:
                _ret_obj.has_return_bytes = True
                _ret_obj.return_bytes = obj
                _ret_obj.return_json = StringTool.object_to_json('{$SIMPLEGRPC_BYTES$}')
                _has_deal_bytes = True
            elif _obj_type in (list, tuple):
                # 处理列表类型
                for _i in range(len(obj)):
                    if type(obj[_i]) == bytes:
                        # 找到字节数组，需要处理
                        _has_deal_bytes = True
                        _ret_obj.has_return_bytes = True
                        _ret_obj.return_bytes = obj[_i]
                        _copyobj = copy.deepcopy(obj)
                        _copyobj = list(_copyobj)
                        _copyobj[_i] = "{$SIMPLEGRPC_BYTES$}"
                        if _obj_type == tuple:
                            _copyobj = tuple(_copyobj)
                        _ret_obj.return_json = StringTool.object_to_json(_copyobj)
                        break
            elif _obj_type == dict:
                # 处理字典类型
                for _key in obj.keys():
                    if type(obj[_key]) == bytes:
                        # 找到字节数组，需要处理
                        _has_deal_bytes = True
                        _ret_obj.has_return_bytes = True
                        _ret_obj.return_bytes = obj[_key]
                        _copyobj = copy.deepcopy(obj)
                        _copyobj[_key] = "{$SIMPLEGRPC_BYTES$}"
                        _ret_obj.return_json = StringTool.object_to_json(_copyobj)
                        break
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

    @staticmethod
    def json_to_object_by_para_mapping(json_str, json_para_mapping_key):
        """
        通过json_para_mapping_key获取到的转换参数，将json字符转换为对象

        @param {string} json_str - 要转换的json字符
        @param {string} json_para_mapping_key - 关键字（一般使用函数名，通过全局公共参数“SIMPLEGRPC_JSON_TO_OBJECT_PARA”获取）

        @return {object} - 转换后的对象
        """
        _json_para = (None, None)
        if json_para_mapping_key is not None:
            _json_para = SimpleGRpcTools.get_json_to_object_para_mapping(json_para_mapping_key)

        return StringTool.json_to_object(
            json_str,
            class_ref=_json_para[0],
            object_hook=_json_para[1]
        )

    #############################
    # 服务端工具
    #############################
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
            [('grpc.max_send_message_length', 最大发送消息长度), ('grpc.max_receive_message_length', 最大接收消息长度)]
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
    def grpc_call_by_stub(stub, rpc_request, call_mode=EnumCallMode.Simple,
                          timeout=None, metadata=None, credentials=None,
                          wait_for_ready=None, compression=None):
        """
        基于stub对象执行远程调用

        @param {msg_pb2_grpc.SimpleGRpcServiceStub} stub - 已连接的stub对象
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
        _is_iterator = False
        try:
            _resp_obj = None
            if call_mode == EnumCallMode.ServerSideStream:
                _is_iterator = True
                _resp_obj = stub.GRpcCallServerSideStream(
                    rpc_request, timeout=timeout, metadata=metadata, credentials=credentials,
                    wait_for_ready=wait_for_ready, compression=compression
                )
            elif call_mode == EnumCallMode.ClientSideStream:
                _resp_obj = stub.GRpcCallClientSideStream(
                    rpc_request, timeout=timeout, metadata=metadata, credentials=credentials,
                    wait_for_ready=wait_for_ready, compression=compression
                )
            elif call_mode == EnumCallMode.BidirectionalStream:
                _is_iterator = True
                _resp_obj = stub.GRpcCallBidirectionalStream(
                    rpc_request, timeout=timeout, metadata=metadata, credentials=credentials,
                    wait_for_ready=wait_for_ready, compression=compression
                )
            else:
                # 简单模式
                _resp_obj = stub.GRpcCallSimple(
                    rpc_request, timeout=timeout, metadata=metadata, credentials=credentials,
                    wait_for_ready=wait_for_ready, compression=compression
                )

            # 针对响应值进行处理并返回
            if _is_iterator:
                # 返回序列
                return SimpleGRpcTools.response_iterator_to_cresults(_resp_obj)
            else:
                # 返回单个对象
                return SimpleGRpcTools.response_obj_to_cresult(_resp_obj)

        except (grpc._channel._Rendezvous, grpc._channel._InactiveRpcError):
            # 执行远程调用出现异常
            _code = '20408'
            _grpc_err = sys.exc_info()[1]
            if _grpc_err._state.code.value[0] == 4:
                # 调用超时
                _code = '30403'
            _result = CResult(
                code=_code,
                error=str(type(_grpc_err)),
                trace_str=traceback.format_exc(),
                i18n_msg_paras=(_grpc_err._state.code.name, _grpc_err._state.details)
            )
        except:
            _error = str(sys.exc_info()[0])
            _result = CResult(
                code='21007',
                error=_error,
                trace_str=traceback.format_exc(),
                i18n_msg_paras=(_error)
            )
        # 异常情况的返回处理
        _result.return_json = ''
        _result.has_return_bytes = False
        _result.return_bytes = b''
        if _is_iterator:
            return SimpleGRpcTools._generate_iterator_object(_result)
        else:
            return _result

    @staticmethod
    def grpc_call_by_channel(channel, rpc_request, call_mode=EnumCallMode.Simple,
                             timeout=None, metadata=None, credentials=None,
                             wait_for_ready=None, compression=None):
        """
        基于channel对象执行远程调用

        @param {grpc.Channel} channel - gRPC连接通道
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
        return SimpleGRpcTools.grpc_call_by_stub(
            SimpleGRpcTools.generate_call_stub(channel),
            rpc_request,
            call_mode=call_mode,
            timeout=timeout, metadata=metadata, credentials=credentials,
            wait_for_ready=wait_for_ready, compression=compression
        )

    @staticmethod
    def grpc_call(connect_para, rpc_request, call_mode=EnumCallMode.Simple,
                  timeout=None, metadata=None, credentials=None,
                  wait_for_ready=None, compression=None):
        """
        执行gRPC远程调用（自动创建channel并在完成后关闭）
        注意：该调用方式不适合ServerSideStream、BidirectionalStream两种模式（自动关闭channel会导致处理失败）

        @param {object} connect_para - 客户端连接参数
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

        @throws {ValueError} - 当call_mode为ServerSideStream、BidirectionalStream时抛出
        """
        if call_mode in (EnumCallMode.ServerSideStream, EnumCallMode.BidirectionalStream):
            raise ValueError('unsupport call_mode')

        with SimpleGRpcTools.generate_channel(connect_para) as channel:
            return SimpleGRpcTools.grpc_call_by_channel(
                channel,
                rpc_request,
                call_mode=call_mode,
                timeout=timeout, metadata=metadata, credentials=credentials,
                wait_for_ready=wait_for_ready, compression=compression
            )

    #############################
    # 自定义的健康检查
    #############################
    @staticmethod
    def simple_grpc_health_check_by_stub(stub, timeout=None):
        """
        SimpleGRpc自定义的健康检查，访问健康检查服务

        @param {msg_pb2_grpc.SimpleGRpcServiceStub} stub - 已连接的stub对象
        @param {number} timeout=None - 超时时间，单位为秒

        @returns {CResult} - 响应对象，判断成功的方法：
            ret.status == msg_pb2.HealthResponse.SERVING
            总共有以下几种状态
            health_pb2.HealthResponse.UNKNOWN
            health_pb2.HealthResponse.SERVICE_UNKNOWN
            health_pb2.HealthResponse.NOT_SERVING
            health_pb2.HealthResponse.SERVING
        """
        _result = CResult(code='00000')
        _result.status = msg_pb2.HealthResponse.UNKNOWN
        try:
            _result = CResult(code='00000')
            _resp_obj = stub.GRpcCallHealthCheck(
                msg_pb2.HealthRequest(service=''),
                timeout=timeout
            )
            _result.status = _resp_obj.status
        except grpc._channel._Rendezvous as grpc_err:
            # 执行远程调用出现异常
            _code = '20408'
            if grpc_err._state.code.value[0] == 4:
                # 调用超时
                _code = '30403'
            _result = CResult(
                code=_code,
                error=str(type(grpc_err)),
                trace_str=traceback.format_exc(),
                i18n_msg_paras=(grpc_err._state.code.name, grpc_err._state.details)
            )
            _result.status = msg_pb2.HealthResponse.UNKNOWN
        except:
            _error = str(sys.exc_info()[0])
            _result = CResult(
                code='21007',
                error=_error,
                trace_str=traceback.format_exc(),
                i18n_msg_paras=(_error)
            )
            _result.status = msg_pb2.HealthResponse.UNKNOWN
        # 返回处理结果
        return _result

    @staticmethod
    def simple_grpc_health_check(connect_para, timeout=None):
        """
        执行SimpleGRpc自定义的健康检查

        @param {object} connect_para - 客户端连接参数
        @param {number} timeout=None - 超时时间，单位为秒

        @returns {CResult} - 响应对象，判断成功的方法：
            ret.status == msg_pb2.HealthResponse.SERVING
            总共有以下几种状态
            health_pb2.HealthResponse.UNKNOWN
            health_pb2.HealthResponse.SERVICE_UNKNOWN
            health_pb2.HealthResponse.NOT_SERVING
            health_pb2.HealthResponse.SERVING
        """
        with SimpleGRpcTools.generate_channel(connect_para) as channel:
            return SimpleGRpcTools.simple_grpc_health_check_by_stub(
                SimpleGRpcTools.generate_call_stub(channel),
                timeout=timeout
            )

    #############################
    # 标准grpc的健康检查
    #############################
    @staticmethod
    def generate_health_check_stub(channel):
        """
        生成gRPC标准的服务健康检查桩代码对象(stub code，可以理解为映射服务端的占坑代码)，

        @param {grpc.Channel} channel - gRPC连接通道

        @return {health_pb2_grpc.HealthStub} - 标准健康检查的桩代码对象
        """
        return health_pb2_grpc.HealthStub(channel)

    @staticmethod
    def health_check_by_stub(stub, servicer_name, timeout=None):
        """
        基于stub对象gRPC标准的服务健康检查

        @param {health_pb2_grpc.HealthStub} stub - 已连接的stub对象
        @param {string} servicer_name - 要检查的服务名
        @param {number} timeout=None - 超时时间，单位为秒

        @returns {CResult} - 响应对象，判断成功的方法：
            ret.status == msg_pb2.HealthCheckResponse.SERVING
            总共有以下几种状态
            health_pb2.HealthCheckResponse.UNKNOWN
            health_pb2.HealthCheckResponse.SERVICE_UNKNOWN
            health_pb2.HealthCheckResponse.NOT_SERVING
            health_pb2.HealthCheckResponse.SERVING
        """
        _result = CResult(code='00000')
        _result.status = msg_pb2.HealthResponse.UNKNOWN
        try:
            _result = CResult(code='00000')
            _resp_obj = stub.Check(
                health_pb2.HealthCheckRequest(service=servicer_name),
                timeout=timeout
            )
            _result.status = _resp_obj.status
        except grpc._channel._Rendezvous as grpc_err:
            # 执行远程调用出现异常
            _code = '20408'
            if grpc_err._state.code.value[0] == 4:
                # 调用超时
                _code = '30403'
            _result = CResult(
                code=_code,
                msg='call grpc error: [status]$1, [details]$2',
                error=str(type(grpc_err)),
                trace_str=traceback.format_exc(),
                i18n_msg_paras=(grpc_err._state.code.name, grpc_err._state.details)
            )
            _result.status = health_pb2.HealthCheckResponse.UNKNOWN
        except:
            _error = str(sys.exc_info()[0])
            _result = CResult(
                code='21007',
                msg='call grpc error',
                error=_error,
                trace_str=traceback.format_exc(),
                i18n_msg_paras=(_error)
            )
            _result.status = health_pb2.HealthCheckResponse.UNKNOWN
        # 返回处理结果
        return _result

    @staticmethod
    def health_check(connect_para, servicer_name, timeout=None):
        """
        执行gRPC标准的服务健康检查

        @param {object} connect_para - 客户端连接参数
        @param {string} servicer_name - 要检查的服务名
        @param {number} timeout=None - 超时时间，单位为秒

        @returns {CResult} - 响应对象，判断成功的方法：
            ret.status == msg_pb2.HealthCheckResponse.SERVING
            总共有以下几种状态
            health_pb2.HealthCheckResponse.UNKNOWN
            health_pb2.HealthCheckResponse.SERVICE_UNKNOWN
            health_pb2.HealthCheckResponse.NOT_SERVING
            health_pb2.HealthCheckResponse.SERVING
        """
        with SimpleGRpcTools.generate_channel(connect_para) as channel:
            return SimpleGRpcTools.health_check_by_stub(
                SimpleGRpcTools.generate_health_check_stub(channel),
                servicer_name,
                timeout=timeout
            )

    #############################
    # 调用链日志处理
    #############################
    @staticmethod
    def write_api_call_chain_log(logger, info_dict):
        """
        记录调用链日志

        @param {simple_log.Logger} logger - 调用链异步日志对象
            注：CallChainTool.create_call_chain_logger产生的日志对象
        @param {dict} info_dict - 信息字典，可传入的接口信息格式如下：
            api_call_type - 接口调用类型
            api_info_type - 接口信息类型
            call_mode - 调用模式
            service_name - 要调用的服务名
            log_level - 打印日志的级别
            call_fun_level - 登记日志时需要记录的实际函数所处层级
            logging_para - dict - 日志参数字典
            para_json - 参数JSON字符串（如果是返回则填入return_json）
            para_bytes - 参数的bytes转换为字符串（如果是返回则填入return_bytes）
            para_bytes_len - 参数的bytes的长度（如果是返回则填入return_bytes_len）
            c-ip - 客户端IP
            c-port - 客户端端口
            s-ip - 服务端IP
            s-port - 服务端端口

            use - 接口执行耗时
            error - 异常对象
            trace_str - 异常堆栈信息

            trace_id - request.trace_id - 调用链追踪ID
            parent_id - request.parent_id - 上一函数的执行ID
            trace_level - request.trace_level - 函数调用层级
            call_id - 当前函数的执行id
        """
        if logger is None:
            return

        # 深复制，避免影响后面的对象
        _info_dict = copy.deepcopy(info_dict)
        if hasattr(logger, '_asyn_base_logger') or hasattr(logger, '_asyn_deal_msg_fun'):
            # 使用了异步日志
            CallChainTool.call_chain_asyn_log(
                logger, _info_dict['log_level'], '',
                extra={
                    'info_dict': _info_dict,
                    'callFunLevel': _info_dict['call_fun_level']
                }
            )
        else:
            # 同步日志处理
            SimpleGRpcTools.call_chain_logging(logger, _info_dict)

    @staticmethod
    def call_chain_logging(logger, info_dict):
        """
        记录调用链日志

        @param {HiveNetLib.simple_log.Logger} logger - 要写日志的日志对象
        @param {dict} info_dict - 信息字典
        """
        with ExceptionTool.ignored_all(
                logger=logger, self_log_msg=info_dict['err_log_msg']
        ):
            _msg = None
            _logging_para = SimpleGRpcTools._get_logging_para_value(info_dict)
            _msg = _logging_para['msg_class'](info_dict['para_json'])

            # 记录日志
            CallChainTool.api_call_chain_logging(
                msg=_msg, proto_msg=None, logger=logger,
                api_mapping=_logging_para['api_mapping'],
                api_call_type=info_dict['api_call_type'], api_info_type=info_dict['api_info_type'],
                trace_id=info_dict['trace_id'], trace_level=info_dict['trace_level'],
                call_id=info_dict['call_id'], parent_id=info_dict['parent_id'],
                logging_head=_logging_para['logging_head'],
                is_print_msg=_logging_para['is_print_msg'],
                msg_print_kwargs=_logging_para['msg_print_kwargs'],
                key_para=_logging_para['key_para'],
                print_in_para=_logging_para['print_in_para'],
                use=info_dict['use'], error=info_dict['error'], trace_str=info_dict['trace_str'],
                log_level=info_dict['log_level'],
                call_fun_level=info_dict['call_fun_level']
            )

    @staticmethod
    def api_call_chain_asyn_deal_msg_fun(topic_name, record):
        """
        将日志record对象中的日志内容部分处理为msg并返回（dict_info字典）

        @param {string} topic_name - 日志主题
        @param {object} record - 日志信息对象

        @return {string} - 处理后的msg
        """
        if hasattr(record, 'info_dict'):
            # 获取信息字典，进行格式化处理
            info_dict = record.info_dict
            _msg = None
            _logging_para = SimpleGRpcTools._get_logging_para_value(info_dict)
            if _logging_para['msg_class'] is not None:
                _msg = _logging_para['msg_class'](info_dict['para_json'])
            # 返回内容
            return CallChainTool.api_call_chain_log_str(
                msg=_msg, proto_msg=None,
                api_mapping=_logging_para['api_mapping'],
                api_call_type=info_dict['api_call_type'], api_info_type=info_dict['api_info_type'],
                trace_id=info_dict['trace_id'], trace_level=info_dict['trace_level'],
                call_id=info_dict['call_id'], parent_id=info_dict['parent_id'],
                logging_head=_logging_para['logging_head'],
                is_print_msg=_logging_para['is_print_msg'],
                msg_print_kwargs=_logging_para['msg_print_kwargs'],
                key_para=_logging_para['key_para'],
                print_in_para=_logging_para['print_in_para'],
                use=info_dict['use'], error=info_dict['error'], trace_str=info_dict['trace_str']
            )
        else:
            # 直接原样返回即可
            return record.msg

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

    @staticmethod
    def _update_logging_head_value(info_dict, logging_para):
        """
        更新打印日志参数的logging_head的值

        @param {dict} info_dict - 信息字典
        @param {dict} logging_para - 要修改的日志参数
        """
        _logging_head = logging_para['logging_head'].copy()
        for _key in _logging_head.keys():
            if _key == 'C-IP':
                _logging_head[_key] = info_dict['c-ip']
            elif _key == 'C-PORT':
                _logging_head[_key] = info_dict['c-port']
            elif _key == 'S-IP':
                _logging_head[_key] = info_dict['s-ip']
            elif _key == 'S-PORT':
                _logging_head[_key] = info_dict['s-port']
            elif _key == 'CALL_MODE':
                _logging_head[_key] = info_dict['call_mode']
            elif _key == 'SERVICE_NAME':
                _logging_head[_key] = info_dict['service_name']
            elif _key == 'PARA_BYTES':
                _logging_head[_key] = info_dict['para_bytes']
            elif _key == 'PARA_BYTES_LEN':
                _logging_head[_key] = info_dict['para_bytes_len']

        # 返回结果
        logging_para['logging_head'] = _logging_head

    @staticmethod
    def _get_logging_para_value(info_dict):
        """
        获取日志打印参数及相应值

        @param {dict} info_dict - 信息字典

        @return {dict} - 带值的打印日志参数字典
        """
        _logging_para = info_dict['logging_para'].copy()

        # 更新logging_head
        SimpleGRpcTools._update_logging_head_value(info_dict, _logging_para)

        # 返回打印日志参数字典
        return _logging_para


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    # 打印版本信息
    print(('模块名：%s  -  %s\n'
           '作者：%s\n'
           '发布日期：%s\n'
           '版本：%s' % (__MOUDLE__, __DESCRIPT__, __AUTHOR__, __PUBLISH__, __VERSION__)))

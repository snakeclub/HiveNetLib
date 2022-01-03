#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
#
# Copyright 2018 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
gRPC服务应用
@module grpc_server
@file grpc_server.py
@see https://grpc.github.io/grpc/python/index.html
@see consul https://www.cnblogs.com/yuzhenjie/p/9398569.html https://pypi.org/project/python-consul/ https://segmentfault.com/a/1190000018424798?utm_source=tag-newest
@see 流模式 https://segmentfault.com/a/1190000017952111
@requires grpcio &
@summary
    依赖grpcio，安装方法：pip install grpcio

"""
import os
import sys
from concurrent import futures
import json
import traceback
import datetime
import threading
import logging
import copy
# 根据当前文件路径将包路径纳入，在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir, os.path.pardir)))
# 动态添加包安装
import HiveNetLib.deps_tool as deps_tool
process_install_grpc = False
while True:
    try:
        import grpc
        from grpc_health.v1.health import HealthServicer
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
import HiveNetLib.simple_grpc.msg_pb2_grpc as msg_pb2_grpc
import HiveNetLib.simple_grpc.msg_pb2 as msg_pb2
from HiveNetLib.simple_grpc.grpc_tool import EnumCallMode, SimpleGRpcTools
from HiveNetLib.generic import CResult, NullObj
from HiveNetLib.simple_server_fw import SimpleServerFW
from HiveNetLib.base_tools.exception_tool import ExceptionTool
from HiveNetLib.base_tools.run_tool import RunTool
from HiveNetLib.simple_i18n import _
from HiveNetLib.base_tools.call_chain_tool import CallChainTool
from HiveNetLib.interface_tool.msg_json import MsgJSON
from HiveNetLib.simple_log import QueueHandler, Logger


__MOUDLE__ = 'grpc_server'  # 模块名
__DESCRIPT__ = u'gRPC服务应用'  # 模块描述
__VERSION__ = '0.1.0'  # 版本
__AUTHOR__ = u'黎慧剑'  # 作者
__PUBLISH__ = '2019.05.24'  # 发布日期


class SimpleGRpcServicer(msg_pb2_grpc.SimpleGRpcServiceServicer):
    """
    重载msg_pb2_grpc.SimpleGRpcServicer服务，修改服务端的通用处理方法

    """
    #############################
    # 内部变量
    #############################
    # 可执行服务列表，分别对应GRpcCall、...
    # 统一格式，key为服务名，value为数组[fun_obj, recv_logging_para, resp_logging_para]
    # fun_obj - 可执行函数对象
    # recv_logging_para 和 resp_logging_para分别是接受报文和返回报文的打印参数，为字典，格式为
    # {"api_mapping": {}, "logging_head": {}, "is_print_msg": bool, "msg_print_kwargs": {}, "key_para" :{}, "print_in_para": {}}
    # 说明如下：
    # api_mapping - 定义从报文中获取logging_head所需的信息，具体格式和定义参见CallChainTool.api_call_chain_logging的参数说明
    # logging_head - 定义打印的日志规范头信息，具体格式和定义参见CallChainTool.api_call_chain_logging的参数说明
    # is_print_msg - 是否打印报文内容
    # msg_print_kwargs - MsgFW对象（统一为MsgJSON）的msg.to_str()函数的传入参数
    # key_para - 要打印的关键业务参数，具体格式和定义参见CallChainTool.api_call_chain_logging的参数说明
    # print_in_para - 要打印的指定接口字段，具体格式和定义参见CallChainTool.api_call_chain_logging的参数说明
    _simple_service_list = None  # 简单调用的可执行的服务列表（动态添加），key为服务名，value为函数对象
    _client_side_stream_service_list = None  # 客户端流式的可执行的服务列表
    _server_side_stream_service_list = None  # 服务端流式的可执行的服务列表
    _bidirectional_stream_service_list = None  # 双向数据流模式的可执行的服务列表

    _dealing_num = 0  # 当前正在处理的报文数
    _dealing_num_lock = None  # 为保证缓存信息的一致性，需要控制的锁

    _logger = None  # 日志对象
    _log_level = logging.INFO  # 日志打印级别
    # 默认的logging打印参数
    _default_logging_para = None

    _idpool = None  # 获取id的资源池
    _get_id_overtime = 0  # 超时时间
    _init_kwargs = None  # 构造函数对应的动态参数

    #############################
    # 构造函数
    #############################
    def __init__(self, logger=None, log_level=logging.INFO, is_use_global_logger=True,
                 idpool=None, get_id_overtime=0,
                 **kwargs):
        """
        构造函数

        @param {simple_log.Logger} logger=None - 日志对象，如果为None代表不需要输出日志
        @param {int} log_level=logging.INFO - 打印日志的级别
        @param {bool} is_use_global_logger=True - 当logger=None时，是否使用全局logger对象
            注：通过RunTool.set_global_logger进行设置
        @param {HiveNetLib.IdPool} idpool=None - 获取id的资源池，如果传入None代表直接通过uuid生成id
        @param {number} get_id_overtime=0 - 超时时间，单位为秒，如果需要一直不超时送入0
        @param {kwargs}  - 动态参数，已定义的参数如下：
            id的资源池的get_id传入参数
        """
        # 内部变量初始化
        self._simple_service_list = dict()  # 简单调用的可执行的服务列表（动态添加），key为服务名，value为函数对象
        self._client_side_stream_service_list = dict()  # 客户端流式的可执行的服务列表
        self._server_side_stream_service_list = dict()  # 服务端流式的可执行的服务列表
        self._bidirectional_stream_service_list = dict()  # 双向数据流模式的可执行的服务列表
        self._dealing_num_lock = threading.RLock()  # 为保证缓存信息的一致性，需要控制的锁

        # 默认的logging打印参数
        self._default_logging_para = {
            EnumCallMode.Simple: {
                'RECV': {
                    'msg_class': MsgJSON,
                    'api_mapping': {},
                    'logging_head': {
                        'S-IP': '',
                        'S-PORT': '',
                        'C-IP': '',
                        'C-PORT': '',
                        'CALL_MODE': '',
                        'SERVICE_NAME': '',
                        'PARA_BYTES_LEN': '',
                    },
                    'is_print_msg': True,
                    'msg_print_kwargs': {},
                    'key_para': {},
                    'print_in_para': {}
                },
                'RESP': {
                    'msg_class': MsgJSON,
                    'api_mapping': {},
                    'logging_head': {
                        'C-IP': '',
                        'C-PORT': '',
                        'CALL_MODE': '',
                        'SERVICE_NAME': '',
                        'PARA_BYTES_LEN': '',
                    },
                    'is_print_msg': True,
                    'msg_print_kwargs': {},
                    'key_para': {},
                    'print_in_para': {}
                }
            },
            EnumCallMode.ClientSideStream: {
                'RECV': {
                    'msg_class': MsgJSON,
                    'api_mapping': {},
                    'logging_head': {
                        'S-IP': '',
                        'S-PORT': '',
                        'C-IP': '',
                        'C-PORT': '',
                        'CALL_MODE': '',
                        'SERVICE_NAME': '',
                        'PARA_BYTES_LEN': '',
                    },
                    'is_print_msg': True,
                    'msg_print_kwargs': {},
                    'key_para': {},
                    'print_in_para': {}
                },
                'RESP': {
                    'msg_class': MsgJSON,
                    'api_mapping': {},
                    'logging_head': {
                        'C-IP': '',
                        'C-PORT': '',
                        'CALL_MODE': '',
                        'SERVICE_NAME': '',
                        'PARA_BYTES_LEN': '',
                    },
                    'is_print_msg': True,
                    'msg_print_kwargs': {},
                    'key_para': {},
                    'print_in_para': {}
                }
            },
            EnumCallMode.ServerSideStream: {
                'RECV': {
                    'msg_class': MsgJSON,
                    'api_mapping': {},
                    'logging_head': {
                        'S-IP': '',
                        'S-PORT': '',
                        'C-IP': '',
                        'C-PORT': '',
                        'CALL_MODE': '',
                        'SERVICE_NAME': '',
                        'PARA_BYTES_LEN': '',
                    },
                    'is_print_msg': True,
                    'msg_print_kwargs': {},
                    'key_para': {},
                    'print_in_para': {}
                },
                'RESP': {
                    'msg_class': MsgJSON,
                    'api_mapping': {},
                    'logging_head': {
                        'C-IP': '',
                        'C-PORT': '',
                        'CALL_MODE': '',
                        'SERVICE_NAME': '',
                        'PARA_BYTES_LEN': '',
                    },
                    'is_print_msg': True,
                    'msg_print_kwargs': {},
                    'key_para': {},
                    'print_in_para': {}
                }
            },
            EnumCallMode.BidirectionalStream: {
                'RECV': {
                    'msg_class': MsgJSON,
                    'api_mapping': {},
                    'logging_head': {
                        'S-IP': '',
                        'S-PORT': '',
                        'C-IP': '',
                        'C-PORT': '',
                        'CALL_MODE': '',
                        'SERVICE_NAME': '',
                        'PARA_BYTES_LEN': '',
                    },
                    'is_print_msg': True,
                    'msg_print_kwargs': {},
                    'key_para': {},
                    'print_in_para': {}
                },
                'RESP': {
                    'msg_class': MsgJSON,
                    'api_mapping': {},
                    'logging_head': {
                        'C-IP': '',
                        'C-PORT': '',
                        'CALL_MODE': '',
                        'SERVICE_NAME': '',
                        'PARA_BYTES_LEN': '',
                    },
                    'is_print_msg': True,
                    'msg_print_kwargs': {},
                    'key_para': {},
                    'print_in_para': {}
                }
            }
        }

        # 调用链ID产生信息
        self._idpool = idpool
        self._get_id_overtime = get_id_overtime
        self._init_kwargs = kwargs

        # 初始化日志信息
        self._logger = logger
        self._log_level = log_level
        if logger is None and is_use_global_logger:
            # 使用全局logger
            self._logger = RunTool.get_global_logger()

    #############################
    # 静态函数
    #############################
    def generate_logging_para(self, call_mode, api_type, init_para={}):
        """
        根据初始化参数生成完整的日志处理参数（没有传进来的以默认值处理）

        @param {EnumCallMode} call_mode - 调用模式
        @param {string} api_type - 'RECV'，请求处理；'RESP',回复处理
        @param {dict} init_para={} - 初始化参数

        @return {dict} - 返回具有完整信息的参数对象
        """
        _ret_para = copy.deepcopy(self._default_logging_para[call_mode][api_type])
        _ret_para.update(init_para)
        return _ret_para

    #############################
    # 公共属性
    #############################
    @property
    def logger(self):
        """
        获取日志类
        @property {HiveNetLib.simple_log.Logger}
        """
        return self._logger

    @property
    def dealing_num(self):
        """
        获取正在执行的报文个数
        @property {int}
        """
        return self._dealing_num

    @property
    def default_logging_para(self):
        """
        获取默认打印参数，可用进行修改
        @property {dict}
        """
        return self._default_logging_para

    #############################
    # 公共函数
    #############################
    def add_service(self, call_mode, name, fun, recv_logging_para={}, resp_logging_para={}):
        """
        添加可执行服务

        @param {EnumCallMode} call_mode - 调用模式
        @param {string} name - 服务名
        @param {function} fun - 服务函数对象
        @param {dict} recv_logging_para={} - 接收报文打印参数
        @param {dict} resp_logging_para={} - 返回报文打印参数
            recv_logging_para的参数格式一致，定义如下：
            'msg_class' {class} - 继承MsgFW框架的报文解析类对象，如果为None代表不处理信息
            'logging_head' {dict}- 定义打印的日志规范头信息
                key {string} - 日志头信息项名，例如'IP'
                value {string} - 日志头信息值，None代表从报文对象msg或proto_msg中获取(从api_mapping获取定义)
                跟当前服务相关的可选信息项包括：
                C-IP : 客户端的IP地址
                C-PORT : 客户端的连接端口
                S-IP : 服务端绑定服务
                S-PORT : 服务端监听端口
                CALL_MODE : 服务端调用模式
                SERVICE_NAME : 访问的服务名
                PARA_BYTES : 转换为字符串显示的参数字节数组信息（如果是返回报文该参数代表显示RETURN_BYTES）
                PARA_BYTES_LEN : 字节数组长度（如果是返回报文该参数代表显示RETURN_BYTES_LEN）

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

        @returns {CResult} - 结果:
            result.code ：'00000'-成功，'11006'-服务名不可为空，'13001'-服务名已存在
        """
        _dict = None
        # 根据不同的模式，切换处理的列表
        if call_mode == EnumCallMode.ClientSideStream:
            _dict = self._client_side_stream_service_list
        elif call_mode == EnumCallMode.ServerSideStream:
            _dict = self._server_side_stream_service_list
        elif call_mode == EnumCallMode.BidirectionalStream:
            _dict = self._bidirectional_stream_service_list
        else:
            _dict = self._simple_service_list

        _result = None
        if name == '':
            # 服务名不可为空
            _result = CResult(code='11006', i18n_msg_paras=('name'))
        elif name in _dict.keys():
            # 服务名已存在
            _result = CResult(code='13001', i18n_msg_paras=('name'))
        else:
            # 接收报文的打印参数，初始化为可用
            _recv_para = self.generate_logging_para(call_mode, 'RECV', recv_logging_para)

            # 响应报文的打印参数，初始化为可用
            _resp_para = self.generate_logging_para(call_mode, 'RESP', resp_logging_para)

            # 加入服务
            _dict[name] = [fun, _recv_para, _resp_para]
            _result = CResult(code='00000')  # 成功

        return _result

    def remove_service(self, call_mode, name):
        """
        移除可执行服务

        @param {EnumCallMode} call_mode - 调用模式
        @param {string} name - 服务名

        @returns {CResult} - 结果:
            result.code ：'00000'-成功，'11006'-服务名不可为空，'13002'-服务名不存在

        """
        _dict = None
        # 根据不同的模式，切换处理的列表
        if call_mode == EnumCallMode.ClientSideStream:
            _dict = self._client_side_stream_service_list
        elif call_mode == EnumCallMode.ServerSideStream:
            _dict = self._server_side_stream_service_list
        elif call_mode == EnumCallMode.BidirectionalStream:
            _dict = self._bidirectional_stream_service_list
        else:
            _dict = self._simple_service_list

        _result = None
        if name == '':
            # 服务名不可为空
            _result = CResult(code='11006', i18n_msg_paras=('name'))
        elif name not in _dict.keys():
            # 服务名不存在
            _result = CResult(code='13002', i18n_msg_paras=('name'))
        else:
            # 移除字典项
            del _dict[name]
            _result = CResult(code='00000')  # 成功

        return _result

    def clear_service(self, call_mode=None):
        """
        清除所有可执行服务

        @param {EnumCallMode} call_mode=None - 调用模式，不传时删除所有服务

        @returns {CResult} - 结果:
            result.code ：'00000'-成功
        """
        if call_mode is None:
            # 删除所有服务
            self._simple_service_list.clear()
            self._client_side_stream_service_list.clear()
            self._server_side_stream_service_list.clear()
            self._bidirectional_stream_service_list.clear()
        else:
            _dict = None
            # 根据不同的模式，切换处理的列表
            if call_mode == EnumCallMode.ClientSideStream:
                _dict = self._client_side_stream_service_list
            elif call_mode == EnumCallMode.ServerSideStream:
                _dict = self._server_side_stream_service_list
            elif call_mode == EnumCallMode.BidirectionalStream:
                _dict = self._bidirectional_stream_service_list
            else:
                _dict = self._simple_service_list
            _dict.clear()
        return CResult(code='00000')  # 成功

    def generate_client_module(self, file_path='', call_mode=None):
        """
        根据服务配置生成客户端调用模块

        @param {string} file_path - 生成的模块文件名
        @param {EnumCallMode} call_mode=None - 调用模式，不传时生成所有服务

        @returns {CResult} - 结果:
            result.code ：'00000'-成功，'11006'-服务名不可为空，'13002'-服务名不存在
        """
        print(RunTool.get_current_function_object())
        # TODO({$AUTHOR$}): Todo Descript
        _result = CResult(code='00000')  # 成功
        return _result

    #############################
    # gRPC的标准接入服务接口
    #############################
    def GRpcCallSimple(self, request, context):
        """
        简单模式(Simple)gRPC的标准接入服务接口

        @param {msg_pb2.RpcRequest} request - 请求对象，与msg.proto定义一致,
          例如可通过request.para_json获取要执行的函数的入参信息
        @param {grpc.ServicerContext} context - 服务端的上下文,
          具体定义@see https://grpc.github.io/grpc/python/grpc.html#service-side-context

        @retrun {msg_pb2.RpcResponse} - 返回调用结果信息
        """
        # 正在处理报文计数+1
        self._dealing_num_addon(1)
        try:
            # 入口的初始化处理
            _start_time = datetime.datetime.now()  # 开始处理时间
            _trace_info = self._get_trace_info(request, context)  # 调用链信息获取及处理
            _call_result = CResult(code='00000')  # 执行结果，默认先为成功
            _return_json_obj = None

            _request_info_dict = dict()
            if self._logger is not None:
                # 获取请求信息中与日志登记相关的信息，形成日志字典
                _request_info_dict = self._get_request_info_dict(
                    request, context, EnumCallMode.Simple)
                # 补充日志字典信息
                _request_info_dict['trace_id'] = _trace_info.trace_id
                _request_info_dict['parent_id'] = _trace_info.parent_id
                _request_info_dict['trace_level'] = _trace_info.trace_level
                _request_info_dict['call_id'] = _trace_info.call_id
                _request_info_dict['api_call_type'] = 'RECV'
                _request_info_dict['api_info_type'] = 'RECV'
                _request_info_dict['err_log_msg'] = 'api call chain recv log error'
                # 打印调用链日志
                self._write_call_chain_log(_request_info_dict)

            # 开始进行处理，处理过程中要捕获异常
            try:
                # 执行函数
                if request.service_name not in self._simple_service_list.keys():
                    # 没有找到服务名，返回执行失败
                    _call_result = CResult(code='11403', i18n_msg_paras=(request.service_name, ))
                else:
                    # 先形成调用参数
                    _fun_object = self._simple_service_list[request.service_name][0]
                    _paras = json.loads(request.para_json)
                    _call_para_str = self._get_call_para_str(
                        request, context, _fun_object, _paras, '_paras', '_trace_info', None
                    )

                    # 开始动态执行函数
                    _fun_return_obj = eval(
                        '_fun_object(%s)' % (_call_para_str))

                    # 返回值转换为json
                    _return_json_obj = SimpleGRpcTools.object_to_json_support_bytes(
                        _fun_return_obj, is_support_bytes=True)
            except:
                _error = str(sys.exc_info()[0])
                _call_result = CResult(code='21008', error=_error, trace_str=traceback.format_exc(),
                                       i18n_msg_paras=(_error, ))

            # 处理返回对象
            if _return_json_obj is None:
                _return_json_obj = NullObj()
                _return_json_obj.return_json = ''
                _return_json_obj.has_return_bytes = False
                _return_json_obj.return_bytes = None

            _return_obj = SimpleGRpcTools.generate_response_obj(
                return_json=_return_json_obj.return_json,
                has_return_bytes=_return_json_obj.has_return_bytes,
                return_bytes=_return_json_obj.return_bytes,
                call_code=_call_result.code,
                call_msg=_call_result.i18n_msg_id,
                call_error=_call_result.error,
                call_msg_para=_call_result.i18n_msg_paras
            )

            if self._logger is not None:
                # 在日志字典中补充返回信息内容
                _request_info_dict['logging_para'] = copy.deepcopy(
                    _request_info_dict['resp_logging_para'])
                _request_info_dict['para_json'] = _return_obj.return_json
                if _return_obj.return_bytes is None:
                    _request_info_dict['para_bytes_len'] = 'None'
                    _request_info_dict['para_bytes'] = 'None'
                else:
                    _request_info_dict['para_bytes_len'] = str(len(_return_obj.return_bytes))
                    if 'PARA_BYTES' in _request_info_dict['logging_para']['logging_head'].keys():
                        _request_info_dict['para_bytes'] = str(_return_obj.return_bytes)

                _request_info_dict['err_log_msg'] = 'api call chain resp log error'
                _request_info_dict['api_call_type'] = 'RECV'
                _request_info_dict['api_info_type'] = 'RET'
                _request_info_dict['log_level'] = self._log_level
                _end_time = datetime.datetime.now()
                _request_info_dict['use'] = (_end_time - _start_time).total_seconds()
                if _call_result.code == '21008':
                    # 异常的情况
                    _request_info_dict['api_info_type'] = 'EX'
                    _request_info_dict['log_level'] = logging.ERROR
                # 异常信息
                _request_info_dict['error'] = _call_result.error
                _request_info_dict['trace_str'] = _call_result.trace_str
                _request_info_dict['error'] = _call_result.error

                # 打印调用链日志
                self._write_call_chain_log(_request_info_dict)

            # 返回结果
            return _return_obj
        except Exception as e:
            # 出现异常，执行打印处理
            if self._logger is not None:
                self._logger.error(
                    '[EX:%s]%s' % (str(sys.exc_info()[0]), traceback.format_exc())
                )
            raise e
        finally:
            # 正在处理报文计数-1
            self._dealing_num_addon(-1)

    def GRpcCallClientSideStream(self, request_iterator, context):
        """
        客户端流模式(ClientSideStream)gRPC的标准接入服务接口

        @param {iterator} request_iterator - 请求对象迭代器（msg_pb2.RpcRequest），单个对象与msg.proto定义一致,
          例如可通过request.para_json获取要执行的函数的入参信息
        @param {grpc.ServicerContext} context - 服务端的上下文,
          具体定义@see https://grpc.github.io/grpc/python/grpc.html#service-side-context

        @retrun {msg_pb2.RpcResponse} - 返回调用结果信息
        """
        # 正在处理报文计数+1
        self._dealing_num_addon(1)
        _start_time = datetime.datetime.now()  # 开始处理时间
        _call_result = CResult(code='00000')  # 执行结果，默认先为成功
        _return_obj = None  # 返回对象（RpcResponse）
        _return_json_obj = None  # 返回对象的json转换对象
        request = None  # 从迭代器获取请求对象
        _next_request = None  # 下一个请求对象
        _has_next = True  # 标识是否有下一个请求对象
        try:
            request = next(request_iterator)
            while _has_next:
                # 循环从迭代器获取请求对象进行处理
                try:
                    # 判断是否有下一个请求
                    _next_request = next(request_iterator)
                except StopIteration:
                    _has_next = False

                # 处理当前请求
                _return_obj = None
                _return_json_obj = None
                _block_start_time = datetime.datetime.now()  # 流数据块开始处理时间
                _trace_info = self._get_trace_info(request, context)  # 调用链信息获取及处理
                _request_info_dict = dict()
                if self._logger is not None:
                    # 获取请求信息中与日志登记相关的信息，形成日志字典
                    _request_info_dict = self._get_request_info_dict(
                        request, context, EnumCallMode.ClientSideStream)
                    # 补充日志字典信息
                    _request_info_dict['trace_id'] = _trace_info.trace_id
                    _request_info_dict['parent_id'] = _trace_info.parent_id
                    _request_info_dict['trace_level'] = _trace_info.trace_level
                    _request_info_dict['call_id'] = _trace_info.call_id
                    _request_info_dict['api_call_type'] = 'RECV'
                    _request_info_dict['api_info_type'] = 'STREAM-RECV'
                    _request_info_dict['err_log_msg'] = 'api call chain recv log error'

                    # 打印调用链日志
                    self._write_call_chain_log(_request_info_dict)

                # 开始进行处理，处理过程中要捕获异常
                try:
                    # 执行函数
                    if request.service_name not in self._client_side_stream_service_list.keys():
                        # 没有找到服务名，返回执行失败
                        _call_result = CResult(
                            code='11403', i18n_msg_paras=(request.service_name, ))
                    else:
                        # 先形成调用参数
                        _fun_object = self._client_side_stream_service_list[request.service_name][0]
                        _paras = json.loads(request.para_json)
                        _call_para_str = self._get_call_para_str(
                            request, context, _fun_object, _paras, '_paras', '_trace_info', _has_next
                        )

                        # 开始动态执行函数
                        _fun_return_obj = eval(
                            '_fun_object(%s)' % (_call_para_str))

                        # 返回值转换为json
                        _return_json_obj = SimpleGRpcTools.object_to_json_support_bytes(
                            _fun_return_obj, is_support_bytes=True)
                except:
                    _error = str(sys.exc_info()[0])
                    _call_result = CResult(code='21008', error=_error, trace_str=traceback.format_exc(),
                                           i18n_msg_paras=(_error, ))

                # 处理返回对象
                if _return_json_obj is None:
                    _return_json_obj = NullObj()
                    _return_json_obj.return_json = ''
                    _return_json_obj.has_return_bytes = False
                    _return_json_obj.return_bytes = None

                _return_obj = SimpleGRpcTools.generate_response_obj(
                    return_json=_return_json_obj.return_json,
                    has_return_bytes=_return_json_obj.has_return_bytes,
                    return_bytes=_return_json_obj.return_bytes,
                    call_code=_call_result.code,
                    call_msg=_call_result.i18n_msg_id,
                    call_error=_call_result.error,
                    call_msg_para=_call_result.i18n_msg_paras
                )

                if self._logger is not None:
                    # 在日志字典中补充返回信息内容
                    _request_info_dict['logging_para'] = copy.deepcopy(
                        _request_info_dict['resp_logging_para'])
                    _request_info_dict['para_json'] = _return_obj.return_json
                    if _return_obj.return_bytes is None:
                        _request_info_dict['para_bytes_len'] = 'None'
                        _request_info_dict['para_bytes'] = 'None'
                    else:
                        _request_info_dict['para_bytes_len'] = str(len(_return_obj.return_bytes))
                        if 'PARA_BYTES' in _request_info_dict['logging_para']['logging_head'].keys():
                            _request_info_dict['para_bytes'] = str(_return_obj.return_bytes)

                    _request_info_dict['err_log_msg'] = 'api call chain resp log error'
                    _request_info_dict['api_call_type'] = 'RECV'
                    _request_info_dict['api_info_type'] = 'STREAM-RET'
                    _request_info_dict['log_level'] = self._log_level
                    _end_time = datetime.datetime.now()
                    _request_info_dict['use'] = (_end_time - _start_time).total_seconds()
                    if _call_result.code == '21008':
                        # 异常的情况
                        _request_info_dict['api_info_type'] = 'EX'
                        _request_info_dict['log_level'] = logging.ERROR
                    elif _has_next:
                        # 还有下一个报文
                        _request_info_dict['api_info_type'] = 'STREAM-DEAL'
                        _request_info_dict['use'] = (_end_time - _block_start_time).total_seconds()

                    # 异常信息
                    _request_info_dict['error'] = _call_result.error
                    _request_info_dict['trace_str'] = _call_result.trace_str
                    _request_info_dict['error'] = _call_result.error

                    # 打印调用链日志
                    self._write_call_chain_log(_request_info_dict)

                # 判断本次处理结果，如果不是成功则直接跳出循环并返回结果
                if not _call_result.is_success():
                    break
                else:
                    # 下一个循环处理
                    request = _next_request

            # 返回最后一个的结果
            return _return_obj
        except Exception as e:
            # 出现异常，执行打印处理
            if self._logger is not None:
                self._logger.error(
                    '[EX:%s]%s' % (str(sys.exc_info()[0]), traceback.format_exc())
                )
            raise e
        finally:
            # 正在处理报文计数-1
            self._dealing_num_addon(-1)

    def GRpcCallServerSideStream(self, request, context):
        """
        服务器流模式(ServerSideStream)gRPC的标准接入服务接口

        @param {msg_pb2.RpcRequest} request - 请求对象，与msg.proto定义一致,
          例如可通过request.para_json获取要执行的函数的入参信息
        @param {grpc.ServicerContext} context - 服务端的上下文,
          具体定义@see https://grpc.github.io/grpc/python/grpc.html#service-side-context

        @retrun {iterator} - 返回调用结果信息（msg_pb2.RpcResponse）的迭代器（iterator）
        """
        # 正在处理报文计数+1
        self._dealing_num_addon(1)
        try:
            # 入口的初始化处理
            _start_time = datetime.datetime.now()  # 开始处理时间
            _trace_info = self._get_trace_info(request, context)  # 调用链信息获取及处理
            _call_result = CResult(code='00000')  # 执行结果，默认先为成功
            _return_json_obj = None
            _fun_iterator = None
            _request_info_dict = dict()
            if self._logger is not None:
                # 获取请求信息中与日志登记相关的信息，形成日志字典
                _request_info_dict = self._get_request_info_dict(
                    request, context, EnumCallMode.ServerSideStream)
                # 补充日志字典信息
                _request_info_dict['trace_id'] = _trace_info.trace_id
                _request_info_dict['parent_id'] = _trace_info.parent_id
                _request_info_dict['trace_level'] = _trace_info.trace_level
                _request_info_dict['call_id'] = _trace_info.call_id
                _request_info_dict['api_call_type'] = 'RECV'
                _request_info_dict['api_info_type'] = 'RECV'
                _request_info_dict['err_log_msg'] = 'api call chain recv log error'

                # 打印调用链日志
                self._write_call_chain_log(_request_info_dict)

            # 开始进行处理，处理过程中要捕获异常
            try:
                # 执行函数
                if request.service_name not in self._server_side_stream_service_list.keys():
                    # 没有找到服务名，返回执行失败
                    _call_result = CResult(code='11403', i18n_msg_paras=(request.service_name, ))
                else:
                    # 先形成调用参数
                    _fun_object = self._server_side_stream_service_list[request.service_name][0]
                    _paras = json.loads(request.para_json)
                    _call_para_str = self._get_call_para_str(
                        request, context, _fun_object, _paras, '_paras', '_trace_info', None
                    )

                    # 开始动态执行函数，注意这里函数执行返回的必须是一个迭代器，由生成器函数yield返回
                    _fun_iterator = eval(
                        '_fun_object(%s)' % (_call_para_str))
            except:
                _error = str(sys.exc_info()[0])
                _call_result = CResult(code='21008', error=_error, trace_str=traceback.format_exc(),
                                       i18n_msg_paras=(_error, ))

            if self._logger is not None:
                # 异常信息
                _request_info_dict['error'] = _call_result.error
                _request_info_dict['trace_str'] = _call_result.trace_str
                _request_info_dict['error'] = _call_result.error

            # 判断是否异常失败，如果是，单独返回
            if not _call_result.is_success():
                _return_obj = SimpleGRpcTools.generate_response_obj(
                    return_json='',
                    has_return_bytes=False,
                    return_bytes=None,
                    call_code=_call_result.code,
                    call_msg=_call_result.i18n_msg_id,
                    call_error=_call_result.error,
                    call_msg_para=_call_result.i18n_msg_paras
                )
                if self._logger is not None:
                    # 在日志字典中补充返回信息内容
                    _request_info_dict['logging_para'] = copy.deepcopy(
                        _request_info_dict['resp_logging_para'])
                    _request_info_dict['para_json'] = _return_obj.return_json
                    if _return_obj.return_bytes is None:
                        _request_info_dict['para_bytes_len'] = 'None'
                        _request_info_dict['para_bytes'] = 'None'
                    else:
                        _request_info_dict['para_bytes_len'] = str(len(_return_obj.return_bytes))
                        if 'PARA_BYTES' in _request_info_dict['logging_para']['logging_head'].keys():
                            _request_info_dict['para_bytes'] = str(_return_obj.return_bytes)

                    _request_info_dict['err_log_msg'] = 'api call chain resp log error'
                    _request_info_dict['api_call_type'] = 'RECV'
                    _request_info_dict['api_info_type'] = 'STREAM-RET'
                    _request_info_dict['log_level'] = self._log_level
                    _end_time = datetime.datetime.now()
                    _request_info_dict['use'] = (_end_time - _start_time).total_seconds()
                    if _call_result.code == '21008':
                        # 异常的情况
                        _request_info_dict['api_info_type'] = 'EX'
                        _request_info_dict['log_level'] = logging.ERROR

                    # 打印调用链日志
                    self._write_call_chain_log(_request_info_dict)

                # 返回处理结果
                yield _return_obj
            else:
                # 迭代器处理
                for _fun_obj in _fun_iterator:
                    # 返回值转换为json
                    _return_json_obj = SimpleGRpcTools.object_to_json_support_bytes(
                        _fun_obj, is_support_bytes=True)

                    _return_obj = SimpleGRpcTools.generate_response_obj(
                        return_json=_return_json_obj.return_json,
                        has_return_bytes=_return_json_obj.has_return_bytes,
                        return_bytes=_return_json_obj.return_bytes,
                        call_code=_call_result.code,
                        call_msg=_call_result.i18n_msg_id,
                        call_error=_call_result.error,
                        call_msg_para=_call_result.i18n_msg_paras
                    )

                    if self._logger is not None:
                        # 在日志字典中补充返回信息内容
                        _request_info_dict['logging_para'] = copy.deepcopy(
                            _request_info_dict['resp_logging_para'])
                        _request_info_dict['para_json'] = _return_obj.return_json
                        if _return_obj.return_bytes is None:
                            _request_info_dict['para_bytes_len'] = 'None'
                            _request_info_dict['para_bytes'] = 'None'
                        else:
                            _request_info_dict['para_bytes_len'] = str(
                                len(_return_obj.return_bytes))
                            if 'PARA_BYTES' in _request_info_dict['logging_para']['logging_head'].keys():
                                _request_info_dict['para_bytes'] = str(_return_obj.return_bytes)

                        _request_info_dict['err_log_msg'] = 'api call chain resp log error'
                        _request_info_dict['api_call_type'] = 'RECV'
                        _request_info_dict['api_info_type'] = 'STREAM-RET'
                        _request_info_dict['log_level'] = self._log_level
                        _end_time = datetime.datetime.now()
                        _request_info_dict['use'] = (_end_time - _start_time).total_seconds()

                        # 打印调用链日志
                        self._write_call_chain_log(_request_info_dict)

                    # 返回结果
                    yield _return_obj
        except Exception as e:
            # 出现异常，执行打印处理
            if self._logger is not None:
                self._logger.error(
                    '[EX:%s]%s' % (str(sys.exc_info()[0]), traceback.format_exc())
                )
            raise e
        except GeneratorExit:
            # 遇到生成器结束的情况
            if self._logger is not None:
                self._logger.error(
                    '[EX:%s]%s' % (str(sys.exc_info()[0]), traceback.format_exc())
                )
        finally:
            # 正在处理报文计数-1
            self._dealing_num_addon(-1)

    def GRpcCallBidirectionalStream(self, request_iterator, context):
        """
        双向流模式(BidirectionalStream)gRPC的标准接入服务接口

        @param {iterator} request_iterator - 请求对象迭代器（msg_pb2.RpcRequest），单个对象与msg.proto定义一致,
          例如可通过request.para_json获取要执行的函数的入参信息
        @param {grpc.ServicerContext} context - 服务端的上下文,
          具体定义@see https://grpc.github.io/grpc/python/grpc.html#service-side-context

        @retrun {iterator} - 返回调用结果信息（msg_pb2.RpcResponse）的迭代器（iterator）
        """
        # 正在处理报文计数+1
        self._dealing_num_addon(1)
        _start_time = datetime.datetime.now()  # 开始处理时间
        _call_result = CResult(code='00000')  # 执行结果，默认先为成功
        _return_obj = None  # 返回对象（RpcResponse）
        _return_json_obj = None  # 返回对象的json转换对象
        request = None  # 从迭代器获取请求对象
        try:
            _has_next = True
            while _has_next:
                # 循环从迭代器获取请求对象进行处理
                try:
                    # 获取下一个请求
                    request = next(request_iterator)
                except StopIteration:
                    _has_next = False

                # 处理当前请求
                _return_obj = None
                _return_json_obj = None
                _block_start_time = datetime.datetime.now()  # 流数据块开始处理时间
                _trace_info = self._get_trace_info(request, context)  # 调用链信息获取及处理
                _request_info_dict = dict()
                if self._logger is not None:
                    # 获取请求信息中与日志登记相关的信息，形成日志字典
                    _request_info_dict = self._get_request_info_dict(
                        request, context, EnumCallMode.BidirectionalStream)
                    # 补充日志字典信息
                    _request_info_dict['trace_id'] = _trace_info.trace_id
                    _request_info_dict['parent_id'] = _trace_info.parent_id
                    _request_info_dict['trace_level'] = _trace_info.trace_level
                    _request_info_dict['call_id'] = _trace_info.call_id
                    _request_info_dict['api_call_type'] = 'RECV'
                    _request_info_dict['api_info_type'] = 'STREAM-RECV'
                    _request_info_dict['err_log_msg'] = 'api call chain recv log error'

                    # 打印调用链日志
                    self._write_call_chain_log(_request_info_dict)

                # 开始进行处理，处理过程中要捕获异常
                try:
                    # 执行函数
                    if request.service_name not in self._bidirectional_stream_service_list.keys():
                        # 没有找到服务名，返回执行失败
                        _call_result = CResult(
                            code='11403', i18n_msg_paras=(request.service_name, ))
                    else:
                        # 先形成调用参数
                        _fun_object = self._bidirectional_stream_service_list[request.service_name][0]
                        _paras = json.loads(request.para_json)
                        _call_para_str = self._get_call_para_str(
                            request, context, _fun_object, _paras, '_paras', '_trace_info', _has_next
                        )

                        # 开始动态执行函数
                        _fun_iterator = eval(
                            '_fun_object(%s)' % (_call_para_str))
                except:
                    _error = str(sys.exc_info()[0])
                    _call_result = CResult(code='21008', error=_error, trace_str=traceback.format_exc(),
                                           i18n_msg_paras=(_error, ))

                if self._logger is not None:
                    # 异常信息
                    _request_info_dict['error'] = _call_result.error
                    _request_info_dict['trace_str'] = _call_result.trace_str
                    _request_info_dict['error'] = _call_result.error

                # 判断是否异常失败，如果是，单独返回
                if not _call_result.is_success():
                    _return_obj = SimpleGRpcTools.generate_response_obj(
                        return_json='',
                        has_return_bytes=False,
                        return_bytes=None,
                        call_code=_call_result.code,
                        call_msg=_call_result.i18n_msg_id,
                        call_error=_call_result.error,
                        call_msg_para=_call_result.i18n_msg_paras
                    )

                    if self._logger is not None:
                        # 在日志字典中补充返回信息内容
                        _request_info_dict['logging_para'] = copy.deepcopy(
                            _request_info_dict['resp_logging_para'])
                        _request_info_dict['para_json'] = _return_obj.return_json
                        if _return_obj.return_bytes is None:
                            _request_info_dict['para_bytes_len'] = 'None'
                            _request_info_dict['para_bytes'] = 'None'
                        else:
                            _request_info_dict['para_bytes_len'] = str(
                                len(_return_obj.return_bytes))
                            if 'PARA_BYTES' in _request_info_dict['logging_para']['logging_head'].keys():
                                _request_info_dict['para_bytes'] = str(_return_obj.return_bytes)

                        _request_info_dict['err_log_msg'] = 'api call chain resp log error'
                        _request_info_dict['api_call_type'] = 'RECV'
                        _request_info_dict['api_info_type'] = 'STREAM-RET'
                        _request_info_dict['log_level'] = self._log_level
                        _end_time = datetime.datetime.now()
                        _request_info_dict['use'] = (_end_time - _start_time).total_seconds()
                        if _call_result.code == '21008':
                            # 异常的情况
                            _request_info_dict['api_info_type'] = 'EX'
                            _request_info_dict['log_level'] = logging.ERROR

                        # 打印调用链日志
                        self._write_call_chain_log(_request_info_dict)

                    # 返回处理结果
                    yield _return_obj
                else:
                    # 迭代器处理
                    for _fun_obj in _fun_iterator:
                        if _fun_obj is None:
                            # 不处理
                            _return_obj = SimpleGRpcTools.generate_response_obj(
                                return_json='',
                                has_return_bytes=False,
                                return_bytes=None,
                                call_code=_call_result.code,
                                call_msg=_call_result.i18n_msg_id,
                                call_error=_call_result.error,
                                call_msg_para=_call_result.i18n_msg_paras
                            )
                            _request_info_dict['api_info_type'] = 'STREAM-DEAL'
                            _use_time = _block_start_time
                        else:
                            # 返回值转换为json
                            _return_json_obj = SimpleGRpcTools.object_to_json_support_bytes(
                                _fun_obj, is_support_bytes=True)

                            _return_obj = SimpleGRpcTools.generate_response_obj(
                                return_json=_return_json_obj.return_json,
                                has_return_bytes=_return_json_obj.has_return_bytes,
                                return_bytes=_return_json_obj.return_bytes,
                                call_code=_call_result.code,
                                call_msg=_call_result.i18n_msg_id,
                                call_error=_call_result.error,
                                call_msg_para=_call_result.i18n_msg_paras
                            )
                            _request_info_dict['api_info_type'] = 'STREAM-RET'
                            _use_time = _start_time

                        if self._logger is not None:
                            # 在日志字典中补充返回信息内容
                            _request_info_dict['logging_para'] = copy.deepcopy(
                                _request_info_dict['resp_logging_para'])
                            _request_info_dict['para_json'] = _return_obj.return_json
                            if _return_obj.return_bytes is None:
                                _request_info_dict['para_bytes_len'] = 'None'
                                _request_info_dict['para_bytes'] = 'None'
                            else:
                                _request_info_dict['para_bytes_len'] = str(
                                    len(_return_obj.return_bytes))
                                if 'PARA_BYTES' in _request_info_dict['logging_para']['logging_head'].keys():
                                    _request_info_dict['para_bytes'] = str(_return_obj.return_bytes)

                            _request_info_dict['err_log_msg'] = 'api call chain resp log error'
                            _request_info_dict['api_call_type'] = 'RECV'
                            _request_info_dict['log_level'] = logging.INFO
                            _end_time = datetime.datetime.now()
                            _request_info_dict['use'] = (_end_time - _use_time).total_seconds()

                            # 打印调用链日志
                            self._write_call_chain_log(_request_info_dict)

                        # 返回结果
                        if _fun_obj is not None:
                            yield _return_obj

                # 判断本次处理结果，如果不是成功则直接跳出循环并返回结果
                if not _call_result.is_success():
                    break
        except Exception as e:
            # 出现异常，执行打印处理
            if self._logger is not None:
                self._logger.error(
                    '[EX:%s]%s' % (str(sys.exc_info()[0]), traceback.format_exc())
                )
            raise e
        finally:
            # 正在处理报文计数-1
            self._dealing_num_addon(-1)

    def GRpcCallHealthCheck(self, request, context):
        """
        自定义的健康检查服务

        @param {msg_pb2.HealthRequest} request - 请求对象，与msg.proto定义一致,
          例如可通过request.para_json获取要执行的函数的入参信息
        @param {grpc.ServicerContext} context - 服务端的上下文,
          具体定义@see https://grpc.github.io/grpc/python/grpc.html#service-side-context

        @retrun {msg_pb2.HealthResponse} - 返回调用结果信息
        """
        return msg_pb2.HealthResponse(status=msg_pb2.HealthResponse.SERVING)

    #############################
    # 内部函数
    #############################
    def _write_call_chain_log(self, info_dict):
        """
        写调用链日志（同步及异步模式区别处理）

        @param {dict} info_dict - 信息字典
        """
        SimpleGRpcTools.write_api_call_chain_log(self._logger, info_dict)

    def _get_request_info_dict(self, request, context, call_mode):
        """
        将请求中的request和context的关键信息转换为字典，用于进行日志处理

        @param {RpcRequest|StreamRpcRequest} request - 请求对象，与msg.proto定义一致
        @param {grpc.ServicerContext} context - 服务端的上下文
        @param {EnumCallMode} call_mode - 调用模式

        @return {dict} - 转换后的信息字典，包括的信息如下“key - value - 说明”：
            call_mode - 调用模式
            para_json - 请求信息
            c-ip - str(context.peer()).split(':')[1] - 客户端IP
            c-port - str(context.peer()).split(':')[2] - 客户端端口
            s-ip - str(context._rpc_event.call_details.host, 'utf-8').split(':')[0] - 服务端IP
            s-port - str(context._rpc_event.call_details.host, 'utf-8').split(':')[1] - 服务端端口
            service_name - request.service_name - 服务名
            logging_para - dict - 日志参数字典
            para_bytes - 请求信息的bytes转换为字符串
            para_bytes_len - 请求信息的bytes的长度

            以下信息为默认信息，可以在处理过程中修改：
            use - 接口执行耗时
            error - 异常对象
            trace_str - 异常堆栈信息

            以下信息在处理过程中再添加：
            trace_id - request.trace_id - 调用链追踪ID
            parent_id - request.parent_id - 上一函数的执行ID
            trace_level - request.trace_level - 函数调用层级
            call_id - 当前函数的执行id

            err_log_msg - 写日志异常时的日志输出
            api_call_type - 接口调用类型
            api_info_type - 接口信息类型

            以下信息作为冗余备份，作用是当请求重复打印请求时可以直接获取处理
            recv_logging_para - dict - 复制self._default_logging_para的对应RECV的日志参数
            resp_logging_para - dict - 复制self._default_logging_para的对应RESP的日志参数
            recv_para_bytes_len
            recv_para_bytes
        """
        _dict = dict()
        # 默认信息
        _dict['use'] = 0
        _dict['error'] = None
        _dict['trace_str'] = ''
        _dict['log_level'] = self._log_level
        _dict['call_fun_level'] = 2
        # _frame = RunTool.get_parent_function_frame(1)
        # _dict['function_name'] = _frame.f_code.co_name
        # _dict['module_file'] = os.path.realpath(_frame.f_code.co_filename)
        # 基本信息
        _dict['call_mode'] = call_mode
        _dict['para_json'] = request.para_json
        # IP信息
        _dict['c-ip'] = str(context.peer()).split(':')[1]
        _dict['c-port'] = str(context.peer()).split(':')[2]
        _dict['s-ip'] = str(context._rpc_event.call_details.host, 'utf-8').split(':')[0]
        _dict['s-port'] = str(context._rpc_event.call_details.host, 'utf-8').split(':')[1]
        # 请求报文信息
        _dict['service_name'] = request.service_name
        # 获取日志打印参数
        _service_list = None
        if call_mode == EnumCallMode.ClientSideStream:
            _service_list = self._client_side_stream_service_list
        elif call_mode == EnumCallMode.ServerSideStream:
            _service_list = self._server_side_stream_service_list
        elif call_mode == EnumCallMode.BidirectionalStream:
            _service_list = self._bidirectional_stream_service_list
        else:
            _service_list = self._simple_service_list
        if request.service_name not in _service_list.keys():
            # 服务不在，取默认打印参数
            _dict['recv_logging_para'] = self._default_logging_para[call_mode]['RECV']
            _dict['resp_logging_para'] = self._default_logging_para[call_mode]['RESP']
        else:
            _dict['recv_logging_para'] = _service_list[request.service_name][1]
            _dict['resp_logging_para'] = _service_list[request.service_name][2]
        _dict['logging_para'] = copy.deepcopy(_dict['recv_logging_para'])
        # 请求信息的bytes数组
        if request.para_bytes is None:
            _dict['recv_para_bytes_len'] = 'None'
            _dict['recv_para_bytes'] = 'None'
        else:
            _dict['recv_para_bytes_len'] = str(len(request.para_bytes))
            if 'PARA_BYTES' in _dict['logging_para']['logging_head'].keys():
                _dict['recv_para_bytes'] = str(request.para_bytes)
            else:
                _dict['recv_para_bytes'] = 'None'
        _dict['para_bytes_len'] = _dict['recv_para_bytes_len']
        _dict['para_bytes'] = _dict['recv_para_bytes']
        # 返回字典
        return _dict

    def _get_trace_info(self, request, context):
        """
        获取调用链信息

        @param {RpcRequest|StreamRpcRequest} request - 请求对象，与msg.proto定义一致
        @param {grpc.ServicerContext} context - 服务端的上下文

        @return {NullObj} - 从request获取信息处理后的调用链信息
        """
        _trace_info = NullObj()
        _trace_info.trace_id = request.trace_id
        _trace_info.parent_id = request.parent_id
        _trace_info.trace_level = request.trace_level
        _trace_info.call_id = CallChainTool.generate_trace_id(
            idpool=self._idpool,
            get_id_overtime=self._get_id_overtime,
            **self._init_kwargs
        )  # 当前函数的执行id
        if _trace_info.trace_id == '':
            # 上送请求没有调用链，则链从自己开始
            _trace_info.trace_id = _trace_info.call_id
            _trace_info.trace_level = 0
        else:
            _trace_info.trace_level = _trace_info.trace_level + 1
        # 返回信息
        return _trace_info

    def _get_call_para_str(self, request, context, fun_object, paras, paras_var_name, trace_info_var_name, has_next_stream_data=None):
        """
        获取调用实际函数的请求参数执行字符串（仅参数部分）

        @param {RpcRequest} request - 请求对象，与msg.proto定义一致
        @param {grpc.ServicerContext} context - 服务端的上下文
        @param {function} fun_object - 要处理的函数
        @param {list} paras - 参数的数组对象
        @param {string} paras_var_name - 参数名
        @param {string} trace_info_var_name - 调用链信息对象名
        @param {string} has_next_stream_data=None - 流模式是否有下一个数据，如果为None则代表无这个参数

        @return {string} - 返回函数调用的参数字符串
        """
        _call_para_str = ''
        _i = 0
        _has_deal_bytes = False
        _is_function_has_var_parameter = RunTool.is_function_has_var_parameter(
            fun_object, var_positional=False, var_keyword=True
        )
        _has_deal_next_stream_data = False
        if has_next_stream_data is None:
            _has_deal_next_stream_data = True
        _has_deal_trace_id = False
        _has_deal_parent_id = False
        _has_deal_trace_level = False

        while _i < len(paras):
            # 如果有传入字节数组，进行处理
            if not _has_deal_bytes and request.has_para_bytes and paras[_i][1] == '{$SIMPLEGRPC_BYTES$}':
                paras[_i][1] = request.para_bytes
                _has_deal_bytes = True

            # 整理参数
            if paras[_i][0] == '':
                # 没有key的情况
                _call_para_str = '%s, %s[%s][1]' % (_call_para_str, paras_var_name, str(_i))
            else:
                # 有key
                if not _has_deal_next_stream_data and paras[_i][0] == 'has_next_stream_data':
                    # 如果外部已经传入这个标识，以远程函数的调用为准
                    _has_deal_next_stream_data = True
                    _call_para_str = '%s, %s=%s[%s][1]' % (
                        _call_para_str, paras[_i][0], paras_var_name, str(_i))
                elif not _has_deal_trace_id and paras[_i][0] == 'trace_id':
                    # 以这次调用的为准
                    _has_deal_trace_id = True
                    _call_para_str = '%s, trace_id=%s.trace_id' % (
                        _call_para_str, trace_info_var_name)
                elif not _has_deal_parent_id and paras[_i][0] == 'parent_id':
                    _has_deal_parent_id = True
                    _call_para_str = '%s, parent_id=%s.call_id' % (
                        _call_para_str, trace_info_var_name)
                elif not _has_deal_trace_level and paras[_i][0] == 'trace_level':
                    _has_deal_trace_level = True
                    _call_para_str = '%s, trace_level=%s.trace_level' % (
                        _call_para_str, trace_info_var_name)
                else:
                    _call_para_str = '%s, %s=%s[%s][1]' % (
                        _call_para_str, paras[_i][0], paras_var_name, str(_i))

            _i = _i + 1

        # 调用链参数传入
        if _is_function_has_var_parameter:
            if not _has_deal_next_stream_data:
                _call_para_str = '%s, has_next_stream_data=%s' % (
                    _call_para_str, str(has_next_stream_data))
            if not _has_deal_trace_id:
                _call_para_str = '%s, trace_id=%s.trace_id' % (_call_para_str, trace_info_var_name)
            if not _has_deal_parent_id:
                _call_para_str = '%s, parent_id=%s.call_id' % (_call_para_str, trace_info_var_name)
            if not _has_deal_trace_level:
                _call_para_str = '%s, trace_level=%s.trace_level' % (
                    _call_para_str, trace_info_var_name)

        # 去掉开始的', '
        if len(_call_para_str) > 0 and _call_para_str[0] == ',':
            _call_para_str = _call_para_str[2:]

        return _call_para_str

    def _dealing_num_addon(self, add_num):
        """
        修改正在处理报文数量（通过所控制一致性）

        @param {int} add_num - 增加或减少的值，减少传入复数即可
        """
        self._dealing_num_lock.acquire()
        try:
            self._dealing_num = self._dealing_num + add_num
        finally:
            self._dealing_num_lock.release()


class SimpleGRpcServicerUnion(msg_pb2_grpc.SimpleGRpcServiceServicer):
    """
    Servicer服务的整合对象（用于将多个Servicer整合为一个Servicer）
    """

    #############################
    # 构造函数
    #############################
    def __init__(self, servicer_list: dict, **kwargs):
        """
        初始化Servicer服务的整合对象

        @param {dict} servicer_list=None - gRpc处理逻辑对象清单(SimpleGRpcServicer)，如果不传会自动创建一个默认的
            key值为Servicer名，value值为Servicer对象
        """
        # 内部参数
        self.servicer_list = servicer_list
        self._mapping = dict()  # key为要执行的服务名，value为Servicer名

        # 执行映射处理, 主要是通过服务名获取到Servicer名
        for _servicer_name in self.servicer_list:
            _servicer = self.servicer_list[_servicer_name]
            for _name in _servicer._simple_service_list.keys():
                self._mapping[_name] = _servicer_name
            for _name in _servicer._client_side_stream_service_list.keys():
                self._mapping[_name] = _servicer_name
            for _name in _servicer._server_side_stream_service_list.keys():
                self._mapping[_name] = _servicer_name
            for _name in _servicer._bidirectional_stream_service_list.keys():
                self._mapping[_name] = _servicer_name

    #############################
    # 重载GRpc入口函数，作为路由
    #############################

    def GRpcCallSimple(self, request, context):
        """
        简单模式(Simple)gRPC的标准接入服务接口

        @param {msg_pb2.RpcRequest} request - 请求对象，与msg.proto定义一致,
          例如可通过request.para_json获取要执行的函数的入参信息
        @param {grpc.ServicerContext} context - 服务端的上下文,
          具体定义@see https://grpc.github.io/grpc/python/grpc.html#service-side-context

        @retrun {msg_pb2.RpcResponse} - 返回调用结果信息
        """
        _service = request.service_name
        if _service not in self._mapping.keys():
            # 没有找到服务名
            return self._response_service_not_found_error(_service)

        # 路由处理
        return self.servicer_list[self._mapping[_service]].GRpcCallSimple(
            request, context
        )

    def GRpcCallClientSideStream(self, request_iterator, context):
        """
        客户端流模式(ClientSideStream)gRPC的标准接入服务接口

        @param {iterator} request_iterator - 请求对象迭代器（msg_pb2.RpcRequest），单个对象与msg.proto定义一致,
          例如可通过request.para_json获取要执行的函数的入参信息
        @param {grpc.ServicerContext} context - 服务端的上下文,
          具体定义@see https://grpc.github.io/grpc/python/grpc.html#service-side-context

        @retrun {msg_pb2.RpcResponse} - 返回调用结果信息
        """
        request = next(request_iterator)
        _service = request.service_name
        if _service not in self._mapping.keys():
            # 没有找到服务名
            return self._response_service_not_found_error(_service)

        # 由于查出来对象，需要重新生成迭代对象返回处理
        def _request_iterator_generater(first_obj, iterator_obj):
            # 先把第一个返回
            yield first_obj
            # 返回剩余的对象
            for next_obj in iterator_obj:
                yield next_obj

        _request_iterator = _request_iterator_generater(request, request_iterator)

        # 路由处理
        return self.servicer_list[self._mapping[_service]].GRpcCallClientSideStream(
            _request_iterator, context
        )

    def GRpcCallServerSideStream(self, request, context):
        """
        服务器流模式(ServerSideStream)gRPC的标准接入服务接口

        @param {msg_pb2.RpcRequest} request - 请求对象，与msg.proto定义一致,
          例如可通过request.para_json获取要执行的函数的入参信息
        @param {grpc.ServicerContext} context - 服务端的上下文,
          具体定义@see https://grpc.github.io/grpc/python/grpc.html#service-side-context

        @retrun {iterator} - 返回调用结果信息（msg_pb2.RpcResponse）的迭代器（iterator）
        """
        _service = request.service_name
        if _service not in self._mapping.keys():
            # 没有找到服务名
            yield self._response_service_not_found_error(_service)

        # 路由处理
        for _ret_obj in self.servicer_list[self._mapping[_service]].GRpcCallServerSideStream(
            request, context
        ):
            yield _ret_obj

    def GRpcCallBidirectionalStream(self, request_iterator, context):
        """
        双向流模式(BidirectionalStream)gRPC的标准接入服务接口

        @param {iterator} request_iterator - 请求对象迭代器（msg_pb2.RpcRequest），单个对象与msg.proto定义一致,
          例如可通过request.para_json获取要执行的函数的入参信息
        @param {grpc.ServicerContext} context - 服务端的上下文,
          具体定义@see https://grpc.github.io/grpc/python/grpc.html#service-side-context

        @retrun {iterator} - 返回调用结果信息（msg_pb2.RpcResponse）的迭代器（iterator）
        """
        request = next(request_iterator)
        _service = request.service_name
        if _service not in self._mapping.keys():
            # 没有找到服务名
            yield self._response_service_not_found_error(_service)

        # 由于查出来对象，需要重新生成迭代对象返回处理
        def _request_iterator_generater(first_obj, iterator_obj):
            # 先把第一个返回
            yield first_obj
            # 返回剩余的对象
            for next_obj in iterator_obj:
                yield next_obj

        _request_iterator = _request_iterator_generater(request, request_iterator)

        # 路由处理
        for _ret_obj in self.servicer_list[self._mapping[_service]].GRpcCallBidirectionalStream(
            _request_iterator, context
        ):
            yield _ret_obj

    def GRpcCallHealthCheck(self, request, context):
        """
        自定义的健康检查服务

        @param {msg_pb2.HealthRequest} request - 请求对象，与msg.proto定义一致,
          例如可通过request.para_json获取要执行的函数的入参信息
        @param {grpc.ServicerContext} context - 服务端的上下文,
          具体定义@see https://grpc.github.io/grpc/python/grpc.html#service-side-context

        @retrun {msg_pb2.HealthResponse} - 返回调用结果信息
        """
        return msg_pb2.HealthResponse(status=msg_pb2.HealthResponse.SERVING)

    #############################
    # 内部函数
    #############################

    def _response_service_not_found_error(self, service_name: str):
        """
        返回服务不存在的报错

        @param {str} service_name - 服务名

        @param {msg_pb2.RpcResponse} - 错误结果对象
        """
        _call_result = CResult(code='11403', i18n_msg_paras=(service_name, ))
        _return_obj = SimpleGRpcTools.generate_response_obj(
            return_json='',
            has_return_bytes=False,
            return_bytes=None,
            call_code=_call_result.code,
            call_msg=_call_result.i18n_msg_id,
            call_error=_call_result.error,
            call_msg_para=_call_result.i18n_msg_paras
        )

        return _return_obj


class SimpleGRpcServer(SimpleServerFW):
    """
    Simple gRPC服务器类,用于管理和启动gRPC服务
    通过重载SimpleServerFW类实现服务的启停管理

    """
    #############################
    # 内部变量
    #############################
    _grpc_server = None  # 服务对象
    _grpc_servicer_list = None  # 服务端处理对象列表，key为服务名，value为服务的servicer
    _grpc_servicer_union = None  # 服务端服务集合对象，支持多个服务端处理对象的集合处理
    _grpc_health_servicer = None  # 服务端健康检查对象
    _server_opts = None  # 启动参数
    _server_credentials = None  # 服务端凭证
    _temp_server_opts = None  # 临时的启动参数，仅在启动时用于临时存储变量
    _temp_servicer_list = None  # 临时的服务端处理对象列表，仅在启动时用于临时存储变量

    #############################
    # 静态函数
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
        @param {bytes} root_certificates=None - 客户端反向认证时（验证客户端证书）的客户端根证书，即客户端的公钥证书文件
            多客户端反向认证时，客户端证书应基于同一个根证书签发，这里使用根证书的公钥证书文件
            with open('ca.crt', 'rb') as f:
                root_certificates = f.read()
        @param {type?} options=None - An optional list of key-value pairs (channel args in gRPC runtime) to configure the channel
            [('grpc.max_send_message_length', 最大发送消息长度), ('grpc.max_receive_message_length', 最大接收消息长度)]
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

    #############################
    # 公共函数
    #############################
    def __init__(self, logger=None, server_status_info_fun=None, self_tag='',
                 log_level=logging.INFO, server_name='SimpleGRpcService',
                 is_auto_load_i18n=True, trans_file_path='', trans_file_prefix='',
                 trans_file_encoding='utf-8'):
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
        @param {int} log_level=logging.INFO - 处理中正常日志的输出登记级别，默认为INFO，如果不想输出
            过多日志可以设置为DEBUG
        @param {string} server_name='NetService' - 服务名，记录日志使用
        @param {bool} is_auto_load_i18n=True - 是否自动加载i18n字典，如果继承类有自己的字典，可以重载__init__函数实现装载
        @param {string} trans_file_path='' - 要加载的i18n字典文件路径，如果填空代表程序运行的当前路径
        @param {string} trans_file_prefix='' - 要加载的i18n字典文件前缀
        @param {string} trans_file_encoding='utf-8' - 要加载的i18n字典文件的字符编

        """
        self._grpc_servicer_list = dict()  # 服务端处理对象列表，key为服务名，value为服务的servicer
        SimpleServerFW.__init__(self, logger=logger, server_status_info_fun=server_status_info_fun,
                                self_tag=self_tag, log_level=log_level, server_log_prefix='LIS',
                                server_name=server_name, is_auto_load_i18n=is_auto_load_i18n,
                                trans_file_path=trans_file_path,
                                trans_file_prefix=trans_file_prefix,
                                trans_file_encoding=trans_file_encoding)

    def start_server(self, server_opts, servicer_list=None, is_wait=False):
        """
        启动GRpc服务(重载start_server函数)

        @param {object} server_opts - 启动服务器参数, 定义如下:
            server_opts.port - 监听端口
            server_opts.max_workers - 最大处理线程数
        @param {dict} servicer_list=None - gRpc处理逻辑对象清单(SimpleGRpcServicer)，如果不传会自动创建一个默认的
            key值为Servicer名，value值为Servicer对象
        @param {bool} is_wait=False - 是否等待服务启动完成后再退出

        @returns {CResult} - 启动结果，result.code：'00000'-成功，'21401'-服务不属于停止状态，不能启动，其他-异常

        """
        self._temp_server_opts = server_opts
        self._temp_servicer_list = servicer_list
        # 尝试启动服务
        return SimpleServerFW.start_server(self, is_wait=is_wait)

    def set_service_status(self, servicer_name, status_code):
        """
        设置服务可用状态

        @param {string} servicer_name - 要设置的服务名，如果为''则代表设置所有服务
        @param {health_pb2.HealthCheckResponse.ServingStatus} status_code - 要设置的服务状态，可取的值包括：
            health_pb2.HealthCheckResponse.SERVING : 服务中
            health_pb2.HealthCheckResponse.NOT_SERVING : 停止服务
            health_pb2.HealthCheckResponse.UNKNOWN : 未知
            health_pb2.HealthCheckResponse.SERVICE_UNKNOWN : 服务状态未知
        """
        if self._server_opts.is_health_check:
            if servicer_name == '':
                # 设置所有服务
                for _servicer_name in self._grpc_servicer_list.keys():
                    self._grpc_health_servicer.set(_servicer_name, status_code)
            else:
                # 设置单个服务
                self._grpc_health_servicer.set(servicer_name, status_code)

    def get_service_status(self, servicer_name=''):
        """
        获取服务可用状态

        @param {string} servicer_name - 要获取的服务名，如果为''则代表获取所有服务状态汇总

        @return {health_pb2.HealthCheckResponse.ServingStatus} - 获取到的状态值
            注意：如果传入的服务名为空，则会检查所有服务的状态，只要有一个不可用，都会返回不可用的状态，返回的优先级别为
            health_pb2.HealthCheckResponse.UNKNOWN、health_pb2.HealthCheckResponse.SERVICE_UNKNOWN、
            health_pb2.HealthCheckResponse.NOT_SERVING、health_pb2.HealthCheckResponse.SERVING
            注意：如果服务名不存在，返回grpc.StatusCode.NOT_FOUND

        """
        if servicer_name == '':
            # 通过递归方式获取所有服务的状态
            _all_status = grpc.StatusCode.NOT_FOUND
            for _servicer_name in self._grpc_servicer_list.keys():
                _status = self.get_service_status(_servicer_name)
                if _status == health_pb2.HealthCheckResponse.UNKNOWN:
                    # 已经是最差的状态了
                    _all_status = _status
                    break
                elif _all_status in (grpc.StatusCode.NOT_FOUND, health_pb2.HealthCheckResponse.SERVING):
                    # 比最好状态差，直接赋值
                    _all_status = _status
                elif _all_status == health_pb2.HealthCheckResponse.NOT_SERVING and _status in (
                    health_pb2.HealthCheckResponse.SERVICE_UNKNOWN
                ):
                    _all_status = _status
                else:
                    # 其他情况不处理
                    pass

            # 循环检查完成
            return _all_status
        else:
            # 获取指定服务状态
            with self._grpc_health_servicer._lock:
                _status = self._grpc_health_servicer._server_status.get(servicer_name)
                if _status is None:
                    return grpc.StatusCode.NOT_FOUND
                else:
                    return _status

    #############################
    # 重载服务启动和关闭函数
    #############################
    def _start_server_self(self, tid):
        """
        重载自定义的服务启动处理函数

        @param {int} tid - 线程id

        @returns {CResult} - 启动结果:
            result.code ：'00000'-成功，其他值为失败
            result.server_info ：启动成功后的服务对象，用于传递到后续的服务处理函数

        """
        _result = CResult(code='00000')  # 成功
        _result.server_info = NullObj()
        with ExceptionTool.ignored_cresult(
            _result,
            logger=self._logger,
            self_log_msg='[%s-STARTING][NAME:%s]%s: ' % (
                self._server_log_prefix, self._server_name,
                _('start service error')),
            force_log_level=logging.ERROR
        ):
            # 初始化临时变量
            self._server_opts = self._temp_server_opts
            if self._temp_servicer_list is None or len(self._temp_servicer_list) == 0:
                # 创建一个默认的服务servicer，使用服务器端的logger
                self._grpc_servicer_list.clear()
                self._grpc_servicer_list['SimpleGRpcServicer'] = SimpleGRpcServicer()
                self._grpc_servicer_list['SimpleGRpcServicer'].logger = self._logger
            else:
                self._grpc_servicer_list = self._temp_servicer_list

            # 初始化GRPC服务
            self._grpc_server = grpc.server(
                futures.ThreadPoolExecutor(max_workers=self._server_opts.max_workers),  # 线程池参数
                maximum_concurrent_rpcs=self._server_opts.max_connect,  # 最大连接数
                options=self._server_opts.options,
                compression=self._server_opts.compression,
                handlers=self._server_opts.handlers,
                interceptors=self._server_opts.interceptors
            )

            # 注册健康检查服务
            self._grpc_health_servicer = HealthServicer()
            if self._server_opts.is_health_check:
                health_pb2_grpc.add_HealthServicer_to_server(
                    self._grpc_health_servicer, self._grpc_server)

            # 向服务注册处理对象
            _grpc_servicer_union = SimpleGRpcServicerUnion(self._grpc_servicer_list)
            msg_pb2_grpc.add_SimpleGRpcServiceServicer_to_server(
                _grpc_servicer_union, self._grpc_server
            )
            for _servicer_name in self._grpc_servicer_list.keys():
                # msg_pb2_grpc.add_SimpleGRpcServiceServicer_to_server(
                #    self._grpc_servicer_list[_servicer_name], self._grpc_server)
                # 设置服务状态，由于未启动，设置为未知
                self.set_service_status(_servicer_name, health_pb2.HealthCheckResponse.UNKNOWN)

            # 设置监听服务
            _server_host_str = ('%s:%s' % (self._server_opts.ip, self._server_opts.port))
            if self._server_opts.is_use_ssl:
                # 使用SSL加密传输
                self._server_credentials = grpc.ssl_server_credentials(
                    self._server_opts.private_key_certificate_chain_pairs,
                    root_certificates=self._server_opts.root_certificates,
                    require_client_auth=(self._server_opts.root_certificates is not None)
                )
                self._grpc_server.add_secure_port(_server_host_str, self._server_credentials)
            else:
                # 非加密方式访问
                self._grpc_server.add_insecure_port(_server_host_str)

            self._grpc_server.start()  # 启动服务

            # 启动后是否自动对外提供服务
            if self._server_opts.auto_service_when_started:
                self.set_service_status('', health_pb2.HealthCheckResponse.SERVING)

        # 返回处理结果
        _result.server_info = None
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
            # 停止前先将服务状态值为不可用，让其他服务不再访问
            self.set_service_status('', health_pb2.HealthCheckResponse.NOT_SERVING)
            # 检查是否有正在处理的报文
            for _name in self._grpc_servicer_list.keys():
                _servicer = self._grpc_servicer_list[_name]
                if hasattr(_servicer, 'dealing_num') and _servicer.dealing_num > 0:
                    # 还有报文没有处理完
                    _result.is_finished = False
                    break

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
            # 停止服务
            self._grpc_server.stop(0)

            # 停止完成更新状态为未知
            self.set_service_status('', health_pb2.HealthCheckResponse.UNKNOWN)

        # 返回处理结果
        return


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    # 打印版本信息
    print(('模块名：%s  -  %s\n'
           '作者：%s\n'
           '发布日期：%s\n'
           '版本：%s' % (__MOUDLE__, __DESCRIPT__, __AUTHOR__, __PUBLISH__, __VERSION__)))

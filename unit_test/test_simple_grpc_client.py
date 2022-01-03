#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""
测试simple_grpc的异步日志
@module test_simple_grpc_asyn_log
@file test_simple_grpc_asyn_log.py
"""

import os
import random
import sys
import threading
import time
import copy
import unittest
import json
import queue
import grpc
from grpc_health.v1 import health_pb2
# 根据当前文件路径将包路径纳入，在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir)))
from HiveNetLib.generic import CResult, NullObj
import HiveNetLib.simple_log as simple_log
from HiveNetLib.base_tools.string_tool import StringTool
from HiveNetLib.base_tools.file_tool import FileTool
from HiveNetLib.base_tools.debug_tool import DebugTool
from HiveNetLib.base_tools.run_tool import RunTool
from HiveNetLib.simple_grpc.grpc_server import SimpleGRpcServer, SimpleGRpcServicer
from HiveNetLib.simple_grpc.grpc_tool import SimpleGRpcTools, EnumCallMode
from HiveNetLib.base_tools.call_chain_tool import CallChainTool
from HiveNetLib.simple_grpc.grpc_client import SimpleGRpcConnection


_TEMP_DIR = os.path.abspath(os.path.dirname(__file__) + '/' +
                            '../test_data/temp/simple_grpc_log/').replace('\\', '/')


TEST_FLAG = {
    'test_simple_tool_call': True,
    'test_simple_tool_call_tsl': True,
    'test_stream': True,
    'test_health_check': True,
    'test_error': True,
    'test_mutiple_thread': True
}

TEMP_QUEUE = queue.Queue()

#############################
# 通用比较函数
#############################


def compare_object_by_json(object1, object2, logger=None):
    """
    比较两个基本对象类型（通过转换为json串）

    @param {object} object1 - 要比较的对象1
    @param {object} object2 - 要比较的对象2
    @param {logging.Logger} logger=None - 输出日志对象，不一样的时候输出

    @return {bool} - 比较是否通过，如果不通过将输出两个对象
    """
    _json1 = StringTool.object_to_json(object1)
    _json2 = StringTool.object_to_json(object2)
    if _json1 == _json2:
        return True
    else:
        # 输出日志
        if logger is None:
            print('object1: ' + _json1)
            print('object2: ' + _json2)
        else:
            logger.error('object1: %s\nobject2: %s' % (_json1, _json2))
        return False


#############################
# 测试同一个连接的多线程处理
#############################
def service_mutiple_thread(a: float) -> float:
    """
    测试一个连接的多线程

    @param {float} a - 等待的秒数

    @returns {float} - 直接返回等待的秒数
    """
    _sleep = random.random()
    time.sleep(_sleep)
    return a

#############################
# 测试输入值
#############################


def service_simple_call_para(a, b, *args, c=10, d={'d1': 'd1value'}, **kwargs):
    """
    测试简单调用，直接返回传入的参数(数组形式)
    """
    # 要清除调用链内容
    _dict = copy.deepcopy(kwargs)
    if 'trace_id' in _dict.keys():
        del _dict['trace_id']
        del _dict['parent_id']
        del _dict['trace_level']
    return [a, b, args, c, d, _dict]


def client_simple_call_para(a, b, *args, c=10, d={'d1': 'd1value'}, **kwargs):
    """
    测试简单调用，直接返回参数
    """
    # 转换参数
    _para_values = RunTool.get_current_function_parameter_values(is_simple_mode=True)
    _para_obj = SimpleGRpcTools.parameters_to_json(_para_values)
    _req_obj = SimpleGRpcTools.generate_request_obj(
        service_name='service_simple_call_para', para_json=_para_obj.para_json,
        has_para_bytes=_para_obj.has_para_bytes, para_bytes=_para_obj.para_bytes
    )
    # 发送请求, 默认使用全局的日志对象
    _connect_para = SimpleGRpcConnection.generate_connect_para(
        conn_str='127.0.0.1:50051', servicer_name='servicer_simple_call',
        test_on_connect=True, test_use_health_check=False
    )
    _connection = SimpleGRpcConnection(_connect_para)
    _cresult = _connection.call(_req_obj)
    _connection.close()
    _cresult.return_obj = SimpleGRpcTools.json_to_object_by_para_mapping(
        _cresult.return_json,
        'client_simple_call_para'
    )
    return _cresult


def service_simple_call_no_para_no_return():
    """
    测试简单调用，无入参无返回
    """
    return


def client_simple_call_no_para_no_return():
    """
    测试简单调用，直接返回参数
    """
    # 转换参数
    _para_values = RunTool.get_current_function_parameter_values(is_simple_mode=True)
    _para_obj = SimpleGRpcTools.parameters_to_json(_para_values)
    _req_obj = SimpleGRpcTools.generate_request_obj(
        service_name='service_simple_call_no_para_no_return', para_json=_para_obj.para_json,
        has_para_bytes=_para_obj.has_para_bytes, para_bytes=_para_obj.para_bytes
    )
    # 发送请求, 默认使用全局的日志对象
    _connect_para = SimpleGRpcConnection.generate_connect_para(
        conn_str='127.0.0.1:50051'
    )
    _connection = SimpleGRpcConnection(_connect_para)
    _cresult = _connection.call(_req_obj)
    _connection.close()
    _cresult.return_obj = SimpleGRpcTools.json_to_object_by_para_mapping(
        _cresult.return_json,
        'client_simple_call_no_para_no_return'
    )
    return _cresult


#############################
# 测试返回值
#############################
def service_simple_call_return(obj):
    """
    测试简单调用，直接返回传入的参数(单对象形式)
    """
    return obj


def client_simple_call_return(obj):
    """
    测试简单调用，直接返回参数
    """
    # 转换参数
    _para_values = RunTool.get_current_function_parameter_values(is_simple_mode=True)
    _para_obj = SimpleGRpcTools.parameters_to_json(_para_values, is_support_bytes=True)
    _req_obj = SimpleGRpcTools.generate_request_obj(
        service_name='service_simple_call_return', para_json=_para_obj.para_json,
        has_para_bytes=_para_obj.has_para_bytes, para_bytes=_para_obj.para_bytes
    )
    # 发送请求, 默认使用全局的日志对象
    _connect_para = SimpleGRpcConnection.generate_connect_para(
        conn_str='127.0.0.1:50051'
    )
    _connection = SimpleGRpcConnection(_connect_para)
    _cresult = _connection.call(_req_obj)
    _connection.close()
    _cresult.return_obj = SimpleGRpcTools.json_to_object_by_para_mapping(
        _cresult.return_json,
        'client_simple_call_return'
    )
    return _cresult


#############################
# 测试抛出异常情况
#############################
def service_simple_throw_excepiton():
    """
    测试简单调用，抛出异常
    """
    return 1 / 0


def client_simple_throw_excepiton():
    """
    测试简单调用，抛出异常
    """
    # 转换参数
    _para_values = RunTool.get_current_function_parameter_values(is_simple_mode=True)
    _para_obj = SimpleGRpcTools.parameters_to_json(_para_values)
    _req_obj = SimpleGRpcTools.generate_request_obj(
        service_name='service_simple_throw_excepiton', para_json=_para_obj.para_json,
        has_para_bytes=_para_obj.has_para_bytes, para_bytes=_para_obj.para_bytes
    )
    # 发送请求, 默认使用全局的日志对象
    _connect_para = SimpleGRpcConnection.generate_connect_para(
        conn_str='127.0.0.1:50051'
    )
    _connection = SimpleGRpcConnection(_connect_para)
    _cresult = _connection.call(_req_obj)
    _connection.close()
    _cresult.return_obj = SimpleGRpcTools.json_to_object_by_para_mapping(
        _cresult.return_json,
        'client_simple_throw_excepiton'
    )
    return _cresult


#############################
# 测试超时情况
#############################
def service_simple_overtime():
    """
    测试简单调用，超时
    """
    # 5秒后返回
    time.sleep(5)
    return True


#############################
# 测试TSL认证模式
# 需先生成相应证书文件（域名为localhost）
# --执行前先进入HiveNetLib/test_data/simple_grpc/路径
# --创建CA根证书（自签名证书）
# --生成rsa私钥文件，使用des3加密文件（密码111111）
# openssl genrsa -passout pass:111111 -des3 -out ca.key 4096
# --通过私钥生成签名证书
# openssl req -passin pass:111111 -new -x509 -days 365 -key ca.key -out ca.crt -subj "/CN=localhost"
#
# --创建服务器证书
# --生成rsa私钥文件
# openssl genrsa -passout pass:111111 -des3 -out server.key 4096
# --通过私钥生成签名证书签名请求文件
# openssl req -passin pass:111111 -new -key server.key -out server.csr -subj "/CN=localhost"
# --由CA根证书签发根据请求文件签发证书
# openssl x509 -req -passin pass:111111 -days 365 -in server.csr -CA ca.crt -CAkey ca.key -set_serial 01 -out server.crt
# --私钥文件由加密转为非加密
# openssl rsa -passin pass:111111 -in server.key -out server.key
#
# --创建客户端证书
# openssl genrsa -passout pass:111111 -des3 -out client.key 4096
# openssl req -passin pass:111111 -new -key client.key -out client.csr -subj "/CN=localhost"
# openssl x509 -passin pass:111111 -req -days 365 -in client.csr -CA ca.crt -CAkey ca.key -set_serial 01 -out client.crt
# openssl rsa -passin pass:111111 -in client.key -out client.key
#
# --对私钥进行pkcs8编码
# openssl pkcs8 -topk8 -nocrypt -in client.key -out client.pem
# openssl pkcs8 -topk8 -nocrypt -in server.key -out server.pem
#############################
def client_simple_call_para_double_tsl(a, b, *args, c=10, d={'d1': 'd1value'}, **kwargs):
    """
    测试简单调用，进行双向认证（服务端验证客户端证书，客户端验证服务端证书）
    """
    # 转换参数
    _para_values = RunTool.get_current_function_parameter_values(is_simple_mode=True)
    _para_obj = SimpleGRpcTools.parameters_to_json(_para_values)
    _req_obj = SimpleGRpcTools.generate_request_obj(
        service_name='service_simple_call_para', para_json=_para_obj.para_json,
        has_para_bytes=_para_obj.has_para_bytes, para_bytes=_para_obj.para_bytes
    )
    # 发送请求
    with open(_TEMP_DIR + '/../../simple_grpc/client.pem', 'rb') as f:
        _client_private_key = f.read()
    with open(_TEMP_DIR + '/../../simple_grpc/client.crt', 'rb') as f:
        _client_certificate_chain = f.read()
    with open(_TEMP_DIR + '/../../simple_grpc/server.crt', 'rb') as f:
        _root_certificates = f.read()

    # 发送请求, 默认使用全局的日志对象
    _connect_para = SimpleGRpcConnection.generate_connect_para(
        ip='localhost', port=50052, is_use_ssl=True,
        root_certificates=_root_certificates,
        private_key=_client_private_key,
        certificate_chain=_client_certificate_chain
    )
    _connection = SimpleGRpcConnection(_connect_para)
    _cresult = _connection.call(_req_obj)
    _connection.close()

    _cresult.return_obj = SimpleGRpcTools.json_to_object_by_para_mapping(
        _cresult.return_json,
        'client_simple_call_para'
    )
    return _cresult


def client_simple_call_para_server_tsl(a, b, *args, c=10, d={'d1': 'd1value'}, **kwargs):
    """
    测试简单调用，进行单向认证（客户端验证服务端证书）
    """
    # 转换参数
    _para_values = RunTool.get_current_function_parameter_values(is_simple_mode=True)
    _para_obj = SimpleGRpcTools.parameters_to_json(_para_values)
    _req_obj = SimpleGRpcTools.generate_request_obj(
        service_name='service_simple_call_para', para_json=_para_obj.para_json,
        has_para_bytes=_para_obj.has_para_bytes, para_bytes=_para_obj.para_bytes
    )
    # 发送请求
    with open(_TEMP_DIR + '/../../simple_grpc/server.crt', 'rb') as f:
        _root_certificates = f.read()

    # 发送请求, 默认使用全局的日志对象
    _connect_para = SimpleGRpcConnection.generate_connect_para(
        ip='localhost', port=50053, is_use_ssl=True,
        root_certificates=_root_certificates
    )
    _connection = SimpleGRpcConnection(_connect_para)
    _cresult = _connection.call(_req_obj)
    _connection.close()

    _cresult.return_obj = SimpleGRpcTools.json_to_object_by_para_mapping(
        _cresult.return_json,
        'client_simple_call_para'
    )
    return _cresult


#############################
# 测试流模式处理
#############################
def service_client_side_stream(a, b, *args, **kwargs):
    """
    测试客户端流模式的服务端应用
    """
    _ret_obj = [a, b, args, kwargs]
    _json_str = StringTool.object_to_json(_ret_obj)
    print('call service_client_side_stream return : ' + _json_str)
    return [a, b, args, kwargs]


def client_side_stream_single_request(a, b, *args, **kwargs):
    """
    客户端流模式，产生请求对象的函数
    """
    # 转换参数
    _para_values = RunTool.get_current_function_parameter_values(is_simple_mode=True)
    _para_obj = SimpleGRpcTools.parameters_to_json(_para_values)
    _req_obj = SimpleGRpcTools.generate_request_obj(
        service_name='service_client_side_stream', para_json=_para_obj.para_json,
        has_para_bytes=_para_obj.has_para_bytes, para_bytes=_para_obj.para_bytes
    )
    return _req_obj


def client_side_stream_generator():
    """
    客户端流模式，客户端流请求生成器
    """
    _i = 0
    while True:
        yield client_side_stream_single_request(_i, 'b' + str(_i))
        _i = _i + 1
        if _i > 4:
            break


def client_side_stream_call():
    """
    客户端流模式，真正调用服务端的函数
    """
    # 发送请求, 默认使用全局的日志对象
    _connect_para = SimpleGRpcConnection.generate_connect_para(
        ip='127.0.0.1', port=50051
    )
    _connection = SimpleGRpcConnection(_connect_para)
    _cresult = _connection.call(client_side_stream_generator(),
                                call_mode=EnumCallMode.ClientSideStream)
    _connection.close()

    _cresult.return_obj = SimpleGRpcTools.json_to_object_by_para_mapping(
        _cresult.return_json,
        'service_client_side_stream'
    )
    return _cresult


def service_server_side_stream(a, b, *args, **kwargs):
    """
    测试服务端流模式的服务端应用
    """
    _ret_obj = [a, b, args, kwargs]
    _json_str = StringTool.object_to_json(_ret_obj)
    print('call service_server_side_stream return : ' + _json_str)
    _i = 0
    while True:
        yield [a, b, 'server+' + str(_i), args, kwargs]
        _i = _i + 1
        if _i > 4:
            break


def server_side_stream_call(a, b, *args, **kwargs):
    """
    服务端流模式，真正调用服务端的函数
    """
    # 转换参数
    _para_values = RunTool.get_current_function_parameter_values(is_simple_mode=True)
    _para_obj = SimpleGRpcTools.parameters_to_json(_para_values)
    _req_obj = SimpleGRpcTools.generate_request_obj(
        service_name='service_server_side_stream', para_json=_para_obj.para_json,
        has_para_bytes=_para_obj.has_para_bytes, para_bytes=_para_obj.para_bytes
    )

    # 发送请求, 默认使用全局的日志对象
    _connect_para = SimpleGRpcConnection.generate_connect_para(
        ip='127.0.0.1', port=50051
    )
    _connection = SimpleGRpcConnection(_connect_para)
    _cresult_iterator = _connection.call(_req_obj,
                                         call_mode=EnumCallMode.ServerSideStream)
    _ret = True
    for _cresult in _cresult_iterator:
        if not _cresult.is_success():
            _ret = False

    _connection.close()

    return _ret


def service_bidirectional_stream(a, b, *args, **kwargs):
    """
    测试双向流模式的服务端应用
    """
    _ret_obj = [a, b, args, kwargs]
    _json_str = StringTool.object_to_json(_ret_obj)
    print('call service_bidirectional_stream get : ' + _json_str)
    if a == 'one':
        # 一个请求一个回应的方式，只回复单个内容
        yield [a, b, 'one-->', args, kwargs]
    elif a == 'end':
        # 收到请求，只要不是最后一个，回应None
        if b == 'end':
            yield [a, b, 'end-->', args, kwargs]
        else:
            yield None
    else:
        # 其他情况，一个回应多个
        _i = 0
        while True:
            yield [a, b, 'bidirectional+' + str(_i), args, kwargs]
            _i = _i + 1
            if _i > 4:
                break


def bidirectional_stream_single_request(a, b, *args, **kwargs):
    """
    双向流模式，产生请求对象的函数
    """
    # 转换参数
    _para_values = RunTool.get_current_function_parameter_values(is_simple_mode=True)
    _para_obj = SimpleGRpcTools.parameters_to_json(_para_values)
    _req_obj = SimpleGRpcTools.generate_request_obj(
        service_name='service_bidirectional_stream', para_json=_para_obj.para_json,
        has_para_bytes=_para_obj.has_para_bytes, para_bytes=_para_obj.para_bytes
    )
    return _req_obj


def bidirectional_stream_one_by_one_generator():
    """
    双向流模式，客户端流请求生成器
    """
    _i = 0
    while True:
        yield bidirectional_stream_single_request('one', 'b' + str(_i))
        _resp_obj = TEMP_QUEUE.get()
        if _resp_obj is not None:
            # 注意队列一定要先传入一个值，否则会因为队列等待一直不发出请求
            print('bidirectional_stream_one_by_one client get: ' + str(_resp_obj))
        _i = _i + 1
        if _i > 4:
            break


def server_bidirectional_stream_call_one_by_one():
    """
    双向流模式，客户端处理，一个请求对应一个响应的情况
    通过队列传递交互传递参数
    """
    # 清空队列
    TEMP_QUEUE.queue.clear()
    TEMP_QUEUE.put(None)

    # 处理
    _connect_para = SimpleGRpcConnection.generate_connect_para(
        ip='127.0.0.1', port=50051
    )
    _connection = SimpleGRpcConnection(_connect_para)
    _cresult_iterator = _connection.call(
        bidirectional_stream_one_by_one_generator(),
        call_mode=EnumCallMode.BidirectionalStream)
    for _cresult in _cresult_iterator:
        # 放入队列
        s = _cresult.return_json
        TEMP_QUEUE.put(s)
        if not _cresult.is_success():
            return False

    _connection.close()
    return True


def bidirectional_stream_one_by_n_generator():
    """
    双向流模式，客户端流请求生成器
    """
    _i = 0
    while True:
        yield bidirectional_stream_single_request('a', 'one->n+' + str(_i))
        _i = _i + 1
        if _i > 4:
            break


def server_bidirectional_stream_call_one_by_n():
    """
    双向流模式，客户端处理，一个请求对应多个响应的情况
    """
    # 发送请求, 默认使用全局的日志对象
    _connect_para = SimpleGRpcConnection.generate_connect_para(
        ip='127.0.0.1', port=50051
    )
    _connection = SimpleGRpcConnection(_connect_para)
    _cresult_iterator = _connection.call(
        bidirectional_stream_one_by_n_generator(),
        call_mode=EnumCallMode.BidirectionalStream)

    _ret = True
    for _cresult in _cresult_iterator:
        # 打印
        print('bidirectional_stream_one_by_n client get: ' + _cresult.return_json)
        if not _cresult.is_success():
            _ret = False

    _connection.close()
    return _ret


def bidirectional_stream_n_by_one_generator():
    """
    双向流模式，客户端流请求生成器
    """
    _i = 0
    while True:
        yield bidirectional_stream_single_request('end', 'end b+' + str(_i))
        _i = _i + 1
        if _i > 4:
            break
    # 最后一个结束标记
    yield bidirectional_stream_single_request('end', 'end')


def server_bidirectional_stream_call_n_by_one():
    """
    双向流模式，客户端处理，多个请求对应一个响应的情况
    """
    # 发送请求, 默认使用全局的日志对象
    _connect_para = SimpleGRpcConnection.generate_connect_para(
        ip='127.0.0.1', port=50051
    )
    _connection = SimpleGRpcConnection(_connect_para)
    _cresult_iterator = _connection.call(bidirectional_stream_n_by_one_generator(),
                                         call_mode=EnumCallMode.BidirectionalStream)

    _ret = True
    for _cresult in _cresult_iterator:
        # 打印
        print('bidirectional_stream_n_by_one client get: ' + _cresult.return_json)
        if not _cresult.is_success():
            _ret = False

    _connection.close()
    return _ret


class TestSimpleGRpc(unittest.TestCase):
    """
    测试simple_grpc
    """

    @classmethod
    def setUpClass(cls):
        """
        启动测试类执行的初始化，只执行一次
        """
        # 初始化日志类
        DebugTool.set_debug(False)
        try:
            # 删除临时日志
            FileTool.remove_files(path=_TEMP_DIR + '/log/', regex_str='test_case_client*')
        except:
            pass

        _logger_conf = os.path.realpath(os.path.join(
            _TEMP_DIR, os.path.pardir, os.path.pardir, 'simple_grpc/test_simple_grpc.json'
        ))
        cls.logger = simple_log.Logger(
            conf_file_name=_logger_conf,
            logger_name=simple_log.EnumLoggerName.ConsoleAndFile,
            config_type=simple_log.EnumLoggerConfigType.JSON_FILE,
            logfile_path=_TEMP_DIR + '/log/test_case_client.log',
            is_create_logfile_by_day=True,
        )
        cls.logger.setLevelWithHandler(simple_log.DEBUG)

        # 设置json转换对象的参数映射

        # 日志处理函数
        def _asyn_logging_fun(levelno, topic_name, msg):
            print('haha client:%s, %s, %s' % (str(levelno), topic_name, msg))

        # 异步日志
        cls._asyn_logger = CallChainTool.create_call_chain_logger(
            logger=cls.logger,
            asyn_logging=False,
            asyn_logging_fun=_asyn_logging_fun,
            asyn_deal_msg_fun=SimpleGRpcTools.api_call_chain_asyn_deal_msg_fun
        )
        RunTool.set_global_logger(cls._asyn_logger)

        # 服务端处理类，可以多个服务公用
        cls.servicer_simple_call = SimpleGRpcServicer(
            logger=cls._asyn_logger, is_use_global_logger=False
        )
        cls.servicer_simple_call.add_service(
            EnumCallMode.Simple, 'service_simple_call_para', service_simple_call_para)
        cls.servicer_simple_call.add_service(
            EnumCallMode.Simple, 'service_simple_call_no_para_no_return', service_simple_call_no_para_no_return)
        cls.servicer_simple_call.add_service(
            EnumCallMode.Simple, 'service_simple_call_return', service_simple_call_return)
        cls.servicer_simple_call.add_service(
            EnumCallMode.Simple, 'service_simple_throw_excepiton', service_simple_throw_excepiton)
        cls.servicer_simple_call.add_service(
            EnumCallMode.Simple, 'service_simple_overtime', service_simple_overtime)
        cls.servicer_simple_call.add_service(
            EnumCallMode.ClientSideStream, 'service_client_side_stream', service_client_side_stream)
        cls.servicer_simple_call.add_service(
            EnumCallMode.ServerSideStream, 'service_server_side_stream', service_server_side_stream)
        cls.servicer_simple_call.add_service(
            EnumCallMode.BidirectionalStream, 'service_bidirectional_stream', service_bidirectional_stream)
        cls.servicer_simple_call.add_service(
            EnumCallMode.Simple, 'service_mutiple_thread', service_mutiple_thread)

        # 初始化并启动服务，简单服务，无SSL，无服务发现
        cls.server_no_ssl_no_zoo_opts = SimpleGRpcServer.generate_server_opts(
            ip='127.0.0.1',
            port=50051,
            max_workers=10,
            max_connect=100,
            is_health_check=True
        )
        cls.server_no_ssl_no_zoo = SimpleGRpcServer(
            server_name='ServerNoSslNoZoo',
            logger=cls._asyn_logger, log_level=simple_log.INFO)

        cls.server_no_ssl_no_zoo.start_server(
            server_opts=cls.server_no_ssl_no_zoo_opts, servicer_list={
                'servicer_simple_call': cls.servicer_simple_call
            }, is_wait=True
        )

        # 初始化并启动服务，简单服务，无服务发现，TSL双向认证模式
        _private_key_certificate_chain_pair = SimpleGRpcTools.get_private_key_certificate_chain_pair(
            _TEMP_DIR + '/../../simple_grpc/server.pem', _TEMP_DIR + '/../../simple_grpc/server.crt'
        )
        with open(_TEMP_DIR + '/../../simple_grpc/client.crt', 'rb') as f:
            # 根证书
            _root_certificates = f.read()

        cls.server_double_ssl_no_zoo_opts = SimpleGRpcServer.generate_server_opts(
            ip='localhost',
            port=50052,
            max_workers=10,
            max_connect=100,
            is_use_ssl=True,
            private_key_certificate_chain_pairs=(_private_key_certificate_chain_pair, ),
            root_certificates=_root_certificates
        )
        cls.server_double_ssl_no_zoo = SimpleGRpcServer(
            server_name='ServerDoubleSslNoZoo',
            logger=cls._asyn_logger, log_level=simple_log.INFO)
        cls.server_double_ssl_no_zoo.start_server(
            server_opts=cls.server_double_ssl_no_zoo_opts, servicer_list={
                'servicer_simple_call': cls.servicer_simple_call
            }, is_wait=True
        )

        # 初始化并启动服务，简单服务，无服务发现，TSL单向认证模式（仅验证服务端证书）
        cls.server_server_ssl_no_zoo_opts = SimpleGRpcServer.generate_server_opts(
            ip='localhost',
            port=50053,
            max_workers=10,
            max_connect=100,
            is_use_ssl=True,
            private_key_certificate_chain_pairs=(_private_key_certificate_chain_pair, ),
            root_certificates=None
        )
        cls.server_server_ssl_no_zoo = SimpleGRpcServer(
            server_name='ServerServerSslNoZoo',
            logger=cls._asyn_logger, log_level=simple_log.INFO)
        cls.server_server_ssl_no_zoo.start_server(
            server_opts=cls.server_server_ssl_no_zoo_opts,
            servicer_list={
                'servicer_simple_call': cls.servicer_simple_call
            },
            is_wait=True
        )

    @classmethod
    def tearDownClass(cls):
        """
        结束测试类执行的销毁，只执行一次
        """
        # 停止服务，简单服务，无SSL，无服务发现
        cls.server_no_ssl_no_zoo.stop_server()
        cls.server_double_ssl_no_zoo.stop_server()
        cls.server_server_ssl_no_zoo.stop_server()

        # 启动写日志任务
        CallChainTool.start_call_chain_asyn_logging(cls._asyn_logger)

        # 等待日志记录完成
        time.sleep(10)

        CallChainTool.stop_call_chain_asyn_logging(cls._asyn_logger)

    def setUp(self):
        """
        启动测试执行的初始化，每个案例执行一次
        """
        pass

    def tearDown(self):
        """
        结束测试执行的销毁，每个案例执行一次
        """
        pass

    def test_simple_tool_call(self):
        """
        测试简单调用
        """
        if not TEST_FLAG['test_simple_tool_call']:
            return

        print("开始测试简单应用")
        print("测试输入值1-只传位置参数")
        _back_server = service_simple_call_para('a1', 'b1')
        _back_client = client_simple_call_para('a1', 'b1')
        self.assertTrue(_back_client.is_success(),
                        msg='测试输入值1失败，执行RPC失败: code=%s, msg=%s, error=%s, i18n_msg_paras=%s' % (
                            _back_client.code, _back_client.msg, _back_client.error,
                            str(_back_client.i18n_msg_paras)
        ))
        self.assertTrue(
            compare_object_by_json(_back_server, _back_client.return_obj),
            msg='测试输入值1失败, 执行参数不一致'
        )

        print("测试输入值2-传入args和kwargs")
        _back_server = service_simple_call_para(
            'a2', 'b2', 'args1', 'args2', c='C100', kwargs1='kw1', kwargs2='kw2')
        _back_client = client_simple_call_para(
            'a2', 'b2', 'args1', 'args2', c='C100', kwargs1='kw1', kwargs2='kw2')
        self.assertTrue(_back_client.is_success(),
                        msg='测试输入值2失败，执行RPC失败: code=%s, msg=%s, error=%s, i18n_msg_paras=%s' % (
                            _back_client.code, _back_client.msg, _back_client.error,
                            str(_back_client.i18n_msg_paras)
        ))
        self.assertTrue(
            compare_object_by_json(_back_server, _back_client.return_obj),
            msg='测试输入值2失败, 执行参数不一致'
        )

        print("测试输入值3-不传参数")
        _back_server = None
        _back_client = client_simple_call_no_para_no_return()
        self.assertTrue(_back_client.is_success(),
                        msg='测试输入值3失败，执行RPC失败: code=%s, msg=%s, error=%s, i18n_msg_paras=%s' % (
                            _back_client.code, _back_client.msg, _back_client.error,
                            str(_back_client.i18n_msg_paras)
        ))
        self.assertTrue(
            _back_server == _back_client.return_obj,
            msg='测试输入值3失败, 返回值不为None'
        )

        print("测试返回值1-整数")
        _back_server = service_simple_call_return(10)
        _back_client = client_simple_call_return(10)
        self.assertTrue(_back_client.is_success(),
                        msg='测试返回值1失败，执行RPC失败: code=%s, msg=%s, error=%s, i18n_msg_paras=%s' % (
                            _back_client.code, _back_client.msg, _back_client.error,
                            str(_back_client.i18n_msg_paras)
        ))
        self.assertTrue(
            _back_server == _back_client.return_obj,
            msg='测试返回值1失败, 返回值不为10'
        )

        print("测试返回值2-字符串")
        _back_server = service_simple_call_return('str')
        _back_client = client_simple_call_return('str')
        self.assertTrue(_back_client.is_success(),
                        msg='测试返回值2失败，执行RPC失败: code=%s, msg=%s, error=%s, i18n_msg_paras=%s' % (
                            _back_client.code, _back_client.msg, _back_client.error,
                            str(_back_client.i18n_msg_paras)
        ))
        self.assertTrue(
            _back_server == _back_client.return_obj,
            msg='测试返回值2失败, 返回值不为str'
        )

        print("测试返回值3-浮点数")
        _back_server = service_simple_call_return(19.1)
        _back_client = client_simple_call_return(19.1)
        self.assertTrue(_back_client.is_success(),
                        msg='测试返回值3失败，执行RPC失败: code=%s, msg=%s, error=%s, i18n_msg_paras=%s' % (
                            _back_client.code, _back_client.msg, _back_client.error,
                            str(_back_client.i18n_msg_paras)
        ))
        self.assertTrue(
            _back_server == _back_client.return_obj,
            msg='测试返回值3失败, 返回值不为19.1'
        )

        print("测试返回值4-数组对象")
        _back_server = service_simple_call_return((1, 'tru'))
        _back_client = client_simple_call_return((1, 'tru'))
        self.assertTrue(_back_client.is_success(),
                        msg='测试返回值4失败，执行RPC失败: code=%s, msg=%s, error=%s, i18n_msg_paras=%s' % (
                            _back_client.code, _back_client.msg, _back_client.error,
                            str(_back_client.i18n_msg_paras)
        ))
        self.assertTrue(
            compare_object_by_json(_back_server, _back_client.return_obj),
            msg='测试返回值4失败, 数组对比失败'
        )

        print("测试返回值5-字节数组")
        _bytes = '测试返回值5-字节转换'.encode('utf-8')
        _back_client = client_simple_call_return(_bytes)
        self.assertTrue(_back_client.is_success(),
                        msg='测试返回值5失败，执行RPC失败: code=%s, msg=%s, error=%s, i18n_msg_paras=%s' % (
                            _back_client.code, _back_client.msg, _back_client.error,
                            str(_back_client.i18n_msg_paras)
        ))
        self.assertTrue(
            _back_client.return_obj == '{$SIMPLEGRPC_BYTES$}' and _back_client.has_return_bytes and str(
                _back_client.return_bytes, 'utf-8') == '测试返回值5-字节转换',
            msg='测试返回值5失败, 字符串对比失败: %s - %s, %s, %s - %s' % (
                _back_client.return_obj, str(_back_client.return_obj == '{$SIMPLEGRPC_BYTES$}'),
                str(_back_client.has_return_bytes),
                str(_back_client.return_bytes,
                    'utf-8'), str(str(_back_client.return_bytes, 'utf-8') == '测试返回值5-字节转换')
            )
        )

        print("测试抛出异常1")
        _back_client = client_simple_throw_excepiton()
        self.assertTrue(_back_client.code == '21008' and _back_client.error == '<class \'ZeroDivisionError\'>',
                        msg='测试抛出异常1失败，执行RPC失败: code=%s, msg=%s, error=%s, i18n_msg_paras=%s' % (
                            _back_client.code, _back_client.msg, _back_client.error,
                            str(_back_client.i18n_msg_paras)
                        ))

    def test_simple_tool_call_tsl(self):
        """
        测试简单调用(TSL模式)
        """
        if not TEST_FLAG['test_simple_tool_call_tsl']:
            return

        print("测试简单调用(TSL模式)")
        print("测试双向TSL验证")
        _back_server = service_simple_call_para('a1', 'b1')
        _back_client = client_simple_call_para_double_tsl('a1', 'b1')
        self.assertTrue(_back_client.is_success(),
                        msg='测试双向TSL验证失败，执行RPC失败: code=%s, msg=%s, error=%s, i18n_msg_paras=%s' % (
                            _back_client.code, _back_client.msg, _back_client.error,
                            str(_back_client.i18n_msg_paras)
        ))
        self.assertTrue(
            compare_object_by_json(_back_server, _back_client.return_obj),
            msg='测试双向TSL验证失败, 执行参数不一致'
        )

        print("测试单向TSL验证")
        _back_server = service_simple_call_para('a1', 'b1')
        _back_client = client_simple_call_para_server_tsl('a1', 'b1')
        self.assertTrue(_back_client.is_success(),
                        msg='测试单向TSL验证失败，执行RPC失败: code=%s, msg=%s, error=%s, i18n_msg_paras=%s' % (
                            _back_client.code, _back_client.msg, _back_client.error,
                            str(_back_client.i18n_msg_paras)
        ))
        self.assertTrue(
            compare_object_by_json(_back_server, _back_client.return_obj),
            msg='测试单向TSL验证失败, 执行参数不一致'
        )

    def test_stream(self):
        """
        测试流模式
        """
        if not TEST_FLAG['test_stream']:
            return

        print("测试流模式")
        print("测试流模式 - 客户端流模式")
        _back_client = client_side_stream_call()
        self.assertTrue(_back_client.is_success(),
                        msg='客户端流模式，执行RPC失败: code=%s, msg=%s, error=%s, i18n_msg_paras=%s' % (
                            _back_client.code, _back_client.msg, _back_client.error,
                            str(_back_client.i18n_msg_paras)
        ))

        print("测试流模式 - 服务端流模式")
        _back_client = server_side_stream_call('a', 'b', 'c', 'd', x=1, y=2)
        self.assertTrue(_back_client, msg='服务端流模式执行失败')

        print("测试流模式 - 双向流模式-一发一收")
        _back_client = server_bidirectional_stream_call_one_by_one()
        self.assertTrue(_back_client, msg='双向流模式执行失败-一发一收')

        print("测试流模式 - 双向流模式-一发多收")
        _back_client = server_bidirectional_stream_call_one_by_n()
        self.assertTrue(_back_client, msg='双向流模式执行失败-一发多收')

        print("测试流模式 - 双向流模式-多发一收")
        _back_client = server_bidirectional_stream_call_n_by_one()
        self.assertTrue(_back_client, msg='双向流模式执行失败-多发一收')

    def test_health_check(self):
        """
        测试服务健康状态
        """
        if not TEST_FLAG['test_health_check']:
            return

        print("测试服务健康状态")
        _connect_para = SimpleGRpcConnection.generate_connect_para(
            ip='127.0.0.1', port=50051, servicer_name='servicer_simple_call', test_use_health_check=True
        )
        _connection = SimpleGRpcConnection(_connect_para)

        print("测试服务健康状态 - 服务中")
        _resp_obj = _connection.test()
        # _resp_obj = SimpleGRpcTools.health_check(_connect_para, 'servicer_simple_call')
        self.assertTrue(_resp_obj.status == health_pb2.HealthCheckResponse.SERVING,
                        '测试服务健康状态失败 - 服务中')

        print("测试服务健康状态 - 停止服务")
        self.server_no_ssl_no_zoo.set_service_status('servicer_simple_call',
                                                     health_pb2.HealthCheckResponse.NOT_SERVING)
        _resp_obj = _connection.test()
        # _resp_obj = SimpleGRpcTools.health_check(_connect_para, 'servicer_simple_call')
        self.assertTrue(_resp_obj.status == health_pb2.HealthCheckResponse.NOT_SERVING,
                        '测试服务健康状态失败 - 停止服务')

        # 恢复服务
        self.server_no_ssl_no_zoo.set_service_status('servicer_simple_call',
                                                     health_pb2.HealthCheckResponse.SERVING)

        _connection.close()

        print("测试服务健康状态 - 服务不存在")
        _connect_para = SimpleGRpcConnection.generate_connect_para(
            ip='127.0.0.2', port=50051, servicer_name='servicer_simple_call'
        )
        _connection = SimpleGRpcConnection(_connect_para)
        _resp_obj = _connection.test()
        # _resp_obj = SimpleGRpcTools.health_check(_connect_para, 'servicer_simple_call')
        self.assertTrue(_resp_obj.status == health_pb2.HealthCheckResponse.UNKNOWN,
                        '测试服务健康状态失败 - 服务不存在')

    def test_error(self):
        """
        测试错误信息
        """
        if not TEST_FLAG['test_error']:
            return

        print("测试错误信息")
        print("测试错误信息 - 连接失败")
        _connect_para = SimpleGRpcConnection.generate_connect_para(
            ip='127.0.0.1', port=60051
        )
        _connection = SimpleGRpcConnection(_connect_para)
        _cresult = _connection.call(SimpleGRpcTools.generate_request_obj('test'))
        _connection.close()
        self.assertTrue(
            _cresult.code == '20408' and grpc.StatusCode.UNAVAILABLE.name == _cresult.i18n_msg_paras[0],
            '测试错误信息失败 - 连接失败 '
        )

        print("测试错误信息 - 服务名不存在")
        _connect_para = SimpleGRpcConnection.generate_connect_para(
            ip='127.0.0.1', port=50051
        )
        _connection = SimpleGRpcConnection(_connect_para)
        _cresult = _connection.call(SimpleGRpcTools.generate_request_obj('test', ''))
        _connection.close()
        self.assertTrue(
            _cresult.code == '11403',
            '测试错误信息失败 - 服务名不存在 '
        )

        print("测试错误信息 - 超时")
        _connect_para = SimpleGRpcConnection.generate_connect_para(
            ip='127.0.0.1', port=50051, timeout=0.1
        )
        _connection = SimpleGRpcConnection(_connect_para)
        _cresult = _connection.call(SimpleGRpcTools.generate_request_obj('service_simple_overtime'))
        _connection.close()
        self.assertTrue(
            _cresult.code == '30403',
            '测试错误信息失败 - 超时'
        )

    #############################
    # 测试同一个连接多线程并发
    #############################
    def test_mutiple_thread(self):
        if not TEST_FLAG['test_mutiple_thread']:
            return

        print("测试同一个连接多线程并发")

        # 建立连接
        _connect_para = SimpleGRpcConnection.generate_connect_para(
            conn_str='127.0.0.1:50051'
        )
        _connection = SimpleGRpcConnection(_connect_para)

        # 创建多线程执行
        _result = list()
        for _i in range(80):
            _result.append(False)
            _call_thread = threading.Thread(
                target=self._mutiple_thread_fun,
                args=(_i, _connection, _result),
                name='Thread-gRpc-call'
            )
            _call_thread.setDaemon(True)
            _call_thread.start()

        # 等待线程执行完成
        time.sleep(20)
        _connection.close()

        # 检查结果
        for _res_i in _result:
            if not _res_i:
                self.assertTrue(False, '测试同一个连接多线程并发失败')

    def _mutiple_thread_fun(self, i, connect, result: list):
        """
        多线程处理
        """
        _i = i + 1

        # 参数处理
        _para_obj = SimpleGRpcTools.parameters_to_json([['', _i]], is_support_bytes=True)
        _req_obj = SimpleGRpcTools.generate_request_obj(
            service_name='service_mutiple_thread', para_json=_para_obj.para_json,
            has_para_bytes=_para_obj.has_para_bytes, para_bytes=_para_obj.para_bytes
        )

        # 通知外面执行是否成功
        result[i] = False

        # 访问服务
        _cresult: CResult = connect.call(_req_obj)

        self.assertTrue(
            _cresult.is_success(), msg='_mutiple_thread_fun [%d] error: %s' % (i, str(_cresult))
        )

        self.assertTrue(
            _cresult.return_json == str(_i), msg='_mutiple_thread_fun [%d] return error: %s' % (i, str(_cresult.return_json))
        )

        # 通知外面执行是否成功
        result[i] = True


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    unittest.main()

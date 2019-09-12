#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""
测试simple_grpc的异步日志
@module test_simple_grpc_asyn_log
@file test_simple_grpc_asyn_log.py
"""

import os
import sys
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
from HiveNetLib.generic import NullObj
import HiveNetLib.simple_log as simple_log
from HiveNetLib.base_tools.string_tool import StringTool
from HiveNetLib.base_tools.file_tool import FileTool
from HiveNetLib.base_tools.debug_tool import DebugTool
from HiveNetLib.base_tools.run_tool import RunTool
from HiveNetLib.simple_grpc.grpc_server import SimpleGRpcServer, SimpleGRpcServicer
from HiveNetLib.simple_grpc.grpc_tool import SimpleGRpcTools, EnumCallMode
from HiveNetLib.base_tools.call_chain_tool import CallChainTool
from HiveNetLib.simple_grpc.grpc_client import SimpleGRpcConnection, SimpleGRpcConnectionPool


_TEMP_DIR = os.path.abspath(os.path.dirname(__file__) + '/' +
                            '../test_data/temp/simple_grpc_log/').replace('\\', '/')


TEST_FLAG = {
    'test_simple_tool_call': True,
    'test_simple_tool_call_tsl': True,
    'test_stream': True,
    'test_health_check': True,
    'test_error': True
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


def get_client_simple_call_para(a, b, *args, c=10, d={'d1': 'd1value'}, **kwargs):
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
    return _req_obj


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

        cls.logger = simple_log.Logger(
            conf_file_name=_TEMP_DIR + '/../../simple_grpc/test_simple_grpc.json',
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
            logger=None, is_use_global_logger=False
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

    @classmethod
    def tearDownClass(cls):
        """
        结束测试类执行的销毁，只执行一次
        """
        # 停止服务，简单服务，无SSL，无服务发现
        cls.server_no_ssl_no_zoo.stop_server()

        # 启动写日志任务
        CallChainTool.start_call_chain_asyn_logging(cls._asyn_logger)

        # 等待日志记录完成
        time.sleep(5)

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

    def test_connect_pool(self):
        """
        测试连接池
        """
        print("开始测试连接池")

        _connect_para = SimpleGRpcConnection.generate_connect_para(
            conn_str='127.0.0.1:50051', servicer_name='servicer_simple_call',
            test_on_connect=False, test_use_health_check=False
        )
        # 建立连接池
        _pool = SimpleGRpcConnectionPool(
            _connect_para, name='ConnectionPool', maxsize=3, minsize=0, realse_free_time=5,
            test_on_get=True, test_on_free=True, test_while_idle=True,
            test_idle_time=5, validation_query='',
            get_connection_timeout=1, logger=self._asyn_logger, init_break_if_connect_error=True
        )

        print("测试连接池-获取连接并执行")
        # 尝试获取连接
        _connection = _pool.get_connection()
        _back_server = service_simple_call_para('a1', 'b1')
        _req_obj = get_client_simple_call_para('a1', 'b1')
        _back_client = _connection.call(_req_obj)
        _back_client.return_obj = SimpleGRpcTools.json_to_object_by_para_mapping(
            _back_client.return_json,
            'client_simple_call_para'
        )

        self.assertTrue(_back_client.is_success(),
                        msg='测试连接池-获取连接并执行失败，执行RPC失败: code=%s, msg=%s, error=%s, i18n_msg_paras=%s' % (
                            _back_client.code, _back_client.msg, _back_client.error,
                            str(_back_client.i18n_msg_paras)
        ))
        self.assertTrue(
            compare_object_by_json(_back_server, _back_client.return_obj),
            msg='测试连接池-获取连接并执行, 执行参数不一致'
        )

        print('测试连接池-获取连接超时')
        _c1 = _pool.get_connection()
        _c2 = _pool.get_connection()

        try:
            _c3 = _pool.get_connection()
            self.assertTrue(False, msg='测试连接池-获取连接超时失败，应抛出超时')
        except TimeoutError:
            pass
        except Exception as e:
            self.assertTrue(False, msg='测试连接池-获取连接超时失败，未期望的异常:%s' % str(e))

        self.assertTrue(3 == _pool.current_size, msg='测试连接池-获取连接超时-当前连接池大小错误：%d' %
                        _pool.current_size)

        print('测试连接池-释放连接')
        _pool.free_connection(_connection)
        _c3 = _pool.get_connection()  # 这样c3可用获取连接并使用
        self.assertTrue(3 == _pool.current_size, msg='测试连接池-释放连接-当前连接池大小错误：%d' %
                        _pool.current_size)

        print('测试连接池-自动释放连接')
        _pool.free_connection(_c1)
        _pool.free_connection(_c2)
        _pool.free_connection(_c3)
        time.sleep(10)
        self.assertTrue(0 == _pool.current_size, msg='测试连接池-自动释放连接-当前连接池大小错误：%d' %
                        _pool.current_size)


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    unittest.main()

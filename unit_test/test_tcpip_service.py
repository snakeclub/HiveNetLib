#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""
测试TcpIP服务
@module test_tcpip_service
@file test_tcpip_service.py
"""

import os
import sys
import time
import unittest
# 根据当前文件路径将包路径纳入，在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir)))
from HiveNetLib.net_service.tcpip_service import TcpIpService
import HiveNetLib.simple_log as simple_log
from HiveNetLib.base_tools.string_tool import StringTool
from HiveNetLib.base_tools.file_tool import FileTool
from HiveNetLib.base_tools.debug_tool import DebugTool


_TEST_DATA_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), os.path.pardir, 'test_data')
)


_TEMP_DIR = os.path.abspath(os.path.dirname(__file__) + '/' +
                            '../test_data/temp/tcpip_service_log/').replace('\\', '/')


class TestTcpIpService(unittest.TestCase):
    """
    测试TcpIpService类
    """

    # 服务端处理函数定义
    @classmethod
    def server_status_info_fun(cls, server_status, result):
        cls.logger.log(
            simple_log.INFO,
            "[服务端]" + result.self_tag + "服务状态变更：" +
            str(server_status) +
            "   结果code：" +
            str(result.code) +
            "  描述：" +
            result.msg
        )
        return

    @classmethod
    def server_connect_deal_fun(cls, thread_id, server_opts, net_info, self_tag):
        cls.logger.log(
            simple_log.INFO,
            "[服务端" +
            self_tag +
            "][" + str(thread_id) +
            "]收到客户端连接：" +
            StringTool.format_obj_property_str(deal_obj=net_info, is_deal_subobj=True)
        )

        # 获取客户端发送的信息，先获取前4个字节
        _read_result = TcpIpService.recv_data(net_info, {'recv_len': 4})
        if _read_result.code != '00000':
            # 获取失败
            cls.logger.log(simple_log.INFO, ("[服务端]获取客户端数据报文头失败，关闭连接：" +
                                             str(_read_result.code) + "-" + _read_result.msg))
            TcpIpService.close_connect(net_info)
            return

        _next_read = int.from_bytes(_read_result.data, byteorder='big', signed=False)
        cls.logger.log(simple_log.INFO, "[服务端]获取到客户端4个字节的后续数据长度：" + str(_next_read))

        # 获取后面的数据
        _read_result = TcpIpService.recv_data(net_info, {'recv_len': _next_read})
        if _read_result.code != '00000':
            # 获取失败
            cls.logger.log(simple_log.INFO, ("[服务端]获取客户端数据报文体失败，关闭连接：" +
                                             str(_read_result.code) + "-" + _read_result.msg))
            TcpIpService.close_connect(net_info)
            return

        _read_str = str(_read_result.data, "utf-8")
        cls.logger.log(simple_log.INFO, "[服务端]获取到客户端报文体数据：" + _read_str)

        if _read_str == "servernoresponse":
            # 隔30秒不响应
            time.sleep(30)

        # 返回内容，先组包
        _ret_str = "处理成功"
        _send_body = bytes(_ret_str, "utf-8")
        _send_head = len(_send_body).to_bytes(4, byteorder='big', signed=False)

        # 发送报文头
        _send_result = TcpIpService.send_data(net_info, _send_head, {})
        if _send_result.code != '00000':
            cls.logger.log(simple_log.INFO, ("[服务端]返回客户端数据报文头失败，关闭连接："
                                             + str(_send_result.code) + "-" + _send_result.msg))
            TcpIpService.close_connect(net_info)
            return

        cls.logger.log(simple_log.INFO, "[服务端]返回客户端4个字节的后续数据长度：" + str(len(_send_body)))
        _send_result = TcpIpService.send_data(net_info, _send_body, {})

        if _send_result.code != '00000':
            cls.logger.log(simple_log.INFO, ("[服务端]返回客户端数据报文体失败，关闭连接："
                                             + str(_send_result.code) + "-" + _send_result.msg))
            TcpIpService.close_connect(net_info)
            return
        cls.logger.log(simple_log.INFO, "[服务端]返回客户端报文体数据：" + _ret_str)

        # 处理完成，关闭连接
        _close_result = TcpIpService.close_connect(net_info)
        if _close_result.code != '00000':
            cls.logger.log(simple_log.INFO, ("[服务端]关闭客户端连接失败："
                                             + str(_close_result.code) + "-" + _close_result.msg))

        cls.logger.log(simple_log.INFO, "[服务端]关闭客户端连接")

    # 客户端发送代码
    def _send_text(self, net_info, str_data):
        # 准备要发送的内容
        _send_body = bytes(str_data, "utf-8")
        _send_head = len(_send_body).to_bytes(4, byteorder='big', signed=False)

        # 发送报文头
        _result = TcpIpService.send_data(net_info=net_info, data=_send_head, send_para={})
        if _result.code != '00000':
            self.logger.log(simple_log.INFO, "[客户端]向服务器发送数据报文头失败，关闭连接：" + '\n'.join(
                ['%s:%s' % item for item in _result.__dict__.items()]))
            return

        self.logger.log(simple_log.INFO, "[客户端]向服务器发送4个字节的后续数据长度：" + str(len(_send_body)))
        _result = TcpIpService.send_data(net_info, _send_body, {})
        if _result.code != '00000':
            self.logger.log(simple_log.INFO, "[客户端]向服务器发送数据报文体失败，关闭连接：" + '\n'.join(
                ['%s:%s' % item for item in _result.__dict__.items()]))
            return
        self.logger.log(simple_log.INFO, "[客户端]向服务器发送数据报文体数据：" + str_data)

        # 获取返回值
        _result = TcpIpService.recv_data(net_info, {'recv_len': 4})
        if not _result.is_success():
            # 获取失败
            self.logger.log(simple_log.INFO, "[客户端]获取服务器端数据报文头失败，关闭连接：" + '\n'.join(
                ['%s:%s' % item for item in _result.__dict__.items()]))
            return
        _next_read = int.from_bytes(_result.data, byteorder='big', signed=False)
        self.logger.log(simple_log.INFO, "[客户端]获取到服务器端4个字节的后续数据长度：" + str(_next_read),
                        )
        # 获取后面的数据
        _result = TcpIpService.recv_data(net_info, {'recv_len': _next_read})
        if not _result.is_success():
            # 获取失败
            self.filelog.log(simple_log.INFO, "[客户端]获取服务器端数据报文体失败，关闭连接：" + '\n'.join(
                ['%s:%s' % item for item in _result.__dict__.items()]))
            return
        _read_str = str(_result.data, "utf-8")
        self.logger.log(simple_log.INFO, "[客户端]获取到服务器端报文体数据：" + _read_str)
        return

    # 整个Test类的开始和结束执行
    @classmethod
    def setUpClass(cls):
        """
        启动测试类执行的初始化，只执行一次
        """
        # 初始化日志类
        DebugTool.set_debug(False)
        try:
            # 删除临时日志
            FileTool.remove_files(path=os.path.join(
                _TEST_DATA_DIR, 'temp/tcpip_service_log/log'), regex_str='test_case*')
        except:
            pass

        cls.logger = simple_log.Logger(
            conf_file_name=os.path.join(_TEST_DATA_DIR, 'tcp_ip_service/test_tcp_ip_service.json'),
            logger_name=simple_log.EnumLoggerName.ConsoleAndFile,
            config_type=simple_log.EnumLoggerConfigType.JSON_FILE,
            logfile_path=os.path.join(_TEST_DATA_DIR, 'temp/tcpip_service_log/log/test_case.log'),
            is_create_logfile_by_day=True,
        )
        cls.logger.setLevelWithHandler(simple_log.DEBUG)

        # 启动服务
        cls.server = TcpIpService(
            logger=cls.logger,
            server_status_info_fun=cls.server_status_info_fun,
            server_connect_deal_fun=cls.server_connect_deal_fun,
            self_tag='UnitTest',
            log_level=simple_log.INFO
        )
        _server_opts = TcpIpService.generate_server_opts()
        _server_opts.ip = "127.0.0.1"
        _server_opts.port = 9512
        cls.server.start_server(server_opts=_server_opts)

    @classmethod
    def tearDownClass(cls):
        """
        结束测试类执行的销毁，只执行一次
        """
        # 关闭服务器连接
        _i = 0
        while _i < 10:
            time.sleep(1)
            _i = _i + 1
        cls.server.stop_server(is_wait=True)

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

    def test_send_text(self):
        """
        测试发送信息
        """
        _i = 0
        while _i < 10:
            time.sleep(0.1)
            _i = _i + 1
        print("案例test_SendText：测试客户端发送信息到服务器端")
        _connect_para = TcpIpService.generate_server_opts()
        _connect_para.ip = "127.0.0.1"
        _connect_para.port = 9512
        _connect_result = TcpIpService.connect_server(_connect_para)
        self.assertTrue(_connect_result.code == '00000',
                        ("[客户端]连接服务器失败："
                         + '\n'.join(['%s:%s' % item for item in _connect_result.__dict__.items()])))

        # 打印连接信息
        self.logger.log(
            simple_log.INFO,
            "[客户端]连接信息：" +
            '\n'.join(['%s:%s' % item for item in _connect_result.net_info.__dict__.items()])
        )

        # 发送数据
        self._send_text(net_info=_connect_result.net_info, str_data="测试案例test_SendText数据")

        # 关闭连接
        _close_result = TcpIpService.close_connect(_connect_result.net_info)
        self.assertTrue(_close_result.code == '00000',
                        ("[客户端]关闭服务器失败："
                         + '\n'.join(['%s:%s' % item for item in _close_result.__dict__.items()])))


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    unittest.main()

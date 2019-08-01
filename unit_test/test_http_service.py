#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""
测试http_service模块
@module test_http_service
@file test_http_service.py
"""

import os
import sys
import time
import unittest
# 根据当前文件路径将包路径纳入，在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir)))
from HiveNetLib.net_service.http_service import HttpService
import HiveNetLib.simple_log as simple_log
from HiveNetLib.base_tools.string_tool import StringTool
from HiveNetLib.base_tools.file_tool import FileTool
from HiveNetLib.base_tools.debug_tool import DebugTool
from HiveNetLib.interface_tool.protocol_msg_http import MsgHTTP
from HiveNetLib.interface_tool.msg_fw import EnumMsgObjType, EnumMsgSRType

_TEMP_DIR = os.path.abspath(os.path.dirname(__file__) + '/' +
                            '../test_data/temp/http_service_log/').replace('\\', '/')


class TestHttpService(unittest.TestCase):
    """
    测试HttpService类
    """

    # 服务端处理函数定义
    def server_status_info_fun(self, server_status, result):
        self.logger.log(
            simple_log.INFO,
            "[服务端]" + result.self_tag + "服务状态变更：" +
            str(server_status) +
            "   结果code：" +
            str(result.code) +
            "  描述：" +
            result.msg
        )
        return

    # 报文处理函数
    def server_http_deal_fun(self, net_info, proto_msg, msg):
        self.logger.log(
            simple_log.INFO,
            "[服务端][处理函数]收到服务请求报文，http报文头: \n%s\n报文体:\n%s\n" % (
                proto_msg.to_str(),
                str(msg, "utf-8")
            )
        )
        # 组织一个异常的返回报文
        _rproto_msg = MsgHTTP('%s 3xx Internal Server Error' % ('HTTP/1.1'),
                              obj_type=EnumMsgObjType.String)
        return (True, _rproto_msg, bytes('Http返回报文', "utf-8"))

    def setUp(self):
        """
        启动测试执行的初始化
        """
        # 初始化日志类
        DebugTool.set_debug(False)
        try:
            # 删除临时日志
            FileTool.remove_files(path=_TEMP_DIR + '/log/', regex_str='test_case*')
        except:
            pass

        self.logger = simple_log.Logger(
            conf_file_name=_TEMP_DIR + '/../../tcp_ip_service/test_http_service.json',
            logger_name=simple_log.EnumLoggerName.ConsoleAndFile,
            config_type=simple_log.EnumLoggerConfigType.JSON_FILE,
            logfile_path=_TEMP_DIR + '/log/test_case.log',
            is_create_logfile_by_day=True
        )
        self.logger.setLevelWithHandler(simple_log.DEBUG)

        # 启动服务
        self.server = HttpService(
            logger=self.logger,
            server_status_info_fun=self.server_status_info_fun,
            self_tag='UnitTest',
            log_level=simple_log.INFO,
            server_http_deal_fun=self.server_http_deal_fun
        )
        _server_opts = HttpService.generate_server_opts()
        _server_opts.ip = "127.0.0.1"
        _server_opts.port = 9513
        self.server.start_server(server_opts=_server_opts)

    def tearDown(self):
        """
        结束测试执行的销毁
        """
        # 关闭服务器连接
        _i = 0
        while _i < 10:
            time.sleep(1)
            _i = _i + 1
        self.server.stop_server(is_wait=True)

    def test_send_text(self):
        """
        测试发送信息
        """
        _i = 0
        while _i < 10:
            time.sleep(0.1)
            _i = _i + 1
        print("案例test_SendText：测试客户端发送信息到服务器端")
        _connect_para = HttpService.generate_server_opts()
        _connect_para.ip = "127.0.0.1"
        _connect_para.port = 9513
        _connect_result = HttpService.connect_server(_connect_para)
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
        _proto_msg = MsgHTTP(
            'my1:my1value\r\nmy2:my2value',
            obj_type=EnumMsgObjType.String,
            **{
                'is_with_first_line': False,
                'msg_sr_type': EnumMsgSRType.Request
            }
        )
        _data = (_proto_msg, bytes('Http发送报文', 'utf-8'))
        _send_result = HttpService.send_data(_connect_result.net_info, _data)
        self.assertTrue(_send_result.code == '00000', '[客户端]发送报文失败：' +
                        '\n'.join(['%s:%s' % item for item in _send_result.__dict__.items()]))

        # 获取返回信息
        _recv_result = HttpService.recv_data(_connect_result.net_info, {})
        self.assertTrue(_recv_result.code == '00000', '[客户端]获取返回报文失败：' +
                        '\n'.join(['%s:%s' % item for item in _send_result.__dict__.items()]))
        print('获取到返回数据：' + HttpService.get_print_str(_recv_result.data[0], _recv_result.data[1]))

        # 关闭连接
        _close_result = HttpService.close_connect(_connect_result.net_info)
        self.assertTrue(_close_result.code == '00000',
                        ("[客户端]关闭服务器失败："
                         + '\n'.join(['%s:%s' % item for item in _close_result.__dict__.items()])))


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    unittest.main()

#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""
测试调用链工具模块
@module test_call_chain_tool
@file test_call_chain_tool.py
"""

import os
import sys
import time
import unittest
# 根据当前文件路径将包路径纳入，在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir)))
from HiveNetLib.base_tools.call_chain_tool import CallChainTool
import HiveNetLib.simple_log as simple_log
from HiveNetLib.base_tools.file_tool import FileTool
from HiveNetLib.generic import CResult
from HiveNetLib.base_tools.run_tool import RunTool
from HiveNetLib.interface_tool.msg_fw import EnumMsgObjType
from HiveNetLib.interface_tool.msg_xml import MsgXML
from HiveNetLib.interface_tool.protocol_msg_http import MsgHTTP
from HiveNetLib.simple_queue import MemoryQueue


__MOUDLE__ = 'test_call_chain_tool'  # 模块名
__DESCRIPT__ = u'测试调用链工具模块'  # 模块描述
__VERSION__ = '0.1.0'  # 版本
__AUTHOR__ = u'黎慧剑'  # 作者
__PUBLISH__ = '2018.09.09'  # 发布日期


_TEMP_DIR = os.path.abspath(os.path.dirname(__file__) + '/' +
                            '../test_data/temp/call_chain_log/').replace('\\', '/')


# 不带任何入参，没有返回出参的函数
@CallChainTool.methon_call_chain(is_use_global_logger=True)
def func_case1_no_para():
    RunTool.get_global_logger().log(simple_log.INFO, 'runing func_case1_no_para')
    time.sleep(0.001)
    return


# 不带任何入参，返回CResult出参的函数
@CallChainTool.methon_call_chain(is_use_global_logger=True, is_print_back=True)
def func_case1_no_para_with_cresult():
    RunTool.get_global_logger().log(simple_log.INFO, 'runing func_case1_no_para_with_cresult')
    time.sleep(0.001)
    _ret = CResult()
    _ret.self_para = [3, 'str']
    return _ret


# 带固定入参的函数
@CallChainTool.methon_call_chain(is_use_global_logger=True, key_para=(0, 1,), print_in_para=(2,), print_out_para=(1,), is_print_back=True)
def func_case1_fix_para(a, b, c):
    RunTool.get_global_logger().log(simple_log.INFO, 'runing func_case1_fix_para(a=%s, b=%s, c=%s)' % (a, b, c))
    time.sleep(0.001)
    return


# 标准输入模式
@CallChainTool.methon_call_chain(is_use_global_logger=True, is_standard_def=True, key_para=(0, 1, 'k1'))
def func_case1_standard(*args, **kwargs):
    RunTool.get_global_logger().log(
        simple_log.INFO,
        'runing func_case1_standard : %s : %s' % (str(args), str(kwargs)))
    time.sleep(0.001)
    return


# 半标准输入模式
@CallChainTool.methon_call_chain(is_use_global_logger=True, key_para=(0, 1, 'k1'))
def func_case1_half_standard(a, b, **kwargs):
    RunTool.get_global_logger().log(
        simple_log.INFO,
        'runing func_case1_half_standard : a=%s, b=%s : %s' % (str(a), str(b), str(kwargs)))
    time.sleep(0.001)
    return


# 嵌套调用，产生调用链
@CallChainTool.methon_call_chain(is_use_global_logger=True, key_para=('k1'))
def func_case1_call_1(a, b, **kwargs):
    RunTool.get_global_logger().log(
        simple_log.INFO,
        'runing func_case1_call_1 : a=%s, b=%s : %s' % (str(a), str(b), str(kwargs)))
    time.sleep(0.001)
    # 执行2
    func_case1_call_2('2a', '2b', '2c', k1=kwargs['k1'])
    # 执行3
    func_case1_call_3(k1=kwargs['k1'])
    return


@CallChainTool.methon_call_chain(is_use_global_logger=True, key_para=('k1'))
def func_case1_call_2(a, b, c, **kwargs):
    RunTool.get_global_logger().log(
        simple_log.INFO,
        'runing func_case1_call_2 : a=%s, b=%s, c=%s: %s' % (str(a), str(b), str(c), str(kwargs)))
    time.sleep(0.001)
    # 执行4
    func_case1_call_4('4a', '4b', '4c', k1=kwargs['k1'])
    return


@CallChainTool.methon_call_chain(is_use_global_logger=True, key_para=('k1'))
def func_case1_call_3(**kwargs):
    RunTool.get_global_logger().log(
        simple_log.INFO,
        'runing func_case1_call_3 : %s' % (str(kwargs)))
    time.sleep(0.001)
    return


@CallChainTool.methon_call_chain(is_use_global_logger=True, key_para=('k1'))
def func_case1_call_4(a, b, c, **kwargs):
    RunTool.get_global_logger().log(
        simple_log.INFO,
        'runing func_case1_call_4 : a=%s, b=%s, c=%s: %s' % (str(a), str(b), str(c), str(kwargs)))
    time.sleep(0.001)
    return


class TestCallChainTool(unittest.TestCase):
    """
    测试CallChainTool类
    """

    def setUp(self):
        """
        启动测试执行的初始化
        """
        # 初始化日志类
        try:
            # 删除临时日志
            FileTool.remove_files(path=_TEMP_DIR + '/log/', regex_str='test_case1*')
        except:
            pass

        # 初始化日志类
        _logger = simple_log.Logger(
            conf_file_name=_TEMP_DIR + '/../../call_chain_tool/test_call_chain.json',
            logger_name=simple_log.EnumLoggerName.ConsoleAndFile,
            config_type=simple_log.EnumLoggerConfigType.JSON_FILE,
            logfile_path=_TEMP_DIR + '/log/test_case1.log',
            is_create_logfile_by_day=True,
        )
        # 设置为全局使用
        RunTool.set_global_logger(_logger)

    def tearDown(self):
        """
        结束测试执行的销毁
        """
        pass

    def test_methon(self):
        """
        测试静态方法方法
        """
        # 不带任何入参的对象
        print('\n不带参数调用')
        func_case1_no_para()
        print('\n\n不带参数有返回结果')
        func_case1_no_para_with_cresult()
        print('\n\n带固定个数输入参数')
        func_case1_fix_para('a-str', 'b-str', 'c-str')
        print('\n\n标准模式')
        func_case1_standard('arg1', 'arg2', k1='kw1', k2='kw2')
        print('\n\n半标准模式')
        func_case1_half_standard('arg1', 'arg2', k1='kw1', k2='kw2')
        print('\n\n调用链执行')
        func_case1_call_1('1a', '1b', k1='testk1')

    def test_api(self):
        """
        aip接口日志测试
        """
        # 报文对象
        _msg = MsgXML(
            '<root><seq>seq00000001</seq><traceid>trace_id_00000000001</traceid><a>av1</a><b>bv1</b><c><c1>c1v1</c1><c2>c2v2</c2></c></root>',
            msg_id='id'
        )
        _proto_msg = MsgHTTP(
            (
                'GET /simple.htm HTTP/1.1\r\n' +
                'Accept: image/gif\r\n' +
                'Accept-Language: zh-cn\r\n' +
                'Accept-Encoding: gzip, deflate\r\n' +
                'Call-Id: call_id_00000001' +
                '\r\n'
            )
        )

        _back_msg = MsgXML(
            '<root><seq>seq00000001</seq><traceid>trace_id_00000000002</traceid><a>av1</a><b>bv1</b><c><c1>c1v1</c1><c2>c2v2</c2></c></root>',
            msg_id='id'
        )

        # 登记发送日志
        CallChainTool.api_call_chain_logging(
            msg=_msg, proto_msg=_proto_msg, logger=None,
            api_mapping={
                'trace_id': ['msg', '/root/traceid', {}],
                'call_id': ['proto_msg', 'Call-Id', {}],
                'SEQ': ['msg', '/root/seq', {}]
            },
            api_call_type='SEND', api_info_type='SEND',
            trace_id=None,  # 不指定可以从报文中获取
            trace_level=1,
            call_id=None,  # 不指定可以从报文中获取
            parent_id='parent_id_demo1',
            logging_head={
                'IP': '127.0.0.1',
                'PORT': '8080',
                'SYS': 'SQL',
                'SEQ': None  # 从api_mapping中获取，注意key要一致
            },
            use=0, error=None, trace_str='',
            is_print_proto_msg=True,
            proto_msg_print_kwargs=dict(),
            is_print_msg=True, msg_print_kwargs=dict(),
            key_para={
                'Key1': ['msg', '/root/a', {}],
                'Key2': ['msg', '/root/c/c2', {}],
                'Key3': ['proto_msg', 'Accept', {}]
            },
            print_in_para={
                'para1': ['msg', '/root/b', {}],
                'para2': ['proto_msg', 'Accept-Encoding', {}]
            },
            is_use_global_logger=True, log_level=simple_log.INFO
        )

        # 登记超时情况
        CallChainTool.api_call_chain_logging(
            msg=_msg, proto_msg=_proto_msg, logger=None,
            api_mapping={
                'SEQ': ['msg', '/root/seq', {}]
            },
            api_call_type='SEND', api_info_type='OT',
            logging_head={
                'SEQ': None
            },
            use=0.1,
            is_use_global_logger=True, log_level=simple_log.INFO
        )

        # 登记异常情况
        CallChainTool.api_call_chain_logging(
            msg=_msg, proto_msg=_proto_msg, logger=None,
            api_mapping={
                'SEQ': ['msg', '/root/seq', {}]
            },
            api_call_type='SEND', api_info_type='EX',
            logging_head={
                'SEQ': None
            },
            use=0.2, error=AttributeError(), trace_str='trace_str info',
            is_use_global_logger=True, log_level=simple_log.INFO
        )

        # 登记返回日志
        CallChainTool.api_call_chain_logging(
            msg=_back_msg, proto_msg=_proto_msg, logger=None,
            api_mapping={
                'SEQ': ['msg', '/root/seq', {}]
            },
            api_call_type='SEND', api_info_type='BACK',
            logging_head={
                'SEQ': None  # 从api_mapping中获取，注意key要一致
            },
            use=0.3,
            is_print_proto_msg=True,
            is_print_msg=True,
            is_use_global_logger=True, log_level=simple_log.INFO
        )


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    unittest.main()

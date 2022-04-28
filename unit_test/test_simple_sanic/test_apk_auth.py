#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

import sys
import os
import time
import json
import requests
import unittest
from sanic.response import text
# 根据当前文件路径将包路径纳入，在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir, os.path.pardir)))
from HiveNetLib.base_tools.run_tool import RunTool
from HiveNetLib.base_tools.test_tool import TestTool
from HiveNetLib.simple_log import Logger
from HiveNetLib.simple_sanic.server import SanicTool, SanicServer
from HiveNetLib.simple_sanic.auth import IPAuth


# 日志配置
_logger_config = {
    'conf_file_name': '',
    'logger_name': 'Console',
    'logfile_path': '',
    'config_type': 'JSON_STR',
    'json_str': """{
                "version": 1,
                "disable_existing_loggers": false,
                "formatters": {
                    "simpleFormatter": {
                        "format": "[%(asctime)s.%(millisecond)s][%(levelname)s][PID:%(process)d][FILE:%(filename)s][FUN:%(funcName)s]%(message)s",
                        "datefmt": "%Y_%m_%d %H:%M:%S"
                    }
                },

                "handlers": {
                    "ConsoleHandler": {
                        "class": "logging.StreamHandler",
                        "level": "DEBUG",
                        "formatter": "simpleFormatter",
                        "stream": "ext://sys.stdout"
                    }
                },

                "loggers": {
                    "Console": {
                        "level": "DEBUG",
                        "handlers": ["ConsoleHandler"]
                    }
                },

                "root": {
                    "level": "DEBUG",
                    "handlers": []
                }
            }
    """,
    'auto_create_conf': False,
    'is_create_logfile_by_day': False,
    'call_fun_level': 0
}


# 日志对象
LOGGER = Logger.create_logger_by_dict(_logger_config)


class TestApi(object):
    """
    测试非实例化调用的API接口
    """
    @staticmethod
    @SanicTool.support_object_resp
    def no_auth_chinese(request):
        return {'a': '中文', '测试': 'no'}

    @classmethod
    def no_auth(cls, request, a: int, b: str, methods=['GET']):
        """
        标题: 没有安全鉴权处理的接口
        详细描述: 详细说明接口

        openapi:
        operationId: fooDots
        tags:
        - one
        - two
        parameters:
          - name: limit
            in: path
            description: How many items to return at one time (max 100)
            required: false
            schema:
            type: integer
            format: int32
        responses:
            '200':
                description: Just some dots
        """
        LOGGER.info('no_auth get request: %d, %s' % (a, b))
        return text('no_auth: {"a":%d, "b":"%s"}' % (a, b))

    @classmethod
    def no_auth_403(cls, request, a: int, b: str, methods=['GET']):
        """
        没有安全鉴权，由处理程序返回指定http状态码的接口
        """
        return text('no_auth_403: {"a":%d, "b":"%s"}' % (a, b), status=403)

    @classmethod
    @SanicTool.support_object_resp
    def no_auth_dict(cls, request, a: int, b: str, methods=['POST'], **kwargs):
        """
        没有安全鉴权并直接返回字典对象, 增加日志记录和支持python对象直接返回的修饰符
        """
        return {"a": a, "b": b}

    @classmethod
    @SanicTool.auth_required(
        get_auth_fun=SanicServer.get_auth_fun, get_auth_para={
            'auth_name': 'IPAuth', 'app_name': 'test_server'}
    )
    def auth_ip(cls, request, a: int, b: str, methods=['GET'], **kwargs):
        """
        进行IP鉴权的接口(不通过)
        """
        return text('{"a":%d, "b":"%s"}' % (a, b))

    @classmethod
    @SanicTool.auth_required(get_auth_fun=SanicServer.get_auth_fun, get_auth_para={'auth_name': 'IPAuthGo', 'app_name': 'test_server'})
    def auth_ip_go(cls, request, a: int, b: str, methods=['GET'], **kwargs):
        """
        进行IP鉴权的接口(通过)
        """
        return text('{"a":%d, "b":"%s"}' % (a, b))


class TestApiInstance(object):
    """
    以实例对象方式的接口对象
    """

    def __init__(self, id: str):
        self.id = id

    def no_auth(self, request, a: int, b: str, methods=['POST'], **kwargs):
        """
        没有安全鉴权的接口
        """
        return text('{"a":%d, "b":"%s", "id":"%s"}' % (a, b, self.id))


class Test(unittest.TestCase):
    # 整个Test类的开始和结束执行
    @classmethod
    def setUpClass(cls):
        # 验证模块
        _ip_auth = IPAuth(
            init_blacklist=['127.0.*.*']
        )
        _ip_auth_go = IPAuth(
        )

        # 实例化的接口对象
        _api_instance = TestApiInstance('instance_id')

        # 服务器配置
        _sever = SanicServer(
            'test_server', server_config={
                'run_config': {
                    'host': '127.0.0.1', 'port': 5000
                },
                'oas': True,
                'oas_config': {
                    'OAS_UI_DEFAULT': 'swagger'
                }

            },
            support_auths={
                'IPAuth': _ip_auth, 'IPAuthGo': _ip_auth_go
            },
            logger=LOGGER
        )

        # 装载api接口
        _sever.add_route_by_class([TestApi, _api_instance])

        # 启动服务
        _sever.start(is_asyn=True)

    @classmethod
    def tearDownClass(cls):
        # 停止服务
        # SanicServer.get_init_server(app_name='test_server').stop()
        pass

    def test_no_auth(self):
        # 等待服务器启动
        _sever: SanicServer = SanicServer.get_init_server(app_name='test_server')
        while _sever.status not in ('running', 'stop'):
            time.sleep(1)

        # 准备初始参数
        _base_url = 'http://127.0.0.1:5000/'

        _tips = "test no_auth_chinese"
        print(_tips)
        _a = 10
        _b = 't10'
        _url = '%sapi/TestApi/no_auth_chinese' % (_base_url, )
        _resp = requests.get(_url)
        self.assertTrue(_resp.status_code == 200, '%s status code error' % _tips)
        _back_str = str(_resp.content, encoding='utf-8')
        _back_json = json.loads(_back_str)
        self.assertTrue(
            TestTool.cmp_dict(_back_json, {'a': '中文', '测试': 'no'}),
            '%s back error: %s' % (_tips, str(_back_json))
        )

        _tips = "test no_auth"
        print(_tips)
        _a = 10
        _b = 't10'
        _url = '%sapi/TestApi/no_auth/%d/%s' % (_base_url, _a, _b)
        _resp = requests.get(_url)
        self.assertTrue(_resp.status_code == 200, '%s status code error' % _tips)
        _back_str = str(_resp.content, encoding='utf-8')
        self.assertTrue(
            _back_str == 'no_auth: {"a":%d, "b":"%s"}' % (_a, _b),
            '%s back error: %s' % (_tips, _back_str)
        )

        _tips = "test no_auth_403"
        print(_tips)
        _a = 11
        _b = 't11'
        _url = '%sapi/TestApi/no_auth_403/%d/%s' % (_base_url, _a, _b)
        _resp = requests.get(_url)
        self.assertTrue(_resp.status_code == 403, '%s status code error' % _tips)
        _back_str = str(_resp.content, encoding='utf-8')
        self.assertTrue(
            _back_str == 'no_auth_403: {"a":%d, "b":"%s"}' % (_a, _b),
            '%s back error: %s' % (_tips, _back_str)
        )

        _tips = "test no_auth_dict"
        print(_tips)
        _a = 12
        _b = 't12'
        _url = '%sapi/TestApi/no_auth_dict/%d/%s' % (_base_url, _a, _b)
        _resp = requests.post(_url)
        # _resp = requests.get(_url)
        self.assertTrue(_resp.status_code == 200, '%s status code error' % _tips)
        _back_str = str(_resp.content, encoding='utf-8')
        _back_dict = json.loads(_back_str)
        self.assertTrue(
            TestTool.cmp_dict(_back_dict, {"a": _a, "b": _b}),
            '%s back error: %s' % (_tips, _back_str)
        )

        _tips = "test instance no_auth"
        print(_tips)
        _a = 12
        _b = 't12'
        _url = '%sapi/TestApiInstance/no_auth/%d/%s' % (_base_url, _a, _b)
        _resp = requests.post(_url)
        # _resp = requests.get(_url)
        self.assertTrue(_resp.status_code == 200, '%s status code error' % _tips)
        _back_str = str(_resp.content, encoding='utf-8')
        _back_dict = json.loads(_back_str)
        self.assertTrue(
            TestTool.cmp_dict(_back_dict, {"a": _a, "b": _b, 'id': 'instance_id'}),
            '%s back error: %s' % (_tips, _back_str)
        )

    def test_auth(self):
        # 等待服务器启动
        _sever: SanicServer = SanicServer.get_init_server(app_name='test_server')
        while _sever.status not in ('running', 'stop'):
            time.sleep(1)

        # 准备初始参数
        _base_url = 'http://127.0.0.1:5000/'

        _tips = "test auth_ip"
        print(_tips)
        _a = 10
        _b = 't10'
        _url = '%sapi/TestApi/auth_ip/%d/%s' % (_base_url, _a, _b)
        _resp = requests.get(_url)
        self.assertTrue(_resp.status_code == 403, '%s status code error' % _tips)
        _back_str = str(_resp.content, encoding='utf-8')
        _back_dict = json.loads(_back_str)
        self.assertTrue(
            TestTool.cmp_dict(_back_dict, {'status': '10409', 'msg': 'IP地址验证失败'}),
            '%s back error: %s' % (_tips, _back_str)
        )

        _tips = "test auth_ip_go"
        print(_tips)
        _a = 10
        _b = 't10'
        _url = '%sapi/TestApi/auth_ip_go/%d/%s' % (_base_url, _a, _b)
        _resp = requests.get(_url)
        self.assertTrue(_resp.status_code == 200, '%s status code error' % _tips)
        _back_str = str(_resp.content, encoding='utf-8')
        _back_dict = json.loads(_back_str)
        self.assertTrue(
            TestTool.cmp_dict(_back_dict, {"a": _a, "b": _b}),
            '%s back error: %s' % (_tips, _back_str)
        )


if __name__ == '__main__':
    unittest.main()

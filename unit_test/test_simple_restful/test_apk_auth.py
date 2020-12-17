#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

import sys
import os
import time
import json
import requests
import unittest
from flask import request, jsonify
# 根据当前文件路径将包路径纳入，在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir, os.path.pardir)))
from HiveNetLib.base_tools.run_tool import RunTool
from HiveNetLib.base_tools.test_tool import TestTool
from HiveNetLib.simple_log import Logger
from HiveNetLib.simple_restful.server import FlaskTool, FlaskServer
from HiveNetLib.simple_restful.auth import IPAuth, AppKeyAuth


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

    @classmethod
    def no_auth(cls, a: int, b: str, methods=['GET']):
        """
        没有安全鉴权处理的接口
        """
        return 'no_auth: {"a":%d, "b":"%s"}' % (a, b)

    @classmethod
    def no_auth_403(cls, a: int, b: str, methods=['GET']):
        """
        没有安全鉴权，由处理程序返回指定http状态码的接口
        """
        return 'no_auth_403: {"a":%d, "b":"%s"}' % (a, b), 403

    @classmethod
    @FlaskTool.log(get_logger_fun=FlaskServer.get_logger_fun, get_logger_para={'app_name': 'test_server'})
    @FlaskTool.support_object_resp
    def no_auth_dict(cls, a: int, b: str, methods=['POST'], **kwargs):
        """
        没有安全鉴权并直接返回字典对象, 增加日志记录和支持python对象直接返回的修饰符
        """
        return {"a": a, "b": b}

    @classmethod
    @FlaskTool.log(get_logger_fun=FlaskServer.get_logger_fun, get_logger_para={'app_name': 'test_server'})
    @FlaskTool.auth_required(
        get_auth_fun=FlaskServer.get_auth_fun, get_auth_para={
            'auth_name': 'IPAuth', 'app_name': 'test_server'}
    )
    def auth_ip(cls, a: int, b: str, methods=['GET'], **kwargs):
        """
        进行IP鉴权的接口(不通过)
        """
        return '{"a":%d, "b":"%s"}' % (a, b)

    @classmethod
    @FlaskTool.log(get_logger_fun=FlaskServer.get_logger_fun, get_logger_para={'app_name': 'test_server'})
    @FlaskTool.auth_required(get_auth_fun=FlaskServer.get_auth_fun, get_auth_para={'auth_name': 'IPAuthGo', 'app_name': 'test_server'})
    def auth_ip_go(cls, a: int, b: str, methods=['GET'], **kwargs):
        """
        进行IP鉴权的接口(通过)
        """
        return '{"a":%d, "b":"%s"}' % (a, b)

    @classmethod
    @FlaskTool.log(get_logger_fun=FlaskServer.get_logger_fun, get_logger_para={'app_name': 'test_server'})
    @FlaskTool.auth_required(
        get_auth_fun=FlaskServer.get_auth_fun, get_auth_para={
            'auth_name': 'AppKeyAuth', 'app_name': 'test_server'}
    )
    def auth_appkey(cls, a: int, b: str, methods=['POST'], **kwargs):
        """
        通过app_key模式鉴权的接口(返回值不加签名验证)
        """
        return '{"a":%d, "b":"%s"}' % (a, b)

    @classmethod
    @FlaskTool.log(get_logger_fun=FlaskServer.get_logger_fun, get_logger_para={'app_name': 'test_server'})
    @FlaskTool.auth_required(
        get_auth_fun=FlaskServer.get_auth_fun, get_auth_para={
            'auth_name': 'AppKeyAuthResp', 'app_name': 'test_server'}
    )
    def auth_appkey_sign_resp(cls, a: int, b: str, methods=['POST'], **kwargs):
        """
        通过app_key模式鉴权的接口(返回值加签名验证)
        """
        _interface_id = request.json.get('interface_id', '')
        return '{"a":%d, "b":"%s", "interface_id": "%s"}' % (a, b, _interface_id)


class TestApiInstance(object):
    """
    以实例对象方式的接口对象
    """

    def __init__(self, id: str):
        self.id = id

    @FlaskTool.log(get_logger_fun=FlaskServer.get_logger_fun, get_logger_para={'app_name': 'test_server'})
    def no_auth(self, a: int, b: str, methods=['POST'], **kwargs):
        """
        没有安全鉴权的接口
        """
        return '{"a":%d, "b":"%s", "id":"%s"}' % (a, b, self.id)


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

        # 响应报文不加签
        _apk_auth = AppKeyAuth(
            algorithm='HMAC-SHA256'
        )

        # 响应报文也加签的情况
        _apk_auth_resp = AppKeyAuth(
            algorithm='HMAC-SHA256', sign_resp=True, interface_id_name='interface_id'
        )

        # 生成app_key, app_secret
        _apk_auth.apk_generate_key_pair('123456')
        _apk_auth_resp.apk_generate_key_pair('654321')

        # 实例化的接口对象
        _api_instance = TestApiInstance('instance_id')

        # 服务器配置
        _sever = FlaskServer(
            'test_server', server_config={
                'debug': True,
                'flask_run': {
                    'host': '127.0.0.1', 'port': 5000
                },
            },
            support_auths={
                'IPAuth': _ip_auth, 'AppKeyAuth': _apk_auth, 'IPAuthGo': _ip_auth_go,
                'AppKeyAuthResp': _apk_auth_resp
            },
            logger=LOGGER
        )

        # 装载api接口
        _sever.add_route_by_class([TestApi, _api_instance])
        print(_sever.app.url_map)

        # 启动服务
        _sever.start(is_asyn=True)

    @classmethod
    def tearDownClass(cls):
        # 停止服务
        FlaskServer.get_init_flask_server(app_name='test_server').stop()

    def test_no_auth(self):
        # 等待服务器启动
        _sever: FlaskServer = FlaskServer.get_init_flask_server(app_name='test_server')
        while _sever.status not in ('running', 'stop'):
            time.sleep(1)

        # 准备初始参数
        _base_url = 'http://127.0.0.1:5000/'

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
        _sever: FlaskServer = FlaskServer.get_init_flask_server(app_name='test_server')
        while _sever.status not in ('running', 'stop'):
            time.sleep(1)

        # 准备初始参数
        _base_url = 'http://127.0.0.1:5000/'
        _headers = {'Content-Type': 'application/json'}

        _auth_appkey: AppKeyAuth = _sever.get_auth_fun(
            auth_name='AppKeyAuth', app_name='test_server')

        _auth_appkey_resp: AppKeyAuth = _sever.get_auth_fun(
            auth_name='AppKeyAuthResp', app_name='test_server')

        _auth_error = AppKeyAuth(
            algorithm='HMAC-SHA256'
        )
        _app_id = '123456'
        _app_id_resp = '654321'
        _auth_error.apk_generate_key_pair(_app_id)

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

        _tips = "test auth_appkey 403"
        print(_tips)
        _a = 10
        _b = 't10'
        _url = '%sapi/TestApi/auth_appkey/%d/%s' % (_base_url, _a, _b)
        _data = {
            'interface_id': '1',
            'app_id': _app_id
        }
        _json = json.dumps(
            _auth_error.sign(_data), ensure_ascii=False
        )
        _resp = requests.post(_url, data=_json, headers=_headers)
        self.assertTrue(_resp.status_code == 403, '%s status code error' % _tips)
        _back_str = str(_resp.content, encoding='utf-8')
        _back_dict = json.loads(_back_str)
        self.assertTrue(
            TestTool.cmp_dict(_back_dict, {'status': '13007', 'msg': '签名检查失败'}),
            '%s back error: %s' % (_tips, _back_str)
        )

        _tips = "test auth_appkey"
        print(_tips)
        _a = 11
        _b = 't11'
        _url = '%sapi/TestApi/auth_appkey/%d/%s' % (_base_url, _a, _b)
        _data = {
            'interface_id': '2',
            'app_id': _app_id
        }
        _json = json.dumps(
            _auth_appkey.sign(_data), ensure_ascii=False
        )
        _resp = requests.post(_url, data=_json, headers=_headers)
        self.assertTrue(_resp.status_code == 200, '%s status code error' % _tips)
        _back_str = str(_resp.content, encoding='utf-8')
        _back_dict = json.loads(_back_str)
        self.assertTrue(
            TestTool.cmp_dict(_back_dict, {'a': _a, 'b': _b}),
            '%s back error: %s' % (_tips, _back_str)
        )

        _tips = "test auth_appkey_sign_resp"
        print(_tips)
        _a = 11
        _b = 't11'
        _url = '%sapi/TestApi/auth_appkey_sign_resp/%d/%s' % (_base_url, _a, _b)
        _data = {
            'interface_id': '3',
            'app_id': _app_id_resp
        }
        _json = json.dumps(
            _auth_appkey_resp.sign(_data), ensure_ascii=False
        )
        _resp = requests.post(_url, data=_json, headers=_headers)
        self.assertTrue(_resp.status_code == 200, '%s status code error' % _tips)
        _back_str = str(_resp.content, encoding='utf-8')
        _back_dict = json.loads(_back_str)
        self.assertTrue(
            _auth_appkey_resp.verify_sign(
                _back_dict) and _back_dict['a'] == _a and _back_dict['b'] == _b and _back_dict['interface_id'] == _data['interface_id'],
            '%s back error: %s' % (_tips, _back_str)
        )


if __name__ == '__main__':
    unittest.main()

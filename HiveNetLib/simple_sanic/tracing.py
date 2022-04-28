#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
# Copyright 2019 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
针对Sanic服务的opentracing实现处理类
注: 核心代码来自sanic-opentracing项目

@module tracing
@file tracing.py
"""

import os
import sys
import json
from typing import Any, Union
sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir, os.path.pardir)))
from HiveNetLib.base_tools.opentracing_tool import OpenTracerFW
# 动态安装包
import HiveNetLib.deps_tool as deps_tool
try:
    from pyjsonpath import JsonPath
except ImportError:
    deps_tool.install_package('pyjsonpath')
    from pyjsonpath import JsonPath
# sanic
try:
    from sanic import Sanic
except ImportError:
    deps_tool.install_package('sanic')
    from sanic import Sanic
from sanic.response import HTTPResponse
from sanic.request import Request
# opentracing
try:
    import opentracing
except ImportError:
    deps_tool.install_package('opentracing')
    import opentracing
from opentracing.ext import tags


__MOUDLE__ = 'tracing'  # 模块名
__DESCRIPT__ = u'针对Sanic服务的opentracing实现'  # 模块描述
__VERSION__ = '0.1.0'  # 版本
__AUTHOR__ = u'黎慧剑'  # 作者
__PUBLISH__ = '2022.01.05'  # 发布日期


class SanicTracer(OpenTracerFW):
    """
    针对Sanic服务的Tracer处理类
    """

    #############################
    # 需要继承类实现的函数（公共函数）
    #############################
    def get_request_obj(self, *args, **kwargs) -> Request:
        """
        获取当前连接的请求对象
        注: 所传入的参数为请求处理函数的入参

        @returns {sanic.request.Request} - 返回请求对象
        """
        req_obj = args[0]
        if type(req_obj) != Request:
            # 针对类实例对象的函数, 第一个参数忽略掉
            req_obj = args[1]
        return args[0]

    def get_request_info(self, request_obj: Request, get_type: str, get_para: str, default: Any = None) -> Any:
        """
        从请求对象获取指定参数值
        注: 需实现类继承并实现具体逻辑

        @param {sanic.request.Request} request_obj - 请求对象
        @param {str} get_type - 获取类型，需至少支持以下3类
            req - 获取请求链接的信息，例如ip, url, method等
            head - 通讯协议的协议头获取信息
            args - 请求参数，从?key1=value1&key2=value2中按key获取
            json - 从报文body内容的json对象获取信息, 参数为JsonPath查找字符串
                例如: $.key1.key2 获取obj[key1][key2]的节点信息
        @param {str} get_para - 要获取信息的具体参数，有实现函数定义参数的具体要求
        @param {Any} default=None - 如果获取不到所返回的默认值

        @returns {Any} - 返回获取到的结果
        """
        if get_type == 'req':
            return getattr(request_obj, get_para, default)
        elif get_type == 'head':
            return request_obj.headers.get(get_para, default)
        elif get_type == 'args':
            return request_obj.args.get(get_para, default)
        elif get_type == 'json':
            _vals = JsonPath(request_obj.json, get_para).load()
            if len(_vals) == 0:
                return default
            else:
                return _vals[0]

        return default

    def get_response_info(self, response_obj: HTTPResponse, get_type: str, get_para: str, default: Any = None) -> Any:
        """
        从响应对象获取指定参数值
        注: 需实现类继承并实现具体逻辑

        @param {sanic.response.HTTPResponse} response_obj - 响应对象
        @param {str} get_type - 获取类型，需至少支持以下3类
            resp - 获取响应协议对象的信息，例如status
            head - 通讯协议的协议头获取信息
            json - 从报文body内容的json对象获取信息, 参数为JsonPath查找字符串
                例如: $.key1.key2 获取obj[key1][key2]的节点信息
        @param {str} get_para - 要获取信息的具体参数，有实现函数定义参数的具体要求
        @param {Any} default=None - 如果获取不到所返回的默认值

        @returns {Any} - 返回获取到的结果
        """
        if get_type == 'resp':
            return getattr(response_obj, get_para, default)
        elif get_type == 'head':
            return response_obj.headers.get(get_para, default)
        elif get_type == 'json':
            # 如果获取不到则创建在响应对象上生成json属性
            body_json = getattr(response_obj, 'body_json', None)
            if body_json is None:
                setattr(response_obj, 'body_json', json.loads(response_obj.body.decode()))
                body_json = getattr(response_obj, 'body_json', None)

            _vals = JsonPath(body_json, get_para).load()
            if len(_vals) == 0:
                return default
            else:
                return _vals[0]

        return default

    def get_protocol_response_error(self, response_obj: HTTPResponse) -> Union[Exception, str]:
        """
        获取通讯协议层面上响应对象的错误对象

        @param {sanic.response.HTTPResponse} response_obj - 响应信息

        @returns {Union[Exception, str]} - 返回通过response_obj判断的错误对象(可以是Exception对象或字符串)
            注: 如果是成功则返回None
        """
        if response_obj.status >= 400:
            return ValueError('get error http status code')
        else:
            # 1xx, 2xx, 3xx 均视为成功
            return None

    def get_request_inject_para(self, request_obj: Request) -> tuple:
        """
        获取新请求对象要注入SpanContext的参数

        @param {sanic.request.Request} request_obj - 新调用请求对象

        @returns {tuple} - 返回 (format, carrier)
        """
        return opentracing.Format.HTTP_HEADERS, request_obj.headers

    #############################
    # 需要继承类实现的函数（内部函数）
    #############################
    def _init(self):
        """
        自定义的初始化处理
        """
        # 添加http协议请求固定的Tags参数
        self._request_tag_paras = self._request_tag_paras.update({
            tags.COMPONENT: 'const:SanicRequest',
            tags.HTTP_METHOD: 'req:method',
            tags.HTTP_URL: 'req:url',
            tags.SPAN_KIND: 'const:%s' % tags.SPAN_KIND_RPC_SERVER
        })

        # 添加http协议响应固定的Tags参数
        self._response_tag_paras = self._response_tag_paras.update({
            tags.HTTP_STATUS_CODE: 'resp:status'
        })

    def _get_extract_para(self, request_obj: Request) -> tuple:
        """
        获取从请求对象提取SpanContext的参数

        @param {sanic.request.Request} request_obj - 请求对象

        @returns {tuple} - 返回(format, carrier)的字典
            例如: return opentracing.Format.HTTP_HEADERS, headers
        """
        headers = {}
        for k, v in request_obj.headers.items():
            headers[k.lower()] = v
        return opentracing.Format.HTTP_HEADERS, headers

    def _set_all_request_trace_middleware(self):
        """
        设置app追踪所有请求的中间件处理函数
        注: 分别在请求处理函数的执行前、执行后、执行中出现异常这3个情况分别执行_before_request_fn和_after_request_fn函数
        """
        # 请求处理中间件
        @self._app.middleware(middleware_or_request="request")
        def start_trace(request: Request):
            self._trace_all_request_middleware_request(
                request, operation_name_para='req:path'
            )

        # 响应处理中间件
        @self._app.middleware(middleware_or_request="response")
        def end_trace(request: Request, response: HTTPResponse):
            return self._trace_all_request_middleware_response(
                request, response
            )

        # 异常处理中间件
        @self._app.exception(Exception)
        def end_trace_error(request: Request, exception: Exception):
            self._trace_all_request_middleware_exception(
                request, exception
            )
            # 继续抛出异常
            raise exception


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    # 打印版本信息
    print(('模块名：%s  -  %s\n'
           '作者：%s\n'
           '发布日期：%s\n'
           '版本：%s' % (__MOUDLE__, __DESCRIPT__, __AUTHOR__, __PUBLISH__, __VERSION__)))

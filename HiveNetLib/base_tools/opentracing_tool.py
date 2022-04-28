#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
# Copyright 2019 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
支持OpenTracing的处理工具

@module opentracing_tool
@file opentracing_tool.py
"""

import os
import sys
import copy
from functools import wraps
from inspect import isawaitable
from typing import List, Callable, Any, Union
# 根据当前文件路径将包路径纳入，在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir, os.path.pardir)))
from HiveNetLib.base_tools.run_tool import RunTool
# 动态安装包
import HiveNetLib.deps_tool as deps_tool
# opentracing
try:
    import opentracing
except ImportError:
    deps_tool.install_package('opentracing')
    import opentracing
from opentracing.ext import tags


__MOUDLE__ = 'opentracing_tool'  # 模块名
__DESCRIPT__ = u'支持OpenTracing的处理工具'  # 模块描述
__VERSION__ = '0.1.0'  # 版本
__AUTHOR__ = u'黎慧剑'  # 作者
__PUBLISH__ = '2022.01.09'  # 发布日期


class OpenTracerFW(opentracing.Tracer):
    """
    通用的支持OpenTracing的Tracer对象框架真正的实现类需要继承并实现具体的处理函数
    """

    #############################
    # 构造函数
    #############################
    def __init__(
        self,
        tracer: opentracing.tracer = None,
        app: Any = None,
        trace_all_requests: bool = False,
        request_tag_paras: dict = None,
        request_baggage_paras: dict = None,
        response_tag_paras: dict = None,
        custom_before_request_func: Callable = None,
        custom_after_request_func: Callable = None,
        trace_all_exception: bool = True,
        trace_exceptions: List[Exception] = [],
        get_response_error_func: Callable = None,
        get_return_error_func: Callable = None
    ):
        """
        支持OpenTracing的处理工具框架

        @param {opentracing.tracer} tracer=None - 实际接入的Tracer对象
            注: 例如jaeger的Tracer实例对象
        @param {Any} app=None - 要追踪的应用实例对象，例如Flask或Sanic的实例对象
        @param {bool} trace_all_requests=False - 是否追踪所有请求，如果为True则自动注入app的所有请求处理
        @param {dict} request_tag_paras=None - 需要从请求对象获取并放入Tags的参数字典
            每个参数的key为要送入Tags的标识名，value为获取参数，格式为'req/head/json/const:para_str'
            注: req或head或json指示从request_obj获取信息位置，const指示直接获取送入的值作为操作名称
        @param {dict} request_baggage_paras=None - 需要从请求对象获取并放入SpanContext中Baggage传递到后续调用的参数字典,
            key为要送入Baggage的标识名，value为获取参数(参数格式和request_tag_paras定义一致)
        @param {dict} response_tag_paras=None - t
        @param {Callable} custom_before_request_func=None - 在创建Span以后，执行请求处理函数前执行的函数
        @param {Callable} custom_after_request_func=None - 在完成请求处理函数调用后，关闭Span前执行的函数
        @param {bool} trace_all_exception=True - 是否记录所有异常错误，如果为False则按照trace_exceptions所设定的异常类型进行记录
        @param {List[Exception]} trace_exceptions=[] - 要记录的异常错误清单
        @param {Callable} get_response_error_func=None - 判断请求返回值是否错误的自定义函数
            函数格式为 func(response_obj) -> None|Exception|str
            注: 如果检查通过返回None，检查不通过返回特定的Exception对象或错误描述字符串
        @param {Callable} get_return_error_func=None - 判断函数返回值是否错误的自定义函数
            函数格式为 func(response_obj) -> None|Exception|str
            注: 如果检查通过返回None，检查不通过返回特定的Exception对象或错误描述字符串
        """
        if trace_all_requests and app is None:
            raise ValueError(
                f"trace_all_requests={trace_all_requests} requires a non None app"
            )

        # 获取实际的tracer对象
        if tracer is None:
            self.tracer = opentracing.tracer
        elif callable(tracer):
            self.tracer = tracer()
        else:
            self.tracer = tracer

        self._app = app
        self._trace_all_requests = trace_all_requests
        self._request_tag_paras = {} if request_tag_paras is None else request_tag_paras
        self._request_baggage_paras = {} if request_baggage_paras is None else request_baggage_paras
        self._response_tag_paras = {} if response_tag_paras is None else response_tag_paras
        self._custom_before_request_func = custom_before_request_func
        self._custom_after_request_func = custom_after_request_func
        self._trace_all_exception = trace_all_exception
        self._exceptions_to_trace = trace_exceptions
        self._get_response_error_func = get_response_error_func
        self._get_return_error_func = get_return_error_func

        # 执行实现类的参数调整
        self._init()

        # 存储Span对象的字典，用于切换不同执行函数范围的Span
        # key为Span对应的request对象的string格式，value为包含Span的Scope对象
        self._current_scopes = {}

        if self._trace_all_requests:
            # 追踪app的所有请求
            self._set_all_request_trace_middleware()

    #############################
    # 公共函数
    #############################
    def get_active_span(self) -> opentracing.Span:
        """
        获取当前激活的Span对象

        @returns {opentracing.Span} - 当前激活的Span对象
            注: 如果当前没有Span返回None
        """
        return self.tracer.active_span

    def set_tag(self, tag_name: str, tag_val: Any) -> opentracing.Span:
        """
        在当前激活的Span上设置Tags

        @param {str} tag_name - 要设置的tag标识
        @param {Any} tag_val - 要设置的值

        @returns {opentracing.Span} - 当前激活的Span对象
        """
        span = self.tracer.active_span
        if span is not None:
            return span.set_tag(tag_name, tag_val)

    def set_baggage(self, itme_name: str, itme_val: Any) -> opentracing.Span:
        """
        在当前激活的Span上设置Baggage（传递到下一次调用）

        @param {str} itme_name - 要设置的Baggage Item标识
        @param {Any} itme_val - 要设置的Baggage Item的值

        @returns {opentracing.Span} - 当前激活的Span对象
        """
        span = self.tracer.active_span
        if span is not None:
            return span.set_baggage_item(itme_name, itme_val)

    def log_kv(self, key_values: dict) -> opentracing.Span:
        """
        在当前激活的Span上记录key_value日志事件

        @param {dict} key_values - 要设置的key_values事件字典

        @returns {opentracing.Span} - 当前激活的Span对象
        """
        span = self.tracer.active_span
        if span is not None:
            return span.log_kv(key_values)

    def inject_to_call(self, format: str, carrier: Any) -> Any:
        """
        注入SpanContext（上下文）到请求载体

        @param {str} format - 格式化类型，例如 opentracing.Format.HTTP_HEADERS
        @param {Any} carrier - 要注入上下文的载体对象
        """
        span = self.tracer.active_span
        if span is not None:
            return self.tracer.inject(span.context, format, carrier)

    #############################
    # 修饰符函数
    #############################
    def trace(
        self, operation_name_para: str = 'const:unknow', self_tag_paras: dict = None,
        self_baggage_paras: dict = None, self_resp_tag_paras: dict = None,
        self_before_func: Callable = None, self_after_func: Callable = None,
        trace_all_exception: bool = None, trace_exceptions: List[Exception] = [],
        get_response_error_func: Callable = None
    ):
        """
        请求处理函数的trace追踪修饰符

        @param {str} operation_name_para=None - 要获取的操作名称的参数，格式为'req/head/json/const:para_str'
            注: req或head或json指示从request_obj获取信息位置，const指示直接获取送入的值作为操作名称
        @param {dict} self_tag_paras=None - 当前函数自有的放入Tags的参数字典，将覆盖实例公共的参数字典
            每个参数的key为要送入Tags的标识名，value为获取参数(参数格式和operation_name_para定义一致)
        @param {dict} self_baggage_paras=None - 当前函数自有的放入SpanContext中Baggage传递到后续调用的参数字典,
            将覆盖实例公共的参数字典, key为要送入Baggage的标识名，value为获取参数(参数格式和operation_name_para定义一致)
        @param {dict} self_resp_tag_paras=None - 当前函数自有的需放入Tags的response信息的参数字典，将覆盖实例公共的参数字典
            每个参数的key为要送入Tags的标识名，value为获取参数，格式为'resp/head/json/const:para_str'
            注: req或head或json指示从response_obj获取信息位置，const指示直接获取送入的值作为操作名称
        @param {Callable} self_before_func=None - 开启Span后，需要执行的自定义请求函数
            函数定义为 func(request_obj, open_tracer), open_tracer传入当前OpenTracer的实例对象
        @param {Callable} self_after_func=None - 关闭Span前需要执行的自定义函数
            函数定义为 func(request_obj, open_tracer), open_tracer传入当前OpenTracer的实例对象
        @param {bool} trace_all_exception=None - 是否记录所有异常错误，如果为False则按照trace_exceptions所设定的异常类型进行记录
            注: 如果为None代表根据实例初始化时定义的参数处理
        @param {List[Exception]} trace_exceptions=[] - 要记录的异常错误清单
        @param {Callable} get_response_error_func=None - 判断请求返回值是否错误的自定义函数
            函数格式为 func(response_obj) -> None|Exception|str
            注: 如果检查通过返回None，检查不通过返回特定的Exception对象或错误描述字符串
        """
        def decorator(f):
            @wraps(f)
            async def decorated_function(*args, **kwargs):
                # 如果已经设置了追踪全部请求，则忽略当前的修饰符
                if self._trace_all_requests:
                    response = f(*args, **kwargs)
                    if isawaitable(response):
                        return await response
                    return response

                # 单独设置修饰符的情况
                request_obj = self.get_request_obj(*args, **kwargs)
                self._trace_all_request_middleware_request(
                    request_obj, operation_name_para=operation_name_para,
                    self_tag_paras=self_tag_paras, self_baggage_paras=self_baggage_paras,
                    self_before_func=self_before_func
                )
                try:
                    # 执行请求处理函数
                    response = f(*args, **kwargs)
                    if isawaitable(response):
                        response = await response

                    # 使用统一的处理逻辑
                    return self._trace_all_request_middleware_response(
                        request_obj, response, self_resp_tag_paras=self_resp_tag_paras,
                        self_after_func=self_after_func,
                        get_response_error_func=get_response_error_func
                    )
                except Exception as e:
                    self._trace_all_request_middleware_exception(
                        request_obj, e, trace_all_exception=trace_all_exception,
                        trace_exceptions=trace_exceptions
                    )
                    raise
            return decorated_function

        return decorator

    def trace_method(
        self, operation_name_para: str = 'const:unknow', tag_paras: dict = None,
        baggage_paras: dict = None, resp_tag_paras: dict = None,
        before_func: Callable = None, after_func: Callable = None,
        trace_all_exception: bool = True, trace_exceptions: List[Exception] = [],
        get_return_error_func: Callable = None
    ):
        """
        调用函数的trace追踪修饰符

        @param {str} operation_name_para=None - 要获取的操作名称的参数，格式为'name/para_pos/para_key/const:para_str'
            const - 固定值
            name - 函数名
            para_pos - 函数指定位置的参数值
            para_key - 函数指定key的参数值
        @param {dict} tag_paras=None - 需放入Tags的参数字典
            每个参数的key为要送入Tags的标识名，value为获取参数(参数格式和operation_name_para定义一致)
        @param {dict} baggage_paras=None - 需放入SpanContext中Baggage传递到后续调用的参数字典,
            key为要送入Baggage的标识名，value为获取参数(参数格式和operation_name_para定义一致)
        @param {dict} resp_tag_paras=None - 当前函数自有的需放入Tags的response信息的参数字典
            每个参数的key为要送入Tags的标识名，value为获取参数
        @param {Callable} before_func=None - 开启Span后，需要执行的自定义函数
            函数定义为 func(method_info_obj, open_tracer), open_tracer传入当前OpenTracer的实例对象
        @param {Callable} after_func=None - 关闭Span前需要执行的自定义函数
            函数定义为 func(method_info_obj, open_tracer), open_tracer传入当前OpenTracer的实例对象
        @param {bool} trace_all_exception=True - 是否记录所有异常错误，如果为False则按照trace_exceptions所设定的异常类型进行记录
        @param {List[Exception]} trace_exceptions=[] - 要记录的异常错误清单
        @param {Callable} get_return_error_func=None - 判断函数返回值是否错误的自定义函数
            函数格式为 func(response_obj) -> None|Exception|str
            注: 如果检查通过返回None，检查不通过返回特定的Exception对象或错误描述字符串
        """
        def decorator(f):
            @wraps(f)
            async def decorated_function(*args, **kwargs):
                # 获取函数信息
                method_info_obj = self._get_method_info_obj(f, args, kwargs)
                self._before_method_fn(
                    method_info_obj, operation_name_para=operation_name_para,
                    tag_paras=tag_paras, baggage_paras=baggage_paras, before_func=before_func
                )
                try:
                    response = f(*args, **kwargs)
                    if isawaitable(response):
                        response = await response

                    # 判断返回值是否错误
                    error = None
                    _get_return_error_func = get_return_error_func if get_return_error_func is not None else self._get_return_error_func
                    if _get_return_error_func is not None:
                        error = _get_return_error_func(response)

                    self._after_method_fn(
                        method_info_obj, response, tag_paras=resp_tag_paras,
                        after_func=after_func, error=error
                    )
                    return response
                except Exception as e:
                    if trace_all_exception or (trace_exceptions and type(e) in trace_exceptions):
                        # 遇到需要追踪的特定错误时，需要记录问题
                        self._after_method_fn(
                            method_info_obj, None, error=e
                        )
                    raise
            return decorated_function

        return decorator

    #############################
    # 内部函数
    #############################
    def _before_request_fn(
        self,
        request_obj: Any,
        operation_name_para: str = 'const:unknow',
        self_tag_paras: dict = None,
        self_baggage_paras: dict = None,
        self_before_func: Callable = None
    ):
        """
        请求处理前要执行的trace处理函数

        @param {Any} request_obj - 请求信息对象
        @param {str} operation_name_para=None - 要获取的操作名称的参数，格式为'req/head/json/const:para_str'
            注: req或head或json指示从request_obj获取信息位置，const指示直接获取送入的值作为操作名称
        @param {dict} self_tag_paras=None - 当前函数自有的放入Tags的参数字典，将覆盖实例公共的参数字典
            每个参数的key为要送入Tags的标识名，value为获取参数(参数格式和operation_name_para定义一致)
        @param {dict} self_baggage_paras=None - 当前函数自有的放入SpanContext中Baggage传递到后续调用的参数字典,
            将覆盖实例公共的参数字典, key为要送入Baggage的标识名，value为获取参数(参数格式和operation_name_para定义一致)
        @param {Callable} self_before_func=None - 开启Span后，需要执行的自定义请求函数
            函数定义为 func(request_obj, open_tracer), open_tracer传入当前OpenTracer的实例对象
        """
        operation_name = self._get_obj_info_inner('req', request_obj, operation_name_para, default='getError')

        # 创建包含Span的Scope对象
        try:
            span_ctx = self.tracer.extract(*self._get_extract_para(request_obj))
            scope = self.tracer.start_active_span(operation_name, child_of=span_ctx)
        except (
            opentracing.InvalidCarrierException,
            opentracing.SpanContextCorruptedException,
        ):
            # 无法获取到SpanContext的情况，创建一个包含新Span的Scope对象
            scope = self.tracer.start_active_span(operation_name)

        self._current_scopes[id(request_obj)] = scope

        span = scope.span
        # 设置Tags，覆盖实例默认要设置的参数
        tag_paras = copy.deepcopy(self._request_tag_paras).update(
            {} if self_tag_paras is None else self_tag_paras
        )
        for tag_name, tag_para in tag_paras.items():
            tag_value = self._get_obj_info_inner('req', request_obj, tag_para)
            if tag_value is not None:
                span.set_tag(tag_name, tag_value)

        # 设置Baggage，覆盖实例默认要设置的参数
        baggage_paras = copy.deepcopy(self._request_baggage_paras).update(
            {} if self_baggage_paras is None else self_baggage_paras
        )
        for baggage_name, baggage_para in baggage_paras.items():
            baggage_value = self._get_obj_info_inner('req', request_obj, baggage_para)
            if baggage_value is not None:
                span.set_baggage_item(baggage_name, baggage_value)

        # 执行通用的请求开始执行函数
        if self._custom_before_request_func is not None:
            self._custom_before_request_func(request_obj, self)

        if self_before_func is not None:
            self_before_func(request_obj, self)

    def _after_request_fn(
        self,
        request_obj: Any,
        response_obj: Any,
        self_tag_paras: dict = None,
        self_after_func: Callable = None,
        error: Union[Exception, str] = None
    ):
        """
        请求处理返回前要执行的trace处理函数

        @param {Any} request_obj - 请求信息对象
        @param {Any} response_obj - 响应信息对象
        @param {dict} self_tag_paras=None - 当前函数自有的需放入Tags的response信息的参数字典，将覆盖实例公共的参数字典
            每个参数的key为要送入Tags的标识名，value为获取参数
        @param {Callable} self_after_func=None - 关闭Span前需要执行的自定义函数
            函数定义为 func(request_obj, open_tracer), open_tracer传入当前OpenTracer的实例对象
        @param {Union[Exception, str]} error=None - 错误信息，如果有传值进来代表响应为失败的情况
        """
        # 执行通用的请求结束执行函数
        if self_after_func is not None:
            self_after_func(request_obj, response_obj, self)

        if self._custom_after_request_func is not None:
            self._custom_after_request_func(request_obj, response_obj, self)

        # 执行Span的关闭处理
        scope = self._current_scopes.pop(id(request_obj), None)
        if scope is None:
            return

        if response_obj is not None:
            span = scope.span
            # 设置Tags，覆盖实例默认要设置的参数
            tag_paras = copy.deepcopy(self._response_tag_paras).update(
                {} if self_tag_paras is None else self_tag_paras
            )
            for tag_name, tag_para in tag_paras.items():
                tag_value = self._get_obj_info_inner('resp', response_obj, tag_para)
                if tag_value is not None:
                    span.set_tag(tag_name, tag_value)

        # 如果有异常，按照OpenTracing标准设置错误并记录日志
        if error is not None:
            scope.span.set_tag(tags.ERROR, True)
            if type(error) == str:
                scope.span.lo_kv({{"message": error}})
            else:
                scope.span.log_kv({"event": tags.ERROR, "error.object": error})

        # 关闭span
        scope.close()

    def _trace_all_request_middleware_request(
        self, request_obj: Any, operation_name_para: str = 'const:unknow', self_tag_paras: dict = None,
        self_baggage_paras: dict = None, self_before_func: Callable = None
    ):
        """
        追踪所有请求的请求中间件入口函数

        @param {Any} request_obj - 请求对象
        @param {str} operation_name_para=None - 要获取的操作名称的参数，格式为'req/head/json/const:para_str'
            注: req或head或json指示从request_obj获取信息位置，const指示直接获取送入的值作为操作名称
        @param {dict} self_tag_paras=None - 当前函数自有的放入Tags的参数字典，将覆盖实例公共的参数字典
            每个参数的key为要送入Tags的标识名，value为获取参数(参数格式和operation_name_para定义一致)
        @param {dict} self_baggage_paras=None - 当前函数自有的放入SpanContext中Baggage传递到后续调用的参数字典,
            将覆盖实例公共的参数字典, key为要送入Baggage的标识名，value为获取参数(参数格式和operation_name_para定义一致)
        @param {Callable} self_before_func=None - 开启Span后，需要执行的自定义请求函数
            函数定义为 func(request_obj, open_tracer), open_tracer传入当前OpenTracer的实例对象
        """
        self._before_request_fn(
            request_obj, operation_name_para=operation_name_para,
            self_tag_paras=self_tag_paras, self_baggage_paras=self_baggage_paras,
            self_before_func=self_before_func
        )

    def _trace_all_request_middleware_response(
        self, request_obj: Any, response_obj: Any, self_resp_tag_paras: dict = None,
        self_after_func: Callable = None, get_response_error_func: Callable = None
    ) -> Any:
        """
        追踪所有请求的响应中间件入口函数

        @param {Any} request_obj - 请求对象
        @param {Any} response_obj - 响应对象
        @param {dict} self_resp_tag_paras=None - 当前函数自有的需放入Tags的response信息的参数字典，将覆盖实例公共的参数字典
            每个参数的key为要送入Tags的标识名，value为获取参数，格式为'resp/head/json/const:para_str'
            注: req或head或json指示从response_obj获取信息位置，const指示直接获取送入的值作为操作名称
        @param {Callable} self_after_func=None - 关闭Span前需要执行的自定义函数
            函数定义为 func(request_obj, open_tracer), open_tracer传入当前OpenTracer的实例对象
        @param {Callable} get_response_error_func=None - 判断请求返回值是否错误的自定义函数
            函数格式为 func(response_obj) -> None|Exception|str
            注: 如果检查通过返回None，检查不通过返回特定的Exception对象或错误描述字符串

        @returns {Any} - 返回响应对象
        """
        # 判断通讯层面响应是否错误
        error = self.get_protocol_response_error(response_obj)
        if error is None:
            # 获取业务层面响应是否错误
            if get_response_error_func is not None:
                _get_response_error_func = get_response_error_func
            else:
                _get_response_error_func = self._get_response_error_func
            if _get_response_error_func is not None:
                error = _get_response_error_func(response_obj)

        self._after_request_fn(
            request_obj, response_obj, self_tag_paras=self_resp_tag_paras,
            self_after_func=self_after_func, error=error
        )
        return response_obj

    def _trace_all_request_middleware_exception(
        self, request_obj: Any, exception: Exception, trace_all_exception: bool = None,
        trace_exceptions: List[Exception] = []
    ):
        """
        追踪所有请求的异常处理中间件入口函数

        @param {Any} request_obj - 请求对象
        @param {Exception} exception - 捕获到的异常对象
        @param {bool} trace_all_exception=None - 是否记录所有异常错误，如果为False则按照trace_exceptions所设定的异常类型进行记录
            注: 如果为None代表根据实例初始化时定义的参数处理
        @param {List[Exception]} trace_exceptions=[] - 要记录的异常错误清单
        """
        _trace_all_exception = trace_all_exception if trace_all_exception is not None else self._trace_all_exception
        exceptions_to_trace = []
        if not _trace_all_exception:
            exceptions_to_trace = copy.copy(self._exceptions_to_trace).extend(
                trace_exceptions
            )
        if _trace_all_exception or (exceptions_to_trace and type(exception) in exceptions_to_trace):
            # 遇到需要追踪的特定错误时，需要记录问题
            self._after_request_fn(
                request_obj, None, error=exception
            )

    def _get_obj_info_inner(self, obj_type: str, obj: Any, para_str: str, default: Any = None) -> Any:
        """
        内部从请求或响应对象获取指定参数值的通用函数

        @param {str} obj_type - 对象类型，req-请求对象, resp-响应对象
        @param {Any} obj - 请求或响应对象
        @param {str} para_str - 获取参数
        @param {Any} default=None - 如果获取不到所返回的默认值

        @returns {Any} - 返回获取到的结果
        """
        # 解析参数
        get_type = 'const'
        get_para = ''
        index = para_str.find(':')
        if index < 0:
            get_para = para_str
        elif index == 0:
            get_para = para_str[1:]
        else:
            get_type = para_str[0:index]
            get_para = para_str[index+1:]

        # 获取信息
        if get_type == 'const':
            return get_para
        else:
            if obj_type == 'resp':
                return self.get_response_info(obj, get_type, get_para, default=default)
            else:
                return self.get_request_info(obj, get_type, get_para, default=default)

    def _before_method_fn(
        self,
        method_info_obj: dict,
        operation_name_para: str = 'name:',
        tag_paras: dict = None,
        baggage_paras: dict = None,
        before_func: Callable = None
    ):
        """
        调用函数处理前要执行的trace处理函数

        @param {dict} method_info_obj - 要处理的函数信息字典
        @param {str} operation_name_para=None - 要获取的操作名称的参数，格式为'name/para_pos/para_key/const:para_str'
            const - 固定值
            name - 函数名
            para_pos - 函数指定位置的参数值
            para_key - 函数指定key的参数值
        @param {dict} tag_paras=None - 需放入Tags的参数字典
            每个参数的key为要送入Tags的标识名，value为获取参数(参数格式和operation_name_para定义一致)
        @param {dict} baggage_paras=None - 需放入SpanContext中Baggage传递到后续调用的参数字典,
            key为要送入Baggage的标识名，value为获取参数(参数格式和operation_name_para定义一致)
        @param {Callable} before_func=None - 开启Span后，需要执行的自定义函数
            函数定义为 func(method_info_obj, open_tracer), open_tracer传入当前OpenTracer的实例对象
        """
        operation_name = self._get_method_info_inner(
            method_info_obj, para_str=operation_name_para, default='getNameError'
        )
        # 创建包含Span的Scope对象
        scope = self.tracer.start_active_span(operation_name, child_of=self.tracer.active_span)
        self._current_scopes[id(method_info_obj)] = scope

        span = scope.span
        # 设置Tags，覆盖实例默认要设置的参数
        _tag_paras = {} if tag_paras is None else tag_paras
        for tag_name, tag_para in _tag_paras.items():
            tag_value = self._get_method_info_inner(method_info_obj, tag_para)
            if tag_value is not None:
                span.set_tag(tag_name, tag_value)

        # 设置Baggage，覆盖实例默认要设置的参数
        _baggage_paras = {} if baggage_paras is None else baggage_paras
        for baggage_name, baggage_para in _baggage_paras.items():
            baggage_value = self._get_method_info_inner(method_info_obj, baggage_para)
            if baggage_value is not None:
                span.set_baggage_item(baggage_name, baggage_value)

        # 执行调用函数前开始执行的函数
        if before_func is not None:
            before_func(method_info_obj, self)

    def _after_method_fn(
        self,
        method_info_obj: Any,
        response_obj: Any,
        tag_paras: dict = None,
        after_func: Callable = None,
        error: Union[Exception, str] = None
    ):
        """
        调用函数处理返回前要执行的trace处理函数

        @param {Any} method_info_obj - 被调用函数信息对象
        @param {Any} response_obj - 返回信息对象
        @param {dict} tag_paras=None - 当前函数自有的需放入Tags的response信息的参数字典
            每个参数的key为要送入Tags的标识名，value为获取参数
        @param {Callable} after_func=None - 关闭Span前需要执行的自定义函数
            函数定义为 func(method_info_obj, open_tracer), open_tracer传入当前OpenTracer的实例对象
        @param {Union[Exception, str]} error=None - 错误信息，如果有传值进来代表响应为失败的情况
        """
        # 执行通用的请求结束执行函数
        if after_func is not None:
            after_func(method_info_obj, response_obj, self)

        # 执行Span的关闭处理
        scope = self._current_scopes.pop(id(method_info_obj), None)
        if scope is None:
            return

        if response_obj is not None:
            span = scope.span
            # 设置Tags，覆盖实例默认要设置的参数
            _tag_paras = {} if tag_paras is None else tag_paras
            for tag_name, tag_para in _tag_paras.items():
                tag_value = self._get_method_info_inner(method_info_obj, tag_para)
                if tag_value is not None:
                    span.set_tag(tag_name, tag_value)

        # 如果有异常，按照OpenTracing标准设置错误并记录日志
        if error is not None:
            scope.span.set_tag(tags.ERROR, True)
            if type(error) == str:
                scope.span.lo_kv({{"message": error}})
            else:
                scope.span.log_kv({"event": tags.ERROR, "error.object": error})

        # 关闭span
        scope.close()

    def _get_method_info_obj(self, func: Callable, args: tuple, kwargs: dict) -> dict:
        """
        获取函数对象的信息

        @param {Callable} func - 函数对象
        @param {tuple} args - 固定位置入参
        @param {dict} kwargs - key-value形式的入参

        @returns {dict} - 返回的函数对象信息，格式为:
            {
                'name': '函数名',
                # 函数入参取值索引
                'parameters': {
                    '入参名': 参数值,
                    '_P1': 第2个位置的参数值（从0开始）,
                    ...
                }
            }
        """
        parameters = {}
        parameter_defines = RunTool.get_function_parameter_defines(func)
        index = 0  # 当前参数的位置
        args_len = len(args)
        for parameter in parameter_defines:
            name = parameter['name']
            para_type = parameter['type']
            if para_type == 'KEYWORD_ONLY':
                parameters[name] = kwargs.get(
                    name, parameter['default'] if parameter['has_default'] else None
                )
            elif para_type == 'POSITIONAL_OR_KEYWORD':
                if index < args_len:
                    val = args[index]
                else:
                    val = kwargs.get(
                        name, parameter['default'] if parameter['has_default'] else None
                    )
                # 同时具有位置和名字检索
                parameters['_P%d' % index] = val
                if name is not None and name != '':
                    parameters[name] = val
            elif para_type == 'VAR_POSITIONAL':
                # *args位置变量, 增加可变的位置检索
                for var_index in range(index, args_len):
                    parameters['_P%d' % var_index] = args[var_index]
            elif para_type == 'VAR_KEYWORD':
                # **kwargs可变数量的kv形式参数, 将所有key-value的值添加到索引
                for key, val in kwargs.items():
                    if parameters.get(key, None) is None:
                        parameters[key] = val

            # 继续下一个循环
            index += 1

        method_info_obj = {
            'name': RunTool.get_function_name(func, is_with_class=True, is_with_module=True),
            'parameters': parameters
        }
        return method_info_obj

    def _get_method_info_inner(self, obj: Any, para_str: str, default: Any = None) -> Any:
        """
        内部从函数信息对象获取指定参数值的通用函数

        @param {Any} obj - 函数信息对象
        @param {str} para_str - 获取参数
        @param {Any} default=None - 如果获取不到所返回的默认值

        @returns {Any} - 返回获取到的结果
        """
        # 解析参数
        get_type = 'const'
        get_para = ''
        index = para_str.find(':')
        if index < 0:
            get_para = para_str
        elif index == 0:
            get_para = para_str[1:]
        else:
            get_type = para_str[0:index]
            get_para = para_str[index+1:]

        # 获取信息
        val = default
        if get_type == 'const':
            val = get_para
        elif get_type == 'name':
            val = obj.get('name', default)
        elif get_type == 'para_pos':
            val = obj.get('_P%s' % get_para, default)
        elif get_type == 'para_key':
            val = obj.get(get_para, default)

        return val

    #############################
    # 需要继承类实现的函数（公共函数）
    #############################
    def get_request_obj(self, *args, **kwargs) -> Any:
        """
        获取当前连接的请求对象
        注: 所传入的参数为请求处理函数的入参

        @returns {Any} - 返回请求对象
        """
        return None

    def get_request_info(self, request_obj: Any, get_type: str, get_para: str, default: Any = None) -> Any:
        """
        从请求对象获取指定参数值
        注: 需实现类继承并实现具体逻辑

        @param {Any} request_obj - 请求对象
        @param {str} get_type - 获取类型，需至少支持以下3类
            req - 获取请求链接的信息，例如ip, url, method等
            head - 通讯协议的协议头获取信息
            json - 从报文body内容的json对象获取信息, 参数为JsonPath查找字符串
        @param {str} get_para - 要获取信息的具体参数，有实现函数定义参数的具体要求
        @param {Any} default=None - 如果获取不到所返回的默认值

        @returns {Any} - 返回获取到的结果
        """
        return None

    def get_response_info(self, response_obj: Any, get_type: str, get_para: str, default: Any = None) -> Any:
        """
        从响应对象获取指定参数值
        注: 需实现类继承并实现具体逻辑

        @param {Any} response_obj - 响应对象
        @param {str} get_type - 获取类型，需至少支持以下3类
            resp - 获取响应协议对象的信息，例如status
            head - 通讯协议的协议头获取信息
            json - 从报文body内容的json对象获取信息, 参数为JsonPath查找字符串
        @param {str} get_para - 要获取信息的具体参数，有实现函数定义参数的具体要求
        @param {Any} default=None - 如果获取不到所返回的默认值

        @returns {Any} - 返回获取到的结果
        """
        return None

    def get_protocol_response_error(self, response_obj: Any) -> Union[Exception, str]:
        """
        获取通讯协议层面上响应对象的错误对象

        @param {Any} response_obj - 响应信息

        @returns {Union[Exception, str]} - 返回通过response_obj判断的错误对象(可以是Exception对象或字符串)
            注: 如果是成功则返回None
        """
        return None

    def get_request_inject_para(self, request_obj: Any) -> tuple:
        """
        获取新请求对象要注入SpanContext的参数

        @param {Any} request_obj - 新调用请求对象

        @returns {tuple} - 返回 (format, carrier)
        """
        return opentracing.Format.HTTP_HEADERS, {}

    #############################
    # 需要继承类实现的函数（内部函数）
    #############################
    def _init(self):
        """
        自定义的初始化处理
        """
        return

    def _get_extract_para(self, request_obj: Any) -> tuple:
        """
        获取从请求对象提取SpanContext的参数

        @param {Any} request_obj - 请求对象

        @returns {tuple} - 返回(format, carrier)的字典
            例如: return opentracing.Format.HTTP_HEADERS, headers
        """
        return opentracing.Format.HTTP_HEADERS, {}

    def _set_all_request_trace_middleware(self):
        """
        设置app追踪所有请求的中间件处理函数
        注: 分别在请求处理函数的执行前、执行后、执行中出现异常这3个情况分别执行_before_request_fn和_after_request_fn函数
        """
        return


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    # 打印版本信息
    print(('模块名：%s  -  %s\n'
           '作者：%s\n'
           '发布日期：%s\n'
           '版本：%s' % (__MOUDLE__, __DESCRIPT__, __AUTHOR__, __PUBLISH__, __VERSION__)))

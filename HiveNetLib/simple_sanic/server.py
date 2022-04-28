#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
# Copyright 2019 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
利用Sanic框架实现的高性能Restful Api服务

@module server
@file server.py
"""
import os
import sys
import inspect
import threading
from inspect import isawaitable
from collections import OrderedDict
from functools import wraps
# 根据当前文件路径将包路径纳入, 在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir, os.path.pardir)))
# 动态安装包
import HiveNetLib.deps_tool as deps_tool
process_install_sanic = False
while True:
    try:
        from sanic import Sanic
        from sanic.response import HTTPResponse, text, json
        from sanic.log import logger as sanic_logger
        from sanic_ext import Extend
        from sanic_ext.config import Config
        break
    except ImportError:
        if not process_install_sanic:
            deps_tool.install_package('sanic')
            deps_tool.install_package('sanic-ext')
            process_install_sanic = True
            continue
        raise
try:
    import gevent
except ImportError:
    deps_tool.install_package('gevent')
    import gevent
# 自有包引用
from HiveNetLib.base_tools.run_tool import RunTool, AsyncTools

__MOUDLE__ = 'server'  # 模块名
__DESCRIPT__ = u'利用Sanic框架实现的高性能Restful Api服务'  # 模块描述
__VERSION__ = '0.1.0'  # 版本
__AUTHOR__ = u'黎慧剑'  # 作者
__PUBLISH__ = '2022.01.03'  # 发布日期


class SanicTool(object):
    """
    Sanic工具类, 提供路由, 内容解析等通用处理功能
    注: 由于Sanic的机制, 不支持线程运行情况的stop操作, 因此取消了stop函数
    """
    @classmethod
    def add_route(cls, app: Sanic, url: str, func, name: str = None,
                  with_para: bool = False, methods: list = None, version=None):
        """
        添加指定路由

        @param {Sanic} app - 要添加路由的服务器实例
        @param {str} url - 路由url, 例如'/test'
        @param {function} func - 要添加路由的函数
        @param {str} name=None - 路由标识, 如果不传默认使用函数名(会存在函数名相同导致异常的情况)
        @param {bool} with_para=False - 路由是否根据函数添加入参
        @param {list} methods=None - 指定路由支持的方法, 如果不传代表支持所有方法
        @param {int｜float|str} version=None - 指定路由的版本, 则路由变为"/v{version}/url"
        """
        _route = url if url == '/' else url.rstrip('/')  # 去掉最后的'/'
        _methods = methods
        _name = name if name is not None else RunTool.get_function_name(
            func, is_with_class=True, is_with_module=True
        )

        if with_para:
            # 根据函数入参处理路由
            _para_list = RunTool.get_function_parameter_defines(func)
            for _para in _para_list:
                if _para['name'] == 'methods':
                    # 指定了处理方法
                    _methods = _para['default']
                elif _para['name'] in ('self', 'cls', 'request'):
                    # 不处理 self 和 cls 入参, 以及第一个请求的入参
                    continue
                elif _para['type'] not in ('VAR_POSITIONAL', 'VAR_KEYWORD'):
                    # 不处理 *args及**kwargs参数
                    _type = ''
                    if _para['annotation'] == str:
                        _type = ':str'
                    if _para['annotation'] == int:
                        _type = ':int'
                    elif _para['annotation'] == float:
                        _type = ':float'

                    _route = '%s/<%s:%s>' % (_route, _para['name'], _type)

        # 处理方法的设置
        _methods = ['GET'] if _methods is None else _methods

        # 添加路由
        app.add_route(
            func, _route, methods=_methods, name=_name, version=version
        )

    @classmethod
    def add_route_by_class(cls, app: Sanic, class_objs: list, blacklist: list = None, class_name_mapping: dict = None,
                           url_base: str = 'api', version=None):
        """
        通过类对象动态增加路由

        @param {Sanic} app - 要增加服务的Sanic应用实例
        @param {list} class_objs - Api类对象清单(可以支持传入类对象, 也可以支持传入类实例)
        @param {list} blacklist=None - 禁止添加的服务黑名单, 格式为"类名/函数名"
        @param {dict} class_name_mapping=None - 类名映射, 可以根据这个改变访问url的路径, key为真实类名, value为映射后的类名
        @param {str} url_base='api' - 路由开始的基础url
        @param {int｜float|str} version=None - 指定路由的版本, 则路由变为"/v{version}/url"
        """
        _blacklist = list() if blacklist is None else blacklist
        _class_name_mapping = dict() if class_name_mapping is None else class_name_mapping
        for _class in class_objs:
            _instance = None
            if not inspect.isclass(_class):
                _instance = _class
                _class = type(_instance)

            _real_class_name = _class.__name__
            # 获取映射后的类名
            _class_name = _class_name_mapping.get(_real_class_name, _real_class_name)
            # 遍历所有函数
            for _name, _value in inspect.getmembers(_class):
                if not _name.startswith('_') and callable(_value):
                    # 判断是否在黑名单中
                    if '%s/%s' % (_real_class_name, _name) in _blacklist:
                        continue

                    # 正常处理
                    _router_name = '%s.%s' % (_class_name, _name)
                    if url_base == '':
                        # 忽略前置
                        _route = '/%s/%s' % (_class_name, _name)
                    else:
                        _route = '/%s/%s/%s' % (url_base, _class_name, _name)
                    _methods = None
                    _para_list = RunTool.get_function_parameter_defines(_value)
                    for _para in _para_list:
                        if _para['name'] == 'methods':
                            # 指定了处理方法
                            _methods = _para['default']
                        elif _para['name'] == 'self' and _instance is not None:
                            # 不处理实例对象的self入参
                            continue
                        elif _para['name'] in ('request', 'cls'):
                            continue
                        elif _para['type'] not in ('VAR_POSITIONAL', 'VAR_KEYWORD'):
                            # 不处理 *args及**kwargs参数
                            _type = ''
                            if _para['annotation'] == str:
                                _type = ':str'
                            if _para['annotation'] == int:
                                _type = ':int'
                            elif _para['annotation'] == float:
                                _type = ':float'

                            _route = '%s/<%s%s>' % (_route, _para['name'], _type)

                    # 处理方法的设置
                    _methods = ['GET'] if _methods is None else _methods

                    # 对于实例对象, 获取真实的函数对象
                    if _instance is not None:
                        _value = getattr(_instance, _name)

                    # 加入路由
                    app.add_route(
                        _value, _route, methods=_methods, name=_router_name, version=version
                    )

    @classmethod
    def support_object_resp(cls, func):
        """
        支持函数直接返回Python对象的修饰符
        注: 正常函数应该返回标准的sanic.response.HTTPResponse对象, 本修饰符允许按以下方式返回
            1、返回sanic.response.HTTPResponse对象
            2、返回二元数组, 其中第1个为要返回的内容对象, 第2个为状态码
            3、直接返回要处理的对象, 状态码默认为200(注意不可直接将数组对象返回)

        @param {function} func - 修饰符处理的函数

        @example Restful函数返回非字符串格式内容
            @SanicTool.support_object_resp
            def func(a, b):
                ...
                return {'a':'value'}
        """
        @wraps(func)
        def wrapper(*args, **kwargs):
            _ret = func(*args, **kwargs)
            if isinstance(_ret, HTTPResponse):
                # 已按正常规范返回
                return _ret
            else:
                _status = 200
                if isinstance(_ret, (tuple, list)):
                    # 是列表, 第1个是要返回的值, 第2个是http状态码
                    _body = _ret[0]
                    if len(_ret) > 1:
                        _status = _ret[1]
                else:
                    _body = _ret

                if isinstance(_body, str):
                    # 字符串
                    return text(_body, status=_status)
                else:
                    # 对象
                    return json(_body, status=_status)
        return wrapper

    @classmethod
    def auth_required(cls, f=None, get_auth_fun=None, get_auth_para: dict = None):
        """
        需要验证的修饰函数

        @param {function} f - 要调用的函数
        @param {function} get_auth_fun - 获取 Auth 实例对象的函数对象
        @param {dict} get_auth_para - 获取 Auth 实例对象的函数KV入参

        @example  指定API需要登陆验证(Token模式)
            class RestfulApiClass(object):
                @classmethod
                @SanicTool.auth_required(get_auth_fun=get_auth_fun)
                def login(user_name, methods=['POST'], **kwargs):
                    ...
        """
        if f is not None and get_auth_fun is None:
            raise ValueError('get_auth_fun should not None!')

        def auth_internal(f):
            @wraps(f)
            def decorated(*args, **kwargs):
                # 获取验证对象
                _get_auth_para = {} if get_auth_para is None else get_auth_para
                _auth = get_auth_fun(**_get_auth_para)

                # 执行验证修饰函数
                return _auth.auth_required_call(f, *args, **kwargs)
            return decorated

        if f:
            return auth_internal(f)
        return auth_internal


class SanicServer(object):
    """
    Sanic服务处理
    """

    #############################
    # 静态函数
    #############################

    @classmethod
    def get_init_server_dict(cls) -> OrderedDict:
        """
        获取已经初始化的SanicServer访问字典

        @returns {OrderedDict} - 返回字典
        """
        INIT_SANIC_SERVER = RunTool.get_global_var('INIT_SANIC_SERVER')
        if INIT_SANIC_SERVER is None:
            INIT_SANIC_SERVER = OrderedDict()
            RunTool.set_global_var('INIT_SANIC_SERVER', INIT_SANIC_SERVER)

        return INIT_SANIC_SERVER

    @classmethod
    def get_init_server(cls, app_name: str = None):
        """
        获取已经初始化的SanicServer对象

        @param {str} app_name=None - 要获取的SanicServer的app_name, 如果不传默认取第一个

        @returns {SanicServer} - 获取到的对象
        """
        INIT_SANIC_SERVER = cls.get_init_server_dict()
        if app_name is None:
            return list(INIT_SANIC_SERVER.values())[0]
        else:
            return INIT_SANIC_SERVER[app_name]

    @classmethod
    def get_auth_fun(cls, auth_name: str = '', app_name: str = None):
        """
        获取SanicServer支持的Auth实例对象
        注: 该函数主要用于 SanicTool 的 auth_required 修饰符入参

        @param {str} auth_name='' - 验证对象类型名(比如类名, 具体取决于SanicServer的初始化参数)
        @param {str} app_name=None - 要获取的SanicServer的app_name, 如果不传默认取第一个
        """
        _server = cls.get_init_server(app_name=app_name)
        return _server.support_auths[auth_name]

    @classmethod
    async def default_index_handler(cls, request):
        """
        默认根路径处理函数, 返回资源部不存在的错误

        @param {sanic.request.Request} request - 请求对象
        """
        return text("Resource not found", status=404)

    #############################
    # 构造及析构函数
    #############################
    def __init__(self, app_name: str, server_config: dict = None, support_auths: dict = None,
                 before_server_start=None, after_server_start=None,
                 before_server_stop=None, after_server_stop=None, logger=None, **kwargs):
        """
        初始化SanicServer

        @param {str} app_name - Sanic服务器名称
        @param {dict} server_config=None - Sanic服务器配置字典, 定义如下:
            app_config {dict} - Sanic初始化参数字典(请参考Sanic官方文档), 常用参数包括:
                ctx {object} - 自定义上下文对象, 通过上下文对象可以在程序中共享数据
                    注: 默认会创建一个SimpleNamespace作为上下文, 你也可以送入一个指定的对象初始化上下文, 例如送入"ctx: {}"
                config {sanic.config.Config} - 自定义应用配置, 传入的对象应继承sanic.config.Config类
                    注: 可以通过 app.config.XXX 访问所设置的自定义配置; 此外也可以在创建服务后, 直接修改 app.config 的配置值(字典操作)
                log_config {dict} - 自定义的日志配置信息, 默认为sanic.log.LOGGING_CONFIG_DEFAULTS
                    注: 要求定义的日志名必须包括sanic.root、sanic.error、sanic.access
                configure_logging {bool} - 是否使用自定义日志配置, 配合log_config自行设置特定的日志
            run_config {dict} - SanicServer运行参数字典(请参考Sanic官方文档), 常用参数包括:
                host {str} - 绑定的主机地址, 默认为'127.0.0.1'
                port {int} - 服务监听的端口, 默认为8000
                workers {int} - 工作线程数, 默认为1
                ssl {ssl.SSLContext|dict} - ssl加密连接的配置, 可以有两种配置方式
                    1、使用ssl.create_default_context方法创建ssl.SSLContext并传入, 具体代码可参考官方文档示例
                    2、通过字典传递密钥和证书文件: ssl = {"cert": "/path/to/cert", "key": "/path/to/keyfile"}
                debug {bool} - 是否开启debug模式(生产部署请关闭), 默认为False
                    注: 非asgi模式不支持设置debug为True
                access_log {bool} - 启用请求访问日志(生产部署请关闭), 默认为True
            cors_config {dict} - 跨域访问的支持参数, 具体参数见 https://sanicframework.org/zh/plugins/sanic-ext/http/cors.html#%E9%85%8D%E7%BD%AE-configuration
                常用的参数如下:
                CORS_ORIGINS - 允许访问资源的来源, 默认为'*', 传参支持:
                    字符串格式, 例如'http://foobar.com,http://bar.com'
                    数组格式, 例如['http://foobar.com', 'http://bar.com']
                    正则表达式对象(re.Pattern), 例如 re.compile(r'http://.*\.bar\.com')
                CORS_METHODS - 允许来源可以使用的http方法, 例如['GET', 'POST']
                CORS_EXPOSE_HEADERS - 允许来源获取到返回值的header中的值列表, 如果不设置客户端只能获取6个基本字段: Cache-Control、Content-Language、Content-Type、Expires、Last-Modified、Pragma
                    例如['header-name-1', 'header-name-2']
                CORS_ALLOW_HEADERS - 服务器支持的header的字段列表, 默认为*
                CORS_SUPPORTS_CREDENTIALS {bool} - 是否允许发送Cookie, 默认为False
            use_asgi {bool} - 是否使用asgi服务模式启动(例如daphne、uvicorn、hypercorn、Gunicorn-不支持异步)
                注: asgi服务模式, 将由第三方服务应用通过app实例启动服务, 不会调用start/stop方法进行处理
            run_in_thread {bool} - 是否线程启动模式, 默认为True
                注: 线程启动模式不支持多工作线程, 而非线程启动不支持异步起动
            auto_trace {bool} - 是否开启http的trace功能(允许客户端TRACE请求时原样返回收到的报文内容), 默认为False
            oas {bool} - 是否开启OpenAPI文档生成, 默认为False
            oas_config {dict} - OpenAPI自动文档生成参数, 具体参数见 https://sanicframework.org/zh/plugins/sanic-ext/openapi/ui.html#%E9%85%8D%E7%BD%AE%E9%80%89%E9%A1%B9-config-options
                常用参数包括:
                OAS_UI_DEFAULT - 控制文档显示的UI, 可以为 redoc(默认) 或 swagger; 如果设置为 None, 则不会设置文档路由
                OAS_URL_PREFIX - 用于 OpenAPI 文档蓝图的 URL 前缀, 默认为 '/docs'
        @param {dict} support_auths=None - 服务器支持的验证对象字典, key为验证对象类型名(可以为类名), value为验证对象实例对象
            注意: 支持的auth对象必须有auth_required这个修饰符函数
        @param {function} before_server_start=None - 服务器启动前执行的函数对象, 传入服务自身(self)
        @param {function} after_server_start=None - 服务器启动后执行的函数对象, 传入服务自身(self)
        @param {function} before_server_stop=None - 服务器关闭前执行的函数对象, 传入服务自身(self)
        @param {function} after_server_stop=None - 服务器关闭后执行的函数对象, 传入服务自身(self)
            注: CPU为M1版本的 Mac Book, 通过 ctrl+c 结束进程时无法正常关闭Sanic, 因此 before_server_stop 和 after_server_stop 无法正常使用
                其他操作系统暂未测试验证
        @param {Logger} logger=None - 自定义应用逻辑使用的日志对象, 如果不传入则使用sanic的日志对象
            注: 同时会将该日志对象绑定到app.ctx.logger上
        @param {kwargs} - 扩展参数
        """
        # 判断服务器名是否重复
        INIT_SANIC_SERVER = self.get_init_server_dict()
        if app_name in INIT_SANIC_SERVER.keys():
            raise RuntimeError('Init sanic server [%s] already exists!' % app_name)

        # 参数处理
        self.app_name = app_name
        self.server_config = {} if server_config is None else server_config
        if self.server_config.get('run_config', None) is None:
            self.server_config['run_config'] = {}

        # 创建应用
        self.app = Sanic(self.app_name, **self.server_config.get('app_config', {}))

        # 跨域访问支持
        self.app.config.update(self.server_config.get('cors_config', {}))
        # 是否开启http trace方法支持
        if self.server_config.get('auto_trace', False):
            self.app.config.HTTP_AUTO_TRACE = True

        # 是否开启OpenAPI文档生成
        if self.server_config.get('oas', False):
            self.app.config.OAS = True
            self.app.config.update(**self.server_config.get('oas_config', {}))
        else:
            # 不开启文档生成
            self.app.config.OAS = False

        Extend(self.app)

        # 日志对象的处理
        self.logger = logger
        if self.logger is None:
            self.logger = sanic_logger
        self.app.ctx.logger = self.logger

        # 事件执行
        self.before_server_start = before_server_start
        self.after_server_start = after_server_start
        self.before_server_stop = before_server_stop
        self.after_server_stop = after_server_stop

        # 安全相关
        self.support_auths = {} if support_auths is None else support_auths

        # 内部控制参数
        self._status_lock = threading.RLock()  # 状态更新的线程锁
        self._status = 'stop'  # 服务器状态, running-运行中, stop-停止
        self._thread = None  # 正在运行的线程对象
        self._is_before_server_stop_runned = True  # 标记结束前函数是否已执行
        self._is_after_server_stop_runned = True  # 标记结束后函数是否已执行

        # 添加服务生命周期的监听服务
        if self.before_server_start is not None:
            self.app.register_listener(self._before_server_start, 'before_server_start')
        if self.after_server_start is not None:
            self.app.register_listener(self._after_server_start, 'after_server_start')

        if not self.server_config.get('run_in_thread', True):
            # 线程执行模式无法处理结束的函数, 需要自行处理
            if self.before_server_stop is not None:
                self.app.register_listener(self._before_server_stop, 'before_server_stop')
            if self.after_server_stop is not None:
                self.app.register_listener(self._after_server_stop, 'after_server_stop')

        # 区别对待不使用asgi启动的处理
        if not self.server_config.get('use_asgi', False):
            self.server_config['run_config']['debug'] = False  # 线程启动不支持debug模式
            self.server_config['run_config']['register_sys_signals'] = False  # 线程启动需要把信号注册去掉
            if self.server_config.get('run_in_thread', True):
                self.server_config['run_config']['workers'] = 1  # 线程启动模式工作线程只支持1个

        # 将自己加入已初始化的服务器对象全局变量
        INIT_SANIC_SERVER[app_name] = self

    def __del__(self):
        """
        析构函数
        """
        # 将自己从已初始化的服务器对象全局变量中移除
        INIT_SANIC_SERVER = self.get_init_server_dict()
        INIT_SANIC_SERVER.pop(self.app_name)

        # 判断是否服务还在运行, 关闭服务
        if self._status == 'running':
            self.app.stop()
            del self.app

    #############################
    # 可用函数
    #############################
    @property
    def status(self) -> str:
        """
        获得服务器运行状态

        @property {str} - 运行状态, running-运行中, stop-停止, stoping-正在停止, starting-正在启动
        """
        return self._status

    def start(self, is_asyn: bool = False, sleep_time: float = 0.5):
        """
        启动Sanic服务

        @param {bool} is_asyn=False - 是否异步处理, 如果是则直接返回
        @param {float} sleep_time=0.5 - 同步处理的每次循环检测状态的睡眠时间, 单位为秒
        """
        _run_in_thread = self.server_config.get('run_in_thread', True)
        # 只有线程启动模式支持异步启动处理
        if not _run_in_thread and is_asyn:
            raise RuntimeError('only run_in_thread mode support async start')

        # 判断服务是否已运行
        self._status_lock.acquire()
        try:
            if self._status != 'stop':
                raise RuntimeError('SanicServer [%s] already running!' % self.app_name)

            # 将运行状态置为正在启动
            self._status = 'starting'
            self._is_before_server_stop_runned = False
            self._is_after_server_stop_runned = False
        finally:
            self._status_lock.release()

        if not _run_in_thread:
            # 直接执行启动动作
            self._server_run_fun()
        else:
            # 线程启动模式
            self._status_lock.acquire()
            try:
                # 启动运行线程
                self._thread = threading.Thread(
                    target=self._server_run_fun,
                    name='Thread-SanicServer-Running-%s' % self.app_name
                )
                self._thread.setDaemon(True)
                self._thread.start()

                # 循环等待服务启动成功
                while self._status == 'starting':
                    if self.app.state.is_started:
                        self._status = 'running'
                        break
                    else:
                        gevent.sleep(sleep_time)
                        continue
            finally:
                self._status_lock.release()

            if not is_asyn:
                # 同步处理, 一直检查状态直到退出
                try:
                    while self._status != 'stop':
                        gevent.sleep(sleep_time)
                except KeyboardInterrupt:
                    # 遇到键盘退出情况, 结束运行
                    self.stop()

    def stop(self):
        """
        关闭Sanic服务
        """
        _run_in_thread = self.server_config.get('run_in_thread', True)
        if not _run_in_thread:
            raise RuntimeError('only run_in_thread mode support stop')

        # 判断服务是否已运行
        self._status_lock.acquire()
        try:
            if self._status != 'running':
                raise RuntimeError('server is not running')

            # 执行关闭前操作
            self._status = 'stoping'
            if not self._is_before_server_stop_runned and self.before_server_stop is not None:
                AsyncTools.sync_run_coroutine(
                    self.before_server_stop(self)
                )

            # 直接结束线程
            RunTool.stop_thread(self._thread)
            self._status = 'stop'

            # 执行关闭后操作
            if not self._is_after_server_stop_runned and self.after_server_stop is not None:
                AsyncTools.sync_run_coroutine(self.after_server_stop(self))

        finally:
            self._status_lock.release()

    def add_route_by_class(self, class_objs: list, blacklist: list = None, class_name_mapping: dict = None,
                           url_base: str = 'api', version=None):
        """
        通过类对象动态增加路由

        @param {list} class_objs - Api类对象清单
        @param {list} blacklist=None - 禁止添加的服务黑名单, 格式为"类名/函数名"
        @param {dict} class_name_mapping=None - 类名映射, 可以根据这个改变访问url的路径, key为真实类名, value为映射后的类名
        @param {str} url_base='api' - 路由开始的基础url
        @param {int｜float|str} version=None - 指定路由的版本, 则路由变为"/v{version}/url"
        """
        SanicTool.add_route_by_class(
            self.app, class_objs, blacklist=blacklist, class_name_mapping=class_name_mapping,
            url_base=url_base, version=version
        )

    def add_route(self, url: str, func, name: str = None,
                  with_para: bool = False, methods: list = None, version=None):
        """
        添加指定路由

        @param {str} url - 路由url, 例如'/test'
        @param {function} func - 要添加路由的函数
        @param {str} name=None - 路由标识, 如果不传默认使用函数名(会存在函数名相同导致异常的情况)
        @param {bool} with_para=False - 路由是否根据函数添加入参
        @param {list} methods=None - 指定路由支持的方法, 如果不传代表支持所有方法
        @param {int｜float|str} version=None - 指定路由的版本, 则路由变为"/v{version}/url"
        """
        SanicTool.add_route(
            self.app, url=url, func=func, name=name, with_para=with_para, methods=methods
        )

    #############################
    # 内部函数
    #############################
    def _server_run_fun(self):
        """
        启动服务器的线程函数
        """
        try:
            # 判断是否已有路由, 如果没有则添加默认路由(否则无法正常启动)
            if len(self.app.router.routes) == 0:
                self.add_route(
                    '/', self.default_index_handler, self.app_name + '.default_index_handler'
                )

            # 启动服务
            _run_config = self.server_config.get('run_config', {})
            self.app.run(**_run_config)
        finally:
            # 更新状态
            self._status = 'stop'

    async def _before_server_start(self, *args, **kwargs):
        """
        服务启动前执行的函数
        """
        _resp = self.before_server_start(self)
        if isawaitable(_resp):
            _resp = await _resp

    async def _after_server_start(self, *args, **kwargs):
        """
        服务启动后函数
        """
        self._status_lock.acquire()
        try:
            self._status = 'running'  # 更新状态为运行中
        finally:
            self._status_lock.release()
        _resp = self.after_server_start(self)  # 执行启动后运行函数
        if isawaitable(_resp):
            _resp = await _resp

    async def _before_server_stop(self, *args, **kwargs):
        """
        服务关闭前执行函数
        """
        self._is_before_server_stop_runned = True
        _resp = self.before_server_stop(self)
        if isawaitable(_resp):
            _resp = await _resp

        self._status_lock.acquire()
        try:
            self._status = 'stoping'  # 更新状态为关闭中
        finally:
            self._status_lock.release()

    async def _after_server_stop(self, *args, **kwargs):
        """
        服务关闭后执行的函数
        """
        self._is_after_server_stop_runned = True

        _resp = self.after_server_stop(self)
        if isawaitable(_resp):
            _resp = await _resp


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    # 打印版本信息
    print(('模块名: %s  -  %s\n'
           '作者: %s\n'
           '发布日期: %s\n'
           '版本: %s' % (__MOUDLE__, __DESCRIPT__, __AUTHOR__, __PUBLISH__, __VERSION__)))

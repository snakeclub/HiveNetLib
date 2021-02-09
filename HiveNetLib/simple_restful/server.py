#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
# Copyright 2019 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
利用Flask实现的简单Restful Api Server模块

@module server
@file server.py
"""

import os
import sys
import inspect
import uuid
import time
import datetime
import logging
import math
import threading
from functools import wraps
from collections import OrderedDict
# 根据当前文件路径将包路径纳入，在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir, os.path.pardir)))
# 动态安装包
import HiveNetLib.deps_tool as deps_tool
try:
    import requests
except ImportError:
    deps_tool.install_package('requests')
    import requests
process_install_flask = False
while True:
    try:
        from flask.helpers import locked_cached_property
        from flask.logging import create_logger
        from flask.wrappers import Response
        from flask import Flask, request, jsonify, session
        from werkzeug.routing import Rule
        from flask_cors import CORS
        break
    except ImportError:
        if not process_install_flask:
            deps_tool.install_package('flask')
            deps_tool.install_package('flask-cors')
            deps_tool.install_package('flask-restful')
            deps_tool.install_package('werkzeug')
            process_install_flask = True
            continue
        raise
try:
    import gevent
    from gevent import pywsgi
except ImportError:
    deps_tool.install_package('gevent')
    import gevent
    from gevent import pywsgi
# 自有包引用
from HiveNetLib.base_tools.run_tool import RunTool
from HiveNetLib.simple_restful.cryptography import HCrypto
from HiveNetLib.simple_restful.auth import TokenAuth, AppKeyAuth


__MOUDLE__ = 'server'  # 模块名
__DESCRIPT__ = u'利用Flask实现的简单Restful Api Server模块'  # 模块描述
__VERSION__ = '0.1.0'  # 版本
__AUTHOR__ = u'黎慧剑'  # 作者
__PUBLISH__ = '2020.11.28'  # 发布日期


class FlaskServerExit(SystemExit):
    """
    自定义异常类，用于中止FlaskServer
    """
    pass


class FlaskWithLogger(Flask):
    """
    自定义Flask的logger设置
    """
    _logger = None  # 自定义的logger

    @locked_cached_property
    def logger(self):
        """A standard Python :class:`~logging.Logger` for the app, with
        the same name as :attr:`name`.

        In debug mode, the logger's :attr:`~logging.Logger.level` will
        be set to :data:`~logging.DEBUG`.

        If there are no handlers configured, a default handler will be
        added. See :doc:`/logging` for more information.

        .. versionchanged:: 1.1.0
            The logger takes the same name as :attr:`name` rather than
            hard-coding ``"flask.app"``.

        .. versionchanged:: 1.0.0
            Behavior was simplified. The logger is always named
            ``"flask.app"``. The level is only set during configuration,
            it doesn't check ``app.debug`` each time. Only one format is
            used, not different ones depending on ``app.debug``. No
            handlers are removed, and a handler is only added if no
            handlers are already configured.

        .. versionadded:: 0.3
        """
        if self._logger is None:
            self._logger = create_logger(self)

        return self._logger


class FlaskTool(object):
    """
    Flash工具类，提供路由，内容解析等通用处理功能
    """

    @classmethod
    def add_route(cls, app: Flask, url: str, func, endpoint: str = None,
                  with_para: bool = False, methods: list = None):
        """
        添加指定路由

        @param {Flask} app - 要添加路由的服务器
        @param {str} url - 路由url, 例如'/test'
        @param {function} func - 要添加路由的函数
        @param {str} endpoint=None - 路由标识，如果不传默认使用函数名(会存在函数名相同导致异常的情况)
        @param {bool} with_para=False - 路由是否根据函数添加入参
        @param {list} methods=None - 指定路由支持的方法，如果不传代表支持所有方法
        """
        _route = url if url == '/' else url.rstrip('/')  # 去掉最后的'/'
        _methods = methods
        _endpoint = endpoint if endpoint is not None else RunTool.get_function_name(
            func, is_with_class=True, is_with_module=True
        )

        # 判断endpoint是否重复
        if _endpoint in app.view_functions.keys():
            raise RuntimeError('endpoint [%s] exists!' % _endpoint)

        if with_para:
            # 根据函数入参处理路由
            _para_list = RunTool.get_function_parameter_defines(func)
            for _para in _para_list:
                if _para['name'] == 'methods':
                    # 指定了处理方法
                    _methods = _para['default']
                elif _para['name'] in ('self', 'cls'):
                    # 不处理 self 和 cls 入参
                    continue
                elif _para['type'] not in ('VAR_POSITIONAL', 'VAR_KEYWORD'):
                    # 不处理 *args及**kwargs参数
                    _type = ''
                    if _para['annotation'] == int:
                        _type = 'int:'
                    elif _para['annotation'] == float:
                        _type = 'float:'

                    _route = '%s/<%s%s>' % (_route, _type, _para['name'])

        # 创建路由
        app.url_map.add(
            Rule(_route, endpoint=_endpoint, methods=_methods)
        )
        # 加入路由
        app.view_functions[_endpoint] = func

    @classmethod
    def add_route_by_class(cls, app: Flask, class_objs: list, blacklist: list = None, class_name_mapping: dict = None,
                           url_base: str = 'api', ver_is_new: bool = True):
        """
        通过类对象动态增加路由

        @param {Flask} app - 要增加服务的Flask应用
        @param {list} class_objs - Api类对象清单(可以支持传入类对象，也可以支持传入类实例)
        @param {list} blacklist=None - 禁止添加的服务黑名单, 格式为"类名/函数名"
        @param {dict} class_name_mapping=None - 类名映射, 可以根据这个改变访问url的路径, key为真实类名, value为映射后的类名
        @param {str} url_base='api' - 路由开始的基础url
        @param {bool} ver_is_new=True - 导入版本为最新, 如果为True, 代表有版本号的情况下也会创建一个非版本访问的路由
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
                    _endpoint = '%s.%s' % (_class_name, _name)
                    if url_base == '':
                        # 忽略前置
                        _route = '{$ver$}/%s/%s' % (_class_name, _name)
                    else:
                        _route = '/%s{$ver$}/%s/%s' % (url_base, _class_name, _name)
                    _methods = None
                    _ver = ''
                    _para_list = RunTool.get_function_parameter_defines(_value)
                    for _para in _para_list:
                        if _para['name'] == 'methods':
                            # 指定了处理方法
                            _methods = _para['default']
                        elif _para['name'] == 'ver':
                            # 有指定ver的入参，在路由api后面进行变更
                            _ver = '/<ver>'
                        elif _para['name'] == 'self' and _instance is not None:
                            # 不处理实例对象的self入参
                            continue
                        elif _para['type'] not in ('VAR_POSITIONAL', 'VAR_KEYWORD'):
                            # 不处理 *args及**kwargs参数
                            _type = ''
                            if _para['annotation'] == int:
                                _type = 'int:'
                            elif _para['annotation'] == float:
                                _type = 'float:'

                            _route = '%s/<%s%s>' % (_route, _type, _para['name'])

                    # 创建路由
                    app.url_map.add(
                        Rule(_route.replace('{$ver$}', _ver), endpoint=_endpoint, methods=_methods)
                    )
                    if _ver != '' and ver_is_new:
                        # 也支持不传入版本的情况
                        app.url_map.add(
                            Rule(_route.replace('{$ver$}', ''),
                                 endpoint=_endpoint, methods=_methods)
                        )

                    # 对于实例对象，获取真实的函数对象
                    if _instance is not None:
                        _value = getattr(_instance, _name)

                    # 加入路由
                    app.view_functions[_endpoint] = _value

    @classmethod
    def db_connect(cls, f=None, db_connect_fun=None, db_connect_para: dict = None, db_close_fun=None):
        """
        连接及关闭数据库的修饰符函数
        注: 该修饰符会将数据库连接对象放入调用函数的 db_connection 入参中, 因此注意入参需要有该参数，或使用**kwargs

        @param {function} f - 要调用的函数
        @param {function} db_connect_fun - 连接数据库并返回可用连接对象的函数，函数定义如下：
            db_connect_fun() {
                ...
                return db_connection
            }
        @param {dict} db_connect_para=None - 调用db_connect_fun的KV入参
        @param {function} db_close_fun=None - 关闭数据库连接对象的函数，如果不穿代表不关闭，函数定义如下：
            db_close_fun(db_connection) {}

        @example 在 login 中打开数据库连接，使用后关闭数据库连接
            class RestfulApiClass(object):
                @classmethod
                @FlaskTool.db_connect(db_connect_fun=db_connect_fun, db_close_fun=db_close_fun)
                def login(user_name, methods=['POST'], **kwargs):
                    ...
                    # 注意 db_connection 的对象类型和使用方法依赖于 db_connect_fun 的返回，并非统一
                    kwargs['db_connection'].execute_sql(...)
                    ...
        """
        if f is not None and db_connect_fun is None:
            raise ValueError('db_connect_fun should not None!')

        def db_internal(f):
            @wraps(f)
            def decorated(*args, **kwargs):
                # 连接数据库
                _db_connect_para = {} if db_connect_para is None else db_connect_para
                _db_connection = db_connect_fun(**_db_connect_para)

                # 将连接对象放入函数的执行参数 db_connection 中
                kwargs['db_connection'] = _db_connection

                # 执行函数
                try:
                    _ret = f(*args, **kwargs)
                finally:
                    if db_close_fun is not None:
                        db_close_fun(_db_connection)

                # 返回执行结果
                return _ret
            return decorated

        if f:
            return db_internal(f)
        return db_internal

    @classmethod
    def log(cls, f=None, get_logger_fun=None, get_logger_para: dict = None, logger_extra: dict = None,
            logging_level: int = logging.DEBUG,
            chain_logging: bool = True, trace_id_generater=None, enconding: str = 'utf-8',
            data_len_max: int = 2000):
        """
        进行API接口日志记录的修饰符函数
        注: 该修饰符会将日志对象及日志对象调用扩展参数放入调用函数的 logger, logger_extra, logging_level 入参中,
            因此注意入参需要有该参数，或使用**kwargs

        @param {function} f - 要调用的函数
        @param {function} get_logger_fun - 获取日志对象的函数，格式为:
            get_logger_fun() {
                ...
                return logger
            }
        @param {dict} get_logger_para=None - 调用get_logger_fun的KV入参
        @param {dict} logger_extra=None - 调用日志记录的扩展参数
        @param {int} logging_level=logging.DEBUG - 记录日志的日志级别
        @param {bool} chain_logging=True - 是否记录API接口的调用链日志
        @param {function} trace_id_generater=None - 调用链日志生成trace_id的生成器函数，格式为:
            trace_id_generater(request){
                # request 为请求报文的 request 对象(Flask)
                ...
                return trace_id
            }
        @param {str} enconding='utf-8' - 通讯报文的编码
        @param {int} data_len_max=2000 - 内容打印长度的限制

        @example  指定记录API调用链日志
            class RestfulApiClass(object):
                @classmethod
                @FlaskTool.log(get_logger_fun=get_logger_fun)
                def login(user_name, methods=['POST'], **kwargs):
                    ...
                    # 记录自身日志
                    kwargs['logger'].log(kwargs['logging_level'], log_str, extra=kwargs['logger_extra'])
                    ...

            可以跟FlaskServer结合, 使用FlaskServer的logger:
            @FlaskTool.log(get_logger_fun=FlaskServer.get_logger_fun, get_logger_para={'app_name': 'test_server'})
            def login(user_name, methods=['POST'], **kwargs):
                ...
        """
        if f is not None and get_logger_fun is None:
            raise ValueError('get_logger_fun should not None!')

        def log_internal(f):
            @wraps(f)
            def decorated(*args, **kwargs):
                # 获取日志对象及参数
                _get_logger_para = {} if get_logger_para is None else get_logger_para
                _logger = get_logger_fun(**_get_logger_para)
                _logger_extra = {} if logger_extra is None else logger_extra

                # 添加到函数调用入参
                kwargs['logger'] = _logger
                kwargs['logger_extra'] = _logger_extra
                kwargs['logging_level'] = logging_level

                # 登记请求日志
                if chain_logging and _logger is not None:
                    _fun_name = f.__name__
                    _start_time = datetime.datetime.now()
                    _IP = request.remote_addr
                    _trace_id = str(
                        uuid.uuid1()
                    ) if trace_id_generater is None else trace_id_generater(request)
                    _enconding = enconding if request.charset == '' else request.charset
                    _log_str = '[API-FUN:%s][IP:%s][INF-RECV][TRACE-API:%s]%s %s\n%s%s' % (
                        _fun_name, _IP, _trace_id, request.method, request.path,
                        str(request.headers),
                        str(request.data, encoding=_enconding) if (request.mimetype.startswith('text/') or request.mimetype in [
                            'application/json', 'application/xml']) and len(request.data) <= data_len_max else ''
                    )
                    _logger.log(
                        logging_level, _log_str, extra=_logger_extra
                    )

                # 执行函数
                _ret = f(*args, **kwargs)

                # 登记返回日志
                if chain_logging and _logger is not None:
                    _resp = _ret
                    if type(_ret) in (list, tuple):
                        _resp = _ret[0]

                    if type(_resp) != Response:
                        _resp = jsonify(_resp)

                    _enconding = enconding if _resp.charset == '' else _resp.charset
                    _log_str = '[API-FUN:%s][IP:%s][INF-RET][TRACE-API:%s][USE:%s]%s%s' % (
                        _fun_name, _IP, _trace_id, str(
                            (datetime.datetime.now() - _start_time).total_seconds()),
                        str(_resp.headers),
                        str(_resp.data, encoding=_enconding) if (_resp.mimetype.startswith('text/') or _resp.mimetype in [
                            'application/json', 'application/xml']) and len(request.data) <= data_len_max else ''
                    )
                    _logger.log(
                        logging_level, _log_str, extra=_logger_extra
                    )

                # 返回处理结果
                return _ret
            return decorated

        if f:
            return log_internal(f)
        return log_internal

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
                @FlaskTool.auth_required(get_auth_fun=get_auth_fun)
                def login(user_name, methods=['POST'], **kwargs):
                    ...

            可以跟FlaskServer结合, 使用FlaskServer的logger:
            @FlaskTool.log(get_auth_fun=FlaskServer.get_auth_fun, get_auth_para={'auth_name': 'AppKeyAuth', 'app_name': 'test_server'})
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

    @classmethod
    def support_object_resp(cls, func):
        """
        支持函数直接返回Python对象的修饰符
        注：正常函数应该返回标准二元组

        @param {function} func - 修饰符处理的函数

        @example Restful函数返回非字符串格式内容
            @FlaskTool.support_object_resp
            def func(a, b):
                ...
                return {'a':'value'}
        """
        @wraps(func)
        def wrapper(*args, **kwargs):
            _ret = func(*args, **kwargs)
            _status = 200
            if _ret not in (tuple, list):
                _resp_msg = _ret
            else:
                _status = _ret[1]
                _resp_msg = _ret[0]

            # 处理非字符串的转换
            if type(_resp_msg) != Response:
                _resp_msg = jsonify(_resp_msg)

            return (_resp_msg, _status)
        return wrapper


class FlaskServer(object):
    """
    Flask服务处理
    """
    #############################
    # 静态函数
    #############################

    @classmethod
    def get_init_flask_server_dict(cls) -> OrderedDict:
        """
        获取已经初始化的FlaskServer访问字典

        @returns {OrderedDict} - 返回字典
        """
        INIT_FLASK_SERVER = RunTool.get_global_var('INIT_FLASK_SERVER')
        if INIT_FLASK_SERVER is None:
            INIT_FLASK_SERVER = OrderedDict()
            RunTool.set_global_var('INIT_FLASK_SERVER', INIT_FLASK_SERVER)

        return INIT_FLASK_SERVER

    @classmethod
    def get_init_flask_server(cls, app_name: str = None):
        """
        获取已经初始化的FlaskServer对象

        @param {str} app_name=None - 要获取的FlaskServer的app_name, 如果不传默认取第一个

        @returns {FlaskServer} - 获取到的对象
        """
        INIT_FLASK_SERVER = cls.get_init_flask_server_dict()
        if app_name is None:
            return list(INIT_FLASK_SERVER.values())[0]
        else:
            return INIT_FLASK_SERVER[app_name]

    @classmethod
    def get_logger_fun(cls, app_name: str = None):
        """
        获取FlaskServer的logger对象
        注: 该函数主要用于 FlaskTool 的 log 修饰符入参

        @param {str} app_name=None - 要获取的FlaskServer的app_name, 如果不传默认取第一个
        """
        return cls.get_init_flask_server(app_name=app_name).logger

    @classmethod
    def get_auth_fun(cls, auth_name: str = '', app_name: str = None):
        """
        获取FlaskServer支持的Auth实例对象
        注: 该函数主要用于 FlaskTool 的 auth_required 修饰符入参

        @param {str} auth_name='' - 验证对象类型名(比如类名, 具体取决于FlaskServer的初始化参数)
        @param {str} app_name=None - 要获取的FlaskServer的app_name, 如果不传默认取第一个
        """
        _server = cls.get_init_flask_server(app_name=app_name)
        return _server.support_auths[auth_name]

    #############################
    # 构造及析构函数
    #############################
    def __init__(self, app_name: str, server_config: dict = None, support_auths: dict = None,
                 before_server_start=None, after_server_start=None,
                 before_server_stop=None, after_server_stop=None, logger=None, **kwargs):
        """
        初始化FlaskServer

        @param {str} app_name - Flask服务器名称
        @param {dict} server_config=None - 服务器配置字典，定义如下:
            app_config {dict} - Flask初始化参数字典(请参考官方Flask文档), 常用参数包括:
                root_path {str} - Flask应用的资源根目录, 默认会获取所执行应用的根目录, 可以手工指定
                static_folder {str} - 静态资源目录, 为 root_path 的相对路径, 默认为'static'
                    注: 如果指定绝对路径则会与 root_path 路径无关
                static_url_path {str} - 静态资源的访问url前缀, 行为表现如下:
                    未传值的情况:
                    1. 如果static_folder未被指定, 那么static_url_path取为static, 也就是通过'/static/index.html'访问静态资源
                    2. 如果static_folder被指定了, 那么static_url_path等于static_folder的最后一级文件夹名称, 也就是通过'/最后一级文件夹/index.html'访问静态资源
                    有传值的情况:
                    1. static_url_path='', 代表直接通过根路径'/'访问静态资源，也就是通过'/index.html'访问静态资源
                    2. static_url_path='path/path2' 或 '/path/path2', 将通过'/path/path2/index.html'访问静态资源
                    3. static_url_path='/path/', 路径前面不带'/'的情况，将通过'/path/index.html'访问静态资源
            cors_config {dict} - flask_cors的配置参数字典，例如:
                supports_credentials {bool} - 是否支持跨域
            flask_run {dict} - FlaskServer运行参数字典(请参考官方Flask文档), 常用参数包括:
                host {str} - 绑定的主机地址，可以为 '127.0.0.1' 或不传
                port {int} - 监听端口, 默认为 5000
                threaded {bool} - 是否启动多线程, 默认为 True
                processes {int} - 进程数, 默认为 1, 如果设置进程数大于1，必须将threaded设置为False
                ssl_context {str|tuple} - 使用https, 有两种使用方式
                    1. ssl_context='adhoc': 使用 pyOpenSSL 自带证书, 注意需进行安装 'pip install pyOpenSSL'
                    2. ssl_context=('/certificates/server.crt', '/certificates/server.key'): 使用指定路径的证书文件
                        示例: ssl_context=('/certificates/server-cert.pem', '/certificates/server-key.pem')
            debug {bool} - 是否debug模式，默认False
            send_file_max_age_default {int} - 单位为秒，发送文件功能最大的缓存超时时间，默认为12小时, 如果要调试静态文件，可以设置为1
            templates_auto_reload {bool} - 是否自动重新加载模版，默认为False，如果要调试模版，可以设置为True
            json_as_ascii {bool} - josn字符串是否采取ascii模式, 默认为True, 如果需要json显示中文需传入False
            max_upload_size {float} - 上传文件的最大大小，单位为MB
            use_wsgi {bool} - 是否使用WSGIServer, 默认为False
                注意: 如果使用wsgi， 处理函数内部请勿使用time.sleep, 否则会造成堵塞, 请统一调整为使用gevent.sleep
        @param {dict} support_auths=None - 服务器支持的验证对象字典, key为验证对象类型名(可以为类名), value为验证对象实例对象
            注意: 支持的auth对象必须有auth_required这个修饰符函数
        @param {function} before_server_start=None - 服务器启动前执行的函数对象，传入服务自身（self）
        @param {function} after_server_start=None - 服务器启动后执行的函数对象，传入服务自身（self）
        @param {function} before_server_stop=None - 服务器关闭前执行的函数对象，传入服务自身（self）
        @param {function} after_server_stop=None - 服务器关闭后执行的函数对象，传入服务自身（self）
        @param {Logger} logger=None - 日志对象
        @param {kwargs} - 扩展参数
        """
        # 判断服务器名是否重复
        INIT_FLASK_SERVER = self.get_init_flask_server_dict()
        if app_name in INIT_FLASK_SERVER.keys():
            raise RuntimeError('Init flask server [%s] already exists!' % app_name)

        # 参数处理
        self.app_name = app_name
        self.logger = logger
        self.server_config = {} if server_config is None else server_config

        # 创建应用
        self.app = FlaskWithLogger(app_name, **self.server_config.get('app_config', {}))
        CORS(self.app, **self.server_config.get('cors_config', {}))

        # Flask应用配置
        if self.logger is not None:
            self.app._logger = self.logger
        else:
            # 不传logger时, 使用flask默认的logger
            self.logger = self.app.logger
        self.app.debug = self.server_config.get('debug', False)
        self.app.send_file_max_age_default = datetime.timedelta(
            seconds=self.server_config.get('send_file_max_age_default', 12 * 60 * 60)
        )
        _templates_auto_reload = self.server_config.get('templates_auto_reload', False)
        if _templates_auto_reload:
            self.app.jinja_env.auto_reload = True
            self.app.templates_auto_reload = True
        self.app.config['JSON_AS_ASCII'] = self.server_config.get('json_as_ascii', True)
        if 'max_upload_size' in self.server_config.keys():
            self.app.config['MAX_CONTENT_LENGTH'] = math.floor(
                self.server_config['max_upload_size'] * 1024 * 1024
            )
        self.use_wsgi = self.server_config.get('use_wsgi', False)

        # 事件执行
        self.before_server_start = before_server_start
        self.after_server_start = after_server_start
        self.before_server_stop = before_server_stop
        self.after_server_stop = after_server_stop

        # 在收到第一个请求前执行的函数(在多进程的情况下没有调用，可能是Flask的bug)
        self.app.before_first_request_funcs.append(self._update_running_status)

        # 安全相关
        self.support_auths = {} if support_auths is None else support_auths

        # 内部控制参数
        self._status_lock = threading.RLock()  # 状态更新的线程锁
        self._status = 'stop'  # 服务器状态，running-运行中, stop-停止
        self._thread = None  # 正在运行的线程对象

        # 将自己加入已初始化的服务器对象全局变量
        INIT_FLASK_SERVER[app_name] = self

    def __del__(self):
        """
        析构函数
        """
        # 将自己从已初始化的服务器对象全局变量中移除
        INIT_FLASK_SERVER = self.get_init_flask_server_dict()
        INIT_FLASK_SERVER.pop(self.app_name)

        # 判断是否服务还在运行, 关闭服务
        if self._status == 'running':
            self.stop()

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
        启动Flask服务

        @param {bool} is_asyn=False - 是否异步处理, 如果是则直接返回
        @param {float} sleep_time=0.5 - 同步处理的每次循环检测状态的睡眠时间，单位为秒
        """
        # 判断服务是否已运行
        self._status_lock.acquire()
        try:
            if self._status != 'stop':
                raise RuntimeError('FlaskServer [%s] already running!' % self.app_name)

            # 将运行状态置为正在启动
            self._status = 'starting'

            # 启动运行线程
            self._thread = threading.Thread(
                target=self._server_run_fun,
                name='Thread-FlaskServer-Running-%s' % self.app_name
            )
            self._thread.setDaemon(True)
            self._thread.start()

            # 循环等待服务启动成功
            if not self.use_wsgi and self.server_config.get('flask_run', {}).get('processes', 1) > 1:
                # 多进程模式由于flask的bug，无法使用标准做法验证，采取等待一段时间后认为进程启动的方式
                gevent.sleep(2)
                if self._status == 'starting':
                    self._status = 'running'
            else:
                _url = '%s://%s:%d/' % (
                    'https' if 'ssl_context' in self.server_config.get(
                        'flask_run', {}).keys() else 'http',
                    self.server_config.get('flask_run', {}).get('host', '127.0.0.1'),
                    self.server_config.get('flask_run', {}).get('port', 5000)
                )
                while self._status == 'starting':
                    # 向Flask发送根目录的请求，触发状态更新
                    gevent.sleep(sleep_time)
                    requests.get(_url)

            # 服务器成功启动后执行事件
            if self.after_server_start is not None:
                self.after_server_start(self)
        finally:
            self._status_lock.release()

        if not is_asyn:
            # 同步处理，一直检查状态直到退出
            try:
                while self._status != 'stop':
                    gevent.sleep(sleep_time)
            except KeyboardInterrupt:
                # 遇到键盘退出情况，调用stop结束运行
                self.stop()
                raise

    def stop(self, overtime: float = 0, sleep_time: int = 0.5) -> bool:
        """
        停止服务运行

        @param {float} overtime=0 - 等待超时时间, 单位为秒, 0代表一直不超时
        @param {float} sleep_time=0.5 - 每次等待睡眠时间，单位为秒

        @returns {bool} - 停止状态，True为停止成功，False为等待停止超时
        """
        self._status_lock.acquire()
        try:
            if self._status != 'running':
                raise RuntimeError('FlaskServer [%s] is not running!' % self.app_name)

            # 执行事件
            if self.before_server_stop is not None:
                self.before_server_stop(self)

            # 向线程发送中止异常
            RunTool.async_raise(self._thread.ident, FlaskServerExit)

            # 更新状态为正在停止
            self._status = 'stoping'
        finally:
            self._status_lock.release()

        # 等待服务停止
        _start_time = datetime.datetime.now()
        while self._status != 'stop':
            if overtime > 0 and (datetime.datetime.now() - _start_time).total_seconds() > overtime:
                return False

            # 睡眠一段时间, 继续检查
            gevent.sleep(sleep_time)

        # 已经完全停止
        return True

    def add_route_by_class(self, class_objs: list, blacklist: list = None, class_name_mapping: dict = None,
                           url_base: str = 'api', ver_is_new: bool = True):
        """
        通过类对象动态增加路由

        @param {list} class_objs - Api类对象清单
        @param {list} blacklist=None - 禁止添加的服务黑名单, 格式为"类名/函数名"
        @param {dict} class_name_mapping=None - 类名映射, 可以根据这个改变访问url的路径, key为真实类名, value为映射后的类名
        @param {str} url_base='api' - 路由开始的基础url
        @param {bool} ver_is_new=True - 导入版本为最新, 如果为True, 代表有版本号的情况下也会创建一个非版本访问的路由
        """
        FlaskTool.add_route_by_class(
            self.app, class_objs, blacklist=blacklist, class_name_mapping=class_name_mapping,
            url_base=url_base, ver_is_new=ver_is_new
        )

    def add_route(self, url: str, func, endpoint: str = None,
                  with_para: bool = False, methods: list = None):
        """
        添加指定路由

        @param {str} url - 路由url, 例如'/test'
        @param {function} func - 要添加路由的函数
        @param {str} endpoint=None - 路由标识，如果不传默认使用函数名(会存在函数名相同导致异常的情况)
        @param {bool} with_para=False - 路由是否根据函数添加入参
        @param {list} methods=None - 指定路由支持的方法，如果不传代表支持所有方法
        """
        FlaskTool.add_route(
            self.app, url=url, func=func, endpoint=endpoint, with_para=with_para, methods=methods
        )

    #############################
    # 内部函数
    #############################
    def _server_run_fun(self):
        """
        启动服务器的线程函数
        """
        try:
            if self.before_server_start is not None:
                # 执行服务启动前执行函数
                self.before_server_start(self)

            # 启动服务
            _flask_run = self.server_config.get('flask_run', {})
            # 因为不在main线程启动Flask，所以不支持use_reloader参数
            _flask_run['use_reloader'] = False
            if self.use_wsgi:
                # 使用WSGIServer
                self._wsgi_server_start(_flask_run)
            else:
                # 使用原生方式启动
                self._flask_server_start(_flask_run)
        except FlaskServerExit:
            # 正常执行中止服务后的操作, 无需抛出异常
            pass
        finally:
            # 标记服务器运行状态为中止
            if self._status in ('stoping', 'running'):
                # 这个状态代表服务已正常启动过, 运行关闭服务后的事件函数
                if self.after_server_stop is not None:
                    self.after_server_stop(self)

            # 更新状态
            self._status = 'stop'

    def _update_running_status(self):
        """
        线程启动完成后更新状态为正在运行
        """
        self._status = 'running'

    def _wsgi_server_start(self, run_para: dict):
        """
        启动wsgi服务器的函数
        注：如果需改用其他wsgi服务器，请继承并重载该函数

        @param {dict} run_para - 启动参数
        """
        _ssl_args = dict()
        # keyfile='server.key', certfile='server.crt'
        _ssl_context = run_para.get('ssl_context', None)
        if _ssl_context is not None and type(_ssl_context) in (tuple, list):
            _ssl_args['certfile'] = _ssl_context[0]
            _ssl_args['keyfile'] = _ssl_context[1]
        _wsgi_server = pywsgi.WSGIServer(
            (run_para.get('host', ''), run_para.get('port', 5000)),
            application=self.app,
            **_ssl_args
        )
        _wsgi_server.serve_forever()

    def _flask_server_start(self, run_para: dict):
        """
        flask原生启动方式
        注：如果需改用其他启动方式，请继承并重载该函数

        @param {dict} run_para - 启动参数
        """
        self.app.run(**run_para)


class WebAuth(object):
    """
    网页登陆验证服务
    用户注册流程如下(需要考虑密码明文传输和保存不被泄露的问题):
        1. 客户端请求 salt 字符串和所需算法，送入客户端送入要注册的用户名 username;
        2. 服务端生成并返回salt字符串(随机), 进行缓存并返回salt
        3. 客户端按算法生成需要保存在服务器端的密码串，算法如下: HS = hamc(salt, uname+pwd)
        4. 客户端使用公钥对HS进行RSA加密，发送到服务器端
        5. 服务器端使用私钥进行RSA解密, 得到HS, 保存客户的密码信息: uname, HS, 加密算法
    用户登陆流程如下:
        1. 客户端请求salt字符串和随机数R, 送入登陆的用户名 uname
        2. 服务端从数据库中获取salt字符串，生成随机数R返回客户端
        3. 客户端按算法生成验证散列串: HC = hamc(R, hamc(salt, uname+pwd))
        4. 服务器收到验证散列串后, 从数据库获取加密密码串，按同样算法生成对应字符串进行比对: HC = hamc(R, HS)
        5. 验证通过后服务器端生成一个具备有效期的Token返回给客户端
        6. 客户端将Token保存到cookie中，在后续访问中使用token进行验证
    用户修改密码流程如下:
        1. 客户端请求salt字符串，送入客户端送入要注册的用户名 uname 和 修改密码标识;
        2. 服务端从数据库中获取salt字符串，生成随机数R，以及生成一个新的salt返回客户端
        3. 客户端按注册流程生成通过RSA加密的HS，以及按登陆流程生成验证散列HC，送给服务端
        4. 服务端进行原密码验证，验证通过后更新新密码
    """

    #############################
    # 构造函数
    #############################
    def __init__(self, **kwargs):
        """
        网页登陆验证服务

        @param {int} salt_len=8 - 盐字符串长度
        @param {str} algorithm='HMAC-SHA256' - 使用的密码加密算法名，支持算法如下
            MD5
            HMAC-SHA256
        @param {dict} algorithm_extend=None - 扩展算法支持, key为algorithm名, value为扩展的算法函数
            扩展函数定义如下: fun(value:str, key:str) -> str
        @param {function} check_username_fmt=None - 检查用户名规则是否正确, 不传则使用内部用户模块工具
        @param {function} check_username_exists=None - 检查用户名是否已存在, 不传则使用内部用户模块工具

        @param {int} embed_username_min_len=3 - 内嵌用户模块最小用户名长度
        @param {int} embed_username_max_len=12 - 内嵌用户模块最大用户名长度

        """
        self.para = kwargs
        self.salt_len = self.para.get('salt_len', 8)

        # 算法扩展支持
        self.algorithm_mapping = {
            'MD5': HCrypto.md5,
            'HMAC-SHA256': HCrypto.hmac_sha256
        }
        self.algorithm_mapping.update(self.para.get('algorithm_extend', {}))
        self.algorithm = self.para.get('algorithm', 'HMAC-SHA256')

        self.check_username_fmt = self.para.get('check_username_fmt', self._check_username_fmt)
        self.check_username_exists = self.para.get(
            'check_username_exists', self._check_username_exists
        )

        # 内嵌用户模块参数
        # 用户数据库, key为用户名, value为dict，定义如下:
        #   nickname {str} - 昵称
        #   status {str} - 用户状态, Normal - 正常, Locked - 已锁定, Delete - 已注销
        #   salt {str} - 盐字符串
        #   pwd {str} - 加密后的密码字符串
        #   algorithm {str} - 加密算法
        self._user_db = dict()
        self.embed_username_min_len = self.para.get('embed_username_min_len', 3)
        self.embed_username_max_len = self.para.get('embed_username_max_len', 12)

    #############################
    # 对外服务
    #############################
    @FlaskTool.support_object_resp
    def register(self, methods=['POST'], **kwargs):
        """
        注册请求服务

        @api {post} {json} /api/WebAuth/register register
        @body-in {str} interface_id - 接口id
        @body-in {str} host - 监听IP地址

        @body-out {str} interface_id - 接口id
        @body-out {str} status - 处理状态, 定义如下
            00000 - 成功
            13009 - 用户名格式错误
            13010 - 用户名已存在
        @body-out {str} msg - 处理状态对应的描述
        @body-out {str} register_id - 当前流程的注册id, 在确认注册时需由客户端提交
        @body-out {str} salt - 获取到的盐字符串
        @body-out {str} algorithm - 加密算法
        """
        _username = request.json['username']

        # 设置返回的字典
        _resp = {
            'interface_id': request.json.get('interface_id', ''),
            'status': '00000',
            'msg': '成功'
        }

        # 检查用户名规则及是否已存在
        if not self.check_username_fmt(_username):
            _resp['status'] = '13009'
            _resp['msg'] = '用户名格式错误'
            return _resp

        if self.check_username_exists(_username):
            _resp['status'] = '13010'
            _resp['msg'] = '用户名已存在'
            return _resp

        # 生成 register_id, salt
        _resp['register_id'] = str(uuid.uuid1())
        _resp['salt'] = HCrypto.generate_salt(str_len=self.salt_len)
        _resp['algorithm'] = self.algorithm

        # 临时信息存入session
        session['register_id'] = _resp['register_id']
        session['salt'] = _resp['salt']
        session['algorithm'] = _resp['algorithm']

        # 返回信息
        return _resp

    #############################
    # 内部函数
    #############################
    def _check_username_fmt(self, username: str) -> bool:
        """
        检查用户名规则是否正确

        @param {str} username - 要检查的用户名

        @returns {bool} - 检查规则是否通过
        """
        _len = len(username)
        if _len < self.embed_username_min_len or _len > self.embed_username_max_len:
            # 用户名长度检查未通过
            return False

        return True

    def _check_username_exists(self, username: str) -> bool:
        """
        检查用户名是否已存在

        @param {str} username - 要检查的用户名

        @returns {bool} - 用户名是否已存在
        """
        if username in self._user_db.keys():
            return True
        else:
            return False


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    # 打印版本信息
    print(('模块名：%s  -  %s\n'
           '作者：%s\n'
           '发布日期：%s\n'
           '版本：%s' % (__MOUDLE__, __DESCRIPT__, __AUTHOR__, __PUBLISH__, __VERSION__)))

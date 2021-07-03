#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
# Copyright 2019 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
支持SocketIO调用

@module socketio
@file socketio.py
"""

import os
import sys
import queue
import threading
from HiveNetLib.base_tools.run_tool import RunTool
# 根据当前文件路径将包路径纳入，在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir, os.path.pardir)))
from HiveNetLib.simple_restful.server import FlaskServer, FlaskServerExit
from HiveNetLib.simple_queue import MemoryQueue
# 动态安装包
import HiveNetLib.deps_tool as deps_tool
try:
    import gevent
except ImportError:
    deps_tool.install_package('gevent')
    import gevent
process_install_flask = False
while True:
    try:
        from flask_socketio import SocketIO, emit
        import socketio
        break
    except ImportError:
        if not process_install_flask:
            deps_tool.install_package('flask-socketio')
            process_install_flask = True
            continue
        raise


__MOUDLE__ = 'socketio'  # 模块名
__DESCRIPT__ = u'支持SocketIO调用'  # 模块描述
__VERSION__ = '0.1.0'  # 版本
__AUTHOR__ = u'黎慧剑'  # 作者
__PUBLISH__ = '2021.01.14'  # 发布日期


class SocketIOServer(FlaskServer):
    """
    SocketIO服务器
    注：直接继承自 FlaskServer
    注意：web请使用socket.io.js的3.x版本进行对接：https://cdnjs.cloudflare.com/ajax/libs/socket.io/3.0.4/socket.io.js
    """

    #############################
    # 重载构造函数
    #############################
    def __init__(self, app_name: str, server_config: dict = None, support_auths: dict = None,
                 before_server_start=None, after_server_start=None,
                 before_server_stop=None, after_server_stop=None, logger=None, **kwargs):
        """
        初始化SocketIOServer

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
            socketio_config {dict} - SocketIO初始化参数，具体支持的参数参考SocketIO文档,例如：
                'cors_allowed_origins': '*'  # 解决跨域访问问题
            flask_run {dict} - SocketIoServer运行参数字典(请参考官方socketio.run文档), 常用参数包括:
                host {str} - 绑定的主机地址，可以为 '127.0.0.1' 或不传
                port {int} - 监听端口, 默认为 5000
            debug {bool} - 是否debug模式，默认False
            send_file_max_age_default {int} - 单位为秒，发送文件功能最大的缓存超时时间，默认为12小时
            json_as_ascii {bool} - josn字符串是否采取ascii模式, 默认为True, 如果需要json显示中文需传入False
            max_upload_size {float} - 上传文件的最大大小，单位为MB
            use_wsgi {bool} - 是否使用WSGIServer, 默认为False
        @param {dict} support_auths=None - 服务器支持的验证对象字典, key为验证对象类型名(可以为类名), value为验证对象实例对象
            注意: 支持的auth对象必须有auth_required这个修饰符函数
        @param {function} before_server_start=None - 服务器启动前执行的函数对象，传入服务自身（self）
        @param {function} after_server_start=None - 服务器启动后执行的函数对象，传入服务自身（self）
        @param {function} before_server_stop=None - 服务器关闭前执行的函数对象，传入服务自身（self）
        @param {function} after_server_stop=None - 服务器关闭后执行的函数对象，传入服务自身（self）
        @param {Logger} logger=None - 日志对象
        @param {kwargs} - 扩展参数
        """
        # 执行父类构造函数
        super(SocketIOServer, self).__init__(
            app_name, server_config=server_config, support_auths=support_auths,
            before_server_start=before_server_start, after_server_start=after_server_start,
            before_server_stop=before_server_stop, after_server_stop=after_server_stop,
            logger=logger,
            **kwargs
        )

        # 设置SokcetIO
        self.socketio: SocketIO = SocketIO(
            app=self.app, **self.server_config.get('socketio_config', {}))

        # 其他变量
        self.bg_task_para = dict()  # 支持连接后执行后台任务的配置

    #############################
    # 重载WSGI服务器启动方式, 暂时仍用原生开发模式启动
    #############################

    def _wsgi_server_start(self, run_para: dict):
        """
        启动wsgi服务器的函数
        注：如果需改用其他wsgi服务器，请继承并重载该函数

        @param {dict} run_para - 启动参数
        """
        self.socketio.run(self.app, **run_para)

    def _flask_server_start(self, run_para: dict):
        """
        flask原生启动方式
        注：如果需改用其他启动方式，请继承并重载该函数

        @param {dict} run_para - 启动参数
        """
        self.socketio.run(self.app, **run_para)

    #############################
    # SocketIO的自有方法
    #############################
    @classmethod
    def broadcast(cls, event: str, data: dict, namespace: str = None, with_context_app=None):
        """
        发送消息给所有连接的客户端
        注意：该函数必须在绑定事件的函数内部使用

        @param {str} event - 事件名
        @param {dict} data - 要通知的数据字典
        @param {str} namespace=None - 命名空间, 例如'/'
        @param {Flask} with_context_app=None - 指定上下文的Flask App对象
            注: 解决 Working outside of application context 的问题
        """
        if with_context_app is None:
            emit(event, data, namespace=namespace, broadcast=True)
        else:
            with with_context_app.app_context():
                emit(event, data, namespace=namespace, broadcast=True)

    @classmethod
    def emit(cls, event, *args, **kwargs):
        """
        向客户端发送消息，是emit函数的直接映射
        注意：该函数必须在绑定事件的函数内部使用

        @param {str} event - 事件
        """
        _with_context_app = kwargs.get('with_context_app', None)
        if _with_context_app is None:
            emit(event, *args, **kwargs)
        else:
            with _with_context_app.app_context():
                emit(event, *args, **kwargs)

    def bind_on_event(self, event: str, func, namespace: str = None):
        """
        绑定指定函数为特定事件的处理函数

        @param {str} event - 事件名, 其中一些事件是标准事件, 例如:
            'connect' - 连接事件
            'disconnect' - 断开连接事件
        @param {function} func - 处理函数对象
        @param {str} namespace=None - 命名空间，例如'/test'
        """
        self.socketio.on_event(event, func, namespace=namespace)

    def bind_bg_task_on_connect(self, task_func, before_func=None, bg_type: str = 'each',
                                namespace: str = None):
        """
        绑定连接时的后台任务
        注：只支持注册一个, 并且需要注意 task_func 内部如果要sleep, 必须使用 socketio.sleep 而不是time.sleep,
            否则将会导致线程阻塞

        @param {function} task_func - 后台执行任务函数，如果是永久运行，需自行实现循环逻辑
        @param {function} before_func=None - 执行后台任务前需执行的操作函数
        @param {str} bg_type='each' - 后台任务执行类型
            'each' - 每个连接都执行
            'local' - 当前服务只执行一个
            'global' - 应用全局只执行一个
        @param {str} namespace=None - 命名空间，例如'/test'
        """
        self.bg_task_para = {
            'task_func': task_func,
            'before_func': before_func,
            'bg_type': bg_type,
            'lock': threading.Lock()
        }
        self.socketio.on_event('connect', self._bg_task_on_connect_func, namespace=namespace)

    #############################
    # 内部函数
    #############################
    def _bg_task_on_connect_func(self):
        """
        连接时的后台服务
        """
        if self.bg_task_para['before_func'] is not None:
            # 执行前面的函数
            self.bg_task_para['before_func']()

        _lock = None
        if self.bg_task_para['bg_type'] == 'local':
            _lock = self.bg_task_para['lock']
        elif self.bg_task_para['bg_type'] == 'global':
            _lock = RunTool.get_global_var('SOCKETIO_SERVER_BG_TASK_LOCK', default=threading.Lock())

        if _lock is None:
            self.socketio.start_background_task(self.bg_task_para['task_func'])
        else:
            # 限制只能启动一个
            with _lock:
                self.bg_task_para['bg_thread'] = self.socketio.start_background_task(
                    self.bg_task_para['task_func']
                )
                print('run task')


class SocketIOClient(object):
    """
    SocketIO简单客户端
    """

    #############################
    # 构造函数
    #############################
    def __init__(self, client_para: dict = None, **kwargs):
        """
        创建SocketIO简单客户端

        @param {dict} client_para - 客户端创建参数，参考python-socketio的创建参数
        """
        self.client_para = client_para if client_para is not None else {}
        self.socketio = socketio.Client(**self.client_para)
        self._thread = None  # 客户端连接等待线程
        self.bg_task_para = dict()  # 连接成功后的后台执行参数
        self.bg_emit_queue = MemoryQueue()  # 后台发送数据的公共队列

    def __del__(self):
        """
        析构函数
        """
        if self.socketio.connected:
            try:
                # 断开连接
                self.disconnect()
            except:
                pass

    #############################
    # 公共函数
    #############################
    def connect(self, url: str, headers={}, transports=None,
                namespaces=None, socketio_path='socket.io', is_asyn: bool = False):
        """
        连接服务器

        @param {str} url - 要连接的url地址, 例如'http://localhost:5000'
        @param {bool} is_asyn=False - 是否异步处理, 如果是则直接返回
        """
        if self.socketio.connected:
            raise RuntimeError('Client is already connected!')

        # 执行连接
        self.socketio.connect(
            url, headers=headers, transports=transports, namespaces=namespaces,
            socketio_path=socketio_path
        )

        if is_asyn:
            # 异步模式
            self._thread = threading.Thread(
                target=self.socketio.wait,
                name='Socketio-client-wait-thread'
            )
            self._thread.setDaemon(True)
            self._thread.start()
        else:
            # 同步模式， 等待连接中断
            self.socketio.wait()

    def disconnect(self):
        """
        关闭连接
        """
        if not self.socketio.connected:
            raise RuntimeError('Client is not connect!')

        # 尝试结束连接的后台线程
        try:
            _thread = self.bg_task_para.get('bg_thread', None)
            if _thread is not None:
                RunTool.stop_thread(_thread)
        except:
            pass

        # 清空所有待发送数据
        self.bg_emit_queue.clear()

        # 断开连接
        self.socketio.disconnect()

    def bind_on_event(self, event: str, func, namespace: str = None):
        """
        绑定指定函数为特定事件的处理函数

        @param {str} event - 事件名, 其中一些事件是标准事件, 例如:
            'connect' - 连接事件
            'disconnect' - 断开连接事件
        @param {function} func - 处理函数对象
        @param {str} namespace=None - 命名空间，例如'/test'
        """
        self.socketio.on(event, handler=func, namespace=namespace)

    def bind_bg_task_on_connected(self, task_func, before_func=None,
                                  namespace: str = None):
        """
        绑定连接成功后的后台任务
        注：只支持注册一个

        @param {function} task_func - 后台执行任务函数，如果是永久运行，需自行实现循环逻辑
        @param {function} before_func=None - 执行后台任务前需执行的操作函数
        @param {str} namespace=None - 命名空间，例如'/test'
        """
        self.bg_task_para = {
            'task_func': task_func,
            'before_func': before_func,
            'lock': threading.Lock()
        }
        self.socketio.on('connect', handler=self._bg_task_on_connected_func, namespace=namespace)

    def emit(self, event, data=None, namespace=None, callback=None):
        """
        向服务器发送信息
        注意：该函数必须在绑定事件的函数内部使用

        @param {str} event - 事件名
        @param {dict} data - 要通知的数据字典
        @param {str} namespace='/' - 命名空间
        @param {function} callback=None - 回调函数
            注：服务端的return值将作为回调函数的入参
        """
        self.socketio.emit(
            event, data=data, namespace=namespace, callback=callback
        )

    def emit_bg(self, event, data=None, namespace=None):
        """
        后台向服务器发送信息
        注：必须设置了emit_bg_task作为后台服务才可以支持

        @param {str} event - 事件名
        @param {dict} data - 要通知的数据字典
        @param {str} namespace='/' - 命名空间
        """
        self.bg_emit_queue.put([
            event, data, namespace
        ])

    def emit_bg_task(self):
        """
        后台向服务器发送信息的线程函数
        注：该函数不可单独调用，用于bind_bg_task_on_connected函数的后台函数，
            监控队列并将送入队列的数据发往服务器
        """
        while True:
            try:
                # 从队列获取数据
                _data = self.bg_emit_queue.get()

                # 向服务器提交数据
                self.emit(
                    _data[0], data=_data[1], namespace=_data[2]
                )
            except queue.Empty:
                # 队列为空
                gevent.sleep(0.1)

    #############################
    # 内部函数
    #############################
    def _bg_task_on_connected_func(self):
        """
        连接时的后台服务
        """
        if self.bg_task_para['before_func'] is not None:
            # 执行前面的函数
            self.bg_task_para['before_func']()

        # 限制只能启动一个
        with self.bg_task_para['lock']:
            self.bg_task_para['bg_thread'] = self.socketio.start_background_task(
                self.bg_task_para['task_func']
            )


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    # 打印版本信息
    print(('模块名：%s  -  %s\n'
           '作者：%s\n'
           '发布日期：%s\n'
           '版本：%s' % (__MOUDLE__, __DESCRIPT__, __AUTHOR__, __PUBLISH__, __VERSION__)))

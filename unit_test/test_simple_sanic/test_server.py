#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""
测试服务器
@module test_server
@file test_server.py
"""
from sanic import Sanic
from sanic.response import text

import sys
import os
import time
import random
import asyncio
# 根据当前文件路径将包路径纳入，在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir, os.path.pardir, os.path.pardir)))
from HiveNetLib.base_tools.run_tool import RunTool
from HiveNetLib.simple_sanic.server import SanicServer


RANDOM_STR = str(random.randint(0, 1000))


async def index(request):
    """
    主页执行函数
    """
    global RANDOM_STR
    await asyncio.sleep(10)
    print('resp: ' + RANDOM_STR)
    return text(RANDOM_STR)


def index1(request):
    """
    主页执行函数
    """
    global RANDOM_STR
    print('resp: ' + RANDOM_STR)
    return text(RANDOM_STR)


def before_server_start(server):
    print('run before_server_start')


def after_server_start(server):
    print('run after_server_start')


def before_server_stop(server):
    print('run before_server_stop haha')


def after_server_stop(server):
    print('run after_server_stop haha')


def server_on_thread_sync():
    """
    线程模式启动, 手动关闭
    """
    _server = SanicServer(
        'no_paraller', server_config={
            'run_config': {
                'debug': True,
                'host': '0.0.0.0',
                'port': 5002,
                'workers': 1,
                'access_log': True
            },
            'run_in_thread': True
        },
        before_server_start=before_server_start,
        after_server_start=after_server_start,
        before_server_stop=before_server_stop,
        after_server_stop=after_server_stop
    )
    _server.add_route('/', index)
    _server.add_route('/a', index1)
    _server.start(is_asyn=True)

    time.sleep(5)

    _server.stop()


def server_on_thread_async():
    """
    线程模式启动, ctrl+c关闭
    """
    _server = SanicServer(
        'no_paraller', server_config={
            'run_config': {
                'debug': True,
                'host': '0.0.0.0',
                'port': 5002,
                'workers': 1,
                'access_log': True
            },
            'run_in_thread': True
        },
        before_server_start=before_server_start,
        after_server_start=after_server_start,
        before_server_stop=before_server_stop,
        after_server_stop=after_server_stop
    )
    _server.add_route('/', index)
    _server.add_route('/a', index1)
    _server.start(is_asyn=False)


def server_main():
    """
    主进程模式启动, ctrl+c关闭
    """
    _server = SanicServer(
        'no_paraller', server_config={
            'run_config': {
                'debug': True,
                'host': '0.0.0.0',
                'port': 5002,
                'workers': 2,
                'access_log': True
            },
            'run_in_thread': False
        },
        before_server_start=before_server_start,
        after_server_start=after_server_start,
        before_server_stop=before_server_stop,
        after_server_stop=after_server_stop
    )
    _server.add_route('/', index)
    _server.add_route('/a', index1)
    _server.start(is_asyn=False)


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    # server_on_thread_sync()
    # server_on_thread_async()
    server_main()

    print('test')

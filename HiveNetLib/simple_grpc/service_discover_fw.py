#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
#
# Copyright 2018 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
服务发现代码框架
@module service_discover_fw
@file service_discover_fw.py
"""

import threading
import functools
import time
from enum import Enum
from abc import ABC, abstractmethod  # 利用abc模块实现抽象类


__MOUDLE__ = 'service_discover_fw'  # 模块名
__DESCRIPT__ = u'服务发现代码框架'  # 模块描述
__VERSION__ = '0.1.0'  # 版本
__AUTHOR__ = u'黎慧剑'  # 作者
__PUBLISH__ = '2019.06.10'  # 发布日期


def register(server_name, ip, port):
     c = consul.Consul() # 连接consul 服务器，默认是127.0.0.1，可用host参数指定host
     print(f"开始注册服务{server_name}")
     check = consul.Check.tcp(ip, port, "10s") # 健康检查的ip，端口，检查时间
     c.agent.service.register(server_name, f"{server_name}-{ip}-{port}",
             address=ip, port=port, check=check) # 注册服务部分
     print(f"注册服务{server_name}成功")

 def unregister(server_name, ip, port):
     c = consul.Consul()
     print(f"开始退出服务{server_name}")
     c.agent.service.deregister(f'{server_name}-{ip}-{port}')

 def serve():
     server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
     test_pb2_grpc.add_OrderHandlerServicer_to_server(OrderHandler(), server)
     server.add_insecure_port('[::]:{}'.format(12006))
     register("order_server", "0.0.0.0", 12006)
     server.start()
     try:
         while True:
             time.sleep(186400)
     except KeyboardInterrupt:
         unregister("order_server", "0.0.0.0", 12006)
         server.stop(0)

def get_ip_port(server_name):
    '''查询出可用的一个ip，和端口'''
     try:
         dnsanswer = consul_resolver.query(f'{server_name}.service.consul', "A")
         dnsanswer_srv = consul_resolver.query(f"{server_name}.service.consul", "SRV")
     except DNSException:
         return None, None
     return dnsanswer[0].address, dnsanswer_srv[0].port

 ip, port = get_ip_port("order_server")

class BaseServiceDiscover(ABC):
    """
    服务发现定义基类, 定义接入及应用服务发现的基本框架函数
    """
    #############################
    # 内部变量
    #############################
    _discover_opts = None  # 注册服务器访问参数

    #############################
    # 公开访问内容
    #############################
    @property
    def discover_opts(self):
        """
        返回注册服务器的连接参数
        @property {object}
        """
        return self._discover_opts


    #############################
    # 构造函数
    #############################
    def __init__(self, discover_opts=None):
        """
        构造函数

        @param {object} discover_opts=None - 注册服务器的访问参数，由具体实现类定义，访问方式参考如下：
            discover_opts.ip
            discover_opts.port
        """
        self._discover_opts = discover_opts

    #############################
    # 公开函数
    #############################
    @abstractmethod
    def register_server(self, server_name, ip, port, opts=None):
        """
        抽象方法，需继承类实现，将服务注册到发现服务器
        注意：实现类需封装该函数的异常处理，通过CResult返回处理情况

        @param {string} server_name - 要注册的服务名
        @param {string} ip - 要注册的服务的访问IP地址
        @param {int} port - 要注册的服务的端口
        @param {object} opts=None - 根据注册服务器传入的个性参数对象，传入心跳间隔时长等参数
            具体参数项和值由指定的注册服务器确定，访问方式示例为:
            opts.heart_time

        @returns {HiveNetLib.generic.CResult} - 服务注册结果，code为0000-成功，其他-注册失败
            另外，要在CResult对象中增加两个返回值

        """
        pass

    @abstractmethod
    def unregister_server(self, server_name, ip, port):
        """
        抽象方法，需继承类实现，取消指定服务的注册
        注意：实现类需封装该函数的异常处理，通过CResult返回处理情况

        @param {string} server_name - 要取消注册的服务名
        @param {string} ip - 要取消注册的服务的访问IP地址
        @param {int} port - 要取消注册的服务的端口

        @returns {HiveNetLib.generic.CResult} - 服务注册结果，code为0000-取消成功，其他-取消失败

        """
        pass

    @abstractmethod
    def get_server_addr(self, server_name):
        """
        抽象方法，需继承类实现，获取指定服务的访问地址
        注意：实现类需封装该函数的异常处理，通过CResult返回处理情况

        @param {string} server_name - 要获取的服务名

        @returns {HiveNetLib.generic.CResult} - 服务获取结果，code为0000-成功，其他-失败
            当获取成功时，在CResult对象中返回以下地址信息：
            CResult.addr.ip {string} - 可访问的服务ip地址
            CResult.addr.port {int} - 可访问的服务端口
        """
        pass


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    # 打印版本信息
    print(('模块名：%s  -  %s\n'
           '作者：%s\n'
           '发布日期：%s\n'
           '版本：%s' % (__MOUDLE__, __DESCRIPT__, __AUTHOR__, __PUBLISH__, __VERSION__)))

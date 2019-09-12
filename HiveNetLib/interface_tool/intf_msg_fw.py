#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
#
# Copyright 2018 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
接口通讯信息处理框架

@module intf_msg_fw
@file intf_msg_fw.py

"""

import os
import sys
from abc import ABC, abstractmethod  # 利用abc模块实现抽象类
# 根据当前文件路径将包路径纳入，在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir, os.path.pardir)))
from HiveNetLib.generic import CResult


__MOUDLE__ = 'intf_msg_fw'  # 模块名
__DESCRIPT__ = u'接口通讯信息处理框架'  # 模块描述
__VERSION__ = '0.1.0'  # 版本
__AUTHOR__ = u'黎慧剑'  # 作者
__PUBLISH__ = '2018.09.12'  # 发布日期


class IntfMsgFW(ABC):
    """
    接口通讯信息处理框架
    定义所有的接口信息必定有两类报文信息：协议信息（例如Http头部分的信息）和报文信息（例如具体的报文内容）

    """
    #############################
    # 访问协议对象
    #############################
    @property
    def msg(self):
        """
        获取报文信息对象

        @property {MsgFW}

        """
        return self.__msg

    @msg.setter
    def msg(self, value):
        """
        设置报文信息对象

        @param {MsgFW} value - 要设置的报文信息对象

        """
        self.__msg = value

    @property
    def proto_msg(self):
        """
        获取协议信息对象

        @property {MsgFW}

        """
        return self.__proto_msg

    @proto_msg.setter
    def proto_msg(self, value):
        """
        设置协议信息对象

        @param {MsgFW} value - 要设置的协议信息对象

        """
        self.__proto_msg = value

    #############################
    # 公共函数
    #############################
    def __init__(self, msg=None, proto_msg=None, proto_obj=None, net_info=None):
        """
        构造函数（如有特殊处理可以重构该函数）

        @param {MsgFW} msg=None - 报文信息对象
        @param {MsgFW} proto_msg=None - 协议信息对象
        @param {object} proto_obj=None - 默认使用的协议通讯对象（长连接情况）
        @param {object} net_info=None - 默认使用的网络连接信息（长连接情况）

        """
        #############################
        # 内部变量
        #############################
        self.__msg = msg  # 报文信息对象
        self.__proto_msg = proto_msg  # 协议信息对象
        self.__proto_obj = proto_obj  # 协议通讯对象
        self.__net_info = net_info  # 网络连接信息

    #############################
    # 需继承类实现的内容
    #############################
    @abstractmethod
    def connect(self, **kwargs):
        """
        连接远端服务器
        （对于长连接或有需要实现先连接再处理的场景使用，其他场景无需重构该函数）

        @param {**kwargs} kwargs - 连接参数（具体由实现类定义）

        @returns {HiveNetLib.generic.CResult} - 处理结果（符合HiveNet 错误码规范）
            当处理结果为成功时，通过CResult返回结果对象：
            CResult.proto_obj {object}  - 协议通讯对象
            CResult.net_info {object}  - 网络连接信息

        """
        _ret = CResult(code='00000')
        _ret.proto_obj = self.__proto_obj
        _ret.net_info = self.__net_info
        return _ret

    @abstractmethod
    def ReadMsg(self, proto_obj=None, net_info=None, msg_id=None, read_para=dict()):
        """
        从网络中读取报文信息

        @param {object} proto_obj=None - 协议通讯对象，如果不传则使用类默认的对象
        @param {object} net_info=None - 网络连接信息，如果不传则使用类默认的对象
        @param {string} msg_id=None - 报文ID
        @param {dict} read_para=dict() - 网络读取参数，具体定义由实现类确认

        @returns {HiveNetLib.generic.CResult} - 处理结果（符合HiveNet 错误码规范）
            注：执行成功后通过类的msg和proto_msg使用获取到的报文信息

        @throws {NotImplementedError} - 当实现类没有实现该方法时，抛出该异常

        """
        raise NotImplementedError

    @abstractmethod
    def SendMsg(self, proto_obj=None, net_info=None, msg_id=None, send_para=dict()):
        """
        向网络中发送报文信息

        @param {object} proto_obj=None - 协议通讯对象，如果不传则使用类默认的对象
        @param {object} net_info=None - 网络连接信息，如果不传则使用类默认的对象
        @param {string} msg_id=None - 报文ID
        @param {dict} send_para=dict() - 网络发送参数，具体定义由实现类确认

        @returns {HiveNetLib.generic.CResult} - 处理结果（符合HiveNet 错误码规范）
            注：应在发送前更新msg和proto_msg的报文信息

        @throws {NotImplementedError} - 当实现类没有实现该方法时，抛出该异常

        """
        raise NotImplementedError


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    # 打印版本信息
    print(('模块名：%s  -  %s\n'
           '作者：%s\n'
           '发布日期：%s\n'
           '版本：%s' % (__MOUDLE__, __DESCRIPT__, __AUTHOR__, __PUBLISH__, __VERSION__)))

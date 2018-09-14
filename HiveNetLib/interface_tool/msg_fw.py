#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
#
# Copyright 2018 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
接口报文处理框架
@module msg_fw
@file msg_fw.py
"""

import os
import sys
from enum import Enum
from abc import ABC, abstractmethod  # 利用abc模块实现抽象类
sys.path.append(os.path.abspath(os.path.dirname(__file__)+'/'+'../..'))
from HiveNetLib.generic import CResult


__MOUDLE__ = 'msg_fw'  # 模块名
__DESCRIPT__ = u'接口报文处理框架'  # 模块描述
__VERSION__ = '0.1.0'  # 版本
__AUTHOR__ = u'黎慧剑'  # 作者
__PUBLISH__ = '2018.09.12'  # 发布日期


class EnumMsgObjType(Enum):
    """
    消息载体对象类型
    @enum {int}
    """
    File = 0  # 文件
    FileHandle = 1  # 打开的文件句柄
    String = 2  # 字符串
    Bytes = 3  # 二进制数组


class EnumMsgSRType(Enum):
    """
    报文收发类型
    @enum {int}
    """
    Request = 0  # 请求报文
    Response = 1  # 相应报文
    Auto = 2  # 自动识别


class MsgFW(ABC):
    """
    基础报文信息处理框架类（message）
    定义通用的接口报文需要实现的方法，便于兼容扩展各类报文处理

    """

    #############################
    # 报文体处理函数
    #############################
    @classmethod
    @property
    @abstractmethod
    def MsgType(cls):
        """
        返回消息对象的类型（实现类应将自己类名返回）
        @property {string}
        """
        return 'MsgFW'

    @classmethod
    @abstractmethod
    def load_msg(cls, obj, msg_id=None, obj_type=None, **kwargs):
        """
        装载报文体对象（主报文）

        @param {object} obj - 要装载的报文载体（与obj_type结合来判断是什么对象），例如(仅供参考)：
            obj_type = EnumMsgObjType.File 时，obj为文件路径
            obj_type = EnumMsgObjType.FileHandle 时，obj为文件句柄
            obj_type = EnumMsgObjType.String 时，obj为报文文本
        @param {string} msg_id=None - 报文id（用于标明该报文是什么报文）
        @param {object} obj_type=None - 报文载体对象类型
        @param {**kwargs} kwargs - 装载参数，例如：
            encoding='utf-8' - 装载字符编码

        @returns {HiveNetLib.generic.CResult} - 处理结果（符合HiveNet 错误码规范）
            当处理结果为成功时，通过CResult返回报文体对象：
            CResult.msg {object}  - 报文体对象(具体对象类型在实现类定义)

        @throws {NotImplementedError} - 当实现类没有实现该方法时，抛出该异常

        """
        raise NotImplementedError

    @classmethod
    @abstractmethod
    def load_submsg(cls, obj, submsg_id=None, obj_type=None, **kwargs):
        """
        装载子报文体对象（独立对象，不嵌入主报文中）

        @param {object} obj - 要装载的报文载体（与obj_type结合来判断是什么对象），例如(仅供参考)：
            obj_type = EnumMsgObjType.File 时，obj为文件路径
            obj_type = EnumMsgObjType.FileHandle 时，obj为文件句柄
            obj_type = EnumMsgObjType.String 时，obj为报文文本
        @param {string} submsg_id=None - 报文id（用于标明该报文是什么报文）
        @param {object} obj_type=None - 报文载体对象类型
        @param {**kwargs} kwargs - 装载参数，例如：
            encoding='utf-8' - 装载字符编码

        @returns {HiveNetLib.generic.CResult} - 处理结果（符合HiveNet 错误码规范）
            当处理结果为成功时，通过CResult返回报文体对象：
            CResult.msg {object}  - 子报文体对象(具体对象类型在实现类定义)

        @throws {NotImplementedError} - 当实现类没有实现该方法时，抛出该异常

        """
        raise NotImplementedError

    @classmethod
    @abstractmethod
    def set_msg_value(cls, msg, search_path, value, msg_id=None, **kwargs):
        """
        设置主报文的内容

        @param {object} msg - 主报文对象
        @param {object} search_path - 需要设置值的索引搜索路径(具体类型在实现类定义)
        @param {object} value - 要设置值（具体对象类型在实现类定义）
        @param {string} msg_id=None - 报文id（用于标明该报文是什么报文）
        @param {**kwargs} kwargs - 设置参数（具体由实现类定义）

        @returns {HiveNetLib.generic.CResult} - 处理结果（符合HiveNet 错误码规范）
            当处理结果为成功时，通过CResult返回报文体对象：
            CResult.msg {object}  - 设置值后的报文对象

        @throws {NotImplementedError} - 当实现类没有实现该方法时，抛出该异常

        """
        raise NotImplementedError

    @classmethod
    @abstractmethod
    def set_submsg_value(cls, submsg, search_path, value, submsg_id=None, **kwargs):
        """
        设置子报文的内容

        @param {object} submsg - 子报文对象
        @param {object} search_path - 需要设置值的索引搜索路径(具体类型在实现类定义)
        @param {object} value - 要设置值（具体对象类型在实现类定义）
        @param {string} submsg_id=None - 报文id（用于标明该报文是什么报文）
        @param {**kwargs} kwargs - 设置参数（具体由实现类定义）

        @returns {HiveNetLib.generic.CResult} - 处理结果（符合HiveNet 错误码规范）
            当处理结果为成功时，通过CResult返回报文体对象：
            CResult.msg {object}  - 设置值后的报文对象

        @throws {NotImplementedError} - 当实现类没有实现该方法时，抛出该异常

        """
        raise NotImplementedError

    @classmethod
    @abstractmethod
    def get_msg_value(cls, msg, search_path, msg_id=None, **kwargs):
        """
        获取主报文的内容

        @param {object} msg - 主报文对象
        @param {object} search_path - 需要获取值的索引搜索路径(具体类型在实现类定义)
        @param {string} msg_id=None - 报文id（用于标明该报文是什么报文）
        @param {**kwargs} kwargs - 设置参数（具体由实现类定义）

        @returns {HiveNetLib.generic.CResult} - 处理结果（符合HiveNet 错误码规范）
            当处理结果为成功时，通过CResult返回报文体对象：
            CResult.get_value {object}  - 获取到的值

        @throws {NotImplementedError} - 当实现类没有实现该方法时，抛出该异常

        """
        raise NotImplementedError

    @classmethod
    @abstractmethod
    def get_submsg_value(cls, submsg, search_path, submsg_id=None, **kwargs):
        """
        获取主报文的内容

        @param {object} submsg - 子报文对象
        @param {object} search_path - 需要获取值的索引搜索路径(具体类型在实现类定义)
        @param {string} submsg_id=None - 报文id（用于标明该报文是什么报文）
        @param {**kwargs} kwargs - 设置参数（具体由实现类定义）

        @returns {HiveNetLib.generic.CResult} - 处理结果（符合HiveNet 错误码规范）
            当处理结果为成功时，通过CResult返回报文体对象：
            CResult.get_value {object}  - 获取到的值

        @throws {NotImplementedError} - 当实现类没有实现该方法时，抛出该异常

        """
        raise NotImplementedError

    @classmethod
    @abstractmethod
    def append_submsg(cls, submsg, msg, search_path, msg_id=None, submsg_id=None, **kwargs):
        """
        将子报文对象添加到主报文对象中

        @param {object} submsg - 子报文对象
        @param {object} msg - 主报文对象
        @param {object} search_path - 添加位置的搜索路径(具体类型在实现类定义)
        @param {string} msg_id=None - 主报文id（用于标明该报文是什么报文）
        @param {string} submsg_id=None - 子报文id（用于标明该报文是什么报文）
        @param {**kwargs} kwargs - 添加参数（具体由实现类定义）

        @returns {HiveNetLib.generic.CResult} - 处理结果（符合HiveNet 错误码规范）
            当处理结果为成功时，通过CResult返回报文体对象：
            CResult.msg {object}  - 完成添加后的主报文对象

        @throws {NotImplementedError} - 当实现类没有实现该方法时，抛出该异常

        """
        raise NotImplementedError

    @classmethod
    @abstractmethod
    def msg_to_str(cls, msg, msg_id=None, **kwargs):
        """
        将主报文对象转换为字符串格式

        @param {object} msg - 报文对象
        @param {string} msg_id=None - 主报文id（用于标明该报文是什么报文）
        @param {**kwargs} kwargs - 转换参数（具体由实现类定义）

        @returns {HiveNetLib.generic.CResult} - 处理结果（符合HiveNet 错误码规范）
            当处理结果为成功时，通过CResult返回结果对象：
            CResult.msg_str {string}  - 输出字符串

        @throws {NotImplementedError} - 当实现类没有实现该方法时，抛出该异常

        """
        raise NotImplementedError

    @classmethod
    @abstractmethod
    def submsg_to_str(cls, submsg, submsg_id=None, **kwargs):
        """
        将主报文对象转换为字符串格式

        @param {object} submsg - 报文对象
        @param {string} submsg_id=None - 报文id（用于标明该报文是什么报文）
        @param {**kwargs} kwargs - 转换参数（具体由实现类定义）

        @returns {HiveNetLib.generic.CResult} - 处理结果（符合HiveNet 错误码规范）
            当处理结果为成功时，通过CResult返回结果对象：
            CResult.msg_str {string}  - 输出字符串

        @throws {NotImplementedError} - 当实现类没有实现该方法时，抛出该异常

        """
        raise NotImplementedError

    @classmethod
    @abstractmethod
    def str_to_msg(cls, msg_str, msg_id=None, **kwargs):
        """
        将字符串转换为主报文对象

        @param {string} msg_str - 字符串
        @param {string} msg_id=None - 报文id（用于标明该报文是什么报文）
        @param {**kwargs} kwargs - 转换参数（具体由实现类定义）

        @returns {HiveNetLib.generic.CResult} - 处理结果（符合HiveNet 错误码规范）
            当处理结果为成功时，通过CResult返回结果对象：
            CResult.msg {object}  - 报文对象

        @throws {NotImplementedError} - 当实现类没有实现该方法时，抛出该异常

        """
        raise NotImplementedError

    @classmethod
    @abstractmethod
    def str_to_submsg(cls, msg_str, submsg_id=None, **kwargs):
        """
        将字符串转换为主报文对象

        @param {string} msg_str - 字符串
        @param {string} submsg_id=None - 报文id（用于标明该报文是什么报文）
        @param {**kwargs} kwargs - 转换参数（具体由实现类定义）

        @returns {HiveNetLib.generic.CResult} - 处理结果（符合HiveNet 错误码规范）
            当处理结果为成功时，通过CResult返回结果对象：
            CResult.msg {object}  - 报文对象

        @throws {NotImplementedError} - 当实现类没有实现该方法时，抛出该异常

        """
        raise NotImplementedError

    @classmethod
    @abstractmethod
    def msg_to_bytes(cls, msg, msg_id=None, **kwargs):
        """
        将主报文对象转换为二进制数组（用于网络通讯）

        @param {object} msg - 报文对象
        @param {string} msg_id=None - 主报文id（用于标明该报文是什么报文）
        @param {**kwargs} kwargs - 转换参数（具体由实现类定义）

        @returns {HiveNetLib.generic.CResult} - 处理结果（符合HiveNet 错误码规范）
            当处理结果为成功时，通过CResult返回结果对象：
            CResult.msg_bytes {byte[]}  - 二进制数组

        @throws {NotImplementedError} - 当实现类没有实现该方法时，抛出该异常

        """
        raise NotImplementedError

    @classmethod
    @abstractmethod
    def bytes_to_msg(cls, msg_bytes, msg_id=None, **kwargs):
        """
        将二进制数组转换为主报文对象（解析网络通讯信息）

        @param {byte[]} msg_bytes - 二进制数组
        @param {string} msg_id=None - 报文id（用于标明该报文是什么报文）
        @param {**kwargs} kwargs - 转换参数（具体由实现类定义）

        @returns {HiveNetLib.generic.CResult} - 处理结果（符合HiveNet 错误码规范）
            当处理结果为成功时，通过CResult返回结果对象：
            CResult.msg {object}  - 报文对象

        @throws {NotImplementedError} - 当实现类没有实现该方法时，抛出该异常

        """
        raise NotImplementedError

    #############################
    # 内部处理函数
    #############################
    @classmethod
    def _get_para_from_kwargs(cls, para_name, default_value='', kwargs=dict()):
        """
        从kwargs参数中获取指定参数值

        @param {string} para_name - 参数名
        @param {string} default_value='' - 默认参数值
        @param {dict} kwargs=dict() - 入参字典

        @returns {object} - 返回参数值

        """
        _ret = default_value
        if para_name in kwargs.keys():
            _ret = kwargs[para_name]
        return _ret


class IntfMsgFW(ABC):
    """
    接口通讯信息处理框架
    定义所有的接口信息必定有两类报文信息：协议信息（例如Http头部分的信息）和报文信息（例如具体的报文内容）

    """
    #############################
    # 内部变量
    #############################
    __msg = None  # 报文信息对象
    __proto_msg = None  # 协议信息对象
    __proto_obj = None  # 协议通讯对象
    __net_info = None  # 网络连接信息

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
        self.__msg = msg
        self.__proto_msg = proto_msg
        self.__proto_obj = proto_obj
        self.__net_info = net_info

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

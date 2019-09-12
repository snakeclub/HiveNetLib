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
# 根据当前文件路径将包路径纳入，在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir, os.path.pardir)))
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
    # 内部变量
    #############################
    _msg_id = None  # 报文标识
    _base_object = None  # 报文主体对象

    #############################
    # 公共属性
    #############################
    @property
    def base_object(self):
        """
        获取报文转换后的基础处理对象
        处理对象类型由实现类定义（例如xml报文，报文将转换为lxml库的xml document对象）

        @property {object}

        """
        return self._base_object

    @property
    def msg_id(self):
        """
        获取当前报文ID（标识）

        @property {string}

        """
        return self._msg_id

    @classmethod
    @property
    @abstractmethod
    def msg_type(cls):
        """
        返回报文类型
        （实现类需重载）

        @property {string}

        """
        return 'MsgFW'

    #############################
    # 构造函数
    #############################
    def __init__(self, obj, msg_id=None, obj_type=EnumMsgObjType.String, **kwargs):
        """
        构造函数

        @param {object} obj - 要装载的报文载体（与obj_type结合来判断是什么对象），例如(仅供参考)：
            obj_type = EnumMsgObjType.File 时，obj为文件路径
            obj_type = EnumMsgObjType.FileHandle 时，obj为文件句柄
            obj_type = EnumMsgObjType.String 时，obj为报文文本
        @param {string} msg_id=None - 报文id（用于标明该报文是什么报文）
        @param {EnumMsgObjType} obj_type=None - 报文载体对象类型
        @param {**kwargs} kwargs - 装载参数，例如：
            encoding='utf-8' - 装载字符编码
            具体参数参考具体实现类的self._load_msg方法参数

        """
        #############################
        # 内部变量
        #############################
        self._msg_id = msg_id  # 报文标识
        # 报文主体对象
        self._base_object = self._load_msg(obj, msg_id=msg_id, obj_type=obj_type, **kwargs)

    #############################
    # 公共函数
    #############################
    def append_submsg(self, submsg_obj, search_path, submsg_id=None, **kwargs):
        """
        添加子报文信息
        将子报文对象（MsgFW实例）添加到当前报文实例的指定路径中（search_path）

        @param {MsgFW} submsg_obj - 子报文对象（MsgFW类型）
        @param {object} search_path - 添加位置的搜索路径(建议兼容xPath语法)
        @param {string} submsg_id=None - 子报文id（用于标明该报文业务类型）
        @param {**kwargs} kwargs - 添加参数（具体参考实现类的_append_submsg函数定义）

        """
        self._base_object = self._append_submsg(
            submsg=submsg_obj.base_object, msg=self._base_object,
            search_path=search_path, msg_id=self._msg_id, submsg_id=submsg_id, **kwargs
        )

    def append_submsg_by_base_object(self, submsg_base_obj, search_path, submsg_id=None, **kwargs):
        """
        添加子报文信息
        将子报文对象（基础处理对象，例如MsgFW.base_object）添加到当前报文实例的指定路径中

        @param {object} submsg_base_obj - 子报文对象（基础处理对象，例如MsgFW.base_object）
        @param {object} search_path - 添加位置的搜索路径(建议兼容xPath语法)
        @param {string} submsg_id=None - 子报文id（用于标明该报文业务类型）
        @param {**kwargs} kwargs - 添加参数（具体参考实现类的_append_submsg函数定义）

        """
        self._base_object = self._append_submsg(
            submsg=submsg_base_obj, msg=self._base_object,
            search_path=search_path, msg_id=self._msg_id, submsg_id=submsg_id, **kwargs
        )

    def append_submsg_by_object(self, obj, search_path, obj_type=None, submsg_id=None, **kwargs):
        """
        添加子报文信息
        将子报文对象（未转换的任意类型，例如文本或文件）添加到当前报文实例的指定路径中（search_path）

        @param {object} obj - 要装载的报文载体（与obj_type结合来判断是什么对象），例如(仅供参考)：
            obj_type = EnumMsgObjType.File 时，obj为文件路径
            obj_type = EnumMsgObjType.FileHandle 时，obj为文件句柄
            obj_type = EnumMsgObjType.String 时，obj为报文文本
        @param {object} search_path - 添加位置的搜索路径(建议兼容xPath语法)
        @param {EnumMsgObjType} obj_type=None - 报文载体对象类型
        @param {string} submsg_id=None - 子报文id（用于标明该报文业务类型）
        @param {**kwargs} kwargs - 装载及添加参数（具体参考实现类的self._load_msg和self._append_submsg的函数定义）

        """
        _submsg = self._load_msg(obj, msg_id=submsg_id, obj_type=obj_type, **kwargs)
        self._base_object = self._append_submsg(
            submsg=_submsg, msg=self._base_object,
            search_path=search_path, msg_id=self._msg_id, submsg_id=submsg_id, **kwargs
        )

    def get_value(self, search_path, **kwargs):
        """
        获取报文的内容

        @param {object} search_path - 需要获取值的索引搜索路径(建议兼容xPath语法)
        @param {**kwargs} kwargs - 获取参数（具体由实现类定义）

        @returns {object} - 获取到的值，如果处理失败需抛出指定异常
        """
        return self._get_msg_value(
            msg=self._base_object, search_path=search_path, msg_id=self._msg_id, **kwargs)

    def set_value(self, search_path, value, **kwargs):
        """
        设置主报文的内容

        @param {object} search_path - 需要设置值的索引搜索路径(建议兼容xPath语法)
        @param {object} value - 要设置值（具体对象类型在实现类定义）
        @param {**kwargs} kwargs - 设置参数（具体由实现类定义）
        """
        self._base_object = self._set_msg_value(
            msg=self._base_object, search_path=search_path,
            value=value, msg_id=self._msg_id, **kwargs
        )

    def to_str(self, **kwargs):
        """
        将报文转换为字符串格式

        @param {**kwargs} kwargs - 转换参数（具体由实现类定义）

        @returns {string} - 输出字符串
        """
        return self._msg_to_str(msg=self._base_object, msg_id=self._msg_id, **kwargs)

    def to_bytes(self, **kwargs):
        """
        将报文转换为二进制数组（用于网络通讯）

        @param {**kwargs} kwargs - 转换参数（具体由实现类定义）

        @returns {byte[]} - 二进制数组
        """
        return self._msg_to_bytes(msg=self._base_object, msg_id=self._msg_id, **kwargs)

    #############################
    # 需重载的内部函数
    #############################
    @classmethod
    @abstractmethod
    def _load_msg(cls, obj, msg_id=None, obj_type=None, **kwargs):
        """
        装载报文对象,将传入的报文对象转换为基础处理对象

        @param {object} obj - 要装载的报文载体（与obj_type结合来判断是什么对象），例如(仅供参考)：
            obj_type = EnumMsgObjType.File 时，obj为文件路径
            obj_type = EnumMsgObjType.FileHandle 时，obj为文件句柄
            obj_type = EnumMsgObjType.String 时，obj为报文文本
        @param {string} msg_id=None - 报文id（用于标明该报文业务类型）
        @param {EnumMsgObjType} obj_type=None - 报文载体对象类型
        @param {**kwargs} kwargs - 装载参数，例如：
            encoding='utf-8' - 装载字符编码

        @returns {object} - 报文对象（具体类型由实现类定义,例如xml报文的报文对象指xml document对象），
            如果处理失败需抛出指定异常

        @throws {NotImplementedError} - 当实现类没有实现该方法时，抛出该异常
        """
        raise NotImplementedError

    @classmethod
    @abstractmethod
    def _append_submsg(cls, submsg, msg, search_path, msg_id=None, submsg_id=None, **kwargs):
        """
        将子报文对象添加到主报文对象中

        @param {object} submsg - 子报文对象,基础处理对象（例如MsgFW.base_object）
        @param {object} msg - 主报文对象,基础处理对象（例如MsgFW.base_object）
        @param {object} search_path - 添加位置的搜索路径(建议兼容xPath语法)
        @param {string} msg_id=None - 主报文id（用于标明该报文业务类型）
        @param {string} submsg_id=None - 子报文id（用于标明该报文业务类型）
        @param {**kwargs} kwargs - 添加参数（具体由实现类定义）

        @returns {object} - 完成添加后的主报文对象（例如MsgFW.base_object），如果处理失败需抛出指定异常

        @throws {NotImplementedError} - 当实现类没有实现该方法时，抛出该异常

        """
        raise NotImplementedError

    @classmethod
    @abstractmethod
    def _get_msg_value(cls, msg, search_path, msg_id=None, **kwargs):
        """
        获取报文指定路径（search_path）的内容值

        @param {object} msg - 主报文对象,基础处理对象（例如MsgFW.base_object）
        @param {object} search_path - 需要获取值的索引搜索路径(建议兼容xPath语法)
        @param {string} msg_id=None - 报文id（用于标明该报文业务类型）
        @param {**kwargs} kwargs - 设置参数（具体由实现类定义）

        @returns {object} - 获取到的值，如果处理失败需抛出指定异常

        @throws {NotImplementedError} - 当实现类没有实现该方法时，抛出该异常

        """
        raise NotImplementedError

    @classmethod
    @abstractmethod
    def _set_msg_value(cls, msg, search_path, value, msg_id=None, **kwargs):
        """
        设置报文指定路径（search_path）的内容值

        @param {object} msg - 报文对象,基础处理对象（例如MsgFW.base_object）
        @param {object} search_path - 需要设置值的索引搜索路径(建议兼容xPath语法)
        @param {object} value - 要设置值（具体对象类型在实现类定义）
        @param {string} msg_id=None - 报文id（用于标明该报文业务类型）
        @param {**kwargs} kwargs - 设置参数（具体由实现类定义）

        @returns {object} - 设置值后的报文对象（例如MsgFW.base_object），如果处理失败需抛出指定异常

        @throws {NotImplementedError} - 当实现类没有实现该方法时，抛出该异常

        """
        raise NotImplementedError

    @classmethod
    @abstractmethod
    def _msg_to_str(cls, msg, msg_id=None, **kwargs):
        """
        将报文对象转换为字符串格式

        @param {object} msg - 报文对象, 基础处理对象（例如MsgFW.base_object）
        @param {string} msg_id=None - 主报文id（用于标明该报文业务类型）
        @param {**kwargs} kwargs - 转换参数（具体由实现类定义）

        @returns {string} - 输出字符串

        @throws {NotImplementedError} - 当实现类没有实现该方法时，抛出该异常

        """
        raise NotImplementedError

    @classmethod
    @abstractmethod
    def _msg_to_bytes(cls, msg, msg_id=None, **kwargs):
        """
        将报文对象转换为二进制数组（用于网络通讯）

        @param {object} msg - 报文对象,基础处理对象（例如MsgFW.base_object）
        @param {string} msg_id=None - 主报文id（用于标明该报文业务类型）
        @param {**kwargs} kwargs - 转换参数（具体由实现类定义）

        @returns {byte[]} - 二进制数组

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

    def __str__(self):
        """
        重载内部打印函数，支持str(MsgFW)的打印方式
        """
        return self.to_str()


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    # 打印版本信息
    print(('模块名：%s  -  %s\n'
           '作者：%s\n'
           '发布日期：%s\n'
           '版本：%s' % (__MOUDLE__, __DESCRIPT__, __AUTHOR__, __PUBLISH__, __VERSION__)))

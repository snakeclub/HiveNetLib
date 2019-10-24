#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
#
# Copyright 2018 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
xml报文处理模块

@module msg_xml
@file msg_xml.py

"""

import os
import sys
import copy
# 根据当前文件路径将包路径纳入，在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir, os.path.pardir)))
from HiveNetLib.generic import CResult
from HiveNetLib.interface_tool.msg_fw import EnumMsgObjType, MsgFW
from HiveNetLib.base_tools.exception_tool import ExceptionTool
from HiveNetLib.simple_xml import EnumXmlObjType, SimpleXml

__MOUDLE__ = 'msg_xml'  # 模块名
__DESCRIPT__ = u'xml报文处理模块'  # 模块描述
__VERSION__ = '0.1.0'  # 版本
__AUTHOR__ = u'黎慧剑'  # 作者
__PUBLISH__ = '2018.09.12'  # 发布日期


class MsgXML(MsgFW):
    """
    XML报文信息处理类（message）

    """

    #############################
    # 重载MsgFW的函数
    #############################
    @classmethod
    @property
    def msg_type(cls):
        """
        消息对象的类型

        @property {string}

        """
        return 'MsgXML'

    @classmethod
    def _load_msg(cls, obj, msg_id=None, obj_type=EnumMsgObjType.String, **kwargs):
        """
        装载报文对象，将传入的报文对象转换为基础处理对象（lxml的xml document对象）

        @param {object} obj - 要装载的报文载体（与obj_type结合来判断是什么对象），例如：
            obj_type = EnumMsgObjType.File 时，obj为文件路径
            obj_type = EnumMsgObjType.String 时，obj为报文文本
        @param {EnumMsgObjType} msg_id=None - 报文id（用于标明该报文是什么报文）
        @param {object} obj_type=EnumMsgObjType.String - 报文载体对象类型
        @param {**kwargs} kwargs - 装载参数，包括：
            encoding='utf-8' - 装载字符编码
            has_sign_info=False - 是否带有签字验证信息（在xml文档结尾），如果有，转换时会去除
            sign_begin_tag='' - 当有签字验证信息时，标记验证信息开头字符串，用于删除验证信息
            register_namespace - 注册命名空间别名，格式为：
                {prefix: uri, prefix: uri, ... }  其中prefix和uri都为字符串
                注册命名空间后，后续的节点就可以通过tag='{uri}tagname'的方式添加带命名空间的节点
            其余参数为SimpleXml的初始化函数的kwargs参数定义
        @returns {object} - 报文体对象（SimpleXml对象）

        @throws {UnboundLocalError} - 对应标准错误码21001，当遇到obj_type不支持时抛出

        """
        _msg = None
        if obj_type in (EnumMsgObjType.File, EnumMsgObjType.String, EnumMsgObjType.Bytes):
            # 字符串方式及二进制
            _xmlstr = ''
            _encoding = cls._get_para_from_kwargs(
                'encoding', default_value='utf-8', kwargs=kwargs)
            _has_sign_info = cls._get_para_from_kwargs(
                'has_sign_info', default_value=False, kwargs=kwargs)
            _sign_begin_tag = cls._get_para_from_kwargs(
                'sign_begin_tag', default_value='', kwargs=kwargs)

            if obj_type == EnumMsgObjType.File:
                with open(obj, 'rt', encoding=_encoding) as f:
                    _xmlstr = f.read()
            elif obj_type == EnumMsgObjType.Bytes:
                _xmlstr = obj.decode(_encoding)
            else:
                _xmlstr = obj

            if _has_sign_info:
                # 要删除掉最后面的签名信息
                _sign_begin = _xmlstr.rfind(_sign_begin_tag)
                if _sign_begin != -1:
                    _xmlstr = _xmlstr[0:_sign_begin]

            # 生成对象
            _msg = SimpleXml(_xmlstr, obj_type=EnumXmlObjType.String, encoding=_encoding,
                             use_chardet=False, register_namespace=None, **kwargs)
        else:
            # 不支持的格式
            raise UnboundLocalError

        # 返回结果
        return _msg

    @classmethod
    def _set_msg_value(cls, msg, search_path, value, msg_id=None, **kwargs):
        """
        设置报文的内容

        @param {object} msg - 报文对象（SimpleXml对象）
        @param {string} search_path - 需要设置值的搜索路径，符合xpath规范
        @param {string} value - 要设置的值
        @param {string} msg_id=None - 报文id（用于标明该报文业务类型）
        @param {**kwargs} kwargs - 设置参数
            namespaces=None - 命名空间
                可传入值的示例如下：
                ns = {
                    'real_person': 'http://people.example.com',
                    'role': 'http://characters.example.com'
                }

        @returns {object} - 设置值后的报文对象（SimpleXml对象）

        @throws {NameError} - 对应标准错误码21002，当参数路径不存在时抛出

        """
        _msg = msg
        _msg.set_value(
            search_path, str(value),
            namespaces=None if 'namespaces' not in kwargs.keys() else kwargs['namespaces'],
            auto_create=True
        )
        return _msg

    @classmethod
    def _get_msg_value(cls, msg, search_path, msg_id=None, **kwargs):
        """
        获取报文的内容（注意只获取第1个取到的节点值）

        @param {object} msg - 主报文对象（SimpleXml对象）
        @param {string} search_path - 需要获取值的搜索路径，符合xpath规范
        @param {string} msg_id=None - 报文id（用于标明该报文业务类型）
        @param {**kwargs} kwargs - 设置参数
            namespaces=None - 命名空间
                可传入值的示例如下：
                ns = {
                    'real_person': 'http://people.example.com',
                    'role': 'http://characters.example.com'
                }

        @returns {string} - 获取到的值

        @throws {NameError} - 对应标准错误码21002，当参数路径不存在时抛出

        """
        return msg.get_value(
            search_path, default=None,
            namespaces=None if 'namespaces' not in kwargs.keys() else kwargs['namespaces']
        )

    @classmethod
    def _append_submsg(cls, submsg, msg, search_path, msg_id=None, submsg_id=None, **kwargs):
        """
        将子报文对象添加到主报文对象中

        @param {object} submsg - 子报文对象（SimpleXml对象）
        @param {object} msg - 主报文对象（SimpleXml对象）
        @param {string} search_path - 添加位置的搜索路径，符合xpath规范
        @param {string} msg_id=None - 主报文id（用于标明该报文业务类型）
        @param {string} submsg_id=None - 子报文id（用于标明该报文业务类型）
        @param {**kwargs} kwargs - 添加参数
            namespaces=None - 命名空间
                可传入值的示例如下：
                ns = {
                    'real_person': 'http://people.example.com',
                    'role': 'http://characters.example.com'
                }

        @returns {object} - 完成添加后的主报文对象（SimpleXml对象）

        @throws {NameError} - 对应标准错误码21002，当参数路径不存在时抛出

        """
        _node = copy.deepcopy(submsg.root)
        _msg = msg
        _msg.append_node(
            search_path, _node,
            namespaces=None if 'namespaces' not in kwargs.keys() else kwargs['namespaces']
        )
        return _msg

    @classmethod
    def _msg_to_str(cls, msg, msg_id=None, **kwargs):
        """
        将报文对象转换为字符串格式

        @param {object} msg - 报文对象（lxml的xml document对象）
        @param {string} msg_id=None - 主报文id（用于标明该报文业务类型）
        @param {**kwargs} kwargs - 转换参数，包括：
            has_sign_info=False - 是否带有签字验证信息（在xml文档结尾），如果有，转换时加到字符串中
            sign_str='' - 当有签字验证信息时，验证信息字符串

            可以支持etree.tostring的参数:
            method="xml"
            xml_declaration=None - 控制是否在文件中添加xml的声明，True - 一直添加, False - 不添加
                如果传None，代表只有encoding不是US-ASCII or UTF-8 or Unicode的时候才添加声明
            pretty_print=True - 是否针对打印格式美化
            with_tail=True
            standalone=None
            doctype=None
            exclusive=False
            inclusive_ns_prefixes=None
            with_comments=True
            strip_text=False

        @returns {string} - 输出字符串

        """
        _msg_str = msg.to_string(**kwargs)
        _has_sign_info = cls._get_para_from_kwargs(
            'has_sign_info', default_value=False, kwargs=kwargs)
        _sign_str = cls._get_para_from_kwargs(
            'sign_str', default_value='', kwargs=kwargs)

        # 添加签名证书
        if _has_sign_info:
            _msg_str = _msg_str + _sign_str

        return _msg_str

    @classmethod
    def _msg_to_bytes(cls, msg, msg_id=None, **kwargs):
        """
        将报文对象转换为二进制数组（用于网络通讯）

        @param {object} msg - 报文对象（lxml的xml document对象）
        @param {string} msg_id=None - 主报文id（用于标明该报文业务类型）
        @param {**kwargs} kwargs - 转换参数，包括
            encoding='utf-8' - 字符编码
            has_sign_info=False - 是否带有签字验证信息（在xml文档结尾），如果有，转换时加到字符串中
            sign_str='' - 当有签字验证信息时，验证信息字符串

            可以支持etree.tostring的参数:
            method="xml"
            xml_declaration=None - 控制是否在文件中添加xml的声明，True - 一直添加, False - 不添加
                如果传None，代表只有encoding不是US-ASCII or UTF-8 or Unicode的时候才添加声明
            pretty_print=True - 是否针对打印格式美化
            with_tail=True
            standalone=None
            doctype=None
            exclusive=False
            inclusive_ns_prefixes=None
            with_comments=True
            strip_text=False

        @returns {byte[]} - 二进制数组

        """
        _str_ret = cls._msg_to_str(msg, msg_id=msg_id, **kwargs)
        _encoding = cls._get_para_from_kwargs(
            'encoding', default_value='utf-8', kwargs=kwargs)
        _msg_bytes = bytes(_str_ret, _encoding)
        return _msg_bytes


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    # 打印版本信息
    print(('模块名：%s  -  %s\n'
           '作者：%s\n'
           '发布日期：%s\n'
           '版本：%s' % (__MOUDLE__, __DESCRIPT__, __AUTHOR__, __PUBLISH__, __VERSION__)))

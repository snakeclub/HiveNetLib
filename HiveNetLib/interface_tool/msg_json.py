#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
#
# Copyright 2018 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
json报文处理模块

@module msg_json
@file msg_json.py

"""

import os
import sys
import json
# 根据当前文件路径将包路径纳入，在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir, os.path.pardir)))
# 动态添加包安装
import HiveNetLib.deps_tool as deps_tool
try:
    from jsonpath_rw import jsonpath, parse
except ImportError:
    deps_tool.install_package('jsonpath-rw')
    from jsonpath_rw import jsonpath, parse
# 引用自有模块
from HiveNetLib.generic import CResult
from HiveNetLib.interface_tool.msg_fw import EnumMsgObjType, MsgFW
from HiveNetLib.interface_tool.msg_xml import MsgXML
from HiveNetLib.base_tools.exception_tool import ExceptionTool


__MOUDLE__ = 'msg_json'  # 模块名
__DESCRIPT__ = u'json报文处理模块'  # 模块描述
__VERSION__ = '0.1.0'  # 版本
__AUTHOR__ = u'黎慧剑'  # 作者
__PUBLISH__ = '2018.09.13'  # 发布日期


class MsgJSON(MsgXML):
    """
    JSON报文信息处理类（message）
    注意：当传入字符串为''时，报文处理对象为None
    """
    #############################
    # 静态函数
    #############################
    @staticmethod
    def get_jsonpath_location_string(find_full_path_obj, left_string=''):
        """
        获取通过jsonpath匹配到对象的代码定位字符串

        @param {object} find_full_path_obj - jsonpath_expr.find函数匹配到的对象的full_path对象
        @param {string} last_string='' - 前缀定位字符串，可以为变量名，也可以不传

        @return {string} - 代码定位字符串

        @example
            _json_str = '{"foo": [{"baz": 0}, {"baz": 1}]}'
            _json_obj = json.loads(_json_str)
            _jsonpath_expr = parse('foo[*].baz')
            _find_obj = _jsonpath_expr.find(_json_obj)
            _location_string = MsgJSON.get_jsonpath_location_string(_find_obj[0].full_path)

            则得到
            _location_string 的值为 '["foo"][0]["baz"]'
        """
        _left_string = left_string
        # 递归方式处理
        if hasattr(find_full_path_obj, 'left'):
            _left_string = MsgJSON.get_jsonpath_location_string(
                find_full_path_obj.left, left_string=_left_string
            )
        if hasattr(find_full_path_obj, 'right'):
            _left_string = MsgJSON.get_jsonpath_location_string(
                find_full_path_obj.right, left_string=_left_string
            )

        # 已经没有left和right的属性，说明已经到路径值了
        if hasattr(find_full_path_obj, 'fields'):
            _left_string = '%s["%s"]' % (
                _left_string,
                '"]["'.join(find_full_path_obj.fields)
            )
        elif hasattr(find_full_path_obj, 'index'):
            _left_string = '%s[%s]' % (_left_string, str(find_full_path_obj.index))

        return _left_string

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
        return 'MsgJSON'

    @classmethod
    def _load_msg(cls, obj, msg_id=None, obj_type=EnumMsgObjType.String, **kwargs):
        """
        装载报文对象，将传入的报文对象转换为基础处理对象（python对象，json.loads得到的对象）

        @param {object} obj - 要装载的报文载体（与obj_type结合来判断是什么对象），例如：
            obj_type = EnumMsgObjType.File 时，obj为文件路径
            obj_type = EnumMsgObjType.String 时，obj为报文文本
        @param {EnumMsgObjType} msg_id=None - 报文id（用于标明该报文是什么报文）
        @param {object} obj_type=EnumMsgObjType.String - 报文载体对象类型
        @param {**kwargs} kwargs - 装载参数，包括：
            encoding='utf-8' - 装载字符编码
            has_sign_info=False - 是否带有签字验证信息（在json文档结尾），如果有，转换时会去除
            sign_begin_tag='' - 当有签字验证信息时，标记验证信息开头字符串，用于删除验证信息

        @returns {object} - 报文体对象（python对象，json.loads得到的对象）

        @throws {UnboundLocalError} - 对应标准错误码21001，当遇到obj_type不支持时抛出

        """
        _msg = None
        if obj_type in (EnumMsgObjType.File, EnumMsgObjType.String, EnumMsgObjType.Bytes):
            # 字符串方式及二进制
            _json_str = ''
            _encoding = MsgFW._get_para_from_kwargs(
                'encoding', default_value='utf-8', kwargs=kwargs)
            _has_sign_info = MsgFW._get_para_from_kwargs(
                'has_sign_info', default_value=False, kwargs=kwargs)
            _sign_begin_tag = MsgFW._get_para_from_kwargs(
                'sign_begin_tag', default_value='', kwargs=kwargs)

            if obj_type == EnumMsgObjType.File:
                with open(obj, 'rt', encoding=_encoding) as f:
                    _json_str = f.read()
            elif obj_type == EnumMsgObjType.Bytes:
                _json_str = obj.decode(_encoding)
            else:
                _json_str = obj

            # 支持空字符串的处理
            if _json_str == '':
                return None

            if _has_sign_info:
                # 要删除掉最后面的签名信息
                _sign_begin = _json_str.rfind(_sign_begin_tag)
                if _sign_begin != -1:
                    _json_str = _json_str[0:_sign_begin]

            # 生成对象
            _msg = json.loads(_json_str)
        else:
            # 不支持的格式
            raise UnboundLocalError

        # 返回结果
        return _msg

    @classmethod
    def _set_msg_value(cls, msg, search_path, value, msg_id=None, **kwargs):
        """
        设置报文的内容

        @param {object} msg - 报文对象（python对象，json.loads得到的对象）
        @param {string} search_path - 需要设置值的搜索路径，符合jsonPath规范
        @param {string} value - 要设置的值
        @param {string} msg_id=None - 报文id（用于标明该报文业务类型）
        @param {**kwargs} kwargs - 设置参数（暂未使用）

        @returns {object} - 设置值后的报文对象（python对象，json.loads得到的对象）

        @throws {NameError} - 对应标准错误码21002，当参数路径不存在时抛出

        """
        # 支持空字符串的处理
        if msg is None:
            raise NameError

        _msg = msg
        _jsonpath_expr = parse(search_path)
        _nodes = _jsonpath_expr.find(_msg)
        if len(_nodes) == 0:
            raise NameError
        else:
            for _item in _nodes:
                # 修改对象值
                exec(
                    '_msg%s = str(value)' % (
                        MsgJSON.get_jsonpath_location_string(_item.full_path)
                    )
                )
        return _msg

    @classmethod
    def _get_msg_value(cls, msg, search_path, msg_id=None, **kwargs):
        """
        获取报文的内容（注意只获取第1个取到的节点值）

        @param {object} msg - 主报文对象（python对象，json.loads得到的对象）
        @param {string} search_path - 需要获取值的搜索路径，符合jsonPath规范
        @param {string} msg_id=None - 报文id（用于标明该报文业务类型）
        @param {**kwargs} kwargs - 设置参数（暂未使用）

        @returns {string} - 获取到的值

        @throws {NameError} - 对应标准错误码21002，当参数路径不存在时抛出

        """
        # 支持空字符串的处理
        if msg is None:
            raise NameError

        _get_value = None
        _jsonpath_expr = parse(search_path)
        _nodes = _jsonpath_expr.find(msg)
        if len(_nodes) == 0:
            raise NameError
        else:
            _get_value = _nodes[0].value
        return _get_value

    @classmethod
    def _append_submsg(cls, submsg, msg, search_path, msg_id=None, submsg_id=None, **kwargs):
        """
        将子报文对象添加到主报文对象中

        @param {object} submsg - 子报文对象（python对象，json.loads得到的对象）
        @param {object} msg - 主报文对象（python对象，json.loads得到的对象）
        @param {string} search_path - 添加位置的搜索路径，符合jsonPath规范
        @param {string} msg_id=None - 主报文id（用于标明该报文业务类型）
        @param {string} submsg_id=None - 子报文id（用于标明该报文业务类型）
        @param {**kwargs} kwargs - 添加参数（具体由实现类定义）

        @returns {object} - 完成添加后的主报文对象（python对象，json.loads得到的对象）

        @throws {NameError} - 对应标准错误码21002，当参数路径不存在时抛出

        """
        # 支持空字符串的处理
        if msg is None:
            raise NameError

        _msg = msg
        _jsonpath_expr = parse(search_path)
        _nodes = _jsonpath_expr.find(msg)
        if len(_nodes) == 0:
            raise NameError
        else:
            exec(
                '_msg%s = submsg' % (
                    MsgJSON.get_jsonpath_location_string(_nodes[0].full_path)
                )
            )
        return _msg

    @classmethod
    def _msg_to_str(cls, msg, msg_id=None, **kwargs):
        """
        将主报文对象转换为字符串格式

        @param {object} msg - 报文对象（python对象，json.loads得到的对象）
        @param {string} msg_id=None - 主报文id（用于标明该报文是什么报文）
        @param {**kwargs} kwargs - 转换参数，包括：
            has_sign_info=False - 是否带有签字验证信息（在json文档结尾），如果有，转换时加到字符串中
            sign_str='' - 当有签字验证信息时，验证信息字符串

        @returns {string} - 输出字符串

        """
        # 支持空字符串的处理
        if msg is None:
            return ''

        _msg_str = ''
        _has_sign_info = cls._get_para_from_kwargs(
            'has_sign_info', default_value=False, kwargs=kwargs)
        _sign_str = cls._get_para_from_kwargs(
            'sign_str', default_value='', kwargs=kwargs)

        _msg_str = json.dumps(msg, ensure_ascii=False)

        # 添加签名证书
        if _has_sign_info:
            _msg_str = _msg_str + _sign_str

        return _msg_str

    @classmethod
    def _msg_to_bytes(cls, msg, msg_id=None, **kwargs):
        """
        将报文对象转换为二进制数组（用于网络通讯）

        @param {object} msg - 报文对象（python对象，json.loads得到的对象）
        @param {string} msg_id=None - 主报文id（用于标明该报文业务类型）
        @param {**kwargs} kwargs - 转换参数，包括
            encoding='utf-8' - 字符编码
            has_sign_info=False - 是否带有签字验证信息（在json文档结尾），如果有，转换时加到字符串中
            sign_str='' - 当有签字验证信息时，验证信息字符串

        @returns {byte[]} - 二进制数组

        """
        # 支持空字符串的处理
        if msg is None:
            return bytes()

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

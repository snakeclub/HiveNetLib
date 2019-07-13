#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
#
# Copyright 2018 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
Http协议头信息

@module protocol_msg_http
@file protocol_msg_http.py

"""

import os
import sys
from datetime import datetime
from time import mktime
from wsgiref.handlers import format_date_time
# 根据当前文件路径将包路径纳入，在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir, os.path.pardir)))
from HiveNetLib.generic import CResult, NullObj
from HiveNetLib.interface_tool.msg_fw import EnumMsgObjType, EnumMsgSRType, MsgFW
from HiveNetLib.base_tools.exception_tool import ExceptionTool


__MOUDLE__ = 'protocol_msg_http'  # 模块名
__DESCRIPT__ = u'Http协议头信息'  # 模块描述
__VERSION__ = '0.1.0'  # 版本
__AUTHOR__ = u'黎慧剑'  # 作者
__PUBLISH__ = '2018.09.14'  # 发布日期


class MsgHTTP(MsgFW):
    """
    HTTP协议报文信息处理类（message）

    """

    #############################
    # 工具函数
    #############################
    @staticmethod
    def get_http_datetime_format(t):
        """
        将指定的datetime转换为HTTP协议的日期格式

        @param {datetime} t - 要转换的时间

        @returns {string} - Http格式的字符串，例如'Wed, 22 Oct 2008 10:52:40 GMT'

        """
        _stamp = mktime(t.timetuple())
        return format_date_time(_stamp)

    #############################
    # 报文体处理函数
    #############################
    @classmethod
    @property
    def msg_type(cls):
        """
        消息对象的类型

        @property {string}

        """
        return 'MsgHTTP'

    @classmethod
    def _load_msg(cls, obj, msg_id=None, obj_type=EnumMsgObjType.String, **kwargs):
        """
        装载报文体对象，将传入的报文对象转换为基础处理对象

        @param {object} obj - 要装载的报文载体（与obj_type结合来判断是什么对象），例如：
            obj_type = EnumMsgObjType.File 时，obj为文件路径
            obj_type = EnumMsgObjType.String 时，obj为报文文本
        @param {EnumMsgObjType} msg_id=None - 报文id（用于标明该报文是什么报文）
        @param {object} obj_type=EnumMsgObjType.String - 报文载体对象类型
        @param {**kwargs} kwargs - 装载参数，包括：
            encoding='ascii' - 装载字符编码
            is_with_first_line=True  - 是否包含第1行信息
            msg_sr_type='EnumMsgSRType.Auto' - 报文收发类型，如果为Auto则信息中必须包含第1行的信息
            ver='HTTP/1.0' - 默认的版本号
            reqtype='GET' - 默认请求方法
            url='' - 默认的请求地址
            statcode='200' - 默认的响应码
            statmsg='OK' - 默认响应消息

        @returns {object} - 报文体对象，格式如下：
                msg.sr_type {EnumMsgSRType} - 报文发送类型
                msg.ver {string} - 版本
                msg.statcode {string} - 反馈报文才有的信息，状态码
                msg.statmsg {string} - 反馈报文才有的信息，状态信息
                msg.reqtype {string} - 请求报文才有的信息，请求类型
                msg.url {string} - 请求报文才有的信息，请求url
                msg.para {dict} - 报文参数，key为参数名，value为参数值，都是string格式
                msg.para_upper_map {dict} - 报文参数名大写映射，key为大写的参数名，value为原报文参数（支持不区分大小写）

        @throws {UnboundLocalError} - 对应标准错误码21001，当遇到obj_type不支持时抛出
        @throws {ValueError} - 对应标准错误码21002，当msg_sr_type取值冲突时抛出

        """
        _msg = None
        if obj_type == EnumMsgObjType.File or obj_type == EnumMsgObjType.String or obj_type == EnumMsgObjType.Bytes:
            # 字符串方式及二进制
            _http_str = ''
            _encoding = cls._get_para_from_kwargs(
                'encoding', default_value='ascii', kwargs=kwargs)
            _is_with_first_line = cls._get_para_from_kwargs(
                'is_with_first_line', default_value=True, kwargs=kwargs)
            _msg_sr_type = cls._get_para_from_kwargs(
                'msg_sr_type', default_value=EnumMsgSRType.Auto, kwargs=kwargs)

            if _msg_sr_type == EnumMsgSRType.Auto and not _is_with_first_line:
                raise ValueError

            if obj_type == EnumMsgObjType.File:
                with open(obj, 'rt', encoding=_encoding) as f:
                    _http_str = f.read()
            elif obj_type == EnumMsgObjType.Bytes:
                _http_str = obj.decode(_encoding)
            else:
                _http_str = obj

            # 转换为行数组进行处理
            _lines = _http_str.replace('\r\n', '\n').replace('\r', '\n').split('\n')
            _index = 0

            # 组装报文头
            _msg = NullObj()
            if _is_with_first_line:
                # 包含第1行，解析处理
                _index = 1
                _headparas = _lines[0].split(' ')
                if _headparas[0].upper()[0:4] == "HTTP":
                    # 响应报文
                    _msg.sr_type = EnumMsgSRType.Response
                    _msg.ver = _headparas[0]
                    _msg.statcode = _headparas[1]
                    _msg.statmsg = _lines[0][len(_msg.ver) + len(_msg.statcode) + 2:]
                else:
                    # 请求报文
                    _msg.sr_type = EnumMsgSRType.Request
                    _msg.reqtype = _headparas[0]
                    _msg.url = ''
                    _msg.ver = ''
                    if len(_headparas) > 1:
                        _msg.url = _headparas[1]
                    if len(_headparas) > 2:
                        _msg.ver = _headparas[2]
            else:
                # 不包含第1行
                _msg.sr_type = _msg_sr_type
                _msg.ver = cls._get_para_from_kwargs(
                    'ver', default_value='HTTP/1.0', kwargs=kwargs)
                if _msg_sr_type == EnumMsgSRType.Response:
                    _msg.statcode = cls._get_para_from_kwargs(
                        'statcode', default_value='200', kwargs=kwargs)
                    _msg.statmsg = cls._get_para_from_kwargs(
                        'statmsg', default_value='OK', kwargs=kwargs)
                else:
                    _msg.reqtype = cls._get_para_from_kwargs(
                        'reqtype', default_value='GET', kwargs=kwargs)
                    _msg.url = cls._get_para_from_kwargs(
                        'url', default_value='', kwargs=kwargs)

            # 请求参数
            _msg.para = {}
            _msg.para_upper_map = {}
            while _index < len(_lines):
                _str = _lines[_index]
                if _str != '':
                    _spit_index = _str.find(':')
                    if _spit_index == -1:
                        _msg.para[_str] = ''
                        _msg.para_upper_map[_str.upper()] = _str
                    else:
                        _msg.para[_str[0:_spit_index]] = _str[_spit_index + 1:]
                        _msg.para_upper_map[_str[0: _spit_index].upper()] = _str[0: _spit_index]
                _index = _index + 1
        else:
            # 不支持的格式
            raise UnboundLocalError

        # 返回结果
        return _msg

    @classmethod
    def _set_msg_value(cls, msg, search_path, value, msg_id=None, **kwargs):
        """
        设置报文的内容

        @param {object} msg - 主报文对象（基础处理对象）
        @param {object} search_path - 需要设置值的索引搜索路径，只需要给出参数名（不区分大小写）
            注意：该参数名不能修改报文请求行的值,不存在的参数名将进行新增
        @param {object} value - 要设置值，如果为None代表删除参数
        @param {string} msg_id=None - 报文id（用于标明该报文是什么报文）
        @param {**kwargs} kwargs - 设置参数（暂未使用）

        @returns {object} - 设置值后的报文对象（基础处理对象）

        """
        _msg = msg
        _upper = search_path.upper()
        if value is None and _upper in _msg.para_upper_map.keys():
            # 删除参数
            del _msg.para[_msg.para_upper_map[_upper]]
            del _msg.para_upper_map[_upper]
        else:
            # 新增或修改参数
            if _upper not in _msg.para_upper_map.keys():
                _msg.para_upper_map[_upper] = search_path
            _msg.para[_msg.para_upper_map[_upper]] = str(value)
        return _msg

    @classmethod
    def _get_msg_value(cls, msg, search_path, msg_id=None, **kwargs):
        """
        获取报文的内容

        @param {object} msg - 报文对象（基础处理对象）
        @param {object} search_path - 需要获取值的索引搜索路径,只需要给出参数名（不区分大小写）
        @param {string} msg_id=None - 报文id（用于标明该报文是什么报文）
        @param {**kwargs} kwargs - 设置参数（暂未使用）

        @returns {string} - 获取到的值，当参数不存在时返回None

        @throws {NameError} - 对应标准错误码21002，当参数路径不存在时抛出

        """
        _get_value = None
        _upper = search_path.upper()
        if _upper in msg.para_upper_map.keys():
            _get_value = msg.para[msg.para_upper_map[_upper]]
        return _get_value

    @classmethod
    def _append_submsg(cls, submsg, msg, search_path, msg_id=None, submsg_id=None, **kwargs):
        """
        将子报文对象添加到主报文对象中
        (进行参数数据合并，相同的参数名不覆盖)

        @param {object} submsg - 子报文对象（基础处理对象）
        @param {object} msg - 主报文对象（基础处理对象）
        @param {object} search_path - 添加位置的搜索路径(参数无效))
        @param {string} msg_id=None - 主报文id（用于标明该报文是什么报文）
        @param {string} submsg_id=None - 子报文id（用于标明该报文是什么报文）
        @param {**kwargs} kwargs - 添加参数（具体由实现类定义）

        @returns {object} - 完成添加后的主报文对象

        """
        _msg = msg
        for _key in submsg.para_upper_map.keys():
            if _key not in _msg.para_upper_map.keys():
                _msg.para[submsg.para_upper_map[_key]] = submsg.para[submsg.para_upper_map[_key]]
        return _msg

    @classmethod
    def _msg_to_str(cls, msg, msg_id=None, **kwargs):
        """
        将报文对象转换为字符串格式

        @param {object} msg - 报文对象（基础处理对象）
        @param {string} msg_id=None - 主报文id（用于标明该报文是什么报文）
        @param {**kwargs} kwargs - 转换参数（具体由实现类定义）

        @returns {string} - 输出字符串

        @throws {NotImplementedError} - 当实现类没有实现该方法时，抛出该异常

        """
        _msg_str = ''
        if msg.sr_type == EnumMsgSRType.Request:
            # 请求报文
            _msg_str = msg.reqtype + ' ' + msg.url + ' ' + msg.ver + '\r\n'
        else:
            # 返回报文
            _msg_str = msg.ver + ' ' + msg.statcode + ' ' + msg.statmsg + '\r\n'
        # 消息参数
        for _key in msg.para_upper_map.keys():
            _msg_str = _msg_str + \
                msg.para_upper_map[_key] + ":" + msg.para[msg.para_upper_map[_key]] + '\r\n'
        # 增加一个空行
        _msg_str = _msg_str + '\r\n'
        return _msg_str

    @classmethod
    def _msg_to_bytes(cls, msg, msg_id=None, **kwargs):
        """
        将主报文对象转换为二进制数组（用于网络通讯）

        @param {object} msg - 报文对象（基础处理对象）
        @param {string} msg_id=None - 主报文id（用于标明该报文是什么报文）
        @param {**kwargs} kwargs - 转换参数，包括
            encoding='ascii' - 字符编码

        @returns {byte[]} - 二进制数组

        """
        _msg_str = cls._msg_to_str(msg, msg_id=msg_id, **kwargs)
        _encoding = cls._get_para_from_kwargs(
            'encoding', default_value='ascii', kwargs=kwargs)
        _msg_bytes = bytes(_msg_str, _encoding)
        return _msg_bytes


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    # 打印版本信息
    print(('模块名：%s  -  %s\n'
           '作者：%s\n'
           '发布日期：%s\n'
           '版本：%s' % (__MOUDLE__, __DESCRIPT__, __AUTHOR__, __PUBLISH__, __VERSION__)))

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
import copy
import json
import xmltodict
from lxml import etree
sys.path.append(os.path.abspath(os.path.dirname(__file__)+'/'+'../..'))
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

    原理为将JSON转换为XML格式进行处理，基于MsgXML降低使用成本

    """

    #############################
    # 以下为覆盖父类函数
    #############################

    @classmethod
    @property
    def MsgType(cls):
        """
        返回消息对象的类型（实现类应将自己类名返回）
        @property {string}
        """
        return 'MsgJSON'

    @classmethod
    def load_msg(cls, obj, msg_id=None, obj_type=EnumMsgObjType.String, **kwargs):
        """
        装载报文体对象（主报文）

        @param {object} obj - 要装载的报文载体（与obj_type结合来判断是什么对象），例如：
            obj_type = EnumMsgObjType.File 时，obj为文件路径
            obj_type = EnumMsgObjType.String 时，obj为报文文本
        @param {EnumMsgObjType} msg_id=None - 报文id（用于标明该报文是什么报文）
        @param {object} obj_type=EnumMsgObjType.String - 报文载体对象类型
        @param {**kwargs} kwargs - 装载参数，包括：
            encoding='utf-8' - 装载字符编码
            has_sign_info=False - 是否带有签字验证信息（在xml文档结尾），如果有，转换时会去除
            sign_begin_tag='' - 当有签字验证信息时，标记验证信息开头字符串，用于删除验证信息
        @returns {HiveNetLib.generic.CResult} - 处理结果（符合HiveNet 错误码规范）
            当处理结果为成功时，通过CResult返回报文体对象：
            CResult.msg {object}  - 报文体对象(具体对象类型在实现类定义)

        """
        _ret = CResult('00000')
        _ret.msg = None
        with ExceptionTool.ignored_cresult(result_obj=_ret, error_map={UnboundLocalError: ('20301', None)}):
            _msg = None
            if obj_type == EnumMsgObjType.File or obj_type == EnumMsgObjType.String or obj_type == EnumMsgObjType.Bytes:
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

                if _has_sign_info:
                    # 要删除掉最后面的签名信息
                    _sign_begin = _json_str.rfind(_sign_begin_tag)
                    if _sign_begin != -1:
                        _json_str = _json_str[0:_sign_begin]

                # 生成对象
                _json_obj = json.loads(_json_str)
                _xml_str = xmltodict.unparse(_json_obj)
                _msg = etree.fromstring(bytes(_xml_str, _encoding))

            else:
                # 不支持的格式
                raise UnboundLocalError

            _ret.msg = _msg

        # 返回结果
        return _ret

    @classmethod
    def msg_to_str(cls, msg, msg_id=None, **kwargs):
        """
        将主报文对象转换为字符串格式

        @param {object} msg - 报文对象
        @param {string} msg_id=None - 主报文id（用于标明该报文是什么报文）
        @param {**kwargs} kwargs - 转换参数，包括：
            has_sign_info=False - 是否带有签字验证信息（在json文档结尾），如果有，转换时加到字符串中
            sign_str='' - 当有签字验证信息时，验证信息字符串

        @returns {HiveNetLib.generic.CResult} - 处理结果（符合HiveNet 错误码规范）
            当处理结果为成功时，通过CResult返回结果对象：
            CResult.msg_str {string}  - 输出字符串

        """
        _ret = CResult('00000')
        _ret.msg_str = ''
        _msg = copy.deepcopy(msg)
        with ExceptionTool.ignored_cresult(result_obj=_ret, error_map={}):
            _has_sign_info = cls._get_para_from_kwargs(
                'has_sign_info', default_value=False, kwargs=kwargs)
            _sign_str = cls._get_para_from_kwargs(
                'sign_str', default_value='', kwargs=kwargs)

            _dictobj = xmltodict.parse(str(etree.tostring(_msg, encoding="utf-8"), "utf-8"))
            _ret.msg_str = json.dumps(_dictobj, indent=4)

            # 添加签名证书
            if _has_sign_info:
                _ret.msg_str = _ret.msg_str + _sign_str
        return _ret


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    # 打印版本信息
    print(('模块名：%s  -  %s\n'
           '作者：%s\n'
           '发布日期：%s\n'
           '版本：%s' % (__MOUDLE__, __DESCRIPT__, __AUTHOR__, __PUBLISH__, __VERSION__)))

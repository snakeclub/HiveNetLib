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
from lxml import etree
sys.path.append(os.path.abspath(os.path.dirname(__file__)+'/'+'../..'))
from HiveNetLib.generic import CResult
from HiveNetLib.interface_tool.msg_fw import EnumMsgObjType, MsgFW
from HiveNetLib.base_tools.exception_tool import ExceptionTool

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
    # 报文体处理函数
    #############################
    @classmethod
    @property
    def MsgType(cls):
        """
        返回消息对象的类型（实现类应将自己类名返回）
        @property {string}
        """
        return 'MsgXML'

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
            remove_namespace_prefix=() - 清除节点的命名空间前缀（目的是简化xpath），为一个数组，例如('prefix1', 'prefix2')
            add_namespace_prefix=() - 为指定节点及子节点增加命名空间前缀，为一个二维数组，例如：
                (('xpath1', 'prefix1'), ('xpath2', 'prefix2'))，其中xpath是符合xml的xpath规范的搜索字符串
            remove_namespace_attr=() - 清除节点的命名空间（目的是简化xpath），为一个数组，例如('name1', 'name2')
                实际上去除的是 xmlns="name1"
            add_namespace_attr=() - 新增节点的命名空间，为一个二维数组，例如：
                (('xpath1', 'name1'), ('xpath2', 'name2'))，其中xpath是符合xml的xpath规范的搜索字符串
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
                _xmlstr = ''
                _encoding = cls._get_para_from_kwargs(
                    'encoding', default_value='utf-8', kwargs=kwargs)
                _has_sign_info = cls._get_para_from_kwargs(
                    'has_sign_info', default_value=False, kwargs=kwargs)
                _sign_begin_tag = cls._get_para_from_kwargs(
                    'sign_begin_tag', default_value='', kwargs=kwargs)
                _remove_namespace_prefix = cls._get_para_from_kwargs(
                    'remove_namespace_prefix', default_value=(), kwargs=kwargs)
                _add_namespace_prefix = cls._get_para_from_kwargs(
                    'add_namespace_prefix', default_value=(), kwargs=kwargs)
                _remove_namespace_attr = cls._get_para_from_kwargs(
                    'remove_namespace_attr', default_value=(), kwargs=kwargs)
                _add_namespace_attr = cls._get_para_from_kwargs(
                    'add_namespace_attr', default_value=(), kwargs=kwargs)

                if obj_type == EnumMsgObjType.File:
                    with open(obj, 'rt', encoding=_encoding) as f:
                        _xmlstr = f.read()
                elif obj_type == EnumMsgObjType.Bytes:
                    _xmlstr = obj.decode(_encoding)
                else:
                    _xmlstr = obj

                _has_xml_def = False
                if _xmlstr[0:5] == "<?xml":
                    _has_xml_def = True

                if _has_sign_info:
                    # 要删除掉最后面的签名信息
                    _sign_begin = _xmlstr.rfind(_sign_begin_tag)
                    if _sign_begin != -1:
                        _xmlstr = _xmlstr[0:_sign_begin]

                # 处理删除命名空间前缀
                for _prefix in _remove_namespace_prefix:
                    _xmlstr = _xmlstr.replace("<"+_prefix+":", "<")

                # 处理删除命名空间
                for _attr in _remove_namespace_attr:
                    _xmlstr = _xmlstr.replace(' xmlns="' + _attr + '"', '')

                # 生成对象
                if _has_xml_def:
                    # 有xml定义，要转回二进制处理
                    _msg = etree.fromstring(bytes(_xmlstr, _encoding))
                else:
                    _msg = etree.fromstring(_xmlstr)
            else:
                # 不支持的格式
                raise UnboundLocalError

            # 处理新增命名空间前缀
            for _prefix in _add_namespace_prefix:
                _msg = cls.add_namespace_prefix(_msg, _prefix[0], _prefix[1])
            # 处理新增命名空间属性
            for _attr in _add_namespace_attr:
                _msg = cls.add_namespace_attr(_msg, _attr[0], _attr[1])

            _ret.msg = _msg

        # 返回结果
        return _ret

    @classmethod
    def load_submsg(cls, obj, submsg_id=None, obj_type=None, **kwargs):
        """
        装载子报文体对象（独立对象，不嵌入主报文中）
        函数定义与load_msg一致： @see load_msg

        """
        return cls.load_msg(obj=obj, msg_id=submsg_id, obj_type=obj_type, **kwargs)

    @classmethod
    def set_msg_value(cls, msg, search_path, value, msg_id=None, **kwargs):
        """
        设置主报文的内容

        @param {object} msg - 主报文对象
        @param {string} search_path - 需要设置值的搜索路径，符合xpath规范
        @param {string} value - 要设置的值
        @param {string} msg_id=None - 报文id（用于标明该报文是什么报文）
        @param {**kwargs} kwargs - 设置参数（暂未使用）

        @returns {HiveNetLib.generic.CResult} - 处理结果（符合HiveNet 错误码规范）
            当处理结果为成功时，通过CResult返回报文体对象：
            CResult.msg {object}  - 设置值后的报文对象

        """
        _ret = CResult('00000')
        _ret.msg = msg
        with ExceptionTool.ignored_cresult(result_obj=_ret, error_map={}):
            _nodes = _ret.msg.xpath(search_path)
            if len(_nodes) == 0:
                _ret.change_code('20302')
                _ret.trace_str = ('set value to xpath "' + search_path +
                                  ' failure，can\'t find nodes, xml="' +
                                  str(etree.tostring(msg, encoding='utf-8'), 'utf-8'))
            else:
                for _item in _nodes:
                    _item.text = str(value)
        return _ret

    @classmethod
    def set_submsg_value(cls, submsg, search_path, value, submsg_id=None, **kwargs):
        """
        设置子报文的内容
        函数定义与set_msg_value一致： @see set_msg_value

        """
        return cls.set_msg_value(submsg, search_path, value, msg_id=submsg_id, **kwargs)

    @classmethod
    def get_msg_value(cls, msg, search_path, msg_id=None, **kwargs):
        """
        获取主报文的内容（注意只获取第1个取到的节点值）

        @param {object} msg - 主报文对象
        @param {string} search_path - 需要获取值的搜索路径，符合xpath规范
        @param {string} msg_id=None - 报文id（用于标明该报文是什么报文）
        @param {**kwargs} kwargs - 设置参数（暂未使用）

        @returns {HiveNetLib.generic.CResult} - 处理结果（符合HiveNet 错误码规范）
            当处理结果为成功时，通过CResult返回报文体对象：
            CResult.get_value {object}  - 获取到的值

        """
        _ret = CResult('00000')
        _ret.get_value = None
        with ExceptionTool.ignored_cresult(result_obj=_ret, error_map={}):
            _nodes = msg.xpath(search_path)
            if len(_nodes) == 0:
                _ret.change_code('20302')
                _ret.trace_str = ('get value from xpath "' + search_path +
                                  ' failure，can\'t find nodes, xml="' +
                                  str(etree.tostring(msg, encoding='utf-8'), 'utf-8'))
            else:
                _ret.get_value = _nodes[0].text
        return _ret

    @classmethod
    def get_submsg_value(cls, submsg, search_path, submsg_id=None, **kwargs):
        """
        获取主报文的内容
        函数定义与get_msg_value一致： @see get_msg_value

        """
        return cls.get_msg_value(submsg, search_path, msg_id=submsg_id, **kwargs)

    @classmethod
    def append_submsg(cls, submsg, msg, search_path, msg_id=None, submsg_id=None, **kwargs):
        """
        将子报文对象添加到主报文对象中

        @param {object} submsg - 子报文对象
        @param {object} msg - 主报文对象
        @param {string} search_path - 添加位置的搜索路径，符合xpath规范
        @param {string} msg_id=None - 主报文id（用于标明该报文是什么报文）
        @param {string} submsg_id=None - 子报文id（用于标明该报文是什么报文）
        @param {**kwargs} kwargs - 添加参数（具体由实现类定义）

        @returns {HiveNetLib.generic.CResult} - 处理结果（符合HiveNet 错误码规范）
            当处理结果为成功时，通过CResult返回报文体对象：
            CResult.msg {object}  - 完成添加后的主报文对象

        """
        _ret = CResult('00000')
        _ret.msg = msg
        with ExceptionTool.ignored_cresult(result_obj=_ret, error_map={}):
            _nodes = _ret.msg.xpath(search_path)
            if len(_nodes) == 0:
                _ret.change_code('20302')
                _ret.trace_str = ('add submsg to xpath "' + search_path +
                                  ' failure，can\'t find nodes, xml="' +
                                  str(etree.tostring(msg, encoding='utf-8'), 'utf-8'))
            else:
                _nodes[0].append(submsg)
        return _ret

    @classmethod
    def msg_to_str(cls, msg, msg_id=None, **kwargs):
        """
        将主报文对象转换为字符串格式

        @param {object} msg - 报文对象
        @param {string} msg_id=None - 主报文id（用于标明该报文是什么报文）
        @param {**kwargs} kwargs - 转换参数，包括：
            has_sign_info=False - 是否带有签字验证信息（在xml文档结尾），如果有，转换时加到字符串中
            sign_str='' - 当有签字验证信息时，验证信息字符串
            remove_namespace_prefix=() - 清除节点的命名空间前缀（目的是简化xpath），为一个数组，例如('prefix1', 'prefix2')
            add_namespace_prefix=() - 为指定节点及子节点增加命名空间前缀，为一个二维数组，例如：
                (('xpath1', 'prefix1'), ('xpath2', 'prefix2'))，其中xpath是符合xml的xpath规范的搜索字符串
            remove_namespace_attr=() - 清除节点的命名空间（目的是简化xpath），为一个数组，例如('name1', 'name2')
                实际上去除的是 xmlns="name1"
            add_namespace_attr=() - 新增节点的命名空间，为一个二维数组，例如：
                (('xpath1', 'name1'), ('xpath2', 'name2'))，其中xpath是符合xml的xpath规范的搜索字符串

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
            _remove_namespace_prefix = cls._get_para_from_kwargs(
                'remove_namespace_prefix', default_value=(), kwargs=kwargs)
            _add_namespace_prefix = cls._get_para_from_kwargs(
                'add_namespace_prefix', default_value=(), kwargs=kwargs)
            _remove_namespace_attr = cls._get_para_from_kwargs(
                'remove_namespace_attr', default_value=(), kwargs=kwargs)
            _add_namespace_attr = cls._get_para_from_kwargs(
                'add_namespace_attr', default_value=(), kwargs=kwargs)

            # 处理新增命名空间前缀
            for _prefix in _add_namespace_prefix:
                _msg = cls.add_namespace_prefix(_msg, _prefix[0], _prefix[1])
            # 处理新增命名空间属性
            for _attr in _add_namespace_attr:
                _msg = cls.add_namespace_attr(_msg, _attr[0], _attr[1])

            _ret.msg_str = str(etree.tostring(_msg, encoding='utf-8'), 'utf-8')

            # 处理删除命名空间前缀
            for _prefix in _remove_namespace_prefix:
                _ret.msg_str = _ret.msg_str.replace('<'+_prefix+':', '<')

            # 处理删除命名空间
            for _attr in _remove_namespace_attr:
                _ret.msg_str = _ret.msg_str.replace(' xmlns="' + _attr + '"', '')

            # 添加签名证书
            if _has_sign_info:
                _ret.msg_str = _ret.msg_str + _sign_str
        return _ret

    @classmethod
    def submsg_to_str(cls, submsg, submsg_id=None, **kwargs):
        """
        将子报文对象转换为字符串格式
        函数定义与msg_to_str一致： @see msg_to_str

        """
        return cls.msg_to_str(submsg, msg_id=submsg_id, **kwargs)

    @classmethod
    def str_to_msg(cls, msg_str, msg_id=None, **kwargs):
        """
        将字符串转换为主报文对象

        @param {string} msg_str - 字符串
        @param {string} msg_id=None - 报文id（用于标明该报文是什么报文）
        @param {**kwargs} kwargs - 转换参数，包括：
            encoding='utf-8' - 装载字符编码
            has_sign_info=False - 是否带有签字验证信息（在xml文档结尾），如果有，转换时会去除
            sign_begin_tag='' - 当有签字验证信息时，标记验证信息开头字符串，用于删除验证信息
            remove_namespace_prefix=() - 清除节点的命名空间前缀（目的是简化xpath），为一个数组，例如('prefix1', 'prefix2')
            add_namespace_prefix=() - 为指定节点及子节点增加命名空间前缀，为一个二维数组，例如：
                (('xpath1', 'prefix1'), ('xpath2', 'prefix2'))，其中xpath是符合xml的xpath规范的搜索字符串
            remove_namespace_attr=() - 清除节点的命名空间（目的是简化xpath），为一个数组，例如('name1', 'name2')
                实际上去除的是 xmlns="name1"
            add_namespace_attr=() - 新增节点的命名空间，为一个二维数组，例如：
                (('xpath1', 'name1'), ('xpath2', 'name2'))，其中xpath是符合xml的xpath规范的搜索字符串

        @returns {HiveNetLib.generic.CResult} - 处理结果（符合HiveNet 错误码规范）
            当处理结果为成功时，通过CResult返回结果对象：
            CResult.msg {object}  - 报文对象

        """
        return cls.load_msg(msg_str, msg_id=msg_id, obj_type=EnumMsgObjType.String, **kwargs)

    @classmethod
    def str_to_submsg(cls, msg_str, submsg_id=None, **kwargs):
        """
        将字符串转换为主报文对象
        函数定义与str_to_msg一致： @see str_to_msg

        """
        return cls.str_to_msg(msg_str, msg_id=submsg_id, **kwargs)

    @classmethod
    def msg_to_bytes(cls, msg, msg_id=None, **kwargs):
        """
        将主报文对象转换为二进制数组（用于网络通讯）

        @param {object} msg - 报文对象
        @param {string} msg_id=None - 主报文id（用于标明该报文是什么报文）
        @param {**kwargs} kwargs - 转换参数，包括
            encoding='utf-8' - 字符编码
            has_sign_info=False - 是否带有签字验证信息（在xml文档结尾），如果有，转换时加到字符串中
            sign_str='' - 当有签字验证信息时，验证信息字符串
            remove_namespace_prefix=() - 清除节点的命名空间前缀（目的是简化xpath），为一个数组，例如('prefix1', 'prefix2')
            add_namespace_prefix=() - 为指定节点及子节点增加命名空间前缀，为一个二维数组，例如：
                (('xpath1', 'prefix1'), ('xpath2', 'prefix2'))，其中xpath是符合xml的xpath规范的搜索字符串
            remove_namespace_attr=() - 清除节点的命名空间（目的是简化xpath），为一个数组，例如('name1', 'name2')
                实际上去除的是 xmlns="name1"
            add_namespace_attr=() - 新增节点的命名空间，为一个二维数组，例如：
                (('xpath1', 'name1'), ('xpath2', 'name2'))，其中xpath是符合xml的xpath规范的搜索字符串

        @returns {HiveNetLib.generic.CResult} - 处理结果（符合HiveNet 错误码规范）
            当处理结果为成功时，通过CResult返回结果对象：
            CResult.msg_bytes {byte[]}  - 二进制数组

        """
        _str_ret = cls.msg_to_str(msg, msg_id=msg_id, **kwargs)
        if _str_ret.code[0] != '0':
            # 转换成字符串失败
            return _str_ret
        _encoding = cls._get_para_from_kwargs(
            'encoding', default_value='utf-8', kwargs=kwargs)
        _ret = CResult('00000')
        _ret.msg_bytes = bytes(_str_ret.msg_str, _encoding)
        return _ret

    @classmethod
    def bytes_to_msg(cls, msg_bytes, msg_id=None, **kwargs):
        """
        将二进制数组转换为主报文对象（解析网络通讯信息）

        @param {byte[]} msg_bytes - 二进制数组
        @param {string} msg_id=None - 报文id（用于标明该报文是什么报文）
        @param {**kwargs} kwargs - 转换参数，包括
            encoding='utf-8' - 装载字符编码
            has_sign_info=False - 是否带有签字验证信息（在xml文档结尾），如果有，转换时会去除
            sign_begin_tag='' - 当有签字验证信息时，标记验证信息开头字符串，用于删除验证信息
            remove_namespace_prefix=() - 清除节点的命名空间前缀（目的是简化xpath），为一个数组，例如('prefix1', 'prefix2')
            add_namespace_prefix=() - 为指定节点及子节点增加命名空间前缀，为一个二维数组，例如：
                (('xpath1', 'prefix1'), ('xpath2', 'prefix2'))，其中xpath是符合xml的xpath规范的搜索字符串
            remove_namespace_attr=() - 清除节点的命名空间（目的是简化xpath），为一个数组，例如('name1', 'name2')
                实际上去除的是 xmlns="name1"
            add_namespace_attr=() - 新增节点的命名空间，为一个二维数组，例如：
                (('xpath1', 'name1'), ('xpath2', 'name2'))，其中xpath是符合xml的xpath规范的搜索字符串

        @returns {HiveNetLib.generic.CResult} - 处理结果（符合HiveNet 错误码规范）
            当处理结果为成功时，通过CResult返回结果对象：
            CResult.msg {object}  - 报文对象

        """
        return cls.load_msg(msg_bytes, msg_id=msg_id, obj_type=EnumMsgObjType.Bytes, **kwargs)

    #############################
    # 内部处理函数
    #############################
    @classmethod
    def add_namespace_prefix(cls, msg, search_path, namespace_prefix):
        """
        为指定节点的所有子节点（含自身）增加命名空间前缀
        （例如：<a><b /></a>变为<prefix:a><prefix:b /></a>）

        @param {object} msg - 消息体对象
        @param {string} search_path - 搜索路径，符合xpath标准
        @param {string} namespace_prefix - 命名空间前缀

        @returns {object} - 处理后的对象，忽略所有异常

        """
        _msg = copy.deepcopy(msg)
        try:
            if search_path is None or search_path == '':
                # 不传入搜索路径代表全部节点增加命名空间前缀
                _xml = str(etree.tostring(_msg, encoding='utf-8'), 'utf-8')
                _xml = _xml.replace('<', '<' + namespace_prefix + ':')
                _msg = etree.fromstring(bytes(_xml, 'utf-8'))
            else:
                _nodes = _msg.xpath(search_path)
                if len(_nodes) == 0:
                    return _msg
                for _subnode in _nodes:
                    _parentNode = _subnode.getparent()
                    _newnode = cls.add_namespace_prefix(_subnode, '', namespace_prefix)
                    _parentNode.remove(_subnode)
                    _parentNode.append(_newnode)
            return _msg
        except Exception:
            return copy.deepcopy(msg)

    @classmethod
    def add_namespace_attr(cls, msg, search_path, namespace):
        """
        为指定节点增加命名空间属性
        （例如：<a xmlns="namespace"><b /></a> 变为 <a><b /></a>）

        @param {object} msg - 消息体对象
        @param {string} search_path - 搜索路径，符合xpath标准
        @param {string} namespace - 命名空间名

        @returns {object} - 处理后的对象，忽略所有异常

        """
        _msg = copy.deepcopy(msg)
        try:
            if search_path is None or search_path == '':
                _tag = _msg.tag
                _xml = str(etree.tostring(_msg, encoding='utf-8'), 'utf-8')
                _xml = _xml[0:len(_tag)+1] + ' xmlns="' + namespace + '"' + _xml[len(_tag)+1:]
                _msg = etree.fromstring(bytes(_xml, "utf-8"))
            else:
                _nodes = _msg.xpath(search_path)
                if len(_nodes) == 0:
                    return _msg
                for _subnode in _nodes:
                    _parentNode = _subnode.getparent()
                    _newnode = cls.add_namespace_attr(_subnode, '', namespace)
                    _parentNode.remove(_subnode)
                    _parentNode.append(_newnode)
            return _msg
        except Exception:
            return copy.deepcopy(_msg)


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    # 打印版本信息
    print(('模块名：%s  -  %s\n'
           '作者：%s\n'
           '发布日期：%s\n'
           '版本：%s' % (__MOUDLE__, __DESCRIPT__, __AUTHOR__, __PUBLISH__, __VERSION__)))
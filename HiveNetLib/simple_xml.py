#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
# Copyright 2018 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
简单xml文件处理模块
@module simple_xml
@file simple_xml.py
"""

import sys
import os
import re
from enum import Enum
import lxml.etree as ET
try:
    import chardet
except:
    pass
# 根据当前文件路径将包路径纳入，在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir)))


__MOUDLE__ = 'simple_xml'  # 模块名
__DESCRIPT__ = u'简单xml文件处理模块'  # 模块描述
__VERSION__ = '0.1.0'  # 版本
__AUTHOR__ = u'黎慧剑'  # 作者
__PUBLISH__ = '2019.10.19'  # 发布日期


class EnumXmlObjType(Enum):
    """
    xml对象类型

    @enum {int}

    """
    File = 0  # 文件
    FileHandle = 1  # 打开的文件句柄
    String = 2  # 字符串
    Bytes = 3  # 二进制数组


class SimpleXml(object):
    """
    Xml配置文件的处理

    @example
        可以通过访问SimpleXml.root直接使用lxml.etree的原生方法

    """

    #############################
    # 内部函数
    #############################
    def __init__(self, xml_obj, obj_type=EnumXmlObjType.File, encoding=None, use_chardet=True,
                 register_namespace=None, **kwargs):
        """
        构造函数

        @param {object} xml_obj - 要装载的报文载体（与obj_type结合来判断是什么对象），例如(仅供参考)：
            obj_type = EnumXmlObjType.File 时，obj为文件路径
            obj_type = EnumXmlObjType.FileHandle 时，obj为文件句柄
            obj_type = EnumXmlObjType.String 时，obj为报文文本
        @param {EnumXmlObjType} obj_type=EnumXmlObjType.File - xml对象类型
        @param {string} encoding=encoding - 装载字符编码，如果传None代表自动判断
        @param {bool} use_chardet=True - 当自动判断的时候，是否使用chardet库
        @param {dict} register_namespace=None - 注册命名空间别名，格式为：
            {prefix: uri, prefix: uri, ... }  其中prefix和uri都为字符串
            注册命名空间后，后续的节点就可以通过tag='{uri}tagname'的方式添加带命名空间的节点
        @param {**kwargs} kwargs - 扩展的装载参数，包括XMLParser的参数
            attribute_defaults - inject default attributes from DTD or XMLSchema
            dtd_validation - validate against a DTD referenced by the document
            load_dtd - use DTD for parsing
            no_network - prevent network access for related files (default: True)
            ns_clean - clean up redundant namespace declarations
            recover - try hard to parse through broken XML
            remove_blank_text - discard blank text nodes that appear ignorable
                装载时是否将空白文本去掉，只有含这个参数，打印时pretty_print才生效
            remove_comments - discard comments
            remove_pis - discard processing instructions
            strip_cdata - replace CDATA sections by normal text content (default: True)
            compact - save memory for short text content (default: True)
            collect_ids - use a hash table of XML IDs for fast access (default: True, always True with DTD validation)
            resolve_entities - replace entities by their text value (default: True)
            huge_tree - disable security restrictions and support very deep trees
            target - a parser target object that will receive the parse events
            schema - an XMLSchema to validate against
        """
        self.file = None  # xml对象的文件路径
        self.root = None  # xml对象的根对象
        self.encoding = encoding
        # 注册命名空间
        if register_namespace is not None:
            for _key in register_namespace.keys():
                ET.register_namespace(_key, register_namespace[_key])

        # 统一采取字符方式获取
        _xml_bytes = None  # 要处理的字节对象
        if obj_type == EnumXmlObjType.File:
            self.file = xml_obj
            with open(self.file, 'rb') as f:
                _xml_bytes = f.read()
        elif obj_type == EnumXmlObjType.FileHandle:
            _xml_bytes = xml_obj.read()
        elif obj_type == EnumXmlObjType.Bytes:
            _xml_bytes = xml_obj
        else:
            if self.encoding is None:
                self.encoding = 'utf-8'
            _xml_bytes = xml_obj.encode(encoding=self.encoding)

        # 判断字符集
        if self.encoding is None:
            if use_chardet:
                self.encoding = chardet.detect(_xml_bytes)['encoding']
                if self.encoding.startswith('ISO-8859'):
                    self.encoding = 'gbk'
            else:
                self.encoding = 'utf-8'

        # 生成root
        _parser = ET.XMLParser(
            encoding=self.encoding,
            attribute_defaults=False if 'attribute_defaults' not in kwargs.keys(
            ) else kwargs['attribute_defaults'],
            dtd_validation=False if 'dtd_validation' not in kwargs.keys(
            ) else kwargs['dtd_validation'],
            load_dtd=False if 'dtd_validation' not in kwargs.keys() else kwargs['dtd_validation'],
            no_network=True if 'no_network' not in kwargs.keys() else kwargs['no_network'],
            ns_clean=False if 'ns_clean' not in kwargs.keys() else kwargs['ns_clean'],
            recover=False if 'recover' not in kwargs.keys() else kwargs['recover'],
            schema=None if 'schema' not in kwargs.keys() else kwargs['schema'],
            huge_tree=False if 'huge_tree' not in kwargs.keys() else kwargs['huge_tree'],
            remove_blank_text=False if 'remove_blank_text' not in kwargs.keys(
            ) else kwargs['remove_blank_text'],
            resolve_entities=True if 'resolve_entities' not in kwargs.keys(
            ) else kwargs['resolve_entities'],
            remove_comments=False if 'remove_comments' not in kwargs.keys(
            ) else kwargs['remove_comments'],
            remove_pis=False if 'remove_pis' not in kwargs.keys() else kwargs['remove_pis'],
            strip_cdata=True if 'strip_cdata' not in kwargs.keys() else kwargs['strip_cdata'],
            collect_ids=True if 'collect_ids' not in kwargs.keys() else kwargs['collect_ids'],
            target=None if 'target' not in kwargs.keys() else kwargs['target'],
            compact=True if 'compact' not in kwargs.keys() else kwargs['compact']
        )
        self.root = ET.fromstring(_xml_bytes, parser=_parser)
        self.tree = ET.ElementTree(self.root)

    def __str__(self):
        """
        调用str时打印的值
        """
        return self.to_string(xml_declaration=None)

    def _xml_node_to_dict_value(self, node, item_dict_nodes=None):
        """
        将指定节点通过递归生成存入dict的key-value值

        @param {Element} node - 要生成key-value的节点
        @param {list} item_dict_nodes = None - 指定list和tuple情况下，使用字典作为列表项的节点清单(Element)

        @return {tuple} - 返回 key, value 值，如果是注释返回 None, None
        """
        if not (hasattr(node, 'tag') and type(node.tag) == str):
            # 不是节点的情况（例如注释），直接返回None
            return None, None

        _key = node.tag
        _value = None
        _type = None

        # 处理数据类型的判断
        if 'type' in node.attrib.keys():
            _type = node.attrib['type']
            if _type not in ('dict', 'list', 'tuple', 'bool', 'int', 'float', 'string'):
                # 非标准类型，当作没有传入，重新再处理
                _type = None

        _childs = None  # 子节点清单
        if _type is None:
            _childs = node.getchildren()
            if len(_childs) > 0:
                # 只要子节点有重复的tag，则认为一定是list
                _tag_list = list()
                _type = 'dict'
                for _childnode in _childs:
                    if not (hasattr(_childnode, 'tag') and type(_childnode.tag) == str):
                        # 注释
                        continue

                    if _childnode.tag in _tag_list:
                        # 发现有tag重复的节点
                        _type = 'list'
                        break
                    else:
                        _tag_list.append(_childnode.tag)
            else:
                _type = 'string'

        # 按不同type属性类型进行处理
        if _type == 'string':
            _value = node.text
        elif _type == 'bool':
            _value = (node.text == 'true')
        elif _type == 'int':
            _value = round(float(node.text))
        elif _type == 'float':
            _value = float(node.text)
        elif _type == 'dict':
            # 字典
            if _childs is None:
                _childs = node.getchildren()
            if len(_childs) > 0:
                # 有子节点
                _value = dict()
                for childnode in node.getchildren():
                    _child_key, _child_value = self._xml_node_to_dict_value(
                        childnode, item_dict_nodes=item_dict_nodes)
                    # 加到字典里面
                    if _child_key is not None:
                        _value[_child_key] = _child_value
            else:
                # 没有子节点，等同于string
                _value = node.text
        else:
            # list或tuple
            if _type == 'tuple':
                _value = tuple()
            else:
                _value = list()
            # 判断是否使用字典方式放在列表中
            _use_dict = False
            if item_dict_nodes is not None:
                for _node in item_dict_nodes:
                    if _node is node:
                        _use_dict = True
                        break
            # 列表处理
            for childnode in node.getchildren():
                _child_key, _child_value = self._xml_node_to_dict_value(
                    childnode, item_dict_nodes=item_dict_nodes)
                if _use_dict:
                    # 列表项按字典处理
                    _child_value = {_child_key: _child_value}
                # 加入列表中
                _value.append(_child_value)

        # 返回自身的key值和Value值
        if _value is None:
            _value = ''
        return _key, _value

    #############################
    # 文件操作
    #############################

    def save(self, file=None, encoding=None, **kwargs):
        """
        保存文件

        @param {string|object} file=None - 要保存的文件的完整路径，如果不传代表修改原文件
            注：也可以传入打开的文件句柄
        @param {string} encoding=None - 文件编码，如果为None代表使用创建时的编码
        @param {**kwargs} kwargs - 扩展的装载参数，包括ElementTree.write的参数:
            method="xml" - 方法，可传入"xml", "html" or "text"
            pretty_print=False - 是否针对打印格式美化
            xml_declaration=None - 控制是否在文件中添加xml的声明，True - 一直添加, False - 不添加
                如果传None，代表只有encoding不是US-ASCII or UTF-8 or Unicode的时候才添加声明
            with_tail=True -
            standalone=None -
            doctype=None -
            compression=0 -
            exclusive=False -
            inclusive_ns_prefixes=None -
            with_comments=True -
            strip_text=False -
        """
        _file = file
        if file is None:
            _file = self.file
        _encoding = encoding
        if encoding is None:
            _encoding = self.encoding

        self.tree.write(
            _file,
            encoding=_encoding,
            method="xml" if 'method' not in kwargs.keys() else kwargs['method'],
            pretty_print=False if 'pretty_print' not in kwargs.keys() else kwargs['pretty_print'],
            xml_declaration=None if 'xml_declaration' not in kwargs.keys(
            ) else kwargs['xml_declaration'],
            with_tail=True if 'with_tail' not in kwargs.keys() else kwargs['with_tail'],
            standalone=None if 'standalone' not in kwargs.keys() else kwargs['standalone'],
            doctype=None if 'doctype' not in kwargs.keys() else kwargs['doctype'],
            compression=0 if 'compression' not in kwargs.keys() else kwargs['compression'],
            exclusive=False if 'exclusive' not in kwargs.keys() else kwargs['exclusive'],
            inclusive_ns_prefixes=None if 'inclusive_ns_prefixes' not in kwargs.keys(
            ) else kwargs['inclusive_ns_prefixes'],
            with_comments=True if 'with_comments' not in kwargs.keys() else kwargs['with_comments'],
            strip_text=False if 'strip_text' not in kwargs.keys() else kwargs['strip_text']
        )

    def to_string(self, xpath=None, namespaces=None, **kwargs):
        """
        输出xml节点为字符串

        @param {string} xpath=None - 符合XPath语法的搜索路径，空代表根节点
        @param {dict} namespaces=None - 命名空间
        @param {**kwargs} kwargs - 扩展的参数，包括etree.tostring的参数:
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

        @return {string} - 输出的字符串
        """
        _node = None
        if xpath is None:
            _node = self.root
        else:
            _nodes = self.root.xpath(xpath, namespaces=namespaces)
            if len(_nodes) > 0:
                _node = _nodes[0]

        return ET.tostring(
            _node, encoding=self.encoding,
            method="xml" if 'method' not in kwargs.keys() else kwargs['method'],
            xml_declaration=None if 'xml_declaration' not in kwargs.keys(
            ) else kwargs['xml_declaration'],
            pretty_print=True if 'pretty_print' not in kwargs.keys() else kwargs['pretty_print'],
            with_tail=True if 'with_tail' not in kwargs.keys() else kwargs['with_tail'],
            standalone=None if 'standalone' not in kwargs.keys() else kwargs['standalone'],
            doctype=None if 'doctype' not in kwargs.keys() else kwargs['doctype'],
            exclusive=False if 'exclusive' not in kwargs.keys() else kwargs['exclusive'],
            inclusive_ns_prefixes=None if 'inclusive_ns_prefixes' not in kwargs.keys(
            ) else kwargs['inclusive_ns_prefixes'],
            with_comments=True if 'with_comments' not in kwargs.keys() else kwargs['with_comments'],
            strip_text=False if 'strip_text' not in kwargs.keys() else kwargs['strip_text']
        ).decode(encoding=self.encoding)

    def to_dict(self, xpath=None, namespaces=None, **kwargs):
        """
        输出xml节点为字典(dict)
        注：该函数不支持处理xml中的属性值

        @param {string} xpath=None - 符合XPath语法的搜索路径，空代表根节点
        @param {dict} namespaces=None - 命名空间
        @param {**kwargs} kwargs - 扩展的参数，包括:
            item_dict_xpaths = None - {dict} - 指定list和tuple情况下，使用字典作为列表项的节点xPath路径
                key - 节点对应的xPath，value - 搜索命名空间，值为None或dict
                注：xPath为列表节点的路径（非列表项节点路径）; xPath的路径从根节点开始查找

        @return {dict} - 转换后的字典对象
            注：包含节点自身，例如<data><a>val1</a><b>val2</b></data>转换后的字典应该通过dict['data']开始访问
        """
        # 生成item_dict_nodes参数
        _item_dict_nodes = None
        if 'item_dict_xpaths' in kwargs.keys() and kwargs['item_dict_xpaths'] is not None:
            _item_dict_nodes = list()
            for _get_xpath in kwargs['item_dict_xpaths'].keys():
                _get_nodes = self.root.xpath(_get_xpath,
                                             namespaces=kwargs['item_dict_xpaths'][_get_xpath])
                # 合并列表
                _item_dict_nodes = _item_dict_nodes + _get_nodes

        # 获取要处理的节点列表
        _roots = [self.root]
        if xpath is not None:
            # 获取全部匹配节点
            _roots = self.root.xpath(xpath, namespaces=namespaces)

        # 生成字典
        _dict = dict()
        for _root in _roots:
            if _root is not None:
                _key, _value = self._xml_node_to_dict_value(_root, item_dict_nodes=_item_dict_nodes)
                if _key is not None:
                    _dict[_key] = _value
        # 返回结果
        return _dict

    #############################
    # 节点操作
    #############################

    def get_nodes(self, xpath, namespaces=None):
        """
        获取xpath指定的节点清单

        @param {string} xpath - 符合XPath语法的搜索路径
        @param {dict} namespaces=None - 命名空间

        @return {list} - 返回节点清单
        """
        return self.root.xpath(xpath, namespaces=namespaces)

    def get_xpath(self, node):
        """
        获取指定节点的xpath路径

        @param {Element} node - 要获取搜索路径的节点

        @return {string} - 可搜索到该节点的xpath
        """
        return self.tree.getpath(node)

    def append_path_node(self, path, namespaces=None):
        """
        按path生成对应路径的节点

        @param {string} path - 要生成节点的搜索路径，不支持非节点tag的属性及通配符的匹配
            标准格式如下：tag/tag/tag
        @param {dict} namespaces=None - 命名空间
            可传入值的示例如下：
                ns = {
                    'real_person': 'http://people.example.com',
                    'role': 'http://characters.example.com'
                }
        @return {Element} - 返回创建完成的节点

        @throws {AttributeError} - 当搜索路径不符合创建规范时，抛出该异常
        """
        # 检查是否有不符合的情况
        _replace_reg = re.compile(r'{[\S\s]+?}')
        _check_str = _replace_reg.sub('X', path)
        if re.search('^/|/$|//|\\*|\\.|\\[*\\]', _check_str, flags=re.M) is not None:
            # 不符合搜索路径的条件，抛出异常
            raise AttributeError('path must just with tag')

        # 获取每个节点
        _node_reg = re.compile(r'(({[\S\s]+?}){0,}[^/]+)')
        _tag_list = _node_reg.findall(path)
        # 从第一级开始找以及新增
        _node = self.root
        for _tag in _tag_list:
            _new_node = _node.find(_tag[0], namespaces=namespaces)
            if _new_node is None:
                # 没有节点，新增
                _new_node = None
                if ':' in _tag[0]:
                    # 有命名空间的处理
                    _prefix, _tag = _tag[0].split(':', 1)
                    _tag = '{' + namespaces[_prefix] + '}' + _tag
                    _new_node = ET.Element(_tag, nsmap=namespaces)
                else:
                    _new_node = ET.Element(_tag[0])
                _node.append(_new_node)
            # 当前节点设置为新增的节点
            _node = _new_node

        # 返回新增的节点
        return _node

    def append_node(self, xpath, node, namespaces=None):
        """
        添加节点到指定路径(匹配的第一个)

        @param {string} xpath - 符合XPath语法的搜索路径
        @param {dict} namespaces=None - 命名空间
        @param {Element} node - 要添加的节点

        @return {Element} - 返回匹配到的节点
        """
        _nodes = self.root.xpath(xpath, namespaces=namespaces)
        if len(_nodes) > 0:
            return _nodes[0].append(node)
        else:
            raise NameError('can\'t find node by xpath')

    def remove_node(self, node, hold_tail=False):
        """
        删除指定节点

        @param {Element} node - 要删除的节点
        @param {bool} hold_tail=False - 是否保留上一节点的tail信息
        """
        _parent = node.getparent()
        if _parent is not None:
            if hold_tail and node.tail is not None:
                # 保存上一节点tail信息
                _tail = node.tail
                _previous = node.getprevious()
                if _previous is not None:
                    _previous.tail = (_previous.tail or '') + _tail
                else:
                    _parent.text = (_parent.text or '') + _tail
                _parent.remove(node)
            else:
                # 直接删除
                _parent.remove(node)

    def remove(self, xpath, namespaces=None, hold_tail=False):
        """
        根据xpath删除节点

        @param {string} xpath - 符合XPath语法的搜索路径

        @param {dict} namespaces=None - 命名空间
        @param {bool} hold_tail=False - 是否保留上一节点的tail信息
        """
        _nodes = self.root.xpath(xpath, namespaces=namespaces)
        for _node in _nodes:
            self.remove_node(_node, hold_tail=hold_tail)

    #############################
    # 节点值处理
    #############################
    def get_value(self, xpath, default='', namespaces=None):
        """
        获取指定节点的值

        @param {string} xpath - 符合XPath语法的搜索路径
            注：（1）如果指定了命名空间，可以通过命名空间的key进行指定，例如'real_person:actor'
                （2）xPath如果不是从'/'开始，则默认从root节点开始搜索
        @param {string} default='' - 如果找不到节点时默认返回的值
        @param {dict} namespaces=None - 命名空间
            可传入值的示例如下：
                ns = {
                    'real_person': 'http://people.example.com',
                    'role': 'http://characters.example.com'
                }

        @return {string} - 第一个匹配节点的文本值，如果没有找到匹配节点，返回''
        """
        _nodes = self.root.xpath(xpath, namespaces=namespaces)
        if len(_nodes) == 0:
            return default
        else:
            return _nodes[0].text

    def get_attr(self, xpath, attr_name, default='', namespaces=None):
        """
        获取指定节点的属性值

        @param {string} xpath - 符合XPath语法的搜索路径
            注：（1）如果指定了命名空间，可以通过命名空间的key进行指定，例如'real_person:actor'
                （2）xPath如果不是从'/'开始，则默认从root节点开始搜索
        @param {string} attr_name - 属性名
        @param {string} default='' - 如果找不到节点或具体属性时默认返回的值
        @param {dict} namespaces=None - 命名空间
            可传入值的示例如下：
                ns = {
                    'real_person': 'http://people.example.com',
                    'role': 'http://characters.example.com'
                }

        @return {string} - 第一个匹配节点的指定属性文本值，如果没有找到匹配节点或属性，返回''
        """
        _nodes = self.root.xpath(xpath, namespaces=namespaces)
        if len(_nodes) == 0:
            return default
        else:
            # 返回属性值
            return _nodes[0].get(attr_name, default=default)

    def set_value(self, xpath, value, namespaces=None, auto_create=True):
        """
        设置指定节点的值

        @param {string} xpath - 符合XPath语法的搜索路径
            注：（1）如果指定了命名空间，可以通过命名空间的key进行指定，例如'real_person:actor'
                （2）xPath如果不是从'/'开始，则默认从root节点开始搜索
        @param {string} value - 要设置的值
        @param {dict} namespaces=None - 命名空间
            可传入值的示例如下：
                ns = {
                    'real_person': 'http://people.example.com',
                    'role': 'http://characters.example.com'
                }
        @param {bool} auto_create=True - 节点不存在的时候是否自动创建节点

        @throw {NameError} - 当节点不存在时抛出该异常
        @throws {AttributeError} - 当搜索路径不符合自动创建规范时，抛出该异常
        """
        _nodes = self.root.xpath(xpath, namespaces=namespaces)
        if len(_nodes) == 0:
            if auto_create:
                # 找不到节点，尝试自动创建节点
                _node = self.append_path_node(xpath, namespaces=namespaces)
                _node.text = value
            else:
                # 不创建节点，抛出异常
                raise NameError('can\'t find node by xpath')
        else:
            for _node in _nodes:
                # 设置节点值
                _node.text = value

    def set_attr(self, xpath, attr_name, value, namespaces=None, auto_create=True):
        """
        设置指定节点的值（只要节点存在强制新增属性）

        @param {string} xpath - 符合XPath语法的搜索路径
            注：（1）如果指定了命名空间，可以通过命名空间的key进行指定，例如'real_person:actor'
                （2）xPath如果不是从'/'开始，则默认从root节点开始搜索
        @param {string} attr_name - 属性名
        @param {string} value - 要设置的值
        @param {dict} namespaces=None - 命名空间
            可传入值的示例如下：
                ns = {
                    'real_person': 'http://people.example.com',
                    'role': 'http://characters.example.com'
                }
        @param {bool} auto_create=True - 节点不存在的时候是否自动创建

        @throw {NameError} - 当节点不存在时抛出该异常
        @throws {AttributeError} - 当搜索路径不符合自动创建规范时，抛出该异常
        """
        _nodes = self.root.xpath(xpath, namespaces=namespaces)
        if len(_nodes) == 0:
            if auto_create:
                # 找不到节点，尝试自动创建节点
                _nodes = [self.append_path_node(xpath, namespaces=namespaces)]
            else:
                # 不创建节点，抛出异常
                raise NameError('can\'t find node by xpath')
        for _node in _nodes:
            # 设置节点属性值
            _node.set(attr_name, value)

    #############################
    # 特定节点的值处理，静态函数
    #############################
    @staticmethod
    def get_value_on_node(node, xpath, default='', namespaces=None):
        """
        获取指定节点的值(从节点开始检索)

        @param {Element} node - 开始检索的节点
        @param {string} xpath - - 符合XPath语法的搜索路径
        @param {string} default='' - 如果找不到节点时默认返回的值
        @param {dict} namespaces=None - 命名空间

        @return {string} - 第一个匹配节点的文本值，如果没有找到匹配节点，返回''
        """
        _nodes = node.xpath(xpath, namespaces=namespaces)
        if len(_nodes) == 0:
            return default
        else:
            return _nodes[0].text

    @staticmethod
    def get_attr_on_node(node, xpath, attr_name, default='', namespaces=None):
        """
        获取指定节点的属性值(从节点开始检索)

        @param {Element} node - 开始检索的节点
        @param {string} xpath - - 符合XPath语法的搜索路径
        @param {string} attr_name - 属性名
        @param {string} default='' - 如果找不到节点或具体属性时默认返回的值
        @param {dict} namespaces=None - 命名空间

        @return {string} - 第一个匹配节点的指定属性文本值，如果没有找到匹配节点或属性，返回''
        """
        _nodes = node.xpath(xpath, namespaces=namespaces)
        if len(_nodes) == 0:
            return default
        else:
            # 返回属性值
            return _nodes[0].get(attr_name, default=default)


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    # 打印版本信息
    print(('模块名：%s  -  %s\n'
           '作者：%s\n'
           '发布日期：%s\n'
           '版本：%s' % (__MOUDLE__, __DESCRIPT__, __AUTHOR__, __PUBLISH__, __VERSION__)))

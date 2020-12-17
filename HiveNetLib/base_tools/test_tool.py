#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
#
# Copyright 2018 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
测试相关工具

@module test_tool
@file test_tool.py

"""

import sys
import os
import json
import operator
# 根据当前文件路径将包路径纳入，在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir, os.path.pardir)))
from HiveNetLib.base_tools.string_tool import StringTool

__MOUDLE__ = 'test_tool'  # 模块名
__DESCRIPT__ = u'测试相关工具'  # 模块描述
__VERSION__ = '0.1.0'  # 版本
__AUTHOR__ = u'黎慧剑'  # 作者
__PUBLISH__ = '2018.08.30'  # 发布日期


class TestTool(object):
    """
    测试相关工具，提供各类检查比较函数

    """

    @staticmethod
    def cmp_list(src_data, dst_data, print_if_diff=True):
        """
        比较两个列表（list）是否一致

        @param {list} src_data - 第1个list对象
        @param {list} dst_data - 第2个list对象
        @param {bool} print_if_diff=True - 当两个list不一致时是否打印对象信息

        @returns {bool} - True-两个list一致，False-两个list不一致

        """
        is_same = True
        try:
            if len(src_data) != len(dst_data):
                is_same = False
            else:
                i = 0
                while i < len(src_data):
                    is_sub_same = True
                    if type(src_data[i]) == list:
                        # 针对有子列表的情况，递归处理
                        is_sub_same = TestTool.cmp_list(
                            src_data[i], dst_data[i], print_if_diff=False)
                        # print('list is_sub_same:'+str(is_sub_same) + str(i))
                    else:
                        is_sub_same = (src_data[i] == dst_data[i])
                        # print('obj is_sub_same:'+str(is_sub_same) + str(i))
                    if not is_sub_same:
                        is_same = False
                        break
                    i = i + 1

        except Exception:
            is_same = False

        if not is_same and print_if_diff:
            print('src_data :' + str(src_data))
            print('dst_data :' + str(dst_data))
        return is_same

    @staticmethod
    def cmp_dict(src_data, dst_data, print_if_diff=True):
        """
        比较两个字典是否一致

        @param {string/dict} src_data - 第1个字典对象（或对象JSON字符串）
        @param {string/dict} dst_data - 第2个字典对象（或对象JSON字符串）
        @param {bool} print_if_diff=True - 当两个字典不一致时是否打印对象信息

        @returns {bool} - True-两个字典一致，False-两个字典不一致

        """
        is_same = False
        if isinstance(src_data, str):
            src_data = json.dumps(src_data)
        if isinstance(dst_data, str):
            dst_data = json.dumps(dst_data)
        if len(src_data) != len(dst_data):
            if print_if_diff:
                print('cmp_dict: len difference!')
        else:
            src_key = list(src_data.keys())
            src_key.sort()
            dst_key = list(dst_data.keys())
            dst_key.sort()
            if operator.eq(src_key, dst_key):
                is_break = False
                for key in src_data.keys():
                    if src_data[key] != dst_data[key]:
                        # print(src_data1[key])
                        print('cmp_dict: value difference in key "%s"!' % (key))
                        is_break = True
                        break
                if not is_break:
                    # 如果没有中断过，则代表比较成功
                    return True
            else:
                print('cmp_dict: key list difference!')
        if print_if_diff:
            print('src_data :' + StringTool.format_obj_property_str(src_data,
                                                                    is_deal_subobj=True, c_level=2))
            print('dst_data :' + StringTool.format_obj_property_str(dst_data,
                                                                    is_deal_subobj=True, c_level=2))
        return is_same

    @staticmethod
    def is_contain_dict(src_data, dst_data):
        """
        检查字典1是否包含在字典2中(字典1为字典2的子集)

        @param {string/dict} src_data - 第1个字典对象（或对象JSON字符串）
        @param {string/dict} dst_data - 第2个字典对象（或对象JSON字符串）

        @returns {bool} - True-字典1包含在字典2中，False-字典1未包含在字典2中

        """
        if isinstance(src_data, str):
            src_data = json.dumps(src_data)
        if isinstance(dst_data, str):
            dst_data = json.dumps(dst_data)
        else:
            src_key = list(src_data.keys())
            dst_key = list(dst_data.keys())
            # print(str(src_key))
            # print(str(dst_key))
            pd = [False for c in src_key if c not in dst_key]
            if pd:
                return False
            else:
                src_val = list(src_data.values())
                dst_val = list(dst_data.values())
                pds = [False for c in src_val if c not in dst_val]
                if pds:
                    return False
                else:
                    return True


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    # 打印版本信息
    print(('模块名：%s  -  %s\n'
           '作者：%s\n'
           '发布日期：%s\n'
           '版本：%s' % (__MOUDLE__, __DESCRIPT__, __AUTHOR__, __PUBLISH__, __VERSION__)))

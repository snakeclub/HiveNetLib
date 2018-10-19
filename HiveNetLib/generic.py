#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
#
# Copyright 2018 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
通用基础模块

@module generic
@file generic.py

"""


import sys
import os
import json
import copy
sys.path.append(os.path.abspath(os.path.dirname(__file__)+'/'+'..'))
from HiveNetLib.simple_i18n import get_global_i18n
from HiveNetLib.base_tools.run_tool import RunTool
from HiveNetLib.base_tools.string_tool import StringTool


__MOUDLE__ = 'generic'  # 模块名
__DESCRIPT__ = '通用基础模块'  # 模块描述
__VERSION__ = '0.1.0'  # 版本
__AUTHOR__ = '黎慧剑'  # 作者
__PUBLISH__ = '2018.08.29'  # 发布日期


class NullObj(object):
    """
    空对象定义类，用于动态增加属性的使用场景

    @example
        msg_obj = NullObj()
        msg_obj.text = u'动态添加属性'

    """
    pass


class CResult(object):
    """
    通用错误类定义，便于规范所有的错误信息返回判断标准，可直接在该类的实例对象上直接添加其他返回值

    @example
        def fun():
            result = CResult('00000',u'success')
            result.job = 'NewJob'
            result.k1 = 10
            return result

    """

    #############################
    # 内部变量
    #############################

    _i18n_obj = None  # 国际化类实例化对象
    i18n_msg_id = ''  # 国际化记录下来的错误码ID串
    i18n_msg_paras = ()  # 国际化记录下来的可替换参数变量

    def __init__(self, code='00000', msg=None, error=None, trace_str='',
                 i18n_obj=None, i18n_msg_paras=()):
        """
        构造函数

        @param {string} code='00000' - 错误码，'00000'代表成功，参照FiveNet的错误码规范
        @param {string} msg=None - 错误信息描述，如果i18n_obj不为None时，该参数传入的是国际化的消息ID
            注意：如果初始化时不传入msg（即msg=None时），自动通过code查找具体的错误信息，且在i18n_obj为None时使用全局国际化对象处理国际化信息
        @param {tuple}} error=None - 发生异常时的sys.exc_info()三元组对象(type, value, traceback):
            type-从获取到的异常中得到类型名称，它是BaseException 的子类
            value-捕获到的异常实例
            traceback-异常跟踪对象，可以用traceback.print_tb()打印具体信息
        @param {string} trace_str='' - 错误追踪堆栈日志，异常时的traceback.format_exc()
        @param {object} i18n_obj=None - 国际化类的实例对象，该对象需实现translate方法
        @param {tuple} i18n_msg_paras=() - 与msg配套使用，当使用国际化时，可以传入变量，用于替换msg中的$1占位符

        """
        self.code = code
        self.msg = msg
        self._i18n_obj = i18n_obj
        if msg is None:
            if i18n_obj is None:
                # 使用全局国际化控件
                self._i18n_obj = get_global_i18n()
            # 尝试先装载错误码映射
            _map_error_code = self.__get_map_error_code()
            # 获取代码表
            if code in _map_error_code.keys():
                self.msg = _map_error_code[code]
            else:
                self.msg = ''

        self.error = error
        self.trace_str = trace_str
        if i18n_obj is not None:
            # 需要国际化处理
            self._i18n_obj = i18n_obj
            self.i18n_msg_id = msg
            self.i18n_msg_paras = i18n_msg_paras
            # 处理国际化
            self.msg = self._i18n_obj.translate(self.i18n_msg_id, self.i18n_msg_paras)

    def is_success(self):
        """
        判断当前错误对象是否成功

        """
        return (self.code[0] == '0')

    def change_code(self, code='00000', msg=None):
        """
        改变错误码及错误信息

        @param {string} code='00000' - 错误码
        @param {string} msg=None - 错误信息描述，如果i18n_obj不为None时，该参数传入的是国际化的消息ID
            注意：如果初始化时不传入msg（即msg=None时），自动通过code查找具体的错误信息，且在i18n_obj为None时使用全局国际化对象处理国际化信息

        """
        self.code = code
        self.msg = msg
        if msg is None:
            # 尝试先装载错误码映射
            _map_error_code = self.__get_map_error_code()

            # 获取代码表
            if code in _map_error_code.keys():
                self.msg = _map_error_code[code]
            else:
                self.msg = ''
        # 国际化处理
        self.set_i18n_msg(msg=self.msg)

    def copy_to(self, dest_obj):
        """
        复制结果对象的标准返回值到新对象中
        简单数据类型（int、string）只要共享地址即可，因为对变量重新复制会指向新的地址，
        不会影响原来的变量值；复杂数据类型（dict等）要通过deepcopy方式拷贝，避免同一内存信息改变互相影响

        @param {object} dest_obj - 要复制到的CResult对象

        """
        dest_obj.code = self.code
        dest_obj.msg = self.msg
        dest_obj.error = copy.deepcopy(self.error)
        dest_obj.trace_str = self.trace_str
        dest_obj.i18n_msg_id = self.i18n_msg_id
        dest_obj.i18n_msg_paras = self.i18n_msg_paras

    def set_i18n_msg(self, msg, i18n_msg_paras=()):
        """
        修改错误信息（支持国际化）

        @param {string} msg - 错误信息描述，如果i18n_obj不为None时，该参数传入的是国际化的消息ID
        @param {tuple} i18n_msg_paras=() - 与msg配套使用，当使用国际化时，可以传入变量，用于替换msg中的$1占位符

        """
        if self._i18n_obj is None:
            self.msg = msg
        else:
            self.i18n_msg_id = msg
            self.i18n_msg_paras = i18n_msg_paras
            self.msg = self._i18n_obj.translate(self.i18n_msg_id, self.i18n_msg_paras)

    def __get_map_error_code(self):
        """
        获取全局的错误码映射表

        """
        _map_error_code = RunTool.get_global_var('HIVENET_ERROR_CODE_MAP')
        if _map_error_code is None:
            _map_file = os.path.realpath(os.path.abspath(os.path.dirname(__file__)+'/') +
                                         '/hivenet_error_code/map_error_code.json')
            _map_error_code = {}
            with open(_map_file, 'rt', encoding='utf-8') as f:
                _map_error_code = json.load(f)
            RunTool.set_global_var('HIVENET_ERROR_CODE_MAP', _map_error_code)
        return _map_error_code

    def __str__(self):
        """
        提供系统层级的str输出格式化字符

        """
        _str = '%s:\n' % (str(type(self)))
        # 其他属性
        _attr_dir = dir(self)
        for _item in _attr_dir:
            if _item[0: 2] != '__' and not callable(getattr(self, _item)) and _item not in ['_i18n_obj', 'i18n_msg_paras', 'i18n_msg_id', 'error']:
                _str += '  (attr).%s=%s\n' % (_item, str(getattr(self, _item)))
        # __dict__上的属性
        if hasattr(self, '__dict__'):
            for _item in self.__dict__.items():
                if _item[0] not in _attr_dir and _item[0] not in ['_i18n_obj', 'i18n_msg_paras', 'i18n_msg_id', 'error']:
                    _str += '  (dict).%s=%s\n' % (_item[0], str(_item[1]))

        return _str


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    # 打印版本信息
    print(('模块名：%s  -  %s\n'
           '作者：%s\n'
           '发布日期：%s\n'
           '版本：%s' % (__MOUDLE__, __DESCRIPT__, __AUTHOR__, __PUBLISH__, __VERSION__)))

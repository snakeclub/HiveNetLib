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

import copy

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

    def __init__(self, code='00000', msg='success', error=None, trace_str='',
                 i18n_obj=None, i18n_msg_paras=()):
        """
        构造函数

        @param {string} code='00000' - 错误码，'00000'代表成功，参照FiveNet的错误码规范
        @param {string} msg='success' - 错误信息描述，如果i18n_obj不为None时，该参数传入的是国际化的消息ID
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
        self.error = error
        self.trace_str = trace_str
        if i18n_obj is not None:
            # 需要国际化处理
            self._i18n_obj = i18n_obj
            self.i18n_msg_id = msg
            self.i18n_msg_paras = i18n_msg_paras
            # 处理国际化
            self.msg = self._i18n_obj.translate(self.i18n_msg_id, self.i18n_msg_paras)

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


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    # 打印版本信息
    print(('模块名：%s  -  %s\n'
           '作者：%s\n'
           '发布日期：%s\n'
           '版本：%s' % (__MOUDLE__, __DESCRIPT__, __AUTHOR__, __PUBLISH__, __VERSION__)))

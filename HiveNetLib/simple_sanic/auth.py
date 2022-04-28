#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
# Copyright 2019 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
sanic api 鉴权模块

@module auth
@file auth.py
"""

import os
import sys
import copy
import re
from functools import wraps
# 根据当前文件路径将包路径纳入，在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir, os.path.pardir)))
# 动态安装包
import HiveNetLib.deps_tool as deps_tool
process_install_sanic = False
while True:
    try:
        from sanic.response import json
        from sanic.request import Request
        break
    except ImportError:
        if not process_install_sanic:
            deps_tool.install_package('sanic')
            process_install_sanic = True
            continue
        raise


__MOUDLE__ = 'auth'  # 模块名
__DESCRIPT__ = u'sanic api 鉴权模块'  # 模块描述
__VERSION__ = '0.1.0'  # 版本
__AUTHOR__ = u'黎慧剑'  # 作者
__PUBLISH__ = '2020.12.03'  # 发布日期


class IPAuth(object):
    """
    IP黑白名单模式验证模块
    """

    #############################
    # 构造函数
    #############################
    def __init__(self, **kwargs):
        """
        IP黑白名单模式验证模块

        @param {list} init_blacklist=None - 初始化的黑名单
            名单可以使用通配符禁止某个网段, 例如 ['127.0.*.*', '138.*.*.*']
        @param {list} init_whitelist=None - 初始化的白名单
        @param {int} error_resp_status=403 - 验证失败返回状态码
        @param {str|dict} error_resp_msg={'status': '10409', 'msg':'IP地址验证失败'} - 验证失败返回的信息
        @param {str} interface_id_name='' - 接口id的参数名，如果为''则代表返回错误时不需要返回请求接口id
        """
        self.para = kwargs
        self.interface_id_name = self.para.get('interface_id_name', '')
        self.error_resp_status = self.para.get('error_resp_status', 403)
        self.error_resp_msg = self.para.get(
            'error_resp_msg', {'status': '10409', 'msg': 'IP地址验证失败'}
        )

        # 黑白名单管理
        self.ip_dict = {
            'blacklist': {
                'show': list(),  # 显示配置
                'reg': dict()  # 正则表的配置, key为show中的显示名, value为正则表达式规则
            },
            'whitelist': {
                'show': list(),  # 显示配置
                'reg': dict()  # 正则表的配置, key为show中的显示名, value为正则表达式规则
            }
        }

        # 初始化黑白名单
        if kwargs.get('init_blacklist', None) is not None:
            self.add_blacklist(kwargs['init_blacklist'])

        if kwargs.get('init_whitelist', None) is not None:
            self.add_whitelist(kwargs['init_whitelist'])

    #############################
    # 增加IP验证的修饰符函数
    #############################
    def auth_required(self, f=None):
        """
        需要IP验证的情况下使用的修饰符

        @param {function} f=None - 所执行的函数
        """
        def auth_required_internal(f):
            @wraps(f)
            def decorated(*args, **kwargs):
                # 执行实际处理函数函数
                return self.auth_required_call(f, *args, **kwargs)
            return decorated

        if f:
            return auth_required_internal(f)
        return auth_required_internal

    def auth_required_call(self, f, *args, **kwargs):
        """
        直接执行的验证修饰符函数

        @param {function} f - 要执行的函数
        @param {args} - 执行函数的固定入参
        @param {kwargs} - 执行函数的kv入参

        @returns {tuple(object, int)} - 返回响应信息(返回信息, http响应码)
        """
        # 进行IP地址的黑白名单校验
        _status = 200
        _resp_msg = ''
        _request = args[0]  # 请求对象为第一个入参
        if type(_request) != Request:
            _request = args[1]
        _ip = _request.ip

        # 先检查白名单
        if len(self.ip_dict['whitelist']['show']) > 0:
            if not self.verify_whitelist(_ip):
                # 不在白名单内
                _status = self.error_resp_status
                _resp_msg = copy.deepcopy(self.error_resp_msg)

        # 再检查黑名单
        if _status == 200 and self.verify_blacklist(_ip):
            # 在黑名单内
            _status = self.error_resp_status
            _resp_msg = copy.deepcopy(self.error_resp_msg)

        if _status != 200:
            # 验证失败
            if type(_resp_msg) == dict:
                if self.interface_id_name != '':
                    # 增加返回的接口id
                    _resp_msg[self.interface_id_name] = _request.json[self.interface_id_name]

            # 标准反馈
            _ret = json(_resp_msg, status=_status)
        else:
            # 验证通过，执行函数
            _ret = f(*args, **kwargs)

        # 返回处理结果
        return _ret

    #############################
    # 黑白名单检查工具
    #############################

    def verify_blacklist(self, ip: str) -> bool:
        """
        验证是否匹配黑名单

        @param {str} ip - 要验证的ip

        @returns {bool} - 检查结果，匹配到返回True
        """
        return self._verify_ip('blacklist', ip)

    def verify_whitelist(self, ip: str) -> bool:
        """
        验证是否匹配白名单

        @param {str} ip - 要验证的ip

        @returns {bool} - 检查结果，匹配到返回True
        """
        return self._verify_ip('whitelist', ip)

    #############################
    # 黑白名单维护工具
    #############################

    def add_blacklist(self, ips):
        """
        添加黑名单

        @param {str|list} ips - 要添加的ip或ip列表
        """
        if type(ips) == str:
            # 单个黑名单
            self._add_list('blacklist', ips)
        else:
            # 多个黑名单
            for _ip in ips:
                self._add_list('blacklist', _ip)

    def remove_blacklist(self, ips):
        """
        删除黑名单

        @param {str|list} ips - 要删除的ip或ip列表
        """
        if type(ips) == str:
            # 单个黑名单
            self._remove_list('blacklist', ips)
        else:
            # 多个黑名单
            for _ip in ips:
                self._remove_list('blacklist', _ip)

    def clear_blacklist(self):
        """
        清除黑名单
        """
        self.ip_dict['blacklist'].clear()
        self.ip_dict['blacklist']['show'] = list()
        self.ip_dict['blacklist']['reg'] = dict()

    def add_whitelist(self, ips):
        """
        添加白名单

        @param {str|list} ips - 要添加的ip或ip列表
        """
        if type(ips) == str:
            # 单个黑名单
            self._add_list('whitelist', ips)
        else:
            # 多个黑名单
            for _ip in ips:
                self._add_list('whitelist', _ip)

    def remove_whitelist(self, ips):
        """
        删除白名单

        @param {str|list} ips - 要删除的ip或ip列表
        """
        if type(ips) == str:
            # 单个黑名单
            self._remove_list('whitelist', ips)
        else:
            # 多个黑名单
            for _ip in ips:
                self._remove_list('whitelist', _ip)

    def clear_whitelist(self):
        """
        清除白名单
        """
        self.ip_dict['whitelist'].clear()
        self.ip_dict['whitelist']['show'] = list()
        self.ip_dict['whitelist']['reg'] = dict()

    #############################
    # 内部函数
    #############################

    def _add_list(self, ip_type: str, ip: str):
        """
        插入名单数据

        @param {str} ip_type - 'blacklist' 或 'whitelist'
        @param {str} ip - 要插入的ip地址
        """
        _dict = self.ip_dict[ip_type]
        if ip in _dict['show']:
            # 名单已存在
            return

        # 加入显示名单
        _dict['show'].append(ip)

        # 生成名单的匹配正则表达式
        if ip.find('*') >= 0:
            # 需要生成正则表达式
            _re = re.compile('^' + ip.replace('.', '\\.').replace('*', '.*') + '$')
            _dict['reg'][ip] = _re

    def _remove_list(self, ip_type: str, ip: str):
        """
        删除名单数据

        @param {str} ip_type - 'blacklist' 或 'whitelist'
        @param {str} ip - 要删除的ip地址
        """
        _dict = self.ip_dict[ip_type]
        if ip in _dict['show']:
            # 删除正则表达式
            _dict['reg'].pop(ip, None)

            # 删除显示ip
            _dict['show'].remove(ip)

    def _verify_ip(self, ip_type: str, ip: str) -> bool:
        """
        检查ip是否匹配名单

        @param {str} ip_type - 'blacklist' 或 'whitelist'
        @param {str} ip - 要检查的ip地址

        @returns {bool} - 检查结果，匹配到返回True
        """
        _dict = self.ip_dict[ip_type]
        if ip in _dict['show']:
            return True

        # 遍历正则规则
        for _re in _dict['reg'].values():
            if _re.search(ip) is not None:
                return True

        # 没有匹配上
        return False


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    # 打印版本信息
    print(('模块名：%s  -  %s\n'
           '作者：%s\n'
           '发布日期：%s\n'
           '版本：%s' % (__MOUDLE__, __DESCRIPT__, __AUTHOR__, __PUBLISH__, __VERSION__)))

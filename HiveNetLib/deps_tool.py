#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
# Copyright 2019 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
依赖包安装工具包
@module deps_tool
@file deps_tool.py
"""

import sys
import subprocess


__MOUDLE__ = 'deps_tool'  # 模块名
__DESCRIPT__ = u'依赖包安装工具包'  # 模块描述
__VERSION__ = '0.1.0'  # 版本
__AUTHOR__ = u'黎慧剑'  # 作者
__PUBLISH__ = '2020.11.30'  # 发布日期


# 依赖字典, key为包名, value为安装的包及版本要求
DEPENDENCIES_DICT = {
    'gevent': {
        'install': 'gevent',
    },
    'eventlet': {
        'install': 'eventlet',
    },
    'prompt-toolkit': {
        'install': 'prompt-toolkit>=2.0.0',
    },
    'dicttoxml': {
        'install': 'dicttoxml>=1.7.4',
    },
    'grpcio': {
        'install': 'grpcio>=1.21.1',
    },
    'grpcio-health': {
        'install': 'grpcio-health-checking>=1.21.1',
    },
    'lxml': {
        'install': 'lxml',
    },
    'elementpath': {
        'install': 'elementpath',
    },
    'googleapis-common-protos': {
        'install': 'googleapis-common-protos',
    },
    'jsonpath-rw': {
        'install': 'jsonpath-rw',
    },
    'netifaces': {
        'install': 'netifaces>=0.10.9',
    },
    'chardet': {
        'install': 'chardet',
    },
    'selenium': {
        'install': 'selenium',
    },
    'flask-cors': {
        'install': 'flask-cors',
    },
    'flask': {
        'install': 'flask',
    },
    'flask-restful': {
        'install': 'flask-restful'
    },
    'flask-httpauth': {
        'install': 'flask-httpauth'
    },
    'flask-socketio': {
        'install': 'flask-socketio'
    },
    'werkzeug': {
        'install': 'werkzeug'
    },
    'pycryptodome': {
        'install': 'pycryptodome' if sys.platform != 'win32' else 'pycryptodomex'
    },
    'pywin32': {
        'install': 'pywin32'
    }
}


def install_package(package_name: str, force_reinstall: bool = False, dependencies_dict: dict = None) -> tuple:
    """
    安装指定依赖包

    @param {str} package_name - 要安装的包名(DEPENDENCIES_DICT中的key)
    @param {bool} force_reinstall=False - 是否强制重新安装
    @param {dict} dependencies_dict=None - 依赖字典, key为依赖的包名，value为{'install': '实际安装包名和版本要求'}
        注：如果为None代表使用 DEPENDENCIES_DICT 字典

    @returns {tuple[int, str]} - 安装结果,
        第一位为运行结果，0代表成本，其他代表失败
        第二位为命令安装结果输出内容
    """
    _dependencies_dict = DEPENDENCIES_DICT if dependencies_dict is None else dependencies_dict

    _result = subprocess.getstatusoutput(
        'pip install %s%s' % (
            '--force-reinstall ' if force_reinstall else '',
            _dependencies_dict[package_name]['install']
        )
    )
    if _result[0] == 0:
        # 安装成功
        print('安装依赖包 %s 成功' % package_name)
    else:
        # 安装失败
        print('安装依赖包 %s 失败\n%s\n' % (package_name, _result))

    return _result


def install_all(force_reinstall: bool = False, dependencies_dict: dict = None) -> bool:
    """
    安装所有依赖包

    @param {bool} force_reinstall=False - 是否强制重新安装
    @param {dict} dependencies_dict=None - 依赖字典, key为依赖的包名，value为{'install': '实际安装包名和版本要求'}
        注：如果为None代表使用 DEPENDENCIES_DICT 字典

    @returns {bool} - 最后安装情况
    """
    _dependencies_dict = DEPENDENCIES_DICT if dependencies_dict is None else dependencies_dict

    _fail_list = []
    for _key in _dependencies_dict.keys():
        _result = install_package(_key, force_reinstall=force_reinstall)
        if _result[0] != 0:
            # 安装失败
            _fail_list.append(_key)

    # 打印最后结果
    if len(_fail_list) > 0:
        print('以下依赖包安装失败: %s' % ', '.join(_fail_list))
        return False
    else:
        return True


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    if len(sys.argv) <= 1:
        # 打印版本信息
        print(('模块名：%s  -  %s\n'
               '作者：%s\n'
               '发布日期：%s\n'
               '版本：%s\n'
               '使用方法:\n%s'
               % (
                   __MOUDLE__, __DESCRIPT__, __AUTHOR__, __PUBLISH__, __VERSION__,
                   '\n'.join([
                       '    安装全部依赖包: python deps_tool.py install',
                       '    安装单个依赖包: python deps_tool.py install flask',
                       '    强制重新安装全部依赖包: python deps_tool.py install -f'
                   ])
               )))
    else:
        # 按命令参数执行
        _force_reinstall = False
        if '-f' in sys.argv:
            _force_reinstall = True

        if sys.argv[1] == 'install':
            # 安装依赖包
            if sys.argv[-1] not in ('install', '-f'):
                # 安装单个包
                _package_name = sys.argv[-1]
                install_package(_package_name, force_reinstall=_force_reinstall)
            else:
                # 安装全部
                install_all(force_reinstall=_force_reinstall)

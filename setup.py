#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
#
#  Copyright 2018 黎慧剑
#
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.


"""The setup.py file for Python HiveNetLib."""

import sys
from setuptools import setup, find_packages


LONG_DESCRIPTION = """
HiveNetLib 是一个方便开发人员调用的，集合一些常用开发功能的开发Python库，
包括网络编程（tcpip、http）、日志、命令行交互、公式计算等。

HiveNetLib 的目的是让开发人员用最简单的方法实现最常用的功能，提高开发效率，关注
具体功能逻辑而非具体技术实现。

同时该库为开源项目HiveNet依赖的基础库。
""".strip()

SHORT_DESCRIPTION = """
一个方便开发人员调用的，集合一些常用开发功能的开发Python库.""".strip()

DEPENDENCIES = [
    'gevent',
    'eventlet',
    'prompt-toolkit>=2.0.0',
    'dicttoxml>=1.7.4',
    'grpcio>=1.21.1',
    'grpcio-health-checking>=1.21.1',
    'lxml',
    'elementpath',
    'googleapis-common-protos',
    'jsonpath-rw',
    'netifaces>=0.10.9',
    'chardet',
    'selenium',
    'flask-cors',
    'flask',
    'flask-restful',
    'flask-httpauth',
    'flask-socketio',
    'werkzeug',
    'requests',
    'pycryptodomex'
]

if sys.platform == 'win32':
    DEPENDENCIES.append('pywin32')

# DEPENDENCIES = []

TEST_DEPENDENCIES = []

VERSION = '0.8.9'
URL = 'https://github.com/snakeclub/HiveNetLib'

setup(
    # pypi中的名称，pip或者easy_install安装时使用的名称
    name="HiveNetLib",
    version=VERSION,
    author="黎慧剑",
    author_email="snakeclub@163.com",
    maintainer='黎慧剑',
    maintainer_email='snakeclub@163.com',
    description=SHORT_DESCRIPTION,
    long_description=LONG_DESCRIPTION,
    license="Mozilla Public License 2.0",
    keywords="HiveNet development lib",
    url=URL,
    platforms=["all"],
    # 需要打包的目录列表, 可以指定路径packages=['path1', 'path2', ...]
    packages=find_packages(),
    install_requires=DEPENDENCIES,
    tests_require=TEST_DEPENDENCIES,
    package_data={'': ['*.json', '*.xml', '*.proto']},  # 这里将打包所有的json文件
    classifiers=[
        'Operating System :: OS Independent',
        'License :: OSI Approved :: Mozilla Public License 2.0 (MPL 2.0)',
        'Programming Language :: Python :: 3.6',
        'Topic :: Software Development :: Libraries'
    ],
    # 此项需要，否则卸载时报windows error
    zip_safe=False
)

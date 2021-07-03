#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
#
# Copyright 2018 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
网络处理相关工具

@module net_tool
@file net_tool.py

"""
import os
import sys
import socket
import urllib
import urllib.request
import copy
import requests
from urllib.parse import urlparse
import re
import json
import datetime
import logging
import traceback
from io import BytesIO
from enum import Enum
# 根据当前文件路径将包路径纳入，在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir, os.path.pardir)))
# 动态添加包安装
import HiveNetLib.deps_tool as deps_tool
process_install_selenium = False
while True:
    try:
        from selenium import webdriver
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
        import selenium.webdriver.chrome.options
        import selenium.webdriver.firefox.options
        break
    except ImportError:
        if not process_install_selenium:
            deps_tool.install_package('selenium')
            process_install_selenium = True
            continue
        raise
try:
    import netifaces
except ImportError:
    deps_tool.install_package('netifaces')
    import netifaces
# 引用自有模块
import HiveNetLib.base_tools.wget as wget
from HiveNetLib.base_tools.run_tool import RunTool


__MOUDLE__ = 'net_tool'  # 模块名
__DESCRIPT__ = u'网络处理相关工具'  # 模块描述
__VERSION__ = '0.1.0'  # 版本
__AUTHOR__ = u'黎慧剑'  # 作者
__PUBLISH__ = '2018.08.29'  # 发布日期


class EnumWebDriverType(Enum):
    """
    selenium的WebDriver类型

    @enum {str}
    """
    Chrome = 'Chrome'  # 谷歌浏览器
    Firefox = 'Firefox'  # 火狐浏览器
    Ie = 'Ie'  # IE
    Edge = 'Edge'  # Edge浏览器
    PhantomJS = 'PhantomJS'  # PhantomJS无头无浏览器模式
    Safari = 'Safari'


class NetTool(object):
    """
    网络处理相关工具
    提供网络处理相关的函数，包括字节转换处理等

    """

    #############################
    # 网络字节转换
    #############################
    @staticmethod
    def int_to_bytes(int_value, fix_len=4, byte_order="big", signed=True):
        """
        将整型数据转换为字节数组,与bytes_to_int配套使用

        @param {int} int_value - 要转换的数字
        @param {int} fix_len=4 - 返回数组的长度，如果整数转换出的字节数组长度超过了该长度，则产生OverflowError
        @param {string} byte_order="big" - 字节顺序，值为'big'或者'little':
            big - 表示最有意义的字节放在字节数组的开头
            little - 表示最有意义的字节放在字节数组的结尾
            sys.byteorder - 保存了主机系统的字节序，可以使用这个属性获取本机顺序
        @param {bool} signed=True - 确定是否使用补码来表示整数，如果值为False，并且是负数，则产生OverflowError

        @returns {bytes} - 转换后的字节数组

        @throws {OverflowError} - 如果整数转换出的字节数组长度超过长度或无符号位时传入负数

        """
        return int_value.to_bytes(length=fix_len, byteorder=byte_order, signed=signed)

    @staticmethod
    def bytes_to_int(bytes_value, byte_order="big", signed=True):
        """
        将字节数组转换为整型数字，与int_to_bytes配套使用

        @param {bytes} bytes_value - 要转换的字节数组
        @param {string} byte_order="big" - 字节顺序，值为'big'或者'little':
            big - 表示最有意义的字节放在字节数组的开头
            little - 表示最有意义的字节放在字节数组的结尾
            sys.byteorder - 保存了主机系统的字节序，可以使用这个属性获取本机顺序
        @param {bool} signed=True - 确定是否使用补码来表示整数，如果值为False，并且是负数，则产生OverflowError

        @returns {int} - 转换后的整数

        @throws {OverflowError} - 无符号位时传入负数抛出该异常

        """
        return int.from_bytes(bytes_value, byteorder=byte_order, signed=signed)

    #############################
    # 获取网卡相关信息
    #############################

    @staticmethod
    def get_net_interfaces():
        """
        获取本机网卡清单

        @return {list} - 返回网卡名(NIC NAME)清单
            例如：['lo0', 'gif0', 'stf0', 'en0', 'en1', 'fw0']
        """
        return netifaces.interfaces()

    @staticmethod
    def get_net_interface_info(nic_name):
        """
        获取指定网卡的地址信息

        @param {string} nic_name - 网卡名(NIC NAME)

        @return {dict} - 返回网卡的地址信息，对应信息的Key为协议(部分研究出来的)：
            netifaces.AF_LINK -1000 物理地址 : {'addr' : 物理地址(MAC地址)}
            netifaces.AF_INET 2 互联网网络地址(ipv4) : {'addr': IP地址, 'netmask': 网络掩码, 'broadcast': 广播地址}
            netifaces.AF_INET6 23 互联网网络地址(ipv6): 跟AF_INET一样
            AF_12844 25
            AF_APPLETALK 16
            AF_ATM 22
            AF_BAN 21
            AF_CCITT 10
            AF_CHAOS 5
            AF_CLUSTER 24
            AF_DATAKIT 9
            AF_DECnet 12
            AF_DLI 13
            AF_ECMA 8
            AF_FIREFOX 19
            AF_HYLINK 15
            AF_IMPLINK 3
            AF_IPX 6
            AF_IRDA 26
            AF_ISO 7
            AF_LAT 14
            AF_NETBIOS 17
            AF_NETDES 28
            AF_NS 6
            AF_PUP 4
            AF_SNA 11
            AF_UNIX 1
            AF_UNKNOWN1 20
            AF_UNSPEC 0
            AF_VOICEVIEW 18
        """
        return netifaces.ifaddresses(nic_name)

    @staticmethod
    def get_net_gateways():
        """
        返回本机的网关信息清单

        @return {dict} - 网关信息清单，key为协议（见address_families, 除default不同），
            value为数组['地址', '使用该网关地址的网卡名NIC NAME', 是否默认网关]
            字典里有一个特殊key为'default'，可通过这个获取到默认网关信息
        """
        return netifaces.gateways()

    #############################
    # 网页处理相关
    #############################
    @staticmethod
    def get_web_page_code(url: str, data=None, timeout=socket._GLOBAL_DEFAULT_TIMEOUT,
                          encoding='utf-8', retry=0, proxy: dict = None,
                          cafile=None, capath=None, cadefault=False, context=None, real_url=['']):
        """
        获取网页代码(静态代码)

        @param {str|urllib.request.Request} url - 要获取的网页的url，可用是一个字符串地址或者Request对象
        @param {bytes} data=None - Post提交的数据，正常以GET参数获取，data传值后将以POST参数获取
            示例(将data转换为字节, urlencode可用支持数组或列表的对象):
                data = urllib.parse.urlencode(data).encode('utf-8')
        @param {float} timeout=socket._GLOBAL_DEFAULT_TIMEOUT - 超时时间，单位为秒
            默认使用socket的默认超时时间，如果没有使用socket.setdefaulttimeout设置，则是不超时
        @param {str} encoding='utf-8' - 解析返回页面内容的编码
        @param {int} retry=0 - 超时重试次数
        @param {dict} proxy=None - 设置访问代理，例如{'http': 'http://61.135.217.7:80'}, 或 {'https': 'https://61.135.217.7:443'}
            注：指定代理模式不支持cafile、capath、cadefault、context等参数
        @param {str} cafile=None - 本地CA证书文件
        @param {str} capath=None - 本地CA证书所在路径
        @param {bool} cadefault=False - ?
        @param {ssl.SSLContext} context=None - SSL证书验证上下文
        @param {list} real_url=[''] - 通过该入参返回真实的url地址(数组第0个)

        @return {str} - 访问网页的静态代码

        @example url使用的Request对象的生成示例：
            # 访问地址
            url = 'xxx'
            # 报文头信息
            headers ={
                "User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/66.0.3359.139 Safari/537.36",
            }
            # 生成Request对象
            urllib.request.Request(url, headers=headers)

        @example 忽略网站的未经核实的证书认证错误
            # 将以下生成的context对象传入执行参数
            import ssl
            context = ssl._create_unverified_context()

        """
        # 创建代理句柄
        if proxy is not None:
            # 处理代理格式
            _new_proxy = dict()
            for _key, _val in proxy:
                _url_info = urlparse(_val)
                _new_proxy[_url_info.scheme] = _url_info.netloc

            _proxy_handle = urllib.request.ProxyHandler(_new_proxy)
            _opener = urllib.request.build_opener(_proxy_handle)

        _retry_time = 1
        while True:
            # 正式的处理逻辑
            try:
                real_url[0] = url
                if proxy is None:
                    # 非代理模式
                    with urllib.request.urlopen(
                        url, data=data, timeout=timeout, cafile=cafile,
                        capath=capath, cadefault=cadefault, context=context
                    ) as _res:
                        real_url[0] = _res.url
                        return _res.read().decode(encoding)
                else:
                    # 代理模式
                    with _opener.open(url, data=data, timeout=timeout) as _res:
                        real_url[0] = _res.url
                        return _res.read().decode(encoding)
            except urllib.error.HTTPError:
                if _retry_time <= retry:
                    _retry_time += 1
                    continue
                else:
                    raise

    @staticmethod
    def get_web_page_dom_code(url: str, browser=None, common_options=None,
                              webdriver_type=EnumWebDriverType.Chrome, driver_options={},
                              cookie: dict = None):
        """
        获取页面加载后的动态html

        @param {str} url - 要访问的url
        @param {WebDriver} browser=None - 要使用的浏览器，如果为None则会创建一个新的
        @param {dict} common_options=None - 通用参数
            headless {bool} True - 是否无界面模式(部分浏览器不支持)
            timeout {float} 10 - 等待超时时间，单位为秒
            wait_all_loaded {bool} True - 是否等待所有页面元素加载完
            roll_to_end {bool} False - 是否滚动到页面结尾(加载更多的情况), 必须跟until_menthod结合判断
            until_menthod {function} - 如果不等待所有页面加载完，判断函数，函数应返回True/False
            until_message {str} - 传入判断函数的信息
            session_id {str} - 上一次调用的浏览器session id (browser.session_id)，需要在同一个浏览器打开下一个页面时使用
            executor_url {str} - 上一次调用的执行url (browser.command_executor._url)，需要在同一个浏览器打开下一个页面时使用
            quit {bool} - 是否关闭浏览器，如果为False，会将当前浏览器的session_id和executor_url返回到传入字典的相应参数中
            size_type {str} - 浏览器大小类型, 不传代表默认大小，max - 最大化, min - 最小化, size - 指定大小
            width {int} - 浏览器宽(px)
            height {int} - 浏览器高(px)
            set_pos {bool} - 是否设置位置
            pos_x {int} - 浏览器x位置(px)
            pos_y {int} - 浏览器y位置(px)
        @param {EnumWebDriverType} webdriver_type=EnumWebDriverType.Chrome - 浏览器驱动类型
        @param {dict} driver_options={} - 调用驱动的参数，具体请查阅浏览器驱动的文档
        @param {dict} cookie=None - 要设置的cookie字典

        @returns {str} - 页面加载后的html代码

        @throws {AttributeError} - 传入不支持的浏览器类型时抛出异常

        @example 使用expected_conditions来实现页面加载等待判断
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.webdriver.common.by import By

            # 当出现id为kw的元素时结束等待
            common_options = {
                'timeout': 10,
                'wait_all_loaded': False,
                'until_menthod': EC.presence_of_element_located((By.ID, "kw")),
                'until_message': ''
            }
        """
        # 参数处理
        _common_options = {
            'headless': True,
            'timeout': 10,
            'wait_all_loaded': True,
            'roll_to_end': False,
            'until_menthod': None,
            'until_message': '',
            'session_id': '',
            'executor_url': '',
            'quit': True,
            'size_type': '',
            'width': '800',
            'height': '600',
            'set_pos': False,
            'pos_x': '0',
            'pos_y': '0',
        }
        if common_options is not None:
            _common_options.update(common_options)

        # 创建浏览器
        _browser = browser
        if browser is None:
            # 创建新的浏览器
            _browser = NetTool.get_webdriver_browser(
                common_options=_common_options,
                webdriver_type=webdriver_type,
                driver_options=driver_options
            )
        elif _common_options['session_id'] != '':
            # 设置sessionid
            _browser.session_id = _common_options['session_id']

            # 设置大小和位置
            if _common_options['size_type'] == 'max':
                _browser.maximize_window()
            elif _common_options['size_type'] == 'min':
                _browser.minimize_window()
            elif _common_options['size_type'] == 'size':
                _browser.set_window_size(
                    int(_common_options['width']), int(_common_options['height'])
                )

            if _common_options['set_pos']:
                _browser.set_window_position(
                    int(_common_options['pos_x']), int(_common_options['pos_y'])
                )

        # cookie
        if cookie is not None:
            _browser.add_cookie(cookie)

        # 打开网页
        _browser.get(url)

        if _common_options['roll_to_end']:
            # 循环操作滚动到结尾
            _start_time = datetime.datetime.now()
            while True:
                # 滚动
                _browser.execute_script('window.scrollTo(0,1000000)')

                # 检查是否达到结束条件
                try:
                    _wait = WebDriverWait(_browser, 1, 0.5)
                    _wait.until(_common_options['until_menthod'], _common_options['until_message'])

                    # 正常执行完成
                    break
                except:
                    _end_time = datetime.datetime.now()
                    _use = (_end_time - _start_time).total_seconds()
                    if _use < _common_options['timeout']:
                        # 没有超时，继续处理
                        continue

                    # 超时了，直接抛出异常
                    raise
        else:
            # 不涉及滚动
            if not _common_options['wait_all_loaded']:
                if _common_options['until_menthod'] is None:
                    # 没有检查方法，直接sleep等待超时
                    RunTool.sleep(_common_options['timeout'])
                else:
                    # 按条件等待加载
                    _wait = WebDriverWait(_browser, _common_options['timeout'], 0.5)
                    _wait.until(_common_options['until_menthod'], _common_options['until_message'])

        # 获取页面代码并返回
        _page_source = ''
        _use_time = 0.01
        while True:
            # 循环获取解决拿不到源码的问题
            _page_source = _browser.page_source
            if _page_source != '' or _use_time > _common_options['timeout']:
                break

            _use_time += 0.01
            RunTool.sleep(0.01)

        if _common_options['quit']:
            # 关闭浏览器
            _browser.quit()
        else:
            # 传入浏览器的信息
            common_options['session_id'] = _browser.session_id
            common_options['executor_url'] = _browser.command_executor._url

        return _page_source

    @staticmethod
    def get_webdriver_browser(common_options=None,
                              webdriver_type=EnumWebDriverType.Chrome, driver_options={}):
        """
        获取webdriver浏览器对象

        @param {dict} common_options=None - 通用参数
            headless {bool} True - 是否无界面模式(部分浏览器不支持)
            wait_all_loaded {bool} True - 是否等待所有页面元素加载完
            session_id {str} - 上一次调用的浏览器session id (browser.session_id)，需要在同一个浏览器打开下一个页面时使用
            executor_url {str} - 上一次调用的执行url (browser.command_executor._url)，需要在同一个浏览器打开下一个页面时使用
            size_type {str} - 浏览器大小类型, 不传代表默认大小，max - 最大化, min - 最小化, size - 指定大小
            width {int} - 浏览器宽(px)
            height {int} - 浏览器高(px)
            set_pos {bool} - 是否设置位置
            pos_x {int} - 浏览器x位置(px)
            pos_y {int} - 浏览器y位置(px)
        @param {EnumWebDriverType} webdriver_type=EnumWebDriverType.Chrome - 浏览器驱动类型
        @param {dict} driver_options=None - 调用驱动的参数，具体请查阅浏览器驱动的文档

        @return {WebDriver} - 浏览器对象
        """
        # 参数处理
        _common_options = {
            'headless': True,
            'wait_all_loaded': True,
            'session_id': '',
            'executor_url': '',
            'size_type': '',
            'width': '800',
            'height': '600',
            'set_pos': False,
            'pos_x': '0',
            'pos_y': '0',
        }
        if common_options is not None:
            _common_options.update(common_options)

        # 创建浏览器
        _desired_capabilities = None

        # 创建新的浏览器
        _browser = None
        if webdriver_type == EnumWebDriverType.Chrome:
            # 设置传入参数的基础值
            if driver_options is not None:
                if 'chrome_options' not in driver_options or driver_options['chrome_options'] is None:
                    driver_options['chrome_options'] = selenium.webdriver.chrome.options.Options()
            else:
                driver_options = {
                    'chrome_options': selenium.webdriver.chrome.options.Options()
                }

            # 设置公共参数
            if _common_options.get('headless', True):
                # 无浏览器模式
                driver_options['chrome_options'].add_argument('--headless')
                driver_options['chrome_options'].add_argument('--disable-gpu')

            if not _common_options['wait_all_loaded']:
                # 注释这两行会导致最后输出结果的延迟，即等待页面加载完成再输出
                _desired_capabilities = DesiredCapabilities.CHROME
                _desired_capabilities["pageLoadStrategy"] = "none"

            if _common_options['session_id'] != '':
                # 使用未关闭的浏览器
                _browser = webdriver.Remote(
                    command_executor=_common_options['executor_url'],
                    desired_capabilities=_desired_capabilities
                )
                _browser.quit()
                _browser.session_id = _common_options['session_id']
            else:
                _browser = webdriver.Chrome(
                    desired_capabilities=_desired_capabilities, **driver_options
                )
        elif webdriver_type == EnumWebDriverType.Firefox:
            if driver_options is not None:
                if 'firefox_options' not in driver_options or driver_options['firefox_options'] is None:
                    driver_options['firefox_options'] = selenium.webdriver.firefox.options.Options()
            else:
                driver_options = {
                    'firefox_options': selenium.webdriver.firefox.options.Options()
                }

            # 设置公共参数
            if _common_options.get('headless', True):
                # 无浏览器模式
                driver_options['firefox_options'].add_argument('-headless')

            if not _common_options['wait_all_loaded']:
                # 注释这两行会导致最后输出结果的延迟，即等待页面加载完成再输出
                _desired_capabilities = DesiredCapabilities.FIREFOX
                _desired_capabilities["pageLoadStrategy"] = "none"

            if _common_options['session_id'] != '':
                # 使用未关闭的浏览器
                _browser = webdriver.Remote(
                    command_executor=_common_options['executor_url'],
                    desired_capabilities=_desired_capabilities
                )
                _browser.quit()
                _browser.session_id = _common_options['session_id']
            else:
                _browser = webdriver.Firefox(
                    desired_capabilities=_desired_capabilities, **driver_options
                )
        elif webdriver_type == EnumWebDriverType.Ie:
            if not _common_options['wait_all_loaded']:
                # 注释这两行会导致最后输出结果的延迟，即等待页面加载完成再输出
                _desired_capabilities = DesiredCapabilities.INTERNETEXPLORER
                _desired_capabilities["pageLoadStrategy"] = "none"

            if _common_options['session_id'] != '':
                # 使用未关闭的浏览器
                _browser = webdriver.Remote(
                    command_executor=_common_options['executor_url'],
                    desired_capabilities=_desired_capabilities
                )
                _browser.session_id = _common_options['session_id']
            else:
                _browser = webdriver.Ie(
                    desired_capabilities=_desired_capabilities,
                    **driver_options
                )
        elif webdriver_type == EnumWebDriverType.Edge:
            if not _common_options['wait_all_loaded']:
                # 注释这两行会导致最后输出结果的延迟，即等待页面加载完成再输出
                _desired_capabilities = DesiredCapabilities.EDGE
                _desired_capabilities["pageLoadStrategy"] = "none"

            if _common_options['session_id'] != '':
                # 使用未关闭的浏览器
                _browser = webdriver.Remote(
                    command_executor=_common_options['executor_url'],
                    desired_capabilities=_desired_capabilities
                )
                _browser.session_id = _common_options['session_id']
            else:
                _browser = webdriver.Edge(
                    capabilities=_desired_capabilities,
                    **driver_options
                )
        elif webdriver_type == EnumWebDriverType.PhantomJS:
            if not _common_options['wait_all_loaded']:
                # 注释这两行会导致最后输出结果的延迟，即等待页面加载完成再输出
                _desired_capabilities = DesiredCapabilities.PHANTOMJS
                _desired_capabilities["pageLoadStrategy"] = "none"

            if _common_options['session_id'] != '':
                # 使用未关闭的浏览器
                _browser = webdriver.Remote(
                    command_executor=_common_options['executor_url'],
                    desired_capabilities=_desired_capabilities
                )
                _browser.session_id = _common_options['session_id']
            else:
                _browser = webdriver.PhantomJS(
                    desired_capabilities=_desired_capabilities,
                    **driver_options
                )
        elif webdriver_type == EnumWebDriverType.Safari:
            if not _common_options['wait_all_loaded']:
                # 注释这两行会导致最后输出结果的延迟，即等待页面加载完成再输出
                _desired_capabilities = DesiredCapabilities.SAFARI
                _desired_capabilities["pageLoadStrategy"] = "none"

            if _common_options['session_id'] != '':
                # 使用未关闭的浏览器
                _browser = webdriver.Remote(
                    command_executor=_common_options['executor_url'],
                    desired_capabilities=_desired_capabilities
                )
                _browser.session_id = _common_options['session_id']
            else:
                _browser = webdriver.Safari(
                    desired_capabilities=_desired_capabilities,
                    **driver_options
                )
        else:
            raise AttributeError('not support webdriver type: %s' % str(webdriver_type))

        # 设置浏览器大小和位置
        if _common_options['size_type'] == 'max':
            _browser.maximize_window()
        elif _common_options['size_type'] == 'min':
            _browser.minimize_window()
        elif _common_options['size_type'] == 'size':
            _browser.set_window_size(
                int(_common_options['width']), int(_common_options['height'])
            )

        if _common_options['set_pos']:
            _browser.set_window_position(
                int(_common_options['pos_x']), int(_common_options['pos_y'])
            )

        # 返回浏览器
        return _browser

    #############################
    # 下载文件相关
    #############################
    @staticmethod
    def get_http_fileinfo(url: str, headers={}, connect_timeout=None,
                          params={}, proxies={}, verify=True, cookies={}):
        """
        获取网络文件基本信息

        @param {str} url - 下载文件的url
        @param {dict} headers={} - 下载请求要自定义的http头
        @param {float} connect_timeout=None - 连接服务器的超时时间，单位为秒
        @param {dict} params={} - 请求url的参数，拼接到url中，例如"https://www.baidu.com/s?wd=Python"
        @param {dict} proxies={} - 代理服务器，例如：
            proxies={
                "http":"http://1.192.242.107:9999"
                # "https":"https://192.168.0.1:80"
            }
        @param {bool} verify=True - ssl证书验证是否跳过，可设置为False跳过
        @param {dict} cookies={} - cookies参数

        @return {dict} - 文件基本信息字典：
            name - 文件名
            size - 文件大小，如果不可预知的大小则为-1
            support_continue - 是否支持断点续传
        """
        # 基本参数
        _headers = copy.deepcopy(headers)
        _headers['Range'] = 'bytes=0-4'
        _content_range = ''
        _support_continue = False
        _total_size = -1

        # 访问网络并获取请求
        _res = requests.head(
            url, headers=_headers, timeout=connect_timeout,
            verify=verify, proxies=proxies, params=params, cookies=cookies
        )
        try:
            if _res.status_code == 206:
                # 服务器支持断点
                if 'content-range' in _res.headers.keys():
                    _content_range = _res.headers['content-range']
                    try:
                        _total_size = int(re.match(r'^bytes 0-4/(\d+)$', _content_range).group(1))
                        _support_continue = True
                    except:
                        _total_size = int(_res.headers['content-length'])
            else:
                _total_size = int(_res.headers['content-length'])
        except:
            pass

        # 返回结果
        return {
            'name': os.path.split(url)[1],
            'size': _total_size,
            'support_continue': _support_continue
        }

    @staticmethod
    def download_http_file(url: str, filename=None, path='', is_resume=False, headers={}, connect_timeout=None,
                           params={}, proxies={}, verify=True, cookies={},
                           block_size=1024, retry=0, show_rate=False):
        """
        下载文件

        @param {str} url - 要下载的文件url
        @param {str} filename=None - 保存的文件名，如果传None代表使用url的文件名
        @param {str} path='' - 要保存的文件路径
        @param {bool} is_resume=False - 是否使用续传功能，如果不使用则统一用wget下载
        @param {dict} headers={} - 要带上的http协议头
        @param {float} connect_timeout=None - 连接超时时间，单位为秒
        @param {dict} params={} - 请求url的参数，拼接到url中，例如"https://www.baidu.com/s?wd=Python"
        @param {dict} proxies={} - 代理服务器，例如：
            proxies={
                "http":"http://1.192.242.107:9999"
                # "https":"https://192.168.0.1:80"
            }
        @param {bool} verify=True - ssl证书验证是否跳过，可设置为False跳过
        @param {dict} cookies={} - cookies参数
        @param {int} block_size=1024 - 每次下载块大小，单位为byte
        @param {int} retry=0 - 自动重试次数
        @param {bool} show_rate=False - 显示下载进度(仅wget模式支持)
        """
        _retry_time = 0
        _fileinfo = None
        _filename = filename

        # 只有需要断点续传的情况才获取文件信息
        if is_resume:
            while True:
                try:
                    _fileinfo = NetTool.get_http_fileinfo(
                        url, headers=headers, connect_timeout=connect_timeout, params=params,
                        proxies=proxies, verify=verify, cookies=cookies
                    )
                    break
                except:
                    if _retry_time < retry:
                        _retry_time += 1
                        continue
                    else:
                        raise

            _filename = filename
            if filename is None:
                _filename = _fileinfo['name']

        # 加上路径
        if _filename is None:
            _filename = os.path.split(url)[1]

        _filename = os.path.join(path, _filename)

        if not is_resume or not _fileinfo['support_continue']:
            # 不需要续传，或不支持自动续传, 使用wget执行完整的下载, 但不显示下载进度
            _bar = None
            if show_rate:
                _bar = wget.bar_adaptive

            _new_proxy = dict()
            if proxies is not None and len(proxies) > 0:
                for _key in proxies.keys():
                    _url_info = urlparse(proxies[_key])
                    _new_proxy[_url_info.scheme] = _url_info.netloc

            if cookies is not None and len(cookies) > 0:
                # 将cookie放入头文件
                if headers is None:
                    headers = {}
                _cookie_str_list = list()
                for _key, _val in cookies:
                    _cookie_str_list.append('%s=%s' % (_key, _val))
                headers['Cookie'] = '; '.join(_cookie_str_list)

            wget.download(url, out=_filename, bar=_bar, headers=headers, proxy=_new_proxy)
        else:
            # 自动续传
            _headers = copy.deepcopy(headers)
            _down_size = 0
            _temp_file = _filename + '.dt'
            if os.path.exists(_temp_file):
                _down_size = os.path.getsize(_temp_file)

            # 打开文件进行处理
            _file = open(_temp_file, 'ab')
            try:
                # 设置报文头，并连接
                _headers['Range'] = 'bytes=%d-' % _down_size
                _retry_time = 0
                _res = None
                while True:
                    try:
                        _res = requests.get(
                            url, timeout=connect_timeout, stream=True, verify=verify, headers=_headers,
                            proxies=proxies, params=params, cookies=cookies
                        )
                        break
                    except:
                        if _retry_time < retry:
                            _retry_time += 1
                            continue
                        else:
                            raise

                for _chunk in _res.iter_content(chunk_size=block_size):
                    if _chunk:
                        _file.write(_chunk)
                        _down_size += len(_chunk)
                        _file.flush()
                        RunTool.sleep(0.001)
            finally:
                _file.close()

            # 正常处理完成
            if os.path.exists(_filename):
                # 删除原来存在的文件
                os.remove(_filename)

            # 修改文件名
            os.rename(_temp_file, _filename)

    #############################
    # Restful Api相关
    #############################
    @staticmethod
    def restful_api_call(url: str, method: str = 'get', back_type: str = 'json', encoding: str = None,
                         block_size: int = 1024, save_file: str = None,
                         raise_exception: bool = False, success_code: list = [200],
                         logger=None, log_level: int = logging.DEBUG, **kwargs):
        """
        调用Restful Api

        @param {str} url - 要调用的url地址
        @param {str} method='get' - Http方法
        @param {str} back_type='json' - 返回信息的类型
            json - json对象(字典或列表)
            text - 文本
            file - 存入指定文件
            bytes - 字节数组
        @param {str} encoding=None - 编码，如果不传则使用返回http头的字符集
        @param {int} block_size=1024 - 如果指定stream时，每次获取的数据块大小
        @param {str} save_file=None - back_type为file时指定要存储的文件
        @param {bool} raise_exception=False - 当出现异常时是否抛出异常
        @param {list} success_code=[200] - 识别返回的status_code为成功的清单
        @param {Logger} logger=None - 日志对象
        @param {int} log_level=logging.DEBUG - 日志级别
        @param {kwargs} - 扩展参数，参考requests.request的参数，主要参数如下：
            headers {dict}  - 要带上的http协议头
            params {dict} - 请求url的参数，拼接到url中，例如"https://www.baidu.com/s?wd=Python"
            json {object} - 报文体内容，可以转换为json字符串的python对象，例如dict、list等
            data {object} - 报文体内容，可以是字典，元组列表，字节或文件对象
                注：json和data可选其中一种方式送入报文体中
            timeout {float} - 超时时间(秒)
            stream {bool} - 指示返回数据是否以流的方式处理
            verify {bool} - ssl证书验证是否跳过，可设置为False跳过
            allow_redirects {bool} - 是否允许重定向
            proxies {dict} - 代理服务器，例如：
                proxies={
                    "http":"http://1.192.242.107:9999"
                    # "https":"https://192.168.0.1:80"
                }

        @returns {dict} - 返回请求结果字典
            {
                'is_success': bool_是否成功,
                'status_code': int_响应状态码,
                'headers': dict_响应http头,
                'back_object': object_返回对象，对应调用参数可以为dict、str、bytes、文件名,
                'exception': 如果出现异常，异常对象,
                'encoding': 字符集
            }
        """
        # 开始先记录日志
        if logger is not None:
            _logger_error = False
            _start_time = datetime.datetime.now()
            _log_str = '[INF-SEND]%s %s' % (method, url)
            if 'params' in kwargs.keys():
                _log_str = '%s %s' % (_log_str, str(kwargs['params']))
            if 'headers' in kwargs.keys():
                _log_str = '%s\n%s' % (_log_str, str(kwargs['headers']))
            if 'json' in kwargs.keys():
                _log_str = '%s\n%s' % (_log_str, str(kwargs['json']))
            if 'data' in kwargs.keys():
                if type(kwargs['data']) == bytes:
                    _log_str = '%s\n%s' % (_log_str, ' '.join(
                        [hex(int(i)) for i in kwargs['data']]))
                else:
                    _log_str = '%s\n%s' % (_log_str, str(kwargs['data']))

            logger.log(log_level, _log_str)

        # 开始处理
        _back = {
            'is_success': True,
            'status_code': -1,
            'headers': None,
            'back_object': None,
            'exception': None,
            'encoding': None
        }
        try:
            _resp = requests.request(method, url, **kwargs)
            _back['status_code'] = _resp.status_code
            _back['is_success'] = (_resp.status_code in success_code)
            _back['headers'] = _resp.headers
            if _back['is_success']:
                _encoding = _resp.encoding if encoding is None else encoding
                _stream_io = None
                _bytes = []
                if back_type == 'file':
                    _stream_io = open(save_file, 'wb')
                    _back['back_object'] = save_file
                else:
                    _stream_io = BytesIO()

                if kwargs.get('stream', False):
                    # 流模式，通过IO获取内容，并保存
                    try:
                        for _chunk in _resp.iter_content(chunk_size=block_size):
                            if _chunk:
                                _stream_io.write(_chunk)
                                _stream_io.flush()
                                RunTool.sleep(0.001)

                        if back_type != 'file':
                            # 非文件模式，转换为bytes数组
                            _bytes = _stream_io.getvalue()
                    finally:
                        _stream_io.close()
                else:
                    _bytes = _resp.content

                # 处理非file的存储
                if back_type == 'json':
                    _back['back_object'] = json.loads(_bytes, encoding=_encoding)
                elif back_type == 'text':
                    _back['back_object'] = str(_bytes, encoding=_encoding)
                elif back_type != 'file':
                    # 直接返回字节数组
                    _back['back_object'] = _bytes
        except:
            if logger is not None:
                _logger_error = True
                _use = str((datetime.datetime.now() - _start_time).total_seconds())
                _log_str = '[INF-SEND][USE:%ss][EX:%s]%s %s\n%s' % (
                    _use, str(sys.exc_info()[0]), method, url, traceback.format_exc()
                )
                logger.log(logging.ERROR, _log_str)

            if raise_exception:
                # 抛出异常
                raise
            else:
                _back['is_success'] = False
                _back['exception'] = sys.exc_info()[1]

        if logger is not None and not _logger_error:
            _use = str((datetime.datetime.now() - _start_time).total_seconds())
            _log_str = '[INF-BACK][USE:%ss]%s %s %s\n%s\n%s' % (
                _use, method, url, str(_back['status_code']), str(_back['headers']),
                str(_back['back_object']) if type(_back['back_object']) != bytes else ' '.join(
                    [hex(int(i)) for i in _back['back_object']])
            )
            logger.log(log_level, _log_str)

        # 返回结果
        return _back


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    # 打印版本信息
    print(('模块名：%s  -  %s\n'
           '作者：%s\n'
           '发布日期：%s\n'
           '版本：%s' % (__MOUDLE__, __DESCRIPT__, __AUTHOR__, __PUBLISH__, __VERSION__)))

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
import netifaces
import socket
import urllib
import copy
import requests
import re
import wget
import time
from enum import Enum
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
import selenium.webdriver.chrome.options
import selenium.webdriver.firefox.options


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
                          encoding='utf-8', retry=0,
                          cafile=None, capath=None, cadefault=False, context=None):
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
        @param {str} cafile=None - 本地CA证书文件
        @param {str} capath=None - 本地CA证书所在路径
        @param {bool} cadefault=False - ?
        @param {ssl.SSLContext} context=None - SSL证书验证上下文

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
        _retry_time = 1
        while True:
            # 正式的处理逻辑
            try:
                with urllib.request.urlopen(
                    url, data=data, timeout=timeout, cafile=cafile,
                    capath=capath, cadefault=cadefault, context=context
                ) as _res:
                    return _res.read().decode(encoding)
            except urllib.error.HTTPError:
                if _retry_time <= retry:
                    _retry_time += 1
                    continue
                else:
                    raise

    @staticmethod
    def get_web_page_dom_code(url: str, browser=None, common_options=None,
                              webdriver_type=EnumWebDriverType.Chrome, driver_options=None):
        """
        获取页面加载后的动态html

        @param {str} url - 要访问的url

        @param {WebDriver} browser=None - 要使用的浏览器，如果为None则会创建一个新的
        @param {dict} common_options=None - 通用参数
            headless {bool} True - 是否无界面模式(部分浏览器不支持)
            timeout {float} 10 - 等待超时时间，单位为秒
            wait_all_loaded {bool} True - 是否等待所有页面元素加载完
            until_menthod {function} - 如果不等待所有页面加载完，判断函数，函数应返回True/False
            until_message {str} - 传入判断函数的信息
        @param {EnumWebDriverType} webdriver_type=EnumWebDriverType.Chrome - 浏览器驱动类型
        @param {dict} driver_options=None - 调用驱动的参数，具体请查阅浏览器驱动的文档

        @returns {str} - 页面加载后的html代码

        @throws {AttributeError} - 传入不支持的浏览器类型时抛出异常

        @example 使用expected_conditions来实现页面加载等待判断
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.webdriver.common.by import By

            # 当出现id为kw的元素时结束等待
            common_options = {
                'timeout': 10,
                'wait_all_loaded': False,
                'until_menthod': EC.presence_of_element_located((By.ID, "kw"),
                'until_message': ''
            }
        """
        # 参数处理
        _common_options = {
            'headless': True,
            'timeout': 10,
            'wait_all_loaded': True,
            'until_menthod': None,
            'until_message': ''
        }
        if common_options is not None:
            _common_options.update(common_options)

        # 创建浏览器
        _browser = browser
        if browser is None:
            # 创建新的浏览器
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

                _browser = webdriver.Chrome(**driver_options)
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

                _browser = webdriver.Firefox(**driver_options)
            elif webdriver_type == EnumWebDriverType.Ie:
                _browser = webdriver.Ie(**driver_options)
            elif webdriver_type == EnumWebDriverType.Edge:
                _browser = webdriver.Edge(**driver_options)
            elif webdriver_type == EnumWebDriverType.PhantomJS:
                _browser = webdriver.PhantomJS(**driver_options)
            elif webdriver_type == EnumWebDriverType.PhantomJS:
                _browser = webdriver.Safari(**driver_options)
            else:
                raise AttributeError('not support webdriver type: %s' % str(webdriver_type))

        # 设置等待全部页面加载完成
        if _common_options['wait_all_loaded']:
            # 全部页面加载完成
            _browser.implicitly_wait(_common_options['timeout'])

        # 打开网页
        _browser.get(url)

        if not _common_options['wait_all_loaded']:
            # 按条件等待加载
            _wait = WebDriverWait(_browser, _common_options['timeout'], 0.5)
            _wait.until(_common_options['until_menthod'], _common_options['until_message'])

        # 获取页面代码并返回
        return _browser.page_source

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
        if 'content-range' in _res.headers.keys():
            _content_range = _res.headers['content-range']
            try:
                _total_size = int(re.match(r'^bytes 0-4/(\d+)$', _content_range).group(1))
                _support_continue = True
            except:
                try:
                    _total_size = int(_content_range)
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
                           block_size=1024, retry=0):
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
        """
        _retry_time = 0
        # 先尝试获取文件信息
        _fileinfo = None
        while True:
            try:
                _fileinfo = NetTool.get_http_fileinfo(
                    url, headers=headers, connect_timeout=connect_timeout)
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
        _filename = os.path.join(path, _filename)

        if not _fileinfo['support_continue'] or not is_resume:
            # 不支持自动续传, 使用wget执行完整的下载
            wget.download(url, out=_filename)
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
                        time.sleep(0.001)
            finally:
                _file.close()

            # 正常处理完成
            if os.path.exists(_filename):
                # 删除原来存在的文件
                os.remove(_filename)

            # 修改文件名
            os.rename(_temp_file, _filename)


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    # 打印版本信息
    print(('模块名：%s  -  %s\n'
           '作者：%s\n'
           '发布日期：%s\n'
           '版本：%s' % (__MOUDLE__, __DESCRIPT__, __AUTHOR__, __PUBLISH__, __VERSION__)))

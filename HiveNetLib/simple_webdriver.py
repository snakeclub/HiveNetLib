#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
# Copyright 2019 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
selenium web driver的简单封装使用模块

@module simple_webdriver
@file simple_webdriver.py
"""

import sys
import os
import datetime
import time
from enum import Enum
# 根据当前文件路径将包路径纳入，在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir)))
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
        from selenium.webdriver.common.proxy import Proxy, ProxyType
        from selenium.webdriver.remote.webelement import WebElement
        from selenium.webdriver.common.by import By
        from selenium.webdriver.common.keys import Keys
        break
    except ImportError:
        if not process_install_selenium:
            deps_tool.install_package('selenium')
            process_install_selenium = True
            continue
        raise
# 装载自有模块
from HiveNetLib.base_tools.run_tool import RunTool


__MOUDLE__ = 'simple_webdriver'  # 模块名
__DESCRIPT__ = u'selenium web driver的简单封装使用模块'  # 模块描述
__VERSION__ = '0.1.0'  # 版本
__AUTHOR__ = u'黎慧剑'  # 作者
__PUBLISH__ = '2021.07.15'  # 发布日期


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


class SimpleWebDriver(object):
    """
    selenium web driver的封装类
    """

    #############################
    # 公共的变量
    #############################
    _by_mapping = {
        'id': By.ID,
        'xpath': By.XPATH,
        'tag_name': By.TAG_NAME,
        'name': By.NAME,
        'class_name': By.CLASS_NAME,
        'css_selector': By.CSS_SELECTOR,
        'link_text': By.LINK_TEXT,
        'partial_link_text': By.PARTIAL_LINK_TEXT
    }

    _driver_class_mapping = {
        EnumWebDriverType.Chrome: webdriver.Chrome,
        EnumWebDriverType.Firefox: webdriver.Firefox
    }

    #############################
    # 静态工具函数
    #############################
    @classmethod
    def get_webdriver(cls, common_options: dict = None, webdriver_type=EnumWebDriverType.Chrome,
                      driver_options: dict = {}, cookie: dict = None):
        """
        获取webdriver浏览器对象

        @param {dict} common_options=None - 通用参数
            headless {bool} True - 是否无界面模式(部分浏览器不支持)
            feign_browser {bool} False - 是否伪装为正常浏览器
            lang {str} - 浏览器默认语言(zh-CN)
            disable_security {bool} False - 是否禁用网络安全限制（以支持跨域），暂时只有Chrome支持
            no_image {bool} False - 是否禁止图片下载
            no_css {bool} False - 是否禁止CSS文件下载
            default_download_path {str} - 设置默认下载路径, 有传值代表设置，暂时只有Chrome支持
            proxy {str} - 指定代理连接，有传值代表设置，格式为'scheme://地址:端口'
            wait_all_loaded {bool} True - 是否等待所有页面元素加载完
            session_id {str} - 上一次调用的浏览器session id (driver.session_id)，需要在同一个浏览器打开下一个页面时使用
            executor_url {str} - 上一次调用的执行url (driver.command_executor._url)，需要在同一个浏览器打开下一个页面时使用
            size_type {str} - 浏览器大小类型, 不传代表默认大小，max - 最大化, min - 最小化, size - 指定大小
            width {int} - 浏览器宽(px)
            height {int} - 浏览器高(px)
            set_pos {bool} - 是否设置位置
            pos_x {int} - 浏览器x位置(px)
            pos_y {int} - 浏览器y位置(px)
        @param {EnumWebDriverType} webdriver_type=EnumWebDriverType.Chrome - 浏览器驱动类型
        @param {dict} driver_options=None - 调用驱动的参数，具体请查阅浏览器驱动的文档
        @param {dict} cookie=None - 要设置的cookie字典

        @return {WebDriver} - 浏览器对象
        """
        # 参数默认值处理
        _common_options = cls._set_common_options_default(common_options)

        # 获取创建浏览器的参数
        if webdriver_type == EnumWebDriverType.Chrome:
            _options = cls.create_chrome_options(common_options, driver_options)
        elif webdriver_type == EnumWebDriverType.Firefox:
            _options = cls.create_firefox_options(common_options, driver_options)
        else:
            raise AttributeError('not support webdriver type: %s' % str(webdriver_type))

        # 创建浏览器对象
        _driver = None
        if _common_options['session_id'] != '':
            # 使用未关闭的浏览器
            _driver = webdriver.Remote(**_options)
            _driver.quit()
            _driver.session_id = _common_options['session_id']
        else:
            # 新建浏览器
            _driver = cls._driver_class_mapping[webdriver_type](**_options)

        # 添加cookie
        if cookie is not None:
            _driver.add_cookie(cookie)

        # 设置浏览器大小和位置
        cls._set_driver_pos(_driver, _common_options)

        # 返回浏览器
        return _driver

    @classmethod
    def get_web_page_dom(cls, url: str, driver=None, common_options: dict = None,
                         webdriver_type=EnumWebDriverType.Chrome, driver_options: dict = {},
                         cookie: dict = None):
        """
        获取页面加载后的动态html

        @param {str} url - 要访问的url
        @param {WebDriver} driver=None - 要使用的浏览器，如果为None则会创建一个新的
        @param {dict} common_options=None - 通用参数
            headless {bool} True - 是否无界面模式(部分浏览器不支持)
            feign_browser {bool} False - 是否伪装为正常浏览器
            lang {str} - 浏览器默认语言(zh-CN)
            disable_security {bool} False - 是否禁用网络安全限制（以支持跨域）
            no_image {bool} False - 是否禁止图片下载
            no_css {bool} False - 是否禁止CSS文件下载
            default_download_path {str} - 设置默认下载路径, 有传值代表设置
            proxy {str} - 指定代理连接，有传值代表设置，格式为'scheme://地址:端口'
            timeout {float} 10 - 等待超时时间，单位为秒
            wait_all_loaded {bool} True - 是否等待所有页面元素加载完
            roll_to_end {bool} False - 是否滚动到页面结尾(加载更多的情况), 必须跟until_menthod结合判断
            until_menthod {function} - 如果不等待所有页面加载完，判断函数，函数应返回True/False
            until_message {str} - 传入判断函数的信息
            session_id {str} - 上一次调用的浏览器session id (driver.session_id)，需要在同一个浏览器打开下一个页面时使用
            executor_url {str} - 上一次调用的执行url (driver.command_executor._url)，需要在同一个浏览器打开下一个页面时使用
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
        _common_options = cls._set_common_options_default(common_options)
        _driver_options = driver_options

        # 创建浏览器
        _driver = driver
        if _driver is None:
            # 创建新的浏览器
            _driver = cls.get_webdriver(
                common_options=common_options, webdriver_type=webdriver_type, driver_options=_driver_options,
                cookie=cookie
            )
        else:
            # 设置cookie
            if cookie is not None:
                _driver.add_cookie(cookie)

        # 打开网页
        _driver.get(url)

        if _common_options['roll_to_end']:
            # 循环操作滚动到结尾
            _start_time = datetime.datetime.now()
            while True:
                # 滚动
                _driver.execute_script('window.scrollTo(0,1000000)')

                # 检查是否达到结束条件
                try:
                    _wait = WebDriverWait(_driver, 1, 0.5)
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
                    _wait = WebDriverWait(_driver, _common_options['timeout'], 0.5)
                    _wait.until(_common_options['until_menthod'], _common_options['until_message'])

        # 获取页面代码并返回
        _page_source = ''
        _use_time = 0.01
        while True:
            # 循环获取解决拿不到源码的问题
            _page_source = _driver.page_source
            if _page_source != '' or _use_time > _common_options['timeout']:
                break

            _use_time += 0.01
            RunTool.sleep(0.01)

        if _common_options['quit']:
            # 关闭浏览器
            _driver.quit()
        else:
            # 传入浏览器的信息
            common_options['session_id'] = _driver.session_id
            common_options['executor_url'] = _driver.command_executor._url

        return _page_source

    #############################
    # 各类WebDriver的创建参数构造函数
    #############################
    @classmethod
    def create_chrome_options(cls, common_options: dict = None, driver_options: dict = {}) -> dict:
        """
        创建Chrome类型WebDriver对象生成参数字典

        @param {dict} common_options=None - 通用参数，支持参数如下：
            headless {bool} True - 是否无界面模式(部分浏览器不支持)
            feign_browser {bool} False - 是否伪装为正常浏览器
            lang {str} - 浏览器默认语言(zh-CN)
            disable_security {bool} False - 是否禁用网络安全限制（以支持跨域）
            no_image {bool} False - 是否禁止图片下载
            no_css {bool} False - 是否禁止CSS文件下载
            default_download_path {str} - 设置默认下载路径, 有传值代表设置
            proxy {str} - 指定代理连接，有传值代表设置，格式为'scheme://地址:端口'
            wait_all_loaded {bool} True - 是否等待所有页面元素加载完
            session_id {str} - 上一次调用的浏览器session id (driver.session_id)，需要在同一个浏览器打开下一个页面时使用
            executor_url {str} - 上一次调用的执行url (driver.command_executor._url)，需要在同一个浏览器打开下一个页面时使用
        @param {dict} driver_options={} - 自定义的创建WebDriver对象参数，具体请查阅WebDriver驱动的文档

        @returns {dict} - 返回可直接送入WebDriver创建函数的入参字典
        """
        _common_options = cls._set_common_options_default(common_options)
        _driver_options = driver_options

        # 需要调整的参数值
        _desired_capabilities = _driver_options.get('desired_capabilities', None)
        _options: selenium.webdriver.chrome.options.Options = _driver_options.get(
            'options', selenium.webdriver.chrome.options.Options()
        )
        if 'prefs' not in _options.experimental_options.keys():
            _options.experimental_options['prefs'] = dict()

        # 参数设置
        if not _common_options['wait_all_loaded']:
            # 是否等待所有页面元素加载完
            # 注释这两行会导致最后输出结果的延迟，即等待页面加载完成再输出
            _desired_capabilities = DesiredCapabilities.CHROME
            _desired_capabilities["pageLoadStrategy"] = "none"

        if _common_options['headless']:
            # 无浏览器模式
            _options.add_argument('--headless')
            # _options.set_headless()
            if sys.platform == 'win32':
                _options.add_argument('--disable-gpu')

        if _common_options['feign_browser']:
            # 防止网站检测出Selenium的window.navigator.webdriver属性
            _options.add_experimental_option('excludeSwitches', ['enable-automation'])
            _options.add_argument("--no-sandbox")

        # 浏览器语言
        _options.add_argument("--lang=%s" % _common_options['lang'])

        if _common_options['disable_security']:
            # 禁用网络安全限制（以支持跨域）
            _options.add_argument("--disable-web-security")

        if _common_options['session_id'] != '':
            # 使用未关闭的浏览器
            _driver_options['command_executor'] = _common_options['executor_url']

        if _common_options['no_image']:
            # 禁止下载图片
            _options.experimental_options['prefs'].update({
                "profile.managed_default_content_settings.images": 2
            })

        if _common_options['no_css']:
            # 禁止下载CSS文件
            _options.experimental_options['prefs'].update({
                'permissions.default.stylesheet': 2
            })

        # 设置默认下载路径
        _default_download_path = _common_options.get('default_download_path', None)
        if _default_download_path is not None:
            _config = {
                'profile.default_content_settings.popups': 0,  # 设置为0禁止弹出窗口
                'download.prompt_for_download': False,
                'download.directory_upgrade': True,
                'safebrowsing.enabled': True,
                'download.default_directory': _default_download_path
            }
            _options.experimental_options['prefs'].update(_config)

        # 通过代理连接
        _proxy: str = _common_options.get('proxy', None)
        if _proxy is not None:
            _options.add_argument(
                "--proxy-server==%s" % _proxy
            )

        # 更新回driver_options
        _driver_options['desired_capabilities'] = _desired_capabilities
        _driver_options['options'] = _options

        return _driver_options

    @classmethod
    def create_firefox_options(cls, common_options: dict = None, driver_options: dict = {}) -> dict:
        """
        创建Firefox类型WebDriver对象生成参数字典

        @param {dict} common_options=None - 通用参数，支持参数如下：
            headless {bool} True - 是否无界面模式(部分浏览器不支持)
            feign_browser {bool} False - 是否伪装为正常浏览器
            lang {str} - 浏览器默认语言(zh-CN)
            no_image {bool} False - 是否禁止图片下载
            no_css {bool} False - 是否禁止CSS文件下载
            proxy {str} - 指定代理连接，有传值代表设置，格式为'scheme://地址:端口'
            wait_all_loaded {bool} True - 是否等待所有页面元素加载完
            session_id {str} - 上一次调用的浏览器session id (driver.session_id)，需要在同一个浏览器打开下一个页面时使用
            executor_url {str} - 上一次调用的执行url (driver.command_executor._url)，需要在同一个浏览器打开下一个页面时使用
        @param {dict} driver_options={} - 自定义的创建WebDriver对象参数，具体请查阅WebDriver驱动的文档

        @returns {dict} - 返回可直接送入WebDriver创建函数的入参字典
        """
        _common_options = cls._set_common_options_default(common_options)
        _driver_options = driver_options

        # 需要调整的参数值
        _desired_capabilities = _driver_options.get('desired_capabilities', None)
        _options: selenium.webdriver.firefox.options.Options = _driver_options.get(
            'options', selenium.webdriver.firefox.options.Options()
        )
        _firefox_profile: selenium.webdriver.firefox.options.FirefoxProfile = _driver_options.get(
            'firefox_profile', selenium.webdriver.firefox.options.FirefoxProfile()
        )

        # 参数设置
        if not _common_options['wait_all_loaded']:
            # 是否等待所有页面元素加载完
            # 注释这两行会导致最后输出结果的延迟，即等待页面加载完成再输出
            _desired_capabilities = DesiredCapabilities.CHROME
            _desired_capabilities["pageLoadStrategy"] = "none"

        if _common_options['headless']:
            # 无浏览器模式
            # _options.add_argument('-headless')
            _options.set_headless()
            _options.add_argument('--disable-gpu')

        if _common_options['feign_browser']:
            # 防止网站检测出Selenium的window.navigator.webdriver属性
            _firefox_profile.set_preference('dom.webdriver.enabled', False)
            _firefox_profile.set_preference('useAutomationExtension', False)

        # 浏览器语言
        _firefox_profile.set_preference('intl.accept_languages', _common_options['lang'])

        if _common_options['session_id'] != '':
            # 使用未关闭的浏览器
            _driver_options['command_executor'] = _common_options['executor_url']

        if _common_options['no_image']:
            # 禁止下载图片
            _firefox_profile.set_preference('permissions.default.image', 2)
            _firefox_profile.set_preference('browser.migration.version', 9001)  # 部分需要加上这个

        if _common_options['no_css']:
            # 禁止下载CSS文件
            _firefox_profile.set_preference('permissions.default.stylesheet', 2)

        # 通过代理连接
        _proxy = _common_options.get('proxy', None)
        if _proxy is not None:
            _proxy_info = _proxy[_proxy.find("://") + 3:]
            _driver_options['proxy'] = Proxy({
                'proxyType': ProxyType.MANUAL,
                'httpProxy': _proxy_info,
                'ftpProxy': _proxy_info,
                'sslProxy': _proxy_info,
                'noProxy': ''
            })

        # 更新回driver_options
        _firefox_profile.update_preferences()
        _driver_options['desired_capabilities'] = _desired_capabilities
        _driver_options['options'] = _options
        _driver_options['firefox_profile'] = _firefox_profile

        return _driver_options

    #############################
    # 类处理函数
    #############################
    def __init__(self, url: str, driver=None, common_options: dict = None,
                 webdriver_type=EnumWebDriverType.Chrome, driver_options: dict = {},
                 cookie: dict = None):
        """
        初始化selenium web driver的封装类

        @param {str} url - 初始访问的url
        @param {WebDriver} driver=None - 要使用的浏览器，如果为None则会创建一个新的
        @param {dict} common_options=None - 通用参数
            headless {bool} True - 是否无界面模式(部分浏览器不支持)
            feign_browser {bool} False - 是否伪装为正常浏览器
            lang {str} - 浏览器默认语言(zh-CN)
            disable_security {bool} False - 是否禁用网络安全限制（以支持跨域）
            no_image {bool} False - 是否禁止图片下载
            no_css {bool} False - 是否禁止CSS文件下载
            default_download_path {str} - 设置默认下载路径, 有传值代表设置
            proxy {str} - 指定代理连接，有传值代表设置，格式为'scheme://地址:端口'
            timeout {float} 10 - 等待超时时间，单位为秒
            wait_all_loaded {bool} True - 是否等待所有页面元素加载完
            roll_to_end {bool} False - 是否滚动到页面结尾(加载更多的情况), 必须跟until_menthod结合判断
            until_menthod {function} - 如果不等待所有页面加载完，判断函数，函数应返回True/False
            until_message {str} - 传入判断函数的信息
            session_id {str} - 上一次调用的浏览器session id (driver.session_id)，需要在同一个浏览器打开下一个页面时使用
            executor_url {str} - 上一次调用的执行url (driver.command_executor._url)，需要在同一个浏览器打开下一个页面时使用
            size_type {str} - 浏览器大小类型, 不传代表默认大小，max - 最大化, min - 最小化, size - 指定大小
            width {int} - 浏览器宽(px)
            height {int} - 浏览器高(px)
            set_pos {bool} - 是否设置位置
            pos_x {int} - 浏览器x位置(px)
            pos_y {int} - 浏览器y位置(px)
            debug_path {str} - 设置获取网页代码的时候存储debug文件的路径，如果传入代表进行debug
        @param {EnumWebDriverType} webdriver_type=EnumWebDriverType.Chrome - 浏览器驱动类型
        @param {dict} driver_options={} - 调用驱动的参数，具体请查阅浏览器驱动的文档
        @param {dict} cookie=None - 要设置的cookie字典
        """
        self.common_options = self._set_common_options_default(common_options)
        self.common_options['quit'] = False  # 不自动退出
        self.webdriver_type = webdriver_type
        self.driver = driver
        if driver is None:
            self.driver = self.get_webdriver(
                common_options=common_options, webdriver_type=webdriver_type,
                driver_options=driver_options, cookie=cookie
            )

        # 打开初始化页面
        self.get_web_page_dom(
            url, driver=self.driver, common_options=self.common_options,
            webdriver_type=webdriver_type
        )

    def __del__(self):
        """
        析构函数
        """
        try:
            if self.driver is not None:
                self.driver.quit()
                self.driver = None
        except:
            # 避免报错
            pass

    #############################
    # 处理函数
    #############################

    def get_current_dom(self) -> str:
        """
        获取当前动态html页面

        @returns {str} - 动态html页面
        """
        _html = self.driver.page_source

        if self.common_options.get('debug_path', None) is not None:
            # 记录网页的信息
            _filename = '%s.html' % datetime.datetime.now().strftime('%Y_%m_%d_%H_%M_%S')
            self._save_file(
                os.path.join(self.para_dict['debug_path'], _filename),
                'URL: %s\n%s' % (self.driver.current_url, _html)
            )

        return _html

    def get_url_dom(self, url: str, common_options: dict = None, cookie: dict = None) -> str:
        """
        在当前窗口打开新url并获取动态html

        @param {str} url - 要打开的新url
        @param {dict} common_options=None - 要设置的加载参数，支持以下几个参数：
            wait_all_loaded {bool} True - 是否等待所有页面元素加载完
            roll_to_end {bool} False - 是否滚动到页面结尾(加载更多的情况), 必须跟until_menthod结合判断
            until_menthod {function} - 如果不等待所有页面加载完，判断函数，函数应返回True/False
            until_message {str} - 传入判断函数的信息
        @param {dict} cookie=None - 要设置的cookie字典

        @returns {str} - 页面加载后的动态html
        """
        # 处理参数
        _common_options = {
            'wait_all_loaded': True,
            'roll_to_end': False,
            'until_menthod': None,
            'until_message': ''
        }
        if common_options is not None:
            _common_options.update(common_options)

        self.common_options.update(_common_options)

        _html = self.get_web_page_dom(
            url, driver=self.driver, common_options=self.common_options,
            webdriver_type=self.webdriver_type, cookie=cookie
        )

        if self.common_options.get('debug_path', None) is not None:
            # 记录网页的信息
            _filename = '%s.html' % datetime.datetime.now().strftime('%Y_%m_%d_%H_%M_%S')
            self._save_file(
                os.path.join(self.para_dict['debug_path'], _filename),
                'URL: %s\n%s' % (self.driver.current_url, _html)
            )

        return _html

    def get_cookies(self) -> dict:
        """
        获取当前页面的cookie字典

        @returns {dict} - cookie字典
        """
        return self.driver.get_cookies()

    #############################
    # iframe操作处理
    #############################

    def switch_to_frame(self, iframe: WebElement):
        """
        将浏览器当前上下文跳转到iframe元素上
        注：如果不进行跳转，外层元素无法直接访问iframe元素的内容

        @param {WebElement} iframe - 要跳转到的iframe元素对象
        """
        self.driver.switch_to.frame(iframe)

    def switch_to_parent_frame(self):
        """
        将浏览器当前上下文跳转到当前iframe的上级
        """
        self.driver.switch_to.parent_frame()

    def switch_to_default_frame(self):
        """
        将浏览器当前上下文跳转到最外层的页面
        """
        self.driver.switch_to.default_content()

    #############################
    # 查找元素
    #############################
    def find_elements(self, steps: list, parent: WebElement = None) -> list:
        """
        按步骤逐级查询对象

        @param {list} steps - 要查询的步骤列表，每一个步骤为一个操作列表，第0个为操作类型，后面为操作参数
            [
                ['pos': 0],  # 获取当前清单中指定位置的元素
                ['children'],  # 获取当前清单元素中的所有子元素
                ['id', 'myId'],  # 通过id获取元素
                ['xpath', '//img[@id="dracga" and @style]'],  # 通过xpaht获取元素
                ['name', 'myName'],  # 通过元素的name属性获取
                ['tag_name', 'img'],  # 通过元素的标签名获取
                ['class_name', 'styleClass'],  # 通过元素的class名获取
                ['css_selector', '#kw'],  # 通过css选择器方式获取，id用#kw, class用.s_ipt, 与css的简写方式相同
                ['link_text', 'hao123'],  # 通过超文本链接上的文字信息来定位元素
                ['partial_link_text', 'hao']  # 通过超文本连接上的文字的一部分关键字信息来定位元素
            ]
        @param {WebElement} parent=None - 开始的父节点，如果不传代表重新开始

        @returns {list} - 返回查找到的对象列表
            注：对象类型为selenium.webdriver.remote.webelement.WebElement
        """
        # 查找第一个步骤
        _elements = self._find_elements_step(steps[0], parent=parent)

        # 循环处理后面每个步骤(从第2个开始)
        for _i in range(1, len(steps)):
            if len(_elements) == 0:
                # 没有找到任何元素，直接退出循环
                break

            # 执行子元素的查找处理
            _step = steps[_i]
            _op = _step[0]
            _new_elements = list()
            if _op == 'pos':
                # 获取当前列表中指定位置的元素
                _new_elements.append(_elements[_step[1]])
            else:
                # 遍历每个元素进行查找
                for _element in _elements:
                    _new_elements.extend(
                        self._find_elements_step(_step, parent=_element)
                    )

            # 更新清单
            _elements = _new_elements

        # 返回结果
        return _elements

    #############################
    # 执行元素操作
    #############################
    def do_script(self, steps: list, parent: WebElement = None) -> list:
        """
        按步骤对元素执行操作

        @param {list} steps - 要执行步骤数组
            [
                ['save_els', 'var_name'],  # 将当前元素存入指定名称的临时变量
                ['set_els', 'var_name'],  # 将临时变量的元素恢复到当前元素清单
                ['wait', '0.1'],  # 等待指定的秒数
                ['open_window', 'chrome://downloads/'],  # 打开新标签页，参数为要打开的页面url
                ['close_window', 'int/str'],  # 关闭指定页签，如果不传值代表关闭当前页签
                    # 如果第一个参数为int类型，代表关闭指定位置的页签
                    # 如果第一个参数为str类型，代表关闭title为送入参数的页签
                ['switch_to', 'frame/parent_frame/default/alert/window', ...],  # 切换浏览器页面
                    # frame-切换到当前元素清单第1个的frame中，parent_frame-切换到父页面，default-切换到最外层页面
                    # alert-切换到浏览器弹出框，后续可以带对弹出框的操作: 'accept'-点击确认按钮，'dismiss'-点击取消按钮
                    # window-切换到指定页签，后续第一个参数如果为数字，代表切换到指定位置的窗口(开始为0，可以用-1指示最后一个)
                    #   后续第一个参数如果为文本，代表通过窗口标题来获取对应的窗口
                ['scroll_into_view'],  # 将当前元素滚动到可视范围
                ['run_script', 'window.alert(\'这是一个测试Alert弹窗\');']  # 执行js脚本
                ['find', op, para1, ...] # 忽略此前步骤查找到的元素，重新全局搜索元素并设置为当前元素, 数组后面为查找指令和对应的参数，参考find_elements
                ['find_child', op, para1, ...] # 搜索此前元素的子元素并设置为当前元素，数组后面为查找指令和对应的参数，参考find_elements
                ['click'] # 点击元素
                ['send_str', '要输入的文本'] # 元素输入文本
                ['send_keys', 'Keys.CONTROL', 'Keys.SHIFT', 'a', ...]  # 输入按键，传入多个代表同时按下
                    # 特殊按键定义参考 selenium.webdriver.common.keys.Keys
            ]
        @param {WebElement} parent=None - 执行的对象（如果步骤中有查找，则会根据查找情况逐步改变执行对象的值）

        @returns {list} - 返回最后的元素列表
        """
        _var_cache = dict()  # 保存元素的临时变量
        _elements = [parent, ]
        # 循环执行
        for _step in steps:
            _new_elements = list()
            _action = _step[0]
            if _action == 'save_els':
                # 保存当前元素
                _var_cache[_step[1]] = _elements
                continue
            elif _action == 'set_els':
                # 取出保存的元素
                _elements = _var_cache[_step[1]]
                continue
            elif _action == 'wait':
                time.sleep(float(_step[1]))
                continue
            elif _action == 'open_window':
                # 打开新标签页，因为chrome有组合键无效的bug，换成用js代码打开
                _js = 'window.open("%s");' % _step[1]
                self.driver.execute_script(_js)
                # 跳转过去并打开新内容(最后一个窗口)
                self.driver.switch_to_window(self.driver.window_handles[-1])
                self.driver.get(_step[1])
                continue
            elif _action == 'close_window':
                # 关闭页签
                _current_handle = self.driver.current_window_handle
                if len(_step) > 1:
                    _index = _step[1]
                    if type(_index) != int:
                        for _handle in self.driver.window_handles:
                            self.driver.switch_to_window(_handle)
                            if self.driver.title == _index:
                                _find_handle = True

                        # 如果没有找到，切换回原来的的窗口, 然后抛出异常
                        if not _find_handle:
                            self.driver.switch_to_window(_current_handle)
                            raise KeyError('window with title [%s] is not found' % _index)
                    else:
                        self.driver.switch_to_window(self.driver.window_handles[_index])

                # 关闭当前页签
                self.driver.close()
                continue
            elif _action == 'switch_to':
                # 切换浏览器
                _op = _step[1]
                if _op == 'frame':
                    self.switch_to_frame(_elements[0])
                elif _op == 'parent_frame':
                    self.switch_to_parent_frame()
                elif _op == 'default':
                    self.switch_to_default_frame()
                elif _op == 'alert':
                    # 切换到弹出框
                    _alert = self.driver.switch_to_alert()
                    _alert_op = _step[2]
                    if _alert_op == 'accept':
                        _alert.accept()
                    elif _alert_op == 'dismiss':
                        _alert.dismiss()
                elif _op == 'window':
                    # 切换到窗口
                    _index = _step[2]
                    if type(_index) != int:
                        _current_handle = self.driver.current_window_handle
                        _find_handle = False
                        for _handle in self.driver.window_handles:
                            self.driver.switch_to_window(_handle)
                            if self.driver.title == _index:
                                _find_handle = True
                                break

                        # 如果没有找到，切换回原来的的窗口, 然后抛出异常
                        if not _find_handle:
                            self.driver.switch_to_window(_current_handle)
                            raise KeyError('window with title [%s] is not found' % _index)
                    else:
                        self.driver.switch_to_window(self.driver.window_handles[_index])
                else:
                    raise KeyError('not support switch_to operator [%s]' % _op)
                continue
            elif _action == 'scroll_into_view':
                # 滚动到显示范围
                _js = 'arguments[0].scrollIntoView();'
                for _el in _elements:
                    self.driver.execute_script(_js, _el)
                continue
            elif _action == 'run_script':
                # 运行js脚本
                self.driver.execute_script(_step[1])
                continue
            else:
                # 遍历执行当前操作
                for _el in _elements:
                    _new_elements.extend(self._do_script_step(
                        _step, parent=_el
                    ))

                # 更新当前元素列表
                _elements = _new_elements

        # 返回最后的元素列表
        if len(_elements) == 1 and _elements[0] is None:
            return []
        else:
            return _elements

    #############################
    # 内部函数
    #############################
    def _find_elements_step(self, step: list, parent: WebElement = None) -> list:
        """
        单步查找元素

        @param {list} step - 执行步骤参数，参数数组中的第0个是查找指令，其他数组对象是查找参数
            ['children']  # 获取当前清单元素中的所有子元素
            ['id', 'myId']  # 通过id获取元素
            ['xpath', '//img[@id="dracga" and @style]']  # 通过xpaht获取元素
            ['name', 'myName']  # 通过元素的name属性获取
            ['tag_name', 'img']  # 通过元素的标签名获取
            ['class_name', 'styleClass']  # 通过元素的class名获取
            ['css_selector', '#kw']  # 通过css选择器方式获取，id用#kw, class用.s_ipt, 与css的简写方式相同
            ['link_text', 'hao123']  # 通过超文本链接上的文字信息来定位元素
            ['partial_link_text', 'hao']  # 通过超文本连接上的文字的一部分关键字信息来定位元素
        @param {WebElement} parent=None - 父节点，如果不传代表全局搜索

        @returns {list} - 返回查找到的元素清单
            注：对象类型为selenium.webdriver.remote.webelement.WebElement
        """
        # 处理父节点
        _parent = parent  # 有父节点，通过元素方式向下查找
        if _parent is None:
            # 没有父节点，通过webdriver查找全局
            _parent = self.driver

        # 处理查找操作
        _elements = list()
        _op = step[0]  # 查找指令
        if _op == 'children':
            # 获取所有子元素
            _elements = _parent.find_elements_by_xpath('.//*')
        elif _op in self._by_mapping.keys():
            # 标准的By查找模式
            _elements = _parent.find_elements(by=self._by_mapping[_op], value=step[1])
        else:
            # 没有匹配到类型
            raise KeyError('not support find elements operator [%s]' % _op)

        return _elements

    def _do_script_step(self, step: list, parent: WebElement = None) -> list:
        """
        单步执行操作

        @param {list} step - 要执行操作的步骤参数
            ['find', op, para1, ...] # 忽略此前步骤查找到的元素，重新全局搜索元素并设置为当前元素, 数组后面为查找指令和对应的参数，参考find_elements
            ['find_child', op, para1, ...] # 搜索此前元素的子元素并设置为当前元素，数组后面为查找指令和对应的参数，参考find_elements
            ['click'] # 点击元素
            ['send_str', '要输入的文本'] # 元素输入文本
            ['send_keys', 'Keys.CONTROL', 'Keys.SHIFT', 'a', ...]  # 输入按键，传入多个代表同时按下
                # 特殊按键定义参考 selenium.webdriver.common.keys.Keys
        @param {WebElement} parent=None - 父节点，如果不传代表全局搜索

        @returns {list} - 如果是执行操作，直接返回包含parent的数组；如果是查询操作，返回查询到的元素清单
        """
        _elements = [parent, ]
        _op = step[0]
        if _op == 'find':
            # 忽略此前步骤查找到的元素，重新全局搜索元素并设置为当前元素
            return self.find_elements([step[1:]], parent=None)
        elif _op == 'find_child':
            return self.find_elements([step[1:]], parent=parent)
        elif _op == 'click':
            parent.click()
        elif _op == 'send_str':
            parent.send_keys(step[1])
        elif _op == 'send_keys':
            # 输入快捷键
            _keys = [eval(_key) if _key.startswith('Keys.') else _key for _key in step[1:]]
            parent.send_keys(*_keys)

        return _elements

    @classmethod
    def _set_common_options_default(cls, common_options: dict = None) -> dict:
        """
        设置common_options的默认值

        @param {dict} common_options=None - 要设置默认值的参数

        @returns {dict} - 返回设置完成默认值的字典
        """
        _common_options = {
            'headless': True,
            'feign_browser': False,
            'lang': 'zh-CN',
            'disable_security': False,
            'no_image': False,
            'no_css': False,
            'wait_all_loaded': True,
            'session_id': '',
            'executor_url': '',
            'size_type': '',
            'width': '800',
            'height': '600',
            'set_pos': False,
            'pos_x': '0',
            'pos_y': '0',
            'timeout': 10,
            'roll_to_end': False,
            'until_menthod': None,
            'until_message': '',
            'quit': True
        }
        if common_options is not None:
            _common_options.update(common_options)

        return _common_options

    @classmethod
    def _set_driver_pos(cls, driver, common_options: dict):
        """
        设置浏览器大小和位置

        @param {WebDriver} driver - 浏览器对象
        @param {dict} common_options - 要设置的参数
        """
        # 设置浏览器大小和位置
        if common_options['size_type'] == 'max':
            driver.maximize_window()
        elif common_options['size_type'] == 'min':
            driver.minimize_window()
        elif common_options['size_type'] == 'size':
            driver.set_window_size(
                int(common_options['width']), int(common_options['height'])
            )

        if common_options['set_pos']:
            driver.set_window_position(
                int(common_options['pos_x']), int(common_options['pos_y'])
            )

    @classmethod
    def _save_file(cls, file: str, content: str, encoding: str = 'utf-8'):
        """
        保存错误文件

        @param {str} file - 要保存的文件路径
        @param {str} content - 要保存的内容
        @param {str} encoding='utf-8' - 文件编码
        """
        with open(file, 'w', encoding=encoding) as f:
            f.write(content)


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    # 打印版本信息
    print(('模块名：%s  -  %s\n'
           '作者：%s\n'
           '发布日期：%s\n'
           '版本：%s' % (__MOUDLE__, __DESCRIPT__, __AUTHOR__, __PUBLISH__, __VERSION__)))

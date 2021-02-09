#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
# Copyright 2019 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
restful api 鉴权模块

@module auth
@file auth.py
"""

import os
import sys
import json
import copy
import datetime
import re
from functools import wraps
# 根据当前文件路径将包路径纳入，在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir, os.path.pardir)))
# 动态安装包
import HiveNetLib.deps_tool as deps_tool
process_install_flask = False
while True:
    try:
        from flask import Flask, request, jsonify
        from flask.wrappers import Response
        from flask_httpauth import HTTPTokenAuth
        from werkzeug.routing import Rule
        from flask_cors import CORS
        break
    except ImportError:
        if not process_install_flask:
            deps_tool.install_package('flask')
            deps_tool.install_package('flask-cors')
            deps_tool.install_package('flask-restful')
            deps_tool.install_package('flask-httpauth')
            deps_tool.install_package('werkzeug')
            process_install_flask = True
            continue
        raise
# 自有包引用
from HiveNetLib.base_tools.string_tool import StringTool
from HiveNetLib.simple_restful.cryptography import HCrypto


__MOUDLE__ = 'auth'  # 模块名
__DESCRIPT__ = u'restful api 鉴权模块'  # 模块描述
__VERSION__ = '0.1.0'  # 版本
__AUTHOR__ = u'黎慧剑'  # 作者
__PUBLISH__ = '2020.12.03'  # 发布日期


"""
网页JS调用Restful API鉴权流程
整体流程：浏览器提交请求至Web服务器(https) -> Web服务器作为调用方，执行Restful API鉴权流程
"""


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
        _ip = request.remote_addr

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
                    _resp_msg[self.interface_id_name] = request.json[self.interface_id_name]

                # 转换json字符串
                _resp_msg = jsonify(_resp_msg)

            # 标准反馈
            _ret = (_resp_msg, _status)
        else:
            # 验证通过，执行函数
            _ret = f(*args, **kwargs)
            if type(_ret) not in (tuple, list):
                _ret = (_ret, 200)

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


class AppKeyAuth(object):
    """
    AppKey模式验证模块
    整体流程: 调用方对请求报文签名 -> 服务方验证请求签名 -> 服务方处理并对返回报文签名 -> 调用方验证返回报文签名
    详细说明如下:
        1. 服务端生成APP信息，线下提供给商户
            AppId: 商户id
            AppKey: 公匙（相当于账号）
            AppSecret: 私匙（相当于密码）
        2. 客户端对要发送的数据进行签名，算法如下:
        (1) 客户端生成 nonce_str 随机字符串, 例如: 'ibuaiVcKdpRxkhJA'
        (2) 设要发送的数据为集合M，将所有非空参数值的参数按照参数名ASCII码从小到大排序（字典序），
        使用URL键值对的格式（即key1=value1&key2=value2…）拼接成字符串stringA, 例如:
            stringA="body=test&device_info=1000&mch_id=10000100"
        (3) 拼接API密钥
            # 拼接app_id、app_key、app_secret、nonce_str、timestamp进入签名字符串
            stringSignTemp=stringA+"&app_id=1333&app_key=123456&app_secret=192006250b4c09247ec02edce69f6a2d&nonce_str=xx&timestamp=xx"
            # 如果选择MD5签名方式, 处理及得到结果如下
            sign=MD5(stringSignTemp).toUpperCase()="9A0A8659F005D6984697E2CA0A9CF3B7"
            # 如果选择HMAC-SHA256算法签名方式，处理及得到结果如下
            # 注意：部分语言的hmac方法生成结果二进制结果，需要调对应函数转化为十六进制字符串。
            sign=hash_hmac("sha256",stringSignTemp,AppSecret).toUpperCase()="6A9AE1657590FD6257D693A078E1C3E4BB6BA4DC30B23E0EE2496E54170DACD6"
        (4) 将sign放入要发送的数据集合中，客户端调用api接口
        (5) 服务器端同样做相应的认证检查
    """

    #############################
    # 构造函数
    #############################
    def __init__(self, **kwargs):
        """
        AppKey模式验证模块

        @param {fuction} get_secret_fun - 取 (app_key, app_secret) 密钥对的函数, 默认使用当前类的自有AppKey管理工具函数
            fun(app_id:str) -> tuple
        @param {bool} sign_resp=False - 是否对返回的报文进行签名
        @param {str} interface_id_name='' - 接口id的参数名，如果为''则代表返回错误时不需要返回请求接口id
        @param {int} sign_error_resp_status=403 - 签名验证失败返回状态码
        @param {str|dict} sign_error_resp_msg={'status': '13007', 'msg':'签名检查失败'} - 签名验证失败返回的信息
        @param {float} timestamp_expired_time=300.0 - 允许服务器时间差异时长，单位为秒，默认5分钟
        @param {int} timestamp_error_resp_status=403 - timestamp已过期时返回状态码
        @param {str|dict} timestamp_error_resp_msg={'status': '13008', 'msg':'时间戳已过期'} - timestamp已过期返回的信息
        @param {int} nonce_len=8 - nonce字符串的长度
        @param {str} timestamp_fmt='%Y%m%d%H%M%S' - timestamp的格式
        @param {str} encoding='utf-8' - 对中文内容的转换编码
        @param {str} algorithm='MD5' - 使用的签名算法名，支持算法如下
            MD5
            HMAC-SHA256
        @param {dict} algorithm_extend=None - 扩展算法支持, key为algorithm名, value为扩展的算法函数
            扩展函数定义如下: fun(value:str, key:str) -> str
        """
        self.para = kwargs
        self.get_secret_fun = self.para.get('get_secret_fun', self.apk_get_secret_fun)
        self.sign_resp = self.para.get('sign_resp', False)
        self.interface_id_name = self.para.get('interface_id_name', '')
        self.sign_error_resp_status = self.para.get('sign_error_resp_status', 403)
        self.sign_error_resp_msg = self.para.get(
            'sign_error_resp_msg', {'status': '13007', 'msg': '签名检查失败'}
        )
        self.timestamp_expired_time = self.para.get('timestamp_expired_time', 300.0)
        self.timestamp_error_resp_status = self.para.get('timestamp_error_resp_status', 403)
        self.timestamp_error_resp_msg = self.para.get(
            'timestamp_error_resp_msg', {'status': '13008', 'msg': '时间戳已过期'}
        )
        self.timestamp_fmt = self.para.get('timestamp_fmt', '%Y%m%d%H%M%S')
        self.encoding = self.para.get('encoding', 'utf-8')

        # 算法扩展支持
        self.algorithm_mapping = {
            'MD5': HCrypto.md5,
            'HMAC-SHA256': HCrypto.hmac_sha256
        }
        self.algorithm_mapping.update(self.para.get('algorithm_extend', {}))
        self.algorithm = self.para.get('algorithm', 'MD5')

        # 简易的AppKey管理台, 内存字典管理，key为app_id, value为(app_key, app_secret) 键值对
        self._app_key_manager = dict()

    #############################
    # 增加签名验证的修饰符
    #############################
    def auth_required(self, f=None):
        """
        需要签名验证的情况下使用的修饰符

        @param {function} f=None - 所执行的函数
        """
        def auth_required_internal(f):
            @wraps(f)
            def decorated(*args, **kwargs):
                return self.auth_required_call(f, *args, **kwargs)
            return decorated

        if f:
            return auth_required_internal(f)
        return auth_required_internal

    def auth_required_call(self, f, *args, **kwargs):
        """
        供其他修饰符函数直接调用的处理函数

        @param {function} f - 要执行的函数
        @param {args} - 执行函数的固定入参
        @param {kwargs} - 执行函数的kv入参
        """
        # 进行时间判断及签名认证
        _status = 200
        _resp_msg = ''
        _json_dict = request.json
        if not self.verify_timestamp(_json_dict):
            # 日期验证失败
            _status = self.timestamp_error_resp_status
            _resp_msg = copy.deepcopy(self.timestamp_error_resp_msg)
        elif not self.verify_sign(_json_dict):
            # 验证失败, 返回标准的错误信息
            _status = self.sign_error_resp_status
            _resp_msg = copy.deepcopy(self.sign_error_resp_msg)

        if _status != 200:
            # 验证失败
            if type(_resp_msg) == dict:
                if self.interface_id_name != '':
                    # 增加返回的接口id
                    _resp_msg[self.interface_id_name] = _json_dict[self.interface_id_name]

                # 转换为字符串格式
                _resp_msg = jsonify(_resp_msg)

            # 直接返回结果
            _ret = (_resp_msg, _status)
        else:
            # 执行函数
            _ret = f(*args, **kwargs)
            if type(_ret) not in (tuple, list):
                # 转换为标准模式
                _ret = (_ret, 200)

        # 看是否对返回结果签名, 由于有可能返回的是字符串，需要转换处理
        if self.sign_resp:
            _temp_msg = _ret[0]
            _type = type(_temp_msg)
            if _type != dict:
                # 尝试转换为dict处理
                try:
                    if _type == Response:
                        _enconding = 'utf-8' if _temp_msg.charset == '' else _temp_msg.charset
                        _temp_msg = json.loads(str(_temp_msg.data, encoding=_enconding))
                    else:
                        _temp_msg = json.loads(_temp_msg)
                except:
                    pass

            if type(_temp_msg) == dict:
                _temp_msg['app_id'] = _json_dict['app_id']
                _ret = (
                    jsonify(self.sign(_temp_msg)), _ret[1]
                )

        # 返回处理结果
        return _ret

    #############################
    # 签名工具
    #############################
    def get_signature(self, msg: dict, app_key: str, app_secret: str, algorithm: str = None) -> str:
        """
        对消息字典进行签名

        @param {dict} msg - 要签名的字典
        @param {str} app_key - 商户持有的app_key（相当于公钥）
        @param {str} app_secret - 商户持有的AppSecret私匙（相当于密码）
        @param {str} algorithm=None - 使用的签名算法名，如果不传使用初始化类的指定算法, 支持算法如下
            MD5
            HMAC-SHA256
        @returns {str} - 返回签名验证字符串
        """
        # 必须要有的参数
        _app_id = msg['app_id']
        _nonce_str = msg['nonce_str']
        _timestamp = msg['timestamp']

        # 参数清单组合, 按参数名排序, 去掉非空值, URL键值对方式组合
        _para_list = list(msg.keys())
        _para_list.sort()
        _str_sign_temp = ''
        for _para in _para_list:
            if _para not in ('app_id', 'nonce_str', 'timestamp', 'sign') and msg[_para] not in (None, ''):
                _value = msg[_para]
                if type(_value) != str:
                    _value = json.dumps(_value, ensure_ascii=False, sort_keys=True)

                _str_sign_temp = '%s%s=%s&' % (
                    _str_sign_temp, _para, _value
                )

        # 增加app_id、app_key、app_secret, nonce_str、timestamp到键值对中
        _str_sign_temp = '%sapp_id=%s&app_key=%s&app_secret=%s&nonce_str=%s&timestamp=%s' % (
            _str_sign_temp, _app_id, app_key, app_secret, _nonce_str, _timestamp
        )

        # 进行加密处理并返回签名串
        _algorithm = self.algorithm if algorithm is None else algorithm
        return self.algorithm_mapping[_algorithm](
            _str_sign_temp, key=app_secret, encoding=self.encoding
        )

    def sign(self, msg: dict) -> dict:
        """
        对报文消息字典进行签名

        @param {dict} msg - 要签名的报文字典

        @returns {dict} - 签名后的报文字典
        """
        _app_id = msg['app_id']
        msg['nonce_str'] = HCrypto.generate_nonce(self.para.get('nonce_len', 8))  # 随机字符串
        msg['timestamp'] = datetime.datetime.now().strftime(self.timestamp_fmt)  # 时间戳
        _sign_type = msg.get('sign_type', self.algorithm)  # 签名类型，如果有送值代表指定算法
        _app_key, _app_secret = self.get_secret_fun(_app_id)  # 通过指定的算法获取
        msg['sign'] = self.get_signature(msg, _app_key, _app_secret, algorithm=_sign_type)

        return msg

    def verify_sign(self, msg: dict) -> bool:
        """
        验证报文签名是否准确

        @param {dict} msg - 要验证的报文字典

        @returns {bool} - 报文验证结果
        """
        try:
            _app_id = msg['app_id']
            _sign_type = msg.get('sign_type', self.algorithm)  # 签名类型，如果有送值代表指定算法
            _app_key, _app_secret = self.get_secret_fun(_app_id)  # 通过指定的算法获取
            _sign = self.get_signature(msg, _app_key, _app_secret, algorithm=_sign_type)
            return _sign == msg['sign']
        except:
            return False

    def verify_timestamp(self, msg: dict) -> bool:
        """
        验证时间戳是否已过期

        @param {dict} msg - 要验证的报文字典

        @returns {bool} - 验证结果
        """
        try:
            _timestamp = datetime.datetime.strptime(msg['timestamp'], self.timestamp_fmt)
            if abs((datetime.datetime.now() - _timestamp).total_seconds()) > self.timestamp_expired_time:
                return False
            return True
        except:
            return False

    #############################
    # 简易AppKey管理台工具
    #############################
    def apk_get_secret_fun(self, app_id: str) -> tuple:
        """
        自有AppKey管理工具(无安全控制)的取密钥对函数

        @param {str} app_id - 要获取的app_id

        @returns {tuple} - (app_key, app_secret) 密钥对
        """
        return self._app_key_manager[app_id]

    def apk_update_secret(self, app_id: str, key_pair: tuple):
        """
        自有AppKey管理工具的密钥对更新

        @param {str} app_id - 要更新的app_id
        @param {tuple} key_pair - (app_key, app_secret) 密钥对
        """
        self._app_key_manager[app_id] = key_pair

    def apk_generate_key_pair(self, app_id: str) -> tuple:
        """
        自有AppKey管理工具的生成新密钥对函数(同时可以加入管理工具)

        @param {str} app_id - 要获取的app_id

        @returns {tuple} - (app_key, app_secret) 密钥对
        """
        # 随机生成字符串, app_key 8位, app_secret 32位
        _app_key = StringTool.get_random_str(random_length=8)
        _app_secret = StringTool.get_random_str(random_length=32)
        self._app_key_manager[app_id] = (_app_key, _app_secret)

        return (_app_key, _app_secret)


class TokenAuth(object):
    """
    通过登陆验证后通过JWT形式的Tocken处理验证模块, 适合Web网形式的验证


    通过Token验证流程如下:
        1. 客户端生成 nonce_str 随机字符串, 例如: 'ibuaiVcKdpRxkhJA'
        2. 设要发送的数据为集合M，将所有非空参数值的参数按照参数名ASCII码从小到大排序（字典序），
            使用URL键值对的格式（即key1=value1&key2=value2…）拼接成字符串stringA, 例如:
            stringA="body=test&device_info=1000&mch_id=10000100"
        3. 拼接验证字符串
            # 拼接user_name、token、nonce_str、timestamp进入签名字符串
            stringSignTemp=stringA+"&user_name=1333&app_key=123456&token=192006250b4c09247ec02edce69f6a2d&nonce_str=xx&timestamp=xx"
            # 如果选择MD5签名方式, 处理及得到结果如下
            sign=MD5(stringSignTemp).toUpperCase()="9A0A8659F005D6984697E2CA0A9CF3B7"
            # 如果选择HMAC-SHA256算法签名方式，处理及得到结果如下
            sign=hash_hmac("sha256",stringSignTemp,AppSecret).toUpperCase()="6A9AE1657590FD6257D693A078E1C3E4BB6BA4DC30B23E0EE2496E54170DACD6"
        4. 将验证字符串sign放入请求的header中: Authorization: 'JWT ' + sign
    """

    #############################
    # 构造函数
    #############################
    def __init__(self, **kwargs):
        """
        通过登陆验证后通过JWT形式的Tocken处理验证模块

        @param {fuction} get_secret_fun - 取 (app_key, app_secret) 密钥对的函数, 默认使用当前类的自有AppKey管理工具函数
            fun(app_id:str) -> tuple
        @param {bool} sign_resp=False - 是否对返回的报文进行签名
        @param {str} interface_id_name='' - 接口id的参数名，如果为''则代表返回错误时不需要返回请求接口id
        @param {int} sign_error_resp_status=403 - 签名验证失败返回状态码
        @param {str|dict} sign_error_resp_msg={'status': '13007', 'msg':'签名检查失败'} - 签名验证失败返回的信息
        @param {float} timestamp_expired_time=300.0 - 允许服务器时间差异时长，单位为秒，默认5分钟
        @param {int} timestamp_error_resp_status=403 - timestamp已过期时返回状态码
        @param {str|dict} timestamp_error_resp_msg={'status': '13008', 'msg':'时间戳已过期'} - timestamp已过期返回的信息
        @param {int} nonce_len=8 - nonce字符串的长度
        @param {str} timestamp_fmt='%Y%m%d%H%M%S' - timestamp的格式
        @param {str} encoding='utf-8' - 对中文内容的转换编码
        @param {str} algorithm='MD5' - 使用的签名算法名，支持算法如下
            MD5
            HMAC-SHA256
        @param {dict} algorithm_extend=None - 扩展算法支持, key为algorithm名, value为扩展的算法函数
            扩展函数定义如下: fun(value:str, key:str) -> str
        """
        self.para = kwargs
        self.get_secret_fun = self.para.get('get_secret_fun', self.apk_get_secret_fun)
        self.sign_resp = self.para.get('sign_resp', False)
        self.interface_id_name = self.para.get('interface_id_name', '')
        self.sign_error_resp_status = self.para.get('sign_error_resp_status', 403)
        self.sign_error_resp_msg = self.para.get(
            'sign_error_resp_msg', {'status': '13007', 'msg': '签名检查失败'}
        )
        self.timestamp_expired_time = self.para.get('timestamp_expired_time', 300.0)
        self.timestamp_error_resp_status = self.para.get('timestamp_error_resp_status', 403)
        self.timestamp_error_resp_msg = self.para.get(
            'timestamp_error_resp_msg', {'status': '13008', 'msg': '时间戳已过期'}
        )
        self.timestamp_fmt = self.para.get('timestamp_fmt', '%Y%m%d%H%M%S')
        self.encoding = self.para.get('encoding', 'utf-8')

        # 算法扩展支持
        self.algorithm_mapping = {
            'MD5': self.md5,
            'HMAC-SHA256': self.hmac_sha256
        }
        self.algorithm_mapping.update(self.para.get('algorithm_extend', {}))
        self.algorithm = self.para.get('algorithm', 'MD5')

        # 简易的AppKey管理台, 内存字典管理，key为app_id, value为(app_key, app_secret) 键值对
        self._app_key_manager = dict()


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    # 打印版本信息
    print(('模块名：%s  -  %s\n'
           '作者：%s\n'
           '发布日期：%s\n'
           '版本：%s' % (__MOUDLE__, __DESCRIPT__, __AUTHOR__, __PUBLISH__, __VERSION__)))

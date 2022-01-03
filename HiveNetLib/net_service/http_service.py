#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
#
# Copyright 2018 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
Http协议服务

@module http_service
@file http_service.py

"""

import os
import sys
import datetime
import copy
import traceback
import logging
# 根据当前文件路径将包路径纳入，在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir, os.path.pardir)))
from HiveNetLib.base_tools.run_tool import RunTool
from HiveNetLib.simple_i18n import _, SimpleI18N
from HiveNetLib.simple_server_fw import EnumServerRunStatus
from HiveNetLib.net_service.tcpip_service import TcpIpService
from HiveNetLib.generic import NullObj, CResult
from HiveNetLib.base_tools.exception_tool import ExceptionTool
from HiveNetLib.interface_tool.msg_fw import EnumMsgObjType, EnumMsgSRType
from HiveNetLib.interface_tool.protocol_msg_http import MsgHTTP


__MOUDLE__ = 'http_service'  # 模块名
__DESCRIPT__ = u'Http协议服务'  # 模块描述
__VERSION__ = '0.1.0'  # 版本
__AUTHOR__ = u'黎慧剑'  # 作者
__PUBLISH__ = '2018.09.14'  # 发布日期


class HttpService(TcpIpService):
    """
    Http协议服务
    基于NetServiceFW框架，继承TcpIpService

    @param {Logger} logger=None - 日志对象，服务过程中通过该函数写日志:
        可以为标准的logging日志库对象，也可以为simple_log对象，但要求对象实现:
        标准的info、debug、warning、error、critical五个日志方法
    @param {function} server_status_info_fun=None - 外围传入的网络服务状态变更通知函数对象，当网络服务状态发生变更时通过:
        该函数通知调用方；形式为fun(server_status, result):
        其中server_status为服务器状态EnumServerRunStatus，
        result为CResult通用执行结果对象，自定义属性self_tag为发起方识别标识
    @param {function} server_connect_deal_fun=None - 外围传入的网络服务与客户端连接后对连接的处理线程函数对象，在该函数中:
        实现服务器端具体的通讯处理（如循环收报文、返回报文等）；
        形式为fun(thread_id, server_opts, net_info, self_tag):
            thread_id - 线程ID
            server_opts -服务的启动参数
            net_info - 具体实现的连接信息（例如Socket对象）
            self_tag - 用于发起端传入自身的识别标识
        需注意实现上应在每次循环时查询服务器关闭状态，如果判断到服务器已关闭，应结束处理.
    @param {string} self_tag='' - 自定义标识
    @param {int} log_level=logging.INFO - 处理中正常日志的输出登记级别，默认为INFO，如果不想输出过多日志可以设置为DEBUG
    @param {string} server_name='NetService' - 服务名，记录日志使用
    @param {bool} is_auto_load_i18n=True - 是否自动加载i18n字典，如果继承类有自己的字典，可以重载__init__函数实现装载
    @param {function} server_http_deal_fun=None - http服务数据处理函数，用于处理服务端收到的http数据:
        形式为：fun(net_info, proto_msg, msg)
            net_info : 连接信息，与TcpIpService的net_info定义一致
            proto_msg {MsgHTTP}  报文头对象
            msg {bytes} 报文体对象
        函数的返回结果为一个数组(is_close, msg, proto_msg)
            is_close : True/False - 处理完成是否关闭连接，以支持长连接情况
            msg {bytes} - 要返回的报文体，如果没有数据传None
            proto_msg {MsgHTTP} - 要返回的协议头，如果不返回传None
        注意：该参数传入代表使用服务自带的服务端监听处理线程函数，server_connect_deal_fun将失效
    @param {bool} is_print_msg_log=True - 是否打印报文日志，仅server_http_deal_fun传入时有效
    @param {string} default_data_encoding='utf-8' - 打印报文的默认字符集

    """
    #############################
    # 内部变量
    #############################
    _server_http_deal_fun = None  # http协议的处理函数
    _is_print_msg_log = True  # 是否打印报文日志
    _default_data_encoding = 'utf-8'  # 打印报文的默认字符集

    #############################
    # 重构构造函数
    #############################
    def __init__(self, logger=None, server_status_info_fun=None, server_connect_deal_fun=None, self_tag='',
                 log_level=logging.INFO, server_name='HttpService', is_auto_load_i18n=True,
                 server_http_deal_fun=None, is_print_msg_log=True, default_data_encoding='utf-8'):
        """
        构造函数

        @param {Logger} logger=None - 日志对象，服务过程中通过该函数写日志:
            可以为标准的logging日志库对象，也可以为simple_log对象，但要求对象实现:
            标准的info、debug、warning、error、critical五个日志方法
        @param {function} server_status_info_fun=None - 外围传入的网络服务状态变更通知函数对象，当网络服务状态发生变更时通过:
            该函数通知调用方；形式为fun(server_status, result):
            其中server_status为服务器状态EnumServerRunStatus，
            result为CResult通用执行结果对象，自定义属性self_tag为发起方识别标识
        @param {function} server_connect_deal_fun=None - 外围传入的网络服务与客户端连接后对连接的处理线程函数对象，在该函数中:
            实现服务器端具体的通讯处理（如循环收报文、返回报文等）；
            形式为fun(thread_id, server_opts, net_info, self_tag):
                thread_id - 线程ID
                server_opts -服务的启动参数
                net_info - 具体实现的连接信息（例如Socket对象）
                self_tag - 用于发起端传入自身的识别标识
            需注意实现上应在每次循环时查询服务器关闭状态，如果判断到服务器已关闭，应结束处理.
        @param {string} self_tag='' - 自定义标识
        @param {int} log_level=logging.INFO - 处理中正常日志的输出登记级别，默认为INFO，如果不想输出过多日志可以设置为DEBUG
        @param {string} server_name='NetService' - 服务名，记录日志使用
        @param {bool} is_auto_load_i18n=True - 是否自动加载i18n字典，如果继承类有自己的字典，可以重载__init__函数实现装载
        @param {function} server_http_deal_fun=None - http服务数据处理函数，用于处理服务端收到的http数据:
            形式为：fun(net_info, proto_msg, msg)
                net_info : 连接信息，与TcpIpService的net_info定义一致
                proto_msg {MsgHTTP}  报文头对象
                msg {bytes} 报文体对象
            函数的返回结果为一个数组(is_close, msg, proto_msg)
                is_close : True/False - 处理完成是否关闭连接，以支持长连接情况
                msg {bytes} - 要返回的报文体，如果没有数据传None
                proto_msg {MsgHTTP} - 要返回的协议头，如果不返回传None
            注意：该参数传入代表使用服务自带的服务端监听处理线程函数，server_connect_deal_fun将失效
        @param {bool} is_print_msg_log=True - 是否打印报文日志，仅server_http_deal_fun传入时有效
        @param {string} default_data_encoding='utf-8' - 打印报文的默认字符集

        """
        # 先调用父类的初始化函数
        self._server_http_deal_fun = server_http_deal_fun
        self._is_print_msg_log = is_print_msg_log
        self._default_data_encoding = default_data_encoding
        if server_http_deal_fun is None:
            TcpIpService.__init__(self, logger=logger, server_status_info_fun=server_status_info_fun, server_connect_deal_fun=server_connect_deal_fun, self_tag=self_tag,
                                  log_level=log_level, server_name=server_name, is_auto_load_i18n=is_auto_load_i18n)
        else:
            TcpIpService.__init__(self, logger=logger, server_status_info_fun=server_status_info_fun, server_connect_deal_fun=self.__server_connect_deal_fun_http, self_tag=self_tag,
                                  log_level=log_level, server_name=server_name, is_auto_load_i18n=is_auto_load_i18n)

    #############################
    # 补充的公开函数
    #############################
    @classmethod
    def recv_http_head(cls, net_info, recv_para={}):
        """
        获取http报文头对象

        @param {object} net_info -  要读取数据的网络信息对象
        @param {dict} recv_para - 获取参数，暂未使用

        @returns {CResult} - 数据获取结果:
            result.code ：'00000'-成功，'20403'-获取数据超时，其他为获取失败
            result.data ：获取到的数据对象，类型为MsgHTTP
            result.recv_time : datetime 实际开始接受数据时间

        """
        if type(recv_para) != dict:
            recv_para = {}
        _result = CResult('00000')
        _result.data = None
        _result.recv_time = datetime.datetime.now()
        _overtime = 10000
        if 'overtime' in recv_para.keys():
            # 外部有传入，优先使用该超时时间
            _overtime = recv_para['overtime']
        elif hasattr(net_info, 'recv_timeout'):
            # 如果net_info有超时的设置
            _overtime = net_info.recv_timeout
        _result.overtime = _overtime

        _recv_para = copy.deepcopy(recv_para)
        _recv_para['recv_len'] = 1

        with ExceptionTool.ignored_cresult(
            _result
        ):
            # 循环获取所有报文头内容
            _get_line_bytes = b''
            _last_is_ln = False  # 标记上一个字符是否回车换行
            while True:
                # 检查是否超时
                if (datetime.datetime.now() - _result.recv_time).total_seconds() * 1000 > _overtime:
                    # 已超时
                    _result.change_code(code='20403')
                    break

                _read_result = TcpIpService.recv_data(net_info, _recv_para)
                if not _read_result.is_success():
                    # 出现异常，直接返回失败
                    _read_result.data = None
                    _read_result.recv_time = _result.recv_time
                    return _read_result
                # 获取成功，判断是否回车换行
                _get_line_bytes = _get_line_bytes + _read_result.data
                if str(_read_result.data, "ascii") == "\n" and _last_is_ln:
                    # 已经连续遇到两次回车换行，说明报文头已收齐退出循环
                    break
                elif str(_read_result.data, "ascii") == "\n":
                    _last_is_ln = True
                    continue
                elif str(_read_result.data, "ascii") == "\r":
                    continue
                else:
                    # 其他字符，不是连续换行
                    _last_is_ln = False
                    continue
            # 取完报文头数据，转换为结构对象
            _result.data = MsgHTTP(_get_line_bytes, msg_id=None, obj_type=EnumMsgObjType.Bytes)
        return _result

    @classmethod
    def recv_http_body(cls, net_info, proto_msg, recv_para={}):
        """
        获取http报文体信息

        @param {object} net_info -  要读取数据的网络信息对象
        @param {MsgHTTP} proto_msg - http报文头
        @param {dict} recv_para - 获取参数，暂未使用

        @returns {CResult} - 数据获取结果:
            result.code ：'00000'-成功，'20403'-获取数据超时，其他为获取失败
            result.msg ：获取到的数据对象，类型为bytes
            result.recv_time : datetime 实际开始接受数据时间

        """
        if type(recv_para) != dict:
            recv_para = {}
        _recv_para = copy.deepcopy(recv_para)
        _result = CResult('00000')
        _result.data = None
        _result.recv_time = datetime.datetime.now()
        with ExceptionTool.ignored_cresult(
            _result
        ):
            _get_value = proto_msg.get_value(search_path='Content-Length')
            if _get_value is not None:
                _len = int(_get_value)
                _recv_para['recv_len'] = _len
                _recv_result = TcpIpService.recv_data(net_info, _recv_para)
                _result = _recv_result
        return _result

    @classmethod
    def recv_data(cls, net_info, recv_para={}):
        """
        从指定的网络连接中读取数据

        @param {object} net_info - 要读取数据的网络信息对象（例如socket对象）
        @param {dict} recv_para - 读取数据的参数(暂时无用)

        @returns {CResult} - 数据获取结果:
            result.code ：'00000'-成功，'20403'-获取数据超时，其他为获取失败
            result.data ：获取到的数据对象，为一个二元数组
                (proto_msg, msg) - MsgHTTP报文头，二进制报文数据
            result.recv_time : datetime 实际开始接受数据时间

        """
        # 子类必须定义该功能
        if type(recv_para) != dict:
            recv_para = {}
        _result = CResult('00000')
        _result.data = None
        _result.recv_time = datetime.datetime.now()
        with ExceptionTool.ignored_cresult(
            _result
        ):
            _head_result = cls.recv_http_head(net_info, recv_para)
            if not _head_result.is_success():
                return _head_result
            _proto_msg = _head_result.data

            _body_result = cls.recv_http_body(net_info, _proto_msg, recv_para)
            if not _body_result.is_success():
                return _body_result

            _result.data = (_proto_msg, _body_result.data)
        return _result

    @classmethod
    def send_data(cls, net_info, data, send_para={}):
        """
        向指定的网络连接发送数据

        @param {object} net_info - 要写入数据的网络信息对象（例如socket对象）
        @param {tuple} data - 要写入的数据对象，(proto_msg, msg)
            proto_msg : MsgHTTP报文头
            msg : 二进制数据
        @param {dict} send_para - 写入数据的参数

        @returns {CResult} - 发送结果:
            result.code ：'00000'-成功，'20404'-写入数据超时，其他为写入失败
            result.send_time : datetime 实际发送完成时间

        """
        # 子类必须定义该功能
        if type(send_para) != dict:
            send_para = {}
        _result = CResult('00000')
        _result.send_time = None
        with ExceptionTool.ignored_cresult(
            _result
        ):
            # 先要更新报文头的长度
            _len = 0
            if data[1] is not None:
                _len = len(data[1])
            data[0].set_value('Content-Length', str(_len))
            _send_result = TcpIpService.send_data(net_info, data[0].to_bytes(), send_para)
            if not _send_result.is_success():
                return _send_result
            if _len > 0:
                _send_result = TcpIpService.send_data(net_info, data[1], send_para)
                _result = _send_result
        return _result

    @classmethod
    def get_print_str(cls, proto_msg, msg):
        """
        获取报文打印字符串

        @param {MsgHTTP} proto_msg - http头对象
        @param {bytes} msg - 报文体

        @returns {string} - 打印字符串

        """
        _head_str = proto_msg.to_str()
        # 从报文头获取字符编码
        _encoding = cls._default_data_encoding
        # TODO({$AUTHOR$}): 方法不对，需要调整用法
        _get_value = proto_msg.get_value('Content-Type')
        if _get_value is not None:
            _content_type = _get_value.lower()
            _index = _content_type.rfind('charset=')
            if _index != -1:
                _encoding = _content_type[_index + 8]
        _body_str = ''
        if _encoding is not None and msg is not None:
            _body_str = msg.decode(_encoding)
        return _head_str + _body_str

    #############################
    # 内部函数
    #############################
    def __server_connect_deal_fun_http(self, thread_id, server_opts, net_info, self_tag):
        """
        Http服务自有的服务处理函数，当server_http_deal_fun被传入的时候使用

        @param {[type]} thread_id - 线程ID
        @param {[type]} server_opts - 服务的启动参数
        @param {[type]} net_info - 具体实现的连接信息（例如Socket对象）
        @param {[type]} self_tag - 用于发起端传入自身的识别标识

        """
        while True:
            # 判断是否要断开服务器
            if self.server_run_status != EnumServerRunStatus.Running:
                # 服务器状态不是运行，直接断开连接
                self._logger.log(
                    self._log_level,
                    '[LIS-HTTP][NAME:%s][IP:%s][PORT:%s]%s' % (
                        self_tag, str(net_info.raddr[0]), str(net_info.raddr[1]),
                        _('close remote connection because servie shutdown')
                    )
                )
                self.close_connect(net_info)
                return

            # 获取报文信息
            _result = self.recv_data(net_info, {})
            if not _result.is_success():
                self._logger.log(
                    logging.ERROR,
                    '[LIS-HTTP][NAME:%s][IP:%s][PORT:%s][EX:%s]%s: %s - %s\n%s' % (
                        self_tag, str(net_info.raddr[0]), str(net_info.raddr[1]),
                        str(type(_result.error)), _('recv data from remote error'),
                        _result.code, _result.msg, _result.trace_str
                    )
                )
                self.close_connect(net_info)
                return

            _proto_msg = _result.data[0]
            _msg = _result.data[1]

            # 写日志
            if self._is_print_msg_log:
                self._logger.log(
                    self._log_level,
                    '[INF-RECV][NAME:%s][IP:%s][PORT:%s]\n%s' % (
                        self_tag, str(net_info.raddr[0]), str(net_info.raddr[1]),
                        self.get_print_str(_proto_msg, _msg)
                    )
                )

            _is_close = True
            _rproto_msg = None
            _rmsg = None
            try:
                (_is_close, _rproto_msg, _rmsg) = self._server_http_deal_fun(net_info, _proto_msg, _msg)
            except Exception as e:
                self._logger.log(
                    logging.ERROR,
                    '[LIS-HTTP][NAME:%s][IP:%s][PORT:%s][EX:%s]%s\n%s' % (
                        self_tag, str(net_info.raddr[0]), str(net_info.raddr[1]),
                        str(type(e)), _('execute server_http_deal_fun error'),
                        traceback.format_exc()
                    )
                )
                # 组织一个异常的返回报文
                _rproto_msg = MsgHTTP('%s 500 Internal Server Error' % (_proto_msg.ver),
                                      obj_type=EnumMsgObjType.String)

            # 组织回包
            if _rproto_msg is not None:
                _result = self.send_data(net_info, (_rproto_msg, _rmsg), {})
                if not _result.is_success():
                    self._logger.log(
                        logging.ERROR,
                        '[LIS-HTTP][NAME:%s][IP:%s][PORT:%s][EX:%s]%s: %s - %s\n%s' % (
                            self_tag, str(net_info.raddr[0]), str(net_info.raddr[1]),
                            str(type(_result.error)), _('send data to remote error'),
                            _result.code, _result.msg, _result.trace_str
                        )
                    )
                    self.close_connect(net_info)
                    return
                # 写日志
                if self._is_print_msg_log:
                    self._logger.log(
                        self._log_level,
                        '[INF-RET][NAME:%s][IP:%s][PORT:%s]\n%s' % (
                            self_tag, str(net_info.raddr[0]), str(net_info.raddr[1]),
                            self.get_print_str(_rproto_msg, _rmsg)
                        )
                    )

            # 判断是否断开连接
            if _is_close:
                self.close_connect(net_info)
                return

            # 睡眠一下，继续处理下一个请求
            RunTool.sleep(0.001)


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    # 打印版本信息
    print(('模块名：%s  -  %s\n'
           '作者：%s\n'
           '发布日期：%s\n'
           '版本：%s' % (__MOUDLE__, __DESCRIPT__, __AUTHOR__, __PUBLISH__, __VERSION__)))

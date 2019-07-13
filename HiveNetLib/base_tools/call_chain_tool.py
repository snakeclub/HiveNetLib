#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
#
# Copyright 2018 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
调用链日志处理工具

@module call_chain_tool
@file call_chain_tool.py

"""

import os
import sys
import uuid
import datetime
import traceback
from queue import Full, Empty
# 根据当前文件路径将包路径纳入，在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir, os.path.pardir)))
from HiveNetLib.simple_log import EnumLogLevel
from HiveNetLib.base_tools.run_tool import RunTool
from HiveNetLib.base_tools.import_tool import ImportTool
from HiveNetLib.base_tools.string_tool import StringTool
from HiveNetLib.base_tools.exception_tool import ExceptionTool
from HiveNetLib.simple_parallel import ThreadParallel, ParallelPool
from HiveNetLib.interface_tool.msg_xml import MsgXML
from HiveNetLib.interface_tool.msg_fw import EnumMsgObjType


__MOUDLE__ = 'call_chain_tool'  # 模块名
__DESCRIPT__ = u'调用链日志处理工具'  # 模块描述
__VERSION__ = '0.1.0'  # 版本
__AUTHOR__ = u'黎慧剑'  # 作者
__PUBLISH__ = '2018.09.06'  # 发布日期


class CallChainTool(object):
    """
    调用链工具类

    """

    #############################
    # 实例化，异步接口调用链日志处理，简化接口调用链的处理
    #############################
    def __init__(self, log_queue, logger=None, auto_start=False, max_thread_num=1, is_use_global_logger=True,
                 log_level=EnumLogLevel.INFO):
        """
        构造函数，如果接口日志需要异步写（避免日志耗时），需实例化处理

        @param {QueueFw} log_queue - 需要放置日志的队列对象
        @param {object} logger=None - 日志对象
        @param {bool} auto_start=False - 是否自动启动日志记录处理
        @param {int} max_thread_num=1 - 日志处理线程数
        @param {bool} is_use_global_logger=True - 当logger=None时，是否使用全局logger对象
            注：通过RunTool.set_global_logger进行设置
        @param {EnumLogLevel} log_level=EnumLogLevel.INFO - 本地服务打印日志的级别

        """
        self._log_queue = log_queue
        self._max_thread_num = max_thread_num
        if max_thread_num < 1:
            self._max_thread_num = 1
        self._logger = logger
        if self._logger is None and is_use_global_logger:
            # 使用全局logger
            self._logger = RunTool.get_global_logger()
        if self._logger is not None:
            self._log_fun = {
                EnumLogLevel.INFO: self._logger.info,
                EnumLogLevel.DEBUG: self._logger.debug,
                EnumLogLevel.WARNING: self._logger.warning,
                EnumLogLevel.ERROR: self._logger.error,
                EnumLogLevel.CRITICAL: self._logger.critical
            }
        self._log_level = log_level

        # 创建线程池进行处理
        self._pool = ParallelPool(
            deal_fun=self._api_chall_chain_logging_threadfun,
            pname='CallChainTool_Logger_ThreadPool',
            logger=self._logger,
            auto_start=auto_start,
            task_queue=self._log_queue,
            maxsize=self._max_thread_num, minsize=1, worker_release_time=60, worker_overtime=60,
            force_kill_overtime_worker=False, replace_overtime_worker=True, daemon_thread_time=0.1
        )

    def start(self):
        """
        启动后台日志处理

        """
        self._pool.start()

    def stop(self, overtime=0, force=False):
        """
        停止后台日志处理

        @param {number} overtime=0 - 等待超时时间，单位为秒，超过时间抛出异常
        @param {bool} force_stop=False - 是否强制关闭日志处理，直接中止所有任务

        @throws {CallOverTime} - 等待超时时抛出异常

        """
        self._pool.stop(overtime=overtime, force=force)

    #############################
    # 异步接口调用链日志处理 - 内部函数
    #############################
    def _api_chall_chain_logging_threadfun(self):
        """
        异步接口调用链日志的处理函数，从队列中获取任务信息并最终写入logger

        """
        # 从队列中获取接口登记任务
        _task = None
        try:
            _task = self._log_queue.get(block=False)
        except Empty:
            # 获取不到队列信息
            return None
        except Exception as e:
            # 存在其他异常，登记异常信息
            if self._logger is not None:
                self._log_fun[EnumLogLevel.ERROR](
                    '[EX:%s]get call chain info from log_queue error: %s' % (
                        str(type(e)),
                        traceback.format_exc()
                    )
                )
            return False

        # 执行日志登记处理
        if self._logger is not None:
            try:
                # 处理msg的格式转换
                _msg = _task['msg']
                if _msg is not None:
                    _class = getattr(
                        ImportTool.import_module(_task['msg_moudle_name']),
                        _task['msg_class_name']
                    )
                    _msg = _class(_task['msg'], msg_id=_task['msg_msg_id'])
                    # _msg = _class.str_to_msg(_task['msg'], msg_id=_task['msg_msg_id'])

                _proto_msg = _task['proto_msg']
                if _proto_msg is not None:
                    _class = getattr(
                        ImportTool.import_module(_task['proto_msg_moudle_name']),
                        _task['proto_msg_class_name']
                    )
                    _proto_msg = _class(_task['proto_msg'], msg_id=_task['proto_msg_msg_id'])
                    # _proto_msg = _class.str_to_msg(_task['proto_msg'], msg_id=_task['proto_msg_msg_id'])

                self.api_call_chain_logging(
                    msg=_msg, proto_msg=_proto_msg, logger=self._logger, api_mapping=_task['api_mapping'],
                    api_call_type=_task['api_call_type'], api_info_type=_task['api_info_type'],
                    trace_id=_task['trace_id'], trace_level=_task['trace_level'], call_id=_task['call_id'],
                    parent_id=_task['parent_id'], logging_head=_task['logging_head'],
                    use=_task['use'], error=_task['error'], trace_str=_task['trace_str'],
                    is_print_proto_msg=_task['is_print_proto_msg'],
                    proto_msg_print_kwargs=_task['proto_msg_print_kwargs'],
                    is_print_msg=_task['is_print_msg'], msg_print_kwargs=_task['msg_print_kwargs'],
                    key_para=_task['key_para'], print_in_para=_task['print_in_para'],
                    is_use_global_logger=False, log_level=_task['log_level']
                )
            except Exception as e:
                # 存在其他异常，登记异常信息
                if self._logger is not None:
                    self._log_fun[EnumLogLevel.ERROR](
                        '[EX:%s]write call chain info error: %s' % (
                            str(type(e)),
                            traceback.format_exc()
                        )
                    )
                return False
            # 处理完成
            return True

    #############################
    # 静态方法
    #############################

    @staticmethod
    def generate_trace_id():
        """
        生成全局唯一的trace_id
        注：目前使用uuid1的方法

        @returns {string} - trace_id

        """
        return str(uuid.uuid1()).replace('-', '')  # 不带-更容易查找日志

    @staticmethod
    def methon_call_chain(logger=None, trace_id=None, trace_level=None, call_id=None,
                          parent_id=None, key_para=(), print_in_para=(),
                          print_out_para=(), is_print_back=False,
                          is_use_global_logger=True, log_level=EnumLogLevel.INFO,
                          is_standard_def=False):
        """
        模块方法调用链修饰符

        @param {object} logger=None - 日志对象，如果为None代表不需要输出日志，传入对象需满足:
            1、标准logging的logger对象
            2、自定义的日志类对象，但应实现info、warning、error等标准方法
        @param {string} trace_id=None - 调用链追踪ID，None代表沿用上一调用函数传递的ID；传入值则以该值向下传递
            注：如果找不到上一调用函数传递的ID，并且修饰符也没有传入值，则自动生成一个唯一的trace_id
        @param {int[]} trace_level=None - 函数调用层级，是一个只有一个int变量的数组，trace_level[0]为当前的执行层级
            注：该变量每执行一次函数应该+1
        @param {string} call_id=None - 当前函数的执行ID，如果未传入，则自动生成一个执行ID
        @param {string} parent_id=None - 上一函数的执行ID，由上一函数传入，或自动获取
        @param {tuple} key_para=() - 定义业务层面唯一标识业务的入参参数名列表，从所修饰函数中获取对应的参数值进行打印
            注意：如果列表中的对象是string，则从函数入参的kwargs参数中获取；如果对象是int，则从args中取指定位置的值
        @param {tuple} print_in_para=() - 定义需要打印的入参参数值
            注意：如果列表中的对象是string，则从函数入参的kwargs参数中获取；如果对象是int，则从args中取指定位置的值
        @param {tuple} print_out_para=() - 定义需要打印的出参参数值（改写入参的情况）
            注意：如果列表中的对象是string，则从函数入参的kwargs参数中获取；如果对象是int，则从args中取指定位置的值
        @param {bool} is_print_back=False - 是否打印返回值信息，直接调用返回值的__str__方法
        @param {bool} is_use_global_logger=True - 当logger=None时，是否使用全局logger对象
            注：通过RunTool.set_global_logger进行设置
        @param {EnumLogLevel} log_level=EnumLogLevel.INFO - 打印日志的级别
        @param {bool} is_standard_def=False - 所修饰是否标准定义格式
            注：标准定义格式指入参固定为 func(*args, **kwargs)，这样修饰函数处理过程中无需判断入参格式，提升处理效率

        @returns {object} - 返回所修饰函数的返回值

        @example

        """
        def wrapper1(func):
            """
            第一层修饰函数，设置两层的目的是支持参数传入

            @param {function} func - 所修饰的函数

            """
            def wrapper2(*args, **kwargs):
                """
                第二层修饰函数，用于向所修饰函数传入参数
                """
                # 处理日志对象和trace_id
                _logger = logger
                if _logger is None and is_use_global_logger:
                    # 使用全局logger
                    _logger = RunTool.get_global_logger()

                if _logger is None:
                    # 没有配置日志类，不做任何封装处理，直接调用和返回
                    return CallChainTool.__call_func(func, args, kwargs, is_standard_def)
                else:
                    # 获取各类信息
                    _start_time = datetime.datetime.now()
                    _call_id = call_id
                    if _call_id is None:
                        _call_id = CallChainTool.generate_trace_id()  # 生成执行ID
                    _file_path, _file_name = os.path.split(sys._getframe().f_code.co_filename)
                    _fun_name = str(func.__name__)
                    _trace_id = trace_id

                    # 处理trace_id，优先获取当前函数参数，没有则找修饰函数传参，没有再找父函数的参数，再没有则自己创建
                    _parent_fun = sys._getframe().f_back
                    _parent_fun_name = str(_parent_fun.f_code.co_name)
                    if 'trace_id' in kwargs.keys():
                        _trace_id = kwargs['trace_id']  # 从上一个函数调用传入了追踪ID，优先使用这个

                    if _trace_id == '' or _trace_id is None and _parent_fun_name != '<module>':
                        # 尝试获取上一个调用函数参数中的trace_id
                        _trace_id = CallChainTool.__get_parent_fun_para_value(
                            _parent_fun, 'trace_id')

                    if _trace_id == '' or _trace_id is None:
                        # 都没有找到，只能当作自己是第1个调用的函数
                        _trace_id = _call_id

                    # 处理trace_level
                    _trace_level = trace_level
                    if 'trace_level' in kwargs.keys():
                        _trace_level = kwargs['trace_level']  # 从上一个函数调用传入了追踪层级，优先使用这个

                    if _trace_level is None and _parent_fun_name != '<module>':
                        # 尝试获取上一个调用函数参数中的trace_level
                        _trace_level = CallChainTool.__get_parent_fun_para_value(
                            _parent_fun, 'trace_level')

                    if _trace_level is None:
                        # 都没有找到，只能当作自己是第1个调用的函数
                        _trace_level = [0]
                    # 自加1
                    _trace_level[0] = _trace_level[0] + 1

                    # 处理parent_call_id
                    _parent_call_id = parent_id
                    if 'parent_id' in kwargs.keys():
                        _parent_call_id = kwargs['parent_id']  # 从上一个函数调用传入了追踪层级，优先使用这个
                    if _parent_call_id is None and _parent_fun_name != '<module>':
                        _parent_call_id = CallChainTool.__get_parent_fun_para_value(
                            _parent_fun, 'call_id')
                    if _parent_call_id is None:
                        _parent_call_id = ''

                    # 生成trace日志信息项
                    _trace_item = '%s:%s:%s:%s:%s:%s' % (
                        _trace_id, _call_id, _parent_call_id, str(_trace_level[0]), _file_name, _fun_name)

                    # 生成日志信息
                    _log_obj = {'key': {}, 'para': {}}
                    for _key in key_para:
                        _log_obj['key'][_key] = str(
                            CallChainTool.__get_value_from_para(_key, args, kwargs))
                    for _key in print_in_para:
                        _log_obj['para'][_key] = str(
                            CallChainTool.__get_value_from_para(_key, args, kwargs))

                    # 打印调用信息
                    _log_str = '[TRACE:%s]%s' % (_trace_item, str(_log_obj))
                    # 日志函数处理, 简化处理代码
                    _log_fun = {
                        EnumLogLevel.INFO: _logger.info,
                        EnumLogLevel.DEBUG: _logger.debug,
                        EnumLogLevel.WARNING: _logger.warning,
                        EnumLogLevel.ERROR: _logger.error,
                        EnumLogLevel.CRITICAL: _logger.critical
                    }
                    _log_fun[log_level](_log_str)

                    # 执行函数，把trace_id和trace_level放入参数中
                    kwargs['trace_id'] = _trace_id
                    kwargs['trace_level'] = _trace_level
                    kwargs['call_id'] = _call_id
                    kwargs['parent_id'] = _parent_call_id
                    try:
                        _back = CallChainTool.__call_func(func, args, kwargs, is_standard_def)
                    except Exception as e:
                        # 记录异常日志
                        _end_time = datetime.datetime.now()
                        _use = (_end_time - _start_time).total_seconds()
                        _log_str = '[TRACE:%s][USE:%ss][EX:%s]%s' % (
                            _trace_item, str(_use), str(type(e)), traceback.format_exc())
                        _log_fun[log_level](_log_str)
                        raise e

                    # 执行完成
                    _end_time = datetime.datetime.now()
                    _use = (_end_time - _start_time).total_seconds()
                    _log_back = ''
                    if is_print_back:
                        _log_obj = {'return': str(_back), 'out_para': {}}
                        for _key in print_out_para:
                            _log_obj['out_para'][_key] = str(
                                CallChainTool.__get_value_from_para(_key, args, kwargs))
                        _log_back = str(_log_obj)
                    # 打印调用信息
                    _log_str = '[TRACE:%s][USE:%ss]%s' % (_trace_item, str(_use), _log_back)
                    _log_fun[log_level](_log_str)
                    return _back
            return wrapper2
        return wrapper1

    @staticmethod
    def api_call_chain_logging(msg=None, proto_msg=None, logger=None, api_mapping=dict(),
                               api_call_type='SEND', api_info_type='SEND',
                               trace_id=None, trace_level=None, call_id=None,
                               parent_id=None, logging_head=dict(),
                               use=0, error=None, trace_str='', is_print_proto_msg=False, proto_msg_print_kwargs=dict(),
                               is_print_msg=False, msg_print_kwargs=dict(),
                               key_para=dict(), print_in_para=dict(),
                               is_use_global_logger=True, log_level=EnumLogLevel.INFO):
        """
        记录api接口调用联日志信息

        @param {interface_tool.IntfMsgFW} msg - 接口报文对象
        @param {interface_tool.IntfMsgFW} proto_msg=None - 协议报文信息对象
        @param {object} logger=None - 日志对象，如果为None代表不需要输出日志，传入对象需满足:
            1、标准logging的logger对象
            2、自定义的日志类对象，但应实现info、warning、error等标准方法
        @param {dict} api_mapping=dict() - 接口信息映射字典，用于从接口中获取指定的信息项，格式如下：
            key {string} - 输入信息项名（与入参名一致）
            value {list}- 映射信息，为三项的数组:
                value[0] {string} - 获取api对象类型，'msg'或'proto_msg'
                value[1] {string} - 搜索路径，具体规则参考对应的IntfMsgFW实例
                value[2] {dict} - 获取参数
        @param {string} api_call_type='SEND' - 接口调用类型，SEND - 发送报文，RECV - 接收报文
        @param {string} api_info_type='SEND' - 接口信息类型，区分两类：
            api_call_type为SEND的情况：
                SEND - 发送报文
                BACK - 返回报文
                OT - 超时
                EX - 异常
                STREAM-SEND - 流报文发送
                STREAM-BACK - 流报文返回
            api_call_type为RECV的情况：
                RECV - 接收报文
                RET - 返回报文
                EX - 异常
                STREAM-RECV - 流报文接收
                STREAM-DEAL - 流报文处理（非返回）
                STREAM-RET - 流报文返回
        @param {string} trace_id=None - 调用链追踪ID，None代表从报文对象msg或proto_msg中获取
        @param {int} trace_level=None - 调用层级，None代表从报文对象msg或proto_msg中获取
        @param {string} call_id=None - 当前接口调用的执行ID，None代表从报文对象msg或proto_msg中获取
        @param {string} parent_id=None - 上一接口的执行ID，None代表从报文对象msg或proto_msg中获取
        @param {dict} logging_head=dict() - 日志头信息项，用于满足日志规范，格式如下：
            key {string} - 日志头信息项名，例如'IP'
            value {string} - 日志头信息值，None代表从报文对象msg或proto_msg中获取
            按照日志规范，发送报文和接收报文的日志头包括：
                IP : 发送IP地址/发起方IP地址
                PORT : 接收方服务端口
                SYS : 目标系统标识/发起方系统标识
                SEQ : 报文流水号
        @param {number} use=0 - 接口执行耗时，api_info_type为非SEND和RECV时需传入
        @param {object} error=None - 异常对象，api_info_type为EX时需传入
        @param {string} trace_str='' - 异常堆栈信息，api_info_type为EX时需传入
        @param {bool} is_print_proto_msg=False - 是否打印协议报文信息对象
        @param {dict} proto_msg_print_kwargs=dict() - 协议报文信息对象打印参数（IntfMsgFW转换为字符串的参数）
        @param {bool} is_print_msg=False - 是否打印接口报文对象
        @param {dict} msg_print_kwargs=dict() - 报文信息对象打印参数（IntfMsgFW转换为字符串的参数
        @param {dict} key_para=dict() - 打印业务层面唯一标识业务的接口参数列表，格式如下：
            key {string} - 打印信息项名
            value {list}- 映射信息，为三项的数组:
                value[0] {string} - 获取api对象类型，'msg'或'proto_msg'
                value[1] {string} - 搜索路径，具体规则参考对应的IntfMsgFW实例
                value[2] {dict} - 获取参数,具体规则参考对应的IntfMsgFW实例
        @param {dict} print_in_para=dict() - 定义需要打印的接口信息，格式如下：
            key {string} - 打印信息项名
            value {list}- 映射信息，为三项的数组:
                value[0] {string} - 获取api对象类型，'msg'或'proto_msg'
                value[1] {string} - 搜索路径，具体规则参考对应的IntfMsgFW实例
                value[2] {dict} - 获取参数,具体规则参考对应的IntfMsgFW实例
        @param {bool} is_use_global_logger=True - 当logger=None时，是否使用全局logger对象
            注：通过RunTool.set_global_logger进行设置
        @param {EnumLogLevel} log_level=EnumLogLevel.INFO - 打印日志的级别

        """
        # 处理日志对象
        _logger = logger
        if _logger is None and is_use_global_logger:
            # 使用全局logger
            _logger = RunTool.get_global_logger()

        if _logger is None:
            # 没有日志对象
            return

        # 组织日志内容
        _log_str = '[INF-%s]' % (api_info_type)
        # 传入的信息项头__get_msg_para_value
        for _key in logging_head.keys():
            _log_str = _log_str + ('[%s:%s]' % (_key, CallChainTool.__get_msg_para_value(
                _key, value=logging_head[_key], msg=msg, proto_msg=proto_msg, api_mapping=api_mapping)))
        # 按不同类型组织其他信息
        if api_info_type in ('SEND', 'RECV', 'STREAM-SEND', 'STREAM-RECV'):
            # 发送报文、接收报文，组织调用链日志
            _log_str = _log_str + (
                '[TRACE-API:%s:%s:%s:%s]' % (
                    CallChainTool.__get_msg_para_value(
                        'trace_id', value=trace_id, msg=msg, proto_msg=proto_msg, api_mapping=api_mapping),
                    CallChainTool.__get_msg_para_value(
                        'call_id', value=call_id, msg=msg, proto_msg=proto_msg, api_mapping=api_mapping),
                    CallChainTool.__get_msg_para_value(
                        'parent_id', value=parent_id, msg=msg, proto_msg=proto_msg, api_mapping=api_mapping),
                    CallChainTool.__get_msg_para_value(
                        'trace_level', value=trace_level, msg=msg, proto_msg=proto_msg, api_mapping=api_mapping)
                )
            )
        else:
            # 返回报文或异常情况
            if trace_id is not None:
                # 外部有传入trace_id相关信息，同样登记
                _log_str = _log_str + (
                    '[TRACE-API:%s:%s:%s:%s]' % (trace_id, call_id, parent_id, str(trace_level))
                )

            # 使用时间
            _log_str = _log_str + ('[USE:%ss]' % (str(use)))

        if api_info_type == 'EX':
            # 异常
            _error_info = error
            if not isinstance(error, str):
                # 不是字符类型
                _error_info = str(type(error))

            _log_str = _log_str + (
                '[EX:%s]%s' % (_error_info, trace_str)
            )
        else:
            # 其他情况，打印报文关键字
            if len(key_para) > 0 or len(print_in_para) > 0:
                _log_obj = {'key': {}, 'para': {}}
                for _key in key_para.keys():
                    _log_obj['key'][_key] = CallChainTool.__get_msg_para_value(
                        _key, value=None, msg=msg, proto_msg=proto_msg, api_mapping=key_para)
                for _key in print_in_para.keys():
                    _log_obj['para'][_key] = CallChainTool.__get_msg_para_value(
                        _key, value=None, msg=msg, proto_msg=proto_msg, api_mapping=print_in_para)
                _log_str = _log_str + str(_log_obj)
            # 打印报文主体
            if is_print_proto_msg and proto_msg is not None:
                _log_str = _log_str + '\r\n' + proto_msg.to_str(**proto_msg_print_kwargs)
            if is_print_msg and msg is not None:
                _log_str = _log_str + '\r\n' + msg.to_str(**msg_print_kwargs)

        # 打印日志，日志函数处理, 简化处理代码
        _log_fun = {
            EnumLogLevel.INFO: _logger.info,
            EnumLogLevel.DEBUG: _logger.debug,
            EnumLogLevel.WARNING: _logger.warning,
            EnumLogLevel.ERROR: _logger.error,
            EnumLogLevel.CRITICAL: _logger.critical
        }
        _log_fun[log_level](_log_str)

    @staticmethod
    def api_call_chain_logging_nowait(log_queue, msg=None, proto_msg=None, api_mapping=dict(),
                                      api_call_type='SEND', api_info_type='SEND',
                                      trace_id=None, trace_level=None, call_id=None,
                                      parent_id=None, logging_head=dict(),
                                      use=0, error=None, trace_str='', is_print_proto_msg=False, proto_msg_print_kwargs=dict(),
                                      is_print_msg=False, msg_print_kwargs=dict(),
                                      key_para=dict(), print_in_para=dict(),
                                      log_level=EnumLogLevel.INFO):
        """
        记录api接口调用联日志信息-异步模式，把信息放入队列处理，快速返回结果

        @param {QueueFw} log_queue - 需要放置日志的队列对象
        @param {interface_tool.IntfMsgFW} msg - 接口报文对象
        @param {interface_tool.IntfMsgFW} proto_msg=None - 协议报文信息对象
        @param {dict} api_mapping=dict() - 接口信息映射字典，用于从接口中获取指定的信息项，格式如下：
            key {string} - 输入信息项名（与入参名一致）
            value {list}- 映射信息，为三项的数组:
                value[0] {string} - 获取api对象类型，'msg'或'proto_msg'
                value[1] {string} - 搜索路径，具体规则参考对应的IntfMsgFW实例
                value[2] {dict} - 获取参数
        @param {string} api_call_type='SEND' - 接口调用类型，SEND - 发送报文，RECV - 接收报文
        @param {string} api_info_type='SEND' - 接口信息类型，区分两类：
            api_call_type为SEND的情况：
                SEND - 发送报文
                BACK - 返回报文
                OT - 超时
                EX - 异常
            api_call_type为RECV的情况：
                RECV - 接收报文
                RET - 返回报文
                EX - 异常
        @param {string} trace_id=None - 调用链追踪ID，None代表从报文对象msg或proto_msg中获取
        @param {int} trace_level=None - 调用层级，None代表从报文对象msg或proto_msg中获取
        @param {string} call_id=None - 当前接口调用的执行ID，None代表从报文对象msg或proto_msg中获取
        @param {string} parent_id=None - 上一接口的执行ID，None代表从报文对象msg或proto_msg中获取
        @param {dict} logging_head=dict() - 日志头信息项，用于满足日志规范，格式如下：
            key {string} - 日志头信息项名，例如'IP'
            value {string} - 日志头信息值，None代表从报文对象msg或proto_msg中获取
            按照日志规范，发送报文和接收报文的日志头包括：
                IP : 发送IP地址/发起方IP地址
                PORT : 接收方服务端口
                SYS : 目标系统标识/发起方系统标识
                SEQ : 报文流水号
        @param {number} use=0 - 接口执行耗时，api_info_type为非SEND和RECV时需传入
        @param {object} error=None - 异常对象，api_info_type为EX时需传入
        @param {string} trace_str='' - 异常堆栈信息，api_info_type为EX时需传入
        @param {bool} is_print_proto_msg=False - 是否打印协议报文信息对象
        @param {dict} proto_msg_print_kwargs=dict() - 协议报文信息对象打印参数（IntfMsgFW转换为字符串的参数）
        @param {bool} is_print_msg=False - 是否打印接口报文对象
        @param {dict} msg_print_kwargs=dict() - 报文信息对象打印参数（IntfMsgFW转换为字符串的参数)
        @param {dict} key_para=dict() - 打印业务层面唯一标识业务的接口参数列表，格式如下：
            key {string} - 打印信息项名
            value {list}- 映射信息，为三项的数组:
                value[0] {string} - 获取api对象类型，'msg'或'proto_msg'
                value[1] {string} - 搜索路径，具体规则参考对应的IntfMsgFW实例
                value[2] {dict} - 获取参数,具体规则参考对应的IntfMsgFW实例
        @param {dict} print_in_para=dict() - 定义需要打印的接口信息，格式如下：
            key {string} - 打印信息项名
            value {list}- 映射信息，为三项的数组:
                value[0] {string} - 获取api对象类型，'msg'或'proto_msg'
                value[1] {string} - 搜索路径，具体规则参考对应的IntfMsgFW实例
                value[2] {dict} - 获取参数,具体规则参考对应的IntfMsgFW实例
        @param {EnumLogLevel} log_level=EnumLogLevel.INFO - 打印日志的级别

        """
        # 将传入的信息转换为一个大dict，推入队列中（需注意要转换为基础类型）
        _task = {
            'msg': None,
            'proto_msg': None,
            'api_mapping': api_mapping,
            'api_call_type': api_call_type,
            'api_info_type': api_info_type,
            'trace_id': trace_id,
            'trace_level': trace_level,
            'call_id': call_id,
            'parent_id': parent_id,
            'logging_head': logging_head,
            'use': use,
            'error': None,
            'trace_str': trace_str,
            'is_print_proto_msg': is_print_proto_msg,
            'proto_msg_print_kwargs': proto_msg_print_kwargs,
            'is_print_msg': is_print_msg,
            'msg_print_kwargs': msg_print_kwargs,
            'key_para': key_para,
            'print_in_para': print_in_para,
            'log_level': log_level
        }

        # 转换已知的非基础类型数据
        if error is not None:
            _task['error'] = str(type(error))
        if msg is not None:
            _task['msg'] = msg.to_str()
            _task['msg_moudle_name'] = RunTool.get_object_moudle_name(msg)
            _task['msg_class_name'] = RunTool.get_object_class_name(msg)
            _task['msg_msg_id'] = msg.msg_id

        if proto_msg is not None:
            _task['proto_msg'] = msg.to_str()
            _task['proto_msg_moudle_name'] = RunTool.get_object_moudle_name(proto_msg)
            _task['proto_msg_class_name'] = RunTool.get_object_class_name(proto_msg)
            _task['proto_msg_msg_id'] = proto_msg.msg_id

        # 放入队列中
        log_queue.put(_task)

    #############################
    # 内部函数
    #############################

    @staticmethod
    def __call_func(func, args, kwargs, is_standard_def):
        """
        内部函数，根据传入参数处理实际的函数调用

        @param {function} func - 要执行的函数
        @param {tuple} args - 不带参数名的参数列表
        @param {dict} kwargs - 带参数名的参数列表
        @param {bool} is_standard_def - 是否标准定义的修饰符函数

        @returns {object} - 返回函数的执行结果

        """
        if is_standard_def:
            # 标准修饰符函数，直接调用无需特殊处理
            return func(*args, **kwargs)
        else:
            # 非标准修饰符函数，通过动态参数传入执行
            _exec_str = 'func('
            # 拼接
            _i = 0
            while _i < len(args):
                _exec_str = _exec_str + ('args[%s],' % (str(_i)))
                _i = _i + 1
            _exec_str_2 = _exec_str.rstrip(',') + ')'  # 这个脚本用于在参数传入执行出错的情况下重新执行
            for _key in kwargs.keys():
                _exec_str = _exec_str + ('%s=kwargs[\'%s\'],' % (_key, _key))
            # 去掉最后一个逗号
            _exec_str = _exec_str.rstrip(',') + ')'
            # 执行并返回
            try:
                return eval(_exec_str)
            except TypeError:
                return eval(_exec_str_2)

    @staticmethod
    def __get_value_from_para(index, args, kwargs):
        """
        从函数入参值中获取指定的值

        @param {string/int} index - key值或位置索引
        @param {tuple} args - 动态位置入参
        @param {dict} kwargs - 动态key-value入参

        @returns {object} - 取到的值，如果取不到则返回None

        """
        try:
            if type(index) == int:
                return args[index]
            else:
                return kwargs[index]
        except Exception:
            return None

    @staticmethod
    def __get_parent_fun_para_value(parent_fun_frame, para_name):
        """
        从父函数堆栈获取参数值

        @param {object} parent_fun_frame - 父函数堆栈（sys._getframe().f_back）
        @param {string} para_name - 参数名

        @returns {object} - 获取到的参数值，如果找不到返回None

        """
        _para_value = None
        if hasattr(parent_fun_frame, 'f_locals'):
            if para_name in parent_fun_frame.f_locals.keys():
                _para_value = parent_fun_frame.f_locals[para_name]
            elif 'kwargs' in parent_fun_frame.f_locals.keys() and para_name in parent_fun_frame.f_locals['kwargs']:
                _para_value = parent_fun_frame.f_locals['kwargs'][para_name]
        return _para_value

    @staticmethod
    def __get_msg_para_value(para_name, value=None, msg=None, proto_msg=None, api_mapping=dict()):
        """
        获取报文消息指定报文项的值

        @param {string} para_name - 报文项标识名，需要与api_mapping的key对应上
        @param {string} value=None - 报文项固定值，只有在None的情况下才会真正找消息体的内容
        @param {interface_tool.IntfMsgFW} msg - 接口报文对象
        @param {interface_tool.IntfMsgFW} proto_msg=None - 协议报文信息对象
        @param {dict} api_mapping=dict() - 接口信息映射字典，用于从接口中获取指定的信息项，格式如下：
            key {string} - 输入信息项名（与入参名一致）
            value {list}- 映射信息，为三项的数组:
                value[0] {string} - 获取api对象类型，'msg'或'proto_msg'
                value[1] {string} - 搜索路径，具体规则参考对应的IntfMsgFW实例
                value[2] {dict} - 获取参数

        @returns {string} - 如果value非None时，直接返回value的值，否则从报文中查找值，查不到返回''

        """
        if value is not None:
            return str(value)

        # 获取值
        _msg_value = ''
        with ExceptionTool.ignored_all():
            if para_name in api_mapping.keys():
                _msg = msg
                if api_mapping[para_name][0] == 'proto_msg':
                    _msg = proto_msg
                if _msg is not None:
                    _msg_value = str(_msg.get_value(
                        search_path=api_mapping[para_name][1], **api_mapping[para_name][2]))
        return _msg_value


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    # 打印版本信息
    print(('模块名：%s  -  %s\n'
           '作者：%s\n'
           '发布日期：%s\n'
           '版本：%s' % (__MOUDLE__, __DESCRIPT__, __AUTHOR__, __PUBLISH__, __VERSION__)))

#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
#
# Copyright 2019 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
连接池处理框架
@module pool_fw
@file pool_fw.py
"""

import os
import sys
import threading
import uuid
import datetime
import time
import logging
import traceback
from queue import Empty
from abc import ABC, abstractmethod  # 利用abc模块实现抽象类
# 根据当前文件路径将包路径纳入，在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir)))
from HiveNetLib.generic import NullObj
from HiveNetLib.simple_queue import MemoryQueue, EnumQueueType
from HiveNetLib.base_tools.exception_tool import ExceptionTool
from HiveNetLib.base_tools.run_tool import RunTool


__MOUDLE__ = 'pool_fw'  # 模块名
__DESCRIPT__ = u'连接池处理框架'  # 模块描述
__VERSION__ = '0.1.0'  # 版本
__AUTHOR__ = u'黎慧剑'  # 作者
__PUBLISH__ = '2019.07.14'  # 发布日期


class ConnectionPoolFw(ABC):
    """
    连接池处理框架类
    抽象连接池的公共方法形成框架，并提供基本的处理功能，简化连接池编程的难度
    """
    #############################
    # 私有变量
    #############################
    _logger = None  # 日志对象
    _current_size = 0  # 当前连接池大小
    _access_lock = None  # 访问连接池对象的线程锁
    # 连接池连接信息，以字典的方式记录每个连接的情况
    # key - 连接对象的id（str(uuid.uuid1())）
    # value - 连接对象属性，为一个NullObj对象，属性定义如下
    #   .connection - 连接对象本身
    #   .is_using {bool} - 是否正被使用
    #   .last_free_time {datetime} - 上一次释放的时间
    #   .last_test_time {datetime} - 上一次检查有效性的时间
    _connection_pool = None

    # 空闲连接池，以队列方式实现，使用MemoryQueue的后进先出模式，仅登记连接对象的id
    # 注意空闲池中的id有可能已被释放，因此取出来要判断对象是否还存在
    _free_pool = None

    _is_destroyed = False  # 标识连接池是否已被销毁
    _daemon_running = False   # 标识守护线程是否在执行

    #############################
    # 公共属性
    #############################
    connect_para = None
    name = 'ConnectionPool'
    maxsize = 100
    minsize = 0
    realse_free_time = 300
    test_on_get = False
    test_on_free = False
    test_while_idle = True
    test_idle_time = 60
    validation_query = ''
    get_connection_timeout = 0
    daemon_sleep_time = 1

    @property
    def is_destroyed(self):
        """
        返回连接池是否已被销毁的标记
        @property {bool}
        """
        return self._is_destroyed

    @property
    def current_size(self):
        """
        返回池子大小
        @property {int}
        """
        return self._current_size

    @property
    def free_pool_size(self):
        """
        返回空闲池大小
        @property {int}
        """
        return self._free_pool.qsize()

    #############################
    # 公共函数
    #############################
    def __init__(self, connect_para, name='ConnectionPool', maxsize=100, minsize=0, realse_free_time=300,
                 test_on_get=False, test_on_free=False, test_while_idle=True,
                 test_idle_time=60, validation_query='',
                 get_connection_timeout=0, logger=None, init_break_if_connect_error=True,
                 daemon_sleep_time=1):
        """
        构造函数，创建连接池

        @param {NullObj} connect_para - 连接参数，具体参数属性根据实现类指定
        @param {string} name='ConnectionPool' - 连接池名称
        @param {int} maxsize=100 - 最大连接数
        @param {int} minsize=0 - 最小保持连接数
        @param {number} realse_free_time=300 - 自动释放多长时间的空闲无操作连接（单位秒）
        @param {bool} test_on_get=False - 是否在获取连接前检查连接是否有效
        @param {bool} test_on_free=False - 是否在归还连接时检查连接是否有效
        @param {bool} test_while_idle=True - 是否检查空闲连接是否有效
        @param {number} test_idle_time=60 - 自动检查空闲连接有效性的时间间隔（单位秒）
        @param {string} validation_query='' - 检查连接是否有效的查询语句（非数据库类的可以传入检查参数）
        @param {number} get_connection_timeout=0 - 获取连接的等待超时时间（单位秒），0代表不超时
        @param {Logger} logger=None - 日志对象，服务过程中通过该函数写日志:
            可以为标准的logging日志库对象，也可以为simple_log对象，但要求对象实现:
            标准的info、debug、warning、error、critical五个日志方法
        @param {bool} init_break_if_connect_error=True - 如果连接失败则初始化抛出异常
        @param {number} daemon_sleep_time=1 - 守护进程的间隔刷新时间（单位秒）
        """
        # 设置初始化参数
        self.connect_para = connect_para
        self.name = name
        self.maxsize = maxsize
        self.minsize = minsize
        self.realse_free_time = realse_free_time
        self.test_on_get = test_on_get
        self.test_on_free = test_on_free
        self.test_while_idle = test_while_idle
        self.test_idle_time = test_idle_time
        self.validation_query = validation_query
        self.get_connection_timeout = get_connection_timeout
        self._logger = logger
        self.daemon_sleep_time = daemon_sleep_time
        # 应在__init__中初始化，否则会出现两个实例对象引用地址一样的问题
        self._connection_pool = dict()
        self._free_pool = MemoryQueue(queue_type=EnumQueueType.LIFO, maxsize=0)
        self._access_lock = threading.Lock()

        # 按最小保持连接数创建连接
        _i = 0
        while _i < self.minsize:
            try:
                # 创建连接出现异常记录日志，并抛出异常
                with ExceptionTool.ignored(
                    expect=(), logger=self._logger,
                    self_log_msg='Connection Pool [%s] Init Error ' % (self.name),
                    force_log_level=logging.ERROR
                ):
                    # 创建连接
                    _cid = self._create_connection()
                    # 把连接加入到空闲池
                    self._free_pool.put(_cid)
                    self._current_size += 1
            except Exception as e:
                # 根据init_break_if_connect_error参数，如果为False则连接异常也继续处理
                if init_break_if_connect_error:
                    raise e
            _i += 1

        # 创建守护线程，负责检查及释放空闲连接
        _daemon_thread = threading.Thread(
            target=self.__start_daemon_thread_fun,
            args=(1,),
            name='DaemonThread-ConnectionPool[%s]' % (self.name)
        )
        _daemon_thread.setDaemon(True)
        self._daemon_running = True
        _daemon_thread.start()

    def get_connection(self):
        """
        获取一个可用连接（从空闲池获取）

        @return {object} - 返回连接对象，具体类型由实现类定义
            注意：该对象会有一个connection_pool_id的属性，用于释放连接时使用

        @throws {TimeoutError} - 如果超时则会抛出该异常
        @throws {NameError} - 如果对象被销毁后再访问，会抛出该异常
        """
        _begin_time = datetime.datetime.now()
        while True:
            if self._is_destroyed:
                # 线程池已销毁，抛出异常
                raise NameError

            # 为了控制超时，所以用循环处理，先获取访问权
            if self._access_lock.acquire(blocking=True, timeout=0.1):
                # 获取锁成功
                _cid = ''  # 登记获取到的连接id
                _is_create_connection = False  # 标识是否新建的连接
                try:
                    # 先尝试从空闲池获取连接
                    try:
                        _cid = self._free_pool.get_nowait()
                    except Empty:
                        pass

                    if _cid == '':
                        # 没有空闲连接，需要创建一个新连接进行处理，考虑效率问题不在锁定状态做
                        if self._current_size < self.maxsize:
                            _is_create_connection = True
                            self._current_size += 1  # 为避免连接数超过限制，这里要先增加当前数量
                    else:
                        # 获取到空闲连接，标记被占用
                        self._connection_pool[_cid].is_using = True
                finally:
                    self._access_lock.release()

                # 如果需要创建新连接
                if _is_create_connection:
                    try:
                        _cid = self._create_connection()
                    except Exception as e:
                        # 创建连接出现异常,当前数量恢复
                        self._access_lock.acquire()
                        self._current_size -= 1
                        self._access_lock.release()
                        # 记录日志
                        if self._logger is not None:
                            self._logger.log(
                                logging.ERROR,
                                '[EX:%s]Create new connection error: %s ' % (
                                    str(type(e)), traceback.format_exc()
                                )
                            )
                        # 抛出异常
                        raise sys.exc_info()[1]
                    # 设置连接被占用
                    self._connection_pool[_cid].is_using = True

                # 校验连接有效性，只有创建了连接才这样处理，注意有可能释放了，但id还在空闲队列的情况
                if _cid != '' and _cid in self._connection_pool.keys():
                    if self.test_on_get:
                        if self.test_connection(self._connection_pool[_cid].connection):
                            # 连接有效，直接返回
                            return self._connection_pool[_cid].connection
                        else:
                            # 连接无效，释放连接，同时继续下一次循环
                            _connection = self._connection_pool[_cid].connection
                            del self._connection_pool[_cid]
                            self._close_connection(_connection)
                            # 当前线程数量恢复
                            self._access_lock.acquire()
                            self._current_size -= 1
                            self._access_lock.release()
                            if self._logger is not None:
                                self._logger.log(
                                    logging.DEBUG,
                                    'Connection Pool [%s] get connection test false, release connection [%s]' % (
                                        self.name, _cid
                                    )
                                )
                    else:
                        # 返回连接
                        return self._connection_pool[_cid].connection

            # 判断是否已超时；如果get_connection_timeout <= 0则会一直阻塞直到异常
            if self.get_connection_timeout > 0 and (datetime.datetime.now() - _begin_time).total_seconds() > self.get_connection_timeout:
                # 已超时，抛出异常
                raise TimeoutError('get_connection timeout!')

    def free_connection(self, connection):
        """
        释放所使用的连接对象（放回空闲池）

        @param {object} connection - 要释放的连接对象
        """
        _cid = connection.connection_pool_id
        if self._is_destroyed or _cid not in self._connection_pool.keys() or not self._connection_pool[_cid].is_using:
            # 对象已销毁，或连接对象不在池中或状态不正确，不处理
            return

        # 判断是否有效
        _is_realse = False
        if self.test_on_free:
            if not self.test_connection(connection):
                # 状态无效，删除该对象
                self._access_lock.acquire()
                try:
                    self._current_size -= 1
                    del self._connection_pool[_cid]
                    _is_realse = True
                finally:
                    self._access_lock.release()

        # 进行最终处理
        if _is_realse:
            # 释放对象
            self._close_connection(connection)
            if self._logger is not None:
                self._logger.log(
                    logging.DEBUG,
                    'Connection Pool [%s] free connection test false, release connection [%s]' % (
                        self.name, _cid
                    )
                )
        else:
            # 放回空闲队列(线程安全，无需锁处理)
            self._connection_pool[_cid].is_using = False
            self._free_pool.put(_cid)

    def test_connection(self, connection):
        """
        检查指定的连接有效性

        @param {object} connection - 要检查的连接对象

        @return {bool} - 测试结果
        """
        try:
            # 执行不抛出异常就是成功
            self._test_connection_self(connection)
            return True
        except Exception as e:
            if self._logger is not None:
                self._logger.log(
                    logging.ERROR,
                    '[EX:%s]Connection Pool [%s] test connection [%s] error:\n%s' % (
                        str(type(e)), self.name, connection.connection_pool_id, traceback.format_exc()
                    )
                )
            return False

    def reconnect(self, connection):
        """
        对指定对象重新进行连接

        @param {object} connection - 要重新连接的对象

        @return {object} - 返回有效的连接对象

        @throws {Exception} - 当重连失败时应抛出异常
        """
        with ExceptionTool.ignored(
            expect=(), logger=self._logger,
            self_log_msg='Connection Pool [%s] reconnect[%s] Error ' % (
                self.name, connection.connection_pool_id),
            force_log_level=logging.ERROR
        ):
            _cid = connection.connection_pool_id
            _new_connection = self._reconnect_self(connection)
            _new_connection.connection_pool_id = _cid
            self._connection_pool[_cid].connection = _new_connection

    def destroy(self):
        """
        销毁连接池并释放资源
        注意连接池销毁后将不能再使用
        """
        # 设置标记
        self._is_destroyed = True
        # 等待守护线程结束
        while self._daemon_running:
            RunTool.sleep(0.5)

        # 清除所有线程连接资源
        self._access_lock.acquire()
        try:
            self._current_size = 0
            self._free_pool.clear()
            for (_key, _value) in self._connection_pool.items():
                # 逐个关闭连接
                self._close_connection(_value.connection)
            self._connection_pool.clear()
        finally:
            self._access_lock.release()

    def __del__(self):
        """
        销毁对象的处理
        """
        self.destroy()

    #############################
    # 内部函数
    #############################

    def _create_connection(self):
        """
        创建一个新的连接对象

        @return {string} - 返回连接对象的id

        @throws {Exception} - 当创建失败或连接无效时应直接抛出异常
        """
        # 调用实现类创建新的连接对象
        _connection = self._create_connection_self()
        _cid = str(uuid.uuid1())
        _connection.connection_pool_id = _cid
        # 生成内部的连接信息对象
        _connection_info = NullObj()
        _connection_info.connection = _connection
        _connection_info.is_using = False
        _connection_info.last_free_time = datetime.datetime.now()
        _connection_info.last_test_time = datetime.datetime.now()
        # 放入连接池
        self._connection_pool[_cid] = _connection_info
        # 返回连接id
        return _cid

    def _close_connection(self, connection):
        """
        关闭连接（出现异常只记录日志不抛出异常）

        @param {object} connection - 要关闭的连接对象
        """
        with ExceptionTool.ignored_all(
            unexpect=(), logger=self._logger,
            self_log_msg='Connection Pool [%s] close connection[%s] error:' % (
                self.name, connection.connection_pool_id),
            force_log_level=logging.ERROR
        ):
            self._close_connection_self(connection)

    def __start_daemon_thread_fun(self, tid):
        """
        守护线程，负责检查连接有效性和释放连接

        @param {int} tid - 线程id
        """
        while True:
            if self._is_destroyed:
                # 出现销毁标记，退出守护
                break

            with ExceptionTool.ignored_all(
                unexpect=(), logger=self._logger,
                self_log_msg='Connection Pool [%s] DaemonThread[%s] Error ' % (self.name, str(tid)),
                force_log_level=logging.ERROR
            ):
                # 遍历连接进行处理，从空闲队列中逐个拿出来进行确认，没有问题再放回去
                _count = self._free_pool.qsize()
                while _count > 0:
                    try:
                        _key = self._free_pool.get_nowait()
                        _count -= 1  # 取出一个减少一次计数，避免无限循环
                    except Empty:
                        # 没有空闲连接，不用处理，退出循环
                        break

                    # 开始进行判断处理
                    _value = self._connection_pool[_key]
                    if self._is_destroyed:
                        # 出现销毁标记，退出守护
                        break

                    _is_realse = False
                    self._access_lock.acquire()
                    try:
                        if _value.is_using:
                            # 使用中，无需处理
                            continue

                        # 看是否要释放对象
                        _now = datetime.datetime.now()
                        if self._current_size > self.minsize and (_now - _value.last_free_time).total_seconds() > self.realse_free_time:
                            # 已经超过空闲时间了，释放连接，实际释放连接在后面再做
                            _is_realse = True
                            self._current_size -= 1
                            del self._connection_pool[_key]
                            if self._logger is not None:
                                self._logger.log(
                                    logging.DEBUG,
                                    'Connection Pool [%s] release free connection [%s], last free time [%s]' % (
                                        self.name, _key, _value.last_free_time.strftime(
                                            '%Y-%m-%d %H:%M:%S')
                                    )
                                )
                    finally:
                        self._access_lock.release()

                    # 检查连接有效性，可能时间比较长，无需锁住对象
                    if not _is_realse and self.test_while_idle and (_now - _value.last_test_time).total_seconds() > self.test_idle_time:
                        _test_result = self.test_connection(_value.connection)  # 检查结果
                        if _test_result:
                            # 通过检查，更新检查时间
                            _value.last_test_time = _now
                        else:
                            # 没有通过检查，需要再次锁定并进行释放
                            self._access_lock.acquire()
                            try:
                                if not _value.is_using:
                                    # 再次确认没有被外部获取，才进行删除
                                    _is_realse = True
                                    self._current_size -= 1
                                    del self._connection_pool[_key]
                                    if self._logger is not None:
                                        self._logger.log(
                                            logging.DEBUG,
                                            'Connection Pool [%s] release invalid connection [%s]' % (
                                                self.name, _key
                                            )
                                        )
                            finally:
                                self._access_lock.release()

                    # 执行真正的关闭连接动作
                    if _is_realse:
                        self._close_connection(_value.connection)
                    else:
                        # 没有释放，把对象放回空闲队列
                        self._free_pool.put(_key)

            # 进行下一次的循环
            RunTool.sleep(self.daemon_sleep_time)

        # 运行到这里说明守护线程结束
        self._daemon_running = False

    #############################
    # 需要具体类实现的函数
    #############################
    @abstractmethod
    def _create_connection_self(self):
        """
        创建一个连接对象（具体类实现）

        @return {object} - 返回有效的连接对象

        @throws {Exception} - 当创建失败或连接无效时应直接抛出异常
        """
        raise NotImplementedError

    @abstractmethod
    def _close_connection_self(self, connection):
        """
        关闭指定的连接对象（具体类实现）

        @param {object} connection - 要关闭的连接对象

        @throws {Exception} - 当关闭失败时应直接抛出异常
        """
        raise NotImplementedError

    @abstractmethod
    def _test_connection_self(self, connection):
        """
        测试指定的连接对象是否有效（具体类实现）

        @param {object} connection - 要测试的连接对象

        @throws {Exception} - 当测试失败时应抛出异常
        """
        raise NotImplementedError

    @abstractmethod
    def _reconnect_self(self, connection):
        """
        对指定对象重新进行连接（具体类实现）

        @param {object} connection - 要重新连接的对象

        @return {object} - 返回有效的连接对象

        @throws {Exception} - 当重连失败时应抛出异常
        """
        raise NotImplementedError


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    # 打印版本信息
    print(('模块名：%s  -  %s\n'
           '作者：%s\n'
           '发布日期：%s\n'
           '版本：%s' % (__MOUDLE__, __DESCRIPT__, __AUTHOR__, __PUBLISH__, __VERSION__)))

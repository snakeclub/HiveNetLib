#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""
测试连接池框架
@module test_connection_pool
@file test_connection_pool.py
"""

import sys
import os
import unittest
import threading
import json
import uuid
import time
# 根据当前文件路径将包路径纳入，在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir)))
from HiveNetLib.generic import NullObj, CResult
from HiveNetLib.connection_pool.pool_fw import ConnectionPoolFw
from HiveNetLib.simple_log import Logger


# 线程池测试，异常抛出控制开关
TEST_SWITCH = {
    'create': True,
    'close': True,
    'test': True,
    'reconnect': True
}


class TestPoolClass(ConnectionPoolFw):
    """
    连接池框架的测试类
    """
    #############################
    # 需要具体类实现的函数
    #############################

    def _create_connection_self(self):
        """
        创建一个连接对象（具体类实现）

        @return {object} - 返回有效的连接对象

        @throws {Exception} - 当创建失败或连接无效时应直接抛出异常
        """
        if not TEST_SWITCH['create']:
            raise InterruptedError('_create_connection_self Interrupted!')
        if self.connect_para.prop1 != 'a' or self.connect_para.prop2 != 'b':
            raise ValueError('_create_connection_self error!')
        connection = NullObj()
        connection.name = 'TestPoolClass'
        connection.id = str(uuid.uuid1())
        connection.status = True
        print('create connection id: %s' % connection.id)
        return connection

    def _close_connection_self(self, connection):
        """
        关闭指定的连接对象（具体类实现）

        @param {object} connection - 要关闭的连接对象

        @throws {Exception} - 当关闭失败时应直接抛出异常
        """
        if not TEST_SWITCH['close']:
            raise InterruptedError('_close_connection_self Interrupted!')
        if hasattr(connection, 'raise_err') and connection.raise_err:
            raise ValueError('_close_connection_self error!')
        print('close connection id: %s' % connection.id)
        connection.status = False

    def _test_connection_self(self, connection):
        """
        测试指定的连接对象是否有效（具体类实现）

        @param {object} connection - 要测试的连接对象

        @throws {Exception} - 当测试失败时应抛出异常
        """
        if not TEST_SWITCH['test']:
            raise InterruptedError('_test_connection_self Interrupted!')
        if hasattr(connection, 'raise_err') and connection.raise_err:
            raise ValueError('_test_connection_self error!')
        print('test connection id: %s' % connection.id)
        return

    def _reconnect_self(self, connection):
        """
        对指定对象重新进行连接（具体类实现）

        @param {object} connection - 要重新连接的对象

        @return {object} - 返回有效的连接对象

        @throws {Exception} - 当重连失败时应抛出异常
        """
        if not TEST_SWITCH['reconnect']:
            raise InterruptedError('_reconnect_self Interrupted!')
        if hasattr(connection, 'raise_err') and connection.raise_err:
            raise ValueError('_reconnect_self error!')
        print('reconnection id: %s' % connection.id)
        return


def setUpModule():
    print("test module start >>>>>>>>>>>>>>")


def tearDownModule():
    print("test module end >>>>>>>>>>>>>>")


class Test(unittest.TestCase):

    # 整个Test类的开始和结束执行
    @classmethod
    def setUpClass(cls):
        print("test class start =======>")
        cls._logger = Logger()

    @classmethod
    def tearDownClass(cls):
        print("test class end =======>")

    # 每个用例的开始和结束执行
    def setUp(self):
        print("test case start -->")

    def tearDown(self):
        print("test case end -->")

    def test_case1(self):
        print("测试案例1")
        print('测试初始化时异常-连接失败')
        _connect_para = NullObj()
        _connect_para.prop1 = 'a'
        _connect_para.prop2 = 'c'
        try:
            _pool = TestPoolClass(
                _connect_para, name='ConnectionPool', maxsize=5, minsize=2, realse_free_time=10,
                test_on_get=True, test_on_free=True, test_while_idle=False,
                test_idle_time=60, validation_query='',
                get_connection_timeout=1, logger=self._logger, init_break_if_connect_error=True
            )
            self.assertTrue(False, '期望初始化异常，但未抛出')
        except Exception as e:
            print('测试抛出初始化异常成功: %s' % str(e))

        print('测试正常获取连接')
        _connect_para = NullObj()
        _connect_para.prop1 = 'a'
        _connect_para.prop2 = 'b'
        _pool = TestPoolClass(
            _connect_para, name='ConnectionPool', maxsize=5, minsize=1, realse_free_time=10,
            test_on_get=True, test_on_free=True, test_while_idle=True,
            test_idle_time=5, validation_query='',
            get_connection_timeout=1, logger=self._logger, init_break_if_connect_error=True
        )
        c_dict = dict()
        c_dict['1'] = _pool.get_connection()
        print('current_size: %d' % _pool.current_size)
        self.assertTrue(
            c_dict['1'].name == 'TestPoolClass', msg='测试正常获取连接失败 - 获取第1个连接信息错误！'
        )

        print('前面获取的是已有连接，后面获取才创建新连接')

        _i = 2
        while _i <= 5:
            c_dict[str(_i)] = _pool.get_connection()
            _i += 1
        print('current_size: %d' % _pool.current_size)

        print('测试连接超过以后获取超时')
        try:
            c_dict['6'] = _pool.get_connection()
            self.assertTrue(
                False, msg='测试连接超过以后获取超时失败 - 期望抛出超时异常！'
            )
        except TimeoutError:
            pass
        except:
            self.assertTrue(
                False, msg='测试连接超过以后获取超时失败，错误信息: %s' % str(sys.exc_info())
            )
        print('current_size: %d' % _pool.current_size)

        print('测试释放连接')
        _pool.free_connection(c_dict['1'])
        print('current_size: %d' % _pool.current_size)
        self.assertTrue(
            _pool.current_size == 5 and _pool.free_pool_size == 1,
            msg='测试释放连接失败1 - 当前连接池大小及空闲池大小错误：%d %d' % (_pool.current_size, _pool.free_pool_size)
        )
        _pool.free_connection(c_dict['2'])
        self.assertTrue(
            _pool.current_size == 5 and _pool.free_pool_size == 2,
            msg='测试释放连接失败2 - 当前连接池大小及空闲池大小错误：%d %d' % (_pool.current_size, _pool.free_pool_size)
        )
        c_dict['1'] = _pool.get_connection()
        c_dict['2'] = _pool.get_connection()
        try:
            c_dict['6'] = _pool.get_connection()
            self.assertTrue(
                False, msg='测试释放连接失败 - 释放后再获取当超过最大大小时，期望抛出超时异常！'
            )
        except TimeoutError:
            pass
        except:
            self.assertTrue(
                False, msg='测试释放连接失败，释放后再获取当超过最大大小时应超时，错误信息: %s' % str(sys.exc_info())
            )

        print('测试自动释放空闲连接')
        _i = 1
        while _i <= 5:
            _pool.free_connection(c_dict[str(_i)])
            _i += 1
        print('等待15秒释放')
        time.sleep(15)
        self.assertTrue(
            _pool.current_size == 1 and _pool.free_pool_size == 1,
            msg='测试自动释放空闲连接 - 当前连接池大小及空闲池大小错误：%d %d' % (_pool.current_size, _pool.free_pool_size)
        )

        print('测试获取连接出现异常的情况')
        TEST_SWITCH['create'] = False  # 生成连接异常
        c_dict['1'] = _pool.get_connection()
        try:
            c_dict['2'] = _pool.get_connection()
            self.assertTrue(
                False, msg='测试获取连接出现异常的情况 - 期望抛出异常！'
            )
        except:
            pass
        self.assertTrue(
            _pool.current_size == 1 and _pool.free_pool_size == 0,
            msg='测试自动释放空测试获取连接出现异常的情况，失败 - 当前连接池大小及空闲池大小错误：%d %d' % (
                _pool.current_size, _pool.free_pool_size)
        )
        TEST_SWITCH['create'] = True

        print('测试释放连接时检查失败的情况')
        TEST_SWITCH['test'] = False
        _pool.free_connection(c_dict['1'])
        self.assertTrue(
            _pool.current_size == 0 and _pool.free_pool_size == 0,
            msg='测试释放连接时检查失败的情况，失败 - 当前连接池大小及空闲池大小错误：%d %d' % (
                _pool.current_size, _pool.free_pool_size)
        )

        print('测试连接时检查失败的情况')
        try:
            c_dict['1'] = _pool.get_connection()
            self.assertTrue(
                False, msg='测试连接时检查失败的情况 - 期望抛出异常！'
            )
        except:
            pass
        self.assertTrue(
            _pool.current_size == 0 and _pool.free_pool_size == 0,
            msg='测试连接时检查失败的情况，失败 - 当前连接池大小及空闲池大小错误：%d %d' % (
                _pool.current_size, _pool.free_pool_size)
        )
        TEST_SWITCH['test'] = True

        print('测试空闲时检查连接的情况')
        _i = 1
        while _i <= 5:
            c_dict[str(_i)] = _pool.get_connection()
            _i += 1
        _i = 1
        while _i <= 5:
            _pool.free_connection(c_dict[str(_i)])
            _i += 1
        self.assertTrue(
            _pool.current_size == 5 and _pool.free_pool_size == 5,
            msg='测试空闲时检查连接的情况，失败 - 当前连接池大小及空闲池大小错误：%d %d' % (
                _pool.current_size, _pool.free_pool_size)
        )
        print('等待8秒，让空闲连接检查连接有效性')
        TEST_SWITCH['test'] = False
        time.sleep(8)
        self.assertTrue(
            _pool.current_size == 0 and _pool.free_pool_size == 0,
            msg='测试空闲时检查连接的情况，失败 - 当前连接池大小及空闲池大小错误：%d %d' % (
                _pool.current_size, _pool.free_pool_size)
        )


if __name__ == '__main__':
    unittest.main()

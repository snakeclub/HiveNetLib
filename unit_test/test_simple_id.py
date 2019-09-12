#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""
测试simple_id模块
@module test_simple_id
@file test_simple_id.py
"""

import os
import sys
import unittest
import time
from queue import Full, Empty
# 根据当前文件路径将包路径纳入，在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir)))
from HiveNetLib.simple_id import IdSourceMemory, IdPool


__MOUDLE__ = 'test_simple_id'  # 模块名
__DESCRIPT__ = u'测试simple_id模块'  # 模块描述
__VERSION__ = '0.1.0'  # 版本
__AUTHOR__ = u'黎慧剑'  # 作者
__PUBLISH__ = '2019.08.05'  # 发布日期


class TestSimpleId(unittest.TestCase):
    """
    测试simple_id模块
    """

    def setUp(self):
        """
        启动测试执行的初始化
        """
        pass

    def tearDown(self):
        """
        结束测试执行的销毁
        """
        pass

    def test_idsource(self):
        """
        测试IdSourceMemory
        """
        print('测试IdSourceMemory - 循环获取')
        _idsource = IdSourceMemory(
            max_id=20, is_circle=True, min_id=1, initial_id=3
        )
        self.assertTrue(_idsource.current_id == 3,
                        '失败：测试IdSourceMemory - 循环获取 - 初始id错误：%d' % _idsource.current_id)

        _min, _max = _idsource.allocate(18)
        self.assertTrue(
            _idsource.current_id == 1 and _min == 3 and _max == 20,
            '失败：测试IdSourceMemory - 循环获取 - 获取最大值边界失败：%d, %d, %d' % (_idsource.current_id, _min, _max)
        )

        _idsource.set_current_id(17)
        self.assertTrue(_idsource.current_id == 17,
                        '失败：测试IdSourceMemory - 循环获取 - 设置当前id错误：%d' % _idsource.current_id)

        _min, _max = _idsource.allocate(6)
        self.assertTrue(
            _idsource.current_id == 1 and _min == 17 and _max == 20,
            '失败：测试IdSourceMemory - 循环获取 - 超过最大值边界失败：%d, %d, %d' % (_idsource.current_id, _min, _max)
        )

        _min, _max = _idsource.allocate(6)
        self.assertTrue(
            _idsource.current_id == 7 and _min == 1 and _max == 6,
            '失败：测试IdSourceMemory - 循环获取 - 分配6个id失败：%d, %d, %d' % (_idsource.current_id, _min, _max)
        )

        _min, _max = _idsource.allocate(3)
        self.assertTrue(
            _idsource.current_id == 10 and _min == 7 and _max == 9,
            '失败：测试IdSourceMemory - 循环获取 - 分配3个id失败：%d, %d, %d' % (_idsource.current_id, _min, _max)
        )

        _idsource = IdSourceMemory(
            max_id=20, is_circle=True, min_id=2, initial_id=None
        )
        self.assertTrue(_idsource.current_id == 2,
                        '失败：测试IdSourceMemory - 循环获取 - id最小值错误：%d' % _idsource.current_id)

        _min, _max = _idsource.allocate(30)
        self.assertTrue(
            _idsource.current_id == 2 and _min == 2 and _max == 20,
            '失败：测试IdSourceMemory - 循环获取 - 设置id最小值跨最大值失败：%d, %d, %d' % (
                _idsource.current_id, _min, _max)
        )

        _min, _max = _idsource.allocate(1)
        self.assertTrue(
            _idsource.current_id == 3 and _min == 2 and _max == 2,
            '失败：测试IdSourceMemory - 循环获取 - 只获取一个失败：%d, %d, %d' % (
                _idsource.current_id, _min, _max)
        )

        print('测试IdSourceMemory - 非循环获取')
        _idsource = IdSourceMemory(
            max_id=20, is_circle=False, min_id=1, initial_id=None
        )
        _min, _max = _idsource.allocate(20)
        self.assertTrue(
            _idsource.current_id == 21 and _min == 1 and _max == 20 and _idsource.is_overflow,
            '失败：测试IdSourceMemory - 非循环获取 - 等最大值失败：%d, %d, %d, %s' % (
                _idsource.current_id, _min, _max, str(_idsource.is_overflow))
        )
        try:
            _min, _max = _idsource.allocate(1)
            self.assertTrue(False, '失败：测试IdSourceMemory - 非循环获取 - 越界后应抛出异常')
        except OverflowError:
            pass

        _idsource = IdSourceMemory(
            max_id=20, is_circle=False, min_id=1, initial_id=None
        )
        _min, _max = _idsource.allocate(30)
        self.assertTrue(
            _idsource.current_id == 21 and _min == 1 and _max == 20 and _idsource.is_overflow,
            '失败：测试IdSourceMemory - 非循环获取 - 跨最大值失败：%d, %d, %d, %s' % (
                _idsource.current_id, _min, _max, str(_idsource.is_overflow))
        )

    def test_idpool(self):
        """
        测试IdPool
        """
        print('测试IdPool - Deamon补充池子的情况')
        _idsource = IdSourceMemory(
            max_id=10, is_circle=True, min_id=1, initial_id=None
        )
        # print(_idsource)
        _idpool = IdPool(_idsource, alloc_size=4, alloc_lower_size=2, is_deamon=True)
        # 等待自动补充池子
        time.sleep(1)
        self.assertTrue(_idpool.pool_size == 4,
                        '失败：测试IdPool - Deamon补充池子的情况 - 开始补充池子：%d' % _idpool.pool_size)
        # 获取id
        _i = 1
        while _i <= 3:
            _id = _idpool.get_id()
            self.assertTrue(_id == _i, '失败：测试IdPool - Deamon补充池子的情况 - 获取id错误：%d, %d' % (_i, _id))
            _i += 1
        # 等待自动补充池子
        time.sleep(1)
        self.assertTrue(_idpool.pool_size == 5,
                        '失败：测试IdPool - Deamon补充池子的情况 - 开始补充池子：%d' % _idpool.pool_size)

        _i = 1
        while _i <= 15:
            print('测试IdPool - Deamon补充池子的情况 - 循环获取: %d ' % _idpool.get_id())
            _i += 1

        print('测试IdPool - 获取触发补充池子的情况')
        _idsource = IdSourceMemory(
            max_id=10, is_circle=True, min_id=1, initial_id=None
        )
        # print(_idsource)
        _idpool = IdPool(_idsource, alloc_size=4, alloc_lower_size=2, is_deamon=False)
        # 等待自动补充池子
        time.sleep(1)
        self.assertTrue(_idpool.pool_size == 0,
                        '失败：测试IdPool - 获取触发补充池子的情况 - 不应补充池子：%d' % _idpool.pool_size)

        # 获取id
        _i = 1
        while _i <= 3:
            _id = _idpool.get_id()
            # print('获取触发补充池子循环: %d' % _id)
            self.assertTrue(_id == _i, '失败：测试IdPool - 获取触发补充池子的情况 - 获取id错误：%d, %d' % (_i, _id))
            _i += 1
        self.assertTrue(_idpool.pool_size == 5,
                        '失败：测试IdPool - 获取触发补充池子的情况 - 开始补充池子：%d' % _idpool.pool_size)

        _i = 1
        while _i <= 15:
            print('测试IdPool - 获取触发补充池子的情况 - 循环获取: %d ' % _idpool.get_id())
            _i += 1

        print('测试IdPool - overflow情况的处理')
        _idsource = IdSourceMemory(
            max_id=5, is_circle=False, min_id=1, initial_id=None
        )
        _idpool = IdPool(_idsource, alloc_size=4, alloc_lower_size=2, is_deamon=False)
        _i = 1
        while _i <= 5:
            _id = _idpool.get_id()
            self.assertTrue(_id == _i, '失败：测试IdPool - overflow情况的处理 - 获取id错误：%d, %d' % (_i, _id))
            _i += 1
        # 再获取应该抛出异常
        try:
            _id = _idpool.get_id()
            self.assertTrue(False, '失败：测试IdPool - overflow情况的处理 - 越界后应抛出异常')
        except OverflowError:
            pass
        # 重置
        _idsource.set_current_id(1)
        while _i <= 5:
            _id = _idpool.get_id()
            self.assertTrue(_id == _i, '失败：测试IdPool - overflow情况的处理 - 第2次获取id错误：%d, %d' % (_i, _id))
            _i += 1

        print('测试IdPool - 测试使用公式')
        _idsource = IdSourceMemory(
            max_id=10, is_circle=True, min_id=1, initial_id=None
        )
        _idpool = IdPool(_idsource, alloc_size=4, alloc_lower_size=2, is_deamon=False,
            is_use_formula=True, formula_str='IUSP-{$PY=1+2$}-{$TIME=%Y-%m-%d$}-{$ID=5$}')
        print(_idpool.get_id())
        _cid = _idpool.get_id(overtime=0, formula_str='IUSP-{$PY=1+2$}-{$ID=5$}')
        self.assertTrue(
            _cid == 'IUSP-3-00002',
            '失败：测试IdPool - 测试使用公式: %s' % _cid
        )


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    unittest.main()

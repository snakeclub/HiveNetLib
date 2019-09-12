#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

import unittest
import threading
import json

# 整个文件的开始和结束执行


def setUpModule():
    print("test module start >>>>>>>>>>>>>>")


def tearDownModule():
    print("test module end >>>>>>>>>>>>>>")


class Test(unittest.TestCase):

    # 整个Test类的开始和结束执行
    @classmethod
    def setUpClass(cls):
        print("test class start =======>")

    @classmethod
    def tearDownClass(cls):
        print("test class end =======>")

    # 每个用例的开始和结束执行
    def setUp(self):
        print("test case start -->")

    def tearDown(self):
        print("test case end -->")

    def test_case(self):
        print("test case1")

    def test_case2(self):
        print("test case2")


class ParaTest(object):
    """
    测试类局部变量的有效范围
    """
    li = list()
    d = dict()
    t = tuple()
    s = 'string'
    i = 10


if __name__ == '__main__':
    # unittest.main()
    c1 = ParaTest()
    c1.li.append(1)
    c1.t = (333)
    c1.d['add'] = 2
    c1.s = 'change'
    c1.i = 22

    c2 = ParaTest()
    print(c2.li)
    print(c2.t)
    print(c2.d)
    print(c2.s)
    print(c2.i)

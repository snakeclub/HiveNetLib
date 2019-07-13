#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

import unittest

# 整个文件的开始和结束执行


def yieldtest1(n):
    i = n
    while i > 0:
        yield i
        i -= 1


def yieldtest2(n):
    try:
        i = n
        while i > 0:
            try:
                yield i
            finally:
                print('yieldtest2 in!')
            i -= 1
    except:
        print('yieldtest2 ex!')
    finally:
        print('yieldtest2 end!')


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


if __name__ == '__main__':
    # unittest.main()
    for a in yieldtest1(5):
        print('yieldtest1 : ' + str(a))

    for a in yieldtest2(5):
        print('yieldtest2 : ' + str(a))

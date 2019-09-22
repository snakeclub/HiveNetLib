#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

import sys
import os
import unittest
import threading
import json
import netifaces
# 根据当前文件路径将包路径纳入，在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir)))
from HiveNetLib.base_tools.net_tool import NetTool
from HiveNetLib.prompt_plus import PromptPlus


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
    # print(NetTool.get_net_interfaces())
    # print(NetTool.get_net_interface_info(NetTool.get_net_interfaces()[5]))
    print(PromptPlus.get_cmd_para_list("abc k1=v1 -a 10 20 -abc 30 -c   'abcd hh=name' -c"))
    print(PromptPlus.get_cmd_para_list("abc k1=v1 -a 10 20 -abc 30 -c   'abcd hh=name "))

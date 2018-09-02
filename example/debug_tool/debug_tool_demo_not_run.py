#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

# 本模块不执行，用于测试和验证跨模块时的DebugTool行为

import sys
import os
sys.path.append(os.path.abspath(os.path.dirname(__file__)+'/'+'../..'))
from HiveNetLib.base_tools.debug_tool import DebugTool


def test_debugtools():
    DebugTool.debug_print("从debug_tool_demo_not_run中的打印信息")

#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

import sys
import os
import time
import unittest
# 根据当前文件路径将包路径纳入，在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir)))
from HiveNetLib.simple_log import Logger
from HiveNetLib.pipeline import Pipeline
from HiveNetLib.pipeline_router import GoToNode


_logger_config = {
    'conf_file_name': '',
    'logger_name': 'Console',
    'logfile_path': '',
    'config_type': 'JSON_STR',
    'json_str': """{
                "version": 1,
                "disable_existing_loggers": false,
                "formatters": {
                    "simpleFormatter": {
                        "format": "[%(asctime)s.%(millisecond)s][%(levelname)s][PID:%(process)d][FILE:%(filename)s][FUN:%(funcName)s]%(message)s",
                        "datefmt": "%Y_%m_%d %H:%M:%S"
                    }
                },

                "handlers": {
                    "ConsoleHandler": {
                        "class": "logging.StreamHandler",
                        "level": "DEBUG",
                        "formatter": "simpleFormatter",
                        "stream": "ext://sys.stdout"
                    }
                },

                "loggers": {
                    "Console": {
                        "level": "DEBUG",
                        "handlers": ["ConsoleHandler"]
                    }
                },

                "root": {
                    "level": "DEBUG",
                    "handlers": []
                }
            }
    """,
    'auto_create_conf': False,
    'is_create_logfile_by_day': False,
    'call_fun_level': 0
}

LOGGER = Logger.create_logger_by_dict(_logger_config)


def asyn_notify_fun(name, run_id, status, context, output):
    """
    管道运行结果通知函数
    """
    print('pipeline [%s] [%s] finished [status: %s]: %s' % (
        name, run_id, status, str(output)
    ))


def running_notify_fun(name, run_id, node_id, node_name):
    """
    节点运行通知函数
    """
    print('pipeline [%s] [%s] start run node [%s: %s]' % (
        name, run_id, node_id, node_name
    ))


def end_running_notify_fun(name, run_id, node_id, node_name, status, status_msg):
    """
    结束节点运行通知
    """
    print('pipeline [%s] [%s] end run node [%s: %s] [status: %s]: %s' % (
        name, run_id, node_id, node_name, status, status_msg
    ))


def setUpModule():
    # 日志对象

    # 装载管道插件
    Pipeline.add_plugin(GoToNode)  # 通用管道插件
    Pipeline.load_plugins_by_path(
        os.path.join(os.path.dirname(__file__), 'pipeline_plugins')
    )


def tearDownModule():
    print("test module end >>>>>>>>>>>>>>")


class Test(unittest.TestCase):
    # 每个用例的开始和结束执行
    def setUp(self):
        # 测试管道设置 - 同步
        _pl_sync_config = {
            '1': {
                "name": "Minus10",
                "processor": "ProcesserAdd",
                "context": {'num': -10},
                "router": "GoToNode",
                "router_para": {'goto_node_id': '3'},
            },
            '2': {
                "name": "NoExecute",
                "processor": "ProcesserAdd",
                "context": {'num': 10}
            },
            '3': {
                "name": "DivideBy50",
                "processor": "ProcesserDivideBy",
                "context": {'num': 50},
                "exception_router": "GoToNode",
                "exception_router_para": {'goto_node_id': '5'}
            },
            '4': {
                "name": "Add100",
                "processor": "ProcesserAdd",
                "context": {'num': 100},
                "router": "",
                "router_para": {},
                "exception_router": "",
                "exception_router_para": {}
            },
            '5': {
                "name": "Multiply2",
                "processor": "ProcesserMultiply",
                "context": {'num': 2}
            },
            '6': {
                "name": "Add3",
                "processor": "ProcesserAdd",
                "context": {'num': 3},
                "router": "",
                "router_para": {},
                "exception_router": "",
                "exception_router_para": {}
            }
        }

        self.pl_sync = Pipeline('pl_sync', _pl_sync_config, is_asyn=False, logger=LOGGER)
        self.pl_sync_asyn = Pipeline(
            'pl_sync_asyn', _pl_sync_config, is_asyn=True, asyn_notify_fun=asyn_notify_fun,
            running_notify_fun=running_notify_fun, end_running_notify_fun=end_running_notify_fun,
            logger=LOGGER
        )

        # 测试管道设置 - 异步
        _pl_asyn_config = {
            '1': {
                "name": "Minus10",
                "processor": "ProcesserAdd",
                "context": {'num': -10},
                "router": "GoToNode",
                "router_para": {'goto_node_id': '3'},
            },
            '2': {
                "name": "NoExecute",
                "processor": "ProcesserAdd",
                "context": {'num': 10}
            },
            '3': {
                "name": "Add100",
                "processor": "ProcesserAsynAdd",
                "context": {'num': 100}
            },
            '4': {
                "name": "Add3",
                "processor": "ProcesserAdd",
                "context": {'num': 3}
            }
        }
        try:
            self.pl_asyn_sync = Pipeline(
                'pl_asyn_sync', _pl_asyn_config, is_asyn=False, logger=LOGGER
            )
            raise RuntimeError('except to raise AttributeError!')
        except AttributeError:
            pass

        self.pl_asyn = Pipeline(
            'pl_asyn', _pl_asyn_config, is_asyn=True, asyn_notify_fun=asyn_notify_fun,
            running_notify_fun=running_notify_fun, end_running_notify_fun=end_running_notify_fun,
            logger=LOGGER
        )

        # 测试管道设置 - 异常
        _pl_ex_config = {
            '1': {
                "name": "Minus10",
                "processor": "ProcesserAdd",
                "context": {'num': -10},
                "router": "GoToNode",
                "router_para": {'goto_node_id': '3'},
            },
            '2': {
                "name": "NoExecute",
                "processor": "ProcesserAdd",
                "context": {'num': 10}
            },
            '3': {
                "name": "DivideBy50",
                "processor": "ProcesserDivideBy",
                "context": {'num': 50}
            },
            '4': {
                "name": "Add100",
                "processor": "ProcesserAdd",
                "context": {'num': 100},
                "router": "",
                "router_para": {},
                "exception_router": "",
                "exception_router_para": {}
            }
        }

        self.pl_ex_sync = Pipeline(
            'pl_ex_sync', _pl_ex_config, is_asyn=False, logger=LOGGER
        )

        self.pl_ex_asyn = Pipeline(
            'pl_ex_asyn', _pl_ex_config, is_asyn=True, asyn_notify_fun=asyn_notify_fun,
            running_notify_fun=running_notify_fun, end_running_notify_fun=end_running_notify_fun,
            logger=LOGGER
        )

    def tearDown(self):
        print("test case end -->")

    def test_pl_sync(self):
        _tips = '测试同步管道 - 同步正常'
        _input_data = 20
        print(_tips)
        _run_id, _status, _output = self.pl_sync.start(input_data=_input_data)
        self.assertEqual(
            _output, (50 / (_input_data - 10) + 100) * 2 + 3,
            '%s: %s' % (_tips, self.pl_sync.context(_run_id))
        )

        _run_id = self.pl_sync_asyn.start(input_data=_input_data)
        while self.pl_sync_asyn.status(run_id=_run_id) not in ['success', 'exception']:
            time.sleep(0.01)

        self.assertEqual(
            self.pl_sync_asyn.output(run_id=_run_id), (50 / (_input_data - 10) + 100) * 2 + 3,
            '%s: %s' % (_tips, self.pl_sync_asyn.context(_run_id))
        )

        _tips = '测试同步管道 - 同步异常跳转'
        _input_data = 10
        print(_tips)
        _run_id, _status, _output = self.pl_sync.start(input_data=_input_data)
        self.assertEqual(
            _output, (_input_data - 10) + 3,
            '%s: %s' % (_tips, self.pl_sync.context(_run_id))
        )

        _run_id = self.pl_sync_asyn.start(input_data=_input_data)
        while self.pl_sync_asyn.status(run_id=_run_id) not in ['success', 'exception']:
            time.sleep(0.01)

        self.assertEqual(
            self.pl_sync_asyn.output(run_id=_run_id), (_input_data - 10) + 3,
            '%s: %s' % (_tips, self.pl_sync_asyn.context(_run_id))
        )

    def test_pl_asyn(self):
        _tips = '测试异步管道 - 正常'
        _input_data = 30
        print(_tips)
        _run_id = self.pl_asyn.start(input_data=_input_data)
        while self.pl_asyn.status(run_id=_run_id) not in ['success', 'exception']:
            time.sleep(0.01)

        self.assertEqual(
            self.pl_asyn.output(run_id=_run_id), (_input_data - 10) + 100 + 3,
            '%s: %s' % (_tips, self.pl_asyn.context(_run_id))
        )

    def test_pl_ex(self):
        _tips = '测试异常管道'
        _input_data = 10
        print(_tips)
        _run_id, _status, _output = self.pl_ex_sync.start(input_data=_input_data)
        self.assertEqual(
            (_status, _output), ('exception', None),
            '%s失败: 应抛出异常' % _tips
        )
        print(self.pl_ex_sync.trace_list(_run_id))

        _run_id = self.pl_ex_asyn.start(input_data=_input_data)
        while self.pl_ex_asyn.status(run_id=_run_id) not in ['success', 'exception']:
            time.sleep(0.01)

        self.assertEqual(
            (self.pl_ex_asyn.status(_run_id), self.pl_ex_asyn.output(_run_id)), ('exception', None),
            '%s失败: 应抛出异常' % _tips
        )
        print(self.pl_ex_asyn.trace_list(_run_id))

    def test_checkpoint(self):
        print(LOGGER)
        _pl_asyn_config = {
            '1': {
                "name": "Minus10",
                "processor": "ProcesserAdd",
                "context": {'num': -10},
                "router": "GoToNode",
                "router_para": {'goto_node_id': '3'},
            },
            '2': {
                "name": "NoExecute",
                "processor": "ProcesserAdd",
                "context": {'num': 10}
            },
            '3': {
                "name": "Add100",
                "processor": "ProcesserAsynAdd",
                "context": {'num': 100}
            },
            '4': {
                "name": "Add3",
                "processor": "ProcesserAdd",
                "context": {'num': 3}
            }
        }
        _tips = '测试存储中间状态'
        _input_data1 = 10
        _input_data2 = 20
        print(_tips)
        _pl1 = Pipeline(
            'pl1', _pl_asyn_config, is_asyn=True, asyn_notify_fun=asyn_notify_fun,
            running_notify_fun=running_notify_fun, end_running_notify_fun=end_running_notify_fun,
            logger=LOGGER
        )
        _run_id1 = _pl1.start(input_data=_input_data1)
        _run_id2 = _pl1.start(input_data=_input_data2, run_id='1')
        _pl1.pause(_run_id2)
        self.assertTrue(_pl1.status(_run_id2) == 'pause', '%s: status error!')
        while _pl1.status(run_id=_run_id1) not in ['success', 'exception']:
            time.sleep(0.01)

        self.assertEqual(
            _pl1.output(run_id=_run_id1), (_input_data1 - 10) + 100 + 3,
            'before load: %s: %s' % (_tips, _pl1.context(_run_id1))
        )

        # print('run_id1 context: %s' % _pl1.context(_run_id1))
        # print('run_id2 context: %s' % _pl1.context(_run_id2))

        # 导出中间状态
        _json = _pl1.save_checkpoint()
        print('Save checkpoint: %s' % _json)
        del _pl1

        _pl2 = Pipeline(
            'pl2', _pl_asyn_config, is_asyn=True, asyn_notify_fun=asyn_notify_fun,
            running_notify_fun=running_notify_fun, end_running_notify_fun=end_running_notify_fun,
            logger=LOGGER
        )

        # 装载中间状态
        _pl2.load_checkpoint(_json)
        self.assertEqual(
            _pl2.output(run_id=_run_id1), (_input_data1 - 10) + 100 + 3,
            'after load: %s: %s' % (_tips, _pl2.context(_run_id1))
        )
        _pl2.resume(_run_id2)
        while _pl2.status(run_id=_run_id2) not in ['success', 'exception']:
            time.sleep(0.01)

        self.assertEqual(
            _pl2.output(run_id=_run_id2), (_input_data2 - 10) + 100 + 3,
            'after load: %s: %s' % (_tips, _pl2.context(_run_id2))
        )


if __name__ == '__main__':
    unittest.main()

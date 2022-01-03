#!/usr/bin/env python3
# -*- coding: UTF-8 -*-


import sys
import os
import random
import unittest
import time
# 根据当前文件路径将包路径纳入，在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir)))
from HiveNetLib.base_tools.test_tool import TestTool
from HiveNetLib.file_transfer.saver import TransferSaver
from HiveNetLib.file_transfer.protocol import LocalProtocol
from HiveNetLib.file_transfer.transfer import Transfer
from HiveNetLib.file_transfer.extend_protocol.grpc import GRpcPullServicerGenerater, GRpcPushServicerGenerater, GRpcPushProtocol, GRpcPullProtocol
from HiveNetLib.base_tools.file_tool import FileTool
from HiveNetLib.prompt_plus import ProgressRate
from HiveNetLib.base_tools.debug_tool import DebugTool
from HiveNetLib.base_tools.net_tool import NetTool
import HiveNetLib.simple_log as simple_log
from HiveNetLib.simple_grpc.grpc_server import SimpleGRpcServer
from HiveNetLib.simple_grpc.grpc_client import SimpleGRpcConnection


TEST_FLAG = {
    'test_TransferSaver_fun': False,
    'test_local_to_local': False,
    'test_local_to_grpc': True,
    'test_grpc_to_local': False
}

_temp_path = os.path.realpath(
    os.path.join(
        os.path.dirname(__file__), os.path.pardir, 'test_data/temp/file_transfer'
    )
)
_temp_file = os.path.join(_temp_path, 'temp_src_file.bin')

_log_path = os.path.join(_temp_path, 'log')


class Test(unittest.TestCase):

    # 整个Test类的开始和结束执行
    @classmethod
    def setUpClass(cls):
        print("test class start =======>")
        print("初始化日志类")
        try:
            # 删除临时日志
            FileTool.remove_files(path=_log_path, regex_str='.*\\.log')
        except:
            pass

        _logger_conf = os.path.realpath(os.path.join(
            _temp_path, os.path.pardir, os.path.pardir, 'file_transfer/test_file_transfer.json'
        ))
        cls.logger = simple_log.Logger(
            conf_file_name=_logger_conf,
            logger_name=simple_log.EnumLoggerName.File,
            config_type=simple_log.EnumLoggerConfigType.JSON_FILE,
            # logfile_path=_TEMP_DIR + '/log/test_case_client.log',
            is_create_logfile_by_day=True,
        )
        cls.logger.setLevelWithHandler(simple_log.DEBUG)

        print('初始化并启动服务，简单服务，无SSL，无服务发现')
        cls.server_no_ssl_no_zoo_opts = SimpleGRpcServer.generate_server_opts(
            ip='127.0.0.1',
            port=50051,
            max_workers=50,
            max_connect=400,
            is_health_check=True
        )
        cls.server_no_ssl_no_zoo = SimpleGRpcServer(
            server_name='ServerNoSslNoZoo',
            logger=cls.logger, log_level=simple_log.INFO)

        _push_services = GRpcPushServicerGenerater(
            work_dir=_temp_path, lock_in_work_dir=True, logger=cls.logger, is_use_global_logger=False
        )
        _pull_services = GRpcPullServicerGenerater(
            work_dir=_temp_path, lock_in_work_dir=True, logger=cls.logger, is_use_global_logger=False
        )

        cls.server_no_ssl_no_zoo.start_server(
            server_opts=cls.server_no_ssl_no_zoo_opts, servicer_list={
                'servicer_file_transfer_push': _push_services.get_servicer(),
                'servicer_file_transfer_pull': _pull_services.get_servicer()
            }, is_wait=True
        )

        # 先创建本地随机文件
        print('创建本地随机文件')
        FileTool.create_dir(_temp_path, exist_ok=True)
        if not os.path.exists(_temp_file):
            with open(_temp_file, 'wb') as _file:
                _real_size = 561 * 1024  # 561kb
                _file.truncate(_real_size)  # 对于已存在的文件，有可能比较大，要进行截断处理
                _file.seek(_real_size - 1)   # 跳到指定位置
                _file.write(b'\x00')  # 一定要写入一个字符，否则无效
                _file.seek(random.randint(0, _real_size - 1 - 1024))
                _file.write(bytes('abcdefg', encoding='utf-8'))
                _file.flush()

    @classmethod
    def tearDownClass(cls):
        print("test class end =======>")
        # 停止服务，简单服务，无SSL，无服务发现
        cls.server_no_ssl_no_zoo.stop_server()

    def test_TransferSaver_fun(self):
        if not TEST_FLAG['test_TransferSaver_fun']:
            return

        print("测试 TransferSaver 算法函数")

        # _f_merge_store_index
        _store_index = [[0, 1000]]
        _merge = TransferSaver._f_merge_store_index(_store_index)
        self.assertTrue(
            TestTool.cmp_list(_store_index, _merge), msg='_f_merge_store_index - 1'
        )

        _store_index = [[0, 300], [301, 1000]]
        _merge = TransferSaver._f_merge_store_index(_store_index)
        self.assertTrue(
            TestTool.cmp_list([[0, 1000]], _merge), msg='_f_merge_store_index - 2'
        )

        _store_index = [[0, 300], [302, 304], [305, 390], [391, 400], [500, 1000]]
        _merge = TransferSaver._f_merge_store_index(_store_index)
        self.assertTrue(
            TestTool.cmp_list([[0, 300], [302, 400], [500, 1000]], _merge), msg='_f_merge_store_index - 3'
        )

        # _f_set_cache_area
        _store_index = [[0, 900], [950, 1000]]
        _cache_size = 30
        _block_size = 0
        _max_cache_pos = [-1, ]
        _thread_num = 5
        _cache = dict()
        for _i in range(_thread_num):
            _cache[_i] = {
                'start': -1,  # 缓存数据对应文件的写入位置, -1代表没有设置
                'size': 0,  # 缓存数据大小
                'end_pos': -1,  # 该缓存对应线程要处理的文件块结束位置
                'get_start': -1,
                'get_size': 0
            }
        for _i in range(_thread_num):
            TransferSaver._f_set_cache_area(
                _cache, _i, _store_index, _cache_size, _block_size, _max_cache_pos
            )

        self.assertTrue(
            TestTool.cmp_dict(
                _cache,
                {
                    0: {'start': 0, 'size': 0, 'end_pos': 223, 'get_start': 0, 'get_size': 0},
                    1: {'start': 950, 'size': 0, 'end_pos': 1000, 'get_start': 950, 'get_size': 0},
                    2: {'start': 450, 'size': 0, 'end_pos': 674, 'get_start': 450, 'get_size': 0},
                    3: {'start': 675, 'size': 0, 'end_pos': 900, 'get_start': 675, 'get_size': 0},
                    4: {'start': 224, 'size': 0, 'end_pos': 449, 'get_start': 224, 'get_size': 0}
                }
            ), msg='_f_set_cache_area - 1'
        )

        _store_index = [[0, 70], [950, 1000]]
        _cache_size = 30
        _max_cache_pos = [-1, ]
        _thread_num = 5
        _cache = dict()
        for _i in range(_thread_num):
            _cache[_i] = {
                'start': -1,  # 缓存数据对应文件的写入位置, -1代表没有设置
                'size': 0,  # 缓存数据大小
                'end_pos': -1,  # 该缓存对应线程要处理的文件块结束位置
                'get_start': -1,
                'get_size': 0
            }
        for _i in range(_thread_num):
            TransferSaver._f_set_cache_area(
                _cache, _i, _store_index, _cache_size, _block_size, _max_cache_pos
            )

        self.assertTrue(
            TestTool.cmp_dict(
                _cache,
                {
                    0: {'start': 0, 'size': 0, 'end_pos': 34, 'get_start': 0, 'get_size': 0},
                    1: {'start': 950, 'size': 0, 'end_pos': 974, 'get_start': 950, 'get_size': 0},
                    2: {'start': 35, 'size': 0, 'end_pos': 52, 'get_start': 35, 'get_size': 0},
                    3: {'start': 975, 'size': 0, 'end_pos': 1000, 'get_start': 975, 'get_size': 0},
                    4: {'start': 53, 'size': 0, 'end_pos': 70, 'get_start': 53, 'get_size': 0}
                }
            ), msg='_f_set_cache_area - 2'
        )

        # _f_update_store_index
        _store_index = [[0, 900], [950, 1000]]
        TransferSaver._f_update_store_index(
            _store_index, 0, 100
        )
        self.assertTrue(
            TestTool.cmp_list(_store_index, [[100, 900], [950, 1000]]),
            msg='_f_update_store_index - 1'
        )

        _store_index = [[0, 900], [950, 1000]]
        TransferSaver._f_update_store_index(
            _store_index, 10, 100
        )
        self.assertTrue(
            TestTool.cmp_list(_store_index, [[0, 9], [110, 900], [950, 1000]]),
            msg='_f_update_store_index - 2'
        )

        _store_index = [[0, 900], [950, 1000]]
        TransferSaver._f_update_store_index(
            _store_index, 900, 10  # 超出部分不考虑
        )
        self.assertTrue(
            TestTool.cmp_list(_store_index, [[0, 899], [950, 1000]]),
            msg='_f_update_store_index - 3'
        )

        # 跨区域的不处理
        _store_index = [[0, 900], [950, 1000]]
        TransferSaver._f_update_store_index(
            _store_index, 920, 960
        )
        self.assertTrue(
            TestTool.cmp_list(_store_index, [[0, 900], [950, 1000]]),
            msg='_f_update_store_index - 4'
        )

    def test_local_to_local(self):
        if not TEST_FLAG['test_local_to_local']:
            return

        print('测试本地文件复制')

        # DebugTool.set_debug(set_on=True)
        _copy_file = os.path.join(_temp_path, 'local_to_local_copy.bin')

        # 删除临时文件
        if os.path.exists(_copy_file):
            FileTool.remove_file(_copy_file)
        for _ext in ('.lock', '.tmp', '.info'):
            if os.path.exists(_copy_file + _ext):
                FileTool.remove_file(_copy_file + _ext)

        # 单线程-缓存大于文件大小
        _tips = '单线程-缓存大于文件大小'
        with LocalProtocol(
            _temp_file, _copy_file, is_resume=True, is_overwrite=True
        ) as _protocol:
            _reader = Transfer(
                _protocol, show_process_bar_fun=ProgressRate.show_cmd_process_bar,
                process_bar_label=_tips,
                thread_interval=0.0
            )
            _status = _reader.start(wait_finished=True)
            self.assertTrue(
                _status == 'finished', msg="本地文件复制-%s: %s" % (_tips, _status)
            )

        # 单线程-每次传输块大小大于文件
        _tips = '单线程-每次传输块大小大于文件'
        with LocalProtocol(
            _temp_file, _copy_file, is_resume=True, is_overwrite=True,
            block_size=600000, auto_expand=False
        ) as _protocol:
            _reader = Transfer(
                _protocol, show_process_bar_fun=ProgressRate.show_cmd_process_bar,
                process_bar_label=_tips,
                thread_interval=0.0
            )
            _status = _reader.start(wait_finished=True)
            self.assertTrue(
                _status == 'finished', msg="本地文件复制-%s: %s" % (_tips, _status)
            )

        # 单线程-缓存小于文件大小
        _tips = '单线程-缓存小于文件大小'
        with LocalProtocol(
            _temp_file, _copy_file, is_resume=True, is_overwrite=True,
            cache_size=2
        ) as _protocol:
            _reader = Transfer(
                _protocol, show_process_bar_fun=ProgressRate.show_cmd_process_bar,
                process_bar_label=_tips,
                thread_interval=0.0
            )
            _status = _reader.start(wait_finished=True)
            self.assertTrue(
                _status == 'finished', msg="本地文件复制-%s: %s" % (_tips, _status)
            )

        # 单线程-暂停重复
        _tips = '单线程-暂停重复'
        with LocalProtocol(
            _temp_file, _copy_file, is_resume=True, is_overwrite=True,
            cache_size=2
        ) as _protocol:
            _reader = Transfer(
                _protocol, show_process_bar_fun=ProgressRate.show_cmd_process_bar,
                process_bar_label=_tips,
                thread_interval=0.1
            )
            _status = _reader.start()
            time.sleep(1)
            _reader.stop()
            self.assertTrue(
                _reader.status == 'stop', msg="本地文件复制-%s(暂停): %s" % (_tips, _reader.status)
            )
            _reader.thread_interval = 0.0
            _status = _reader.start(wait_finished=True)
            self.assertTrue(
                _status == 'finished', msg="本地文件复制-%s: %s" % (_tips, _status)
            )

        # 单线程-停止后续传
        _tips = '单线程-停止后续传'
        with LocalProtocol(
            _temp_file, _copy_file, is_resume=True, is_overwrite=True,
            cache_size=2
        ) as _protocol:
            _reader = Transfer(
                _protocol, show_process_bar_fun=ProgressRate.show_cmd_process_bar,
                process_bar_label=_tips,
                thread_interval=0.1
            )
            _status = _reader.start()
            time.sleep(1)
            _reader.stop()
        self.assertTrue(
            _reader.status == 'stop', msg="本地文件复制-%s(暂停): %s" % (_tips, _reader.status)
        )
        # 续传处理
        with LocalProtocol(
            _temp_file, _copy_file, is_resume=True, is_overwrite=True,
            cache_size=2
        ) as _protocol:
            _reader = Transfer(
                _protocol, show_process_bar_fun=ProgressRate.show_cmd_process_bar,
                process_bar_label=_tips,
                thread_interval=0.0
            )
            _status = _reader.start(wait_finished=True)
            self.assertTrue(
                _status == 'finished', msg="本地文件复制-%s: %s" % (_tips, _status)
            )

        # 多线程
        _tips = '多线程'
        with LocalProtocol(
            _temp_file, _copy_file, is_resume=True, is_overwrite=True,
            cache_size=2, thread_num=200
        ) as _protocol:
            _reader = Transfer(
                _protocol, show_process_bar_fun=ProgressRate.show_cmd_process_bar,
                process_bar_label=_tips,
                thread_interval=0.0
            )
            _status = _reader.start(wait_finished=True)
            self.assertTrue(
                _status == 'finished', msg="本地文件复制-%s: %s" % (_tips, _status)
            )

        # 多线程-缓存大于文件大小
        _tips = '多线程-缓存大于文件大小'
        with LocalProtocol(
            _temp_file, _copy_file, is_resume=True, is_overwrite=True,
            thread_num=5
        ) as _protocol:
            _reader = Transfer(
                _protocol, show_process_bar_fun=ProgressRate.show_cmd_process_bar,
                process_bar_label=_tips,
                thread_interval=0.0
            )
            _status = _reader.start(wait_finished=True)
            self.assertTrue(
                _status == 'finished', msg="本地文件复制-%s: %s" % (_tips, _status)
            )

        # 多线程-每次传输块大小大于文件
        _tips = '多线程-每次传输块大小大于文件'
        with LocalProtocol(
            _temp_file, _copy_file, is_resume=True, is_overwrite=True,
            thread_num=5, block_size=600000
        ) as _protocol:
            _reader = Transfer(
                _protocol, show_process_bar_fun=ProgressRate.show_cmd_process_bar,
                process_bar_label=_tips,
                thread_interval=0.0
            )
            _status = _reader.start(wait_finished=True)
            self.assertTrue(
                _status == 'finished', msg="本地文件复制-%s: %s" % (_tips, _status)
            )

        # 多线程-暂停重复
        _tips = '多线程-暂停重复'
        with LocalProtocol(
            _temp_file, _copy_file, is_resume=True, is_overwrite=True,
            cache_size=2, thread_num=5
        ) as _protocol:
            _reader = Transfer(
                _protocol, show_process_bar_fun=ProgressRate.show_cmd_process_bar,
                process_bar_label=_tips,
                thread_interval=0.3
            )
            _status = _reader.start()
            time.sleep(1)
            _reader.stop()
            self.assertTrue(
                _reader.status == 'stop', msg="本地文件复制-%s(暂停): %s" % (_tips, _reader.status)
            )
            _reader.thread_interval = 0.0
            _status = _reader.start(wait_finished=True)
            if _status != 'finished':
                print(NetTool.get_file_md5(_temp_file))
                print(NetTool.get_file_md5(_copy_file + '.tmp'))
            self.assertTrue(
                _status == 'finished', msg="本地文件复制-%s: %s" % (_tips, _status)
            )

        # 多线程-停止后续传
        _tips = '多线程-停止后续传'
        with LocalProtocol(
            _temp_file, _copy_file, is_resume=True, is_overwrite=True,
            cache_size=2, thread_num=5
        ) as _protocol:
            _reader = Transfer(
                _protocol, show_process_bar_fun=ProgressRate.show_cmd_process_bar,
                process_bar_label=_tips,
                thread_interval=0.3
            )
            _status = _reader.start()
            time.sleep(1)
            _reader.stop()
        self.assertTrue(
            _reader.status == 'stop', msg="本地文件复制-%s(暂停): %s" % (_tips, _reader.status)
        )

        # 续传处理
        with LocalProtocol(
            _temp_file, _copy_file, is_resume=True, is_overwrite=True,
            cache_size=2, thread_num=5
        ) as _protocol:
            _reader = Transfer(
                _protocol, show_process_bar_fun=ProgressRate.show_cmd_process_bar,
                process_bar_label=_tips,
                thread_interval=0.0
            )
            _status = _reader.start(wait_finished=True)
            if _status != 'finished':
                print(NetTool.get_file_md5(_temp_file))
                print(NetTool.get_file_md5(_copy_file + '.tmp'))

            print(_status)
            self.assertTrue(
                _status == 'finished', msg="本地文件复制-%s: %s" % (_tips, _status)
            )

    def test_local_to_grpc(self):
        if not TEST_FLAG['test_local_to_grpc']:
            return

        print('测试本地gRpc推送远程')

        # DebugTool.set_debug(set_on=True)
        _copy_file = os.path.join(_temp_path, 'local_to_grpc.bin')

        # 删除临时文件
        if os.path.exists(_copy_file):
            FileTool.remove_file(_copy_file)
        for _ext in ('.lock', '.tmp', '.info'):
            if os.path.exists(_copy_file + _ext):
                FileTool.remove_file(_copy_file + _ext)

        # 连接参数
        _connect_para = SimpleGRpcConnection.generate_connect_para(
            conn_str='127.0.0.1:50051'
        )

        # 单线程-缓存大于文件大小
        _tips = '单线程-缓存大于文件大小'
        with GRpcPushProtocol(
            _temp_file, _copy_file, is_resume=True, is_overwrite=True,
            block_size=40960,
            connect_para=_connect_para
        ) as _protocol:
            _reader = Transfer(
                _protocol, show_process_bar_fun=ProgressRate.show_cmd_process_bar,
                process_bar_label=_tips,
                thread_interval=0.0
            )
            _status = _reader.start(wait_finished=True)
            self.assertTrue(
                _status == 'finished', msg="本地gRpc推送-%s: %s" % (_tips, _status)
            )

        # 单线程-缓存小于文件大小
        _tips = '单线程-缓存小于文件大小'
        with GRpcPushProtocol(
            _temp_file, _copy_file, is_resume=True, is_overwrite=True,
            cache_size=2, block_size=40960,
            connect_para=_connect_para
        ) as _protocol:
            _reader = Transfer(
                _protocol, show_process_bar_fun=ProgressRate.show_cmd_process_bar,
                process_bar_label=_tips,
                thread_interval=0.0
            )
            _status = _reader.start(wait_finished=True)
            self.assertTrue(
                _status == 'finished', msg="本地gRpc推送-%s: %s" % (_tips, _status)
            )

        # 单线程-暂停重复
        _tips = '单线程-暂停重复'
        with GRpcPushProtocol(
            _temp_file, _copy_file, is_resume=True, is_overwrite=True,
            cache_size=2, block_size=40960,
            connect_para=_connect_para
        ) as _protocol:
            _reader = Transfer(
                _protocol, show_process_bar_fun=ProgressRate.show_cmd_process_bar,
                process_bar_label=_tips,
                thread_interval=0.1
            )
            _status = _reader.start()
            time.sleep(1)
            _reader.stop()
            self.assertTrue(
                _reader.status == 'stop', msg="本地gRpc推送-%s(暂停): %s" % (_tips, _reader.status)
            )
            _reader.thread_interval = 0.0
            _status = _reader.start(wait_finished=True)
            self.assertTrue(
                _status == 'finished', msg="本地gRpc推送-%s: %s" % (_tips, _status)
            )

        # 单线程-停止后续传
        _tips = '单线程-停止后续传'
        with GRpcPushProtocol(
            _temp_file, _copy_file, is_resume=True, is_overwrite=True,
            cache_size=2, block_size=40960,
            connect_para=_connect_para
        ) as _protocol:
            _reader = Transfer(
                _protocol, show_process_bar_fun=ProgressRate.show_cmd_process_bar,
                process_bar_label=_tips,
                thread_interval=0.1
            )
            _status = _reader.start()
            time.sleep(1)
            _reader.stop()
        self.assertTrue(
            _reader.status == 'stop', msg="本地gRpc推送-%s(暂停): %s" % (_tips, _reader.status)
        )
        # 续传处理
        with GRpcPushProtocol(
            _temp_file, _copy_file, is_resume=True, is_overwrite=True,
            cache_size=2, block_size=40960,
            connect_para=_connect_para
        ) as _protocol:
            _reader = Transfer(
                _protocol, show_process_bar_fun=ProgressRate.show_cmd_process_bar,
                process_bar_label=_tips,
                thread_interval=0.0
            )
            _status = _reader.start(wait_finished=True)
            self.assertTrue(
                _status == 'finished', msg="本地gRpc推送-%s: %s" % (_tips, _status)
            )

        # 多线程
        _tips = '多线程'
        with GRpcPushProtocol(
            _temp_file, _copy_file, is_resume=True, is_overwrite=True,
            cache_size=2, thread_num=230, block_size=40960,
            connect_para=_connect_para
        ) as _protocol:
            _reader = Transfer(
                _protocol, show_process_bar_fun=ProgressRate.show_cmd_process_bar,
                process_bar_label=_tips,
                thread_interval=0.0
            )
            _status = _reader.start(wait_finished=True)
            self.assertTrue(
                _status == 'finished', msg="本地gRpc推送-%s: %s" % (_tips, _status)
            )

        # 多线程-缓存大于文件大小
        _tips = '多线程-缓存大于文件大小'
        with GRpcPushProtocol(
            _temp_file, _copy_file, is_resume=True, is_overwrite=True,
            thread_num=5, block_size=40960,
            connect_para=_connect_para
        ) as _protocol:
            _reader = Transfer(
                _protocol, show_process_bar_fun=ProgressRate.show_cmd_process_bar,
                process_bar_label=_tips,
                thread_interval=0.0
            )
            _status = _reader.start(wait_finished=True)
            self.assertTrue(
                _status == 'finished', msg="本地gRpc推送-%s: %s" % (_tips, _status)
            )

        # 多线程-每次传输块大小大于文件
        _tips = '多线程-每次传输块大小大于文件'
        with GRpcPushProtocol(
            _temp_file, _copy_file, is_resume=True, is_overwrite=True,
            thread_num=5, block_size=900000,
            connect_para=_connect_para
        ) as _protocol:
            _reader = Transfer(
                _protocol, show_process_bar_fun=ProgressRate.show_cmd_process_bar,
                process_bar_label=_tips,
                thread_interval=0.0
            )
            _status = _reader.start(wait_finished=True)
            self.assertTrue(
                _status == 'finished', msg="本地gRpc推送-%s: %s" % (_tips, _status)
            )

        # 多线程-暂停重复
        _tips = '多线程-暂停重复'
        with GRpcPushProtocol(
            _temp_file, _copy_file, is_resume=True, is_overwrite=True,
            cache_size=2, thread_num=5, block_size=40960,
            connect_para=_connect_para
        ) as _protocol:
            _reader = Transfer(
                _protocol, show_process_bar_fun=ProgressRate.show_cmd_process_bar,
                process_bar_label=_tips,
                thread_interval=0.3
            )
            _status = _reader.start()
            time.sleep(1)
            _reader.stop()
            self.assertTrue(
                _reader.status == 'stop', msg="本地gRpc推送-%s(暂停): %s" % (_tips, _reader.status)
            )
            _reader.thread_interval = 0.0
            _status = _reader.start(wait_finished=True)
            if _status != 'finished':
                print(NetTool.get_file_md5(_temp_file))
                print(NetTool.get_file_md5(_copy_file + '.tmp'))
            self.assertTrue(
                _status == 'finished', msg="本地gRpc推送-%s: %s" % (_tips, _status)
            )

        # 多线程-停止后续传
        _tips = '多线程-停止后续传'
        with GRpcPushProtocol(
            _temp_file, _copy_file, is_resume=True, is_overwrite=True,
            cache_size=2, thread_num=5, block_size=40960,
            connect_para=_connect_para
        ) as _protocol:
            _reader = Transfer(
                _protocol, show_process_bar_fun=ProgressRate.show_cmd_process_bar,
                process_bar_label=_tips,
                thread_interval=0.3
            )
            _status = _reader.start()
            time.sleep(1)
            _reader.stop()
        self.assertTrue(
            _reader.status == 'stop', msg="本地gRpc推送-%s(暂停): %s" % (_tips, _reader.status)
        )

        # 续传处理
        with GRpcPushProtocol(
            _temp_file, _copy_file, is_resume=True, is_overwrite=True,
            cache_size=2, thread_num=5, block_size=40960,
            connect_para=_connect_para
        ) as _protocol:
            _reader = Transfer(
                _protocol, show_process_bar_fun=ProgressRate.show_cmd_process_bar,
                process_bar_label=_tips,
                thread_interval=0.0
            )
            _status = _reader.start(wait_finished=True)
            if _status != 'finished':
                print(NetTool.get_file_md5(_temp_file))
                print(NetTool.get_file_md5(_copy_file + '.tmp'))

            self.assertTrue(
                _status == 'finished', msg="本地gRpc推送-%s: %s" % (_tips, _status)
            )

    def test_grpc_to_local(self):
        if not TEST_FLAG['test_grpc_to_local']:
            return

        print('测试获取gRpc远程文件')

        # DebugTool.set_debug(set_on=True)
        _copy_file = os.path.join(_temp_path, 'grpc_to_local.bin')

        # 删除临时文件
        if os.path.exists(_copy_file):
            FileTool.remove_file(_copy_file)
        for _ext in ('.lock', '.tmp', '.info'):
            if os.path.exists(_copy_file + _ext):
                FileTool.remove_file(_copy_file + _ext)

        # 连接参数
        _connect_para = SimpleGRpcConnection.generate_connect_para(
            conn_str='127.0.0.1:50051'
        )

        # 单线程-缓存大于文件大小
        _tips = '单线程-缓存大于文件大小'
        with GRpcPullProtocol(
            _temp_file, _copy_file, is_resume=True, is_overwrite=True,
            block_size=40960,
            connect_para=_connect_para
        ) as _protocol:
            _reader = Transfer(
                _protocol, show_process_bar_fun=ProgressRate.show_cmd_process_bar,
                process_bar_label=_tips,
                thread_interval=0.0
            )
            _status = _reader.start(wait_finished=True)
            self.assertTrue(
                _status == 'finished', msg="本地gRpc推送-%s: %s" % (_tips, _status)
            )

        # 单线程-缓存小于文件大小
        _tips = '单线程-缓存小于文件大小'
        with GRpcPullProtocol(
            _temp_file, _copy_file, is_resume=True, is_overwrite=True,
            cache_size=2, block_size=40960,
            connect_para=_connect_para
        ) as _protocol:
            _reader = Transfer(
                _protocol, show_process_bar_fun=ProgressRate.show_cmd_process_bar,
                process_bar_label=_tips,
                thread_interval=0.0
            )
            _status = _reader.start(wait_finished=True)
            self.assertTrue(
                _status == 'finished', msg="本地gRpc推送-%s: %s" % (_tips, _status)
            )

        # 单线程-暂停重复
        _tips = '单线程-暂停重复'
        with GRpcPullProtocol(
            _temp_file, _copy_file, is_resume=True, is_overwrite=True,
            cache_size=2, block_size=40960,
            connect_para=_connect_para
        ) as _protocol:
            _reader = Transfer(
                _protocol, show_process_bar_fun=ProgressRate.show_cmd_process_bar,
                process_bar_label=_tips,
                thread_interval=0.1
            )
            _status = _reader.start()
            time.sleep(1)
            _reader.stop()
            self.assertTrue(
                _reader.status == 'stop', msg="本地gRpc推送-%s(暂停): %s" % (_tips, _reader.status)
            )
            _reader.thread_interval = 0.0
            _status = _reader.start(wait_finished=True)
            self.assertTrue(
                _status == 'finished', msg="本地gRpc推送-%s: %s" % (_tips, _status)
            )

        # 单线程-停止后续传
        _tips = '单线程-停止后续传'
        with GRpcPullProtocol(
            _temp_file, _copy_file, is_resume=True, is_overwrite=True,
            cache_size=2, block_size=40960,
            connect_para=_connect_para
        ) as _protocol:
            _reader = Transfer(
                _protocol, show_process_bar_fun=ProgressRate.show_cmd_process_bar,
                process_bar_label=_tips,
                thread_interval=0.1
            )
            _status = _reader.start()
            time.sleep(1)
            _reader.stop()
        self.assertTrue(
            _reader.status == 'stop', msg="本地gRpc推送-%s(暂停): %s" % (_tips, _reader.status)
        )
        # 续传处理
        with GRpcPullProtocol(
            _temp_file, _copy_file, is_resume=True, is_overwrite=True,
            cache_size=2, block_size=40960,
            connect_para=_connect_para
        ) as _protocol:
            _reader = Transfer(
                _protocol, show_process_bar_fun=ProgressRate.show_cmd_process_bar,
                process_bar_label=_tips,
                thread_interval=0.0
            )
            _status = _reader.start(wait_finished=True)
            self.assertTrue(
                _status == 'finished', msg="本地gRpc推送-%s: %s" % (_tips, _status)
            )

        # 多线程
        _tips = '多线程'
        with GRpcPullProtocol(
            _temp_file, _copy_file, is_resume=True, is_overwrite=True,
            cache_size=2, thread_num=230, block_size=40960,
            connect_para=_connect_para
        ) as _protocol:
            _reader = Transfer(
                _protocol, show_process_bar_fun=ProgressRate.show_cmd_process_bar,
                process_bar_label=_tips,
                thread_interval=0.0
            )
            _status = _reader.start(wait_finished=True)
            self.assertTrue(
                _status == 'finished', msg="本地gRpc推送-%s: %s" % (_tips, _status)
            )

        # 多线程-缓存大于文件大小
        _tips = '多线程-缓存大于文件大小'
        with GRpcPullProtocol(
            _temp_file, _copy_file, is_resume=True, is_overwrite=True,
            thread_num=5, block_size=40960,
            connect_para=_connect_para
        ) as _protocol:
            _reader = Transfer(
                _protocol, show_process_bar_fun=ProgressRate.show_cmd_process_bar,
                process_bar_label=_tips,
                thread_interval=0.0
            )
            _status = _reader.start(wait_finished=True)
            self.assertTrue(
                _status == 'finished', msg="本地gRpc推送-%s: %s" % (_tips, _status)
            )

        # 多线程-每次传输块大小大于文件
        _tips = '多线程-每次传输块大小大于文件'
        with GRpcPullProtocol(
            _temp_file, _copy_file, is_resume=True, is_overwrite=True,
            thread_num=5, block_size=900000,
            connect_para=_connect_para
        ) as _protocol:
            _reader = Transfer(
                _protocol, show_process_bar_fun=ProgressRate.show_cmd_process_bar,
                process_bar_label=_tips,
                thread_interval=0.0
            )
            _status = _reader.start(wait_finished=True)
            self.assertTrue(
                _status == 'finished', msg="本地gRpc推送-%s: %s" % (_tips, _status)
            )

        # 多线程-暂停重复
        _tips = '多线程-暂停重复'
        with GRpcPullProtocol(
            _temp_file, _copy_file, is_resume=True, is_overwrite=True,
            cache_size=2, thread_num=5, block_size=40960,
            connect_para=_connect_para
        ) as _protocol:
            _reader = Transfer(
                _protocol, show_process_bar_fun=ProgressRate.show_cmd_process_bar,
                process_bar_label=_tips,
                thread_interval=0.3
            )
            _status = _reader.start()
            time.sleep(1)
            _reader.stop()
            self.assertTrue(
                _reader.status == 'stop', msg="本地gRpc推送-%s(暂停): %s" % (_tips, _reader.status)
            )
            _reader.thread_interval = 0.0
            _status = _reader.start(wait_finished=True)
            if _status != 'finished':
                print(NetTool.get_file_md5(_temp_file))
                print(NetTool.get_file_md5(_copy_file + '.tmp'))
            self.assertTrue(
                _status == 'finished', msg="本地gRpc推送-%s: %s" % (_tips, _status)
            )

        # 多线程-停止后续传
        _tips = '多线程-停止后续传'
        with GRpcPullProtocol(
            _temp_file, _copy_file, is_resume=True, is_overwrite=True,
            cache_size=2, thread_num=5, block_size=40960,
            connect_para=_connect_para
        ) as _protocol:
            _reader = Transfer(
                _protocol, show_process_bar_fun=ProgressRate.show_cmd_process_bar,
                process_bar_label=_tips,
                thread_interval=0.3
            )
            _status = _reader.start()
            time.sleep(1)
            _reader.stop()
        self.assertTrue(
            _reader.status == 'stop', msg="本地gRpc推送-%s(暂停): %s" % (_tips, _reader.status)
        )

        # 续传处理
        with GRpcPullProtocol(
            _temp_file, _copy_file, is_resume=True, is_overwrite=True,
            cache_size=2, thread_num=5, block_size=40960,
            connect_para=_connect_para
        ) as _protocol:
            _reader = Transfer(
                _protocol, show_process_bar_fun=ProgressRate.show_cmd_process_bar,
                process_bar_label=_tips,
                thread_interval=0.0
            )
            _status = _reader.start(wait_finished=True)
            if _status != 'finished':
                print(NetTool.get_file_md5(_temp_file))
                print(NetTool.get_file_md5(_copy_file + '.tmp'))

            self.assertTrue(
                _status == 'finished', msg="本地gRpc推送-%s: %s" % (_tips, _status)
            )


if __name__ == '__main__':
    unittest.main()

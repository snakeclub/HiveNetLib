import sys
import os
import time
# 根据当前文件路径将包路径纳入，在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir, os.path.pardir)))
from HiveNetLib.simple_log import Logger
from HiveNetLib.simple_restful.socketio import SocketIOServer, SocketIOClient


# 日志配置
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


# 日志对象
LOGGER = Logger.create_logger_by_dict(_logger_config)


# SocketIO处理函数
def server_on_connect():
    """
    客户端连接
    """
    print('server: client connect!')


def server_on_disconnect():
    print('server: client disconnect!')


def sever_on_add(data):
    """
    加法运算并返回结果

    @param {dict} data - 要加的变量字典
    """
    print('server: get ', data)
    _num = 0
    for _value in data.values():
        _num += _value

    # 返回结果
    SocketIOServer.emit('resp_add', {'data': _num})


# SocketIOClient处理函数
def client_on_connect():
    """
    客户端连接
    """
    print('client: client connect!')


def client_on_disconnect():
    print('client: client disconnect!')


class Test():
    # 整个Test类的开始和结束执行
    @classmethod
    def setUpClass(cls):
        # 启动服务
        _sever = SocketIOServer(
            'test_sio_server', server_config={
                'debug': True,
                'flask_run': {
                    'host': '127.0.0.1', 'port': 5001
                },
            },
            logger=LOGGER
        )

        # 绑定服务函数
        _sever.bind_on_event('connect', server_on_connect)
        _sever.bind_on_event('disconnect', server_on_disconnect)
        _sever.bind_on_event('add', sever_on_add)

        # 启动服务
        _sever.start(is_asyn=True)

    @classmethod
    def tearDownClass(cls):
        # 停止服务
        SocketIOServer.get_init_flask_server(app_name='test_sio_server').stop()
        pass

    @classmethod
    def test(cls):
        # 进行测试
        time.sleep(3)

        def client_on_resp_add(data):
            print('client: resp add ', data)

        _client = SocketIOClient()
        _client.bind_bg_task_on_connected(
            _client.emit_bg_task, before_func=client_on_connect
        )
        _client.bind_on_event('disconnect', client_on_disconnect)
        _client.bind_on_event('resp_add', client_on_resp_add)
        _client.connect('http://127.0.0.1:5001', is_asyn=True)
        _client.emit_bg(
            'add', {'a': 10, 'b': 15}
        )
        time.sleep(5)
        _client.disconnect()


if __name__ == '__main__':
    Test.setUpClass()

    Test.test()

    time.sleep(5)
    Test.tearDownClass()

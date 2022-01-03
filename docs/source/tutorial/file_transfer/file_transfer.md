# file_transfer使用说明

file_transfer库实现了文件传输（本地或网络）的基本框架，支持快速扩展不同通讯协议下的文件传输功能。



## 基本设计

文件传输库的核心模块包括：

- file_transfer.saver：文件保存模块，该模块实现了 TransferSaver（文件保存对象）类，负责将传输中收到的文件数据保存为目标文件。该对象支持文件断点续传、多并发保存、文件MD5校验等功能。
- file_transfer.protocol：文件传输协议模块，该模块定义了 ProtocolFw（文件传输协议框架）类，用于扩展针对不同的源文件数据读取（例如本地文件读取、远程url文件读取等）、目标文件保存（例如本地文件保存，通过RPC通讯保存等）的协议和方法，来支持各类不同情况的文件传输。文件传输协议类负责打开和关闭文件保存对象，以及实现数据获取和传输的具体处理。protocol 模块还提供了本地文件复制的 ProtocolFw 实现类 LocalProtocol （本地文件传输至本地的传输协议），可作为扩展文件传输协议的开发参考。
- file_transfer.transfer：文件传输控制模块，该模块实现了 Transfer（文件传输控制对象）类，负责发起文件传输处理，并控制数据传输的过程。Transfer 可通过搭配不同的 ProtocolFw 实现来支持各种各样的传输需求。
- file_transfer.exceptions：文件传输库的自定义异常模块，该模块定义了文件传输过程需要用到的各种自定义异常类。

此外，文件传输库还实现了基于 simple_grpc的远程文件传输扩展模块 file_transfer.extend_protocol.grpc，包括将文件推送至远程服务器（push）和从远程服务器获取文件（pull）两种模式。



## 使用步骤

1、选取或自主实现文件传输协议类

可以选取文件传输库已实现的 LocalProtocol 或 extend_protocol.grpc 已实现的远程传输协议类，也可以通过继承扩展 file_transfer.protocol.ProtocolFw  实现自己的文件传输协议类。

注：自主实现文件传输协议类可参考 LocalProtocol，也可以采用直接继承 LocalProtocol 的方式实现，来减少一些重复代码。



2、通过以下代码步骤发起传输处理

```
# 步骤1.初始化文件传输协议类，该类会同步打开文件保存对象，并在传输完成关闭文件保存对象，可以通过with方式在传输完成自动关闭
with LocalProtocol(
    _temp_file, _copy_file, is_resume=True, is_overwrite=True,
    block_size=600000, auto_expand=False
) as _protocol:
    # 步骤2.初始化文件传输控制类，指定文件传输协议对象，以及进度显示函数及参数
    _reader = Transfer(
        _protocol, show_process_bar_fun=ProgressRate.show_cmd_process_bar,
        process_bar_label='文件传输',
        thread_interval=0.0
    )
    # 步骤3.启动传输处理，如果希望同步等待传输结束，可指定 wait_finished 参数为 True
    _status = _reader.start(wait_finished=True)
```



3、如果需要能控制传输暂停，请将 Transfer 的 start 函数的 wait_finished 参数置为 False，然后在任意时间停止传输，例如：

```
...
		# 异步方式传输
		_reader.start(wait_finished=False)
		...
		# 停止传输
		_reader.stop()
```

注：如果停止传输后未关闭文件传输协议类（ProtocolFw），则可以直接再用start函数续传；如果关闭了文件传输协议类，则需要以初始化文件传输协议类、文件传输控制类的方式重新开始传输任务，文件传输协议类可根据传入参数，以及目标目录中的临时文件判断是否断点续传。



## gRpc远程传输的使用步骤

1、在远端服务器启动gRpc服务

```
...
# 引用simple_grpc包及file_transfer的grpc服务生成类
from HiveNetLib.simple_grpc.grpc_server import SimpleGRpcServer
from HiveNetLib.file_transfer.extend_protocol.grpc import GRpcPullServicerGenerater, GRpcPushServicerGenerater

...
# 创建grpc服务
_server_no_ssl_no_zoo_opts = SimpleGRpcServer.generate_server_opts(
    ip='127.0.0.1',
    port=50051,
    max_workers=50,
    max_connect=400,
    is_health_check=True
)
_server_no_ssl_no_zoo = SimpleGRpcServer(
    server_name='ServerNoSslNoZoo',
    logger=_logger, log_level=simple_log.INFO
)

# 初始化服务生成对象，按实际需要确定要初始化哪个服务生成对象（也可以都要）
_push_services = GRpcPushServicerGenerater(
    work_dir=_temp_path, lock_in_work_dir=True, logger=_logger, is_use_global_logger=False
)
_pull_services = GRpcPullServicerGenerater(
    work_dir=_temp_path, lock_in_work_dir=True, logger=_logger, is_use_global_logger=False
)

# 启动服务并将服务设定进grpc服务中（servicer_list参数），按实际需要看要将哪个服务放进来
_server_no_ssl_no_zoo.start_server(
    server_opts=_server_no_ssl_no_zoo_opts, servicer_list={
        'servicer_file_transfer_push': _push_services.get_servicer(),
        'servicer_file_transfer_pull': _pull_services.get_servicer()
    }, is_wait=True
)
```



2、在本地端执行文件传输处理

```
...
# 引用simple_grpc包及file_transfer的grpc的文件传输协议类
from HiveNetLib.simple_grpc.grpc_client import SimpleGRpcConnection
from HiveNetLib.file_transfer.extend_protocol.grpc import GRpcPushProtocol, GRpcPullProtocol
from HiveNetLib.prompt_plus import ProgressRate  # 进度显示类

...
# grpc连接参数
_connect_para = SimpleGRpcConnection.generate_connect_para(
    conn_str='127.0.0.1:50051'
)

# 本地文件传输到远程的模式（push）
with GRpcPushProtocol(
    _temp_file, _copy_file, is_resume=True, is_overwrite=True,
    block_size=40960,
    connect_para=_connect_para
) as _protocol:
    _reader = Transfer(
        _protocol, show_process_bar_fun=ProgressRate.show_cmd_process_bar,
        process_bar_label='push模式文件传输',
        thread_interval=0.0
    )
    _status = _reader.start(wait_finished=True)

# 远程文件传输到本地的模式（pull）
with GRpcPullProtocol(
    _temp_file, _copy_file, is_resume=True, is_overwrite=True,
    cache_size=2, block_size=40960,
    connect_para=_connect_para
) as _protocol:
    _reader = Transfer(
        _protocol, show_process_bar_fun=ProgressRate.show_cmd_process_bar,
        process_bar_label='pull模式文件传输',
        thread_interval=0.0
    )
    _status = _reader.start(wait_finished=True)
```


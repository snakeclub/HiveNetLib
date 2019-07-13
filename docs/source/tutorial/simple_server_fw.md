# simple_server_fw使用说明

模块名：HiveNetLib.simple_server_fw

simple_server_fw是服务启停服务处理的基础框架，用于支持各类服务启停处理的简单代码实现。



## 使用示例

1、实现类继承SimpleServerFW框架类

```
class XSever(SimpleServerFW):
	# 实现类的代码
```

2、重载“\_start_server_self ”、“\_server_run_self ”、“\_stop_server_predeal_self”、“\_stop_server_end_self”函数分别实现服务的启动和停止处理（如无特殊处理逻辑可以不重载），服务的处理流程伪代码如下：

```
start server：
	run _start_server_self
	while no stop single
		run _server_run_self

stop server:
	while true
		run _stop_server_predeal_self
		when result is true
			break
	run _stop_server_end_self
```

3、如果需要改变服务类的初始化参数，可以重载“\_\_init\_\_”函数

```
def __init__(self, ...):
	# 执行自己的初始化处理代码
	
	SimpleServerFW.__init__(self, ...)  # 执行框架的初始化函数实现框架类属性的初始化
```

4、如果需要在启动函数或停止函数上增加参数，可以重载相应的函数

```
def start_server(self, ...):
	# 执行自己的处理代码
	
	return SimpleServerFW.start_server(self, is_wait=?)  # 执行框架的启动服务函数
```

5、使用服务类

```
# 实例化对象
server = XSever(...)

# 启动服务
server.start_server()

# 查看服务启动状态
print(server.server_run_status)

# 关闭服务
server.stop_server()
```



## 主要重载函数说明

### _start_server_self 

自定义服务启动函数，执行服务的启动处理，例如启动网络监听，注意该函数不应阻塞

```
	def _start_server_self(self, tid):
        """
        自定义服务启动函数，实现类可重载该函数加入自己的处理逻辑

        @param {int} tid - 线程id

        @returns {CResult} - 启动结果:
            result.code ：'00000'-成功，其他值为失败
            result.server_info ：启动成功后的服务对象，用于传递到后续的服务处理函数

        """
        _result = CResult(code='00000')  # 成功
        _result.server_info = NullObj()
        with ExceptionTool.ignored_cresult(_result):
            # 可在该部分实现自定义逻辑
            pass
        # 返回处理结果
        return _result
```



### _server_run_self 

自定义服务处理函数，启动服务后框架将自动循环执行该处理函数，这里可以放置需循环处理的服务逻辑，注意该函数不应阻塞

```
	def _server_run_self(self, tid, server_info):
        """
        自定义服务处理函数，实现类可重载该函数加入自己的处理逻辑（例如进行实际业务处理）
            注意：该函数每次只处理一次就应该返回，且应该实现异常处理

        @param {int} tid - 线程id
        @param {object} server_info - _start_server_self函数生成的server_info信息

        @returns {CResult} - 处理结果:
            result.code ：'00000'-成功，其他值为失败
            result.is_finished ：处理是否已完成，True - 已处理完成，False - 未完成，需循环再处理

        """
        _result = CResult(code='00000')  # 成功
        _result.is_finished = False
        with ExceptionTool.ignored_cresult(
            _result,
            logger=self._logger,
            self_log_msg='[%s][NAME:%s]%s: ' % (
                self._server_log_prefix, self._server_name, _('service run error')),
            force_log_level=EnumLogLevel.ERROR
        ):
            # 可在该部分实现自定义逻辑
            pass
        # 返回处理结果
        return _result
```



### _stop_server_predeal_self

自定义服务停止前处理函数，在非强制关闭服务的情况下，框架将循环执行该函数，用于进行关闭前的处理，例如结束线程回收资源

```
	def _stop_server_predeal_self(self, tid, server_info):
        """
        自定义服务停止前处理函数，实现类可重载该函数加入自己的处理逻辑（例如结束子线程）

        @param {int} tid - 线程id
        @param {object} server_info - _start_server_self函数生成的server_info信息

        @returns {CResult} - 处理结果:
            result.code ：'00000'-成功，其他值为失败
            result.is_finished ：处理是否已完成，True - 已处理完成，False - 未完成，需循环再处理

        """
        _result = CResult(code='00000')  # 成功
        _result.is_finished = True
        with ExceptionTool.ignored_cresult(
            _result,
            logger=self._logger,
            self_log_msg='[%s-STOPING][NAME:%s]%s: ' % (
                self._server_log_prefix, self._server_name, _('stop service predeal error')),
            force_log_level=EnumLogLevel.ERROR
        ):
            # 可在该部分实现自定义逻辑
            pass
        # 返回处理结果
        return _result
```



### _stop_server_end_self 

自定义服务停止后处理函数，在服务循环运行停止后，执行该函数，可在该函数执行实际的服务停止代码

```
	def _stop_server_end_self(self, tid):
        """
        自定义服务停止后处理函数，实现类可重载该函数加入自己的处理逻辑
            注意：函数应屏蔽异常

        @param {int} tid - 线程id

        """
        _result = CResult(code='00000')  # 成功
        with ExceptionTool.ignored_cresult(
            _result,
            logger=self._logger,
            self_log_msg='[%s-STOPING][NAME:%s]%s: ' % (
                self._server_log_prefix, self._server_name, _('stop service end fun error')),
            force_log_level=EnumLogLevel.ERROR
        ):
            # 可在该部分实现自定义逻辑
            pass
        # 返回处理结果
        return
```



## 原生初始化参数说明

```
		@param {Logger} logger=None - 日志对象，服务过程中通过该函数写日志:
            可以为标准的logging日志库对象，也可以为simple_log对象，但要求对象实现:
            标准的info、debug、warning、error、critical五个日志方法
        @param {function} server_status_info_fun=None - 外围传入的服务状态变更通知函数对象，当服务状态发生变更时通过:
            该函数通知调用方；形式为fun(server_status, result):
            其中server_status为服务器状态EnumServerRunStatus，
            result为CResult通用执行结果对象，自定义属性self_tag为发起方识别标识
        @param {string} self_tag='' - 自定义标识
        @param {EnumLogLevel} log_level=EnumLogLevel.INFO - 处理中正常日志的输出登记级别，默认为INFO，如果不想输出过:
            多日志可以设置为DEBUG
        @param {string} server_log_prefix='SER' - 服务日志记录前缀，记录日志使用，例如[SER-STARTING]...
        @param {string} server_name='Service' - 服务名，记录日志使用
        @param {bool} is_auto_load_i18n=True - 是否自动加载i18n字典，如果继承类有自己的字典，可以重载__init__函数实现装载
        @param {string} trans_file_path='' - 要加载的i18n字典文件路径，如果填空代表程序运行的当前路径
        @param {string} trans_file_prefix='' - 要加载的i18n字典文件前缀
        @param {string} trans_file_encoding='utf-8' - 要加载的i18n字典文件的字符编码
```


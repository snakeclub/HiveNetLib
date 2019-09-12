# connection_pool连接池框架使用说明

模块名：HiveNetLib.connection_pool

connection_pool连接池服务框架定义了标准的连接池处理模型，可基于该模型实现数据库、网络连接的连接池。



## 使用示例

1、实现类继承ConnectionPoolFw框架类

```
class TestPoolClass(ConnectionPoolFw):
	# 实现类的代码
```

2、重载“\_create_connection_self”、“\_close_connection_self”、“\_test_connection_self”、“\_reconnect_self”函数，分别实现新连接的创建、已有连接的关闭、连接有效性的测试、已有连接的重连处理：

```
	def _create_connection_self(self):
        """
        创建一个连接对象（具体类实现）

        @return {object} - 返回有效的连接对象

        @throws {Exception} - 当创建失败或连接无效时应直接抛出异常
        """
        # 实现类重载代码

    def _close_connection_self(self, connection):
        """
        关闭指定的连接对象（具体类实现）

        @param {object} connection - 要关闭的连接对象

        @throws {Exception} - 当关闭失败时应直接抛出异常
        """
        # 实现类重载代码

    def _test_connection_self(self, connection):
        """
        测试指定的连接对象是否有效（具体类实现）

        @param {object} connection - 要测试的连接对象

        @throws {Exception} - 当测试失败时应抛出异常
        """
        # 实现类重载代码

    def _reconnect_self(self, connection):
        """
        对指定对象重新进行连接（具体类实现）

        @param {object} connection - 要重新连接的对象

        @return {object} - 返回有效的连接对象

        @throws {Exception} - 当重连失败时应抛出异常
        """
        # 实现类重载代码
        
```

3、使用连接池

```
# 实例化连接池对象
_pool = TestPoolClass(...)

# 获取连接, 注意获取失败会抛出异常，因此需要考虑异常处理
try:
	_connection = _pool.get_connection()
except TimeoutError:
	# 获取超时
	pass
except:
	...

# 检查连接有效性
if not _pool.test_connection(_connection):
	# 重新连接，注意重新连接失败时会抛出异常
	try:
		_pool.reconnect(_connection)
	except:
		...

# 不再使用连接时释放连接
_pool.free_connection(_connection)
```



## 原生初始化参数说明

```
		@param {NullObj} connect_para - 连接参数，具体参数属性根据实现类指定
        @param {string} name='ConnectionPool' - 连接池名称
        @param {int} maxsize=100 - 最大连接数
        @param {int} minsize=0 - 最小保持连接数
        @param {number} realse_free_time=300 - 自动释放多长时间的空闲无操作连接（单位秒）
        @param {bool} test_on_get=False - 是否在获取连接前检查连接是否有效
        @param {bool} test_on_free=False - 是否在归还连接时检查连接是否有效
        @param {bool} test_while_idle=True - 是否检查空闲连接是否有效
        @param {number} test_idle_time=60 - 自动检查空闲连接有效性的时间间隔（单位秒）
        @param {string} validation_query='' - 检查连接是否有效的查询语句（非数据库类的可以传入检查参数）
        @param {number} get_connection_timeout=0 - 获取连接的等待超时时间（单位秒），0代表不超时
        @param {Logger} logger=None - 日志对象，服务过程中通过该函数写日志:
            可以为标准的logging日志库对象，也可以为simple_log对象，但要求对象实现:
            标准的info、debug、warning、error、critical五个日志方法
        @param {bool} init_break_if_connect_error=True - 如果连接失败则初始化抛出异常
        @param {number} daemon_sleep_time=1 - 守护进程的间隔刷新时间（单位秒）
```


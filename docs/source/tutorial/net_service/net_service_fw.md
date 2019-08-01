# net_service_fw网络服务框架应用

net_service_fw网络服务框架定义了一个标准的网络服务模型，并封装实现了部分网络服务启动、关闭、监听请求及调度具体请求处理线程的功能，以统一网络服务的标准使用方式，以及简化网络服务的开发工作。



## 遵循标准

hivenet_error_code_standards_v1.0.0

hivenet_log_standards_v1.0.0



## 网络服务框架的标准接口（服务端）

### 构造函数（\_\_init\_\_)

几个重要参数说明（详细说明请参看接口文档）

server_status_info_fun ：指定当服务状态变更时所执行的通知函数（让自定义服务及时响应服务状态变更处理）

server_connect_deal_fun ：指定客户端连接成功后，进行报文收发处理的函数（自行实现收发逻辑），注意每次客户端连接后只执行一次该函数，如果需要保持连接，需该函数内部自行实现循环（同时循环中必须检查服务器关闭状态，遇到关闭时必须结束处理）

is_auto_load_i18n ： 是否自动加载i18n字典，基础类会自动加载netservicefw_en.json和netservicefw_zh.json文件到全局多国语言对象中（参考simple_i18n），以支持多国语言；如果需要加载自己的语言字典，可以自己重载\_\_init\_\_方法增加加载操作

### 启动网络服务（start_server）

启动网络服务，根据传入的服务器参数，启动网络服务监听线程。监听线程的处理方式如下：

1、执行自定义的_start_server_without_accept方法进行网络监听，但不获取客户端连接

2、循环调用自定义的_accept_one获取客户端端连接

3、当_accept_one获取到连接后，针对每个客户端连接单独启动独立线程（线程函数__server_connect_thread_fun），该线程再调用构造函数传入的server_connect_deal_fun执行报文收发处理

### 关闭网络服务（stop_server）

关闭已启动的网络服务。

### 获取服务端信息（get_server_info）

获取服务端指定的信息。

### 公开属性

log_level ： 获取或设置输出日志级别

server_opts ： 获取服务器启动参数

self_tag ：获取自定义的服务标识

server_run_status ： 获取服务运行状态

server_run_status_desc ：获取服务运行状态的描述



## 网络服务框架的标准接口（公共）

### 获取数据（recv_data）

从指定的网络对象中获取数据，该方法需由网络服务的具体实现类继承和实现。

### 发送数据（send_data）

向指定的网络对象中发送数据，该方法需由网络服务的具体实现类继承和实现。

### 关闭网络连接（close_connect）

关闭指定的网络连接。

### 连接指定服务（connect_server）

建立与指定服务地址的连接（客户端发起）。

### 获取客户端信息（get_client_info）

获取客户端的指定参数信息。



## 基于框架实现自定义网络服务

1、实现类必须继承NetServiceFW框架类

```
class TcpIpService(NetServiceFW):
	...
```

2、实现以下抽象方法的具体逻辑

_start_server_without_accept ： 启动监听服务，但不获取客户端连接（无需处理轮询监听逻辑）

_accept_one ： 获取一个客户端连接并立即返回（轮询逻辑由框架实现）

recv_data :  获取数据

send_data：发送数据

close_connect： 关闭连接

connect_server： 建立与服务端的连接

get_server_info： 获取服务端信息

get_client_info： 获取客户端信息

3、注意事项

net_info定义：每个自定义网络服务类都应明确net_info的具体定义，该对象用于登记具体的网络处理信息，在各个处理方法中流转，是比较重要的对象



## tcpip_service服务

tcpip_service服务是net_service_fw的一个tcpip协议实现，采用非阻塞的方式实现监听和网络报文的收取，支持超时控制处理。

### net_info定义

```
        net_info.csocket - socket对象
        net_info.laddr 本地地址，地址对象，("IP地址",打开端口)
        net_info.raddr 远端地址，地址对象，("IP地址",打开端口)
        net_info.send_timeout 发送超时时间，单位为毫秒
        net_info.recv_timeout 收取超时时间，单位为毫秒
```

### 服务启动参数定义

```
		_server_opts.ip = ip  # 主机名或IP地址
        _server_opts.port = 8080  # 监听端口
        _server_opts.max_connect = 20  # 允许最大连接数
        _server_opts.recv_timeout = 10000  # 数据接收的超时时间，单位为毫秒
        _server_opts.send_timeout = 10000  # 数据发送的超时时间，单位为毫秒
```



### 使用方法步骤

1、定义网络服务状态变更通知函数

```
	def server_status_info_fun(self, server_status, result):
        self.logger.log(
            logging.INFO,
            (
                "[服务端]"+result.self_tag+"服务状态变更：" +
                str(server_status) +
                "   结果code：" +
                str(result.code) +
                "  描述：" +
                result.msg
            )
        )
        return
```

2、定义网络服务连接报文处理函数

```
	def server_connect_deal_fun(self, thread_id, server_opts, net_info, self_tag):
        self.logger.log(
            logging.INFO,
            (
                "[服务端" +
                self_tag +
                "][" + str(thread_id) +
                "]收到客户端连接：" +
                StringTool.format_obj_property_str(deal_obj=net_info, is_deal_subobj=True)
            )
        )

        # 获取客户端发送的信息，先获取前4个字节
        _read_result = TcpIpService.recv_data(net_info, {'recv_len': 4})
        if _read_result.code != '00000':
            # 获取失败
            self.logger.log(logging.INFO, ("[服务端]获取客户端数据报文头失败，关闭连接："
                                   + str(_read_result.code) + "-" + _read_result.msg))
            TcpIpService.close_connect(net_info)
            return

        _next_read = int.from_bytes(_read_result.data, byteorder='big', signed=False)
        self.logger.log(logging.INFO, "[服务端]获取到客户端4个字节的后续数据长度：" + str(_next_read))

        # 获取后面的数据
        _read_result = TcpIpService.recv_data(net_info, {'recv_len': _next_read})
        if _read_result.code != '00000':
            # 获取失败
            self.logger.log(logging.INFO, ("[服务端]获取客户端数据报文体失败，关闭连接：" +
                                   str(_read_result.code) + "-" + _read_result.msg))
            TcpIpService.close_connect(net_info)
            return

        _read_str = str(_read_result.data, "utf-8")
        self.logger.log(logging.INFO, "[服务端]获取到客户端报文体数据：" + _read_str)

        # 返回内容，先组包
        _ret_str = "处理成功"
        _send_body = bytes(_ret_str, "utf-8")
        _send_head = len(_send_body).to_bytes(4, byteorder='big', signed=False)

        # 发送报文头
        _send_result = TcpIpService.send_data(net_info, _send_head, {})
        if _send_result.code != '00000':
            self.logger.log(logging.INFO, ("[服务端]返回客户端数据报文头失败，关闭连接："
                                   + str(_send_result.code) + "-" + _send_result.msg))
            TcpIpService.close_connect(net_info)
            return

        self.logger.log(logging.INFO, "[服务端]返回客户端4个字节的后续数据长度：" + str(len(_send_body)))
        _send_result = TcpIpService.send_data(net_info, _send_body, {})

        if _send_result.code != '00000':
            self.logger.log(logging.INFO, ("[服务端]返回客户端数据报文体失败，关闭连接："
                                   + str(_send_result.code) + "-" + _send_result.msg))
            TcpIpService.close_connect(net_info)
            return
        self.logger.log(logging.INFO, "[服务端]返回客户端报文体数据：" + _ret_str)

        # 处理完成，关闭连接
        _close_result = TcpIpService.close_connect(net_info)
        if _close_result.code != '00000':
            self.logger.log(logging.INFO, ("[服务端]关闭客户端连接失败："
                                   + str(_close_result.code) + "-" + _close_result.msg))

        self.logger.log(logging.INFO, "[服务端]关闭客户端连接")
```

3、初始化服务对象

```
	self.server = TcpIpService(
            logger=self.logger,
            server_status_info_fun=self.server_status_info_fun,
            server_connect_deal_fun=self.server_connect_deal_fun,
            self_tag='UnitTest',
            log_level=logging.DEBUG
        )
```

4、启动网络服务

```
		_server_opts = TcpIpService.generate_server_opts()
        _server_opts.ip = "127.0.0.1"
        _server_opts.port = 9512
        self.server.start_server(server_opts=_server_opts)
```



## http_service服务

http_service服务是net_service_fw的一个http协议实现，网络协议是tcpip协议；该服务实际上是基于tcpip_service服务实现。

**注：http_service的net_info定义与tcpip_service服务一致；服务启动参数与tcpip_service服务也一致**

### 与标准框架的区别

1、初始参数区别

可以像tcpip_service一样自己定义server_connect_deal_fun，但本服务类中增加了server_http_deal_fun来简化对http报文的处理，定义如下：

```
@param {function} server_http_deal_fun=None - http服务数据处理函数，用于处理服务端收到的http数据:
            形式为：fun(net_info, proto_msg, msg)
                net_info : 连接信息，与TcpIpService的net_info定义一致
                proto_msg {MsgHTTP}  报文头对象
                msg {bytes} 报文体对象
            函数的返回结果为一个数组(is_close, msg, proto_msg)
                is_close : True/False - 处理完成是否关闭连接，以支持长连接情况
                msg {bytes} - 要返回的报文体，如果没有数据传None
                proto_msg {MsgHTTP} - 要返回的协议头，如果不返回传None
            注意：该参数传入代表使用服务自带的服务端监听处理线程函数，server_connect_deal_fun将失效
```

2、采用了HiveNetLib.interface_tool.protocol_msg_http简化报文头的处理

### 使用方法步骤

1、定义网络服务状态变更通知函数

```
	def server_status_info_fun(self, server_status, result):
        self.logger.log(
            (
                logging.INFO,
                "[服务端]"+result.self_tag+"服务状态变更：" +
                str(server_status) +
                "   结果code：" +
                str(result.code) +
                "  描述：" +
                result.msg
            )
        )
        return
```

2、定义http报文处理函数

```
	def server_http_deal_fun(self, net_info, proto_msg, msg):
        self.logger.log(
            (
                logging.INFO,
                "[服务端][处理函数]收到服务请求报文，http报文头: \n%s\n报文体:\n%s\n" % (
                    MsgHTTP.msg_to_str(proto_msg),
                    str(msg, "utf-8")
                )
            )
        )
        # 组织一个异常的返回报文
        _rproto_msg = MsgHTTP.load_msg('%s 3xx Internal Server Error' % ('HTTP/1.1'),
                                       obj_type=EnumMsgObjType.String)
        return (True, _rproto_msg, bytes('Http返回报文', "utf-8"))
```

3、初始化服务对象

```
		self.server = HttpService(
            logger=self.logger,
            server_status_info_fun=self.server_status_info_fun,
            self_tag='UnitTest',
            log_level=logging.DEBUG,
            server_http_deal_fun=self.server_http_deal_fun
        )
```

4、启动网络服务

```
		_server_opts = HttpService.generate_server_opts()
        _server_opts.ip = "127.0.0.1"
        _server_opts.port = 9513
        self.server.start_server(server_opts=_server_opts)
```


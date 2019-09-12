# simple_grpc使用说明

simple_grpc库对Google的gRPC库进行了封装，简化Python实现rpc调用的编码方式。



## 基本设计

### 网络参数传递

simple_grpc库的设计理念是将rpc调用视为普通函数调用处理，因此将rpc调用的传递参数设计为固定的值，并增加调用链参数的传递，简化网络参数的处理。

- 请求信息包括：调用链信息、远程函数调用信息（服务名、json格式的参数名及参数值、字节参数值-暂时仅支持一个参数为字节数组）
- 响应信息包括：返回值（json格式）、返回值里包含的字节数组（暂时仅支持一个参数为字节数组）、执行错误信息

以下是proto3的参数定义：

```
// 请求消息结构
message RpcRequest {
  // 调用链相关信息
  string trace_id = 1;  // 追踪ID
  string parent_id = 3;  // 父调用函数的执行ID
  int32 trace_level = 4;  // 调用层级，每CALL一个下级函数+1

  // 执行远程函数信息
  string service_name = 5;  // 要执行的服务名
  string para_json = 6;  // 要执行的函数的入参信息，JSON格式
  bool has_para_bytes = 7;  // 用于通知服务端所传入的参数是否有字节数组，当有字节数组时，参数值为字符格式且内容为占位字符'{$SIMPLEGRPC_BYTES$}'
  bytes para_bytes = 8;  // 当传入参数有字节数组时，通过该字段传入数组信息
}

// 响应消息结构
message RpcResponse {
  string return_json = 1;  // 函数执行返回的信息，JSON格式
  bool has_return_bytes = 2;  // 用于判断返回值是否有字节数组，当有字节数组时，参数值为字符格式且内容为占位字符'{$SIMPLEGRPC_BYTES$}'
  bytes return_bytes = 3;  // 当返回值有字节数组时，通过该字段传入数组信息

  // 执行异常会抛出的信息
  string call_code = 4;  // 执行错误码:'00000'-成功,'11403'-服务名不存在,'21007'-执行抛出异常
  string call_msg = 5;  //执行错误信息
  string call_error = 6;  //如果出现异常时的错误类型
  string call_msg_para = 7; //执行错误信息对应的参数，JSON格式，数组()
}

// 自定义健康检查的服务
message HealthRequest {
  string service = 1; // 健康监控请求
}

message HealthResponse {
  enum ServingStatus {
    UNKNOWN = 0;
    SERVING = 1;
    NOT_SERVING = 2;
    SERVICE_UNKNOWN = 3;
  }
  ServingStatus status = 1;
}
```



### gRPC客户端调用流程

gRPC客户端的标准调用流程如下（用于说明底层客户端接入的方式以及概念）：

1、根据接入参数建立连接通道（channel），连接通道可以是非安全通道（insecure_channel）和安全通道（secure_channel），建立通道时不会直接连接服务器端，只是将相应的连接信息准备好；

2、在连接通道下建立桩代码对象(stub code，可以理解为映射服务端的占坑代码)，stub指定具体的gRPC服务端的处理服务类，建立stub时也不会连接服务器端，只是指定了该stub接入的具体服务；

3、通过stub执行RPC调用，调用stub下注册的不同服务函数（注：simple_grpc中针对call_mode只有4个对应的服务端标准服务函数），这时才真正建立连接并执行调用。



### 安全连接（SSL/TSL）

SSL/TSL的原理介绍：[SSL&TSL原理](https://github.com/snakeclub/DevStandards/blob/master/docs/security/SSL%26TSL原理.md)

OpenSSL的使用方法介绍：[openssl安装及使用说明](https://github.com/snakeclub/DevStandards/blob/master/docs/security/openssl安装及使用说明.md)

simple_grpc库沿用了gRPC的安全机制，以下对2种常见的安全连接验证场景进行说明：

**1、单向认证：服务端验证客户端证书**

- 服务端导入证书

  server.pem（服务器私钥，private_key）+ server.crt（服务器公钥证书，certificate_chain） -> 共同形成私钥证书证书链对（private_key_certificate_chain_pairs）

  注：一个服务器可以导入多个私钥证书证书链对，以支持不同客户端发布不同的证书

- 客户端导入证书：server.crt（服务器下发的公钥证书，传入根证书链-root_certificates）



**2、双向认证：服务端验证客户端证书，客户端验证服务端证书**

- 服务端导入证书

  server.pem（服务器私钥，private_key）+ server.crt（服务器公钥证书，certificate_chain） -> 共同形成私钥证书证书链对（private_key_certificate_chain_pairs）

  client.crt（客户端发布的公钥证书，用于反向验证，传入根证书链-root_certificates）

  注：一个服务器可以导入多个私钥证书证书链对，以支持不同客户端发布不同的证书

- 客户端导入证书：client.pem（客户端私钥文件，private_key）、client.crt（客端公钥证书，传入证书链-certificate_chain），server.crt（服务器下发的公钥证书，传入根证书链-root_certificates）



**注意：使用SSL/TSL模式，客户端访问服务器应通过域名来访问，例如'localhost'，如果通过IP访问可能会出现验证失败的问题。**



### RPC流模式支持

simple_grpc库支持gRPC的流模式处理，可以通过call_mode指定使用不同的流模式接口，共支持以下四种流模式：

- EnumCallMode.Simple  :  简单模式，形式为客户端一次请求服务器一次应答
- EnumCallMode.ClientSideStream  :  客户端流模式，形式为客户端多次请求服务器一次应答，例如文件上传，客端可将文件数据拆分为多个请求上传，服务端收到全部请求后再一次返回应答
- EnumCallMode.ServerSideStream  : 服务端流模式，形式为客户端一次请求服务器多次应答，例如文件下载，客户端发起文件请求，服务器端将文件数据拆分为多个应答返回
- EnumCallMode.BidirectionalStream : 双向数据流模式，形式为客户端多次上传，服务端多次应答，这个模式比较灵活，客户端和服务器端在交互过程中不中断连接，直到双方所有数据处理完成

注：gRPC的流模式在Python中采用的是iterator迭代器进行处理，如果要支持流，对应的请求和响应信息应按iterator迭代器方式返回（yeild关键字方式返回）。



## SimpleGRpcTools工具类(simple_grpc.grpc_tool)

SimpleGRpcTools工具类提供了一些公共工具函数，可以对Grpc调用过程的参数和数据进行处理。

### 公共工具函数

- generate_request_obj : 创建rpc调用请求参数对象RpcRequest
- generate_response_obj : 创建rpc响应对象RpcResponse
- response_obj_to_cresult : 将RpcResponse对象转换为CResult对象，CResult对象的以下属性包含返回信息：
  - return_json - 返回值的json字符串
  - has_return_bytes - 是否有返回字节数组
  - return_bytes - 返回的字节数组

- response_iterator_to_cresults :  将RpcResponsed的iterator对象转换为CResult的iterator对象（Stream流处理的模式使用）

- parameters_to_json : 将[[para_name, call_value], ... ]格式的参数列表转换为json字符串对象，用于创建请求参数，函数返回的对象如下：

  - object.para_json : 返回的json字符串

  - object.has_para_bytes : 传入的参数是否有字节数组

  - object.para_bytes : 当传入参数有字节数组时，通过该字段传入数组信息

    注：参数列表清单可以自行生成，也可以通过RunTool.get_current_function_parameter_values方法动态获取

- object_to_json_support_bytes : 将一个Python对象转换为json字符串对象（支持bytes的情况），用于将响应对象转换为simple_grpc的标准响应返回；函数返回的对象如下：

  - obj.return_json : 转换后的JSON格式字符串
  - obj.has_return_bytes : 返回值是否有字节数组
  - obj.return_bytes : 有字节数组时，通过该字段传入数组信息

- get_json_to_object_para_mapping : 获取json转换为对象的映射参数（从全局公共参数“SIMPLEGRPC_JSON_TO_OBJECT_PARA”获取对应key的映射参数），用于后续根据参数调用StringTool.json_to_object，将json字符串转换为Python对象（支持特定Python对象与json的转换，详见StringTool.json_to_object的定义）

- set_json_to_object_para_mapping : 设置json转换为Python对象的映射参数（放入全局公共参数“SIMPLEGRPC_JSON_TO_OBJECT_PARA”）

- json_to_object_by_para_mapping : 通过json_para_mapping_key获取到的转换参数，将json字符转换为Python对象，用于支持特定Python对象的转换处理（注意：并非所有Python对象都可以直接转为json，原生方法只支持基础类型的转换）



### 服务端工具函数

- get_private_key_certificate_chain_pair : 根据.key和.crt文件生成private_key_certificate_chain_pair，返回对应签名证书的(private_key, certificate_chain)，用于服务端TSL模式



### 客户端工具函数

- generate_connect_para : 生成客户端连接参数，注意这个函数生成的连接参数只用于SimpleGRpcTools的调用函数，不能用于SimpleGRpcConnection

- generate_channel :  生成gRPC通道，注意该通道需要在使用后，后续代码主动关闭

- generate_call_stub : 生成gRPC桩代码对象

- grpc_call_by_stub : 基于stub对象执行远程调用

- grpc_call_by_channel : 基于channel对象执行远程调用，自动创建stub

- grpc_call : 单次执行gRPC远程调用（自动创建channel并在完成后关闭）

  注意：该调用方式不适合ServerSideStream、BidirectionalStream两种模式（自动关闭channel会导致处理失败）



### 健康检查工具函数

- simple_grpc_health_check_by_stub : 执行SimpleGRpc自定义的健康检查（基于已创建的stub），访问服务端的健康检查服务
- simple_grpc_health_check :  执行SimpleGRpc自定义的健康检查
- generate_health_check_stub : 生成gRPC标准的服务健康检查桩代码对象
- health_check_by_stub : 基于stub对象gRPC标准的服务健康检查
- health_check : 执行gRPC标准的服务健康检查



### 调用链日志工具函数

- write_api_call_chain_log : 记录调用链日志，日志相关信息通过信息字典（info_dict）传入，注意日志对象可以是call_chain_tool.CallChainTool.create_call_chain_logger产生的异步日志对象，也可以是普通日志对象
- call_chain_logging : 实时记录调用链日志，日志相关信息通过信息字典（info_dict）传入
- api_call_chain_asyn_deal_msg_fun : 供call_chain_tool.CallChainTool.create_call_chain_logger生成异步日志对象使用，将日志record对象中的日志内容部分处理为msg并返回（dict_info字典）



## 建立gRPC服务端(simple_grpc.grpc_server)

### 简单gRPC服务端应用

1、创建异步记录日志对象（也可创建普通日志对象或不记录日志）

```
# 创建最终输出日志
cls.logger = simple_log.Logger(
	conf_file_name=_TEMP_DIR + '/../../simple_grpc/test_simple_grpc.json',
	logger_name=simple_log.EnumLoggerName.ConsoleAndFile,
	config_type=simple_log.EnumLoggerConfigType.JSON_FILE,
	logfile_path=_TEMP_DIR + '/log/test_case_asyn.log',
	is_create_logfile_by_day=True,
)

# 生成异步日志对象，注意使用SimpleGRpcTools.api_call_chain_asyn_deal_msg_fun处理日志内容
cls._asyn_logger = CallChainTool.create_call_chain_logger(
    logger=cls.logger,
    asyn_logging=True,
    asyn_logging_fun=None,
    asyn_deal_msg_fun=SimpleGRpcTools.api_call_chain_asyn_deal_msg_fun
)

# 启动后台写日志任务线程
CallChainTool.start_call_chain_asyn_logging(cls._asyn_logger)
```

2、定义服务端应用处理函数，与一般的函数定义相同，无需特殊处理

```
def service_simple_call_para(a, b, *args, c=10, d={'d1': 'd1value'}, **kwargs):
    """
    测试简单调用，直接返回传入的参数(数组形式)
    """
    # 要清除调用链内容
    _dict = copy.deepcopy(kwargs)
    if 'trace_id' in _dict.keys():
        del _dict['trace_id']
        del _dict['parent_id']
        del _dict['trace_level']
    return [a, b, args, c, d, _dict]

def service_simple_call_no_para_no_return():
    """
    测试简单调用，无入参无返回
    """
    return
```

3、创建服务端处理服务对象，并绑定服务端应用处理函数

```
# 服务端处理服务对象，可以多个应用服务共用
cls.servicer_simple_call = SimpleGRpcServicer(
    logger=cls._asyn_logger
)
# 绑定服务端应用处理函数，指定服务类型和服务名（service_name）
cls.servicer_simple_call.add_service(
    EnumCallMode.Simple, 'service_simple_call_para', service_simple_call_para)
cls.servicer_simple_call.add_service(
    EnumCallMode.Simple, 'service_simple_call_no_para_no_return', service_simple_call_no_para_no_return)
```

4、创建gRPC服务器，并启动服务

```
# 服务器创建参数
cls.server_no_ssl_no_zoo_opts = SimpleGRpcServer.generate_server_opts(
    ip='127.0.0.1',
    port=50051,
    max_workers=10,
    max_connect=100,
    is_health_check=True
)

# 创建gRPC服务器
cls.server_no_ssl_no_zoo = SimpleGRpcServer(
    server_name='ServerNoSslNoZoo',
    logger=cls.logger, log_level=simple_log.INFO)
    
# 启动服务，指定服务端处理服务对象清单
cls.server_no_ssl_no_zoo.start_server(
    server_opts=cls.server_no_ssl_no_zoo_opts, servicer_list={
        'servicer_simple_call': cls.servicer_simple_call
    }, is_wait=True
)
```

5、如果需要关闭服务，执行以下代码

```
# 停止服务，简单服务，无SSL，无服务发现
cls.server_no_ssl_no_zoo.stop_server()

# 停止异步日志后台处理线程
CallChainTool.stop_call_chain_asyn_logging(cls._asyn_logger)
```



### gRPC服务端高阶应用技巧

#### 自定义调用链日志打印内容

在SimpleGRpcServicer的add_service函数中，可以通过传入recv_logging_para及resp_logging_para变更调用链日志的打印内容：

```
@param {dict} recv_logging_para={} - 接收报文打印参数
@param {dict} resp_logging_para={} - 返回报文打印参数
    recv_logging_para的参数格式一致，定义如下：
    'msg_class' {class} - 继承MsgFW框架的报文解析类对象，如果为None代表不处理信息
    'logging_head' {dict}- 定义打印的日志规范头信息
        key {string} - 日志头信息项名，例如'IP'
        value {string} - 日志头信息值，None代表从报文对象msg或proto_msg中获取(从api_mapping获取定义)
        跟当前服务相关的可选信息项包括：
        C-IP : 客户端的IP地址
        C-PORT : 客户端的连接端口
        S-IP : 服务端绑定服务
        S-PORT : 服务端监听端口
        CALL_MODE : 服务端调用模式
        SERVICE_NAME : 访问的服务名
        PARA_BYTES : 转换为字符串显示的参数字节数组信息（如果是返回报文该参数代表显示RETURN_BYTES）
        PARA_BYTES_LEN : 字节数组长度（如果是返回报文该参数代表显示RETURN_BYTES_LEN）

    'api_mapping' {dict}- 定义从报文中获取logging_head所需的信息
    'key_para' {dict} - 要打印的关键业务参数
    'print_in_para' {dict} - 要打印的指定接口字段
        以上三项的定义都是一样
        key {string} - 打印信息项名
        value {list}- 映射信息，为三项的数组:
            value[0] {string} - 获取api对象类型，'msg'或'proto_msg'
            value[1] {string} - 搜索路径，具体规则参考对应的MsgFW实例
            value[2] {dict} - 获取参数,具体规则参考对应的MsgFW实例

    'is_print_msg' {bool} - 是否打印报文内容
    'msg_print_kwargs' {dict} - MsgFW对象（例如MsgJSON）的msg.to_str()函数的传入参数
```



#### 服务端应用处理函数入参及返回值

服务端应用处理函数的入参除了按客户端上送的标准函数入参外，还会传入以下入参，在处理时可以获取并应用：

- 调用链信息：trace_id、parent_id、trace_level，让函数可以兼容进行调用链日志的记录
- has_next_stream_data ：{bool} ，对于客户端请求为流模式的情况，通过该参数确定是否还有下一个请求

服务端应用处理函数所返回的值应为基础数据类型，以保证默认处理可转换为json字符串进行返回；否则所返回的对象应自带“\_\_json\_\_” 函数，用于自定义对象转换为json字符串进行返回。

服务端应用的返回如果是流处理模式，则应使用yield方式形成iterator迭代器进行流对象返回，例如：

```
def service_server_side_stream(a, b, *args, **kwargs):
    """
    测试服务端流模式的服务端应用
    """
    _ret_obj = [a, b, args, kwargs]
    _json_str = StringTool.object_to_json(_ret_obj)
    print('call service_server_side_stream return : ' + _json_str)
    _i = 0
    while True:
        yield [a, b, 'server+' + str(_i), args, kwargs]
        _i = _i + 1
        if _i > 4:
            break
```



#### 开启服务端健康检查服务

可以在启动服务时通过server_opts.is_health_check参数开启服务端的健康检查服务，开启健康检查服务后，客户端可以利用simple_grpc的自定义健康检查方法（SimpleGRpcTools.simple_grpc_health_check ）或标准gRPC健康检查方法（SimpleGRpcTools.health_check ）确认服务端的指定服务状态是否正常。

开启健康检查服务后，可以利用服务器的set_service_status方法设置全部或某个服务端处理服务对象（servicer）的服务状态。

注：推荐使用自定义健康检查方法（SimpleGRpcTools.simple_grpc_health_check ）进行服务端状态检查，标准gRPC健康检查方法（SimpleGRpcTools.health_check ）在判断某个服务端处理服务对象的服务状态时会存在缺陷。



## gRPC客户端应用

### 如何生成调用请求信息

可以通过以下几种方式来生成调用请求信息：

1、直接通过SimpleGRpcTools.generate_request_obj传入相应值生成RpcRequest对象；

2、从所执行的客户端函数的入参动态生成RpcRequest对象（在客户端建立一个和服务端处理函数入参一样的执行函数，便于简化处理），例如：

```
# 服务端处理函数
def service_simple_call_para(a, b, *args, c=10, d={'d1': 'd1value'}, **kwargs):
    """
    测试简单调用，直接返回传入的参数(数组形式)
    """
    # 要清除调用链内容
    _dict = copy.deepcopy(kwargs)
    if 'trace_id' in _dict.keys():
        del _dict['trace_id']
        del _dict['parent_id']
        del _dict['trace_level']
    return [a, b, args, c, d, _dict]

# 客户端对应函数
def client_simple_call_para(a, b, *args, c=10, d={'d1': 'd1value'}, **kwargs):
    """
    测试简单调用，直接返回参数
    """
    # 根据函数入参动态生成请求RpcRequest对象
    _para_values = RunTool.get_current_function_parameter_values(is_simple_mode=True)
    _para_obj = SimpleGRpcTools.parameters_to_json(_para_values)
    _req_obj = SimpleGRpcTools.generate_request_obj(
        service_name='service_simple_call_para', para_json=_para_obj.para_json,
        has_para_bytes=_para_obj.has_para_bytes, para_bytes=_para_obj.para_bytes
    )
    
    # 连接并发送请求
    _connect_para = SimpleGRpcTools.generate_connect_para(
        conn_str='127.0.0.1:50051'
    )
    _cresult = SimpleGRpcTools.grpc_call(_connect_para, _req_obj)
    _cresult.return_obj = SimpleGRpcTools.json_to_object_by_para_mapping(
        _cresult.return_json,
        'client_simple_call_para'
    )
    return _cresult
```



### 如何处理服务端返回的响应信息

通过simple_grpc库的客户端工具进行gRPC调用，统一返回的都是CResult的结果，以下是对CResult结果的可选处理方式：

1、判断gRPC调用状态，可以通过CResult.code判断调用情况，'00000'-成功,'11403'-服务名不存在,'21007'-服务端执行抛出异常，'20408'-客户端执行出现异常，'30403'-调用超时；

2、在调用成功的情况下，可以通过CResult以下几个属性获取服务端返回的值：

- return_json - 返回值的json字符串
- has_return_bytes - 是否有返回字节数组
- return_bytes - 返回的字节数组

3、可以通过StringTool.json_to_object方法，将CResult.return_json 转换为Python对象，注意返回值如果有字节数组（has_return_bytes），应通过return_bytes获取到字节数组，按双方约定好的属性补充到Python对象中；

4、可以通过SimpleGRpcTools.json_to_object_by_para_mapping方法，直接从全局公共参数“SIMPLEGRPC_JSON_TO_OBJECT_PARA”中获取指定的json转换参数，实现Python对象的转换。



### 如何处理流模式

针对不同流模式的处理，有以下处理方法的参考：

1、客户端流模式（EnumCallMode.ClientSideStream）：

```
# 通过yield方式产生请求对象迭代器
def client_side_stream_generator():
    """
    客户端流模式，客户端流请求生成器
    """
    _i = 0
    while True:
        yield SimpleGRpcTools.generate_request_obj(...)
        _i = _i + 1
        if _i > 4:
            break

# 发送请求
_connect_para = SimpleGRpcTools.generate_connect_para(
    ip='127.0.0.1', port=50051
)
_cresult = SimpleGRpcTools.grpc_call(
    _connect_para, client_side_stream_generator(), call_mode=EnumCallMode.ClientSideStream
)
```

2、服务端流模式（EnumCallMode.ServerSideStream)

```
with SimpleGRpcTools.generate_channel(_connect_para) as channel:
	# 发送请求
    _cresult_iterator = SimpleGRpcTools.grpc_call_by_channel(
        channel, _req_obj, call_mode=EnumCallMode.ServerSideStream)
        
    # 以迭代器方式处理返回结果
    for _cresult in _cresult_iterator:
        if not _cresult.is_success():
            return
        else:
        	...
```

3、双向数据流模式（EnumCallMode.BidirectionalStream) 

实际上是客户端流模式和服务端流模式的组合，根据实际需要，可以设计为1个请求对应1个响应、1个请求对应n个响应，n个请求对应1个响应这3种情况，同时通过迭代器来判断响应是否已完成。

**注意：流模式的处理要特别注意连接通道的关闭，不能在流未完成处理前关闭连接通道，否则会导致下一个流数据的获取出现异常。**



### 使用SimpleGRpcTools的客端工具函数进行gRPC调用

可以直接使用SimpleGRpcTools的客端工具函数进行gRPC的调用，标准处理流程如下：

1、生成调用请求RpcRequest对象

```
# 根据函数入参动态生成请求RpcRequest对象
_para_values = RunTool.get_current_function_parameter_values(is_simple_mode=True)
_para_obj = SimpleGRpcTools.parameters_to_json(_para_values)
_req_obj = SimpleGRpcTools.generate_request_obj(
    service_name='service_simple_call_para', para_json=_para_obj.para_json,
    has_para_bytes=_para_obj.has_para_bytes, para_bytes=_para_obj.para_bytes
)
```

2、建立连接通道

```
_connect_para = SimpleGRpcTools.generate_connect_para(
    conn_str='127.0.0.1:50051'
)
_channel = SimpleGRpcTools.generate_channel(_connect_para)
```

3、创建桩代码对象

```
_stub = SimpleGRpcTools.generate_call_stub(_channel)
```

4、执行远程调用

```
# 进行远程调用
_cresult = SimpleGRpcTools.grpc_call_by_stub(_stub, _req_obj)

# 将结果转换为Python对象
_cresult.return_obj = SimpleGRpcTools.json_to_object_by_para_mapping(
    _cresult.return_json,
    'client_simple_call_para'
)

# 关闭连接通道
_channel.close()
```

5、另外一个方法可以直接简单调用（单次使用即释放）

```
# 直接进行远程调用
_cresult = SimpleGRpcTools.grpc_call(_connect_para, _req_obj)
_cresult.return_obj = SimpleGRpcTools.json_to_object_by_para_mapping(
    _cresult.return_json,
    'client_simple_call_para'
)
```



### 使用grpc_client及连接池

另外一个使用客户端的更优方法是使用grpc_client的客户端连接SimpleGRpcConnection进行远程调用，客户端连接对象支持连接有效性检查和重连接，以及支持调用链日志的记录，使用方法示例如下：

```
# 建立连接
_connect_para = SimpleGRpcConnection.generate_connect_para(
	ip='127.0.0.1', port=50051, 
    servicer_name='servicer_simple_call', test_use_health_check=True
)
_connection = SimpleGRpcConnection(_connect_para)

# 执行健康检查
_resp_obj = _connection.test()

# 执行远程调用
_cresult = _connection.call(SimpleGRpcTools.generate_request_obj('test'))
```



此外，还可以使用客户端连接池（SimpleGRpcConnectionPool）进行连接的管理，具体连接池的使用方法参考[connection_pool](connection_pool/connection_pool.md)连接池服务框架。
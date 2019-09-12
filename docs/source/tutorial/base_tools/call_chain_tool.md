# base_tools.call_chain_tool使用说明

call_chain_tool是用于产生调用链日志（包括接口调用、函数调用）的处理工具，原理是通过日志记录函数调用记录，并根据trace_id（追踪ID）、parent_call_id（父函数执行ID）等信息找到函数及接口之间的调用关系。通过修饰符方式来实现链的向下延伸，无需实际逻辑函数自身实现调用链相关代码。



## CallChainTool工具类

### 生成trace_id（追踪ID）

可以通过调用链工具的generate_trace_id方法生成全局唯一的trace_id（追踪ID），该方法默认通过uuid来生成唯一的ID，同时如果使用HiveNetLib.IdPool模式可以生成更个性化的唯一ID，函数的定义如下：

```
@param {HiveNetLib.IdPool} idpool=None - 获取id的资源池，如果传入None代表直接通过uuid生成id
@param {number} get_id_overtime=0 - 超时时间，单位为秒，如果需要一直不超时送入0
@param {kwargs}  - id的资源池的get_id传入参数

@returns {string} - trace_id
```



### 方法调用链标准应用

#### 第1步：定义日志类

使用调用链必须先定义日志类，用于将调用链日志信息输出到指定的日志载体中（具体记录在文件还是其他设备上由日志类控制），可以通过修饰符参数指定是使用通用的日志类，还是使用独立的日志类。

自行实现的日志类必须实现info、warning、error等标准写日志方法（参考Python自带的logging类）。

以下示例为使用simple_log日志类及使用全局通用日志类写日志：

```
from HiveNetLib.simple_log import Logger, EnumLoggerName, EnumLoggerConfigType

        # 初始化日志类
        _logger = Logger(
            conf_file_name=_TEMP_DIR + '/../../call_chain_tool/test_call_chain.json',
            logger_name=EnumLoggerName.ConsoleAndFile.value,
            logfile_path=_TEMP_DIR + '/log/test_case1.log',
            is_create_logfile_by_day=True,
            is_print_file_name=True,
            is_print_fun_name=True
        )
        # 设置为全局使用
        CallChainTool.set_global_logger(_logger)
```



#### 第2步：在需要追踪的函数定义上增加修饰符

注意：要追踪的调用函数必须都要加上调用链修饰符，比如a call b，b call c， c call d，则abcd都要加上调用链修饰符，如果c不增加修饰符，则无法从a 追踪到 d。

```
# 嵌套调用，产生调用链
@CallChainTool.methon_call_chain(is_use_global_logger=True, key_para=('k1'))
def func_case1_call_1(a, b, **kwargs):
    CallChainTool.get_global_logger().log(logging.INFO,
        'runing func_case1_call_1 : a=%s, b=%s : %s' % (str(a), str(b), str(kwargs)))
    time.sleep(0.001)
    # 执行2
    func_case1_call_2('2a', '2b', '2c', k1=kwargs['k1'])
    # 执行3
    func_case1_call_3(k1=kwargs['k1'])
    return


@CallChainTool.methon_call_chain(is_use_global_logger=True, key_para=('k1'))
def func_case1_call_2(a, b, c, **kwargs):
    CallChainTool.get_global_logger().log(logging.INFO,
        'runing func_case1_call_2 : a=%s, b=%s, c=%s: %s' % (str(a), str(b), str(c), str(kwargs)))
    time.sleep(0.001)
    # 执行4
    func_case1_call_4('4a', '4b', '4c', k1=kwargs['k1'])
    return


@CallChainTool.methon_call_chain(is_use_global_logger=True, key_para=('k1'))
def func_case1_call_3(**kwargs):
    CallChainTool.get_global_logger().log(logging.INFO,
        'runing func_case1_call_3 : %s' % (str(kwargs)))
    time.sleep(0.001)
    return


@CallChainTool.methon_call_chain(is_use_global_logger=True, key_para=('k1'))
def func_case1_call_4(a, b, c, **kwargs):
    CallChainTool.get_global_logger().log(logging.INFO,
        'runing func_case1_call_4 : a=%s, b=%s, c=%s: %s' % (str(a), str(b), str(c), str(kwargs)))
    time.sleep(0.001)
    return
```



#### 第3步：直接执行函数，将自动产生调用链日志

```
func_case1_call_1('1a', '1b', k1='testk1')
```

产生的日志符合HiveNet日志规范，TRACE : 调用关系追踪信息，里面登记多个信息，通过冒号（“:”）分隔，按顺序依次为TRACE_ID（追踪ID）、CALL_FILE（调用文件）、CALL_FUN（调用函数名）、TRACE_LEVEL（调用层级，每CALL一个下级函数+1）、PARENT_CALL_ID（父调用函数的执行ID）、CALL_ID（执行ID）

第1个函数（发起函数）的TRACE_ID自动生成；通过TRACE_ID可以找到本次执行调用的所有函数；通过PARENT_CALL_ID和CALL_ID可以依次向下找到调用关系；通过TRACE_LEVEL可以确定调用顺序。

示例如下：

```
[2018-09-11 23:16:14,595][INFO][PID:7716][TID:420][FILE:call_chain_tool.py][FUN:wrapper2][TRACE:9fa68424b5d511e891fdc2335e3520d4:9fa68424b5d511e891fdc2335e3520d4::1:call_chain_tool.py:func_case1_call_1]{'key': {'k': 'None', '1': 'None'}, 'para': {}}
[2018-09-11 23:16:14,595][INFO][PID:7716][TID:420][FILE:test_call_chain_tool.py][FUN:func_case1_call_1]runing func_case1_call_1 : a=1a, b=1b : {'k1': 'testk1', 'trace_id': '9fa68424b5d511e891fdc2335e3520d4', 'trace_level': [1], 'call_id': '9fa68424b5d511e891fdc2335e3520d4', 'parent_id': ''}
[2018-09-11 23:16:14,610][INFO][PID:7716][TID:420][FILE:call_chain_tool.py][FUN:wrapper2][TRACE:9fa68424b5d511e891fdc2335e3520d4:9fa8e67ab5d511e8bb9cc2335e3520d4:9fa68424b5d511e891fdc2335e3520d4:2:call_chain_tool.py:func_case1_call_2]{'key': {'k': 'None', '1': 'None'}, 'para': {}}
[2018-09-11 23:16:14,610][INFO][PID:7716][TID:420][FILE:test_call_chain_tool.py][FUN:func_case1_call_2]runing func_case1_call_2 : a=2a, b=2b, c=2c: {'k1': 'testk1', 'trace_id': '9fa68424b5d511e891fdc2335e3520d4', 'trace_level': [2], 'call_id': '9fa8e67ab5d511e8bb9cc2335e3520d4', 'parent_id': '9fa68424b5d511e891fdc2335e3520d4'}
[2018-09-11 23:16:14,626][INFO][PID:7716][TID:420][FILE:call_chain_tool.py][FUN:wrapper2][TRACE:9fa68424b5d511e891fdc2335e3520d4:9fab48ccb5d511e8acf9c2335e3520d4:9fa8e67ab5d511e8bb9cc2335e3520d4:3:call_chain_tool.py:func_case1_call_4]{'key': {'k': 'None', '1': 'None'}, 'para': {}}
[2018-09-11 23:16:14,626][INFO][PID:7716][TID:420][FILE:test_call_chain_tool.py][FUN:func_case1_call_4]runing func_case1_call_4 : a=4a, b=4b, c=4c: {'k1': 'testk1', 'trace_id': '9fa68424b5d511e891fdc2335e3520d4', 'trace_level': [3], 'call_id': '9fab48ccb5d511e8acf9c2335e3520d4', 'parent_id': '9fa8e67ab5d511e8bb9cc2335e3520d4'}
[2018-09-11 23:16:14,642][INFO][PID:7716][TID:420][FILE:call_chain_tool.py][FUN:wrapper2][TRACE:9fa68424b5d511e891fdc2335e3520d4:9fab48ccb5d511e8acf9c2335e3520d4:9fa8e67ab5d511e8bb9cc2335e3520d4:3:call_chain_tool.py:func_case1_call_4][USE:0.015624s]
[2018-09-11 23:16:14,642][INFO][PID:7716][TID:420][FILE:call_chain_tool.py][FUN:wrapper2][TRACE:9fa68424b5d511e891fdc2335e3520d4:9fa8e67ab5d511e8bb9cc2335e3520d4:9fa68424b5d511e891fdc2335e3520d4:2:call_chain_tool.py:func_case1_call_2][USE:0.031249s]
[2018-09-11 23:16:14,642][INFO][PID:7716][TID:420][FILE:call_chain_tool.py][FUN:wrapper2][TRACE:9fa68424b5d511e891fdc2335e3520d4:9fadab26b5d511e899c9c2335e3520d4:9fa68424b5d511e891fdc2335e3520d4:4:call_chain_tool.py:func_case1_call_3]{'key': {'k': 'None', '1': 'None'}, 'para': {}}
[2018-09-11 23:16:14,642][INFO][PID:7716][TID:420][FILE:test_call_chain_tool.py][FUN:func_case1_call_3]runing func_case1_call_3 : {'k1': 'testk1', 'trace_id': '9fa68424b5d511e891fdc2335e3520d4', 'trace_level': [4], 'call_id': '9fadab26b5d511e899c9c2335e3520d4', 'parent_id': '9fa68424b5d511e891fdc2335e3520d4'}
[2018-09-11 23:16:14,657][INFO][PID:7716][TID:420][FILE:call_chain_tool.py][FUN:wrapper2][TRACE:9fa68424b5d511e891fdc2335e3520d4:9fadab26b5d511e899c9c2335e3520d4:9fa68424b5d511e891fdc2335e3520d4:4:call_chain_tool.py:func_case1_call_3][USE:0.015633s]
[2018-09-11 23:16:14,657][INFO][PID:7716][TID:420][FILE:call_chain_tool.py][FUN:wrapper2][TRACE:9fa68424b5d511e891fdc2335e3520d4:9fa68424b5d511e891fdc2335e3520d4::1:call_chain_tool.py:func_case1_call_1][USE:0.062506s]
```



### 方法调用链高阶应用

#### 支持函数定义类型

@CallChainTool.methon_call_chain修饰符要求函数必须有\*\*kwargs的动态可变KV变量参数，用于传递4个关键的调用链参数trace_id、trace_level、call_id、parent_id。如果所定义的函数没有\*\*kwargs参数，虽然不会执行出错，但无法传递和跟踪整个调用链执行情况，只能记录当前函数的执行日志（包括执行使用时间）。

支持的函数定义类型参考如下：

- def func(\*args, \*\*kwargs)

- def func(para1,  para2,  **kwargs)

- def func(para1,  para2,  para3=v3,  **kwargs)
- def func(**kwargs)

注意如果是func(\*args, \*\*kwargs)的类型，可以通过设置修饰符参数is_standard_def=True来提升执行效率（无需动态执行函数）。

#### 如何自行传递调用链参数

如果存在需要自行定义调用链参数的情况，例如收到一笔网络报文后，处理函数作为调用链开始，但需要使用网络传过来的trace_id时可以通过以下操作实现自定义调用链参数：

方式1：在修饰符参数指定

通过修饰符参数  “trace_id=, trace_level=, call_id=, parent_id=”  可以直接指定相关参数并传入到执行函数中。

```
@CallChainTool.methon_call_chain(trace_id='xxx', trace_level=[0], call_id='xx', parent_id='xx')
def func(...):
	...
```

方式2：在函数的kwargs参数中传递

在调用函数时，在函数的kwargs参数中设置trace_id、trace_level、call_id、parent_id的值。

```
@CallChainTool.methon_call_chain()
def func(... ,trace_id='xxx', trace_level=[0], call_id='xx', parent_id='xx'):
	...
```

注：在调用链监控设计中，可能存在部分内部函数的执行不希望打印追踪日志，这时可以在有修饰符的函数的kwargs参数中获取trace_id、trace_level、call_id、parent_id的值， 用以上两种方式按规则传递给下一个追踪函数即可（中间过程不处理）。

#### 特殊参数说明

指定打印的日志级别：log_level=logging.INFO

指定打印关键参数信息：key_para=(‘para_name’, 0, ..)，参数为一个数组，如果值为字符串，代表打印这个名字的参数值（对应函数的kwargs参数），如果为数字，代表打印第几个位置的参数（对应函数的args参数）；注意如果只有一个参数，写法必须为(0,) ，以标注这个是数组

指定打印参数信息：print_in_para=(‘para_name’, 0, ..)，格式与key_para一致

在函数执行后，指定打印出参（例如参数中有引用类型的情况，可能值会被改变）：print_out_para=(‘para_name’, 0, ..)，格式与key_para一致

函数执行后，是否打印返回对象（调用对象的\_\_str\_\_方法）:is_print_back=True



### 接口调用链标准应用

#### 方法1：直接记录接口调用链日志

可以直接调用api_call_chain_logging方法记录接口的日志（满足HiveNet日志规范），接口日志打印的设计原理如下：

1、要打印的报文对象，包括接口报文（具体的业务报文，例如http协议的主体部分）和协议报文（协议相关的报文信息，例如http协议的协议头报文），必须是interface_tool.MsgFW的继承类实现；

2、通过api_mapping提供字段的映射关系字典，将接口信息项（自定义的名字或接口设计字段名）对应到msg或proto_msg中的搜索路径，供日志打印获取相应的值；

3、通过logging_head定义日志头要打印信息字典（在日志前面，用[]包裹的信息），可以支持两种情况：如果传入的value非None，则直接按传入的值打印；如果传入的value为None，则通过api_mapping字典找到key对应搜索路径，从报文中获取相应值进行打印；

4、key_para和print_in_para定义要打印为JSON格式的重要信息，打印出来的JSON格式为“{‘key’: {'字段名': '字段值', '字段名': '字段值', ... }, 'para': {'字段名': '字段值', '字段名': '字段值', ...}}”

方法的入参具体说明如下：

```
		@param {interface_tool.MsgFW} msg - 接口报文对象
        @param {interface_tool.MsgFW} proto_msg=None - 协议报文信息对象
        @param {object} logger=None - 日志对象，如果为None代表不需要输出日志，传入对象需满足:
            1、标准logging的logger对象
            2、自定义的日志类对象，但应实现info、warning、error等标准方法
        @param {dict} api_mapping=dict() - 接口信息映射字典，用于从接口中获取指定的信息项，格式如下：
            key {string} - 输入信息项名（与入参名一致）
            value {list}- 映射信息，为三项的数组:
                value[0] {string} - 获取api对象类型，'msg'或'proto_msg'
                value[1] {string} - 搜索路径，具体规则参考对应的MsgFW实例
                value[2] {dict} - 获取参数
        @param {string} api_call_type='SEND' - 接口调用类型，SEND - 发送报文，RECV - 接收报文
        @param {string} api_info_type='SEND' - 接口信息类型，区分两类：
            api_call_type为SEND的情况：
                SEND - 发送报文
                BACK - 返回报文
                OT - 超时
                EX - 异常
                STREAM-SEND - 流报文发送
                STREAM-BACK - 流报文返回
            api_call_type为RECV的情况：
                RECV - 接收报文
                RET - 返回报文
                EX - 异常
                STREAM-RECV - 流报文接收
                STREAM-DEAL - 流报文处理（非返回）
                STREAM-RET - 流报文返回
        @param {string} trace_id=None - 调用链追踪ID，None代表从报文对象msg或proto_msg中获取
        @param {int} trace_level=None - 调用层级，None代表从报文对象msg或proto_msg中获取
        @param {string} call_id=None - 当前接口调用的执行ID，None代表从报文对象msg或proto_msg中获取
        @param {string} parent_id=None - 上一接口的执行ID，None代表从报文对象msg或proto_msg中获取
        @param {dict} logging_head=dict() - 日志头信息项，用于满足日志规范，格式如下：
            key {string} - 日志头信息项名，例如'IP'
            value {string} - 日志头信息值，None代表从报文对象msg或proto_msg中获取
            按照日志规范，发送报文和接收报文的日志头包括：
                IP : 发送IP地址/发起方IP地址
                PORT : 接收方服务端口
                SYS : 目标系统标识/发起方系统标识
                SEQ : 报文流水号
        @param {number} use=0 - 接口执行耗时，api_info_type为非SEND和RECV时需传入
        @param {object} error=None - 异常对象，api_info_type为EX时需传入
        @param {string} trace_str='' - 异常堆栈信息，api_info_type为EX时需传入
        @param {bool} is_print_proto_msg=False - 是否打印协议报文信息对象
        @param {dict} proto_msg_print_kwargs=dict() - 协议报文信息对象打印参数（MsgFW转换为字符串的参数）
        @param {bool} is_print_msg=False - 是否打印接口报文对象
        @param {dict} msg_print_kwargs=dict() - 报文信息对象打印参数（MsgFW转换为字符串的参数
        @param {dict} key_para=dict() - 打印业务层面唯一标识业务的接口参数列表，格式如下：
            key {string} - 打印信息项名
            value {list}- 映射信息，为三项的数组:
                value[0] {string} - 获取api对象类型，'msg'或'proto_msg'
                value[1] {string} - 搜索路径，具体规则参考对应的MsgFW实例
                value[2] {dict} - 获取参数,具体规则参考对应的MsgFW实例
        @param {dict} print_in_para=dict() - 定义需要打印的接口信息，格式如下：
            key {string} - 打印信息项名
            value {list}- 映射信息，为三项的数组:
                value[0] {string} - 获取api对象类型，'msg'或'proto_msg'
                value[1] {string} - 搜索路径，具体规则参考对应的MsgFW实例
                value[2] {dict} - 获取参数,具体规则参考对应的MsgFW实例
        @param {bool} is_use_global_logger=True - 当logger=None时，是否使用全局logger对象
            注：通过RunTool.set_global_logger进行设置
        @param {int} log_level=logging.INFO - 打印日志的级别
        @param {int} call_fun_level=0 - 登记日志时需要记录的实际函数所处层级，
            从当前执行函数开始，如果需要记录当前函数则传0；记录父函数则传1，记录父父函数则传2...
```

注：如果想自己进行打印，可以通过api_call_chain_log_str方法直接生成日志打印项，再自行打印输出。

#### 方法2：异步记录接口调用链日志

对于远程记录日志，以及需要降低日志记录对处理性能影响的情况，可以通过异步记录日志的方式进行接口调用链日志的记录，具体处理步骤如下：

**1、定义进行日志信息msg生成的函数**

该函数负责根据日志的record信息，生成想要打印的日志内容（msg部分，不包括日志定义的输出格式部分），record对象存储了执行日志输出函数的所有信息，包括extra字典中传入的各类参数。

以下示例从record获取到输出日志时存入的info_dict字典，从字典中获取相应打印信息，调用api_call_chain_log_str生成日志内容msg并返回；对于找不到info_dict属性的情况，认为是正常的日志处理，直接原样返回record.msg：

```
	def api_call_chain_asyn_deal_msg_fun(topic_name, record):
        """
        将日志record对象中的日志内容部分处理为msg并返回（dict_info字典）

        @param {string} topic_name - 日志主题
        @param {object} record - 日志信息对象

        @return {string} - 处理后的msg
        """
        if hasattr(record, 'info_dict'):
            # 获取信息字典，进行格式化处理
            info_dict = record.info_dict
            _msg = None
            _logging_para = SimpleGRpcTools._get_logging_para_value(info_dict)
            if _logging_para['msg_class'] is not None:
                _msg = _logging_para['msg_class'](info_dict['para_json'])
            # 返回内容
            return CallChainTool.api_call_chain_log_str(
                msg=_msg, proto_msg=None,
                api_mapping=_logging_para['api_mapping'],
                api_call_type=info_dict['api_call_type'], 
                api_info_type=info_dict['api_info_type'],
                trace_id=info_dict['trace_id'], trace_level=info_dict['trace_level'],
                call_id=info_dict['call_id'], parent_id=info_dict['parent_id'],
                logging_head=_logging_para['logging_head'],
                is_print_msg=_logging_para['is_print_msg'],
                msg_print_kwargs=_logging_para['msg_print_kwargs'],
                key_para=_logging_para['key_para'],
                print_in_para=_logging_para['print_in_para'],
                use=info_dict['use'], error=info_dict['error'], 
                trace_str=info_dict['trace_str']
            )
        else:
            # 直接原样返回即可
            return record.msg
```



**2、定义最终需要进行日志输出的日志对象**

所定义的日志对象将负责进行最终日志的输出处理，这个日志对象可以定义为一般的文件记录日志，或者远程调用日志，或则队列日志等，以支持各种形式的日志处理：

```
		# 创建一个最终进行日志处理的日志对象
       logger = simple_log.Logger(
            conf_file_name=_TEMP_DIR + '/../../simple_grpc/test_simple_grpc.json',
            logger_name=simple_log.EnumLoggerName.ConsoleAndFile,
            config_type=simple_log.EnumLoggerConfigType.JSON_FILE,
            logfile_path=_TEMP_DIR + '/log/test_case_asyn.log',
            is_create_logfile_by_day=True
        )
        logger.setLevelWithHandler(simple_log.DEBUG)
```

注意：通过异步日志处理，会将logger日志对象的输出格式变更为'%(message)s'，因此需要注意这个日志对象不要和其他日志处理共用。



**3、通过create_call_chain_logger方法生成一个异步日志Logger对象**

有几个参数需要注意：

- 如果需要自己处理日志的输出，可以传入asyn_logging_fun函数，这时候就不会使用logger进行日志输出
- asyn_deal_msg_fun需要指定进行特殊的日志内容（msg）的生成函数
- asyn_formater指定了最终日志输出的格式，如果传空会默认从logger中获取原始格式

另外这个函数也支持返回非异步的日志对象，指定asyn_logging为False就可以按正常同步日志的模式处理

```
        # 利用已有的日志对象创建异步日志（后续将通过该日志对象进行真正的日志记录）
        _asyn_logger = CallChainTool.create_call_chain_logger(
            logger=logger, is_use_global_logger=False,
            asyn_logging=True, asyn_log_config_level=logging.DEBUG,
            topic_name='', asyn_logging_fun=None, 
            asyn_deal_msg_fun=api_call_chain_asyn_deal_msg_fun, 
            asyn_formater=None
        )
```



**4、启动日志异步处理线程**

通过start_call_chain_asyn_logging启动异步日志的后台处理：

```
		# 启动写日志任务
        CallChainTool.start_call_chain_asyn_logging(_asyn_logger)
```



**5、进行日志内容的输出处理**

通过call_chain_asyn_log执行日志的输出：

```
            # 使用了异步日志
            CallChainTool.call_chain_asyn_log(
                logger, _info_dict['log_level'], '',
                extra={
                    'info_dict': _info_dict,
                    'callFunLevel': _info_dict['call_fun_level']
                }
            )
```



**6、可以暂停日志异步处理线程（暂停日志的输出）**

通过stop_call_chain_asyn_logging暂停日志异步处理线程：

```
CallChainTool.stop_call_chain_asyn_logging(_asyn_logger)
```

